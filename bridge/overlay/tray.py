"""
Milestone 5: system tray icon -- the entry point for opening the dashboard, syncing on
demand, and quitting. pystray's `Icon.run()` is blocking, so it owns its own dedicated
thread; every menu action just forwards to a callback rather than touching UI state
directly, since only the Tk thread may touch Tk widgets (see ui.py).
"""

from __future__ import annotations

import threading
from typing import Callable

import pystray
from PIL import Image, ImageDraw


def _make_icon_image() -> Image.Image:
    img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.ellipse((4, 4, 60, 60), fill=(220, 140, 20, 255))
    draw.text((18, 22), "AP", fill=(30, 20, 0, 255))
    return img


def start_tray(on_open_dashboard: Callable[[], None], on_sync_now: Callable[[], None],
               on_quit: Callable[[], None]) -> pystray.Icon:
    menu = pystray.Menu(
        pystray.MenuItem("Open Dashboard", lambda icon, item: on_open_dashboard(), default=True),
        pystray.MenuItem("Sync Now", lambda icon, item: on_sync_now()),
        pystray.MenuItem("Quit", lambda icon, item: on_quit()),
    )
    icon = pystray.Icon("ets2ats_ap", _make_icon_image(), "ETS2ATS Archipelago", menu)
    threading.Thread(target=icon.run, name="tray-icon", daemon=True).start()
    return icon
