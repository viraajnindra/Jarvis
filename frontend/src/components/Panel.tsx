import { ReactNode } from "react";

export default function Panel({
  title,
  children,
  className = "",
  alert = false,
}: {
  title?: string;
  children: ReactNode;
  className?: string;
  alert?: boolean;
}) {
  return (
    <div
      className={`hud-panel p-3 ${className}`}
      style={
        alert
          ? { borderColor: "var(--color-alert-dim)", background: "#160a0e" }
          : undefined
      }
    >
      {title && (
        <div
          className="panel-title mb-2"
          style={alert ? { color: "var(--color-alert)" } : undefined}
        >
          {title}
        </div>
      )}
      {children}
    </div>
  );
}
