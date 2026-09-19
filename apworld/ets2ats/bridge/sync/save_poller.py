"""
Milestone 6: read the tracked fields a save-file poller needs -- city discovery, dealer
unlocks, money, and XP -- none of which have a live telemetry equivalent (see
docs/game-design.md). This is read-only, so unlike Sync (bridge/sync/apply_items.py) it does
NOT need the main-menu precondition or a confirmation prompt: reading the wrong profile's
save by mistake just misattributes a discovery to the wrong session, it can't corrupt
anything. The caller (client.py's save_poller task) decides which file to point this at.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from . import sii_crypto, sii_format


@dataclass
class TrackedFields:
    money: int
    xp: int
    visited_cities: set[str]
    unlocked_dealers: set[str]


def _array_values(unit: sii_format.SiiUnit, key: str) -> set[str]:
    count = unit.get(key)
    if count is None:
        return set()
    return {unit.get(f"{key}[{i}]") for i in range(int(count))}


def read_tracked_fields(save_path: Path) -> TrackedFields:
    raw = save_path.read_bytes()
    text = (sii_crypto.decrypt(raw) if sii_crypto.is_encrypted(raw) else raw).decode("utf-8")
    sii = sii_format.parse(text)

    banks = sii.find_all("bank")
    if len(banks) != 1:
        raise ValueError(f"Expected exactly 1 'bank' unit in save, found {len(banks)}")

    economies = sii.find_all("economy")
    if len(economies) != 1:
        raise ValueError(f"Expected exactly 1 'economy' unit in save, found {len(economies)}")
    economy = economies[0]

    return TrackedFields(
        money=int(banks[0].get("money_account")),
        xp=int(economy.get("experience_points")),
        visited_cities=_array_values(economy, "visited_cities"),
        unlocked_dealers=_array_values(economy, "unlocked_dealers"),
    )
