"""Background fact extraction and session summaries (local model only —
conversation content is personal and never routes to Gemini)."""

import json
import logging
import time

import httpx

import config
import db
from memory import store

log = logging.getLogger("jarvis.memory.extract")

EXTRACT_PROMPT = """Extract durable facts about the user from this exchange — preferences,
courses/classes, goals, projects, recurring commitments, tools they use. Only facts useful
in FUTURE conversations.

STRICT RULES:
- Only extract what the USER stated or clearly implied about themselves.
- Never extract from the assistant's reply — its suggestions and elaborations are not user facts.
- Ignore one-off requests, pleasantries, and anything about the assistant.

Exchange:
USER: {user}
ASSISTANT: {assistant}

Reply with a JSON array of short third-person statements, e.g.
["prefers bullet-point study guides", "is taking BIO 301"].
Empty array if nothing durable. JSON only, no prose."""

SUMMARY_PROMPT = """Summarize this conversation in 2-3 sentences for a "previously on"
recap. Capture decisions, open tasks, and topics. Plain text only.

{transcript}"""


async def _local_completion(prompt: str) -> str:
    async with httpx.AsyncClient(timeout=180) as client:
        r = await client.post(
            f"{config.OLLAMA_URL}/api/chat",
            json={
                "model": config.LOCAL_MODEL,
                "messages": [{"role": "user", "content": prompt}],
                "stream": False,
            },
        )
        r.raise_for_status()
        return r.json()["message"]["content"]


async def extract_and_store(user_msg: str, assistant_msg: str) -> list[str]:
    """Post-turn extraction pass. Returns contents of newly stored facts."""
    try:
        raw = await _local_completion(
            EXTRACT_PROMPT.format(user=user_msg[:2000], assistant=assistant_msg[:2000])
        )
        start, end = raw.find("["), raw.rfind("]")
        if start == -1 or end == -1:
            return []
        candidates = json.loads(raw[start : end + 1])
    except (httpx.HTTPError, json.JSONDecodeError) as e:
        log.warning("extraction failed: %s", e)
        return []

    stored = []
    for c in candidates:
        if not isinstance(c, str) or len(c) < 8:
            continue
        # Inferred facts stored active with lower confidence; the memory pane is the
        # review surface until the Phase 4 approval queue exists.
        if await store.add_fact(c, source="inferred", confidence=0.7) is not None:
            stored.append(c)
    return stored


async def summarize_conversation(conv_id: str) -> None:
    messages = db.get_messages(conv_id)
    if len(messages) < 2:
        return
    transcript = "\n".join(f"{m['role'].upper()}: {m['content'][:500]}" for m in messages[-20:])
    try:
        summary = await _local_completion(SUMMARY_PROMPT.format(transcript=transcript))
    except httpx.HTTPError as e:
        log.warning("summary failed: %s", e)
        return
    with db.connect() as conn:
        conn.execute(
            "UPDATE conversations SET summary=?, updated_at=? WHERE id=?",
            (summary.strip(), time.time(), conv_id),
        )


def latest_summary() -> str | None:
    with db.connect() as conn:
        row = conn.execute(
            "SELECT summary FROM conversations WHERE summary IS NOT NULL "
            "ORDER BY updated_at DESC LIMIT 1"
        ).fetchone()
    return row["summary"] if row else None
