"""Agent loop: LLM <-> tools until final answer.

Tool registry arrives in Phase 4; the loop already supports tool calls so the
protocol is stable from day one. Each event yielded maps 1:1 to a WS message.
"""

import json
import logging
from collections.abc import AsyncIterator

import config
import router

log = logging.getLogger("jarvis.agent")

SYSTEM_PROMPT = """You are J.A.R.V.I.S., a personal assistant. Address the user as "Boss".
Be terse, precise, and dryly witty. Never invent facts; say when you don't know.
You may be given tools; use them when they materially help. Never fabricate tool results.

{memory_block}"""


def build_system_prompt(memory_block: str = "") -> str:
    block = f"What I know about the user:\n{memory_block}" if memory_block else ""
    return SYSTEM_PROMPT.format(memory_block=block).strip()


# Populated in Phase 4 by the tool registry: name -> (schema, async fn, tier).
TOOLS: dict = {}


def _tool_schemas() -> list[dict] | None:
    return [t["schema"] for t in TOOLS.values()] or None


async def run_turn(
    messages: list[dict],
    *,
    deep_research: bool = False,
    sensitive: bool = False,
) -> AsyncIterator[dict]:
    """Run one agent turn. Yields:
    {'state': 'thinking', 'model': ...}
    {'assistant_token': str}
    {'tool_call': {...}} / {'tool_result': {...}}   (Phase 4)
    {'done': True, 'content': full_text}
    """
    which = router.choose_model(messages, deep_research=deep_research, sensitive=sensitive)
    model_name = config.GEMINI_MODEL if which == "gemini" else config.LOCAL_MODEL
    yield {"state": "thinking", "model": model_name}

    full: list[str] = []
    for iteration in range(config.AGENT_MAX_ITERATIONS):
        pending_tool_calls = []
        if which == "gemini":
            stream = router.stream_gemini(messages, reason="chat")
        else:
            stream = router.stream_local(messages, tools=_tool_schemas())
        async for event in stream:
            if "token" in event:
                full.append(event["token"])
                yield {"assistant_token": event["token"]}
            if "tool_calls" in event:
                pending_tool_calls.extend(event["tool_calls"])

        if not pending_tool_calls:
            break

        # Execute tools, append results, loop again (Phase 4 fills TOOLS).
        messages = list(messages) + [
            {"role": "assistant", "content": "", "tool_calls": pending_tool_calls}
        ]
        for call in pending_tool_calls:
            name = call["function"]["name"]
            args = call["function"].get("arguments") or {}
            yield {"tool_call": {"name": name, "arguments": args}}
            tool = TOOLS.get(name)
            if tool is None:
                result = {"error": f"unknown tool: {name}"}
            else:
                result = await tool["fn"](**args)
            yield {"tool_result": {"name": name, "result": result}}
            messages.append({"role": "tool", "content": json.dumps(result)})
    else:
        log.warning("agent hit max iterations (%d)", config.AGENT_MAX_ITERATIONS)

    yield {"done": True, "content": "".join(full)}
