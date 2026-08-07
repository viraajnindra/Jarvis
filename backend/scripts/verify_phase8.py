"""Phase 8 verification: events, study tracker, metric sources, proactive briefs,
scheduler jobs. Runs against a scratch DB — the real one is untouched.

Usage: uv run scripts/verify_phase8.py
"""

import asyncio
import os
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ["JARVIS_DATA_DIR"] = tempfile.mkdtemp(prefix="jarvis_p8_")

import db  # noqa: E402
import events  # noqa: E402
import metrics  # noqa: E402
import proactive  # noqa: E402
import scheduler  # noqa: E402
import tools  # noqa: E402
from tools import study  # noqa: E402

PASS = 0


def ok(label: str, cond: bool, extra: str = "") -> None:
    global PASS
    print(("PASS  " if cond else "FAIL  ") + label + (f"  ({extra})" if extra else ""))
    if not cond:
        sys.exit(1)
    PASS += 1


async def main() -> None:
    db.init()
    events.init()
    tools.load_all()
    reg = tools.REGISTRY

    # Study tools registered, READ tier (voice-friendly, no approval friction)
    for name in ("study_start", "study_stop", "study_status"):
        ok(f"tool registered: {name}", name in reg and reg[name].tier == "READ")

    # Study session lifecycle + events
    r = await study.study_start(note="bio")
    ok("study start", r.get("started") is True)
    r = await study.study_start()
    ok("double start blocked", "error" in r)
    r = await study.study_stop()
    ok("study stop", r.get("stopped") is True and r["note"] == "bio")
    r = await study.study_stop()
    ok("stop without session blocked", "error" in r)
    names = [e["name"] for e in events.recent(10)]
    ok(
        "study events emitted",
        "study.session.started" in names and "study.session.finished" in names,
    )

    # Stats shape
    s = study.stats()
    ok("stats shape", len(s["days"]) == 7 and s["active"] is False and "week_h" in s)

    # Stale session hygiene
    with db.connect() as conn:
        conn.execute(
            "INSERT INTO study_sessions (started_at, note) VALUES (?, 'stale')",
            (time.time() - 15 * 3600,),
        )
    ok("stale session closed", study.close_stale_sessions() == 1)

    # Metrics: record -> event -> latest -> series
    metrics.record("project.views", 100)
    metrics.record("project.views", 150)
    panel = metrics.latest("project.")
    ok("latest metric value", panel["project.views"]["value"] == 150)
    ok("metric series", len(metrics.series("project.views", 1)) == 2)
    ok(
        "metric event emitted",
        any(e["name"] == "project.metric.recorded" for e in events.recent(5)),
    )
    ok("unknown source rejected", "error" in await metrics.poll_source("nope"))

    # Proactive: quiet without data, fires with a due assignment
    ok("due alert quiet with no data", await proactive.due_tomorrow_alert() is None)
    with db.connect() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO canvas_courses (id,name,code,synced_at) VALUES (1,'BIO 301','BIO',?)",
            (time.time(),),
        )
        conn.execute(
            "INSERT OR REPLACE INTO canvas_assignments "
            "(id,course_id,name,due_at,points,submitted,graded,html_url,synced_at) "
            "VALUES (1,1,'Lab report',?,50,0,0,'',?)",
            (
                time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(time.time() + 20 * 3600)),
                time.time(),
            ),
        )
    alert = await proactive.due_tomorrow_alert()
    ok("due alert fires", alert is not None and "Lab report" in alert)
    brief = await proactive.morning_brief()
    ok("morning brief lists due work", "Lab report" in brief and "BIO 301" in brief)
    names = [e["name"] for e in events.recent(5)]
    ok("brief events emitted", "brief.morning" in names and "brief.due_alert" in names)

    # Scheduler wires all Phase 8 jobs
    scheduler.start()
    jobs = {j.id for j in scheduler._sched.get_jobs()}
    ok(
        "scheduler jobs",
        {"canvas_sync", "morning_brief", "due_alert", "study_hygiene"}
        <= jobs,
        str(sorted(jobs)),
    )
    scheduler._sched.shutdown(wait=False)

    print(f"\n{PASS} checks passed")


if __name__ == "__main__":
    asyncio.run(main())
