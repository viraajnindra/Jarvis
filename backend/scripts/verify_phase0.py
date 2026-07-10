"""Phase 0 verification: local model chat + tool call, Gemini key smoke test.

Run: uv run scripts/verify_phase0.py
"""

import json
import sys

import httpx
import keyring

OLLAMA = "http://127.0.0.1:11434"
MODEL = "qwen3.5:9b"


def check_ollama_chat() -> bool:
    print(f"[1/3] {MODEL} chat...", end=" ", flush=True)
    r = httpx.post(
        f"{OLLAMA}/api/chat",
        json={
            "model": MODEL,
            "messages": [{"role": "user", "content": "Reply with exactly: JARVIS ONLINE"}],
            "stream": False,
        },
        timeout=120,
    )
    r.raise_for_status()
    reply = r.json()["message"]["content"]
    ok = "JARVIS ONLINE" in reply.upper()
    print("OK" if ok else f"UNEXPECTED REPLY: {reply!r}")
    return ok


def check_ollama_tool_call() -> bool:
    print("[2/3] tool-call smoke test...", end=" ", flush=True)
    tools = [
        {
            "type": "function",
            "function": {
                "name": "get_weather",
                "description": "Get current weather for a city",
                "parameters": {
                    "type": "object",
                    "properties": {"city": {"type": "string"}},
                    "required": ["city"],
                },
            },
        }
    ]
    r = httpx.post(
        f"{OLLAMA}/api/chat",
        json={
            "model": MODEL,
            "messages": [{"role": "user", "content": "What's the weather in Tokyo? Use the tool."}],
            "tools": tools,
            "stream": False,
        },
        timeout=120,
    )
    r.raise_for_status()
    calls = r.json()["message"].get("tool_calls") or []
    ok = bool(calls) and calls[0]["function"]["name"] == "get_weather"
    print("OK" if ok else f"NO VALID TOOL CALL: {json.dumps(r.json()['message'])[:300]}")
    return ok


def check_gemini() -> bool:
    print("[3/3] Gemini key...", end=" ", flush=True)
    key = keyring.get_password("jarvis", "gemini_api_key")
    if not key:
        print("NOT STORED (run scripts/store_gemini_key.py first)")
        return False
    r = httpx.post(
        "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent",
        headers={"x-goog-api-key": key},
        json={"contents": [{"parts": [{"text": "Reply with exactly: CLOUD LINK OK"}]}]},
        timeout=60,
    )
    if r.status_code != 200:
        print(f"HTTP {r.status_code}: {r.text[:200]}")
        return False
    text = r.json()["candidates"][0]["content"]["parts"][0]["text"]
    print("OK" if "CLOUD LINK OK" in text.upper() else f"UNEXPECTED: {text!r}")
    return True


if __name__ == "__main__":
    results = []
    for check in (check_ollama_chat, check_ollama_tool_call, check_gemini):
        try:
            results.append(check())
        except Exception as e:  # noqa: BLE001 - report and continue to next check
            print(f"FAILED: {e}")
            results.append(False)
    print(f"\n{sum(results)}/3 checks passed")
    sys.exit(0 if all(results) else 1)
