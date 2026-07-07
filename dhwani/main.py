"""Wiring. Thread map (each does one thing):

  main thread        tkinter mainloop — owns the overlay (tk is not thread-safe)
  keyboard hook      fires toggle() on the hotkey; touches only audio + a queue
  audio callback     sounddevice's thread; buffers chunks + RMS levels
  worker             single consumer of a job queue: transcribe -> clean ->
                     save -> paste. ONE worker on purpose — v0.1 ran a thread
                     per utterance and rapid toggles interleaved three
                     transcriptions into each other's paste targets.
  uvicorn daemon     serves the localhost UI
  model loader       background whisper load at startup + idle unload/reload

Stages exchange plain data only (float32 audio in, str out).
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

DEBOUNCE_S = 0.5  # Windows key auto-repeat re-fires hotkeys every ~120 ms


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    recorder = Recorder()
    transcriber = Transcriber()  # starts loading immediately, in background
    state.update(model_size=config.MODEL_SIZE, hotkey=config.HOTKEY)

    root = tk.Tk()
    root.withdraw()  # no main window; tk exists to host the overlay
    overlay = Overlay(root, recorder.levels)
    ui_events: queue.Queue[str] = queue.Queue()
    jobs: queue.Queue[tuple] = queue.Queue()
    started_at = {"t": 0.0}
    last_fire = {"t": 0.0}

    def toggle() -> None:
        """Hotkey handler (keyboard hook thread). No tk calls here."""
        now = time.time()
        if now - last_fire["t"] < DEBOUNCE_S:  # swallow key auto-repeat
            return
        last_fire["t"] = now

        if not recorder.active:
            recorder.start()
            started_at["t"] = now
            state["recording"] = True
            ui_events.put("show")
        else:
            audio = recorder.stop()
            state["recording"] = False
            ui_events.put("hide")
            jobs.put((audio, now - started_at["t"]))

    def _worker() -> None:
        """Sole consumer: utterances process and inject strictly in order."""
        while True:
            audio, duration = jobs.get()
            try:
                raw = transcriber.transcribe(audio)
                if not raw:
                    log.info("empty utterance (%.1fs) — nothing injected", duration)
                    continue
                text = clean(raw)
                store.save(raw, text, duration)
                inject.paste(text)
                log.info("dictated %.1fs -> %d chars", duration, len(text))
            except Exception:
                log.exception("utterance failed")

    def _pump() -> None:
        """Main-thread heartbeat: apply queued overlay commands, mirror state."""
        try:
            while True:
                overlay.show() if ui_events.get_nowait() == "show" else overlay.hide()
        except queue.Empty:
            pass
        state["model_ready"] = transcriber.ready
        root.after(50, _pump)

    def _idle_watch() -> None:
        """Free model RAM after IDLE_UNLOAD_MIN quiet minutes."""
        if (
            config.IDLE_UNLOAD_MIN > 0
            and transcriber.ready
            and not recorder.active
            and jobs.empty()
            and time.time() - transcriber.last_used > config.IDLE_UNLOAD_MIN * 60
        ):
            transcriber.unload()
            log.info(
                "idle %.0f min — model unloaded (~300 MB freed; reloads on next %s)",
                config.IDLE_UNLOAD_MIN, config.HOTKEY,
            )
        root.after(60_000, _idle_watch)

    threading.Thread(target=_worker, daemon=True).start()
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
    root.after(60_000, _idle_watch)
    root.mainloop()


if __name__ == "__main__":
    main()
