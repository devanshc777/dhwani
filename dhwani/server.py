"""Localhost web UI: transcript history, live status, context words.

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


@app.get("/api/prompt")
def get_prompt_words() -> list[str]:
    return store.prompt_words()


@app.post("/api/prompt/{word}")
def add_prompt_word(word: str) -> list[str]:
    store.add_prompt_word(word)
    return store.prompt_words()


@app.delete("/api/prompt/{word}")
def remove_prompt_word(word: str) -> list[str]:
    store.remove_prompt_word(word)
    return store.prompt_words()
