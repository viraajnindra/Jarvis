"""System tools: open URL in default browser (ACT), launch whitelisted app (ACT),
read/write files inside the workspace directory only."""

import os
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
