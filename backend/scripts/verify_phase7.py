"""Phase 7 verification: research/video tools register, helpers behave, and (if the
network / Ollama are up) the live paths work.

Usage: uv run scripts/verify_phase7.py [--live]
  --live also runs a small end-to-end deep_research (slow, uses searches + models)
"""

import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import db  # noqa: E402
import tools  # noqa: E402
from tools import research, video  # noqa: E402

PASS = 0


def ok(label: str, cond: bool, extra: str = "") -> None:
    global PASS
    print(("PASS  " if cond else "FAIL  ") + label + (f"  ({extra})" if extra else ""))
    if not cond:
        sys.exit(1)
    PASS += 1


async def main() -> None:
    db.init()
    tools.load_all()
    reg = tools.REGISTRY

    # Registration + tiers (all READ: network reads + internal writes only)
    for name in ("deep_research", "read_and_learn", "summarize_video"):
        ok(f"tool registered: {name}", name in reg)
        ok(f"{name} is READ", reg[name].tier == "READ")

    # YouTube URL parsing
    cases = {
        "https://www.youtube.com/watch?v=dQw4w9WgXcQ": "dQw4w9WgXcQ",
        "https://youtu.be/dQw4w9WgXcQ?t=10": "dQw4w9WgXcQ",
        "https://www.youtube.com/shorts/abcdefghijk": "abcdefghijk",
        "https://www.youtube.com/watch?list=x&v=dQw4w9WgXcQ": "dQw4w9WgXcQ",
        "https://example.com/watch?v=nope": None,
    }
    ok("video_id parsing", all(video.video_id(u) == want for u, want in cases.items()))

    # Timestamp grouping
    entries = [(0.0, "a"), (20.0, "b"), (50.0, "c"), (95.0, "d")]
    ts = video._timestamped(entries, block_s=45)
    ok("timestamped grouping", ts.startswith("[0:00] a b c") and "[1:35] d" in ts, repr(ts))
    ok("mmss over an hour", video._mmss(3725) == "1:02:05")

    # JSON extraction from model chatter
    ok(
        "json block parsing",
        research._json_block('here you go:\n```json\n["q1", "q2"]\n```') == ["q1", "q2"]
        and research._json_block("no json here") is None,
    )

    # Report writer
    path = research.save_report(
        "test question?", "# Test\nbody [1]", [{"n": 1, "title": "t", "url": "u"}]
    )
    p = Path(path)
    ok("report saved", p.exists() and p.read_text(encoding="utf-8").startswith("# Test"))
    src_pkg = p.with_suffix("").with_suffix(".sources.json")
    ok("source package saved", src_pkg.exists() and json.loads(src_pkg.read_text())[0]["n"] == 1)
    p.unlink()
    src_pkg.unlink()

    # Live network: fetch + strip
    try:
        page = await research.fetch_source("https://example.com")
        ok("fetch_source html", "Example Domain" in page["title"], page["title"])
    except Exception as e:  # noqa: BLE001
        print(f"SKIP  fetch_source (network down? {e})")

    # Live transcript (graceful if YouTube blocks or captions change)
    try:
        entries = await asyncio.to_thread(video._fetch_transcript, "jNQXAC9IVRw")  # "Me at the zoo"
        ok("youtube transcript fetch", len(entries) > 0, f"{len(entries)} snippets")
    except Exception as e:  # noqa: BLE001
        print(f"SKIP  youtube transcript ({e})")

    if "--live" in sys.argv:
        print("\nRunning live deep_research (this takes a few minutes)...")
        r = await reg["deep_research"].fn(question="What is sqlite-vec?", max_sources=3)
        ok("live deep_research", "report_path" in r, str(r)[:200])
        print(f"  report: {r.get('report_path')}  facts stored: {r.get('facts_stored')}")

    print(f"\n{PASS} checks passed")


if __name__ == "__main__":
    asyncio.run(main())
