"""Transcript history + context words in SQLite (stdlib). One connection
per call keeps it trivially thread-safe across the hotkey worker and the
web server threads — at dictation rates, connection cost is irrelevant.

Context words are user-managed vocabulary (names, jargon) appended to
whisper's initial_prompt so they spell correctly. Managed from the web UI.
"""

import sqlite3
import time

from . import config

_SCHEMA = """
CREATE TABLE IF NOT EXISTS transcripts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at REAL NOT NULL,
    duration_s REAL NOT NULL,
    raw TEXT NOT NULL,
    text TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS prompt_words (
    word TEXT PRIMARY KEY,
    added_at REAL NOT NULL
);
"""


def _conn() -> sqlite3.Connection:
    conn = sqlite3.connect(config.DB_PATH)
    conn.executescript(_SCHEMA)
    return conn


def save(raw: str, text: str, duration_s: float) -> None:
    with _conn() as conn:
        conn.execute(
            "INSERT INTO transcripts (created_at, duration_s, raw, text) VALUES (?, ?, ?, ?)",
            (time.time(), round(duration_s, 2), raw, text),
        )


def recent(limit: int = 200) -> list[dict]:
    with _conn() as conn:
        rows = conn.execute(
            "SELECT id, created_at, duration_s, raw, text FROM transcripts"
            " ORDER BY id DESC LIMIT ?",
            (limit,),
        ).fetchall()
    return [
        {"id": r[0], "created_at": r[1], "duration_s": r[2], "raw": r[3], "text": r[4]}
        for r in rows
    ]


def prompt_words() -> list[str]:
    with _conn() as conn:
        rows = conn.execute(
            "SELECT word FROM prompt_words ORDER BY added_at"
        ).fetchall()
    return [r[0] for r in rows]


def add_prompt_word(word: str) -> None:
    word = word.strip()
    if not word:
        return
    with _conn() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO prompt_words (word, added_at) VALUES (?, ?)",
            (word, time.time()),
        )


def remove_prompt_word(word: str) -> None:
    with _conn() as conn:
        conn.execute("DELETE FROM prompt_words WHERE word = ?", (word,))
