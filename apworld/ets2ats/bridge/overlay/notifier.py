"""
Milestone 5: transparent, click-through, always-on-top corner window for live check/item
notifications.

This is a plain win32 layered+transparent window (WS_EX_LAYERED | WS_EX_TRANSPARENT), not a
DirectX-hooked overlay -- it sits on top of the game via the desktop compositor, with no
process injection. See docs/design-decisions.md ("Milestone roadmap update") for why this
was chosen over OS toasts (suppressed by Focus Assist/Game Mode during play) and over a real
render-hooked overlay (a separate, much larger effort). Requires the game to run in
Borderless Windowed mode -- invisible in exclusive Fullscreen, where the desktop compositor
is bypassed entirely.
"""

from __future__ import annotations

import ctypes
import tkinter as tk

GWL_EXSTYLE = -20
WS_EX_LAYERED = 0x00080000
WS_EX_TRANSPARENT = 0x00000020
WS_EX_TOOLWINDOW = 0x00000080

DISPLAY_MS = 6000


def _make_click_through(window: tk.Toplevel) -> None:
    hwnd = ctypes.windll.user32.GetParent(window.winfo_id())
    if not hwnd:
        hwnd = window.winfo_id()
    style = ctypes.windll.user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
    ctypes.windll.user32.SetWindowLongW(
        hwnd, GWL_EXSTYLE, style | WS_EX_LAYERED | WS_EX_TRANSPARENT | WS_EX_TOOLWINDOW
    )


class OverlayNotifier:
    """Built once at UI startup; `show()` is safe to call repeatedly (resets the dismiss timer)."""

    def __init__(self, root: tk.Tk) -> None:
        self._root = root
        self._hide_job: str | None = None

        win = tk.Toplevel(root)
        win.overrideredirect(True)
        win.attributes("-topmost", True)
        win.attributes("-alpha", 0.92)
        win.configure(bg="#1c1c1c")

        self._label = tk.Label(
            win, text="", bg="#1c1c1c", fg="#ffcc66", font=("Segoe UI", 11),
            padx=14, pady=8, justify="left", wraplength=320,
        )
        self._label.pack()
        win.update_idletasks()
        _make_click_through(win)
        win.withdraw()
        self._window = win

    def show(self, text: str) -> None:
        self._label.config(text=text)
        self._window.update_idletasks()
        width = self._window.winfo_reqwidth()
        screen_w = self._window.winfo_screenwidth()
        self._window.geometry(f"+{screen_w - width - 24}+24")
        self._window.deiconify()

        if self._hide_job is not None:
            self._root.after_cancel(self._hide_job)
        self._hide_job = self._root.after(DISPLAY_MS, self._window.withdraw)
