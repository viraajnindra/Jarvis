import { BrainIcon, DbIcon, CloudIcon, WaveIcon } from "./icons";

function Segment({
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
    <div className="flex items-center gap-2 px-5">
      <span className="text-cyan">{icon}</span>
      <div>
        <div className="text-text-dim text-[9px] tracking-[0.2em]">{label}</div>
        <div
          className="text-[11px] tracking-wider"
          style={{ color: ok ? "var(--color-ok)" : "var(--color-cyan)" }}
        >
          {value}
        </div>
      </div>
    </div>
  );
}

export default function StatusBar({
  localModel,
  memoryOnline,
  cloudModel,
  voiceMode,
}: {
  localModel: string;
  memoryOnline: boolean;
  cloudModel: string;
  voiceMode: boolean;
}) {
  return (
    <footer className="flex items-center justify-center border-t border-cyan-faint py-2 divide-x divide-cyan-faint">
      <Segment icon={<BrainIcon size={16} />} label="LOCAL MODEL" value={localModel.toUpperCase()} />
      <Segment icon={<DbIcon size={16} />} label="MEMORY CORE" value={memoryOnline ? "ONLINE" : "OFFLINE"} ok={memoryOnline} />
      <Segment icon={<CloudIcon size={16} />} label="CLOUD LINK" value={cloudModel.toUpperCase()} />
      {voiceMode ? (
        <Segment icon={<WaveIcon size={16} />} label="CHAT BOX" value="ACTIVE" />
      ) : (
        <Segment icon={<WaveIcon size={16} />} label="VOICE SYSTEM" value="STANDBY" />
      )}
    </footer>
  );
}
