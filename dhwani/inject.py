"""Text injection into whatever app has focus.

Clipboard + Ctrl+V is the blunt-but-reliable path: it survives every app
that accepts paste, including ones where synthetic per-key typing breaks
(Electron apps, some IMEs, RDP). Previous clipboard content is restored
after a short delay.

Subtlety: the hotkey is Alt+V, so Alt is often still physically held when
injection runs. Without releasing it, Ctrl+V becomes Ctrl+Alt+V (which
most apps ignore). We force-release modifiers and give the OS a beat.
"""

import threading
import time

import keyboard
import pyperclip


def paste(text: str) -> None:
    if not text:
        return

    try:
        previous = pyperclip.paste()
    except Exception:  # clipboard can hold non-text (images) — skip restore
        previous = None

    pyperclip.copy(text)

    for key in ("alt", "ctrl", "shift", "windows", "tab"):
        keyboard.release(key)
    time.sleep(0.15)  # let the target app see the modifiers go up

    keyboard.send("ctrl+v")

    if previous is not None:

        def restore() -> None:
            time.sleep(0.4)  # after the target app has read the clipboard
            try:
                pyperclip.copy(previous)
            except Exception:
                pass

        threading.Thread(target=restore, daemon=True).start()
