"""The recording pill: a small floating waveform near the bottom of the
screen while recording — smooth mirrored glow lines (violet/indigo), not
bars. tkinter has no alpha blending, so "glow" is layered strokes: wide
dark stroke under progressively narrower, brighter ones. The window
background is keyed transparent (-transparentcolor), so only the waveform
floats over whatever's behind it.

Critical detail: WS_EX_NOACTIVATE. The overlay must NEVER take keyboard
focus — focus stays in the app the user is dictating into, or the paste
would land in the overlay. WS_EX_TOOLWINDOW keeps it out of the taskbar.
"""

import ctypes
import tkinter as tk

GWL_EXSTYLE = -20
WS_EX_NOACTIVATE = 0x08000000
WS_EX_TOOLWINDOW = 0x00000080

WIDTH, HEIGHT = 200, 44
BG = "#0a0714"  # also the transparency key color
# glow = layered strokes, darkest/widest first
LAYERS = [("#2a1b5e", 7), ("#5b3fd4", 4), ("#8f6fff", 2), ("#e6ddff", 1)]


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
        try:
            win.attributes("-transparentcolor", BG)  # float the waveform alone
        except tk.TclError:
            pass  # non-Windows: solid pill, still fine
        sw, sh = win.winfo_screenwidth(), win.winfo_screenheight()
        win.geometry(f"{WIDTH}x{HEIGHT}+{(sw - WIDTH) // 2}+{sh - HEIGHT - 70}")
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

    def _wave_points(self) -> list[float]:
        """Zigzag through the level history; smooth=True splines it into a
        waveform. Newest audio on the right."""
        levels = list(self._levels)
        n = self._levels.maxlen or 28
        mid = HEIGHT / 2
        step = WIDTH / (n - 1)
        pts: list[float] = []
        for i in range(n):
            level = levels[-(n - i)] if len(levels) >= n - i else 0.0
            amp = min(mid - 4, 1.5 + level * 300)
            y = mid - amp if i % 2 == 0 else mid + amp
            pts += [i * step, y]
        return pts

    def _animate(self) -> None:
        if self._win is None or self._canvas is None:
            return
        c = self._canvas
        c.delete("all")
        pts = self._wave_points()
        for color, width in LAYERS:
            c.create_line(
                *pts, smooth=True, fill=color, width=width,
                capstyle=tk.ROUND, joinstyle=tk.ROUND,
            )
        self._win.after(50, self._animate)  # ~20 fps is plenty for a meter

    def hide(self) -> None:
        if self._win is not None:
            self._win.destroy()
            self._win = None
            self._canvas = None
