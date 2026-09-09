"""
Milestone 0 spike: is it safe to edit the save file while the game is running but
backed out to the main menu (profile unloaded), instead of requiring a full process close?

Not shipped code -- throwaway tooling for a single yes/no/partial answer, to be recorded
in docs/design-decisions.md.

Usage:
  py milestone0_main_menu_test.py find <profile_dir>
      Locate the most recently modified game.sii under a profile's save/ tree.

  py milestone0_main_menu_test.py inspect <path-to-game.sii>
      Report: text or binary/encrypted format, whether the file is currently lockable
      for writing (proves/disproves "OS handle held for process lifetime"), and print
      any lines that look like economy/progression fields (candidates for the patch step).

  py milestone0_main_menu_test.py patch <path-to-game.sii> --find TEXT --replace TEXT
      Make a single, exact text substitution (after taking a timestamped backup) so we
      have a distinctive, easily-verified change to look for in-game after hitting
      Continue without restarting the process.
"""

import argparse
import shutil
import sys
import time
from pathlib import Path

ECONOMY_KEYWORDS = (
    "money", "bank", "experience", "xp_", "cash", "adblue_fine", "fine",
    "skill_", "employ", "loan",
)


def find_latest_save(profile_dir: Path) -> None:
    save_root = profile_dir / "save"
    if not save_root.is_dir():
        print(f"No save/ directory under {profile_dir}")
        return
    candidates = sorted(
        save_root.glob("*/game.sii"), key=lambda p: p.stat().st_mtime, reverse=True
    )
    if not candidates:
        print(f"No game.sii files found under {save_root}")
        return
    for path in candidates[:10]:
        mtime = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(path.stat().st_mtime))
        print(f"{mtime}  {path}")
    print(f"\nMost recent: {candidates[0]}")


def inspect(path: Path) -> None:
    if not path.is_file():
        print(f"Not found: {path}")
        return

    with open(path, "rb") as f:
        header = f.read(16)

    is_text = header.startswith(b"SiiNunit")
    print(f"Format: {'plain text (SiiNunit)' if is_text else 'binary/encrypted'}  "
          f"(header bytes: {header[:8]!r})")
    if not is_text:
        print("Not text format -- g_save_format may not have applied to this slot yet "
              "(only affects saves written after the setting changed). Trigger a fresh "
              "save in-game (manual save or autosave) and re-run inspect on the new file.")

    # Lock test: try to open for read+write without truncating.
    try:
        with open(path, "r+b"):
            pass
        print("Lock test: WRITABLE -- no exclusive OS lock held by the game process "
              "right now.")
    except PermissionError as exc:
        print(f"Lock test: LOCKED -- {exc}")
        print("This alone would answer Milestone 0 with 'no, main menu isn't enough' "
              "if the game is currently at the main menu with this profile's save loaded.")
        return

    if is_text:
        text = path.read_text(encoding="utf-8", errors="replace")
        print("\nCandidate economy/progression lines (grep by keyword, not confirmed field names):")
        hits = 0
        for lineno, line in enumerate(text.splitlines(), start=1):
            lowered = line.lower()
            if any(kw in lowered for kw in ECONOMY_KEYWORDS):
                print(f"  {lineno}: {line.strip()}")
                hits += 1
        if not hits:
            print("  (none matched -- keyword list may need adjusting once we see real field names)")


def patch(path: Path, find: str, replace: str) -> None:
    if not path.is_file():
        print(f"Not found: {path}")
        return
    text = path.read_text(encoding="utf-8", errors="replace")
    count = text.count(find)
    if count == 0:
        print(f"'{find}' not found in {path} -- nothing changed.")
        return
    if count > 1:
        print(f"'{find}' appears {count} times -- refusing to patch ambiguously. "
              "Narrow the --find string to a full, unique line.")
        return

    backup = path.with_suffix(path.suffix + f".bak-{int(time.time())}")
    shutil.copy2(path, backup)
    print(f"Backup written: {backup}")

    try:
        with open(path, "r+", encoding="utf-8") as f:
            pass  # re-confirm writability right before the real write
    except PermissionError as exc:
        print(f"Lock test failed at patch time: {exc}")
        return

    path.write_text(text.replace(find, replace), encoding="utf-8")
    print(f"Patched. Replaced:\n  {find}\nwith:\n  {replace}")
    print("\nNow, WITHOUT restarting the game process, click Continue on this profile "
          "in-game and check whether the change took effect.")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    p_find = sub.add_parser("find", help="locate the most recently modified game.sii")
    p_find.add_argument("profile_dir", type=Path)

    p_inspect = sub.add_parser("inspect", help="check format + lock status + candidate fields")
    p_inspect.add_argument("path", type=Path)

    p_patch = sub.add_parser("patch", help="make one exact, backed-up text substitution")
    p_patch.add_argument("path", type=Path)
    p_patch.add_argument("--find", required=True)
    p_patch.add_argument("--replace", required=True)

    args = parser.parse_args()
    if args.command == "find":
        find_latest_save(args.profile_dir)
    elif args.command == "inspect":
        inspect(args.path)
    elif args.command == "patch":
        patch(args.path, args.find, args.replace)


if __name__ == "__main__":
    sys.exit(main())
