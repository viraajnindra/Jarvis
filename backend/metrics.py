"""Generic persisted metric utilities and optional polling sources."""

import logging
import time
from dataclasses import dataclass
from typing import Awaitable, Callable

import db
import events

log = logging.getLogger("jarvis.metrics")


@dataclass
class MetricSource:
    name: str
    poll: Callable[[], Awaitable[dict[str, float] | None]]
    interval_s: int
    configured: Callable[[], bool] = lambda: True


SOURCES: dict[str, MetricSource] = {}


def register(source: MetricSource) -> None:
    SOURCES[source.name] = source


def record(metric: str, value: float, meta: str | None = None) -> None:
    with db.connect() as conn:
        conn.execute(
            "INSERT INTO metrics_log (metric, value, meta, created_at) VALUES (?,?,?,?)",
            (metric, value, meta, time.time()),
        )
    events.emit("project.metric.recorded", {"metric": metric, "value": value})


def latest(prefix: str) -> dict:
    """Most recent value per metric under a prefix, plus its timestamp."""
    with db.connect() as conn:
        rows = conn.execute(
            "SELECT metric, value, MAX(created_at) AS at FROM metrics_log "
            "WHERE metric LIKE ? GROUP BY metric",
            (prefix + "%",),
        ).fetchall()
    return {r["metric"]: {"value": r["value"], "at": r["at"]} for r in rows}


def series(metric: str, days: int = 30) -> list[dict]:
    since = time.time() - days * 86400
    with db.connect() as conn:
        rows = conn.execute(
            "SELECT value, created_at FROM metrics_log WHERE metric=? AND created_at>=? "
            "ORDER BY created_at",
            (metric, since),
        ).fetchall()
    return [dict(r) for r in rows]


async def poll_source(name: str) -> dict:
    src = SOURCES.get(name)
    if src is None:
        return {"error": f"unknown metric source: {name}"}
    if not src.configured():
        return {"skipped": "not configured"}
    try:
        values = await src.poll()
    except Exception as e:  # noqa: BLE001 - one bad poll must not kill the scheduler
        log.exception("metric source %s failed", name)
        return {"error": str(e)}
    if not values:
        return {"error": "poll returned nothing"}
    for metric, value in values.items():
        record(f"{name}.{metric}", float(value))
    return {"recorded": values}
