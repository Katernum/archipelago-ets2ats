"""
Milestone 6: locations, per docs/game-design.md.

The ID map below is the full static universe this world could ever generate across any
option combination -- Archipelago requires location_name_to_id to be stable regardless of a
specific seed's options, so `Ets2AtsWorld.create_regions` only adds a SUBSET of these (e.g.
"Delivery #1".."Delivery #{delivery_location_count}", or only base-game cities for a player
with no DLC options enabled) rather than changing the ID map itself.

City-based locations now cover all 341 real cities (base game + all 9 map DLCs), pulled
directly from the game's own archives via sk-zk/Extractor rather than guessed from community
sources -- see city_data.py and docs/game-design.md for how this was extracted and verified.
Every city gets a static id here regardless of DLC ownership (same reasoning as
delivery_location_count above); `create_regions` decides which are actually reachable for a
given seed based on the DLC toggle options.
"""

from __future__ import annotations

from BaseClasses import Location

from .city_data import CITIES

GAME_NAME = "ETS2ATS"

MAX_DELIVERY_LOCATIONS = 100

DISTANCE_MILESTONES_KM = [500, 1_500, 3_000]
XP_MILESTONES = [1_000, 5_000, 15_000]

VICTORY_LOCATION = "Victory"

DELIVERY_LOCATIONS = [f"Delivery #{n}" for n in range(1, MAX_DELIVERY_LOCATIONS + 1)]
# Sorted by city id (not display name) so the generated ID table has a stable, reviewable order.
CITY_DISCOVERED_LOCATIONS = [f"City Discovered: {name}" for _id, (name, _dlc) in sorted(CITIES.items())]
DEALER_UNLOCKED_LOCATIONS = [f"Dealer Unlocked: {name}" for _id, (name, _dlc) in sorted(CITIES.items())]
DISTANCE_LOCATIONS = [f"Drive {km:,} km" for km in DISTANCE_MILESTONES_KM]
XP_LOCATIONS = [f"Earn {xp:,} XP" for xp in XP_MILESTONES]

ALL_LOCATIONS = (
    DELIVERY_LOCATIONS + CITY_DISCOVERED_LOCATIONS + DEALER_UNLOCKED_LOCATIONS
    + DISTANCE_LOCATIONS + XP_LOCATIONS
)
# Victory is a pure event location (address=None), not a networked location -- it must NOT be
# in this ID table. Its locked event item (code=None) requires the location's own address to
# also be None (Main.py's write_multidata enforces this pairing), matching how e.g. the
# `adventure` world's own "Chalice Home" final location is defined.

LOCATION_NAME_TO_ID = {name: i + 1 for i, name in enumerate(ALL_LOCATIONS)}


class Ets2AtsLocation(Location):
    game = GAME_NAME
