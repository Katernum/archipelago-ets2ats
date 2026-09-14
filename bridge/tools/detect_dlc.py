"""
Milestone 6 follow-up: detect which ETS2 map DLCs are installed by checking for their known
.scs files, and write the corresponding dlc_* option values into a player's YAML.

`Generate.py` only ever reads a static YAML file, and may run on a machine other than the
player's own (a host generating for the whole group, or the website's generator) -- so the
apworld itself can't auto-detect installed DLC at generation time. This is the practical
equivalent: the player runs it once, on their own machine, before generating.

File-to-DLC mapping confirmed directly against a real installation (see docs/game-design.md)
-- not guessed from documentation. Deliberately doesn't import apworld/ets2ats/city_data.py's
DLC_OPTION_NAMES (which would require a full Archipelago checkout on PYTHONPATH just to run a
file-existence check) -- the dlc key set below must be kept in sync with that module by hand.

Usage: py detect_dlc.py <path-to-ETS2-install> <path-to-player.yaml>
"""

from __future__ import annotations

import sys
from pathlib import Path

import yaml

GAME_NAME = "ETS2ATS"

# dlc key (must match apworld/ets2ats/city_data.py's DLC_OPTION_NAMES) -> known .scs filename
DLC_FILES = {
    "going_east": "dlc_east.scs",
    "scandinavia": "dlc_north.scs",
    "vive_la_france": "dlc_fr.scs",
    "italia": "dlc_it.scs",
    "beyond_baltic": "dlc_balt.scs",
    "road_to_black_sea": "dlc_balkan_e.scs",
    "west_balkans": "dlc_balkan_w.scs",
    "iberia": "dlc_iberia.scs",
    "greece": "dlc_greece.scs",
}


def detect(install_dir: Path) -> dict[str, bool]:
    return {key: (install_dir / filename).exists() for key, filename in DLC_FILES.items()}


def main() -> None:
    install_dir = Path(sys.argv[1])
    yaml_path = Path(sys.argv[2])

    detected = detect(install_dir)

    doc = yaml.safe_load(yaml_path.read_text()) or {}
    game_block = doc.setdefault(GAME_NAME, {})
    for key, owned in detected.items():
        game_block[f"dlc_{key}"] = owned

    yaml_path.write_text(yaml.safe_dump(doc, sort_keys=False))

    owned_names = [key for key, owned in detected.items() if owned] or ["(none)"]
    print(f"Detected DLCs: {', '.join(owned_names)}")
    print(f"Updated {yaml_path}")


if __name__ == "__main__":
    sys.exit(main())
