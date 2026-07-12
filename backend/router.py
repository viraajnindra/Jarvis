"""Model router: local qwen via Ollama by default, Gemini Flash for big/special tasks.

Sensitive content (email bodies, personal facts) must never route to Gemini —
callers mark that with sensitive=True and the router hard-pins local.
"""

import json
import logging
from collections.abc import AsyncIterator
from typing import Any

import httpx
import keyring

import config
import db

log = logging.getLogger("jarvis.router")


def _estimate_tokens(messages: list[dict]) -> int:
    chars = sum(len(m.get("content") or "") for m in messages)
    return chars // 4


def choose_model(
    messages: list[dict],
    *,
    deep_research: bool = False,
    has_vision: bool = False,
    sensitive: bool = False,
) -> str:
    """Return 'local' or 'gemini'."""
    if sensitive:
        return "local"
    if deep_research or has_vision or _estimate_tokens(messages) > config.ROUTER_LOCAL_TOKEN_LIMIT:
        if db.gemini_calls_today() >= config.GEMINI_DAILY_LIMIT:
            log.warning("Gemini daily limit reached, falling back to local")
            return "local"
        return "gemini"
    return "local"


async def stream_local(
    messages: list[dict], tools: list[dict] | None = None
) -> AsyncIterator[dict]:
    """Stream Ollama /api/chat chunks. Yields {'token': str} and/or {'tool_calls': [...]},
    ends with {'done': True}."""
    payload: dict[str, Any] = {"model": config.LOCAL_MODEL, "messages": messages, "stream": True}
    if tools:
        payload["tools"] = tools
    async with httpx.AsyncClient(timeout=300) as client:
        async with client.stream("POST", f"{config.OLLAMA_URL}/api/chat", json=payload) as r:
            r.raise_for_status()
            async for line in r.aiter_lines():
                if not line.strip():
                    continue
                chunk = json.loads(line)
                msg = chunk.get("message", {})
                if msg.get("content"):
                    yield {"token": msg["content"]}
                if msg.get("tool_calls"):
                    yield {"tool_calls": msg["tool_calls"]}
                if chunk.get("done"):
                    yield {"done": True}
                    return


def _gemini_key() -> str:
    key = keyring.get_password(config.KEYRING_SERVICE, "gemini_api_key")
    if not key:
        raise RuntimeError("Gemini API key not in Credential Manager")
    return key


def _to_gemini_contents(messages: list[dict]) -> tuple[str | None, list[dict]]:
    system = None
    contents = []
    for m in messages:
        if m["role"] == "system":
            system = m["content"]
        else:
            role = "model" if m["role"] == "assistant" else "user"
            contents.append({"role": role, "parts": [{"text": m["content"]}]})
    return system, contents


async def stream_gemini(messages: list[dict], reason: str) -> AsyncIterator[dict]:
    """Stream Gemini generateContent (SSE). Yields {'token': str}, ends {'done': True}."""
    system, contents = _to_gemini_contents(messages)
    payload: dict[str, Any] = {"contents": contents}
    if system:
        payload["systemInstruction"] = {"parts": [{"text": system}]}
    url = (
        "https://generativelanguage.googleapis.com/v1beta/models/"
        f"{config.GEMINI_MODEL}:streamGenerateContent?alt=sse"
    )
    db.log_gemini_call(reason)
    async with httpx.AsyncClient(timeout=300) as client:
        async with client.stream(
            "POST", url, headers={"x-goog-api-key": _gemini_key()}, json=payload
        ) as r:
            r.raise_for_status()
            async for line in r.aiter_lines():
                if not line.startswith("data: "):
                    continue
                data = json.loads(line[6:])
                for cand in data.get("candidates", []):
                    for part in cand.get("content", {}).get("parts", []):
                        if part.get("text"):
                            yield {"token": part["text"]}
    yield {"done": True}
