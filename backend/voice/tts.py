"""Piper TTS: lazy-loaded voices, synth to numpy for playback or WAV bytes for preview."""

import io
import logging
import wave

import numpy as np

import config

log = logging.getLogger("jarvis.voice.tts")

_voices: dict = {}


def _load(voice: str):
    if voice not in _voices:
        from piper import PiperVoice

        path = config.VOICES_DIR / f"{voice}.onnx"
        if not path.exists():
            raise FileNotFoundError(f"voice not found: {path}")
        _voices[voice] = PiperVoice.load(str(path))
        log.info("loaded TTS voice %s", voice)
    return _voices[voice]


def preload(voice: str | None = None) -> None:
    """Load a voice before the first reply so its model-load delay is not silent."""
    _load(voice or config.TTS_VOICE)


def list_voices() -> list[str]:
    return sorted(p.stem for p in config.VOICES_DIR.glob("*.onnx"))


def synth_wav_bytes(text: str, voice: str | None = None) -> bytes:
    v = _load(voice or config.TTS_VOICE)
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        v.synthesize_wav(text, wf)
    return buf.getvalue()


def synth_pcm(text: str, voice: str | None = None) -> tuple[np.ndarray, int]:
    """Return (int16 mono samples, sample_rate) for direct playback."""
    raw = synth_wav_bytes(text, voice)
    with wave.open(io.BytesIO(raw), "rb") as wf:
        rate = wf.getframerate()
        frames = wf.readframes(wf.getnframes())
    return np.frombuffer(frames, dtype=np.int16), rate
