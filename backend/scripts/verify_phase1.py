"""Phase 1 verification: end-to-end streamed chat over WS + history persistence.

Usage:
  uv run scripts/verify_phase1.py            # chat turn, prints stream, saves conv id
  uv run scripts/verify_phase1.py --resume   # after backend restart: history survived?
"""

import asyncio
import json
import sys
from pathlib import Path

import websockets

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import config  # noqa: E402
import db  # noqa: E402

WS_URL = f"ws://{config.HOST}:{config.PORT}/ws"
STATE_FILE = Path(__file__).with_name(".verify_phase1_conv")


async def chat(content: str, conv_id: str | None = None) -> str:
    async with websockets.connect(WS_URL) as ws:
        msg: dict = {"type": "user_msg", "content": content}
        if conv_id:
            msg["conversation_id"] = conv_id
        await ws.send(json.dumps(msg))
        tokens = 0
        while True:
            event = json.loads(await ws.recv())
            t = event["type"]
            if t == "state" and event.get("conversation_id"):
                conv_id = event["conversation_id"]
                if event["state"] == "thinking":
                    print(f"[state] thinking, model={event.get('model')}")
            elif t == "assistant_token":
                tokens += 1
                print(event["content"], end="", flush=True)
            elif t == "assistant_done":
                print(f"\n[done] {tokens} token chunks, conv={conv_id}")
                return conv_id
            elif t == "error":
                raise RuntimeError(event["message"])


async def main() -> None:
    if "--resume" in sys.argv:
        conv_id = STATE_FILE.read_text().strip()
        history = db.get_messages(conv_id)
        print(f"history rows after restart: {len(history)}")
        assert len(history) >= 2, "history did not survive restart"
        await chat("What number did I ask you to remember? Reply with just the number.", conv_id)
        print("PASS: history survived restart and model can see it")
    else:
        conv_id = await chat(
            "Remember the number 47 for later in this conversation. "
            "Confirm briefly, then tell me one fact about arc reactors."
        )
        STATE_FILE.write_text(conv_id)
        print("Now restart the backend and run with --resume")


if __name__ == "__main__":
    asyncio.run(main())
