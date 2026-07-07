"""Speech-to-text via faster-whisper (CTranslate2, int8, CPU).

Quality settings (each earned by a v0.1 field failure — see docs/BUILD_LOG.md):
- language pinned (auto-detect misfires on short clips),
- vad_filter=True: faster-whisper's bundled Silero pass strips in-clip
  silence so whisper stops hallucinating "You You... Hi. Hi." on quiet
  stretches. (Different job from utterance-delimiting VAD, which the
  push-to-talk UX still makes unnecessary.)
- initial_prompt biases spelling of names/jargon,
- condition_on_previous_text=False kills repetition loops.

The model unloads after IDLE_UNLOAD_MIN minutes (frees ~300 MB) and
reloads transparently on next use.
"""

import threading
import time

import numpy as np
from faster_whisper import WhisperModel

from . import config


class Transcriber:
    def __init__(self) -> None:
        self._model: WhisperModel | None = None
        self._lock = threading.Lock()
        self.last_used = time.time()
        threading.Thread(target=self._ensure_loaded, daemon=True).start()

    @property
    def ready(self) -> bool:
        return self._model is not None

    def _ensure_loaded(self) -> WhisperModel:
        with self._lock:
            if self._model is None:
                self._model = WhisperModel(
                    config.MODEL_SIZE,
                    device=config.DEVICE,
                    compute_type=config.COMPUTE_TYPE,
                )
        return self._model

    def unload(self) -> None:
        with self._lock:
            self._model = None  # CTranslate2 frees weights with the object

    def transcribe(self, audio: np.ndarray) -> str:
        if audio.size < config.SAMPLE_RATE // 4:  # <0.25s: nothing real said
            return ""
        self.last_used = time.time()
        model = self._ensure_loaded()  # blocks ~2s if idle-unloaded
        segments, _ = model.transcribe(
            audio,
            language=config.LANGUAGE,
            initial_prompt=config.INITIAL_PROMPT,
            beam_size=5,
            vad_filter=True,
            vad_parameters={"min_silence_duration_ms": 500},
            condition_on_previous_text=False,
        )
        text = " ".join(seg.text.strip() for seg in segments).strip()
        self.last_used = time.time()
        return text
