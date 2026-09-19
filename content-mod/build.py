"""
Milestone 7: package this folder into a .scs mod file. SCS's own mod format is just a plain,
UNCOMPRESSED zip archive renamed to .scs (confirmed via SCS's own official forum guide and
modding wiki -- a completely different, much simpler format than the HashFS v2 archives the
game's own shipped content uses, see docs/game-design.md).

Usage: py build.py [output_path]   (default: dist/archipelago_rewards.scs, next to this file)
"""

from __future__ import annotations

import sys
import zipfile
from pathlib import Path

MOD_ROOT = Path(__file__).parent
EXCLUDE = {"build.py", "dist", "__pycache__"}


def main() -> None:
    out_path = Path(sys.argv[1]) if len(sys.argv) > 1 else MOD_ROOT / "dist" / "archipelago_rewards.scs"
    out_path.parent.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(out_path, "w", zipfile.ZIP_STORED) as zf:
        for path in sorted(MOD_ROOT.rglob("*")):
            if path.is_dir() or path.relative_to(MOD_ROOT).parts[0] in EXCLUDE:
                continue
            zf.write(path, path.relative_to(MOD_ROOT).as_posix())

    print(f"Wrote {out_path}")


if __name__ == "__main__":
    sys.exit(main())
