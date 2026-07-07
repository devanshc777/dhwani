"""Central config. Everything overridable via environment variables.

Design rule: the pipeline stages (record -> transcribe -> clean -> inject)
only exchange plain data (numpy audio, str text). Any stage can be swapped
without touching the others as long as this contract holds.
"""

import os
from pathlib import Path

# Whisper model: tiny | base | small (bigger = slower + better; all CPU-fine)
MODEL_SIZE = os.getenv("DHWANI_MODEL", "base")
DEVICE = "cpu"
COMPUTE_TYPE = "int8"  # quantized CPU inference via CTranslate2

# None = whisper auto-detects language per utterance (handles Hinglish);
# set DHWANI_LANGUAGE=en to pin English for speed + accuracy.
LANGUAGE = os.getenv("DHWANI_LANGUAGE") or None

SAMPLE_RATE = 16_000  # whisper's native rate
HOTKEY = os.getenv("DHWANI_HOTKEY", "alt+v")
PORT = int(os.getenv("DHWANI_PORT", "8770"))

DB_PATH = Path(os.getenv("DHWANI_DB", "~/.dhwani/transcripts.db")).expanduser()
DB_PATH.parent.mkdir(parents=True, exist_ok=True)
