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

# "Go out of your way" checks, per player request -- route variety and economic/flavor
# challenges built entirely on telemetry events already fully defined in shared_memory_map.py
# but never wired up until now (special_b.ferry/train/tollgate/refuelPayed/fined). Thresholds
# favor repeated/deliberate engagement over one-off incidental triggers: a single small fine
# happens to anyone, but a $2,000+ one implies a serious, deliberate violation; a single ferry
# crossing might just be on an assigned route, but 4 *different* ferry routes means actively
# seeking them out (ferry/train telemetry carries named source/target fields, so distinct
# routes -- not just repeat counts -- can be tracked as a set). Fuel is tracked by volume
# (liters), not cost -- the struct's only refuel field (`refuelAmount`) is a quantity, unlike
# the other payment events which carry an explicit *PayAmount; there's no refuel-cost field to
# read, so "spend $X on fuel" was never actually buildable and would have misrepresented what
# telemetry provides.
TOLLGATE_MILESTONES = [10, 50, 150]
REFUEL_COUNT_MILESTONES = [10, 50, 150]
FUEL_VOLUME_MILESTONES = [1_000, 5_000]
FERRY_ROUTE_MILESTONES = [2, 4]
TRAIN_ROUTE_MILESTONES = [2, 4]
MAJOR_FINE_THRESHOLD = 2_000
FERRY_ONEOFF_LOCATION = "Take a Ferry"
TRAIN_ONEOFF_LOCATION = "Take a Train"
MAJOR_FINE_LOCATION = "Get a Major Fine"

# Cheeky rolling-window challenges, per player request. Fine offence type confirmed against
# SCS's own SDK header (scssdk_telemetry_common_gameplay_events.h) -- "speeding" and
# "speeding_camera" are both real, documented fine_offence values (others include crash,
# wrong_way, red_signal, etc.), not guessed. Damage uses chassis/cabin wear specifically
# (not engine/transmission, which accumulate from normal use and overheating, not collisions)
# since those are the two components that actually spike from a crash.
SPEEDING_OFFENCE_TYPES = {"speeding", "speeding_camera"}
SPEEDING_SPREE_COUNT = 5
SPEEDING_SPREE_WINDOW_SECONDS = 60.0
SPEEDING_SPREE_LOCATION = "5 Speeding Fines in 1 Minute"
SUDDEN_DAMAGE_THRESHOLD = 0.5
SUDDEN_DAMAGE_WINDOW_SECONDS = 30.0
SUDDEN_DAMAGE_LOCATION = "50% Damage in 30 Seconds"

VICTORY_LOCATION = "Victory"

DELIVERY_LOCATIONS = [f"Delivery #{n}" for n in range(1, MAX_DELIVERY_LOCATIONS + 1)]
# Sorted by city id (not display name) so the generated ID table has a stable, reviewable order.
CITY_DISCOVERED_LOCATIONS = [f"City Discovered: {name}" for _id, (name, _dlc) in sorted(CITIES.items())]
DEALER_UNLOCKED_LOCATIONS = [f"Dealer Unlocked: {name}" for _id, (name, _dlc) in sorted(CITIES.items())]
DISTANCE_LOCATIONS = [f"Drive {km:,} km" for km in DISTANCE_MILESTONES_KM]
XP_LOCATIONS = [f"Earn {xp:,} XP" for xp in XP_MILESTONES]
TOLLGATE_LOCATIONS = [f"Cross {n} Tollgates" for n in TOLLGATE_MILESTONES]
REFUEL_COUNT_LOCATIONS = [f"Refuel {n} Times" for n in REFUEL_COUNT_MILESTONES]
FUEL_VOLUME_LOCATIONS = [f"Refuel {liters:,} Liters Total" for liters in FUEL_VOLUME_MILESTONES]
FERRY_ROUTE_LOCATIONS = [f"{n} Different Ferry Routes" for n in FERRY_ROUTE_MILESTONES]
TRAIN_ROUTE_LOCATIONS = [f"{n} Different Train Routes" for n in TRAIN_ROUTE_MILESTONES]

ALL_LOCATIONS = (
    DELIVERY_LOCATIONS + CITY_DISCOVERED_LOCATIONS + DEALER_UNLOCKED_LOCATIONS
    + DISTANCE_LOCATIONS + XP_LOCATIONS
    + [FERRY_ONEOFF_LOCATION, TRAIN_ONEOFF_LOCATION, MAJOR_FINE_LOCATION,
       SPEEDING_SPREE_LOCATION, SUDDEN_DAMAGE_LOCATION]
    + TOLLGATE_LOCATIONS + REFUEL_COUNT_LOCATIONS + FUEL_VOLUME_LOCATIONS
    + FERRY_ROUTE_LOCATIONS + TRAIN_ROUTE_LOCATIONS
)
# Victory is a pure event location (address=None), not a networked location -- it must NOT be
# in this ID table. Its locked event item (code=None) requires the location's own address to
# also be None (Main.py's write_multidata enforces this pairing), matching how e.g. the
# `adventure` world's own "Chalice Home" final location is defined.

LOCATION_NAME_TO_ID = {name: i + 1 for i, name in enumerate(ALL_LOCATIONS)}


class Ets2AtsLocation(Location):
    game = GAME_NAME
