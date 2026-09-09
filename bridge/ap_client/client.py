"""
Milestone 3: minimal Archipelago client, built on CommonClient/CommonContext, for the
placeholder "ETS2ATS Test" world. No game integration yet -- this proves the AP network
plumbing (connect, auth, DataPackage, LocationChecks, ReceivedItems) works end to end.
Location checks are triggered manually via a `/check <location name>` command instead of
being detected from telemetry (that's Milestone 4).

Must be run from within an Archipelago source checkout (needs CommonClient.py, NetUtils.py,
worlds/ets2ats, etc. importable) -- this repo doesn't vendor them.

Usage: py client.py --connect localhost:38281
"""

from __future__ import annotations

import asyncio
import typing

import ModuleUpdate
ModuleUpdate.update()

import Utils
from CommonClient import ClientCommandProcessor, CommonContext, get_base_parser, logger, server_loop
from worlds.ets2ats import LOCATION_NAME_TO_ID

GAME_NAME = "ETS2ATS Test"


class Ets2AtsClientCommandProcessor(ClientCommandProcessor):
    ctx: "Ets2AtsContext"

    def _cmd_check(self, location_name: str = "") -> bool:
        """Manually report a location check by name (Milestone 3 stand-in for telemetry detection)."""
        if not self.ctx.server or self.ctx.slot is None:
            self.output("Not connected to a server yet.")
            return False
        location_id = LOCATION_NAME_TO_ID.get(location_name)
        if location_id is None:
            self.output(f"Unknown location {location_name!r}. Known locations: "
                        f"{', '.join(sorted(LOCATION_NAME_TO_ID))}")
            return False
        Utils.async_start(self.ctx.check_locations([location_id]))
        self.output(f"Sent check for {location_name!r} (id {location_id}).")
        return True


class Ets2AtsContext(CommonContext):
    command_processor = Ets2AtsClientCommandProcessor
    game = GAME_NAME
    items_handling = 0b111  # full remote: get everything, including our own checks

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
                            f"player {item.player})")


async def auto_check_after_connect(ctx: Ets2AtsContext, location_name: str) -> None:
    """Non-interactive stand-in for typing /check -- waits for a real connection, then fires once."""
    while not (ctx.server and ctx.slot is not None):
        await asyncio.sleep(0.2)
    location_id = LOCATION_NAME_TO_ID[location_name]
    logger.info(f"[auto-check] sending check for {location_name!r} (id {location_id})")
    await ctx.check_locations([location_id])


async def main_async(args) -> None:
    ctx = Ets2AtsContext(args.connect, args.password)
    if args.name:
        ctx.auth = args.name  # skip the interactive slot-name prompt for scripted runs
    ctx.server_task = asyncio.create_task(server_loop(ctx), name="server loop")
    ctx.run_cli()

    if args.auto_check:
        asyncio.create_task(auto_check_after_connect(ctx, args.auto_check), name="auto-check")

    await ctx.exit_event.wait()
    ctx.server_address = None
    await ctx.shutdown()


if __name__ == "__main__":
    parser = get_base_parser(description="Milestone 3 ETS2ATS test client (manual /check command).")
    parser.add_argument("--name", default=None, help="Slot name (skips the interactive prompt).")
    parser.add_argument("--auto-check", default=None,
                         help="Automatically send this location check once connected "
                              "(non-interactive stand-in for /check, for scripted testing).")
    cli_args = parser.parse_args()
    Utils.init_logging("ETS2ATSTestClient")
    asyncio.run(main_async(cli_args))
