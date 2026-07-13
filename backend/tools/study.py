"""Study tracker (Phase 8): manual start/stop sessions, daily/weekly stats.

Voice/chat/UI all land on the same tools. Sessions attribute their full
duration to the day they started (simple, predictable). A forgotten open
session is capped at MAX_SESSION_H and auto-closed by the daily scheduler job.
Passive window tracking is deliberately NOT here — opt-in, later, visible.
"""

import logging
import time
from datetime import datetime, timedelta

import db
import events
from tools.registry import READ, tool

log = logging.getLogger("jarvis.study")

MAX_SESSION_H = 12

SCHEMA = """
CREATE TABLE IF NOT EXISTS study_sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    started_at REAL NOT NULL,
    ended_at REAL,
    note TEXT NOT NULL DEFAULT ''
);
"""


def init() -> None:
    with db.connect() as conn:
        conn.executescript(SCHEMA)


def _open_session(conn) -> dict | None:
    row = conn.execute(
        "SELECT id, started_at, note FROM study_sessions WHERE ended_at IS NULL "
        "ORDER BY id DESC LIMIT 1"
    ).fetchone()
    return dict(row) if row else None


def _duration_h(started: float, ended: float | None) -> float:
    return min((ended or time.time()) - started, MAX_SESSION_H * 3600) / 3600


@tool(
    "study_start",
    "Start a study session timer. Optional note for what is being studied.",
    {
        "type": "object",
        "properties": {"note": {"type": "string", "description": "subject/topic (optional)"}},
    },
    READ,
)
async def study_start(note: str = "") -> dict:
    with db.connect() as conn:
        if s := _open_session(conn):
            return {
                "error": "a session is already running",
                "since": s["started_at"],
                "note": s["note"],
            }
        cur = conn.execute(
            "INSERT INTO study_sessions (started_at, note) VALUES (?,?)", (time.time(), note)
        )
    events.emit("study.session.started", {"id": cur.lastrowid, "note": note})
    return {"started": True, "session_id": cur.lastrowid, "note": note}


@tool(
    "study_stop",
    "Stop the running study session timer and report its length.",
    {"type": "object", "properties": {}},
    READ,
)
async def study_stop() -> dict:
    now = time.time()
    with db.connect() as conn:
        s = _open_session(conn)
        if not s:
            return {"error": "no session running"}
        conn.execute("UPDATE study_sessions SET ended_at=? WHERE id=?", (now, s["id"]))
    hours = _duration_h(s["started_at"], now)
    events.emit(
        "study.session.finished", {"id": s["id"], "hours": round(hours, 2), "note": s["note"]}
    )
    return {"stopped": True, "hours": round(hours, 2), "note": s["note"]}


@tool(
    "study_status",
    "Report the study timer state and today's / this week's study hours.",
    {"type": "object", "properties": {}},
    READ,
)
async def study_status() -> dict:
    return stats()


def stats() -> dict:
    """Panel numbers: today/week hours, per-day hours for the current ISO week
    (Monday first), and whether a session is running."""
    now = datetime.now()
    monday = (now - timedelta(days=now.weekday())).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    today = now.replace(hour=0, minute=0, second=0, microsecond=0)
    with db.connect() as conn:
        rows = conn.execute(
            "SELECT started_at, ended_at, note FROM study_sessions WHERE started_at >= ?",
            (monday.timestamp(),),
        ).fetchall()
        active = _open_session(conn)
    days = [0.0] * 7
    for r in rows:
        d = datetime.fromtimestamp(r["started_at"])
        days[d.weekday()] += _duration_h(r["started_at"], r["ended_at"])
    today_h = days[today.weekday()]
    return {
        "today_h": round(today_h, 2),
        "week_h": round(sum(days), 2),
        "days": [round(h, 2) for h in days],
        "active": active is not None,
        "active_since": active["started_at"] if active else None,
        "active_note": active["note"] if active else None,
    }


def close_stale_sessions() -> int:
    """Daily job: close sessions left running longer than MAX_SESSION_H."""
    cutoff = time.time() - MAX_SESSION_H * 3600
    with db.connect() as conn:
        rows = conn.execute(
            "SELECT id, started_at FROM study_sessions WHERE ended_at IS NULL AND started_at < ?",
            (cutoff,),
        ).fetchall()
        for r in rows:
            conn.execute(
                "UPDATE study_sessions SET ended_at=? WHERE id=?",
                (r["started_at"] + MAX_SESSION_H * 3600, r["id"]),
            )
    if rows:
        log.info("closed %d stale study session(s)", len(rows))
    return len(rows)
