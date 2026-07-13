"""System tools: open URL in default browser (ACT), launch whitelisted app (ACT),
read/write/move/open files inside the workspace directory only, clipboard write,
user notifications.

Phase 9 boundary: narrow typed tools only. No general computer control, no
blind input injection (pyautogui and friends), no password handling, no delete
outside the workspace — deletion tools don't exist at all."""

import os
import shutil
import subprocess
import webbrowser
from pathlib import Path

import config
from tools.registry import ACT, READ, tool

WORKSPACE = config.DATA_DIR / "workspace"
WORKSPACE.mkdir(parents=True, exist_ok=True)

# Whitelist: chat name -> command. No arbitrary executables, ever.
APP_WHITELIST = {
    "notepad": "notepad.exe",
    "calculator": "calc.exe",
    "explorer": "explorer.exe",
    "vscode": "code",
    "spotify": "spotify",
}


def _safe_path(rel: str) -> Path:
    p = (WORKSPACE / rel).resolve()
    if not p.is_relative_to(WORKSPACE.resolve()):
        raise ValueError("path escapes workspace")
    return p


@tool(
    "open_url",
    "Open a URL in the user's default browser.",
    {
        "type": "object",
        "properties": {"url": {"type": "string"}},
        "required": ["url"],
    },
    ACT,
    summary=lambda a: ("Open website", a.get("url", "?"), ""),
)
def open_url(url: str) -> dict:
    if not url.startswith(("http://", "https://")):
        return {"error": "only http(s) URLs"}
    webbrowser.open(url)
    return {"opened": url}


@tool(
    "launch_app",
    f"Launch an application. Allowed: {', '.join(APP_WHITELIST)}.",
    {
        "type": "object",
        "properties": {"app": {"type": "string", "description": "app name from the allowed list"}},
        "required": ["app"],
    },
    ACT,
    summary=lambda a: ("Launch application", a.get("app", "?"), ""),
)
def launch_app(app: str) -> dict:
    cmd = APP_WHITELIST.get(app.lower().strip())
    if cmd is None:
        return {"error": f"app not in whitelist: {sorted(APP_WHITELIST)}"}
    subprocess.Popen(cmd, shell=True)  # noqa: S602 - fixed whitelist values only
    return {"launched": app}


@tool(
    "read_file",
    "Read a text file from the Jarvis workspace folder.",
    {
        "type": "object",
        "properties": {"path": {"type": "string", "description": "relative path in workspace"}},
        "required": ["path"],
    },
    READ,
)
def read_file(path: str) -> dict:
    p = _safe_path(path)
    if not p.is_file():
        return {"error": f"not found: {path}"}
    return {"path": path, "content": p.read_text(encoding="utf-8", errors="replace")[:16000]}


@tool(
    "write_file",
    "Write a text file inside the Jarvis workspace folder.",
    {
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "relative path in workspace"},
            "content": {"type": "string"},
        },
        "required": ["path", "content"],
    },
    ACT,
    summary=lambda a: (
        "Write file in workspace",
        a.get("path", "?"),
        (a.get("content", "") or "")[:400],
    ),
)
def write_file(path: str, content: str) -> dict:
    p = _safe_path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")
    return {"written": path, "bytes": len(content.encode())}


@tool(
    "open_file",
    "Open a file from the Jarvis workspace folder in its default application.",
    {
        "type": "object",
        "properties": {"path": {"type": "string", "description": "relative path in workspace"}},
        "required": ["path"],
    },
    ACT,
    summary=lambda a: ("Open workspace file", a.get("path", "?"), ""),
)
def open_file(path: str) -> dict:
    p = _safe_path(path)
    if not p.is_file():
        return {"error": f"not found: {path}"}
    os.startfile(p)  # noqa: S606 - workspace-scoped path, default-app open only
    return {"opened": path}


@tool(
    "move_file",
    "Move or rename a file inside the Jarvis workspace folder. Never overwrites.",
    {
        "type": "object",
        "properties": {
            "src": {"type": "string", "description": "relative source path in workspace"},
            "dst": {"type": "string", "description": "relative destination path in workspace"},
        },
        "required": ["src", "dst"],
    },
    ACT,
    summary=lambda a: ("Move workspace file", f"{a.get('src', '?')} -> {a.get('dst', '?')}", ""),
)
def move_file(src: str, dst: str) -> dict:
    s = _safe_path(src)
    d = _safe_path(dst)
    if not s.is_file():
        return {"error": f"not found: {src}"}
    if d.exists():
        return {"error": f"destination exists: {dst} (overwrite not allowed)"}
    d.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(s), str(d))
    return {"moved": src, "to": dst}


@tool(
    "clipboard_write",
    "Copy text to the user's clipboard.",
    {
        "type": "object",
        "properties": {"text": {"type": "string"}},
        "required": ["text"],
    },
    ACT,
    summary=lambda a: ("Copy to clipboard", (a.get("text", "") or "")[:80], (a.get("text", "") or "")[:400]),
)
def clipboard_write(text: str) -> dict:
    import pyperclip

    pyperclip.copy(text)
    return {"copied": True, "chars": len(text)}


@tool(
    "notification_show",
    "Show the user a notification (in-app toast, plus OS notification if allowed).",
    {
        "type": "object",
        "properties": {
            "title": {"type": "string"},
            "body": {"type": "string"},
        },
        "required": ["title", "body"],
    },
    READ,
)
def notification_show(title: str, body: str) -> dict:
    import events

    events.notify(title[:80], body[:1000])
    return {"shown": True}


@tool(
    "list_files",
    "List files in the Jarvis workspace folder.",
    {"type": "object", "properties": {}},
    READ,
)
def list_files() -> dict:
    files = [
        str(p.relative_to(WORKSPACE)) for p in WORKSPACE.rglob("*") if p.is_file()
    ][:200]
    return {"files": files}
