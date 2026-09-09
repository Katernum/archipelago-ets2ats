"""
Milestone 4: apply queued Archipelago money items to a live ETS2/ATS save file.

Uses the Milestone 0/1-proven round trip: read the save (decrypting it first if it's still
a ScsC container), parse it losslessly, add the pending amount to the `bank` unit's
money_account field, and write the result back as plain SiiNunit text -- no re-encryption
needed, since the game accepts a plain-text save directly (see docs/design-decisions.md,
Milestone 0).

This must only be run while the game is at the main menu, not mid-session -- a live
gameplay session holds its own in-memory copy of save state and will overwrite an external
edit on its next autosave (see docs/design-decisions.md, Milestone 0).
"""

from __future__ import annotations

import shutil
import time
from pathlib import Path

from . import sii_crypto, sii_format


def apply_money_delta(save_path: Path, delta: int) -> tuple[int, int]:
    """Add `delta` to the save's bank.money_account. Returns (old_balance, new_balance)."""
    raw = save_path.read_bytes()
    text = (sii_crypto.decrypt(raw) if sii_crypto.is_encrypted(raw) else raw).decode("utf-8")

    sii = sii_format.parse(text)
    banks = sii.find_all("bank")
    if len(banks) != 1:
        raise ValueError(f"Expected exactly 1 'bank' unit in save, found {len(banks)}")
    bank = banks[0]

    old_balance = int(bank.get("money_account"))
    new_balance = old_balance + delta
    bank.set("money_account", str(new_balance))

    backup = save_path.with_suffix(save_path.suffix + f".pre-ap-sync-{int(time.time())}")
    shutil.copy2(save_path, backup)

    save_path.write_bytes(sii_format.serialize(sii).encode("utf-8"))
    return old_balance, new_balance
