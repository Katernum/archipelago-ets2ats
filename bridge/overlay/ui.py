"""
Milestone 5: owns the Tk root and mainloop on a dedicated UI thread, since the AP client's
asyncio loop already owns the main thread. Tkinter isn't safe to touch across threads, so
the asyncio side never calls into a widget directly -- it only pushes onto a thread-safe
queue.Queue, which this thread drains on its own `root.after()` poll. The tray icon runs on
a third thread (pystray's own requirement); its callbacks are forwarded here the same way.
"""

from __future__ import annotations

import queue
import threading
import tkinter as tk
from typing import Callable

from .dashboard import Dashboard
from .notifier import OverlayNotifier
from .tray import start_tray

POLL_MS = 50


class UI:
    def __init__(self, on_sync_now: Callable[[], None], on_quit: Callable[[], None]) -> None:
        self._events: queue.Queue = queue.Queue()
        self._on_sync_now = on_sync_now
        self._on_quit = on_quit
        self._ready = threading.Event()
        self._thread = threading.Thread(target=self._run, name="ui-thread", daemon=True)
        self._thread.start()
        self._ready.wait()

    # ---- thread-safe API for the asyncio side ----
    def notify(self, text: str) -> None:
        self._events.put(("notify", text))

    def set_status(self, text: str) -> None:
        self._events.put(("status", text))

    def set_pending(self, names: list[str]) -> None:
        self._events.put(("pending", names))

    def stop(self) -> None:
        self._events.put(("quit", None))

    # ---- UI thread body -- everything below only ever runs here ----
    def _run(self) -> None:
        root = tk.Tk()
        root.withdraw()  # the root itself is never shown, it only anchors the mainloop

        overlay = OverlayNotifier(root)
        dashboard = Dashboard(root, on_sync_now=self._on_sync_now)
        tray = start_tray(dashboard.show, self._on_sync_now, lambda: self._events.put(("quit", None)))

        def poll() -> None:
            try:
                while True:
                    kind, payload = self._events.get_nowait()
                    if kind == "notify":
                        overlay.show(payload)
                        dashboard.log(payload)
                    elif kind == "status":
                        dashboard.set_status(payload)
                    elif kind == "pending":
                        dashboard.set_pending(payload)
                    elif kind == "quit":
                        self._on_quit()
                        tray.stop()
                        root.quit()
                        return
            except queue.Empty:
                pass
            root.after(POLL_MS, poll)

        root.after(POLL_MS, poll)
        self._ready.set()
        root.mainloop()
