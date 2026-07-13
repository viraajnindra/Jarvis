"""Approval queue + append-only audit log.

The model proposes; this module decides. Tier enforcement happens HERE, in code,
before any tool executes — never in the prompt. ACT and SENSITIVE tools block on
an approval_request round-trip to the UI; timeout auto-cancels.
"""

import asyncio
import json
import logging
import time
import uuid
from collections.abc import Awaitable, Callable

import db

log = logging.getLogger("jarvis.approval")

APPROVAL_TIMEOUT_S = 120

AUDIT_SCHEMA = """
CREATE TABLE IF NOT EXISTS audit_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tool TEXT NOT NULL,
    args TEXT NOT NULL,
    tier TEXT NOT NULL,
    outcome TEXT NOT NULL CHECK (outcome IN
        ('executed','denied','cancelled','timeout','error')),
    detail TEXT,
    created_at REAL NOT NULL
);
"""

# main.py registers a broadcaster so approval requests reach every connected UI.
_broadcast: Callable[[dict], Awaitable[None]] | None = None
_pending: dict[str, asyncio.Future] = {}


def init() -> None:
    with db.connect() as conn:
        conn.executescript(AUDIT_SCHEMA)


def set_broadcaster(fn: Callable[[dict], Awaitable[None]]) -> None:
    global _broadcast
    _broadcast = fn


def audit(tool: str, args: dict, tier: str, outcome: str, detail: str = "") -> None:
    with db.connect() as conn:
        conn.execute(
            "INSERT INTO audit_log (tool, args, tier, outcome, detail, created_at) "
            "VALUES (?,?,?,?,?,?)",
            (tool, json.dumps(args, default=str), tier, outcome, detail[:500], time.time()),
        )


def audit_rows(limit: int = 50) -> list[dict]:
    with db.connect() as conn:
        rows = conn.execute(
            "SELECT * FROM audit_log ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()
    return [dict(r) for r in rows]


async def request_approval(action: str, target: str, detail: str = "") -> bool:
    """Send an approval card to the UI and block until confirm/cancel/timeout."""
    if _broadcast is None:
        log.error("no broadcaster registered; denying by default")
        return False
    req_id = uuid.uuid4().hex[:12]
    fut: asyncio.Future = asyncio.get_running_loop().create_future()
    _pending[req_id] = fut
    await _broadcast(
        {
            "type": "approval_request",
            "id": req_id,
            "action": action,
            "target": target,
            "detail": detail,
        }
    )
    try:
        return bool(await asyncio.wait_for(fut, timeout=APPROVAL_TIMEOUT_S))
    except asyncio.TimeoutError:
        await _broadcast({"type": "approval_expired", "id": req_id})
        return False
    finally:
        _pending.pop(req_id, None)


def deny_all() -> int:
    """Emergency stop: deny every pending approval immediately. Returns count."""
    n = 0
    for fut in list(_pending.values()):
        if not fut.done():
            fut.set_result(False)
            n += 1
    return n


def resolve(req_id: str, approved: bool) -> bool:
    """Called from the WS handler on approval_response. Returns False if unknown/expired."""
    fut = _pending.get(req_id)
    if fut is None or fut.done():
        return False
    fut.set_result(approved)
    return True
