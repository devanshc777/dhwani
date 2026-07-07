"""Wiring. Thread map (each does one thing):

  main thread        tkinter mainloop — owns the overlay (tk is not thread-safe)
  keyboard hook      fires toggle() on Alt+V; touches only audio + a queue
  audio callback     sounddevice's thread; buffers chunks + RMS levels
  worker (per stop)  transcribe -> clean -> save -> paste
  uvicorn daemon     serves the localhost UI
  model loader       one-shot background whisper load at startup

Stages exchange plain data only (float32 audio in, str out) — swap any
stage (e.g. OpenVINO whisper, an LLM cleaner) without touching the rest.
"""

import logging
import queue
import threading
import time
import tkinter as tk

import keyboard
import uvicorn

from . import config, inject, store
from .audio import Recorder
from .cleanup import clean
from .overlay import Overlay
from .server import app, state
from .transcribe import Transcriber

log = logging.getLogger("dhwani")


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    recorder = Recorder()
    transcriber = Transcriber()  # starts loading immediately, in background
    state.update(model_size=config.MODEL_SIZE, hotkey=config.HOTKEY)

    root = tk.Tk()
    root.withdraw()  # no main window; tk exists to host the overlay
    overlay = Overlay(root, recorder.levels)
    ui_events: queue.Queue[str] = queue.Queue()
    started_at = {"t": 0.0}

    def toggle() -> None:
        """Alt+V handler. Runs on the keyboard hook thread — no tk calls here;
        overlay commands go through the queue to the main thread."""
        if not recorder.active:
            recorder.start()
            started_at["t"] = time.time()
            state["recording"] = True
            ui_events.put("show")
        else:
            audio = recorder.stop()
            duration = time.time() - started_at["t"]
            state["recording"] = False
            ui_events.put("hide")
            threading.Thread(
                target=_process, args=(audio, duration), daemon=True
            ).start()

    def _process(audio, duration: float) -> None:
        raw = transcriber.transcribe(audio)
        if not raw:
            log.info("empty utterance (%.1fs) — nothing injected", duration)
            return
        text = clean(raw)
        store.save(raw, text, duration)
        inject.paste(text)
        log.info("dictated %.1fs -> %d chars", duration, len(text))

    def _pump() -> None:
        """Main-thread heartbeat: apply queued overlay commands, mirror state."""
        try:
            while True:
                overlay.show() if ui_events.get_nowait() == "show" else overlay.hide()
        except queue.Empty:
            pass
        state["model_ready"] = transcriber.ready
        root.after(50, _pump)

    keyboard.add_hotkey(config.HOTKEY, toggle, suppress=True)

    threading.Thread(
        target=uvicorn.run,
        kwargs=dict(app=app, host="127.0.0.1", port=config.PORT, log_level="warning"),
        daemon=True,
    ).start()

    log.info(
        "dhwani up · hotkey=%s · ui=http://127.0.0.1:%d · model=%s (warming up)",
        config.HOTKEY, config.PORT, config.MODEL_SIZE,
    )
    root.after(50, _pump)
    root.mainloop()


if __name__ == "__main__":
    main()
