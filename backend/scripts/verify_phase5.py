"""Phase 5 verification (non-interactive parts).

Proves the STT/TTS/wakeword/VAD components work without needing a live mic:
- TTS: Piper synthesizes speech to PCM.
- STT round-trip: that synthesized speech transcribes back correctly.
- Wakeword + VAD models load and score frames.

The full hands-free loop (real "Hey Jarvis" from the mic, barge-in) is a manual
check in the app — this covers everything else.

Usage: uv run scripts/verify_phase5.py
"""

import os
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import config  # noqa: E402
from voice import tts  # noqa: E402

PASS = 0


def ok(label: str, cond: bool, extra: str = "") -> None:
    global PASS
    print(("PASS  " if cond else "FAIL  ") + label + (f"  ({extra})" if extra else ""))
    if not cond:
        sys.exit(1)
    PASS += 1


def main() -> None:
    # TTS -> PCM
    phrase = "what is two plus two"
    pcm, rate = tts.synth_pcm(phrase, config.TTS_VOICE)
    ok("TTS synthesizes PCM", pcm.size > rate // 2 and rate in (16000, 22050), f"{pcm.size} @ {rate}Hz")

    # Resample to 16k for whisper if needed (simple decimation is fine for a check).
    if rate != 16000:
        idx = (np.arange(int(pcm.size * 16000 / rate)) * rate / 16000).astype(int)
        pcm16 = pcm[idx]
    else:
        pcm16 = pcm

    # STT round-trip
    from faster_whisper import WhisperModel

    stt = WhisperModel(config.STT_MODEL, device="cpu", compute_type="int8")
    audio = pcm16.astype(np.float32) / 32768.0
    segments, _ = stt.transcribe(audio, language="en", beam_size=1)
    text = " ".join(s.text for s in segments).lower()
    print(f"      STT heard: {text!r}")
    # whisper may write "two" as "2"; accept either.
    hit = ("plus" in text) + ("two" in text or "2" in text)
    ok("STT round-trips synthesized speech", hit >= 2, text.strip())

    # Wakeword + VAD load and score
    import openwakeword
    from openwakeword.model import Model
    from openwakeword.vad import VAD

    base = os.path.join(os.path.dirname(openwakeword.__file__), "resources", "models")
    oww = Model(wakeword_model_paths=[os.path.join(base, f"{config.WAKEWORD}.onnx")])
    frame = np.zeros(config.FRAME_SAMPLES, dtype=np.int16)
    score = oww.predict(frame)[config.WAKEWORD]
    ok("wakeword model scores frames", 0.0 <= score <= 1.0, f"silence score={score:.3f}")

    vad = VAD()
    vscore = vad.predict(frame)
    ok("VAD model scores frames", 0.0 <= float(vscore) <= 1.0, f"silence prob={float(vscore):.3f}")

    print(f"\n{PASS} checks passed")


if __name__ == "__main__":
    main()
