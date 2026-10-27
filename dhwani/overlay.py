"""The recording pill: a small forest-green capsule at the bottom of the
screen, a mint "live" dot, and one flowing line that swells with your voice.

Why this look (v4): the pill wears the web UI's colours (forest, mint,
cream) and the hero's motif, a single hand-drawn line, instead of v3's
violet bar meter, which belonged to no other part of dhwani. Each colour has
one job: mint means "listening" (the dot breathes even in silence, so you
can tell a quiet mic from a stopped one), cream is your voice.

Why a solid capsule (since v3): anti-aliased strokes blend against the
transparency key color and produce off-hue fringe pixels, so the body stays
solid and the key only touches its silhouette. Levels ease toward their
targets instead of jumping.

Capsule trick: one thick horizontal line with rounded caps IS a capsule —
two of them, 2px apart in width, give a 1px border for free.

Critical detail: WS_EX_NOACTIVATE — the pill must never steal focus from
the app being dictated into, or the paste lands in the pill.
"""

import ctypes
import math
import tkinter as tk

GWL_EXSTYLE = -20
WS_EX_NOACTIVATE = 0x08000000
WS_EX_TOOLWINDOW = 0x00000080

WIDTH, HEIGHT = 148, 34
KEY = "#010203"       # transparency key; never used in the artwork
PILL_BG = "#1d3d2f"   # --forest in web/index.html
PILL_EDGE = "#33604a" # --forest-line
LIVE = "#b9e0c3"      # --mint: the "listening" dot
VOICE = "#f3eddd"     # --cream: the voice line

DOT_X = 17
DOT_R = 3.5
LINE_X0, LINE_X1 = 30, WIDTH - 16
N_POINTS = 28
MAX_AMP = (HEIGHT - 12) / 2   # line half-height ceiling inside the capsule
QUIET_AMP = 1.0               # silence reads as a faint ripple, not a dead line


class Overlay:
    """show()/hide() from the tk main thread only (root.after handles that)."""

    def __init__(self, root: tk.Tk, levels) -> None:
        self._root = root
        self._levels = levels  # Recorder.levels deque (audio thread writes)
        self._win: tk.Toplevel | None = None
        self._canvas: tk.Canvas | None = None
        self._shown = [0.0] * N_POINTS  # eased amplitudes along the line
        self._phase = 0.0

    def show(self) -> None:
        if self._win is not None:
            return
        win = tk.Toplevel(self._root)
        win.overrideredirect(True)
        win.attributes("-topmost", True)
        try:
            win.attributes("-transparentcolor", KEY)  # round the corners
        except tk.TclError:
            pass  # non-Windows: rectangular pill, still fine
        sw, sh = win.winfo_screenwidth(), win.winfo_screenheight()
        win.geometry(f"{WIDTH}x{HEIGHT}+{(sw - WIDTH) // 2}+{sh - HEIGHT - 60}")
        win.configure(bg=KEY)

        c = tk.Canvas(win, width=WIDTH, height=HEIGHT, bg=KEY, highlightthickness=0)
        c.pack()
        mid = HEIGHT / 2
        r = HEIGHT / 2
        # capsule body: thick round-capped lines (edge under body = 1px border)
        c.create_line(r, mid, WIDTH - r, mid, width=HEIGHT - 1,
                      capstyle=tk.ROUND, fill=PILL_EDGE)
        c.create_line(r, mid, WIDTH - r, mid, width=HEIGHT - 3,
                      capstyle=tk.ROUND, fill=PILL_BG)

        win.update_idletasks()
        self._make_unfocusable(win)
        self._win = win
        self._canvas = c
        self._shown = [0.0] * N_POINTS
        self._phase = 0.0
        self._animate()

    def _make_unfocusable(self, win: tk.Toplevel) -> None:
        try:
            hwnd = ctypes.windll.user32.GetParent(win.winfo_id())
            style = ctypes.windll.user32.GetWindowLongPtrW(hwnd, GWL_EXSTYLE)
            ctypes.windll.user32.SetWindowLongPtrW(
                hwnd, GWL_EXSTYLE, style | WS_EX_NOACTIVATE | WS_EX_TOOLWINDOW
            )
        except Exception:
            pass

    def _animate(self) -> None:
        if self._win is None or self._canvas is None:
            return
        c = self._canvas
        c.delete("live")
        mid = HEIGHT / 2
        self._phase += 0.22

        # breathing dot: slow pulse, independent of the mic
        dr = DOT_R + 0.8 * math.sin(self._phase * 0.35)
        c.create_oval(DOT_X - dr, mid - dr, DOT_X + dr, mid + dr,
                      fill=LIVE, outline="", tags="live")

        levels = list(self._levels)
        recent = levels[-N_POINTS:] if levels else []
        recent = [0.0] * (N_POINTS - len(recent)) + recent  # left-pad quiet
        step = (LINE_X1 - LINE_X0) / (N_POINTS - 1)
        coords = []
        for i in range(N_POINTS):
            target = min(MAX_AMP, recent[i] * 240)
            self._shown[i] += (target - self._shown[i]) * 0.3  # ease, don't jump
            # taper both ends so the line leaves and rejoins the midline
            taper = math.sin(math.pi * i / (N_POINTS - 1))
            amp = max(QUIET_AMP, self._shown[i]) * taper
            y = mid + amp * math.sin(self._phase + i * 0.9)
            coords += [LINE_X0 + i * step, y]
        c.create_line(*coords, width=2, fill=VOICE, smooth=True,
                      capstyle=tk.ROUND, joinstyle=tk.ROUND, tags="live")
        self._win.after(33, self._animate)  # ~30 fps for smooth easing

    def hide(self) -> None:
        if self._win is not None:
            self._win.destroy()
            self._win = None
            self._canvas = None
