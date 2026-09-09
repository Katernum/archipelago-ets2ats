"""
Milestone 0, step 2: decrypt the live save, bump money_account to a distinctive value,
and write the result back as PLAIN TEXT (no re-encryption) -- testing whether the game's
loader accepts a raw SiiN-format save directly, and whether it's picked up via Continue
without restarting the process.

Usage: py milestone0_apply_test_edit.py <path-to-game.sii> <new_money_value>
"""

import shutil
import sys
import time
from pathlib import Path

import sii_crypto


def main() -> None:
    path = Path(sys.argv[1])
    new_value = sys.argv[2]

    raw = path.read_bytes()
    if not sii_crypto.is_encrypted(raw):
        print("File is not ScsC-encrypted -- unexpected, aborting.")
        return

    plain = sii_crypto.decrypt(raw)
    text = plain.decode("utf-8")

    old_line_start = "money_account: "
    lines = text.splitlines(keepends=True)
    changed = 0
    for i, line in enumerate(lines):
        if line.strip().startswith(old_line_start):
            stripped = line.rstrip("\r\n")
            newline = line[len(stripped):]
            lines[i] = f" money_account: {new_value}{newline}"
            changed += 1
    if changed != 1:
        print(f"Expected exactly 1 money_account line, found {changed} -- aborting.")
        return

    backup = path.with_suffix(path.suffix + f".orig-encrypted-{int(time.time())}")
    shutil.copy2(path, backup)
    print(f"Backup of original encrypted save: {backup}")

    new_text = "".join(lines)
    path.write_bytes(new_text.encode("utf-8"))
    print(f"Wrote plain-text save with money_account: {new_value} to {path}")
    print("\nNow, WITHOUT restarting the game process, click Continue on this profile "
          "and report what your bank balance shows.")


if __name__ == "__main__":
    sys.exit(main())
