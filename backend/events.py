"""Event system (Phase 8): append-only event log + WS broadcast.

Names in use: study.session.started/finished, canvas.assignment.synced,
research.report.completed, message.sent, project.metric.recorded,
brief.morning, brief.due_alert. Dashboard panels and proactive rules derive
from these rather than poking modules directly.

emit() is safe from sync or async code: the row always lands; the broadcast
is scheduled only when an event loop is running.
"""

import asyncio
import json
import logging
import time
from collections.abc import Awaitable, Callable

import db

log = logging.getLogger("jarvis.events")

SCHEMA = """
CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    payload TEXT,
    created_at REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_events_name ON events(name, id);
"""

_broadcast: Callable[[dict], Awaitable[None]] | None = None


def init() -> None:
    with db.connect() as conn:
        conn.executescript(SCHEMA)


def set_broadcaster(fn: Callable[[dict], Awaitable[None]]) -> None:
    global _broadcast
    _broadcast = fn


def emit(name: str, payload: dict | None = None) -> None:
    with db.connect() as conn:
        conn.execute(
            "INSERT INTO events (name, payload, created_at) VALUES (?,?,?)",
            (name, json.dumps(payload or {}, default=str), time.time()),
        )
    log.info("event %s %s", name, payload or {})
    _push({"type": "event", "name": name, "payload": payload or {}})


def notify(title: str, body: str) -> None:
    """Proactive suggestion to the user: broadcast only, never an action."""
    _push({"type": "notification", "title": title, "body": body})


def _push(payload: dict) -> None:
    if _broadcast is None:
        return
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        return  # no loop (tests, scripts): row is stored, broadcast skipped
    loop.create_task(_broadcast(payload))


def recent(limit: int = 50, name: str | None = None) -> list[dict]:
    q = "SELECT id, name, payload, created_at FROM events"
    args: tuple = ()
    if name:
        q += " WHERE name = ?"
        args = (name,)
    q += " ORDER BY id DESC LIMIT ?"
    with db.connect() as conn:
        rows = conn.execute(q, (*args, limit)).fetchall()
    return [
        {**dict(r), "payload": json.loads(r["payload"] or "{}")} for r in rows
    ]
