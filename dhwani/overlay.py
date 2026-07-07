"""The recording pill, Wispr-style: a small solid dark capsule at the
bottom of the screen with a row of eased level bars inside it.

Why a solid capsule (v3) and not floating strokes (v2): anti-aliased
strokes blend against the transparency key color and produce off-hue
fringe pixels ("weird green"), and raw per-frame RMS makes any wave shape
teleport jarringly. A solid body confines key-color blending to the
capsule silhouette, and bars ease toward their targets instead of jumping.

Capsule trick: one thick horizontal line with rounded caps IS a capsule —
two of them, 2px apart in width, give a 1px border for free.

Critical detail: WS_EX_NOACTIVATE — the pill must never steal focus from
the app being dictated into, or the paste lands in the pill.
"""

import ctypes
import tkinter as tk

GWL_EXSTYLE = -20
WS_EX_NOACTIVATE = 0x08000000
WS_EX_TOOLWINDOW = 0x00000080

WIDTH, HEIGHT = 132, 34
KEY = "#010203"       # transparency key; never used in the artwork
PILL_BG = "#14101f"
PILL_EDGE = "#2e2547"

N_BARS = 13
BAR_W = 3
GAP = 4
MAX_AMP = (HEIGHT - 14) / 2   # bar half-height ceiling inside the capsule
LOW = (109, 91, 208)          # quiet bar color
HIGH = (237, 233, 254)        # loud bar color


def _lerp_color(t: float) -> str:
    r, g, b = (round(a + (b_ - a) * t) for a, b_ in zip(LOW, HIGH))
    return f"#{r:02x}{g:02x}{b:02x}"


class Overlay:
    """show()/hide() from the tk main thread only (root.after handles that)."""

    def __init__(self, root: tk.Tk, levels) -> None:
        self._root = root
        self._levels = levels  # Recorder.levels deque (audio thread writes)
        self._win: tk.Toplevel | None = None
        self._canvas: tk.Canvas | None = None
        self._shown = [0.0] * N_BARS  # eased bar amplitudes

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
        self._shown = [0.0] * N_BARS
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
        c.delete("bars")

        levels = list(self._levels)
        recent = levels[-N_BARS:] if levels else []
        recent = [0.0] * (N_BARS - len(recent)) + recent  # left-pad quiet
        mid = HEIGHT / 2
        total = N_BARS * BAR_W + (N_BARS - 1) * GAP
        x = (WIDTH - total) / 2 + BAR_W / 2
        for i in range(N_BARS):
            target = min(MAX_AMP, recent[i] * 240)
            self._shown[i] += (target - self._shown[i]) * 0.35  # ease, don't jump
            amp = max(1.2, self._shown[i])  # silence reads as a dotted line
            c.create_line(
                x, mid - amp, x, mid + amp,
                width=BAR_W, capstyle=tk.ROUND,
                fill=_lerp_color(min(1.0, amp / MAX_AMP)),
                tags="bars",
            )
            x += BAR_W + GAP
        self._win.after(33, self._animate)  # ~30 fps for smooth easing

    def hide(self) -> None:
        if self._win is not None:
            self._win.destroy()
            self._win = None
            self._canvas = None
