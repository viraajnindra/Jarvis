import { useEffect, useRef, useState } from "react";
import ReactMarkdown from "react-markdown";
import ArcReactor from "../components/ArcReactor";
import { SendIcon, MicIcon, UserIcon } from "../components/icons";

export type ChatMessage = { role: "user" | "assistant"; content: string; time: string };

function Waveform({ active }: { active: boolean }) {
  const bars = Array.from({ length: 48 }, (_, i) => i);
  return (
    <div className="flex items-center gap-[2px] h-6 flex-1 overflow-hidden" aria-hidden="true">
      {bars.map((i) => (
        <span
          key={i}
          className={active ? "wave-bar" : ""}
          style={{
            width: 2,
            height: active ? 4 + ((i * 7) % 14) : 2,
            background: "var(--color-cyan-dim)",
            animationDelay: `${(i % 12) * 0.09}s`,
          }}
        />
      ))}
    </div>
  );
}

export default function ChatMode({
  messages,
  streaming,
  state,
  model,
  onSend,
  draft,
  setDraft,
  onVoiceMode,
}: {
  messages: ChatMessage[];
  streaming: string;
  state: string;
  model: string;
  onSend: (text: string) => void;
  draft: string;
  setDraft: (v: string) => void;
  onVoiceMode: () => void;
}) {
  const scrollRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const [greetingTime] = useState(() => {
    const h = new Date().getHours();
    return h < 12 ? "morning" : h < 18 ? "afternoon" : "evening";
  });

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight });
  }, [messages, streaming]);

  const busy = state === "thinking";

  const submit = () => {
    const text = draft.trim();
    if (!text || busy) return;
    onSend(text);
    setDraft("");
  };

  return (
    <div className="hud-panel h-full flex flex-col">
      <div className="flex items-center gap-2 px-4 py-2 border-b border-cyan-faint">
        <span className="panel-title">ACTIVE SESSION</span>
        <span
          className="w-1.5 h-1.5 rounded-full pulse-soft"
          style={{ background: busy ? "var(--color-cyan)" : "var(--color-ok)" }}
        />
        <span className="text-text-dim text-[10px] tracking-[0.15em]">
          MODEL: {model.toUpperCase()} (LOCAL)
        </span>
      </div>

      <div ref={scrollRef} className="chat-scroll flex-1 overflow-y-auto px-4 py-3 space-y-3">
        {messages.length === 0 && !streaming && (
          <div className="flex items-center gap-4 mt-6">
            <ArcReactor size={72} />
            <div>
              <div className="text-3xl" style={{ fontFamily: "var(--font-display)" }}>
                Good {greetingTime}, Boss.
              </div>
              <div className="text-text-dim mt-1 text-sm">How can I assist you today?</div>
            </div>
          </div>
        )}

        {messages.map((m, i) =>
          m.role === "user" ? (
            <div key={i} className="border border-cyan-faint rounded-md px-3 py-2 ml-8">
              <div className="flex items-center gap-2 text-[10px] text-text-dim mb-1">
                <UserIcon size={12} /> You
              </div>
              <div className="text-sm">{m.content}</div>
              <div className="text-right text-[9px] text-text-dim mt-1">{m.time}</div>
            </div>
          ) : (
            <div key={i} className="flex gap-2 mr-8">
              <div className="shrink-0 mt-1">
                <ArcReactor size={26} spin={false} />
              </div>
              <div className="flex-1">
                <div className="text-[10px] text-cyan tracking-wider mb-1">J.A.R.V.I.S.</div>
                <div className="text-sm leading-relaxed">
                  <ReactMarkdown>{m.content}</ReactMarkdown>
                </div>
                <div className="text-[9px] text-text-dim mt-1">{m.time}</div>
              </div>
            </div>
          ),
        )}

        {streaming && (
          <div className="flex gap-2 mr-8">
            <div className="shrink-0 mt-1">
              <ArcReactor size={26} spin={false} />
            </div>
            <div className="flex-1">
              <div className="text-[10px] text-cyan tracking-wider mb-1">J.A.R.V.I.S.</div>
              <div className="text-sm leading-relaxed">
                <ReactMarkdown>{streaming}</ReactMarkdown>
              </div>
            </div>
          </div>
        )}
      </div>

      <div className="px-4 pb-3">
        <div className="flex items-center border border-cyan-faint rounded-md">
          <input
            ref={inputRef}
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && submit()}
            placeholder="Ask me anything..."
            className="flex-1 bg-transparent outline-none px-3 py-2.5 text-sm placeholder:text-text-dim"
          />
          <button onClick={submit} disabled={busy} className="text-cyan px-3 disabled:opacity-40">
            <SendIcon size={18} />
          </button>
        </div>
        <div className="flex items-center gap-3 mt-2">
          <button
            onClick={onVoiceMode}
            className="flex items-center gap-2 border border-cyan-faint px-3 py-1.5 text-[10px] tracking-[0.2em] text-cyan hover:bg-cyan-faint"
            title="Switch to voice mode"
          >
            <MicIcon size={13} /> VOICE MODE
          </button>
          <Waveform active={busy} />
        </div>
      </div>
    </div>
  );
}
