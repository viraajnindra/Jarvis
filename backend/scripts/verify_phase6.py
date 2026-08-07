"""Phase 6 verification: integrations register, degrade gracefully, and (if tokens
are present) hit the real APIs.

Usage: uv run scripts/verify_phase6.py
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import db  # noqa: E402
import tools  # noqa: E402
from tools import canvas, comms  # noqa: E402

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

    # Registration + tiers
    reg = tools.REGISTRY
    for name in (
        "canvas_assignments",
        "canvas_courses",
        "canvas_sync",
        "discord_send",
        "gmail_send",
        "gmail_get_vacation_settings",
        "gmail_list_messages",
        "gmail_search_messages",
        "gmail_read_message",
        "gmail_read_thread",
        "gmail_list_attachments",
        "gmail_download_attachment",
        "gmail_create_reply_draft",
        "gmail_send_reply",
        "gmail_list_filters",
        "gmail_create_filter",
        "gmail_delete_filter",
    ):
        ok(f"tool registered: {name}", name in reg)
    ok("gmail_send is SENSITIVE", reg["gmail_send"].tier == "SENSITIVE")
    ok("gmail vacation settings is READ", reg["gmail_get_vacation_settings"].tier == "READ")
    ok("gmail message listing is READ", reg["gmail_list_messages"].tier == "READ")
    ok("gmail message reading is READ", reg["gmail_read_message"].tier == "READ")
    ok("gmail replies are SENSITIVE", reg["gmail_send_reply"].tier == "SENSITIVE")
    ok("gmail drafts are SENSITIVE", reg["gmail_create_reply_draft"].tier == "SENSITIVE")
    ok("gmail filter changes are SENSITIVE", reg["gmail_create_filter"].tier == "SENSITIVE")
    ok("discord_send is SENSITIVE", reg["discord_send"].tier == "SENSITIVE")
    ok("canvas_assignments is READ", reg["canvas_assignments"].tier == "READ")

    # No submit tool exists — schoolwork boundary holds
    ok("no canvas submit tool", not any("submit" in n for n in reg))

    # Approval-card summaries expose the full payload for SENSITIVE sends
    action, target, detail = reg["gmail_send"].summary(
        {"to": "prof@uni.edu", "subject": "Question", "body": "Hello professor"}
    )
    ok("gmail card shows recipient", target == "prof@uni.edu")
    ok("gmail card shows full body", "Hello professor" in detail and "Question" in detail)

    # Graceful degradation when unconfigured
    if not canvas.configured():
        r = await reg["canvas_assignments"].fn(days_ahead=7)
        ok("canvas degrades cleanly", "error" in r, "not configured")
    else:
        r = await canvas.sync()
        ok("canvas live sync", "assignments" in r, str(r))
        counts = canvas.panel_counts()
        ok("canvas panel counts", counts is not None, str(counts))

    if not comms.gmail_configured():
        r = comms.gmail_send.__wrapped__ if hasattr(comms.gmail_send, "__wrapped__") else None
        # direct call returns error without creds
        res = comms.gmail_send(to="x@y.com", subject="s", body="b")
        ok("gmail degrades cleanly", "error" in res, "not configured")
        res = comms.gmail_get_vacation_settings()
        ok("gmail vacation settings degrades cleanly", "error" in res, "not configured")
        res = comms.gmail_list_messages()
        ok("gmail message listing degrades cleanly", "error" in res, "not configured")
        res = comms.gmail_read_message(message_id="example")
        ok("gmail message reading degrades cleanly", "error" in res, "not configured")
        res = comms.gmail_read_thread(thread_id="example")
        ok("gmail thread reading degrades cleanly", "error" in res, "not configured")
        res = comms.gmail_list_attachments(message_id="example")
        ok("gmail attachment listing degrades cleanly", "error" in res, "not configured")

    print(f"\n{PASS} checks passed")
    print("\nIntegration status:")
    print(f"  Canvas:  {'configured' if canvas.configured() else 'NOT configured'}")
    print(f"  Discord: {'configured' if comms._discord_token() else 'NOT configured'}")
    print(f"  Gmail:   {'configured' if comms.gmail_configured() else 'NOT configured'}")


if __name__ == "__main__":
    asyncio.run(main())
