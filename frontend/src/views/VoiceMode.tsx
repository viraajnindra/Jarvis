import ArcReactor from "../components/ArcReactor";
import { MicIcon } from "../components/icons";
import { jarvis } from "../ws";

const STATE_TEXT: Record<string, { big: string; sub: string }> = {
  IDLE: { big: "VOICE SYSTEM STANDBY", sub: "Click the mic to activate" },
  STARTING: { big: "STARTING VOICE SYSTEM", sub: "Loading microphone and wake-word detector..." },
  LISTENING: { big: "VOICE SYSTEM ACTIVE", sub: "Listening for your command..." },
  TRANSCRIBING: { big: "TRANSCRIBING", sub: "Understanding what you said..." },
  THINKING: { big: "PROCESSING", sub: "Working on it, Boss..." },
  SPEAKING: { big: "SPEAKING", sub: "..." },
  ERROR: { big: "VOICE ERROR", sub: "Check microphone / logs" },
};

function Waveform({ active }: { active: boolean }) {
  const bars = Array.from({ length: 80 }, (_, i) => i);
  return (
    <div className="flex items-center justify-center gap-[3px] h-16 w-full" aria-hidden="true">
      {bars.map((i) => (
        <span
          key={i}
          className={active ? "wave-bar" : ""}
          style={{
            width: 3,
            height: active ? 6 + ((i * 13) % 40) : 3,
            background: "var(--color-cyan-dim)",
            animationDelay: `${(i % 16) * 0.07}s`,
          }}
        />
      ))}
    </div>
  );
}

export default function VoiceMode({
  active,
  voiceState,
  transcript,
  reply,
  onToggle,
  onChatMode,
}: {
  active: boolean;
  voiceState: string;
  transcript: string;
  reply: string;
  onToggle: () => void;
  onChatMode: () => void;
}) {
  const st = STATE_TEXT[voiceState] ?? STATE_TEXT.IDLE;
  const listening = ["STARTING", "LISTENING", "TRANSCRIBING", "THINKING", "SPEAKING"].includes(voiceState);

  return (
    <div className="hud-panel h-full flex flex-col">
      <div className="flex items-center gap-2 px-4 py-2 border-b border-cyan-faint">
        <span className="panel-title">VOICE SYSTEM</span>
        <span
          className="w-1.5 h-1.5 rounded-full pulse-soft"
          style={{ background: listening ? "var(--color-cyan)" : "var(--color-text-dim)" }}
        />
        <span className="text-text-dim text-[10px] tracking-[0.15em]">{voiceState}</span>
        <button
          onClick={onChatMode}
          className="ml-auto border border-cyan-faint text-cyan text-[10px] tracking-[0.2em] px-2 py-1 hover:bg-cyan-faint"
        >
          CHAT MODE
        </button>
      </div>

      <div className="flex-1 flex flex-col items-center justify-center gap-6 px-6">
        <div className="relative">
          <ArcReactor size={230} spin={listening} />
          <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
            <div className="w-[280px] absolute" style={{ left: -25 }}>
              <Waveform active={voiceState === "LISTENING" || voiceState === "SPEAKING"} />
            </div>
          </div>
        </div>

        <div className="text-center">
          <div className="text-2xl text-cyan text-glow tracking-[0.15em]">{st.big}</div>
          <div className="text-text-dim mt-1 text-sm">{st.sub}</div>
        </div>

        {transcript && (
          <div className="text-center max-w-lg border border-cyan-faint px-4 py-2 text-sm">
            <span className="text-text-dim text-[10px] tracking-widest block mb-1">HEARD</span>
            {transcript}
          </div>
        )}

        {reply && (
          <div className="text-center max-w-lg border border-cyan-faint px-4 py-2 text-sm">
            <span className="text-text-dim text-[10px] tracking-widest block mb-1">REPLY</span>
            {reply}
          </div>
        )}

        <div className="text-text-dim text-[11px]">
          {!active
            ? "Click the mic to enable wake-word listening"
            : voiceState === "SPEAKING"
              ? "Use Push to Talk to interrupt"
              : "Say \"Hey Jarvis\" or use Push to Talk"}
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={onToggle}
            className="rounded-full p-5 border-2 transition-colors"
            style={{
              borderColor: active ? "var(--color-cyan)" : "var(--color-cyan-faint)",
              background: active ? "var(--color-cyan-faint)" : "transparent",
              color: "var(--color-cyan)",
            }}
            title={active ? "Stop voice system" : "Start voice system"}
          >
            <MicIcon size={28} />
          </button>
          {active && (
            <button
              onClick={() => jarvis.pushToTalk()}
              className="border border-cyan-faint text-cyan text-[10px] tracking-[0.2em] px-3 py-2 hover:bg-cyan-faint"
            >
              PUSH TO TALK
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
