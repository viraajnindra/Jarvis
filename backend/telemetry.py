"""System telemetry: CPU/RAM/GPU + model/internet status, pushed over WS.

Study tracker / Lovable / Canvas figures arrive in Phases 6 and 8 — until then
those fields are null and the UI renders placeholders.
"""

import logging
import socket

import httpx
import psutil

import config

log = logging.getLogger("jarvis.telemetry")

try:
    import pynvml

    pynvml.nvmlInit()
    _gpu = pynvml.nvmlDeviceGetHandleByIndex(0)
    _gpu_name = pynvml.nvmlDeviceGetName(_gpu)
except Exception as e:  # noqa: BLE001 - no NVML => no GPU stats, keep serving
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
            r = await client.get(f"{config.OLLAMA_URL}/api/version")
            return r.status_code == 200
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
        "lovable": _lovable_panel(),
        "canvas": _canvas_counts(),
    }


def _study_stats() -> dict | None:
    try:
        from tools import study

        return study.stats()
    except Exception:  # noqa: BLE001 - telemetry must never crash the loop
        return None


def _lovable_panel() -> dict | None:
    try:
        import metrics

        return metrics.lovable_panel()
    except Exception:  # noqa: BLE001
        return None


def _canvas_counts() -> dict | None:
    try:
        from tools import canvas

        return canvas.panel_counts()
    except Exception:  # noqa: BLE001 - telemetry must never crash the loop
        return None
