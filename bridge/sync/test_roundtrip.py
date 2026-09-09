"""
Milestone 1 verification: parse a real save, serialize it back unchanged and confirm
byte-identical output (proves the parser/writer loses no information), then edit one
field and confirm only that field's line changed.

Usage: py test_roundtrip.py <path-to-real-game.sii>  (the real, possibly-encrypted file)
"""

import sys
from pathlib import Path

import sii_crypto
import sii_format


def main() -> None:
    path = Path(sys.argv[1])
    raw = path.read_bytes()
    if sii_crypto.is_encrypted(raw):
        text = sii_crypto.decrypt(raw).decode("utf-8")
    else:
        text = raw.decode("utf-8")

    sii = sii_format.parse(text)
    print(f"Parsed {len(sii.units)} units.")

    # 1. Identity round trip: no edits, output must match input exactly.
    reserialized = sii_format.serialize(sii)
    if reserialized == text:
        print("PASS: identity round trip is byte-identical.")
    else:
        print("FAIL: identity round trip differs from original.")
        a, b = text.splitlines(), reserialized.splitlines()
        for i, (la, lb) in enumerate(zip(a, b)):
            if la != lb:
                print(f"  first difference at line {i + 1}:")
                print(f"    original:     {la!r}")
                print(f"    reserialized: {lb!r}")
                break
        else:
            print(f"  line count differs: original={len(a)} reserialized={len(b)}")
        sys.exit(1)

    # 2. Targeted edit: change money_account, confirm only that line differs.
    bank = sii.find_all("bank")
    if len(bank) != 1:
        print(f"FAIL: expected exactly 1 'bank' unit, found {len(bank)}.")
        sys.exit(1)
    bank_unit = bank[0]
    old_value = bank_unit.get("money_account")
    print(f"Current money_account: {old_value}")
    bank_unit.set("money_account", "777777")

    edited = sii_format.serialize(sii)
    a, b = text.splitlines(), edited.splitlines()
    diffs = [(i, la, lb) for i, (la, lb) in enumerate(zip(a, b)) if la != lb]
    if len(diffs) == 1 and "money_account: 777777" in diffs[0][2]:
        print(f"PASS: exactly one line changed (line {diffs[0][0] + 1}):")
        print(f"    before: {diffs[0][1]!r}")
        print(f"    after:  {diffs[0][2]!r}")
    else:
        print(f"FAIL: expected exactly 1 changed line, found {len(diffs)}.")
        for i, la, lb in diffs[:5]:
            print(f"    line {i + 1}: {la!r} -> {lb!r}")
        sys.exit(1)


if __name__ == "__main__":
    sys.exit(main())
