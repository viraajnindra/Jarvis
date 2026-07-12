import { useEffect, useState } from "react";
import { jarvis, Fact } from "../ws";
import Panel from "./Panel";
import { DbIcon } from "./icons";

export default function MemoryPane({ facts, onClose }: { facts: Fact[]; onClose: () => void }) {
  const [editing, setEditing] = useState<number | null>(null);
  const [editText, setEditText] = useState("");
  const [newFact, setNewFact] = useState("");

  useEffect(() => {
    jarvis.memoryList();
  }, []);

  const saveEdit = (id: number) => {
    if (editText.trim()) jarvis.memoryUpdate(id, editText.trim());
    setEditing(null);
  };

  return (
    <div
      className="absolute inset-0 z-50 flex items-center justify-center"
      style={{ background: "#050a12cc" }}
      onClick={onClose}
    >
      <div className="w-[640px] max-h-[70%] flex" onClick={(e) => e.stopPropagation()}>
        <Panel title="MEMORY CORE" className="flex-1 flex flex-col">
          <div className="flex items-center gap-2 mb-2">
            <input
              value={newFact}
              onChange={(e) => setNewFact(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && newFact.trim()) {
                  jarvis.memoryAdd(newFact.trim());
                  setNewFact("");
                }
              }}
              placeholder="Add a fact..."
              className="flex-1 bg-transparent border border-cyan-faint px-2 py-1.5 text-[12px] outline-none placeholder:text-text-dim"
            />
            <button
              onClick={onClose}
              className="border border-cyan-faint text-cyan px-3 py-1.5 text-[10px] tracking-[0.2em] hover:bg-cyan-faint"
            >
              CLOSE
            </button>
          </div>
          <div className="chat-scroll overflow-y-auto space-y-1.5 pr-1">
            {facts.length === 0 && (
              <div className="text-text-dim text-[11px] flex items-center gap-2 py-4">
                <DbIcon size={14} /> Memory core empty. Say "Jarvis, remember ..." or add facts
                above.
              </div>
            )}
            {facts.map((f) => (
              <div key={f.id} className="border border-cyan-faint px-2 py-1.5 text-[11px]">
                {editing === f.id ? (
                  <input
                    autoFocus
                    value={editText}
                    onChange={(e) => setEditText(e.target.value)}
                    onKeyDown={(e) => e.key === "Enter" && saveEdit(f.id)}
                    onBlur={() => saveEdit(f.id)}
                    className="w-full bg-transparent border-b border-cyan outline-none"
                  />
                ) : (
                  <div className="flex items-start gap-2">
                    <span className="flex-1">{f.content}</span>
                    <span
                      className="text-[9px] tracking-wider shrink-0"
                      style={{
                        color: f.source === "explicit" ? "var(--color-ok)" : "var(--color-text-dim)",
                      }}
                    >
                      {f.source.toUpperCase()}
                    </span>
                    <button
                      onClick={() => {
                        setEditing(f.id);
                        setEditText(f.content);
                      }}
                      className="text-cyan text-[10px] hover:underline shrink-0"
                    >
                      EDIT
                    </button>
                    <button
                      onClick={() => jarvis.memoryDelete(f.id)}
                      className="text-[10px] hover:underline shrink-0"
                      style={{ color: "var(--color-alert)" }}
                    >
                      DEL
                    </button>
                  </div>
                )}
              </div>
            ))}
          </div>
        </Panel>
      </div>
    </div>
  );
}
