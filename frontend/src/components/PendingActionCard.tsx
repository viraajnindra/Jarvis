import Panel from "./Panel";
import { WarnIcon } from "./icons";

export type PendingAction = { id: string; action: string; target: string; detail?: string };

export default function PendingActionCard({
  action,
  onRespond,
}: {
  action: PendingAction;
  onRespond: (id: string, approved: boolean) => void;
}) {
  return (
    <Panel title="PENDING ACTION" alert>
      <div className="flex gap-2">
        <div className="text-[11px] flex-1">
          J.A.R.V.I.S. wants to perform an automation action on your system.
        </div>
        <WarnIcon size={34} className="pulse-soft" />
      </div>
      <div className="mt-2 text-[11px] space-y-1">
        <div>
          <span className="text-text-dim tracking-wider text-[9px]">ACTION:</span>
          <div>{action.action}</div>
        </div>
        <div>
          <span className="text-text-dim tracking-wider text-[9px]">TARGET:</span>
          <div className="break-all">{action.target}</div>
        </div>
        {action.detail && (
          <div>
            <span className="text-text-dim tracking-wider text-[9px]">DETAIL:</span>
            <div className="break-all whitespace-pre-wrap">{action.detail}</div>
          </div>
        )}
      </div>
      <button
        onClick={() => onRespond(action.id, true)}
        className="mt-3 w-full py-2 text-[11px] tracking-[0.2em] border"
        style={{
          background: "var(--color-alert-dim)",
          borderColor: "var(--color-alert)",
          color: "#ffb3ba",
        }}
      >
        CONFIRM OS ACTION
      </button>
      <button
        onClick={() => onRespond(action.id, false)}
        className="mt-2 w-full py-1.5 text-[11px] tracking-[0.2em] border border-cyan-faint text-text-dim hover:bg-cyan-faint"
      >
        CANCEL
      </button>
    </Panel>
  );
}
