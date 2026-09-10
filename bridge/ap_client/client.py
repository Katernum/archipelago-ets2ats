"""
Milestone 5: bundle everything into one launch -- the AP network client, the telemetry
watcher, and now the tray icon + transparent overlay + dashboard (bridge/overlay/) -- and
expose a `launch()` entry point registrable as an Archipelago Launcher Component (see
apworld/ets2ats/__init__.py), so a player never runs a command line at all: one click in the
Launcher they already use for any other game's client brings up the whole stack.

Items are still applied on the player's own schedule (the "hybrid: instant notification,
deferred effect" UX), but Sync Now (tray menu or dashboard button) no longer needs a manual
path -- bridge/sync/profile_paths.py locates the save from the AP slot name, matching it to
the ETS2/ATS profile name (falling back to "most recently modified save" with a warning if
no profile matches). `/sync [path]` remains as a manual CLI override for when that heuristic
picks the wrong file.

Must be run from within an Archipelago source checkout (needs CommonClient.py, NetUtils.py,
worlds/ets2ats, etc. importable) -- this repo doesn't vendor them.

Usage: py client.py --connect localhost:38281
"""

from __future__ import annotations

import asyncio
import ctypes
import json
import sys
import typing
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import ModuleUpdate
ModuleUpdate.update()

import Utils
from CommonClient import ClientCommandProcessor, CommonContext, get_base_parser, logger, server_loop
from worlds.ets2ats import GAME_NAME, ITEM_MONEY_VALUES, LOCATION_NAME_TO_ID

from bridge.overlay.ui import UI
from bridge.sync import profile_paths
from bridge.sync.apply_items import apply_money_delta
from bridge.telemetry.shared_memory_map import MMF_NAME, MMF_SIZE, ScsTelemetryMap
from bridge.telemetry.win_mmf import ExistingFileMapping

TELEMETRY_POLL_HZ = 10
PENDING_ITEMS_FILE = Path(__file__).parent / "pending_items.json"
TELEMETRY_GAME_NAMES = {1: "ets2", 2: "ats"}


class Ets2AtsClientCommandProcessor(ClientCommandProcessor):
    ctx: "Ets2AtsContext"

    def _cmd_sync(self, save_path: str = "") -> bool:
        """Apply all pending received items to a save file's bank balance (auto-detects the
        save from your slot name if no path is given). Do this at the main menu, not
        mid-session (see docs/design-decisions.md, Milestone 0)."""
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
        self.pending_items: list[str] = self.load_pending()
        self.last_seen_game: str | None = None
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

    total = sum(ITEM_MONEY_VALUES[name] for name in ctx.pending_items)
    try:
        old, new = apply_money_delta(save_path, total)
    except Exception as exc:
        report(f"Sync failed: {exc}")
        return

    report(f"Synced {len(ctx.pending_items)} item(s) (+{total}): {old} -> {new}. "
           "Click Continue on that profile.")
    ctx.pending_items.clear()
    ctx.save_pending()
    if ctx.tracker_ui:
        ctx.tracker_ui.set_pending([])


async def telemetry_watcher(ctx: Ets2AtsContext) -> None:
    """Poll SCS shared memory; turn real jobDelivered edges into LocationChecks."""
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
            ctx.delivery_count += 1
            location_name = f"Delivery #{ctx.delivery_count}"
            location_id = LOCATION_NAME_TO_ID.get(location_name)
            if location_id is not None:
                logger.info(f"[telemetry] jobDelivered -> checking {location_name!r} "
                            f"(revenue={snap.gameplay_ll.jobDeliveredRevenue})")
                if ctx.tracker_ui:
                    ctx.tracker_ui.notify(f"Check: {location_name}")
                await ctx.check_locations([location_id])
            else:
                logger.info(f"[telemetry] jobDelivered detected, but all "
                            f"{len(LOCATION_NAME_TO_ID)} delivery locations are checked.")
        prev_delivered = delivered

        await asyncio.sleep(1.0 / TELEMETRY_POLL_HZ)

    if mm is not None:
        mm.close()


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

    await ctx.exit_event.wait()
    ctx.server_address = None
    await ctx.shutdown()
    if ctx.tracker_ui:
        ctx.tracker_ui.stop()


def launch(*args: str) -> None:
    """Entry point for the Archipelago Launcher component (apworld/ets2ats/__init__.py) --
    also used by the __main__ block below for direct CLI invocation."""
    parser = get_base_parser(description="ETS2ATS client (telemetry checks, tray + overlay, /sync items).")
    parser.add_argument("--name", default=None, help="Slot name (skips the interactive prompt).")
    cli_args = parser.parse_args(list(args) if args else None)
    Utils.init_logging("ETS2ATSClient")
    asyncio.run(main_async(cli_args))


if __name__ == "__main__":
    launch(*sys.argv[1:])
