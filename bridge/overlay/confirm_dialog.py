"""
Milestone 5: a yes/no confirmation dialog, used to gate risky actions (applying items to a
save file we only guessed at) behind an explicit answer.

Deliberately not `tkinter.messagebox` -- that dialog is parented to our root window, which is
permanently withdrawn (see ui.py) since it only exists to anchor the mainloop, and in testing
the resulting messagebox did not reliably raise itself above other windows on Windows. This
builds a plain Toplevel the same way notifier.py's overlay does (explicit `-topmost` plus
`lift()`/`focus_force()`), which was already confirmed to show up reliably.
"""

from __future__ import annotations

import tkinter as tk


def ask_yes_no(root: tk.Tk, title: str, message: str) -> bool:
    result = {"value": False}

    win = tk.Toplevel(root)
    win.title(title)
    win.attributes("-topmost", True)
    win.resizable(False, False)
    win.protocol("WM_DELETE_WINDOW", lambda: answer(False))

    tk.Label(win, text=message, justify="left", padx=16, pady=16, wraplength=360).pack()

    def answer(value: bool) -> None:
        result["value"] = value
        win.destroy()

    buttons = tk.Frame(win)
    buttons.pack(pady=(0, 12))
    tk.Button(buttons, text="Yes", width=10, command=lambda: answer(True)).pack(side="left", padx=6)
    tk.Button(buttons, text="No", width=10, command=lambda: answer(False)).pack(side="left", padx=6)

    win.update_idletasks()
    screen_w, screen_h = win.winfo_screenwidth(), win.winfo_screenheight()
    w, h = win.winfo_reqwidth(), win.winfo_reqheight()
    win.geometry(f"+{(screen_w - w) // 2}+{(screen_h - h) // 2}")

    win.grab_set()
    win.lift()
    win.focus_force()
    win.wait_window()
    return result["value"]
