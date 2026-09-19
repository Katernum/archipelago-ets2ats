"""
Milestone 6: the real ETS2/ATS design, per docs/game-design.md. Split into modules matching
the official APQuest tutorial shape (options/items/locations/rules), now that there's enough
real design to justify it -- Milestones 3-5 kept everything in this one file since it was
pure plumbing/placeholder content.
"""

from __future__ import annotations

from typing import Any

from BaseClasses import ItemClassification, Region
from worlds.AutoWorld import World
from worlds.LauncherComponents import Component, Type, components
from worlds.LauncherComponents import launch as launch_component

from .city_data import CITIES, DLC_OPTION_NAMES
from .items import (
    FILLER_WEIGHTS,
    ITEM_CLASSIFICATIONS,
    ITEM_NAME_TO_ID,
    MONEY_ITEM_VALUES,
    XP_ITEM_VALUES,
    Ets2AtsItem,
)
from .locations import (
    DISTANCE_LOCATIONS,
    DISTANCE_MILESTONES_KM,
    LOCATION_NAME_TO_ID,
    VICTORY_LOCATION,
    XP_LOCATIONS,
    XP_MILESTONES,
    Ets2AtsLocation,
)
from .options import Ets2AtsOptions
from .rules import set_rules


def launch_client(*args: str) -> None:
    # bridge/ lives inside this package now (apworld/ets2ats/bridge/) so it ships inside the
    # real .apworld -- no sys.path tricks needed, this is just a normal nested import.
    from .bridge.ap_client.client import launch
    launch_component(launch, name="ETS2ATS Client", args=args)


components.append(Component("ETS2ATS Client", func=launch_client, component_type=Type.CLIENT))

GAME_NAME = "ETS2ATS"

GOAL_TYPE_NAMES = ["flawless_long_haul", "money_target", "delivery_count", "xp_amount"]


def _active_cities(options: Ets2AtsOptions) -> dict[str, str]:
    """city_id -> display_name for base game plus every DLC this player has enabled. Shared
    between create_regions (which locations exist) and fill_slot_data (what the client needs
    to map a save's city ids to those location names) so the two can never disagree."""
    return {
        city_id: name
        for city_id, (name, dlc) in CITIES.items()
        if dlc is None or getattr(options, DLC_OPTION_NAMES[dlc])
    }


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
        active_cities = _active_cities(self.options)
        city_names = [f"City Discovered: {name}" for name in active_cities.values()]
        dealer_names = [f"Dealer Unlocked: {name}" for name in active_cities.values()]
        active_names = (
            delivery_names + city_names + dealer_names + DISTANCE_LOCATIONS + XP_LOCATIONS
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
            "cities": _active_cities(self.options),
            "distance_milestones_km": DISTANCE_MILESTONES_KM,
            "xp_milestones": XP_MILESTONES,
            "money_item_values": MONEY_ITEM_VALUES,
            "xp_item_values": XP_ITEM_VALUES,
        }
