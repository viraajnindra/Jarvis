import Panel from "./Panel";
import { Telemetry } from "../ws";
import { CpuIcon, RamIcon, GpuIcon, BrainIcon, GlobeIcon, CheckboxIcon, ExternalIcon } from "./icons";

function Ring({ label }: { label: string }) {
  // Study data arrives in Phase 8; render the ring with a placeholder center.
  const r = 34;
  const c = 2 * Math.PI * r;
  return (
    <svg width="88" height="88" viewBox="0 0 88 88" className="glow-cyan">
      <circle cx="44" cy="44" r={r} fill="none" stroke="var(--color-cyan-faint)" strokeWidth="6" />
      <circle
        cx="44"
        cy="44"
        r={r}
        fill="none"
        stroke="var(--color-cyan)"
        strokeWidth="6"
        strokeDasharray={`${c * 0.0} ${c}`}
        strokeLinecap="round"
        transform="rotate(-90 44 44)"
      />
      <text x="44" y="41" textAnchor="middle" fill="var(--color-cyan)" fontSize="16" fontFamily="var(--font-mono)">
        {label}
      </text>
      <text x="44" y="56" textAnchor="middle" fill="var(--color-text-dim)" fontSize="8" letterSpacing="2">
        HOURS
      </text>
    </svg>
  );
}

function StatRow({
  icon,
  label,
  value,
  ok,
}: {
  icon: React.ReactNode;
  label: string;
  value: string;
  ok?: boolean;
}) {
  return (
    <div className="flex items-center gap-2 py-1 text-[11px]">
      <span className="text-cyan">{icon}</span>
      <span className="text-text-dim tracking-wider flex-1">{label}</span>
      <span style={{ color: ok ? "var(--color-ok)" : "var(--color-text)" }}>{value}</span>
    </div>
  );
}

export default function TelemetryPanel({ t }: { t: Telemetry | null }) {
  return (
    <div className="flex flex-col gap-3 h-full">
      <div className="panel-title">SYSTEM TELEMETRY</div>

      <Panel title="STUDY TRACKER">
        <div className="flex items-center gap-3">
          <Ring label="--" />
          <div className="text-[11px] space-y-2">
            <div>
              <div className="text-text-dim tracking-wider">TODAY</div>
              <div className="text-cyan">-- hrs</div>
            </div>
            <div>
              <div className="text-text-dim tracking-wider">WEEK</div>
              <div className="text-cyan">-- hrs</div>
            </div>
          </div>
        </div>
        <div className="flex justify-between text-[9px] text-text-dim mt-2 px-1 tracking-widest">
          {["M", "T", "W", "T", "F", "S", "S"].map((d, i) => (
            <span key={i}>{d}</span>
          ))}
        </div>
      </Panel>

      <Panel title="LOVABLE APPS">
        <div className="flex gap-4 text-[11px]">
          <div>
            <div className="text-text-dim tracking-wider">ACTIVE APPS</div>
            <div className="text-cyan text-2xl">--</div>
          </div>
          <div>
            <div className="text-text-dim tracking-wider">TOTAL VIEWS</div>
            <div className="text-cyan text-2xl">--</div>
            <div className="text-text-dim text-[9px]">tracking starts Phase 8</div>
          </div>
        </div>
      </Panel>

      <Panel title="CANVAS OVERVIEW">
        <div className="text-[11px] space-y-1">
          {["Assignments Due Soon", "Ungraded Submissions", "New Announcements"].map((label) => (
            <div key={label} className="flex items-center gap-2">
              <CheckboxIcon size={14} className="text-cyan" />
              <span className="text-text-dim">--</span>
              <span>{label}</span>
            </div>
          ))}
        </div>
        <button className="mt-2 w-full border border-cyan-faint text-cyan text-[10px] tracking-[0.2em] py-1.5 hover:bg-cyan-faint flex items-center justify-center gap-1">
          OPEN CANVAS <ExternalIcon size={11} />
        </button>
      </Panel>

      <Panel title="SYSTEM STATUS">
        <StatRow icon={<CpuIcon size={14} />} label="CPU USAGE" value={t ? `${Math.round(t.cpu_pct)}%` : "--"} />
        <StatRow icon={<RamIcon size={14} />} label="RAM USAGE" value={t ? `${Math.round(t.ram_pct)}%` : "--"} />
        <StatRow
          icon={<GpuIcon size={14} />}
          label={t?.gpu ? `GPU (${t.gpu.name.replace("NVIDIA GeForce ", "")})` : "GPU"}
          value={t?.gpu ? `${t.gpu.util_pct}%` : "--"}
        />
        <StatRow
          icon={<BrainIcon size={14} />}
          label="LOCAL MODEL"
          value={t ? (t.model_online ? "ONLINE" : "OFFLINE") : "--"}
          ok={t?.model_online}
        />
        <StatRow
          icon={<GlobeIcon size={14} />}
          label="INTERNET"
          value={t ? (t.internet ? "CONNECTED" : "DOWN") : "--"}
          ok={t?.internet}
        />
      </Panel>

      <div className="hud-panel mt-auto px-3 py-2 flex items-center gap-2 text-[10px] tracking-[0.2em]">
        <span
          className="w-2 h-2 rounded-full pulse-soft"
          style={{
            background:
              t && t.model_online && t.internet ? "var(--color-ok)" : "var(--color-alert)",
          }}
        />
        <span style={{ color: t && t.model_online && t.internet ? "var(--color-ok)" : "var(--color-alert)" }}>
          {t ? (t.model_online && t.internet ? "ALL SYSTEMS OPERATIONAL" : "DEGRADED") : "CONNECTING..."}
        </span>
      </div>
    </div>
  );
}
