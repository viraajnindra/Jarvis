"""Non-secret configuration. Secrets live in Windows Credential Manager only."""

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = Path(os.getenv("JARVIS_DATA_DIR", BASE_DIR / "data"))
DATA_DIR.mkdir(parents=True, exist_ok=True)

DB_PATH = DATA_DIR / "jarvis.db"

HOST = "127.0.0.1"  # never 0.0.0.0
PORT = int(os.getenv("JARVIS_PORT", "8735"))

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://127.0.0.1:11434")
LOCAL_MODEL = os.getenv("JARVIS_LOCAL_MODEL", "qwen3.5:9b")
EMBED_MODEL = os.getenv("JARVIS_EMBED_MODEL", "nomic-embed-text")

GEMINI_MODEL = os.getenv("JARVIS_GEMINI_MODEL", "gemini-3.5-flash")
GEMINI_DAILY_LIMIT = int(os.getenv("JARVIS_GEMINI_DAILY_LIMIT", "1400"))  # stay under 1500

# Rough token threshold above which input routes to Gemini (large-context tasks).
ROUTER_LOCAL_TOKEN_LIMIT = int(os.getenv("JARVIS_ROUTER_TOKEN_LIMIT", "8000"))

AGENT_MAX_ITERATIONS = int(os.getenv("JARVIS_AGENT_MAX_ITERATIONS", "10"))

KEYRING_SERVICE = "jarvis"

# Integrations (tokens live in Credential Manager under KEYRING_SERVICE;
# only non-secret endpoints/ids belong here or in .env)
CANVAS_BASE_URL = os.getenv("JARVIS_CANVAS_URL", "").rstrip("/")  # e.g. https://school.instructure.com
CANVAS_SYNC_INTERVAL_S = int(os.getenv("JARVIS_CANVAS_SYNC_INTERVAL_S", "1800"))

# Phase 8: proactive
BRIEF_HOUR = int(os.getenv("JARVIS_BRIEF_HOUR", "8"))       # morning brief (local time)
DUE_ALERT_HOUR = int(os.getenv("JARVIS_DUE_ALERT_HOUR", "18"))  # due-tomorrow check

# Deep research
REPORTS_DIR = DATA_DIR / "reports"
RESEARCH_MAX_SOURCES = int(os.getenv("JARVIS_RESEARCH_MAX_SOURCES", "6"))
RESEARCH_SOURCE_CHARS = int(os.getenv("JARVIS_RESEARCH_SOURCE_CHARS", "12000"))

# Voice pipeline
VOICES_DIR = DATA_DIR / "voices"
TTS_VOICE = os.getenv("JARVIS_TTS_VOICE", "en_US-ryan-high")  # bake-off winner; swap freely
WAKEWORD = "hey_jarvis_v0.1"
WAKEWORD_THRESHOLD = float(os.getenv("JARVIS_WAKEWORD_THRESHOLD", "0.5"))
STT_MODEL = os.getenv("JARVIS_STT_MODEL", "small")
SAMPLE_RATE = 16000
FRAME_SAMPLES = 1280  # 80 ms at 16 kHz — openWakeWord's expected frame
VAD_THRESHOLD = float(os.getenv("JARVIS_VAD_THRESHOLD", "0.5"))
VAD_SILENCE_MS = int(os.getenv("JARVIS_VAD_SILENCE_MS", "1000"))  # end-of-speech hangover
VAD_START_TIMEOUT_MS = int(os.getenv("JARVIS_VAD_START_TIMEOUT_MS", "4000"))  # wait for speech
MAX_UTTERANCE_MS = int(os.getenv("JARVIS_MAX_UTTERANCE_MS", "15000"))
PREBUFFER_FRAMES = 12  # ~1s of audio kept before the wakeword fires
VOICE_OUTPUT_COOLDOWN_MS = int(os.getenv("JARVIS_VOICE_OUTPUT_COOLDOWN_MS", "750"))
