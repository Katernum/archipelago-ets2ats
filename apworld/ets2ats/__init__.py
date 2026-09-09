"""
Milestone 3 placeholder apworld: the smallest possible world (3 locations, 3 items, one
region, no access rules) purely to prove the Archipelago generation/server/client plumbing
works end-to-end, independent of any real game integration.

This is NOT the real ETS2/ATS design (that's Milestone 7) -- it exists so Milestone 3 can
validate: generate a multiworld with this game -> run a local server -> connect a client
built on CommonClient -> send a LocationChecks -> receive a ReceivedItems.

Modeled on the official APQuest tutorial world (worlds/apquest in the Archipelago repo),
condensed into one file since there's no real game logic yet to justify splitting into
items.py/locations.py/regions.py/rules.py.
"""

from __future__ import annotations

from typing import Any

from BaseClasses import Item, ItemClassification, Location, Region
from worlds.AutoWorld import World

GAME_NAME = "ETS2ATS Test"

ITEM_NAME_TO_ID = {
    "Progressive Truck": 1,
    "Money Bundle": 2,
}

LOCATION_NAME_TO_ID = {
    "Deliver Job A": 1,
    "Deliver Job B": 2,
    "Deliver Job C": 3,
}

ITEM_CLASSIFICATIONS = {
    "Progressive Truck": ItemClassification.progression,
    "Money Bundle": ItemClassification.filler,
}


class Ets2AtsTestItem(Item):
    game = GAME_NAME


class Ets2AtsTestLocation(Location):
    game = GAME_NAME


class Ets2AtsTestWorld(World):
    """Minimal placeholder world for validating the Archipelago plumbing (Milestone 3)."""

    game = GAME_NAME
    item_name_to_id = ITEM_NAME_TO_ID
    location_name_to_id = LOCATION_NAME_TO_ID

    def create_regions(self) -> None:
        menu = Region("Menu", self.player, self.multiworld)
        self.multiworld.regions.append(menu)
        menu.add_locations(LOCATION_NAME_TO_ID, Ets2AtsTestLocation)

    def create_items(self) -> None:
        pool = [
            self.create_item("Progressive Truck"),
            self.create_item("Money Bundle"),
            self.create_item("Money Bundle"),
        ]
        self.multiworld.itempool += pool

    def create_item(self, name: str) -> Ets2AtsTestItem:
        return Ets2AtsTestItem(name, ITEM_CLASSIFICATIONS[name], ITEM_NAME_TO_ID[name], self.player)

    def get_filler_item_name(self) -> str:
        return "Money Bundle"

    def fill_slot_data(self) -> dict[str, Any]:
        return {}
