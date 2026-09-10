"""
Milestone 6: access rules. Currently just the completion condition -- no location in this
world requires an item to reach yet (see docs/game-design.md's decision to keep dealer-unlock
a location, not an access-gating item, at least for this pass). The goal TYPE (which of the
four conditions in options.py applies) doesn't change this rule; it only changes when the
bridge client decides the Victory location is satisfied and sends the check for it.
"""

from __future__ import annotations

from worlds.AutoWorld import World


def set_rules(world: World) -> None:
    world.multiworld.completion_condition[world.player] = (
        lambda state: state.has("Victory", world.player)
    )
