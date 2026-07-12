import { useEffect, useRef, useState } from "react";
import Header from "./components/Header";
import TelemetryPanel from "./components/TelemetryPanel";
import QuickTools from "./components/QuickTools";
import PendingActionCard, { PendingAction } from "./components/PendingActionCard";
import ActivityFeed, { ActivityItem } from "./components/ActivityFeed";
import StatusBar from "./components/StatusBar";
import MemoryPane from "./components/MemoryPane";
import ChatMode, { ChatMessage } from "./views/ChatMode";
import VoiceMode from "./views/VoiceMode";
import { jarvis, Fact, ServerMsg, Telemetry } from "./ws";

const LOCAL_MODEL = "qwen3.5:9b";
const CLOUD_MODEL = "Gemini 3.5 Flash";

function now() {
  return new Date().toLocaleTimeString("en-US", { hour: "numeric", minute: "2-digit" });
}

export default function App() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [streaming, setStreaming] = useState("");
  const [state, setState] = useState("idle");
  const [model, setModel] = useState(LOCAL_MODEL);
  const [telemetry, setTelemetry] = useState<Telemetry | null>(null);
  const [pending, setPending] = useState<PendingAction | null>(null);
  const [activity, setActivity] = useState<ActivityItem[]>([]);
  const [connected, setConnected] = useState(false);
  const [draft, setDraft] = useState("");
  const [facts, setFacts] = useState<Fact[]>([]);
  const [memoryOpen, setMemoryOpen] = useState(false);
  const [mode, setMode] = useState<"chat" | "voice">("chat");
  const [voiceActive, setVoiceActive] = useState(false);
  const [voiceState, setVoiceState] = useState("IDLE");
  const [transcript, setTranscript] = useState("");
  const convRef = useRef<string | undefined>(
    localStorage.getItem("jarvis.conversation") ?? undefined,
  );

  useEffect(() => {
    jarvis.connect();
    const unsub = jarvis.subscribe((msg: ServerMsg) => {
      switch (msg.type) {
        case "state":
          if (msg.state === "connected") setConnected(true);
          else if (msg.state === "disconnected") setConnected(false);
          else setState(msg.state);
          if (msg.model) setModel(msg.model);
          if (msg.conversation_id) {
            convRef.current = msg.conversation_id;
            localStorage.setItem("jarvis.conversation", msg.conversation_id);
          }
          break;
        case "assistant_token":
          setStreaming((s) => s + msg.content);
          break;
        case "assistant_done":
          setStreaming("");
          setMessages((m) => [...m, { role: "assistant", content: msg.content, time: now() }]);
          setActivity((a) => [{ text: "Reply generated", time: now() }, ...a]);
          break;
        case "telemetry":
          setTelemetry(msg);
          break;
        case "approval_request":
          setPending({ id: msg.id, action: msg.action, target: msg.target, detail: msg.detail });
          break;
        case "approval_expired":
          setPending((p) => (p && p.id === msg.id ? null : p));
          setActivity((a) => [{ text: "Approval timed out — cancelled", time: now() }, ...a]);
          break;
        case "activity":
          setActivity((a) => [{ text: msg.text, time: now() }, ...a]);
          break;
        case "memory_list":
          setFacts(msg.facts);
          break;
        case "voice_state":
          setVoiceState(msg.state);
          break;
        case "voice_transcript":
          setTranscript(msg.text);
          setMessages((m) => [...m, { role: "user", content: msg.text, time: now() }]);
          break;
        case "error":
          setActivity((a) => [{ text: `Error: ${msg.message}`, time: now() }, ...a]);
          break;
      }
    });
    return unsub;
  }, []);

  const send = (text: string) => {
    setMessages((m) => [...m, { role: "user", content: text, time: now() }]);
    jarvis.sendUserMsg(text, convRef.current);
  };

  const toggleVoice = () => {
    if (voiceActive) {
      jarvis.voiceStop();
      setVoiceActive(false);
    } else {
      jarvis.voiceStart();
      setVoiceActive(true);
    }
  };

  const respondApproval = (id: string, approved: boolean) => {
    jarvis.approvalResponse(id, approved);
    setActivity((a) => [
      { text: `Action ${approved ? "confirmed" : "cancelled"}`, time: now() },
      ...a,
    ]);
    setPending(null);
  };

  return (
    <div className="h-full flex flex-col relative">
      <Header onOpenMemory={() => setMemoryOpen(true)} />
      {memoryOpen && <MemoryPane facts={facts} onClose={() => setMemoryOpen(false)} />}
      <main className="flex-1 grid grid-cols-[25%_1fr_27%] gap-3 p-3 min-h-0">
        <TelemetryPanel t={telemetry} />
        {mode === "chat" ? (
          <ChatMode
            messages={messages}
            streaming={streaming}
            state={state}
            model={model}
            onSend={send}
            draft={draft}
            setDraft={setDraft}
            onVoiceMode={() => setMode("voice")}
          />
        ) : (
          <VoiceMode
            active={voiceActive}
            voiceState={voiceState}
            transcript={transcript}
            onToggle={toggleVoice}
            onChatMode={() => setMode("chat")}
          />
        )}
        <div className="flex flex-col gap-3 min-h-0">
          <QuickTools onPick={(p) => setDraft(p)} />
          {pending && <PendingActionCard action={pending} onRespond={respondApproval} />}
          <ActivityFeed items={activity} />
        </div>
      </main>
      <StatusBar
        localModel={LOCAL_MODEL}
        memoryOnline={connected}
        cloudModel={CLOUD_MODEL}
        voiceMode={mode === "voice"}
      />
    </div>
  );
}
