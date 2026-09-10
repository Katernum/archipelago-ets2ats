"""
Milestone 5: the on-demand dashboard window (opened from the tray icon) -- connection/
telemetry status, a scrolling log of checks and received items, and a manual Sync Now
button. Built once at UI startup and kept withdrawn until the player opens it, so status
updates arriving before the first open aren't lost.
"""

from __future__ import annotations

import tkinter as tk
from tkinter import scrolledtext
from typing import Callable


class Dashboard:
    def __init__(self, root: tk.Tk, on_sync_now: Callable[[], None]) -> None:
        win = tk.Toplevel(root)
        win.title("ETS2ATS Archipelago")
        win.geometry("380x320")
        win.protocol("WM_DELETE_WINDOW", win.withdraw)

        self._status_var = tk.StringVar(value="Connecting...")
        tk.Label(win, textvariable=self._status_var, anchor="w").pack(fill="x", padx=8, pady=(8, 0))

        self._pending_var = tk.StringVar(value="Pending items: 0")
        tk.Label(win, textvariable=self._pending_var, anchor="w").pack(fill="x", padx=8)

        self._log = scrolledtext.ScrolledText(win, height=12, state="disabled", wrap="word")
        self._log.pack(fill="both", expand=True, padx=8, pady=8)

        tk.Button(win, text="Sync Now", command=on_sync_now).pack(pady=(0, 8))

        win.withdraw()
        self._window = win

    def show(self) -> None:
        self._window.deiconify()
        self._window.lift()

    def set_status(self, text: str) -> None:
        self._status_var.set(text)

    def set_pending(self, names: list[str]) -> None:
        self._pending_var.set(f"Pending items: {len(names)}")

    def log(self, text: str) -> None:
        self._log.config(state="normal")
        self._log.insert("end", text + "\n")
        self._log.see("end")
        self._log.config(state="disabled")
