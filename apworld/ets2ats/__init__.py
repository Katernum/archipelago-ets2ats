"""
Milestone 4 real slice: still a tiny stub world (not the full Milestone 7 design), but now
backed by real game mechanics instead of pure plumbing placeholders --

- Locations check off real telemetry events (`special_b.jobDelivered` rising edges read from
  the SCS shared-memory map, see bridge/telemetry/), one location per delivery in order.
- Items are money bundles applied to a real save file's `bank.money_account` field (the exact
  mechanism proven safe in Milestone 0/1), via bridge/sync/apply_items.py.

Still one flat region, no access rules -- that's still deferred to Milestone 7.
"""

from __future__ import annotations

from typing import Any

from BaseClasses import Item, ItemClassification, Location, Region
from worlds.AutoWorld import World

GAME_NAME = "ETS2ATS"

ITEM_MONEY_VALUES = {
    "10,000 Bundle": 10_000,
    "25,000 Bundle": 25_000,
    "50,000 Bundle": 50_000,
}

ITEM_NAME_TO_ID = {name: i + 1 for i, name in enumerate(ITEM_MONEY_VALUES)}

LOCATION_NAME_TO_ID = {
    "Delivery #1": 1,
    "Delivery #2": 2,
    "Delivery #3": 3,
}

ITEM_CLASSIFICATIONS = {name: ItemClassification.filler for name in ITEM_MONEY_VALUES}


class Ets2AtsItem(Item):
    game = GAME_NAME


class Ets2AtsLocation(Location):
    game = GAME_NAME


class Ets2AtsWorld(World):
    """Milestone 4 slice: real telemetry-driven locations, real save-file-applied items."""

    game = GAME_NAME
    item_name_to_id = ITEM_NAME_TO_ID
    location_name_to_id = LOCATION_NAME_TO_ID

    def create_regions(self) -> None:
        menu = Region("Menu", self.player, self.multiworld)
        self.multiworld.regions.append(menu)
        menu.add_locations(LOCATION_NAME_TO_ID, Ets2AtsLocation)

    def create_items(self) -> None:
        self.multiworld.itempool += [self.create_item(name) for name in ITEM_MONEY_VALUES]

    def create_item(self, name: str) -> Ets2AtsItem:
        return Ets2AtsItem(name, ITEM_CLASSIFICATIONS[name], ITEM_NAME_TO_ID[name], self.player)

    def get_filler_item_name(self) -> str:
        return "10,000 Bundle"

    def fill_slot_data(self) -> dict[str, Any]:
        return {}
