"""
Milestone 6: apply queued Archipelago items to a live ETS2/ATS save file. Extends the
Milestone 4 money-only version to also grant XP, in one read-modify-write pass covering
whichever fields have a non-zero pending delta.

Uses the Milestone 0/1-proven round trip: read the save (decrypting it first if it's still
a ScsC container), parse it losslessly, add the pending amount(s) to the relevant field(s),
and write the result back as plain SiiNunit text -- no re-encryption needed, since the game
accepts a plain-text save directly (see docs/design-decisions.md, Milestone 0).

This must only be run while the game is at the main menu, not mid-session -- a live
gameplay session holds its own in-memory copy of save state and will overwrite an external
edit on its next autosave (see docs/design-decisions.md, Milestone 0).
"""

from __future__ import annotations

import shutil
import time
from pathlib import Path

from . import sii_crypto, sii_format


def apply_deltas(save_path: Path, *, money_delta: int = 0, xp_delta: int = 0) -> dict[str, tuple[int, int]]:
    """Add money_delta to bank.money_account and/or xp_delta to economy.experience_points.
    Returns {"money": (old, new), "xp": (old, new)} for whichever deltas were non-zero; a
    zero delta is skipped entirely rather than touching a field with no pending change."""
    raw = save_path.read_bytes()
    text = (sii_crypto.decrypt(raw) if sii_crypto.is_encrypted(raw) else raw).decode("utf-8")
    sii = sii_format.parse(text)

    results: dict[str, tuple[int, int]] = {}

    if money_delta:
        banks = sii.find_all("bank")
        if len(banks) != 1:
            raise ValueError(f"Expected exactly 1 'bank' unit in save, found {len(banks)}")
        bank = banks[0]
        old_money = int(bank.get("money_account"))
        new_money = old_money + money_delta
        bank.set("money_account", str(new_money))
        results["money"] = (old_money, new_money)

    if xp_delta:
        # experience_points lives directly on the `economy` unit -- NOT on the unit that
        # economy's own `player` field references (a different, confusingly similarly-named
        # unit of type `player`). See docs/game-design.md's spike-test note.
        economies = sii.find_all("economy")
        if len(economies) != 1:
            raise ValueError(f"Expected exactly 1 'economy' unit in save, found {len(economies)}")
        economy = economies[0]
        old_xp = int(economy.get("experience_points"))
        new_xp = old_xp + xp_delta
        economy.set("experience_points", str(new_xp))
        results["xp"] = (old_xp, new_xp)

    if not results:
        return results

    backup = save_path.with_suffix(save_path.suffix + f".pre-ap-sync-{int(time.time())}")
    shutil.copy2(save_path, backup)
    save_path.write_bytes(sii_format.serialize(sii).encode("utf-8"))
    return results
