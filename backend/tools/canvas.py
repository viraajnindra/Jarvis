"""Canvas LMS integration (read-only). Token from Credential Manager.

Boundary (non-negotiable, from PLAN.md): Jarvis never submits schoolwork.
Only read tools exist here — there is deliberately no submit/upload tool.

Normalized copies land in local tables so telemetry and prioritization work
offline; sync runs on startup and every CANVAS_SYNC_INTERVAL_S.
"""

import logging
import time

import httpx
import keyring

import config
import db
from tools.registry import READ, tool

log = logging.getLogger("jarvis.canvas")

SCHEMA = """
CREATE TABLE IF NOT EXISTS canvas_courses (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    code TEXT,
    synced_at REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS canvas_assignments (
    id INTEGER PRIMARY KEY,
    course_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    due_at TEXT,
    points REAL,
    submitted INTEGER NOT NULL DEFAULT 0,
    graded INTEGER NOT NULL DEFAULT 0,
    html_url TEXT,
    synced_at REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS canvas_announcements (
    id INTEGER PRIMARY KEY,
    course_id INTEGER,
    title TEXT NOT NULL,
    posted_at TEXT,
    read INTEGER NOT NULL DEFAULT 0,
    synced_at REAL NOT NULL
);
"""


def init() -> None:
    with db.connect() as conn:
        conn.executescript(SCHEMA)


def _token() -> str | None:
    return keyring.get_password(config.KEYRING_SERVICE, "canvas_token")


def configured() -> bool:
    return bool(config.CANVAS_BASE_URL and _token())


async def _get(path: str, params: dict | None = None) -> list | dict:
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.get(
            f"{config.CANVAS_BASE_URL}/api/v1{path}",
            headers={"Authorization": f"Bearer {_token()}"},
            params={"per_page": 50, **(params or {})},
        )
        r.raise_for_status()
        return r.json()


async def sync() -> dict:
    """Pull courses, assignments, announcements into local tables."""
    if not configured():
        return {"error": "Canvas not configured (set JARVIS_CANVAS_URL + store canvas_token)"}
    now = time.time()
    courses = await _get("/courses", {"enrollment_state": "active"})
    with db.connect() as conn:
        for c in courses:
            if "name" not in c:
                continue
            conn.execute(
                "INSERT OR REPLACE INTO canvas_courses (id, name, code, synced_at) VALUES (?,?,?,?)",
                (c["id"], c["name"], c.get("course_code"), now),
            )
    n_assign = 0
    for c in courses:
        if "name" not in c:
            continue
        try:
            assignments = await _get(
                f"/courses/{c['id']}/assignments", {"include[]": "submission"}
            )
        except httpx.HTTPStatusError:
            continue
        with db.connect() as conn:
            for a in assignments:
                sub = a.get("submission") or {}
                conn.execute(
                    "INSERT OR REPLACE INTO canvas_assignments "
                    "(id, course_id, name, due_at, points, submitted, graded, html_url, synced_at) "
                    "VALUES (?,?,?,?,?,?,?,?,?)",
                    (
                        a["id"],
                        c["id"],
                        a["name"],
                        a.get("due_at"),
                        a.get("points_possible"),
                        1 if sub.get("submitted_at") else 0,
                        1 if sub.get("graded_at") else 0,
                        a.get("html_url"),
                        now,
                    ),
                )
                n_assign += 1
    try:
        anns = await _get(
            "/announcements",
            {"context_codes[]": [f"course_{c['id']}" for c in courses if "name" in c]},
        )
        with db.connect() as conn:
            for an in anns:
                conn.execute(
                    "INSERT OR REPLACE INTO canvas_announcements "
                    "(id, course_id, title, posted_at, read, synced_at) VALUES (?,?,?,?,?,?)",
                    (
                        an["id"],
                        an.get("course_id"),
                        an["title"],
                        an.get("posted_at"),
                        1 if an.get("read_state") == "read" else 0,
                        now,
                    ),
                )
    except httpx.HTTPError:
        anns = []
    log.info("canvas sync: %d courses, %d assignments, %d announcements",
             len(courses), n_assign, len(anns))
    return {"courses": len(courses), "assignments": n_assign, "announcements": len(anns)}


def panel_counts() -> dict | None:
    """Numbers for the CANVAS OVERVIEW telemetry panel; None if never synced."""
    with db.connect() as conn:
        if not conn.execute("SELECT 1 FROM canvas_courses LIMIT 1").fetchone():
            return None
        due_soon = conn.execute(
            "SELECT COUNT(*) n FROM canvas_assignments WHERE submitted=0 AND due_at IS NOT NULL "
            "AND datetime(due_at) BETWEEN datetime('now') AND datetime('now', '+7 days')"
        ).fetchone()["n"]
        ungraded = conn.execute(
            "SELECT COUNT(*) n FROM canvas_assignments WHERE submitted=1 AND graded=0"
        ).fetchone()["n"]
        unread = conn.execute(
            "SELECT COUNT(*) n FROM canvas_announcements WHERE read=0"
        ).fetchone()["n"]
    return {"due_soon": due_soon, "ungraded": ungraded, "announcements": unread}


@tool(
    "canvas_courses",
    "List the user's active Canvas courses.",
    {"type": "object", "properties": {}},
    READ,
)
async def canvas_courses() -> dict:
    if not configured():
        return {"error": "Canvas not configured"}
    with db.connect() as conn:
        rows = conn.execute("SELECT id, name, code FROM canvas_courses").fetchall()
    if not rows:
        await sync()
        with db.connect() as conn:
            rows = conn.execute("SELECT id, name, code FROM canvas_courses").fetchall()
    return {"courses": [dict(r) for r in rows]}


@tool(
    "canvas_assignments",
    "List Canvas assignments with due dates and submission status. "
    "Use days_ahead to limit to upcoming ones.",
    {
        "type": "object",
        "properties": {
            "days_ahead": {"type": "integer", "description": "only due within N days (default all)"},
            "unsubmitted_only": {"type": "boolean"},
        },
    },
    READ,
)
async def canvas_assignments(days_ahead: int = 0, unsubmitted_only: bool = False) -> dict:
    if not configured():
        return {"error": "Canvas not configured"}
    q = (
        "SELECT a.name, a.due_at, a.points, a.submitted, a.graded, a.html_url, c.name AS course "
        "FROM canvas_assignments a JOIN canvas_courses c ON c.id = a.course_id WHERE 1=1"
    )
    if days_ahead:
        q += (
            " AND a.due_at IS NOT NULL AND datetime(a.due_at) BETWEEN datetime('now') "
            f"AND datetime('now', '+{int(days_ahead)} days')"
        )
    if unsubmitted_only:
        q += " AND a.submitted=0"
    q += " ORDER BY a.due_at IS NULL, datetime(a.due_at)"
    with db.connect() as conn:
        rows = conn.execute(q).fetchall()
    return {"assignments": [dict(r) for r in rows][:50]}


@tool(
    "canvas_sync",
    "Refresh Canvas data (courses, assignments, announcements) from the server now.",
    {"type": "object", "properties": {}},
    READ,
)
async def canvas_sync_tool() -> dict:
    return await sync()
