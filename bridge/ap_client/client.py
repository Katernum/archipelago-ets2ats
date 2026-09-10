"""
Milestone 6: real telemetry- and save-based checks (deliveries, city discovery, dealer
unlocks, distance/XP milestones), real items (money, XP, fines), and player-selectable goal
detection, layered on top of the Milestone 5 tray/overlay/dashboard/Launcher plumbing.

Two independent watcher tasks feed checks, matching the two detection mechanisms established
in docs/game-design.md: `telemetry_watcher` handles anything with a live shared-memory event
(deliveries, distance accumulated per delivery), `save_poller` handles anything that only
exists in the save file (city discovery, dealer unlocks, money, XP) by periodically
re-reading and diffing it. The save poller is read-only, so unlike Sync it never needs the
main-menu precondition or a confirmation prompt -- reading the wrong profile by mistake just
misattributes a discovery, it can't corrupt anything.

Must be run from within an Archipelago source checkout (needs CommonClient.py, NetUtils.py,
worlds/ets2ats, etc. importable) -- this repo doesn't vendor them.

Usage: py client.py --connect localhost:38281
"""

from __future__ import annotations

import asyncio
import ctypes
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import ModuleUpdate
ModuleUpdate.update()

import Utils
from CommonClient import ClientCommandProcessor, CommonContext, get_base_parser, logger, server_loop
from NetUtils import ClientStatus
from worlds.ets2ats import GAME_NAME
from worlds.ets2ats.items import MONEY_ITEM_VALUES, XP_ITEM_VALUES
from worlds.ets2ats.locations import DISTANCE_MILESTONES_KM, LOCATION_NAME_TO_ID, STARTER_CITIES, XP_MILESTONES

from bridge.overlay.ui import UI
from bridge.sync import profile_paths
from bridge.sync.apply_items import apply_deltas
from bridge.sync.save_poller import read_tracked_fields
from bridge.telemetry.shared_memory_map import MMF_NAME, MMF_SIZE, ScsTelemetryMap
from bridge.telemetry.win_mmf import ExistingFileMapping

TELEMETRY_POLL_HZ = 10
SAVE_POLL_SECONDS = 20
PENDING_ITEMS_FILE = Path(__file__).parent / "pending_items.json"
TELEMETRY_GAME_NAMES = {1: "ets2", 2: "ats"}
CITY_ID_TO_NAME = dict(STARTER_CITIES)


class Ets2AtsClientCommandProcessor(ClientCommandProcessor):
    ctx: "Ets2AtsContext"

    def _cmd_sync(self, save_path: str = "") -> bool:
        """Apply all pending received items to a save file's bank/XP (auto-detects the save
        from your slot name if no path is given). Do this at the main menu, not mid-session
        (see docs/design-decisions.md, Milestone 0)."""
        explicit = Path(save_path) if save_path else None
        Utils.async_start(perform_sync(self.ctx, explicit))
        return True


class Ets2AtsContext(CommonContext):
    command_processor = Ets2AtsClientCommandProcessor
    game = GAME_NAME
    items_handling = 0b111  # full remote: get everything, including our own checks

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.delivery_count = 0
        self.cumulative_distance_km = 0.0
        self.distance_milestones_sent: set[int] = set()
        self.xp_milestones_sent: set[int] = set()
        self.visited_cities_seen: set[str] = set()
        self.unlocked_dealers_seen: set[str] = set()
        self.pending_items: list[str] = self.load_pending()
        self.last_seen_game: str | None = None
        self.goal_type: str | None = None
        self.goal_params: dict = {}
        self.goal_sent = False
        # NOTE: deliberately not named `self.ui` -- CommonContext reserves that name for its
        # own (Kivy-based) GUI object and checks `if self.ui:` internally (e.g. server_loop's
        # reconnect handling); overwriting it here broke that with no error until the
        # reconnect path actually ran. See docs/design-decisions.md, Milestone 5.
        self.tracker_ui: UI | None = None  # set once the asyncio loop is running, see main_async

    @staticmethod
    def load_pending() -> list[str]:
        if PENDING_ITEMS_FILE.exists():
            return json.loads(PENDING_ITEMS_FILE.read_text())
        return []

    def save_pending(self) -> None:
        PENDING_ITEMS_FILE.write_text(json.dumps(self.pending_items))

    async def server_auth(self, password_requested: bool = False) -> None:
        if password_requested and not self.password:
            await super().server_auth(password_requested)
        await self.get_username()
        await self.send_connect()

    def on_package(self, cmd: str, args: dict) -> None:
        if cmd == "Connected":
            logger.info(f"Connected as slot {self.slot} in team {self.team}.")
            slot_data = args.get("slot_data", {})
            self.goal_type = slot_data.get("goal_type")
            self.goal_params = slot_data
            if self.tracker_ui:
                self.tracker_ui.set_status(f"Connected as {self.auth} (slot {self.slot})")
        elif cmd == "ReceivedItems":
            for item in args["items"]:
                item_name = self.item_names.lookup_in_game(item.item, self.game)
                logger.info(f"RECEIVED ITEM: {item_name} (from location {item.location}, "
                            f"player {item.player}) -- queued, run /sync to apply.")
                self.pending_items.append(item_name)
                if self.tracker_ui:
                    self.tracker_ui.notify(f"Item received: {item_name} -- Sync when ready")
                    self.tracker_ui.set_pending(self.pending_items)
            self.save_pending()


async def perform_sync(ctx: Ets2AtsContext, explicit_path: Path | None) -> None:
    def report(text: str) -> None:
        logger.info(text)
        if ctx.tracker_ui:
            ctx.tracker_ui.notify(text)

    if not ctx.pending_items:
        report("No pending items to sync.")
        return

    save_path = explicit_path
    if save_path is None:
        game = ctx.last_seen_game or "ets2"
        save_path = profile_paths.find_profile_save(game, ctx.auth or "")
        if save_path is None:
            # No exact profile-name match -- this is a guess, not the mechanism the player
            # set up (renaming their profile to match their slot name). Applying a wrong
            # guess would silently corrupt someone else's real save, so it requires an
            # explicit yes rather than proceeding quietly.
            fallback = profile_paths.find_any_recent_save(game)
            if fallback is None:
                report("Could not locate a save file to sync. Use /sync <path> to specify one.")
                return
            if ctx.tracker_ui is None:
                report(f"No profile named {ctx.auth!r} found, and no UI is available to "
                        "confirm a fallback. Use /sync <path> to specify one explicitly.")
                return
            confirmed = await asyncio.wrap_future(ctx.tracker_ui.confirm(
                f"No profile named {ctx.auth!r} found.\n\n"
                f"Apply {len(ctx.pending_items)} pending item(s) to the most recently "
                f"modified save instead?\n\n{fallback}\n\n"
                "Rename your profile to match your slot name to avoid seeing this."
            ))
            if not confirmed:
                report("Sync cancelled -- no changes made.")
                return
            save_path = fallback

    money_delta = sum(MONEY_ITEM_VALUES[name] for name in ctx.pending_items if name in MONEY_ITEM_VALUES)
    xp_delta = sum(XP_ITEM_VALUES[name] for name in ctx.pending_items if name in XP_ITEM_VALUES)

    try:
        results = apply_deltas(save_path, money_delta=money_delta, xp_delta=xp_delta)
    except Exception as exc:
        report(f"Sync failed: {exc}")
        return

    parts = []
    if "money" in results:
        old, new = results["money"]
        parts.append(f"money {old} -> {new}")
    if "xp" in results:
        old, new = results["xp"]
        parts.append(f"XP {old} -> {new}")
    report(f"Synced {len(ctx.pending_items)} item(s): {', '.join(parts)}. "
           "Click Continue on that profile.")
    ctx.pending_items.clear()
    ctx.save_pending()
    if ctx.tracker_ui:
        ctx.tracker_ui.set_pending([])


async def report_goal_complete(ctx: Ets2AtsContext) -> None:
    if ctx.goal_sent:
        return
    ctx.goal_sent = True
    ctx.finished_game = True
    logger.info("[goal] condition met -- reporting CLIENT_GOAL.")
    if ctx.tracker_ui:
        ctx.tracker_ui.notify("Goal complete!")
    await ctx.send_msgs([{"cmd": "StatusUpdate", "status": ClientStatus.CLIENT_GOAL}])


async def telemetry_watcher(ctx: Ets2AtsContext) -> None:
    """Poll SCS shared memory for anything with a live event: jobDelivered edges drive
    Delivery #N locations, distance milestones, and two of the four goal types (flawless
    long-haul, delivery count)."""
    mm: ExistingFileMapping | None = None
    prev_delivered = False

    while not ctx.exit_event.is_set():
        if mm is None:
            try:
                mm = ExistingFileMapping(MMF_NAME, MMF_SIZE)
                logger.info("[telemetry] attached to SCS shared memory.")
                if ctx.tracker_ui:
                    ctx.tracker_ui.set_status("Telemetry: attached")
            except OSError:
                await asyncio.sleep(5.0)
                continue

        buf = mm.read()[:ctypes.sizeof(ScsTelemetryMap)]
        snap = ScsTelemetryMap.from_buffer_copy(buf)
        ctx.last_seen_game = TELEMETRY_GAME_NAMES.get(snap.scs_values.game, ctx.last_seen_game)

        delivered = bool(snap.special_b.jobDelivered)
        if delivered and not prev_delivered:
            distance_km = snap.gameplay_f.jobDeliveredDistanceKm
            damage_pct = snap.gameplay_f.jobDeliveredCargoDamage * 100.0

            ctx.delivery_count += 1
            location_name = f"Delivery #{ctx.delivery_count}"
            location_id = LOCATION_NAME_TO_ID.get(location_name)
            if location_id is not None:
                logger.info(f"[telemetry] jobDelivered -> checking {location_name!r} "
                            f"(distance={distance_km:.1f}km damage={damage_pct:.1f}%)")
                if ctx.tracker_ui:
                    ctx.tracker_ui.notify(f"Check: {location_name}")
                await ctx.check_locations([location_id])

            ctx.cumulative_distance_km += distance_km
            for threshold in DISTANCE_MILESTONES_KM:
                if threshold in ctx.distance_milestones_sent or ctx.cumulative_distance_km < threshold:
                    continue
                ctx.distance_milestones_sent.add(threshold)
                stat_location = f"Drive {threshold:,} km"
                stat_id = LOCATION_NAME_TO_ID.get(stat_location)
                if stat_id is not None:
                    logger.info(f"[telemetry] distance milestone -> checking {stat_location!r}")
                    if ctx.tracker_ui:
                        ctx.tracker_ui.notify(f"Check: {stat_location}")
                    await ctx.check_locations([stat_id])

            if ctx.goal_type == "flawless_long_haul" and not ctx.goal_sent:
                if (distance_km >= ctx.goal_params.get("goal_distance_km", float("inf"))
                        and damage_pct <= ctx.goal_params.get("goal_max_damage_pct", 0)):
                    await report_goal_complete(ctx)
            elif ctx.goal_type == "delivery_count" and not ctx.goal_sent:
                if ctx.delivery_count >= ctx.goal_params.get("goal_delivery_count", float("inf")):
                    await report_goal_complete(ctx)

        prev_delivered = delivered
        await asyncio.sleep(1.0 / TELEMETRY_POLL_HZ)

    if mm is not None:
        mm.close()


async def save_poller(ctx: Ets2AtsContext) -> None:
    """Periodically re-read the active save for anything with no live telemetry event: city
    discovery, dealer unlocks, XP milestones, and the two save-only goal types (money target,
    XP amount). Read-only -- no main-menu precondition, no confirmation prompt."""
    warned_no_profile_match = False

    while not ctx.exit_event.is_set():
        await asyncio.sleep(SAVE_POLL_SECONDS)

        game = ctx.last_seen_game or "ets2"
        save_path = profile_paths.find_profile_save(game, ctx.auth or "")
        if save_path is None:
            save_path = profile_paths.find_any_recent_save(game)
            if save_path is not None and not warned_no_profile_match:
                warned_no_profile_match = True
                logger.info(f"[save-poll] No profile named {ctx.auth!r} found -- reading "
                            "the most recently modified save instead. Rename your profile "
                            "to match your slot name to fix this.")
        if save_path is None:
            continue

        try:
            fields = read_tracked_fields(save_path)
        except Exception as exc:
            logger.info(f"[save-poll] Could not read {save_path}: {exc}")
            continue

        new_cities = fields.visited_cities - ctx.visited_cities_seen
        ctx.visited_cities_seen |= fields.visited_cities
        for city_id in new_cities:
            name = CITY_ID_TO_NAME.get(city_id)
            if name is None:
                continue
            location_name = f"City Discovered: {name}"
            location_id = LOCATION_NAME_TO_ID.get(location_name)
            if location_id is not None:
                logger.info(f"[save-poll] {city_id} newly visited -> checking {location_name!r}")
                if ctx.tracker_ui:
                    ctx.tracker_ui.notify(f"Check: {location_name}")
                await ctx.check_locations([location_id])

        new_dealers = fields.unlocked_dealers - ctx.unlocked_dealers_seen
        ctx.unlocked_dealers_seen |= fields.unlocked_dealers
        for city_id in new_dealers:
            name = CITY_ID_TO_NAME.get(city_id)
            if name is None:
                continue
            location_name = f"Dealer Unlocked: {name}"
            location_id = LOCATION_NAME_TO_ID.get(location_name)
            if location_id is not None:
                logger.info(f"[save-poll] {city_id} dealer newly unlocked -> checking {location_name!r}")
                if ctx.tracker_ui:
                    ctx.tracker_ui.notify(f"Check: {location_name}")
                await ctx.check_locations([location_id])

        for threshold in XP_MILESTONES:
            if threshold in ctx.xp_milestones_sent or fields.xp < threshold:
                continue
            ctx.xp_milestones_sent.add(threshold)
            location_name = f"Earn {threshold:,} XP"
            location_id = LOCATION_NAME_TO_ID.get(location_name)
            if location_id is not None:
                logger.info(f"[save-poll] XP milestone -> checking {location_name!r}")
                if ctx.tracker_ui:
                    ctx.tracker_ui.notify(f"Check: {location_name}")
                await ctx.check_locations([location_id])

        if ctx.goal_type == "money_target" and not ctx.goal_sent:
            if fields.money >= ctx.goal_params.get("goal_money", float("inf")):
                await report_goal_complete(ctx)
        elif ctx.goal_type == "xp_amount" and not ctx.goal_sent:
            if fields.xp >= ctx.goal_params.get("goal_xp", float("inf")):
                await report_goal_complete(ctx)


def _start_ui(ctx: Ets2AtsContext, loop: asyncio.AbstractEventLoop) -> UI:
    """UI callbacks run on the tray/Tk threads, not the asyncio loop -- hand them back to
    the loop with call_soon_threadsafe/run_coroutine_threadsafe rather than touching
    asyncio state directly from a foreign thread."""

    def on_sync_now() -> None:
        asyncio.run_coroutine_threadsafe(perform_sync(ctx, None), loop)

    def on_quit() -> None:
        loop.call_soon_threadsafe(ctx.exit_event.set)

    return UI(on_sync_now=on_sync_now, on_quit=on_quit)


async def main_async(args) -> None:
    ctx = Ets2AtsContext(args.connect, args.password)
    if args.name:
        ctx.auth = args.name  # skip the interactive slot-name prompt for scripted runs
    ctx.server_task = asyncio.create_task(server_loop(ctx), name="server loop")
    ctx.run_cli()

    ctx.tracker_ui = _start_ui(ctx, asyncio.get_running_loop())
    ctx.tracker_ui.set_pending(ctx.pending_items)

    asyncio.create_task(telemetry_watcher(ctx), name="telemetry watcher")
    asyncio.create_task(save_poller(ctx), name="save poller")

    await ctx.exit_event.wait()
    ctx.server_address = None
    await ctx.shutdown()
    if ctx.tracker_ui:
        ctx.tracker_ui.stop()


def launch(*args: str) -> None:
    """Entry point for the Archipelago Launcher component (apworld/ets2ats/__init__.py) --
    also used by the __main__ block below for direct CLI invocation."""
    parser = get_base_parser(description="ETS2ATS client (telemetry+save checks, tray + overlay, /sync items).")
    parser.add_argument("--name", default=None, help="Slot name (skips the interactive prompt).")
    cli_args = parser.parse_args(list(args) if args else None)
    Utils.init_logging("ETS2ATSClient")
    asyncio.run(main_async(cli_args))


if __name__ == "__main__":
    launch(*sys.argv[1:])
