"""Speech-to-text via faster-whisper (CTranslate2, int8, CPU).

The model loads in a background thread at startup so the first Alt+V
doesn't eat the load time. First-ever run also downloads the model
(~74 MB for base) to the local HF cache — one-time cost.

Whisper emits punctuated, capitalized text natively, which is why this
project needs no separate punctuation model and no LLM.
"""

import threading

import numpy as np
from faster_whisper import WhisperModel

from . import config


class Transcriber:
    def __init__(self) -> None:
        self._model: WhisperModel | None = None
        self._ready = threading.Event()
        threading.Thread(target=self._load, daemon=True).start()

    @property
    def ready(self) -> bool:
        return self._ready.is_set()

    def _load(self) -> None:
        self._model = WhisperModel(
            config.MODEL_SIZE, device=config.DEVICE, compute_type=config.COMPUTE_TYPE
        )
        self._ready.set()

    def transcribe(self, audio: np.ndarray) -> str:
        if audio.size < config.SAMPLE_RATE // 4:  # <0.25s: nothing real said
            return ""
        self._ready.wait()  # only blocks if hotkey beat the model load
        segments, _ = self._model.transcribe(
            audio, language=config.LANGUAGE, beam_size=5
        )
        return " ".join(seg.text.strip() for seg in segments).strip()
