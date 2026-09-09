"""
Milestone 4: drive real Archipelago location checks from live SCS telemetry, and apply
received items to a real save file on demand -- the "hybrid: instant notification, deferred
effect" UX the user chose. Locations are no longer manually triggered (that was Milestone 3);
`telemetry_watcher` below edge-detects real `special_b.jobDelivered` events from shared
memory and sends the matching `Delivery #N` check automatically. Items are still applied on
the player's own schedule via `/sync <path>`, since Milestone 0 proved that must happen at
the main menu, not mid-session.

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

from bridge.sync.apply_items import apply_money_delta
from bridge.telemetry.shared_memory_map import MMF_NAME, MMF_SIZE, ScsTelemetryMap
from bridge.telemetry.win_mmf import ExistingFileMapping

TELEMETRY_POLL_HZ = 10
PENDING_ITEMS_FILE = Path(__file__).parent / "pending_items.json"


class Ets2AtsClientCommandProcessor(ClientCommandProcessor):
    ctx: "Ets2AtsContext"

    def _cmd_sync(self, save_path: str = "") -> bool:
        """Apply all pending received items to a save file's bank balance. Do this at the
        main menu, not mid-session (see docs/design-decisions.md, Milestone 0)."""
        if not self.ctx.pending_items:
            self.output("No pending items to sync.")
            return True
        if not save_path:
            self.output("Usage: /sync <path to game.sii> -- do this at the main menu, "
                         "not mid-session.")
            return False
        total = sum(ITEM_MONEY_VALUES[name] for name in self.ctx.pending_items)
        try:
            old, new = apply_money_delta(Path(save_path), total)
        except Exception as exc:
            self.output(f"Sync failed: {exc}")
            return False
        self.output(f"Applied {len(self.ctx.pending_items)} item(s) (+{total}): "
                     f"{old} -> {new}. Now click Continue on that profile.")
        self.ctx.pending_items.clear()
        self.ctx.save_pending()
        return True


class Ets2AtsContext(CommonContext):
    command_processor = Ets2AtsClientCommandProcessor
    game = GAME_NAME
    items_handling = 0b111  # full remote: get everything, including our own checks

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.delivery_count = 0
        self.pending_items: list[str] = self.load_pending()

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
        elif cmd == "ReceivedItems":
            for item in args["items"]:
                item_name = self.item_names.lookup_in_game(item.item, self.game)
                logger.info(f"RECEIVED ITEM: {item_name} (from location {item.location}, "
                            f"player {item.player}) -- queued, run /sync to apply.")
                self.pending_items.append(item_name)
            self.save_pending()


async def telemetry_watcher(ctx: Ets2AtsContext) -> None:
    """Poll SCS shared memory; turn real jobDelivered edges into LocationChecks."""
    mm: ExistingFileMapping | None = None
    prev_delivered = False

    while not ctx.exit_event.is_set():
        if mm is None:
            try:
                mm = ExistingFileMapping(MMF_NAME, MMF_SIZE)
                logger.info("[telemetry] attached to SCS shared memory.")
            except OSError:
                await asyncio.sleep(5.0)
                continue

        buf = mm.read()[:ctypes.sizeof(ScsTelemetryMap)]
        snap = ScsTelemetryMap.from_buffer_copy(buf)

        delivered = bool(snap.special_b.jobDelivered)
        if delivered and not prev_delivered:
            ctx.delivery_count += 1
            location_name = f"Delivery #{ctx.delivery_count}"
            location_id = LOCATION_NAME_TO_ID.get(location_name)
            if location_id is not None:
                logger.info(f"[telemetry] jobDelivered -> checking {location_name!r} "
                            f"(revenue={snap.gameplay_ll.jobDeliveredRevenue})")
                await ctx.check_locations([location_id])
            else:
                logger.info(f"[telemetry] jobDelivered detected, but all "
                            f"{len(LOCATION_NAME_TO_ID)} delivery locations are checked.")
        prev_delivered = delivered

        await asyncio.sleep(1.0 / TELEMETRY_POLL_HZ)

    if mm is not None:
        mm.close()


async def main_async(args) -> None:
    ctx = Ets2AtsContext(args.connect, args.password)
    if args.name:
        ctx.auth = args.name  # skip the interactive slot-name prompt for scripted runs
    ctx.server_task = asyncio.create_task(server_loop(ctx), name="server loop")
    ctx.run_cli()

    asyncio.create_task(telemetry_watcher(ctx), name="telemetry watcher")

    await ctx.exit_event.wait()
    ctx.server_address = None
    await ctx.shutdown()


if __name__ == "__main__":
    parser = get_base_parser(description="Milestone 4 ETS2ATS client (telemetry checks, /sync items).")
    parser.add_argument("--name", default=None, help="Slot name (skips the interactive prompt).")
    cli_args = parser.parse_args()
    Utils.init_logging("ETS2ATSClient")
    asyncio.run(main_async(cli_args))
