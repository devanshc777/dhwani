"""Microphone capture. Push-to-talk toggle means no VAD is needed:
the user delimits speech with the hotkey, so we just buffer everything
between start() and stop().

`levels` is a rolling RMS deque the overlay reads to animate its bars —
audio thread writes, UI thread reads; deque(maxlen) makes that safe.
"""

from collections import deque

import numpy as np
import sounddevice as sd

from . import config


class Recorder:
    def __init__(self) -> None:
        self._chunks: list[np.ndarray] = []
        self._stream: sd.InputStream | None = None
        self.levels: deque[float] = deque(maxlen=28)

    @property
    def active(self) -> bool:
        return self._stream is not None

    def start(self) -> None:
        self._chunks = []
        self.levels.clear()
        self._stream = sd.InputStream(
            samplerate=config.SAMPLE_RATE,
            channels=1,
            dtype="float32",
            callback=self._on_audio,
        )
        self._stream.start()

    def _on_audio(self, indata, frames, time_info, status) -> None:
        self._chunks.append(indata.copy())
        self.levels.append(float(np.sqrt(np.mean(indata**2))))

    def stop(self) -> np.ndarray:
        """Stop capture, return the full utterance as float32 mono @16kHz."""
        if self._stream is not None:
            self._stream.stop()
            self._stream.close()
            self._stream = None
        if not self._chunks:
            return np.zeros(0, dtype=np.float32)
        return np.concatenate(self._chunks).flatten()
