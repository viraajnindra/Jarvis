"""APScheduler wrapper: periodic Canvas sync now; metrics polling + proactive
briefs join here in Phase 8."""

import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler

import config
from tools import canvas

log = logging.getLogger("jarvis.scheduler")

_sched: AsyncIOScheduler | None = None


async def _canvas_job() -> None:
    if not canvas.configured():
        return
    try:
        await canvas.sync()
    except Exception:  # noqa: BLE001
        log.exception("scheduled canvas sync failed")


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
    _sched.start()
    log.info("scheduler started (canvas sync every %ds)", config.CANVAS_SYNC_INTERVAL_S)
