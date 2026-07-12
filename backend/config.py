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

GEMINI_MODEL = os.getenv("JARVIS_GEMINI_MODEL", "gemini-2.5-flash")
GEMINI_DAILY_LIMIT = int(os.getenv("JARVIS_GEMINI_DAILY_LIMIT", "1400"))  # stay under 1500

# Rough token threshold above which input routes to Gemini (large-context tasks).
ROUTER_LOCAL_TOKEN_LIMIT = int(os.getenv("JARVIS_ROUTER_TOKEN_LIMIT", "8000"))

AGENT_MAX_ITERATIONS = int(os.getenv("JARVIS_AGENT_MAX_ITERATIONS", "10"))

KEYRING_SERVICE = "jarvis"
