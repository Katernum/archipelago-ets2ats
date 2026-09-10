"""
Milestone 6: player options, per docs/game-design.md.

DLC toggles are reserved for when DLC-scoped city locations are added (see
docs/game-design.md, "Not yet built") -- they exist now so the option shape is stable, but
have no effect on location generation yet; only the small, empirically-confirmed base set of
cities in locations.py is used regardless of these settings.
"""

from __future__ import annotations

from dataclasses import dataclass

from Options import Choice, PerGameCommonOptions, Range, Toggle


class GoalType(Choice):
    """Which win condition applies to this world. All four reuse mechanisms already proven
    against the real game rather than needing new capability."""
    display_name = "Goal Type"
    option_flawless_long_haul = 0
    option_money_target = 1
    option_delivery_count = 2
    option_xp_amount = 3
    default = 0


class GoalDistanceKm(Range):
    """Minimum distance (km) a single delivery must cover to count toward the Flawless
    Long-Haul Delivery goal."""
    display_name = "Goal: Long-Haul Distance (km)"
    range_start = 200
    range_end = 3000
    default = 1200


class GoalMaxDamagePct(Range):
    """Maximum cargo damage percent (0-100) a delivery may have and still count as
    "flawless" for the Flawless Long-Haul Delivery goal."""
    display_name = "Goal: Max Cargo Damage %"
    range_start = 0
    range_end = 10
    default = 1


class GoalMoney(Range):
    """Bank balance required to complete the Money Target goal."""
    display_name = "Goal: Money Target"
    range_start = 10_000
    range_end = 10_000_000
    default = 1_000_000


class GoalDeliveryCount(Range):
    """Total deliveries required to complete the Delivery Count goal."""
    display_name = "Goal: Delivery Count"
    range_start = 5
    range_end = 200
    default = 25


class GoalXp(Range):
    """Total experience points required to complete the XP Amount goal."""
    display_name = "Goal: XP Amount"
    range_start = 500
    range_end = 100_000
    default = 5_000


class DeliveryLocationCount(Range):
    """How many Delivery #N locations to generate. Each corresponds to one real in-game
    delivery, detected live via telemetry."""
    display_name = "Delivery Location Count"
    range_start = 1
    range_end = 100
    default = 10


class DlcGoingEast(Toggle):
    """Reserved for future DLC-scoped city locations (Going East!). No effect yet."""
    display_name = "Owns: Going East!"


class DlcScandinavia(Toggle):
    """Reserved for future DLC-scoped city locations (Scandinavia). No effect yet."""
    display_name = "Owns: Scandinavia"


class DlcViveLaFrance(Toggle):
    """Reserved for future DLC-scoped city locations (Vive la France!). No effect yet."""
    display_name = "Owns: Vive la France!"


class DlcItalia(Toggle):
    """Reserved for future DLC-scoped city locations (Italia). No effect yet."""
    display_name = "Owns: Italia"


class DlcBeyondBaltic(Toggle):
    """Reserved for future DLC-scoped city locations (Beyond the Baltic Sea). No effect yet."""
    display_name = "Owns: Beyond the Baltic Sea"


class DlcRoadToBlackSea(Toggle):
    """Reserved for future DLC-scoped city locations (Road to the Black Sea). No effect yet."""
    display_name = "Owns: Road to the Black Sea"


class DlcWestBalkans(Toggle):
    """Reserved for future DLC-scoped city locations (West Balkans). No effect yet."""
    display_name = "Owns: West Balkans"


class DlcIberia(Toggle):
    """Reserved for future DLC-scoped city locations (Iberia). No effect yet."""
    display_name = "Owns: Iberia"


class DlcGreece(Toggle):
    """Reserved for future DLC-scoped city locations (Greece). No effect yet."""
    display_name = "Owns: Greece"


@dataclass
class Ets2AtsOptions(PerGameCommonOptions):
    goal_type: GoalType
    goal_distance_km: GoalDistanceKm
    goal_max_damage_pct: GoalMaxDamagePct
    goal_money: GoalMoney
    goal_delivery_count: GoalDeliveryCount
    goal_xp: GoalXp
    delivery_location_count: DeliveryLocationCount
    dlc_going_east: DlcGoingEast
    dlc_scandinavia: DlcScandinavia
    dlc_vive_la_france: DlcViveLaFrance
    dlc_italia: DlcItalia
    dlc_beyond_baltic: DlcBeyondBaltic
    dlc_road_to_black_sea: DlcRoadToBlackSea
    dlc_west_balkans: DlcWestBalkans
    dlc_iberia: DlcIberia
    dlc_greece: DlcGreece
