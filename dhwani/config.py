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

# Pinned to English by default: auto-detect on short utterances is a coin
# toss (v0.1 field test: 0.3s clips detected as Russian at p=0.20 and came
# out as Cyrillic). Set DHWANI_LANGUAGE=auto to re-enable detection, or
# e.g. hi for Hindi.
_lang = os.getenv("DHWANI_LANGUAGE", "en").strip().lower()
LANGUAGE = None if _lang in ("", "auto") else _lang

# Decoder bias: words whisper should spell correctly (names, jargon).
# Comma-separated, fed as initial_prompt. Fixes "Chowdhary" -> "Chaudhary".
INITIAL_PROMPT = os.getenv(
    "DHWANI_PROMPT", "Devansh Chowdhary, dhwani, FastAPI, Qilin."
)

SAMPLE_RATE = 16_000  # whisper's native rate
# Ctrl+F9: Tab+Q (v0.2) kept firing while tab-cycling in browsers; a chorded
# F-key can't collide with typing or site shortcuts. (Bare Fn is firmware-level
# and invisible to the OS, so it can't be part of a software hotkey.)
HOTKEY = os.getenv("DHWANI_HOTKEY", "ctrl+f9")
PORT = int(os.getenv("DHWANI_PORT", "8770"))

# Free the model weights (~300 MB for base) after this many idle minutes;
# they reload transparently (~2 s) on the next hotkey press. 0 disables.
IDLE_UNLOAD_MIN = float(os.getenv("DHWANI_IDLE_UNLOAD_MIN", "30"))

DB_PATH = Path(os.getenv("DHWANI_DB", "~/.dhwani/transcripts.db")).expanduser()
DB_PATH.parent.mkdir(parents=True, exist_ok=True)
