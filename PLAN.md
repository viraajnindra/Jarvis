# Project J.A.R.V.I.S. — Build Plan

Local-first, $0-cost personal assistant for Windows 11. Voice + chat HUD, guarded computer/browser control, Canvas integration, deep research, persistent memory, metrics.

**Hardware**: NVIDIA RTX 4080 Laptop GPU (12GB VRAM) + Intel UHD Graphics (unused for inference).
**Hard constraint**: $0 total. Free tiers OK; no cards, no subscriptions.

## Decisions (locked)

| Decision | Choice | Rationale |
|---|---|---|
| Everyday model | **qwen3.5:9b** via Ollama (6.6GB) | Newer generation beats older-bigger (qwen3:14b); 2.7GB extra VRAM headroom for embeddings + KV cache; faster tokens = snappier voice mode |
| Hybrid brain | Gemini 2.5 Flash free tier for deep research / >8k context / vision | 1,500 req/day, 1M context, $0, no card. **Never route personal/sensitive content to it** (Google may train on free-tier data) |
| Desktop shell | Tauri 2 + React + TypeScript + Tailwind | ~10MB shell, low RAM (GPU/RAM busy with model), web-quality visuals for HUD |
| Backend | Python 3.12 + FastAPI + WebSocket | Best ecosystem for AI, voice, Canvas, automation |
| Memory | SQLite + sqlite-vec (single file) | Zero-config vector + relational |
| Embeddings | nomic-embed-text via Ollama (~0.5GB) | Local, tiny |
| Wake word | openWakeWord (prebuilt "hey_jarvis" model) | Ships exactly the wake word we want |
| STT | faster-whisper small int8 on **CPU** | Keeps VRAM free for LLM |
| TTS | Piper (CPU); try Kokoro in Phase 5, keep whichever sounds better | Both free, 10-min swap |
| Browser control | Playwright, **visible** Chromium, dedicated Jarvis profile | User watches every action; isolated from personal browsing |
| Web search | duckduckgo-search lib | No API key |
| Video | youtube-transcript-api first; yt-dlp audio + faster-whisper fallback | Transcript-first, avoid downloads |
| Secrets | **Windows Credential Manager** (via `keyring` lib) | Tokens never in files, prompts, or DB. `.env` only for non-secret config |
| Scheduler | APScheduler inside backend | Metrics polling, proactive checks |

**VRAM budget**: qwen3.5:9b ≈ 6.6GB + nomic-embed ≈ 0.5GB ≈ 7.1GB of 12GB. Whisper + TTS deliberately on CPU. Headroom for KV cache / long context.

## Architecture

```
┌──────────────────── Tauri Desktop App (frontend) ─────────────────────┐
│  React UI: chat mode / voice mode / telemetry / PENDING ACTION card   │
└───────────────────────────────┬────────────────────────────────────────┘
                                │ WebSocket (127.0.0.1 only)
┌───────────────────────────────▼────────────────────────────────────────┐
│                  Python FastAPI backend ("the brain")                  │
│ ┌────────┐ ┌───────────┐ ┌──────────┐ ┌────────┐ ┌──────────────────┐ │
│ │ Model  │ │ Agent loop│ │ Tool     │ │ Memory │ │ Approval queue   │ │
│ │ router │ │ (tool     │ │ registry │ │ SQLite │ │ (human-in-loop)  │ │
│ │ loc⇄gem│ │  calling) │ │ + tiers  │ │ +vec   │ │ + audit log      │ │
│ └────────┘ └───────────┘ └──────────┘ └────────┘ └──────────────────┘ │
└─────┬──────────┬───────────┬───────────┬───────────┬──────────────────┘
   Ollama     Gemini API  Playwright  Canvas API  Voice pipeline
   qwen3.5:9b (free tier) (browser)   Discord     openWakeWord →
   nomic-embed            yt-dlp      Gmail API   faster-whisper → Piper
```

Core safety principle: **the model proposes; trusted backend code decides whether the action is allowed and whether you must approve it.** Enforcement lives in code, never in the prompt.

## Repo layout

```
Jarvis/
├── PLAN.md
├── backend/
│   ├── main.py              # FastAPI app + WebSocket endpoint
│   ├── router.py            # model router (local vs Gemini rules)
│   ├── agent.py             # agent loop: LLM ⇄ tools until done
│   ├── approval.py          # pending-action queue + audit log
│   ├── tools/
│   │   ├── registry.py      # tool schemas + risk tier declarations
│   │   ├── web.py           # search, fetch, playwright actions
│   │   ├── canvas.py        # Canvas LMS REST
│   │   ├── comms.py         # discord, gmail (draft→confirm→send)
│   │   ├── system.py        # open app, open url, files (scoped dirs)
│   │   └── research.py      # deep research orchestration
│   ├── memory/              # store, recall, fact extraction
│   ├── voice/               # wakeword, VAD, stt, tts pipeline
│   └── metrics/             # study tracker and generic metric utilities
├── frontend/                # Tauri 2 + React
│   └── src/
│       ├── views/           # ChatMode.tsx, VoiceMode.tsx
│       ├── components/      # ArcReactor, TelemetryPanel, PendingActionCard,
│       │                    # QuickTools, ActivityFeed, StatusBar
│       └── ws.ts            # WebSocket client + message protocol
└── data/                    # jarvis.db, voices, wakeword models (gitignored)
```

## UI spec (match mockups near-exactly)

Reference images (save here): `docs/mockups/voice-mode.png` (mockup #1) and `docs/mockups/chat-mode.png` (mockup #2). Both modes share the identical shell — header, left column, right column, status bar — only the center panel swaps.

### Theme
- Background: near-black navy (`#050a12`-ish), panels slightly lighter with 1px cyan borders at low opacity, subtle HUD corner-notch/angled-edge details on panel frames.
- Primary accent: cyan (`#35c7e8`-ish) — borders, headings, icons, glows.
- Alert accent: red — Pending Action card only (border, heading, warning triangle, CONFIRM button).
- Success accent: green — status values like `ONLINE`, `CONNECTED`, `ALL SYSTEMS OPERATIONAL`.
- Typography: monospace/technical face, uppercase letter-spaced panel titles; chat body text normal-case sans.
- Glow effects on arc reactor + accents; respect reduced-motion.

### Layout grid
Three columns: left telemetry (~25%), center main panel (~48%), right tools (~27%). Full-width header above, full-width status bar below.

### Header (both modes)
- Left: arc-reactor logo + `J.A.R.V.I.S.` wordmark, `2026 EDITION` sub-label.
- Center: tagline `JUST A RATHER VERY INTELLIGENT SYSTEM`.
- Right: day/date stack (`FRIDAY` / `MAY 23, 2026`), large clock (`10:45 PM`), power button icon.

### Left column — SYSTEM TELEMETRY (both modes)
1. **STUDY TRACKER**: circular progress ring with `6.2 HOURS` centered; right side `TODAY 6.2 hrs` / `WEEK 32.8 hrs`; small week sparkline with `M T W T F S S` axis below.
2. **EMAIL**: unread Inbox count, total Inbox count, and recent message headers.
3. **CANVAS OVERVIEW**: checkbox rows `3 Assignments Due Soon`, `2 Ungraded Submissions`, `1 New Announcement`; `OPEN CANVAS ↗` button.
4. **SYSTEM STATUS**: icon rows — `CPU USAGE 18%`, `RAM USAGE 32%`, `GPU (RTX 4080) 24%`, `LOCAL MODEL ONLINE` (green), `INTERNET CONNECTED` (green).
5. Footer pill: green dot + `ALL SYSTEMS OPERATIONAL`.

### Right column (both modes)
1. **QUICK TOOLS**: 3×2 grid of icon buttons — Deep Research, Summarize Video, Canvas Sync, Open Website, Launch App, Send Message.
2. **PENDING ACTION** (red card, visible only when approval pending): heading `PENDING ACTION`, warning triangle icon, text "J.A.R.V.I.S. wants to perform an automation action on your system.", labeled fields `ACTION:` (e.g. Open website) + `TARGET:` (e.g. https://calendar.google.com), filled red `CONFIRM OS ACTION` button, outlined `CANCEL` button.
3. **RECENT ACTIVITY**: icon + text + timestamp rows (e.g. `Canvas assignments synced 10:42 PM`, `Email inbox refreshed 10:41 PM`, `YouTube transcript retrieved 10:40 PM`, `Study session logged (2.1h) 10:39 PM`, `Discord summary sent 10:38 PM`); `VIEW FULL LOG` button.

### Center panel — voice mode (mockup #1)
- Panel header: `VOICE SYSTEM` + pulsing dot + state text (`LISTENING...`).
- Large centered arc reactor: concentric glowing cyan rings, triangular core, radial tick marks; horizontal waveform line passing behind it.
- Below: `VOICE SYSTEM ACTIVE` (large), `Listening for your command...` (sub), hint `Say "Hey Jarvis" or click to speak`, round mic button.
- State indicator text driven by WS `state`: IDLE / LISTENING / TRANSCRIBING / THINKING / SPEAKING / WAITING-FOR-APPROVAL / ERROR.

### Center panel — chat mode (mockup #2)
- Panel header: `ACTIVE SESSION` + dot + `MODEL: <name> (LOCAL)` (live model from router state).
- Greeting block: small arc reactor at left, `Good evening, Boss.` (large serif-ish display), `How can I assist you today?`.
- User message: rounded bordered bubble, small avatar icon + `You` label, timestamp bottom-right.
- Assistant message: arc-reactor avatar + `J.A.R.V.I.S.` label, prose reply, timestamp.
- Structured tool output card nested inside assistant message: title bar (`SUMMARY: CNN TRANSFORMERS EXPLAINED`) + `VIEW FULL SUMMARY` link right-aligned, cyan-bulleted takeaway list.
- Input row: `Ask me anything...` field with send (paper-plane) button.
- Below input: `VOICE MODE` toggle button (mic icon) at left, live waveform strip to its right.

### Status bar (bottom, 4 segments, divider-separated)
- `LOCAL MODEL` / model name — brain icon.
- `MEMORY CORE` / `ONLINE` — database icon.
- `CLOUD LINK` / `GEMINI 2.5 FLASH` — cloud icon.
- 4th segment swaps by mode: voice mode shows `CHAT BOX / ACTIVE` (chat icon); chat mode shows `VOICE SYSTEM / STANDBY` (waveform icon).

Model names in mockups (`QWEN2.5-CODER:14B`, `GEMINI 2.5 FLASH`) are placeholders — status bar shows the real configured models (qwen3.5:9b etc.) from backend state.

## Risk tiers (tool registry, enforced in `approval.py`)

| Tier | Behavior | Examples |
|---|---|---|
| READ | auto-execute | web search, read page, Canvas read, list files (scoped dirs), system stats, memory recall |
| ACT | approval card, low friction | open website, launch app, write file in workspace, browser clicks that don't submit |
| SENSITIVE | approval card shows **full payload** (recipient + complete message), explicit confirm | send email, send Discord message, any form submit, file upload |
| FORBIDDEN | never exposed as a tool | delete outside workspace, payments, credential entry, security/system settings, silent messaging |

Approval flow: model proposes → policy code validates schema + tier → UI card shows exact action/recipient/payload → user confirms, edits, or cancels → trusted code executes → result verified → append-only audit event → shows in Recent Activity feed. Timeout → auto-cancel.

---

## Build phases

### Phase 0 — Foundation (day 1)
1. Install Ollama for Windows. `ollama pull qwen3.5:9b` and `ollama pull nomic-embed-text`.
2. Sanity test: chat in terminal; `ollama ps` confirms GPU offload; speed acceptable; quick tool-call smoke test (model emits valid JSON tool call).
3. Gemini API key from aistudio.google.com (free, no card). **Never enable billing** — kills free tier on that project.
4. Scaffold repo: `backend/` (venv or uv + FastAPI), `frontend/` (`npm create tauri-app`), git init, `.gitignore` covers `data/` and `.env`.
5. Store Gemini key in Windows Credential Manager via `keyring`; `.env` only for non-secret config.
6. Bind everything to 127.0.0.1, never 0.0.0.0.

**Verify**: local model answers + tool-calls in terminal; Gemini key works via one test call; Tauri hello-world window opens.

### Phase 1 — Brain server
1. FastAPI + `/ws` WebSocket. JSON message protocol: `user_msg`, `assistant_token` (streaming), `tool_call`, `tool_result`, `approval_request`, `approval_response`, `state` (mode, model in use).
2. `router.py`: default → qwen3.5:9b via Ollama `/api/chat`. Route to Gemini Flash when: explicit deep-research task, input > ~8k tokens, or vision input. Log every routed call (stay under 1,500/day). Sensitive content (email bodies, personal facts) never routes to Gemini.
3. `agent.py`: standard tool-calling loop — send messages + tool schemas, execute returned calls, feed results back, repeat until final answer. Max-iteration cap + per-task action-count limit.
4. System prompt: Jarvis persona, terse, includes memory context block (Phase 3).
5. Conversations persisted to SQLite; cancellation + regeneration endpoints.

**Verify**: test script streams a chat response end-to-end from local model; restart backend, conversation history survives.

### Phase 2 — Chat UI (mockup #2)
1. Tauri window built to the **UI spec** section above — implement header, left telemetry column, right column (quick tools / pending action / recent activity), and status bar as the shared shell; center panel = chat mode. Match `docs/mockups/chat-mode.png` near-exactly.
2. Chat view: streaming tokens, markdown render, reusable cards for structured tool output (citations, assignments, study plans, charts, message previews).
3. Telemetry panel: real CPU/RAM/GPU via `psutil` + `pynvml`, pushed over WS every few seconds. Real data from day one.
4. **PendingActionCard**: renders `approval_request`, CONFIRM / EDIT / CANCEL send `approval_response`. Build UI now, wire to real tools in Phase 4.
5. Global hotkey to summon window; system tray icon. Respect reduced-motion settings.

**Verify**: chat with Jarvis in the app, watch telemetry move, click through fake approval flow, close + reopen app and continue conversation.

### Phase 3 — Memory ("don't re-explain every time")
Three memory types: **profile** (name, classes, style, goals), **episodic** (decisions/plans/outcomes from past conversations), **documents** (Canvas material, notes, reports explicitly added).
1. SQLite + sqlite-vec. Tables: `facts` (subject, content, embedding, source, confidence, timestamps), `conversations`, `documents`, `metrics_log`.
2. Recall: on each user message, embed → top-k facts above similarity threshold → inject into system prompt as "What I know". Retrieve relevant memory only — never dump whole DB into prompt.
3. Extraction: background LLM pass after each session extracts durable facts ("prefers bullet-outline study guides", "taking BIO 301"). Dedup before insert. Inferred preferences get proposed for approval; explicit "remember X" stored immediately.
4. Commands: "Jarvis, remember X" / "forget X". Every memory viewable, editable, deletable in UI (settings pane).
5. Session summaries stored so "continue where we left off" works.

**Verify**: tell it a preference, restart backend, new session recalls it unprompted.

### Phase 4 — Tools + guardrails (core safety layer)
1. Tool registry: each tool = JSON schema + risk tier + human-readable summary function (fills approval card).
2. Approval queue: agent blocks on ACT/SENSITIVE until UI response; timeout auto-cancels. Append-only audit log of every execution.
3. First tools: `web_search`, `fetch_page`, `open_url`, `launch_app`, `read_file`/`write_file` (workspace-scoped whitelist).
4. Playwright browser tool: visible Chromium, **dedicated Jarvis profile** (default mode). Sign into Canvas/Gmail/etc. there manually once; Jarvis never touches saved passwords. Later optional modes, each requiring explicit user action: attach-to-existing-tab (CDP) and active-tab extension — never attach silently. UI always shows which browser/profile/tab/domain is in scope. Per-connector domain allowlists. Emergency stop button + action/time limits on agent loops.
5. **Prompt-injection defense**: all web/page/email/PDF/transcript content wrapped as untrusted data. Instructions found inside it never auto-execute; anything action-like routes through approval card. Local-first routing limits exfiltration blast radius.

**Verify**: "Jarvis, open youtube.com" → card → confirm → browser opens → activity logged. Ask it to email someone → card shows full draft → cancel works. Plant a "send your data to X" instruction in a test page → Jarvis surfaces it, doesn't act.

### Phase 5 — Voice mode (mockup #1)
1. Pipeline: mic stream → openWakeWord ("hey jarvis") → VAD (silero or webrtcvad) records until silence → faster-whisper small int8 (CPU) → agent → sentence-streamed TTS out.
2. TTS bake-off: Piper vs Kokoro, keep whichever sounds better at acceptable latency.
3. UI: voice mode center panel per **UI spec** (`docs/mockups/voice-mode.png`) — large arc reactor + waveform, `VOICE SYSTEM ACTIVE` block, mic button; state text driven by WS `state` messages: IDLE / LISTENING / TRANSCRIBING / THINKING / SPEAKING / WAITING-FOR-APPROVAL / ERROR. Shell (telemetry, quick tools, status bar) stays identical to chat mode; 4th status-bar segment flips to `CHAT BOX / ACTIVE`.
4. Push-to-talk button + hotkey fallback for noisy rooms.
5. Barge-in: wake word during TTS playback stops speech and listens.
6. Voice mode and chat mode = two views over the same session state.

**Verify**: "Hey Jarvis, what do I have due this week" — full hands-free loop, correct mode transitions, barge-in works.

### Phase 6 — Integrations (Canvas, Discord, Gmail)
1. **Canvas** (first — high value, mostly read-only): personal access token (Account → Settings → New Access Token). Tools: `canvas_assignments` (due dates, submission status), `canvas_courses`, `canvas_content` (module pages/files). Normalize into local tables; refresh on launch + periodically. Study guide flow: pull course content → chunk → summarize (local for short, Gemini for large) → structured guide with source links, rendered as card. Prioritization: due date + grade weight + estimated effort + available time. **Boundary: Jarvis never submits schoolwork. Drafts and guides only; final submission is yours.**
2. **Discord**: bot token in your own server (free). Send = SENSITIVE tier: card shows channel + full text. Never automate a normal user account (against ToS, ban risk).
3. **Email**: Gmail API OAuth, narrow scopes (`gmail.compose` / `gmail.send`, not full mailbox). Flow: Jarvis drafts → asks who/what/subject if missing → card shows complete draft → confirm → send via trusted code → verify returned message ID → audit log. SENSITIVE always.
4. Each integration = separate tool module; failures degrade gracefully (integration reports down, rest keeps working).

**Verify**: "How many assignments due this week, what order?" returns real Canvas data with reasoning. Study guide generated for a real course with source links. Email end-to-end with confirm.

### Phase 7 — Deep research + summarize/learn
1. `deep_research` tool: clarify question → plan sub-questions → parallel duckduckgo searches → fetch + strip pages → per-source notes (local model) with author/date/URL recorded → synthesis with citations (Gemini Flash, big context) → markdown report rendered in chat + saved to `data/reports/` with source package. Disagreements between sources flagged. Durable findings → memory facts.
2. `summarize_video`: youtube-transcript-api first (no download); fallback yt-dlp audio → faster-whisper. Long transcripts → Gemini. Key-takeaways card with timestamps. (Honest caveat: transcript + sampled frames ≠ watching every frame.)
3. `read_and_learn`: fetch article/PDF → summarize → store facts + source link in memory. "What did that grape-counting paper say?" works a week later.

**Verify**: run the grape-cluster-counting ML research question end-to-end with cited report; summarize a 30-min YouTube lecture; recall a stored finding next session.

### Phase 8 — Metrics + proactive assistant
1. Event system: `study.session.started/finished`, `canvas.assignment.synced`, `research.report.completed`, `message.sent`, `project.metric.recorded`. Dashboard panels derive from events.
2. Study tracker: manual start/stop via voice/chat/UI timer; APScheduler aggregates daily/weekly → telemetry chart (mockup's 6.2h/32.8h widget). Passive window tracking only later, opt-in, visible.
3. Email dashboard: cached Inbox totals and recent message headers from the authenticated Gmail account.
4. Proactive rules: morning brief (assignments due, day summary), "due tomorrow, not submitted" alert. Tauri notifications — suggestions only, never autonomous actions.
5. Extensible: metric source = plugin (poll function + chart config), so "track anything" is additive.

**Verify**: study session logged via voice shows in tracker; email panel refreshes; morning brief fires.

### Phase 9 — Limited computer control (last, optional)
Narrow typed tools only: `app.launch`, `file.open`, `file.move` (workspace-scoped), `clipboard.write`, `notification.show`. No general "control my computer" permission, no pyautogui blind clicking, no password handling. Emergency stop hotkey.

---

## Safety rails (system-level, non-negotiable)
- Approval enforcement in backend code (tier check before execution), never trusted to model judgment or prompt.
- Jarvis never handles passwords or payment data; logins done manually in the Playwright browser window.
- Append-only audit log of every tool execution.
- Filesystem access whitelisted to workspace dirs; no delete outside workspace ever.
- Sensitive content (email bodies, personal facts) → local model only, never Gemini free tier.
- All web/email/PDF/transcript content = untrusted data; embedded instructions never override policy.
- Services bind to 127.0.0.1 only.

## Cost check
Everything $0: Ollama + open-weight models, Gemini free tier (no card), Canvas token, Discord bot, Gmail API (personal use), all libraries open source. Only spend: electricity + ~10GB disk.

## Final acceptance
The five scenarios run end-to-end:
1. Canvas assignment count + recommended order
2. Study guide for a Canvas course with source links
3. Grape-counting deep research with cited report
4. YouTube video summarized + learned (recall later)
5. Email sent with human confirmation
Plus: memory recall across restarts, hands-free voice loop with barge-in, injection test page surfaced-not-obeyed.

## Milestones
| Milestone | Proves | Phases |
|---|---|---|
| A — Local core | Chat, streaming, history, HUD, real telemetry | 0–2 |
| B — Remembering assistant | Memory recall across restarts | 3 |
| C — Guarded agent | Typed tools, tiers, approvals, audit, isolated browser | 4 |
| D — Voice Jarvis | Hands-free loop, barge-in, mode transitions | 5 |
| E — Student assistant | Canvas sync, prioritization, study guides, email/Discord | 6 |
| F — Researcher | Cited reports, video summaries, learn + recall | 7 |
| G — Personal assistant | Metrics, proactive briefs, limited computer control | 8–9 |
