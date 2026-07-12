"""Phase 3 verification: explicit remember, vector recall, recall across restart.

Usage:
  uv run scripts/verify_phase3.py            # store preference via WS command
  uv run scripts/verify_phase3.py --resume   # after backend restart: recall works?
"""

import asyncio
import json
import sys
from pathlib import Path

import websockets

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import config  # noqa: E402
import db  # noqa: E402
import memory  # noqa: E402

WS_URL = f"ws://{config.HOST}:{config.PORT}/ws"
PREFERENCE = "Jarvis, remember that I prefer bullet-point study guides with key terms bolded"
QUERY = "how should I format my study guides?"


async def send_and_wait(content: str, conv_id: str | None = None) -> tuple[str, str]:
    async with websockets.connect(WS_URL) as ws:
        msg: dict = {"type": "user_msg", "content": content}
        if conv_id:
            msg["conversation_id"] = conv_id
        await ws.send(json.dumps(msg))
        conv = conv_id or ""
        while True:
            event = json.loads(await ws.recv())
            if event["type"] == "state" and event.get("conversation_id"):
                conv = event["conversation_id"]
            elif event["type"] == "assistant_done":
                return event["content"], conv
            elif event["type"] == "error":
                raise RuntimeError(event["message"])


async def main() -> None:
    db.init()
    if "--resume" in sys.argv:
        block = await memory.recall_block(QUERY)
        print(f"recall block for {QUERY!r}:\n{block}\n")
        assert "bullet" in block.lower(), "stored preference not recalled by vector search"
        reply, _ = await send_and_wait(QUERY)  # fresh conversation, no prior context
        print(f"assistant reply:\n{reply}\n")
        assert "bullet" in reply.lower(), "reply ignored recalled preference"
        print("PASS: preference recalled unprompted after restart, in a new conversation")
    else:
        reply, _ = await send_and_wait(PREFERENCE)
        print(f"reply: {reply}")
        assert "remember" in reply.lower() or "noted" in reply.lower(), "remember command failed"
        facts = [f for f in memory.list_facts() if "bullet" in f["content"].lower()]
        assert facts, "fact not stored"
        print(f"stored: {facts[0]['content']!r} (source={facts[0]['source']})")
        print("Now restart the backend and run with --resume")


if __name__ == "__main__":
    asyncio.run(main())
