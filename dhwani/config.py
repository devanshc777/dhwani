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
# Right Alt, tapped: the least-colliding trigger on this keyboard (no Right
# Ctrl present). Bare Fn is firmware-invisible, F-keys sit behind media mode,
# and every modifier chord (Ctrl+Alt, Ctrl+Shift+Alt) doubles as some app's
# shortcut prefix. Left Alt still carries all shortcuts. On AltGr layouts
# (right alt types accents), override via DHWANI_HOTKEY instead.
# Comma-separated aliases all bind to the same toggle: Windows reports the
# physical Right Alt key as "alt gr" on some layouts and "right alt" on others.
HOTKEY = os.getenv("DHWANI_HOTKEY", "right alt,alt gr")
PORT = int(os.getenv("DHWANI_PORT", "8770"))

# Free the model weights (~300 MB for base) after this many idle minutes;
# they reload transparently (~2 s) on the next hotkey press. 0 disables.
IDLE_UNLOAD_MIN = float(os.getenv("DHWANI_IDLE_UNLOAD_MIN", "30"))

DB_PATH = Path(os.getenv("DHWANI_DB", "~/.dhwani/transcripts.db")).expanduser()
DB_PATH.parent.mkdir(parents=True, exist_ok=True)
