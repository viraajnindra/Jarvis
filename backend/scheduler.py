"""APScheduler wrapper: Canvas sync, metric polling, proactive briefs,
study-session hygiene."""

import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler

import config
import metrics
import proactive
from tools import canvas, study

log = logging.getLogger("jarvis.scheduler")

_sched: AsyncIOScheduler | None = None


async def _canvas_job() -> None:
    if not canvas.configured():
        return
    try:
        await canvas.sync()
    except Exception:  # noqa: BLE001
        log.exception("scheduled canvas sync failed")


async def _metric_job(name: str) -> None:
    result = await metrics.poll_source(name)
    log.info("metric poll %s: %s", name, result)


async def _brief_job() -> None:
    try:
        await proactive.morning_brief()
    except Exception:  # noqa: BLE001
        log.exception("morning brief failed")


async def _due_alert_job() -> None:
    try:
        await proactive.due_tomorrow_alert()
    except Exception:  # noqa: BLE001
        log.exception("due-tomorrow alert failed")


def start() -> None:
    global _sched
    if _sched is not None:
        return
    _sched = AsyncIOScheduler()
    _sched.add_job(
        _canvas_job,
        "interval",
        seconds=config.CANVAS_SYNC_INTERVAL_S,
        id="canvas_sync",
        next_run_time=None,  # first run scheduled explicitly at startup
    )
    for name, src in metrics.SOURCES.items():
        _sched.add_job(
            _metric_job,
            "interval",
            seconds=src.interval_s,
            id=f"metric_{name}",
            args=[name],
        )
    _sched.add_job(_brief_job, "cron", hour=config.BRIEF_HOUR, minute=0, id="morning_brief")
    _sched.add_job(
        _due_alert_job, "cron", hour=config.DUE_ALERT_HOUR, minute=0, id="due_alert"
    )
    _sched.add_job(study.close_stale_sessions, "cron", hour=4, minute=0, id="study_hygiene")
    _sched.start()
    log.info(
        "scheduler started (canvas %ds, %d metric source(s), brief %02d:00, due alert %02d:00)",
        config.CANVAS_SYNC_INTERVAL_S,
        len(metrics.SOURCES),
        config.BRIEF_HOUR,
        config.DUE_ALERT_HOUR,
    )
