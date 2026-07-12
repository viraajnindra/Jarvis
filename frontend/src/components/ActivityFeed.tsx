import Panel from "./Panel";
import { SyncIcon } from "./icons";

export type ActivityItem = { text: string; time: string };

export default function ActivityFeed({ items }: { items: ActivityItem[] }) {
  return (
    <Panel title="RECENT ACTIVITY" className="flex-1 flex flex-col">
      <div className="flex-1 space-y-1.5 overflow-hidden">
        {items.length === 0 && (
          <div className="text-text-dim text-[11px]">No activity yet this session.</div>
        )}
        {items.slice(0, 6).map((it, i) => (
          <div key={i} className="flex items-center gap-2 text-[11px]">
            <SyncIcon size={12} className="text-cyan shrink-0" />
            <span className="flex-1 truncate">{it.text}</span>
            <span className="text-text-dim text-[10px]">{it.time}</span>
          </div>
        ))}
      </div>
      <button className="mt-2 w-full border border-cyan-faint text-cyan text-[10px] tracking-[0.2em] py-1.5 hover:bg-cyan-faint">
        VIEW FULL LOG
      </button>
    </Panel>
  );
}
