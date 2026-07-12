import { useEffect, useState } from "react";
import ArcReactor from "./ArcReactor";
import { PowerIcon } from "./icons";

export default function Header() {
  const [now, setNow] = useState(new Date());
  useEffect(() => {
    const t = setInterval(() => setNow(new Date()), 1000);
    return () => clearInterval(t);
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
          title="Power"
        >
          <PowerIcon size={18} />
        </button>
      </div>
    </header>
  );
}
