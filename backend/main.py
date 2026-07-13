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
import re

import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect

import agent
import approval
import config
import db
import events
import memory
import metrics
import proactive
import scheduler
import telemetry
import tools
from voice import VoicePipeline, list_voices, synth_wav_bytes

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("jarvis.main")

app = FastAPI(title="jarvis-backend")

_clients: set[WebSocket] = set()
TELEMETRY_INTERVAL_S = 3

# Voice conversation id — the voice pipeline shares one rolling conversation.
_voice_conv: dict[str, str] = {}


def _voice_conv_id() -> str:
    if "id" not in _voice_conv or not db.conversation_exists(_voice_conv["id"]):
        _voice_conv["id"] = db.create_conversation("Voice session")
    return _voice_conv["id"]


voice_pipeline: VoicePipeline | None = None


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


async def _broadcast(payload: dict) -> None:
    for ws in list(_clients):
        try:
            await ws.send_json(payload)
        except Exception:  # noqa: BLE001 - dead socket
            _clients.discard(ws)


async def _voice_converse(conv_id: str, text: str):
    """Voice entrypoint into converse: persist the spoken turn, then delegate."""
    db.add_message(conv_id, "user", text)
    async for event in converse(conv_id, text):
        yield event


@app.on_event("startup")
async def _startup() -> None:
    global voice_pipeline
    db.init()
    approval.init()
    approval.set_broadcaster(_broadcast)
    events.init()
    events.set_broadcaster(_broadcast)
    tools.load_all()
    log.info("tools registered: %s", sorted(tools.REGISTRY))
    voice_pipeline = VoicePipeline(_broadcast, _voice_converse, _voice_conv_id)
    asyncio.create_task(_telemetry_loop())
    scheduler.start()
    if tools.canvas.configured():
        asyncio.create_task(_initial_canvas_sync())


async def _initial_canvas_sync() -> None:
    try:
        result = await tools.canvas.sync()
        log.info("startup canvas sync: %s", result)
        await _broadcast({"type": "activity", "text": "Canvas synced"})
    except Exception:  # noqa: BLE001
        log.exception("startup canvas sync failed")


@app.get("/audit")
def audit_log(limit: int = 50) -> dict:
    return {"entries": approval.audit_rows(limit)}


@app.get("/voices")
def voices() -> dict:
    return {"voices": list_voices(), "current": config.TTS_VOICE}


@app.get("/tts_preview")
def tts_preview(text: str, voice: str | None = None):
    from fastapi import Response

    return Response(synth_wav_bytes(text, voice), media_type="audio/wav")


@app.get("/events")
def event_log(limit: int = 50, name: str | None = None) -> dict:
    return {"events": events.recent(limit, name)}


@app.get("/metrics/{metric}")
def metric_series(metric: str, days: int = 30) -> dict:
    return {"metric": metric, "points": metrics.series(metric, days)}


@app.get("/study")
def study_stats() -> dict:
    from tools import study

    return study.stats()


@app.post("/brief/preview")
async def brief_preview() -> dict:
    """Manual trigger: compose + broadcast the morning brief now."""
    return {"brief": await proactive.morning_brief()}


@app.get("/health")
def health() -> dict:
    from tools import canvas, comms

    return {
        "status": "ok",
        "local_model": config.LOCAL_MODEL,
        "gemini_model": config.GEMINI_MODEL,
        "gemini_calls_today": db.gemini_calls_today(),
        "integrations": {
            "canvas": canvas.configured(),
            "discord": bool(comms._discord_token()),
            "gmail": comms.gmail_configured(),
        },
        "canvas_url": config.CANVAS_BASE_URL,
    }


REMEMBER_RE = re.compile(r"^(?:jarvis[,!]?\s+)?remember\s+(?:that\s+)?(.+)$", re.I | re.S)
FORGET_RE = re.compile(r"^(?:jarvis[,!]?\s+)?forget\s+(?:about\s+|that\s+)?(.+)$", re.I | re.S)


async def _memory_command_reply(text: str) -> str | None:
    """Explicit remember/forget commands bypass the LLM. Returns reply or None."""
    if m := REMEMBER_RE.match(text.strip()):
        fact_id = await memory.add_fact(m.group(1).strip(), source="explicit")
        return (
            "Noted, Boss. I'll remember that."
            if fact_id is not None
            else "Already in my memory core, Boss."
        )
    if m := FORGET_RE.match(text.strip()):
        deleted = await memory.forget(m.group(1).strip())
        return (
            f"Forgotten: “{deleted['content']}”"
            if deleted
            else "Nothing in my memory core matches that, Boss."
        )
    return None


async def converse(conv_id: str, user_text: str):
    """Shared conversation generator used by both text (WS) and voice paths.

    Handles memory commands, recall injection, the agent turn, persistence, and
    the background post-turn pass. Yields protocol events; the caller decides how
    to deliver them (per-socket for text, broadcast + TTS for voice).
    """
    # A new user turn is the explicit "resume" signal after an emergency stop.
    tools.registry.clear_emergency_stop()

    reply = await _memory_command_reply(user_text)
    if reply is not None:
        db.add_message(conv_id, "assistant", reply)
        yield {"done": True, "content": reply}
        return

    history = db.get_messages(conv_id)
    memory_block = await memory.recall_block(user_text)
    if len(history) <= 1 and (prev := memory.latest_summary()):
        memory_block += f"\n\nLast session recap: {prev}"
    messages = [
        {"role": "system", "content": agent.build_system_prompt(memory_block.strip())}
    ] + history
    final = ""
    async for event in agent.run_turn(messages):
        if event.get("done"):
            final = event["content"]
        yield event
    db.add_message(conv_id, "assistant", final)
    asyncio.create_task(_post_turn(conv_id, user_text, final))


async def _run_and_stream(ws: WebSocket, conv_id: str, user_text: str) -> None:
    final = ""
    async for event in converse(conv_id, user_text):
        if "state" in event:
            await ws.send_json(
                {"type": "state", "state": event["state"], "model": event["model"],
                 "conversation_id": conv_id}
            )
        elif "assistant_token" in event:
            await ws.send_json({"type": "assistant_token", "content": event["assistant_token"]})
        elif "tool_call" in event:
            await ws.send_json({"type": "tool_call", **event["tool_call"]})
            await _broadcast(
                {"type": "activity", "text": f"Tool: {event['tool_call']['name']}"}
            )
        elif "tool_result" in event:
            await ws.send_json({"type": "tool_result", **event["tool_result"]})
        elif event.get("done"):
            final = event["content"]
    await ws.send_json({"type": "assistant_done", "content": final})
    await ws.send_json({"type": "state", "state": "idle", "conversation_id": conv_id})


async def _post_turn(conv_id: str, user_text: str, assistant_text: str) -> None:
    """Background pass: extract durable facts, refresh session summary."""
    try:
        stored = await memory.extract_and_store(user_text, assistant_text)
        if stored:
            log.info("extracted %d fact(s): %s", len(stored), stored)
        await memory.summarize_conversation(conv_id)
    except Exception:  # noqa: BLE001
        log.exception("post-turn memory pass failed")


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
            if mtype == "approval_response":
                approval.resolve(str(msg.get("id", "")), bool(msg.get("approved")))
                continue

            if mtype == "voice_start":
                if voice_pipeline:
                    await voice_pipeline.start()
                continue
            if mtype == "voice_stop":
                if voice_pipeline:
                    await voice_pipeline.stop()
                continue
            if mtype == "push_to_talk":
                if voice_pipeline:
                    voice_pipeline.push_to_talk()
                continue

            if mtype == "emergency_stop":
                tools.registry.engage_emergency_stop()
                denied = approval.deny_all()
                if task and not task.done():
                    task.cancel()
                if voice_pipeline:
                    await voice_pipeline.stop()
                approval.audit(
                    "emergency_stop", {}, "SYSTEM", "executed",
                    f"denied {denied} pending approval(s)",
                )
                await _broadcast(
                    {"type": "activity", "text": "EMERGENCY STOP — all actions halted"}
                )
                await _broadcast(
                    {
                        "type": "notification",
                        "title": "Emergency stop",
                        "body": "All actions halted and pending approvals denied. "
                        "Send a message to resume.",
                    }
                )
                await ws.send_json({"type": "state", "state": "idle"})
                continue

            if mtype in ("study_start", "study_stop"):
                result = await tools.execute_tool(mtype, {})
                label = result.get("error") or (
                    "Study session started"
                    if mtype == "study_start"
                    else f"Study session stopped ({result.get('hours', 0):g}h)"
                )
                await _broadcast({"type": "activity", "text": label})
                snap = await telemetry.snapshot()
                await _broadcast({"type": "telemetry", **snap})
                continue

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
                text = msg.get("content", "")
                db.add_message(conv_id, "user", text)
                task = asyncio.create_task(_run_and_stream(ws, conv_id, text))
            elif mtype == "regenerate":
                conv_id = msg.get("conversation_id", "")
                if not db.conversation_exists(conv_id):
                    await ws.send_json({"type": "error", "message": "unknown conversation"})
                    continue
                db.delete_last_assistant_message(conv_id)
                history = db.get_messages(conv_id)
                last_user = next(
                    (m["content"] for m in reversed(history) if m["role"] == "user"), ""
                )
                task = asyncio.create_task(_run_and_stream(ws, conv_id, last_user))
            elif mtype == "memory_list":
                await ws.send_json({"type": "memory_list", "facts": memory.list_facts()})
            elif mtype == "memory_delete":
                memory.delete_fact(int(msg["id"]))
                await ws.send_json({"type": "memory_list", "facts": memory.list_facts()})
            elif mtype == "memory_update":
                await memory.update_fact(int(msg["id"]), msg["content"])
                await ws.send_json({"type": "memory_list", "facts": memory.list_facts()})
            elif mtype == "memory_add":
                await memory.add_fact(msg["content"], source="explicit")
                await ws.send_json({"type": "memory_list", "facts": memory.list_facts()})
            else:
                await ws.send_json({"type": "error", "message": f"unknown type: {mtype}"})
    except WebSocketDisconnect:
        if task and not task.done():
            task.cancel()
    finally:
        _clients.discard(ws)


if __name__ == "__main__":
    uvicorn.run(app, host=config.HOST, port=config.PORT)
