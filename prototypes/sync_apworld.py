"""
Dev helper: copy apworld/ets2ats/ (bridge/ included -- it lives inside the package now, see
docs/design-decisions.md) into a local Archipelago source checkout's worlds/ folder, for
testing against Generate.py/MultiServer.py. Not shipped -- end users get the packaged
.apworld, not this repo's dev layout.

Usage: py sync_apworld.py <path-to-Archipelago-checkout>
"""

import shutil
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
SOURCE = REPO_ROOT / "apworld" / "ets2ats"


def main() -> None:
    checkout = Path(sys.argv[1])
    dest = checkout / "worlds" / "ets2ats"
    if dest.exists():
        shutil.rmtree(dest)
    shutil.copytree(SOURCE, dest)
    print(f"Synced {SOURCE} -> {dest}")


if __name__ == "__main__":
    sys.exit(main())
