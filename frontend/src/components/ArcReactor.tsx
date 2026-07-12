// Concentric glowing rings + triangular core + radial ticks, per mockups.

export default function ArcReactor({ size = 64, spin = true }: { size?: number; spin?: boolean }) {
  const ticks = Array.from({ length: 36 }, (_, i) => i * 10);
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 100 100"
      className="glow-cyan"
      aria-hidden="true"
    >
      <circle cx="50" cy="50" r="48" fill="none" stroke="var(--color-cyan-faint)" strokeWidth="1" />
      <g className={spin ? "reactor-spin" : undefined}>
        {ticks.map((deg) => (
          <line
            key={deg}
            x1="50"
            y1="6"
            x2="50"
            y2={deg % 30 === 0 ? "12" : "9"}
            stroke="var(--color-cyan-dim)"
            strokeWidth="1"
            transform={`rotate(${deg} 50 50)`}
          />
        ))}
      </g>
      <circle cx="50" cy="50" r="38" fill="none" stroke="var(--color-cyan)" strokeWidth="1.5" opacity="0.8" />
      <circle cx="50" cy="50" r="30" fill="none" stroke="var(--color-cyan-dim)" strokeWidth="4" />
      <circle cx="50" cy="50" r="22" fill="none" stroke="var(--color-cyan)" strokeWidth="1" opacity="0.6" />
      <circle cx="50" cy="50" r="15" fill="#0c2333" stroke="var(--color-cyan)" strokeWidth="1.5" />
      {/* triangular core */}
      <polygon
        points="50,38 61,57 39,57"
        fill="none"
        stroke="var(--color-cyan)"
        strokeWidth="2"
        className="pulse-soft"
      />
      <circle cx="50" cy="50" r="4" fill="var(--color-cyan)" className="pulse-soft" />
    </svg>
  );
}
