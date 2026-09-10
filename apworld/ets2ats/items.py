"""
Milestone 6: items, per docs/game-design.md. All apply to a real save via
bridge/sync/apply_items.py -- Money Bundle and the Fine trap both edit bank.money_account
(the trap is just a negative delta, same mechanism), XP Grant edits
economy.experience_points the same way.

Victory is an event item (code=None) placed on the always-reachable Victory location by
Ets2AtsWorld.create_regions -- never sent over the network, just how AutoWorld tracks that
this player's goal condition is satisfied (see rules.py).
"""

from __future__ import annotations

from BaseClasses import Item, ItemClassification

GAME_NAME = "ETS2ATS"

# name -> money delta (negative for traps)
MONEY_ITEM_VALUES = {
    "10,000 Bundle": 10_000,
    "25,000 Bundle": 25_000,
    "50,000 Bundle": 50_000,
    "Minor Fine (Trap)": -2_000,
    "Major Fine (Trap)": -8_000,
}

# name -> XP delta
XP_ITEM_VALUES = {
    "500 XP Grant": 500,
    "1,500 XP Grant": 1_500,
    "3,000 XP Grant": 3_000,
}

ITEM_NAME_TO_ID = {
    name: i + 1
    for i, name in enumerate(list(MONEY_ITEM_VALUES) + list(XP_ITEM_VALUES))
}

ITEM_CLASSIFICATIONS = {
    **{name: ItemClassification.trap if "Trap" in name else ItemClassification.filler
       for name in MONEY_ITEM_VALUES},
    **{name: ItemClassification.filler for name in XP_ITEM_VALUES},
}

# Default filler pool weights: fewer traps than rewards, matching a typical AP filler mix.
FILLER_WEIGHTS = {
    "10,000 Bundle": 4,
    "25,000 Bundle": 3,
    "50,000 Bundle": 2,
    "500 XP Grant": 4,
    "1,500 XP Grant": 3,
    "3,000 XP Grant": 2,
    "Minor Fine (Trap)": 2,
    "Major Fine (Trap)": 1,
}


class Ets2AtsItem(Item):
    game = GAME_NAME
