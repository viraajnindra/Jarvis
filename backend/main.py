"""J.A.R.V.I.S. backend: FastAPI + WebSocket endpoint.

Run: uv run main.py   (binds 127.0.0.1 only)

WS protocol (JSON, one object per frame):
  client -> server:
    {"type": "user_msg", "content": str, "conversation_id"?: str}
    {"type": "regenerate", "conversation_id": str}
    {"type": "cancel"}
  server -> client:
    {"type": "state", "state": "idle|thinking", "model"?: str, "conversation_id"?: str}
    {"type": "assistant_token", "content": str}
    {"type": "tool_call", ...} / {"type": "tool_result", ...}
    {"type": "assistant_done", "content": str}
    {"type": "error", "message": str}
"""

import asyncio
import json
import logging

import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect

import agent
import config
import db
import telemetry

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("jarvis.main")

app = FastAPI(title="jarvis-backend")

_clients: set[WebSocket] = set()
TELEMETRY_INTERVAL_S = 3


async def _telemetry_loop() -> None:
    while True:
        if _clients:
            snap = await telemetry.snapshot()
            payload = {"type": "telemetry", **snap}
            for ws in list(_clients):
                try:
                    await ws.send_json(payload)
                except Exception:  # noqa: BLE001 - dead socket, drop it
                    _clients.discard(ws)
        await asyncio.sleep(TELEMETRY_INTERVAL_S)


@app.on_event("startup")
async def _startup() -> None:
    db.init()
    asyncio.create_task(_telemetry_loop())


@app.get("/health")
def health() -> dict:
    return {
        "status": "ok",
        "local_model": config.LOCAL_MODEL,
        "gemini_model": config.GEMINI_MODEL,
        "gemini_calls_today": db.gemini_calls_today(),
    }


async def _run_and_stream(ws: WebSocket, conv_id: str) -> None:
    history = db.get_messages(conv_id)
    messages = [{"role": "system", "content": agent.build_system_prompt()}] + history
    final = ""
    async for event in agent.run_turn(messages):
        if "state" in event:
            await ws.send_json(
                {"type": "state", "state": event["state"], "model": event["model"],
                 "conversation_id": conv_id}
            )
        elif "assistant_token" in event:
            await ws.send_json({"type": "assistant_token", "content": event["assistant_token"]})
        elif "tool_call" in event:
            await ws.send_json({"type": "tool_call", **event["tool_call"]})
        elif "tool_result" in event:
            await ws.send_json({"type": "tool_result", **event["tool_result"]})
        elif event.get("done"):
            final = event["content"]
    db.add_message(conv_id, "assistant", final)
    await ws.send_json({"type": "assistant_done", "content": final})
    await ws.send_json({"type": "state", "state": "idle", "conversation_id": conv_id})


@app.websocket("/ws")
async def ws_endpoint(ws: WebSocket) -> None:
    await ws.accept()
    _clients.add(ws)
    task: asyncio.Task | None = None
    try:
        while True:
            raw = await ws.receive_text()
            try:
                msg = json.loads(raw)
            except json.JSONDecodeError:
                await ws.send_json({"type": "error", "message": "invalid JSON"})
                continue

            mtype = msg.get("type")
            if mtype == "cancel":
                if task and not task.done():
                    task.cancel()
                await ws.send_json({"type": "state", "state": "idle"})
                continue

            if task and not task.done():
                await ws.send_json({"type": "error", "message": "busy: previous turn running"})
                continue

            if mtype == "user_msg":
                conv_id = msg.get("conversation_id")
                if not conv_id or not db.conversation_exists(conv_id):
                    conv_id = db.create_conversation()
                db.add_message(conv_id, "user", msg.get("content", ""))
                task = asyncio.create_task(_run_and_stream(ws, conv_id))
            elif mtype == "regenerate":
                conv_id = msg.get("conversation_id", "")
                if not db.conversation_exists(conv_id):
                    await ws.send_json({"type": "error", "message": "unknown conversation"})
                    continue
                db.delete_last_assistant_message(conv_id)
                task = asyncio.create_task(_run_and_stream(ws, conv_id))
            else:
                await ws.send_json({"type": "error", "message": f"unknown type: {mtype}"})
    except WebSocketDisconnect:
        if task and not task.done():
            task.cancel()
    finally:
        _clients.discard(ws)


if __name__ == "__main__":
    uvicorn.run(app, host=config.HOST, port=config.PORT)
