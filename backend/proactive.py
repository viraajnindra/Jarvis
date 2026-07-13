"""Proactive rules (Phase 8): morning brief + due-tomorrow alert.

Suggestions only — these compose text and notify; they never take actions.
Deterministic SQL + formatting, no LLM: a brief must fire reliably at 7am
whether or not models are up.
"""

import logging
from datetime import datetime

import db
import events
from tools import canvas, study

log = logging.getLogger("jarvis.proactive")


def _due_assignments(within_hours: int) -> list[dict]:
    with db.connect() as conn:
        rows = conn.execute(
            "SELECT a.name, a.due_at, a.points, c.name AS course "
            "FROM canvas_assignments a JOIN canvas_courses c ON c.id = a.course_id "
            "WHERE a.submitted=0 AND a.due_at IS NOT NULL "
            "AND datetime(a.due_at) BETWEEN datetime('now') "
            f"AND datetime('now', '+{int(within_hours)} hours') "
            "ORDER BY datetime(a.due_at)"
        ).fetchall()
    return [dict(r) for r in rows]


def _fmt_due(a: dict) -> str:
    due = a["due_at"][:16].replace("T", " ") if a["due_at"] else "?"
    pts = f", {a['points']:g} pts" if a["points"] else ""
    return f"- {a['name']} ({a['course']}{pts}) — due {due} UTC"


async def morning_brief() -> str:
    lines: list[str] = [f"Good morning, Boss. {datetime.now():%A, %B %d}."]

    due_week = _due_assignments(7 * 24)
    if due_week:
        n_24 = len(_due_assignments(24))
        lines.append(f"\n{len(due_week)} assignment(s) due this week"
                     + (f", {n_24} within 24h:" if n_24 else ":"))
        lines += [_fmt_due(a) for a in due_week[:6]]
    elif canvas.configured():
        lines.append("\nNo unsubmitted assignments due this week.")

    s = study.stats()
    if s["week_h"]:
        lines.append(f"\nStudy so far this week: {s['week_h']:g}h.")

    counts = canvas.panel_counts()
    if counts and counts["announcements"]:
        lines.append(f"{counts['announcements']} unread Canvas announcement(s).")

    text = "\n".join(lines)
    events.notify("Morning brief", text)
    events.emit("brief.morning", {"due_week": len(due_week)})
    log.info("morning brief sent (%d due this week)", len(due_week))
    return text


async def due_tomorrow_alert() -> str | None:
    """Evening check: unsubmitted work due within 36h -> one alert, or None."""
    due = _due_assignments(36)
    if not due:
        return None
    text = "Due soon and not submitted:\n" + "\n".join(_fmt_due(a) for a in due[:6])
    events.notify("Assignments due tomorrow", text)
    events.emit("brief.due_alert", {"count": len(due)})
    log.info("due-tomorrow alert sent (%d)", len(due))
    return text
