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
  const [canvasUrl, setCanvasUrl] = useState<string>("");
  const [mode, setMode] = useState<"chat" | "voice">("chat");
  const [notif, setNotif] = useState<{ title: string; body: string } | null>(null);
  const notifTimer = useRef<number | undefined>(undefined);
  const [voiceActive, setVoiceActive] = useState(false);
  const [voiceState, setVoiceState] = useState("IDLE");
  const [transcript, setTranscript] = useState("");
  const [voiceReply, setVoiceReply] = useState("");
  const [restartOpen, setRestartOpen] = useState(false);
  const [shutdownOpen, setShutdownOpen] = useState(false);
  const convRef = useRef<string | undefined>(
    localStorage.getItem("jarvis.conversation") ?? undefined,
  );

  useEffect(() => {
    fetch("http://127.0.0.1:8735/health")
      .then((r) => r.json())
      .then((h) => setCanvasUrl(h.canvas_url || ""))
      .catch(() => {});
  }, []);

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
          setVoiceReply(msg.content);
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
        case "notification":
          setNotif({ title: msg.title, body: msg.body });
          window.clearTimeout(notifTimer.current);
          notifTimer.current = window.setTimeout(() => setNotif(null), 20000);
          setActivity((a) => [{ text: msg.title, time: now() }, ...a]);
          // Native OS notification only if permission already granted — never
          // prompt from a background message (the in-app toast always shows).
          if ("Notification" in window && Notification.permission === "granted") {
            new Notification(msg.title, { body: msg.body });
          }
          break;
        case "memory_list":
          setFacts(msg.facts);
          break;
        case "voice_state":
          setVoiceState(msg.state);
          if (msg.state === "IDLE" || msg.state === "ERROR") setVoiceActive(false);
          break;
        case "voice_transcript":
          setTranscript(msg.text);
          setVoiceReply("");
          setMessages((m) => [...m, { role: "user", content: msg.text, time: now() }]);
          break;
        case "error":
          setActivity((a) => [{ text: `Error: ${msg.message}`, time: now() }, ...a]);
          break;
      }
    });
    return unsub;
  }, []);

  const emergencyStop = () => {
    jarvis.emergencyStop();
    setVoiceActive(false);
    setPending(null);
    setStreaming("");
  };

  const shutDown = async () => {
    emergencyStop();
    setShutdownOpen(false);
    try {
      await fetch("http://127.0.0.1:8735/shutdown", { method: "POST" });
    } catch {
      // The desktop shell should still close if the local service is unavailable.
    }
    try {
      const { invoke } = await import("@tauri-apps/api/core");
      await invoke("quit_app");
    } catch {
      window.close();
    }
  };

  const restart = async () => {
    emergencyStop();
    setRestartOpen(false);
    try {
      await fetch("http://127.0.0.1:8735/restart", { method: "POST" });
    } catch {
      // The desktop app restart can still recover the UI if the local service is unavailable.
    }
    try {
      const { invoke } = await import("@tauri-apps/api/core");
      await invoke("restart_app");
    } catch {
      window.location.reload();
    }
  };

  // Emergency stop: Ctrl+Shift+X — global via Tauri when running as the app,
  // plus an in-window fallback for the plain-browser dev case.
  useEffect(() => {
    let unlisten: (() => void) | undefined;
    import("@tauri-apps/api/event")
      .then(({ listen }) => listen("emergency-stop", emergencyStop))
      .then((f) => (unlisten = f))
      .catch(() => {}); // not running inside Tauri
    const onKey = (e: KeyboardEvent) => {
      if (e.ctrlKey && e.shiftKey && e.key.toUpperCase() === "X") {
        e.preventDefault();
        emergencyStop();
      }
    };
    window.addEventListener("keydown", onKey);
    return () => {
      unlisten?.();
      window.removeEventListener("keydown", onKey);
    };
  }, []);

  const send = (text: string) => {
    setMessages((m) => [...m, { role: "user", content: text, time: now() }]);
    jarvis.sendUserMsg(text, convRef.current);
  };

  const startVoice = () => {
    setTranscript("");
    setVoiceReply("");
    setVoiceState("STARTING");
    setVoiceActive(true);
    jarvis.voiceStart();
  };

  const stopVoice = () => {
    jarvis.voiceStop();
    setVoiceActive(false);
    setVoiceState("IDLE");
    setTranscript("");
    setVoiceReply("");
  };

  const toggleVoice = () => {
    if (voiceActive) stopVoice();
    else startVoice();
  };

  const openVoiceMode = () => {
    setMode("voice");
    if (!voiceActive) startVoice();
  };

  const openChatMode = () => {
    if (voiceActive) stopVoice();
    setMode("chat");
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
      <Header
        onOpenMemory={() => setMemoryOpen(true)}
        onEmergencyStop={emergencyStop}
        onRestart={() => setRestartOpen(true)}
        onShutDown={() => setShutdownOpen(true)}
      />
      {restartOpen && (
        <div className="absolute inset-0 z-50 flex items-center justify-center bg-bg/80 px-4">
          <div className="hud-panel w-full max-w-md p-5">
            <div className="panel-title">Confirm restart</div>
            <p className="mt-3 text-sm text-text">
              This will halt active work, restart the local J.A.R.V.I.S. service, and relaunch the app.
            </p>
            <div className="mt-5 flex justify-end gap-3">
              <button
                className="border border-cyan-faint px-4 py-2 text-[11px] text-text-dim hover:bg-cyan-faint"
                onClick={() => setRestartOpen(false)}
              >
                CANCEL
              </button>
              <button
                className="border border-cyan px-4 py-2 text-[11px] text-cyan hover:bg-cyan-faint"
                onClick={restart}
              >
                RESTART
              </button>
            </div>
          </div>
        </div>
      )}
      {shutdownOpen && (
        <div className="absolute inset-0 z-50 flex items-center justify-center bg-bg/80 px-4">
          <div className="hud-panel w-full max-w-md p-5">
            <div className="panel-title">Confirm shutdown</div>
            <p className="mt-3 text-sm text-text">
              This will halt active work, stop the local J.A.R.V.I.S. service, and close the app.
            </p>
            <div className="mt-5 flex justify-end gap-3">
              <button
                className="border border-cyan-faint px-4 py-2 text-[11px] text-text-dim hover:bg-cyan-faint"
                onClick={() => setShutdownOpen(false)}
              >
                CANCEL
              </button>
              <button
                className="border border-alert px-4 py-2 text-[11px] text-alert hover:bg-alert-dim"
                onClick={shutDown}
              >
                SHUT DOWN
              </button>
            </div>
          </div>
        </div>
      )}
      {memoryOpen && <MemoryPane facts={facts} onClose={() => setMemoryOpen(false)} />}
      {notif && (
        <div className="hud-panel absolute top-14 right-4 z-50 max-w-sm px-4 py-3 border border-cyan-faint">
          <div className="flex items-center justify-between gap-4">
            <span className="text-cyan text-[11px] tracking-[0.2em]">{notif.title.toUpperCase()}</span>
            <button
              onClick={() => setNotif(null)}
              className="text-text-dim hover:text-cyan text-xs"
            >
              ✕
            </button>
          </div>
          <div className="text-[11px] mt-1 whitespace-pre-wrap">{notif.body}</div>
        </div>
      )}
      <main className="flex-1 grid grid-cols-[25%_1fr_27%] gap-3 p-3 min-h-0">
        <TelemetryPanel t={telemetry} canvasUrl={canvasUrl} />
        {mode === "chat" ? (
          <ChatMode
            messages={messages}
            streaming={streaming}
            state={state}
            model={model}
            onSend={send}
            draft={draft}
            setDraft={setDraft}
            onVoiceMode={openVoiceMode}
          />
        ) : (
          <VoiceMode
            active={voiceActive}
            voiceState={voiceState}
            transcript={transcript}
            reply={voiceReply}
            onToggle={toggleVoice}
            onChatMode={openChatMode}
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
