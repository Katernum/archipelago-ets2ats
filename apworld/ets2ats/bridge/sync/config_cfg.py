"""
Milestone 6 follow-up: read/write SCS's `config.cfg` cvar file. Distinct from the SII save
format (bridge/sync/sii_format.py) -- config.cfg is a flat, order-independent list of
`uset <key> "<value>"` lines (confirmed CRLF throughout on a real installation), not a
nested unit structure, so no array-index/positional-fidelity concerns apply here the way they
do for SII edits.

Unlike a save file, config.cfg is installation-wide, not per-profile -- a cvar set here
affects every profile on this game installation, not just one dedicated to an AP run. Used
here to set `g_exp_gain` near zero, suppressing natural XP gain so AP's XP Grant items (a
separate, raw edit to a save's experience_points field, unaffected by this multiplier) become
the dominant leveling path instead of a bonus on top of normal play.
"""

from __future__ import annotations

import re
import shutil
import time
from pathlib import Path

_CVAR_LINE = re.compile(r'^uset (\S+) "(.*)"$')  # splitlines() already strips \r\n/\n


def get_cvar(config_path: Path, key: str) -> str | None:
    for line in config_path.read_text(encoding="utf-8").splitlines():
        match = _CVAR_LINE.match(line)
        if match and match.group(1) == key:
            return match.group(2)
    return None


def set_cvar(config_path: Path, key: str, value: str) -> str | None:
    """Set `uset <key> "<value>"`, replacing an existing line for that key or appending a new
    one (cvar order has no semantic meaning in this format). Returns the previous value, or
    None if the cvar wasn't already set."""
    lines = config_path.read_text(encoding="utf-8").splitlines()
    old_value: str | None = None
    replaced = False

    for i, line in enumerate(lines):
        match = _CVAR_LINE.match(line)
        if match and match.group(1) == key:
            old_value = match.group(2)
            lines[i] = f'uset {key} "{value}"'
            replaced = True
            break

    if not replaced:
        lines.append(f'uset {key} "{value}"')

    backup = config_path.with_suffix(config_path.suffix + f".pre-ap-edit-{int(time.time())}")
    shutil.copy2(config_path, backup)

    config_path.write_text("\r\n".join(lines) + "\r\n", encoding="utf-8")
    return old_value
