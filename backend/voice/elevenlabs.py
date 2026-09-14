"""ElevenLabs STT/TTS provider with local-fallback-friendly error handling.

The caller treats :class:`ElevenLabsUnavailable` as a signal to use the local
provider.  Every cloud request is gated by the live subscription allowance so
Jarvis stops using ElevenLabs before the configured portion of the plan is used.
"""

import logging
import threading
import time
from dataclasses import dataclass
from typing import Any

import httpx
import keyring
import numpy as np

import config

log = logging.getLogger("jarvis.voice.elevenlabs")

API_ROOT = "https://api.elevenlabs.io/v1"
KEYRING_ACCOUNT = "elevenlabs_api_key"


class ElevenLabsUnavailable(RuntimeError):
    """The cloud provider should not be used for this voice operation."""


@dataclass(frozen=True)
class Subscription:
    used: int
    limit: int
    reset_at: int | None


_usage_lock = threading.Lock()
_cached_subscription: Subscription | None = None
_cached_at = 0.0


def is_configured() -> bool:
    """Whether a key exists locally (without exposing it)."""
    return bool(keyring.get_password(config.KEYRING_SERVICE, KEYRING_ACCOUNT))


def _api_key() -> str:
    key = keyring.get_password(config.KEYRING_SERVICE, KEYRING_ACCOUNT)
    if not key:
        raise ElevenLabsUnavailable("ElevenLabs API key is not stored")
    return key


def _headers() -> dict[str, str]:
    return {"xi-api-key": _api_key()}


def _error_detail(response: httpx.Response) -> str:
    """Return a safe, actionable API error identifier without exposing secrets."""
    try:
        detail = response.json().get("detail", {})
    except ValueError:
        return f"HTTP {response.status_code}"
    if isinstance(detail, dict):
        code = detail.get("code") or detail.get("type")
        message = detail.get("message")
        if code and message:
            return f"{code}: {message}"
        if code:
            return str(code)
    return f"HTTP {response.status_code}"


def _subscription(*, force: bool = False) -> Subscription:
    """Read and briefly cache the current plan usage from ElevenLabs."""
    global _cached_subscription, _cached_at

    now = time.monotonic()
    with _usage_lock:
        if (
            not force
            and _cached_subscription is not None
            and now - _cached_at < config.ELEVENLABS_USAGE_CACHE_SECONDS
        ):
            return _cached_subscription

        try:
            response = httpx.get(
                f"{API_ROOT}/user/subscription",
                headers=_headers(),
                timeout=config.ELEVENLABS_TIMEOUT_SECONDS,
            )
            response.raise_for_status()
            payload: dict[str, Any] = response.json()
            used = int(payload["character_count"])
            limit = int(payload["character_limit"])
        except httpx.HTTPStatusError as exc:
            raise ElevenLabsUnavailable(
                f"could not read ElevenLabs subscription usage: {_error_detail(exc.response)}"
            ) from exc
        except (httpx.HTTPError, KeyError, TypeError, ValueError) as exc:
            raise ElevenLabsUnavailable("could not read ElevenLabs subscription usage") from exc

        if limit <= 0:
            raise ElevenLabsUnavailable("ElevenLabs plan reports no usable credit allowance")
        _cached_subscription = Subscription(
            used=used,
            limit=limit,
            reset_at=payload.get("next_character_count_reset_unix"),
        )
        _cached_at = now
        return _cached_subscription


def usage_status() -> Subscription:
    """Return live usage for diagnostics and the optional verification script."""
    return _subscription(force=True)


def _require_capacity(estimated_credits: int = 0) -> None:
    usage = _subscription()
    fraction = min(max(config.ELEVENLABS_USAGE_FRACTION, 0.0), 1.0)
    cutoff = int(usage.limit * fraction)
    if usage.used + max(estimated_credits, 0) >= cutoff:
        raise ElevenLabsUnavailable(
            f"ElevenLabs allowance is at {usage.used}/{usage.limit}; "
            f"local fallback starts at {cutoff}"
        )


def _record_usage(response: httpx.Response, default: int = 0) -> None:
    """Keep the short-lived cache conservative between subscription refreshes."""
    global _cached_at, _cached_subscription
    raw_cost = response.headers.get("character-cost")
    try:
        cost = int(float(raw_cost)) if raw_cost is not None else default
    except ValueError:
        cost = default
    if cost <= 0:
        # Scribe responses do not necessarily include a character-cost header.
        # Force the next request to query the subscription endpoint instead of
        # risking a stale estimate of a credit-metered transcription.
        with _usage_lock:
            _cached_at = 0.0
        return
    with _usage_lock:
        if _cached_subscription is not None:
            _cached_subscription = Subscription(
                used=_cached_subscription.used + cost,
                limit=_cached_subscription.limit,
                reset_at=_cached_subscription.reset_at,
            )


def _raise_for_cloud_error(response: httpx.Response, operation: str) -> None:
    try:
        response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        raise ElevenLabsUnavailable(
            f"ElevenLabs {operation} request failed: {_error_detail(response)}"
        ) from exc


def synth_pcm(text: str) -> tuple[np.ndarray, int]:
    """Synthesize 16 kHz signed-16-bit PCM with the configured ElevenLabs voice."""
    if not config.ELEVENLABS_VOICE_ID:
        raise ElevenLabsUnavailable("ElevenLabs voice ID is not configured")
    _require_capacity(len(text))
    try:
        response = httpx.post(
            f"{API_ROOT}/text-to-speech/{config.ELEVENLABS_VOICE_ID}",
            params={"output_format": "pcm_16000"},
            headers={**_headers(), "Content-Type": "application/json"},
            json={"text": text, "model_id": config.ELEVENLABS_TTS_MODEL},
            timeout=config.ELEVENLABS_TIMEOUT_SECONDS,
        )
    except httpx.HTTPError as exc:
        raise ElevenLabsUnavailable("ElevenLabs TTS request could not be completed") from exc
    _raise_for_cloud_error(response, "TTS")
    if len(response.content) % 2:
        raise ElevenLabsUnavailable("ElevenLabs TTS returned malformed PCM audio")
    _record_usage(response, default=len(text))
    return np.frombuffer(response.content, dtype="<i2").copy(), config.SAMPLE_RATE


def transcribe_pcm(audio: np.ndarray) -> str:
    """Transcribe 16 kHz mono signed-16-bit PCM with ElevenLabs Scribe."""
    _require_capacity()
    if audio.dtype != np.int16:
        audio = audio.astype(np.int16)
    try:
        response = httpx.post(
            f"{API_ROOT}/speech-to-text",
            headers=_headers(),
            data={
                "model_id": config.ELEVENLABS_STT_MODEL,
                "file_format": "pcm_s16le_16",
                "language_code": "eng",
            },
            files={
                "file": (
                    "utterance.pcm",
                    audio.astype("<i2", copy=False).tobytes(),
                    "application/octet-stream",
                )
            },
            timeout=config.ELEVENLABS_TIMEOUT_SECONDS,
        )
    except httpx.HTTPError as exc:
        raise ElevenLabsUnavailable("ElevenLabs STT request could not be completed") from exc
    _raise_for_cloud_error(response, "STT")
    try:
        text = str(response.json()["text"])
    except (KeyError, TypeError, ValueError) as exc:
        raise ElevenLabsUnavailable("ElevenLabs STT returned no transcript") from exc
    _record_usage(response)
    return text
