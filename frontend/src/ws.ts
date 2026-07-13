// WebSocket client for the Jarvis backend. Singleton with auto-reconnect.

export type ServerMsg =
  | { type: "state"; state: string; model?: string; conversation_id?: string }
  | { type: "assistant_token"; content: string }
  | { type: "assistant_done"; content: string }
  | { type: "tool_call"; name: string; arguments: unknown }
  | { type: "tool_result"; name: string; result: unknown }
  | {
      type: "telemetry";
      cpu_pct: number;
      ram_pct: number;
      gpu: { name: string; util_pct: number; vram_used_gb: number; vram_total_gb: number } | null;
      model_online: boolean;
      internet: boolean;
      study: {
        today_h: number;
        week_h: number;
        days: number[];
        active: boolean;
        active_since: number | null;
        active_note: string | null;
      } | null;
      lovable: { apps: number | null; views: number | null; updated: number } | null;
      canvas: { due_soon: number; ungraded: number; announcements: number } | null;
    }
  | { type: "approval_request"; id: string; action: string; target: string; detail?: string }
  | { type: "approval_expired"; id: string }
  | { type: "activity"; text: string }
  | { type: "notification"; title: string; body: string }
  | { type: "event"; name: string; payload: Record<string, unknown> }
  | { type: "memory_list"; facts: Fact[] }
  | { type: "voice_state"; state: string }
  | { type: "voice_transcript"; text: string }
  | { type: "error"; message: string };

export type Fact = {
  id: number;
  subject: string;
  content: string;
  source: "explicit" | "inferred" | "document";
  confidence: number;
  created_at: number;
};

export type Telemetry = Extract<ServerMsg, { type: "telemetry" }>;

const WS_URL = "ws://127.0.0.1:8735/ws";

type Listener = (msg: ServerMsg) => void;

class JarvisSocket {
  private ws: WebSocket | null = null;
  private listeners = new Set<Listener>();
  private retryMs = 1000;
  connected = false;

  connect() {
    if (this.ws && this.ws.readyState <= WebSocket.OPEN) return;
    this.ws = new WebSocket(WS_URL);
    this.ws.onopen = () => {
      this.connected = true;
      this.retryMs = 1000;
      this.emit({ type: "state", state: "connected" });
    };
    this.ws.onmessage = (ev) => {
      try {
        this.emit(JSON.parse(ev.data));
      } catch {
        // malformed frame, ignore
      }
    };
    this.ws.onclose = () => {
      this.connected = false;
      this.emit({ type: "state", state: "disconnected" });
      setTimeout(() => this.connect(), this.retryMs);
      this.retryMs = Math.min(this.retryMs * 2, 15000);
    };
    this.ws.onerror = () => this.ws?.close();
  }

  private emit(msg: ServerMsg) {
    this.listeners.forEach((fn) => fn(msg));
  }

  subscribe(fn: Listener): () => void {
    this.listeners.add(fn);
    return () => this.listeners.delete(fn);
  }

  private send(obj: object) {
    if (this.ws?.readyState === WebSocket.OPEN) this.ws.send(JSON.stringify(obj));
  }

  sendUserMsg(content: string, conversationId?: string) {
    this.send({ type: "user_msg", content, conversation_id: conversationId });
  }
  cancel() {
    this.send({ type: "cancel" });
  }
  regenerate(conversationId: string) {
    this.send({ type: "regenerate", conversation_id: conversationId });
  }
  approvalResponse(id: string, approved: boolean) {
    this.send({ type: "approval_response", id, approved });
  }
  memoryList() {
    this.send({ type: "memory_list" });
  }
  memoryDelete(id: number) {
    this.send({ type: "memory_delete", id });
  }
  memoryUpdate(id: number, content: string) {
    this.send({ type: "memory_update", id, content });
  }
  memoryAdd(content: string) {
    this.send({ type: "memory_add", content });
  }
  emergencyStop() {
    this.send({ type: "emergency_stop" });
  }
  studyStart() {
    this.send({ type: "study_start" });
  }
  studyStop() {
    this.send({ type: "study_stop" });
  }
  voiceStart() {
    this.send({ type: "voice_start" });
  }
  voiceStop() {
    this.send({ type: "voice_stop" });
  }
  pushToTalk() {
    this.send({ type: "push_to_talk" });
  }
}

export const jarvis = new JarvisSocket();
