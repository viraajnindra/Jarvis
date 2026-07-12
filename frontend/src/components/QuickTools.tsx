import Panel from "./Panel";
import { SearchIcon, VideoIcon, SyncIcon, GlobeIcon, AppIcon, SendIcon } from "./icons";

const TOOLS = [
  { label: "Deep Research", icon: SearchIcon, prompt: "Run deep research on: " },
  { label: "Summarize Video", icon: VideoIcon, prompt: "Summarize this video: " },
  { label: "Canvas Sync", icon: SyncIcon, prompt: "Sync my Canvas data" },
  { label: "Open Website", icon: GlobeIcon, prompt: "Open website: " },
  { label: "Launch App", icon: AppIcon, prompt: "Launch app: " },
  { label: "Send Message", icon: SendIcon, prompt: "Send a message to " },
];

export default function QuickTools({ onPick }: { onPick: (prompt: string) => void }) {
  return (
    <Panel title="QUICK TOOLS">
      <div className="grid grid-cols-3 gap-2">
        {TOOLS.map(({ label, icon: Icon, prompt }) => (
          <button
            key={label}
            onClick={() => onPick(prompt)}
            className="border border-cyan-faint hover:bg-cyan-faint text-center py-3 px-1 flex flex-col items-center gap-2"
          >
            <Icon size={18} className="text-cyan" />
            <span className="text-[9px] text-text-dim leading-tight">{label}</span>
          </button>
        ))}
      </div>
    </Panel>
  );
}
