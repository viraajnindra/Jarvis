"""System telemetry: CPU/RAM/GPU, service health, study, Gmail, and Canvas."""

import asyncio
import logging
import socket
import time

import httpx
import psutil

import config

log = logging.getLogger("jarvis.telemetry")

EMAIL_REFRESH_S = 60
_email_panel_cache: dict | None = None
_email_panel_updated_at = 0.0

try:
    import pynvml

    pynvml.nvmlInit()
    _gpu = pynvml.nvmlDeviceGetHandleByIndex(0)
    _gpu_name = pynvml.nvmlDeviceGetName(_gpu)
except Exception as e:  # noqa: BLE001 - no NVML means no GPU stats
    log.warning("NVML unavailable: %s", e)
    _gpu = None
    _gpu_name = None


def _gpu_stats() -> dict | None:
    if _gpu is None:
        return None
    util = pynvml.nvmlDeviceGetUtilizationRates(_gpu)
    mem = pynvml.nvmlDeviceGetMemoryInfo(_gpu)
    return {
        "name": _gpu_name,
        "util_pct": util.gpu,
        "vram_used_gb": round(mem.used / 1e9, 1),
        "vram_total_gb": round(mem.total / 1e9, 1),
    }


def _internet_up() -> bool:
    try:
        socket.create_connection(("1.1.1.1", 53), timeout=2).close()
        return True
    except OSError:
        return False


async def _model_online() -> bool:
    try:
        async with httpx.AsyncClient(timeout=3) as client:
            response = await client.get(f"{config.OLLAMA_URL}/api/version")
            return response.status_code == 200
    except httpx.HTTPError:
        return False


async def snapshot() -> dict:
    return {
        "cpu_pct": psutil.cpu_percent(interval=None),
        "ram_pct": psutil.virtual_memory().percent,
        "gpu": _gpu_stats(),
        "model_online": await _model_online(),
        "internet": _internet_up(),
        "study": _study_stats(),
        "email": await _email_panel(),
        "canvas": _canvas_counts(),
    }


def _study_stats() -> dict | None:
    try:
        from tools import study

        return study.stats()
    except Exception:  # noqa: BLE001 - telemetry must never crash the loop
        return None


async def _email_panel() -> dict:
    """Refresh Gmail once per minute; telemetry itself is pushed every few seconds."""
    global _email_panel_cache, _email_panel_updated_at
    try:
        from tools import comms

        if not comms.gmail_configured():
            return {"configured": False, "unread": None, "total": None, "recent": []}
        now = time.monotonic()
        if _email_panel_cache is not None and now - _email_panel_updated_at < EMAIL_REFRESH_S:
            return _email_panel_cache
        summary = await asyncio.to_thread(comms.gmail_inbox_summary)
        if "error" in summary:
            return {"configured": False, "unread": None, "total": None, "recent": []}
        _email_panel_cache = {"configured": True, **summary}
        _email_panel_updated_at = now
        return _email_panel_cache
    except Exception:  # noqa: BLE001 - telemetry must never crash the loop
        log.exception("email telemetry refresh failed")
        return _email_panel_cache or {
            "configured": True,
            "unread": None,
            "total": None,
            "recent": [],
        }


def _canvas_counts() -> dict | None:
    try:
        from tools import canvas

        return canvas.panel_counts()
    except Exception:  # noqa: BLE001 - telemetry must never crash the loop
        return None
