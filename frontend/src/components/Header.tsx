import { useEffect, useRef, useState } from "react";
import ArcReactor from "./ArcReactor";
import { DbIcon, PowerIcon } from "./icons";

type HeaderProps = {
  onOpenMemory?: () => void;
  onEmergencyStop?: () => void;
  onRestart?: () => void;
  onShutDown?: () => void;
};

export default function Header({ onOpenMemory, onEmergencyStop, onRestart, onShutDown }: HeaderProps) {
  const [now, setNow] = useState(new Date());
  const [powerOpen, setPowerOpen] = useState(false);
  const [powerMenuPosition, setPowerMenuPosition] = useState<{ left: number; top: number }>();
  const powerMenu = useRef<HTMLDivElement>(null);
  const powerButton = useRef<HTMLButtonElement>(null);
  useEffect(() => {
    const t = setInterval(() => setNow(new Date()), 1000);
    return () => clearInterval(t);
  }, []);

  useEffect(() => {
    if (!powerOpen) return;
    const updatePosition = () => {
      const rect = powerButton.current?.getBoundingClientRect();
      if (rect) setPowerMenuPosition({ left: rect.left - 10, top: Math.max(8, rect.top) });
    };
    updatePosition();
    window.addEventListener("resize", updatePosition);
    return () => window.removeEventListener("resize", updatePosition);
  }, [powerOpen]);

  useEffect(() => {
    const closeMenu = (event: MouseEvent) => {
      if (!powerMenu.current?.contains(event.target as Node)) setPowerOpen(false);
    };
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") setPowerOpen(false);
    };
    document.addEventListener("mousedown", closeMenu);
    document.addEventListener("keydown", onKeyDown);
    return () => {
      document.removeEventListener("mousedown", closeMenu);
      document.removeEventListener("keydown", onKeyDown);
    };
  }, []);

  const day = now.toLocaleDateString("en-US", { weekday: "long" }).toUpperCase();
  const date = now
    .toLocaleDateString("en-US", { month: "long", day: "numeric", year: "numeric" })
    .toUpperCase();
  const time = now.toLocaleTimeString("en-US", { hour: "numeric", minute: "2-digit" });
  const [clock, ampm] = time.split(" ");

  return (
    <header className="flex items-center justify-between px-5 py-2 border-b border-cyan-faint">
      <div className="flex items-center gap-3">
        <ArcReactor size={44} />
        <div>
          <div className="text-cyan text-xl tracking-[0.35em] text-glow">J.A.R.V.I.S.</div>
          <div className="text-text-dim text-[10px] tracking-[0.3em]">2026 EDITION</div>
        </div>
      </div>
      <div className="text-cyan text-[11px] tracking-[0.35em] text-glow">
        JUST A RATHER VERY INTELLIGENT SYSTEM
      </div>
      <div className="flex items-center gap-4">
        <div className="text-right">
          <div className="text-text-dim text-[10px] tracking-[0.2em]">{day}</div>
          <div className="text-text-dim text-[10px] tracking-[0.15em]">{date}</div>
        </div>
        <div className="text-cyan text-3xl text-glow">
          {clock}
          <span className="text-xs ml-1">{ampm}</span>
        </div>
        <button
          className="text-cyan border border-cyan-faint rounded-full p-2 hover:bg-cyan-faint"
          title="Memory core"
          onClick={onOpenMemory}
        >
          <DbIcon size={18} />
        </button>
        <div className="relative" ref={powerMenu}>
          <button
            ref={powerButton}
            className="text-cyan border border-cyan-faint rounded-full p-2 hover:bg-cyan-faint"
            title="Power options"
            aria-label="Power options"
            aria-expanded={powerOpen}
            onClick={() => {
              const rect = powerButton.current?.getBoundingClientRect();
              if (rect) setPowerMenuPosition({ left: rect.left - 10, top: Math.max(8, rect.top) });
              setPowerOpen((open) => !open);
            }}
          >
            <PowerIcon size={18} />
          </button>
          {powerOpen && powerMenuPosition && (
            <div
              className="hud-panel fixed z-[60] w-60 p-1.5 shadow-lg"
              style={{
                position: "fixed",
                left: powerMenuPosition.left,
                top: powerMenuPosition.top,
                transform: "translateX(-100%)",
              }}
            >
              <button
                className="w-full px-3 py-2 text-left text-[11px] text-alert hover:bg-alert-dim"
                onClick={() => {
                  setPowerOpen(false);
                  onEmergencyStop?.();
                }}
              >
                <span className="block tracking-[0.15em]">EMERGENCY STOP</span>
                <span className="block mt-1 text-[9px] text-text-dim tracking-normal">
                  Halt active work and deny pending approvals
                </span>
              </button>
              <div className="my-1 border-t border-cyan-faint" />
              <button
                className="w-full px-3 py-2 text-left text-[11px] text-cyan hover:bg-cyan-faint"
                onClick={() => {
                  setPowerOpen(false);
                  onRestart?.();
                }}
              >
                <span className="block tracking-[0.15em]">RESTART J.A.R.V.I.S.</span>
                <span className="block mt-1 text-[9px] text-text-dim tracking-normal">
                  Restart the local service and desktop application
                </span>
              </button>
              <div className="my-1 border-t border-cyan-faint" />
              <button
                className="w-full px-3 py-2 text-left text-[11px] text-cyan hover:bg-cyan-faint"
                onClick={() => {
                  setPowerOpen(false);
                  onShutDown?.();
                }}
              >
                <span className="block tracking-[0.15em]">SHUT DOWN J.A.R.V.I.S.</span>
                <span className="block mt-1 text-[9px] text-text-dim tracking-normal">
                  Stop the service and close the application
                </span>
              </button>
            </div>
          )}
        </div>
      </div>
    </header>
  );
}
