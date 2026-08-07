# J.A.R.V.I.S.

> A local-first Windows desktop assistant that combines voice, chat, personal
> productivity tools, and human-approved automation in a privacy-conscious UI.

J.A.R.V.I.S. is a full-stack personal assistant built as a desktop application,
not a browser demo. It runs a local model through Ollama, keeps everyday data on
the machine, and uses a trusted backend to control tools and approvals. The
result is a voice-enabled assistant that can help with research, email, Canvas,
study tracking, and browser tasks without giving an LLM unrestricted control of
the computer.

## Highlights

- **Local AI by default** — routes everyday prompts to Qwen via Ollama and keeps
  embeddings, memory, voice processing, and application data local.
- **Voice assistant pipeline** — openWakeWord → VAD → faster-whisper → agent →
  Piper TTS, with push-to-talk interruption and speaker-echo protection.
- **Human-in-the-loop automation** — tool calls are assigned risk tiers; sensitive
  actions require an approval card before trusted code executes them.
- **Productivity integrations** — Gmail, Canvas LMS, Discord, web research,
  browser control, YouTube summaries, study tracking, and scheduled briefings.
- **Persistent memory** — SQLite + sqlite-vec stores explicit and inferred facts
  locally for retrieval in later conversations.
- **Desktop-first experience** — a Tauri, React, and TypeScript HUD provides chat,
  telemetry, approvals, voice status, and recent activity in one application.

## How it is built

```text
┌──────────────────────────────────────────────────────────────┐
│ Tauri desktop shell                                            │
│ React + TypeScript UI · chat · voice · telemetry · approvals   │
└───────────────────────────────┬──────────────────────────────┘
                                │ WebSocket on 127.0.0.1
┌───────────────────────────────▼──────────────────────────────┐
│ FastAPI backend                                                │
│ agent loop · model router · tool registry · approval queue     │
│ SQLite/vector memory · scheduler · audit log                   │
└───────┬──────────────────┬──────────────────┬────────────────┘
        │                  │                  │
  Ollama + Qwen      Voice pipeline       Integrations
  local embeddings   wake word / STT/TTS  Gmail · Canvas · Discord
```

### Request flow

1. The React client sends a chat or voice request over a localhost WebSocket.
2. FastAPI builds the model context using recent conversation history and relevant
   local memories.
3. The agent either answers directly or proposes tool calls.
4. The tool registry applies a `READ`, `ACT`, or `SENSITIVE` policy before calling
   integration code; approval is required where appropriate.
5. Events stream back to the desktop UI, while voice replies are synthesized and
   played locally.

### Technology choices

| Area | Implementation |
| --- | --- |
| Desktop UI | Tauri 2, React 19, TypeScript, Vite, Tailwind CSS |
| API and orchestration | Python 3.12, FastAPI, WebSockets, APScheduler |
| Local AI | Ollama, Qwen, nomic-embed-text |
| Voice | openWakeWord, faster-whisper, Piper, sounddevice |
| Memory | SQLite, sqlite-vec |
| Automation | Playwright, Gmail API, Canvas API, Discord API |
| Research | DuckDuckGo search, Beautiful Soup, YouTube transcripts / audio fallback |

## Privacy and safety by design

The important boundary in this project is: **the model proposes; trusted backend
code decides what may execute.**

- The backend binds to `127.0.0.1`; the desktop client is the intended interface.
- Secrets are stored with Windows Credential Manager through `keyring`, never in
  source files or the SQLite database.
- `.env` files, local databases, downloaded voice models, reports, and OAuth client
  files are excluded from Git.
- Browser automation uses a dedicated visible profile so actions are inspectable.
- Email and web content are treated as untrusted data, not instructions.
- An audit log records tool execution, approval, denial, and emergency-stop events.

## Project structure

```text
backend/
  agent.py          # LLM/tool loop and response streaming
  main.py           # FastAPI app and WebSocket protocol
  router.py         # local vs. cloud model routing rules
  memory/           # SQLite + vector recall and fact extraction
  tools/            # integrations, policies, and tool registry
  voice/            # wake word, recording, STT, TTS, playback
frontend/
  src/              # React views, components, and WebSocket client
  src-tauri/        # native desktop shell
data/               # local-only models, database, reports (gitignored)
```

## Run locally

### Prerequisites

- Windows 11
- Python 3.12+ and [uv](https://docs.astral.sh/uv/)
- Node.js and npm
- Rust toolchain (for Tauri)
- [Ollama](https://ollama.com/) with a local chat model and embedding model

```powershell
# Install backend dependencies
Set-Location backend
uv sync

# Install frontend dependencies
Set-Location ..\frontend
npm install

# From the repository root, launch the backend and Tauri app
Set-Location ..
.\start.ps1
```

The exact Ollama model names are configurable through `JARVIS_LOCAL_MODEL` and
`JARVIS_EMBED_MODEL`. Voice models and optional integrations are intentionally
local setup steps and are not committed to this repository.

## Optional integrations

Gmail, Canvas, and Discord are optional. Their credentials belong in Windows
Credential Manager; follow the scripts in `backend/scripts/` to configure them.
Never commit OAuth JSON, tokens, `.env` files, or the `data/` directory.

## Resume summary

Built a local-first, security-conscious AI desktop assistant using **Tauri,
React, TypeScript, FastAPI, WebSockets, Ollama, SQLite vector search, and a
complete wake-word/STT/TTS voice pipeline**. Designed a tool-policy and
human-approval layer that separates LLM planning from privileged execution.

## License

This project currently has no license file. Add one before distributing or
accepting outside contributions.
