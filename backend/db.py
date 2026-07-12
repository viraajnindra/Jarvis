"""SQLite persistence: conversations, messages, Gemini call log."""

import sqlite3
import time
import uuid

import config

SCHEMA = """
CREATE TABLE IF NOT EXISTS conversations (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL DEFAULT 'New conversation',
    created_at REAL NOT NULL,
    updated_at REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    conversation_id TEXT NOT NULL REFERENCES conversations(id),
    role TEXT NOT NULL CHECK (role IN ('system','user','assistant','tool')),
    content TEXT NOT NULL,
    created_at REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_messages_conv ON messages(conversation_id, id);
CREATE TABLE IF NOT EXISTS gemini_calls (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    reason TEXT NOT NULL,
    created_at REAL NOT NULL
);
"""


def connect() -> sqlite3.Connection:
    conn = sqlite3.connect(config.DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init() -> None:
    with connect() as conn:
        conn.executescript(SCHEMA)


def create_conversation(title: str = "New conversation") -> str:
    conv_id = uuid.uuid4().hex
    now = time.time()
    with connect() as conn:
        conn.execute(
            "INSERT INTO conversations (id, title, created_at, updated_at) VALUES (?,?,?,?)",
            (conv_id, title, now, now),
        )
    return conv_id


def conversation_exists(conv_id: str) -> bool:
    with connect() as conn:
        row = conn.execute("SELECT 1 FROM conversations WHERE id=?", (conv_id,)).fetchone()
    return row is not None


def add_message(conv_id: str, role: str, content: str) -> int:
    now = time.time()
    with connect() as conn:
        cur = conn.execute(
            "INSERT INTO messages (conversation_id, role, content, created_at) VALUES (?,?,?,?)",
            (conv_id, role, content, now),
        )
        conn.execute("UPDATE conversations SET updated_at=? WHERE id=?", (now, conv_id))
    return cur.lastrowid


def get_messages(conv_id: str) -> list[dict]:
    with connect() as conn:
        rows = conn.execute(
            "SELECT role, content FROM messages WHERE conversation_id=? ORDER BY id",
            (conv_id,),
        ).fetchall()
    return [{"role": r["role"], "content": r["content"]} for r in rows]


def delete_last_assistant_message(conv_id: str) -> None:
    """Drop the trailing assistant message so the turn can be regenerated."""
    with connect() as conn:
        row = conn.execute(
            "SELECT id, role FROM messages WHERE conversation_id=? ORDER BY id DESC LIMIT 1",
            (conv_id,),
        ).fetchone()
        if row and row["role"] == "assistant":
            conn.execute("DELETE FROM messages WHERE id=?", (row["id"],))


def log_gemini_call(reason: str) -> None:
    with connect() as conn:
        conn.execute(
            "INSERT INTO gemini_calls (reason, created_at) VALUES (?,?)", (reason, time.time())
        )


def gemini_calls_today() -> int:
    day_start = time.time() - (time.time() % 86400)
    with connect() as conn:
        row = conn.execute(
            "SELECT COUNT(*) AS n FROM gemini_calls WHERE created_at >= ?", (day_start,)
        ).fetchone()
    return row["n"]
