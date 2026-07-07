"""Localhost web UI: transcript history + live status.

One FastAPI app, one HTML file, zero build step. The page polls JSON —
at dictation rates a WebSocket would be ceremony.
"""

from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse

from . import store

_PAGE = Path(__file__).parent / "web" / "index.html"

app = FastAPI(title="dhwani")

# main.py sets these so the UI can show live state
state = {"recording": False, "model_ready": False, "model_size": "", "hotkey": ""}


@app.get("/")
def index() -> FileResponse:
    return FileResponse(_PAGE)


@app.get("/api/status")
def status() -> dict:
    return state


@app.get("/api/transcripts")
def transcripts() -> list[dict]:
    return store.recent()
