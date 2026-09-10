"""
Milestone 5: locate a profile's live save file on disk, so syncing needs no manual path
entry. Realizes the very first architecture idea raised for this whole project -- match the
AP slot name to the ETS2/ATS profile name, dedicated to the run.

Profile folders are named as the uppercase hex encoding of the profile's UTF-8 display name
(confirmed empirically against real profiles: "Mod Test" -> "4D6F642054657374").
"""

from __future__ import annotations

from pathlib import Path

GAME_DOCUMENTS_FOLDER = {
    "ets2": "Euro Truck Simulator 2",
    "ats": "American Truck Simulator",
}


def profile_folder_name(profile_display_name: str) -> str:
    return profile_display_name.encode("utf-8").hex().upper()


def _documents_dir() -> Path:
    return Path.home() / "Documents"


def _newest_save(save_root: Path) -> Path | None:
    candidates = list(save_root.glob("**/game.sii"))
    if not candidates:
        return None
    return max(candidates, key=lambda p: p.stat().st_mtime)


def find_profile_save(game: str, profile_name: str) -> Path | None:
    """Newest save for the profile whose name matches `profile_name` exactly, or None."""
    documents = GAME_DOCUMENTS_FOLDER.get(game)
    if documents is None or not profile_name:
        return None
    save_root = _documents_dir() / documents / "profiles" / profile_folder_name(profile_name) / "save"
    if not save_root.is_dir():
        return None
    return _newest_save(save_root)


def find_any_recent_save(game: str) -> Path | None:
    """Fallback: newest save across ALL profiles for this game, regardless of name match."""
    documents = GAME_DOCUMENTS_FOLDER.get(game)
    if documents is None:
        return None
    profiles_root = _documents_dir() / documents / "profiles"
    if not profiles_root.is_dir():
        return None

    newest: Path | None = None
    for profile_dir in profiles_root.iterdir():
        candidate = _newest_save(profile_dir / "save")
        if candidate is not None and (newest is None or candidate.stat().st_mtime > newest.stat().st_mtime):
            newest = candidate
    return newest
