"""The little recording pill: a borderless, always-on-top strip of animated
level bars near the bottom of the screen while recording.

tkinter (stdlib) instead of a GUI dependency — it's one canvas.

Critical detail: WS_EX_NOACTIVATE. The overlay must NEVER take keyboard
focus — focus stays in the app the user is dictating into, or the paste
would land in the overlay. WS_EX_TOOLWINDOW keeps it out of the taskbar.
"""

import ctypes
import tkinter as tk

GWL_EXSTYLE = -20
WS_EX_NOACTIVATE = 0x08000000
WS_EX_TOOLWINDOW = 0x00000080

WIDTH, HEIGHT, BARS = 240, 56, 24
BG, BAR_COLOR = "#0d0d10", "#e8b849"


class Overlay:
    """show()/hide() from the tk main thread only (root.after handles that)."""

    def __init__(self, root: tk.Tk, levels) -> None:
        self._root = root
        self._levels = levels  # Recorder.levels deque (audio thread writes)
        self._win: tk.Toplevel | None = None
        self._canvas: tk.Canvas | None = None

    def show(self) -> None:
        if self._win is not None:
            return
        win = tk.Toplevel(self._root)
        win.overrideredirect(True)
        win.attributes("-topmost", True)
        sw, sh = win.winfo_screenwidth(), win.winfo_screenheight()
        win.geometry(f"{WIDTH}x{HEIGHT}+{(sw - WIDTH) // 2}+{sh - HEIGHT - 80}")
        win.configure(bg=BG)

        self._canvas = tk.Canvas(
            win, width=WIDTH, height=HEIGHT, bg=BG, highlightthickness=0
        )
        self._canvas.pack()

        win.update_idletasks()
        self._make_unfocusable(win)
        self._win = win
        self._animate()

    def _make_unfocusable(self, win: tk.Toplevel) -> None:
        try:
            hwnd = ctypes.windll.user32.GetParent(win.winfo_id())
            style = ctypes.windll.user32.GetWindowLongPtrW(hwnd, GWL_EXSTYLE)
            ctypes.windll.user32.SetWindowLongPtrW(
                hwnd, GWL_EXSTYLE, style | WS_EX_NOACTIVATE | WS_EX_TOOLWINDOW
            )
        except Exception:
            pass  # non-Windows: overlay still works, just may take focus

    def _animate(self) -> None:
        if self._win is None or self._canvas is None:
            return
        c = self._canvas
        c.delete("all")
        levels = list(self._levels)
        slot = WIDTH / BARS
        mid = HEIGHT / 2
        for i in range(BARS):
            # newest level on the right, fading history to the left
            level = levels[-(BARS - i)] if len(levels) >= BARS - i else 0.0
            half = max(2.0, min(mid - 6, level * 260))  # RMS -> pixel half-height
            x = i * slot + slot / 2
            c.create_line(x, mid - half, x, mid + half, fill=BAR_COLOR, width=3)
        self._win.after(50, self._animate)  # ~20 fps is plenty for a meter

    def hide(self) -> None:
        if self._win is not None:
            self._win.destroy()
            self._win = None
            self._canvas = None
