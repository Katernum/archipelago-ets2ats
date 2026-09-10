"""
Dev helper: copy apworld/ets2ats/ into a local Archipelago source checkout's worlds/
folder, for testing against Generate.py/MultiServer.py. Not shipped -- end users get the
packaged .apworld, not this repo's dev layout.

Also drops a `_dev_repo_root.txt` marker into the copied world folder recording this repo's
absolute path, which apworld/ets2ats/__init__.py reads to put `bridge/` on sys.path for its
Launcher component's `launch_client`. This only exists to make the dev loop work while
apworld/ and bridge/ are separate folders -- a real packaged .apworld would need bridge/'s
code bundled inside it instead (see docs/design-decisions.md), so this marker is deliberately
dev-only and never written into this repo's own apworld/ets2ats/ source.

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
    (dest / "_dev_repo_root.txt").write_text(str(REPO_ROOT))
    print(f"Synced {SOURCE} -> {dest}")


if __name__ == "__main__":
    sys.exit(main())
