"""Verify the optional ElevenLabs STT/TTS integration.

Requires a key stored by store_elevenlabs_key.py. This makes two small API calls
and therefore consumes a small amount of the monthly allowance.

Usage: uv run scripts/verify_elevenlabs_voice.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from voice import elevenlabs  # noqa: E402


def main() -> None:
    if not elevenlabs.is_configured():
        print("FAIL  ElevenLabs API key is not stored. Run store_elevenlabs_key.py first.")
        raise SystemExit(1)

    usage = elevenlabs.usage_status()
    print(f"PASS  ElevenLabs subscription available ({usage.used}/{usage.limit} credits used)")

    phrase = "Jarvis voice integration test."
    pcm, rate = elevenlabs.synth_pcm(phrase)
    if pcm.size <= rate // 4:
        print("FAIL  ElevenLabs TTS returned insufficient audio")
        raise SystemExit(1)
    print(f"PASS  ElevenLabs TTS returned PCM ({pcm.size} samples at {rate}Hz)")

    text = elevenlabs.transcribe_pcm(pcm).lower()
    if "jarvis" not in text or "test" not in text:
        print(f"FAIL  ElevenLabs STT transcript was unexpected: {text!r}")
        raise SystemExit(1)
    print(f"PASS  ElevenLabs STT transcribed: {text!r}")


if __name__ == "__main__":
    main()
