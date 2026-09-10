"""
Milestone 6 spike: test whether appending a city name to economy.player.unlocked_dealers
actually unlocks a truck dealer in that city, as a candidate mechanism for a real "unlock
a dealer" AP item. Throwaway script, not shipped -- mirrors milestone0_apply_test_edit.py's
approach (backup, decrypt if needed, edit, write plain text).

Usage: py milestone6_dealer_unlock_test.py <path-to-game.sii> <city_id>
"""

import shutil
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from bridge.sync import sii_crypto, sii_format


def main() -> None:
    path = Path(sys.argv[1])
    city_id = sys.argv[2]

    raw = path.read_bytes()
    text = (sii_crypto.decrypt(raw) if sii_crypto.is_encrypted(raw) else raw).decode("utf-8")
    sii = sii_format.parse(text)

    # unlocked_dealers lives directly on the `economy` unit itself -- NOT on the unit that
    # economy's own `player` field references (a different, confusingly-similarly-named
    # thing: a unit of type `player` holding vehicle/HQ/driving-time state).
    econ = sii.find_all("economy")[0]

    count = int(econ.get("unlocked_dealers"))
    existing = [econ.get(f"unlocked_dealers[{i}]") for i in range(count)]
    if city_id in existing:
        print(f"{city_id!r} is already in unlocked_dealers ({existing}) -- nothing to test.")
        return

    econ.set("unlocked_dealers", str(count + 1))
    # Insert right after the last existing array element (or the count field, if the array
    # was empty) rather than at the end of the whole unit -- keeps the file's structure close
    # to what the game itself would write, rather than relying on the parser being fully
    # position-independent for something we haven't tested (only scalar edits, so far).
    insert_after_key = f"unlocked_dealers[{count - 1}]" if count > 0 else "unlocked_dealers"
    insert_idx = next(i for i, (k, _v) in enumerate(econ.fields) if k == insert_after_key) + 1
    econ.fields.insert(insert_idx, (f"unlocked_dealers[{count}]", city_id))
    print(f"unlocked_dealers: {existing} -> {existing + [city_id]}")

    backup = path.with_suffix(path.suffix + f".pre-m6-spike-{int(time.time())}")
    shutil.copy2(path, backup)
    print(f"Backup: {backup}")

    path.write_bytes(sii_format.serialize(sii).encode("utf-8"))
    print(f"Wrote edited save to {path}")
    print("\nNow load this profile (no restart needed if the game isn't already mid-session) "
          f"and check whether {city_id} shows a truck dealer.")


if __name__ == "__main__":
    sys.exit(main())
