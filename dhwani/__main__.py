import faulthandler
import logging
import os
import sys
from pathlib import Path

# Under pythonw sys.stdout/stderr are None. uvicorn's logging setup writes to
# sys.stderr during server startup and its thread dies BEFORE binding the port
# — silently. Shim the null streams first, before anything imports uvicorn.
if sys.stdout is None:
    sys.stdout = open(os.devnull, "w", encoding="utf-8")
if sys.stderr is None:
    sys.stderr = open(os.devnull, "w", encoding="utf-8")

from .main import main

# Under pythonw there is no console: dump hard crashes (segfaults in native
# audio/keyboard hooks) and top-level exceptions where we can read them.
_log_dir = Path("~/.dhwani").expanduser()
_log_dir.mkdir(parents=True, exist_ok=True)
_crash = open(_log_dir / "crash.log", "a", encoding="utf-8")
faulthandler.enable(file=_crash)

try:
    main()
except Exception:
    logging.getLogger("dhwani").exception("fatal: main() died")
    raise
