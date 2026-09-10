"""
Milestone 6: locations, per docs/game-design.md.

The ID map below is the full static universe this world could ever generate across any
option combination -- Archipelago requires location_name_to_id to be stable regardless of a
specific seed's options, so `Ets2AtsWorld.create_regions` only adds a SUBSET of these (e.g.
"Delivery #1".."Delivery #{delivery_location_count}") rather than changing the ID map itself.

City-based locations are deliberately a small, empirically-confirmed starter set (Kassel,
Hannover, Frankfurt, Nurnberg -- the exact city id strings confirmed present in a real save's
economy.visited_cities/unlocked_dealers, see docs/game-design.md) rather than a full base-game
or DLC city catalog. Guessing at additional city id strings risks a silent mismatch (the
game's internal ids don't always match the obvious English spelling), so expanding this list
is left as real data-entry work for later, not attempted here.
"""

from __future__ import annotations

from BaseClasses import Location

GAME_NAME = "ETS2ATS"

MAX_DELIVERY_LOCATIONS = 100

# (city id as used in economy.visited_cities/unlocked_dealers, display name)
STARTER_CITIES = [
    ("kassel", "Kassel"),
    ("hannover", "Hannover"),
    ("frankfurt", "Frankfurt"),
    ("nurnberg", "Nurnberg"),
]

DISTANCE_MILESTONES_KM = [500, 1_500, 3_000]
XP_MILESTONES = [1_000, 5_000, 15_000]

VICTORY_LOCATION = "Victory"

DELIVERY_LOCATIONS = [f"Delivery #{n}" for n in range(1, MAX_DELIVERY_LOCATIONS + 1)]
CITY_DISCOVERED_LOCATIONS = [f"City Discovered: {name}" for _id, name in STARTER_CITIES]
DEALER_UNLOCKED_LOCATIONS = [f"Dealer Unlocked: {name}" for _id, name in STARTER_CITIES]
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
