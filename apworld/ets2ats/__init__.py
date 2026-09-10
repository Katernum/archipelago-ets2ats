"""
Milestone 6: the real ETS2/ATS design, per docs/game-design.md. Split into modules matching
the official APQuest tutorial shape (options/items/locations/rules), now that there's enough
real design to justify it -- Milestones 3-5 kept everything in this one file since it was
pure plumbing/placeholder content.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

from BaseClasses import ItemClassification, Region
from worlds.AutoWorld import World
from worlds.LauncherComponents import Component, Type, components
from worlds.LauncherComponents import launch as launch_component

from .items import (
    FILLER_WEIGHTS,
    ITEM_CLASSIFICATIONS,
    ITEM_NAME_TO_ID,
    MONEY_ITEM_VALUES,
    XP_ITEM_VALUES,
    Ets2AtsItem,
)
from .locations import (
    CITY_DISCOVERED_LOCATIONS,
    DEALER_UNLOCKED_LOCATIONS,
    DISTANCE_LOCATIONS,
    DISTANCE_MILESTONES_KM,
    LOCATION_NAME_TO_ID,
    STARTER_CITIES,
    VICTORY_LOCATION,
    XP_LOCATIONS,
    XP_MILESTONES,
    Ets2AtsLocation,
)
from .options import Ets2AtsOptions
from .rules import set_rules

# Dev-only: prototypes/sync_apworld.py drops this marker when copying this folder into an
# Archipelago checkout, so `launch_client` below can find bridge/ next door in this repo
# instead of inside the packaged world (see docs/design-decisions.md). A real packaged
# .apworld has no marker -- bridge/'s code would need to be bundled inside it instead.
_dev_repo_root = Path(__file__).parent / "_dev_repo_root.txt"
if _dev_repo_root.exists():
    repo_root = _dev_repo_root.read_text().strip()
    if repo_root not in sys.path:
        sys.path.insert(0, repo_root)


def launch_client(*args: str) -> None:
    from bridge.ap_client.client import launch
    launch_component(launch, name="ETS2ATS Client", args=args)


components.append(Component("ETS2ATS Client", func=launch_client, component_type=Type.CLIENT))

GAME_NAME = "ETS2ATS"

GOAL_TYPE_NAMES = ["flawless_long_haul", "money_target", "delivery_count", "xp_amount"]


class Ets2AtsWorld(World):
    """The real ETS2/ATS design: deliveries, city/dealer discovery, and stat milestones as
    locations; money, XP, and fines as items; a player-selectable goal condition."""

    game = GAME_NAME
    options_dataclass = Ets2AtsOptions
    options: Ets2AtsOptions
    item_name_to_id = ITEM_NAME_TO_ID
    location_name_to_id = LOCATION_NAME_TO_ID

    def create_regions(self) -> None:
        menu = Region("Menu", self.player, self.multiworld)
        self.multiworld.regions.append(menu)

        delivery_names = [
            f"Delivery #{n}" for n in range(1, self.options.delivery_location_count.value + 1)
        ]
        active_names = (
            delivery_names + CITY_DISCOVERED_LOCATIONS + DEALER_UNLOCKED_LOCATIONS
            + DISTANCE_LOCATIONS + XP_LOCATIONS
        )
        menu.add_locations({name: LOCATION_NAME_TO_ID[name] for name in active_names}, Ets2AtsLocation)

        # address=None: a pure event location, not a networked one -- required to pair with
        # the code=None event item placed on it below (see locations.py).
        victory = Ets2AtsLocation(self.player, VICTORY_LOCATION, None, menu)
        menu.locations.append(victory)
        victory.place_locked_item(
            Ets2AtsItem("Victory", ItemClassification.progression, None, self.player)
        )

        set_rules(self)

    def create_items(self) -> None:
        location_count = len(self.multiworld.get_unfilled_locations(self.player))
        chosen = self.random.choices(
            list(FILLER_WEIGHTS), weights=list(FILLER_WEIGHTS.values()), k=location_count
        )
        self.multiworld.itempool += [self.create_item(name) for name in chosen]

    def create_item(self, name: str) -> Ets2AtsItem:
        return Ets2AtsItem(name, ITEM_CLASSIFICATIONS[name], ITEM_NAME_TO_ID[name], self.player)

    def get_filler_item_name(self) -> str:
        return self.random.choices(list(FILLER_WEIGHTS), weights=list(FILLER_WEIGHTS.values()))[0]

    def fill_slot_data(self) -> dict[str, Any]:
        return {
            "goal_type": GOAL_TYPE_NAMES[self.options.goal_type.value],
            "goal_distance_km": self.options.goal_distance_km.value,
            "goal_max_damage_pct": self.options.goal_max_damage_pct.value,
            "goal_money": self.options.goal_money.value,
            "goal_delivery_count": self.options.goal_delivery_count.value,
            "goal_xp": self.options.goal_xp.value,
            "starter_cities": STARTER_CITIES,
            "distance_milestones_km": DISTANCE_MILESTONES_KM,
            "xp_milestones": XP_MILESTONES,
            "money_item_values": MONEY_ITEM_VALUES,
            "xp_item_values": XP_ITEM_VALUES,
        }
