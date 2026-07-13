"""Phase 9 verification: narrow computer-control tools + emergency stop.

Usage: uv run scripts/verify_phase9.py
"""

import asyncio
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ["JARVIS_DATA_DIR"] = tempfile.mkdtemp(prefix="jarvis_p9_")

import approval  # noqa: E402
import db  # noqa: E402
import events  # noqa: E402
import tools  # noqa: E402
from tools import registry, system  # noqa: E402

PASS = 0


def ok(label: str, cond: bool, extra: str = "") -> None:
    global PASS
    print(("PASS  " if cond else "FAIL  ") + label + (f"  ({extra})" if extra else ""))
    if not cond:
        sys.exit(1)
    PASS += 1


async def main() -> None:
    db.init()
    approval.init()
    events.init()
    tools.load_all()
    reg = tools.REGISTRY

    # Registration + tiers
    for name, tier in (
        ("open_file", "ACT"),
        ("move_file", "ACT"),
        ("clipboard_write", "ACT"),
        ("notification_show", "READ"),
        ("launch_app", "ACT"),
    ):
        ok(f"{name} registered as {tier}", name in reg and reg[name].tier == tier)

    # No deletion or blind-input tool exists at all
    ok("no delete tool", not any("delete" in n or "remove" in n for n in reg))
    ok("no input-injection tool", not any("click" in n or "keypress" in n for n in reg))

    # Workspace scoping: escapes rejected for move/open
    ok(
        "move_file blocks escape (src)",
        "escapes workspace" in str(_call(system.move_file, src="../x.txt", dst="y.txt")),
    )
    ok(
        "move_file blocks escape (dst)",
        "escapes workspace" in str(_call(system.move_file, src="a.txt", dst="../../y.txt")),
    )

    # move_file: happy path + no-overwrite
    (system.WORKSPACE / "a.txt").write_text("hello")
    r = system.move_file(src="a.txt", dst="sub/b.txt")
    ok("move_file moves", r.get("moved") == "a.txt" and (system.WORKSPACE / "sub/b.txt").is_file())
    (system.WORKSPACE / "a2.txt").write_text("x")
    r = system.move_file(src="a2.txt", dst="sub/b.txt")
    ok("move_file refuses overwrite", "destination exists" in r.get("error", ""))

    # clipboard roundtrip
    import pyperclip

    prev = pyperclip.paste()
    r = system.clipboard_write(text="jarvis-p9-test")
    ok("clipboard write", r.get("copied") and pyperclip.paste() == "jarvis-p9-test")
    pyperclip.copy(prev)  # restore the user's clipboard

    # notification_show emits a broadcast-only suggestion (no event loop needed here)
    r = system.notification_show(title="t", body="b")
    ok("notification_show", r.get("shown") is True)

    # Emergency stop: blocks ALL tiers at the choke point, audited
    registry.engage_emergency_stop()
    r = await tools.execute_tool("list_files", {})  # READ tool
    ok("emergency stop blocks READ tool", "cancelled" in r, str(r)[:80])
    r = await tools.execute_tool("open_file", {"path": "sub/b.txt"})  # ACT tool
    ok("emergency stop blocks ACT tool", "cancelled" in r)
    rows = approval.audit_rows(5)
    ok(
        "emergency stop audited",
        any(row["outcome"] == "cancelled" and "emergency" in (row["detail"] or "") for row in rows),
    )

    # deny_all resolves pending approvals as denied
    fut = asyncio.get_running_loop().create_future()
    approval._pending["test123"] = fut
    n = approval.deny_all()
    ok("deny_all denies pending", n == 1 and fut.result() is False)
    approval._pending.pop("test123", None)

    # Clear -> tools run again
    registry.clear_emergency_stop()
    r = await tools.execute_tool("list_files", {})
    ok("cleared: tools run again", "files" in r)

    print(f"\n{PASS} checks passed")


def _call(fn, **kw) -> dict:
    try:
        return fn(**kw)
    except ValueError as e:
        return {"error": str(e)}


if __name__ == "__main__":
    asyncio.run(main())
