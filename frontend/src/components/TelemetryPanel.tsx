import Panel from "./Panel";
import { Telemetry, jarvis } from "../ws";
import { CpuIcon, RamIcon, GpuIcon, BrainIcon, GlobeIcon, CheckboxIcon, ExternalIcon } from "./icons";

const DAY_GOAL_H = 6; // ring fills at this many hours studied today

function Ring({ label, fraction }: { label: string; fraction: number }) {
  const r = 34;
  const c = 2 * Math.PI * r;
  const f = Math.max(0, Math.min(fraction, 1));
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
        strokeDasharray={`${c * f} ${c}`}
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

export default function TelemetryPanel({
  t,
  canvasUrl,
}: {
  t: Telemetry | null;
  canvasUrl?: string;
}) {
  const s = t?.study ?? null;
  return (
    <div className="flex flex-col gap-3 h-full">
      <div className="panel-title">SYSTEM TELEMETRY</div>

      <Panel title="STUDY TRACKER">
        <div className="flex items-center gap-3">
          <Ring
            label={s ? s.today_h.toFixed(1) : "--"}
            fraction={s ? s.today_h / DAY_GOAL_H : 0}
          />
          <div className="text-[11px] space-y-2">
            <div>
              <div className="text-text-dim tracking-wider">TODAY</div>
              <div className="text-cyan">{s ? `${s.today_h.toFixed(1)} hrs` : "-- hrs"}</div>
            </div>
            <div>
              <div className="text-text-dim tracking-wider">WEEK</div>
              <div className="text-cyan">{s ? `${s.week_h.toFixed(1)} hrs` : "-- hrs"}</div>
            </div>
          </div>
        </div>
        <div className="flex justify-between items-end mt-2 px-1 h-8">
          {(s?.days ?? Array(7).fill(0)).map((h, i) => (
            <div key={i} className="flex flex-col items-center gap-0.5 w-4">
              <div
                className="w-1.5"
                style={{
                  height: `${Math.min(h / DAY_GOAL_H, 1) * 20}px`,
                  background: h > 0 ? "var(--color-cyan)" : "var(--color-cyan-faint)",
                  minHeight: "2px",
                }}
              />
              <span className="text-[9px] text-text-dim tracking-widest">
                {["M", "T", "W", "T", "F", "S", "S"][i]}
              </span>
            </div>
          ))}
        </div>
        <button
          onClick={() => (s?.active ? jarvis.studyStop() : jarvis.studyStart())}
          className="mt-2 w-full border border-cyan-faint text-[10px] tracking-[0.2em] py-1.5 hover:bg-cyan-faint"
          style={{ color: s?.active ? "var(--color-alert)" : "var(--color-cyan)" }}
        >
          {s?.active ? "■ STOP SESSION" : "▶ START SESSION"}
        </button>
      </Panel>

      <Panel title="LOVABLE APPS">
        <div className="flex gap-4 text-[11px]">
          <div>
            <div className="text-text-dim tracking-wider">ACTIVE APPS</div>
            <div className="text-cyan text-2xl">{t?.lovable?.apps ?? "--"}</div>
          </div>
          <div>
            <div className="text-text-dim tracking-wider">TOTAL VIEWS</div>
            <div className="text-cyan text-2xl">{t?.lovable?.views ?? "--"}</div>
            <div className="text-text-dim text-[9px]">
              {t?.lovable
                ? `updated ${new Date(t.lovable.updated * 1000).toLocaleTimeString("en-US", { hour: "numeric", minute: "2-digit" })}`
                : "not configured — set JARVIS_LOVABLE_URL"}
            </div>
          </div>
        </div>
      </Panel>

      <Panel title="CANVAS OVERVIEW">
        <div className="text-[11px] space-y-1">
          {[
            { label: "Assignments Due Soon", v: t?.canvas?.due_soon },
            { label: "Ungraded Submissions", v: t?.canvas?.ungraded },
            { label: "New Announcements", v: t?.canvas?.announcements },
          ].map(({ label, v }) => (
            <div key={label} className="flex items-center gap-2">
              <CheckboxIcon size={14} className="text-cyan" />
              <span className="text-cyan w-4">{v ?? "--"}</span>
              <span>{label}</span>
            </div>
          ))}
        </div>
        {!t?.canvas && (
          <div className="text-text-dim text-[9px] mt-1">Not connected — add Canvas token</div>
        )}
        <button
          onClick={() => canvasUrl && window.open(canvasUrl, "_blank")}
          className="mt-2 w-full border border-cyan-faint text-cyan text-[10px] tracking-[0.2em] py-1.5 hover:bg-cyan-faint flex items-center justify-center gap-1"
        >
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
