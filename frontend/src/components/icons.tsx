// Minimal inline SVG icon set, 1.5px stroke, currentColor.

type P = { size?: number; className?: string };

const base = (size = 16) => ({
  width: size,
  height: size,
  viewBox: "0 0 24 24",
  fill: "none",
  stroke: "currentColor",
  strokeWidth: 1.5,
  strokeLinecap: "round" as const,
  strokeLinejoin: "round" as const,
});

export const SearchIcon = ({ size, className }: P) => (
  <svg {...base(size)} className={className}>
    <circle cx="11" cy="11" r="7" />
    <path d="m21 21-4.3-4.3" />
  </svg>
);

export const VideoIcon = ({ size, className }: P) => (
  <svg {...base(size)} className={className}>
    <rect x="2" y="5" width="20" height="14" rx="2" />
    <path d="m10 9 5 3-5 3z" />
  </svg>
);

export const SyncIcon = ({ size, className }: P) => (
  <svg {...base(size)} className={className}>
    <path d="M21 12a9 9 0 1 1-2.6-6.4" />
    <path d="M21 3v6h-6" />
  </svg>
);

export const GlobeIcon = ({ size, className }: P) => (
  <svg {...base(size)} className={className}>
    <circle cx="12" cy="12" r="9" />
    <path d="M3 12h18M12 3a15 15 0 0 1 0 18M12 3a15 15 0 0 0 0 18" />
  </svg>
);

export const AppIcon = ({ size, className }: P) => (
  <svg {...base(size)} className={className}>
    <rect x="3" y="3" width="7" height="7" rx="1" />
    <rect x="14" y="3" width="7" height="7" rx="1" />
    <rect x="3" y="14" width="7" height="7" rx="1" />
    <rect x="14" y="14" width="7" height="7" rx="1" />
  </svg>
);

export const SendIcon = ({ size, className }: P) => (
  <svg {...base(size)} className={className}>
    <path d="m22 2-7 20-4-9-9-4z" />
    <path d="M22 2 11 13" />
  </svg>
);

export const MicIcon = ({ size, className }: P) => (
  <svg {...base(size)} className={className}>
    <rect x="9" y="2" width="6" height="12" rx="3" />
    <path d="M5 10v1a7 7 0 0 0 14 0v-1M12 18v4" />
  </svg>
);

export const CpuIcon = ({ size, className }: P) => (
  <svg {...base(size)} className={className}>
    <rect x="5" y="5" width="14" height="14" rx="1" />
    <rect x="9" y="9" width="6" height="6" />
    <path d="M9 2v3M15 2v3M9 19v3M15 19v3M2 9h3M2 15h3M19 9h3M19 15h3" />
  </svg>
);

export const RamIcon = ({ size, className }: P) => (
  <svg {...base(size)} className={className}>
    <rect x="2" y="7" width="20" height="10" rx="1" />
    <path d="M6 11v2M10 11v2M14 11v2M18 11v2M4 17v2M20 17v2" />
  </svg>
);

export const GpuIcon = ({ size, className }: P) => (
  <svg {...base(size)} className={className}>
    <rect x="2" y="6" width="18" height="10" rx="1" />
    <circle cx="9" cy="11" r="2.5" />
    <circle cx="15" cy="11" r="2.5" />
    <path d="M4 16v3M8 16v3" />
  </svg>
);

export const BrainIcon = ({ size, className }: P) => (
  <svg {...base(size)} className={className}>
    <path d="M9.5 2A4.5 4.5 0 0 0 5 6.5c0 .6.1 1.1.3 1.6A4.5 4.5 0 0 0 4 16a4.5 4.5 0 0 0 5.5 4.4A4.5 4.5 0 0 0 12 22V2h-2.5z" />
    <path d="M14.5 2A4.5 4.5 0 0 1 19 6.5c0 .6-.1 1.1-.3 1.6A4.5 4.5 0 0 1 20 16a4.5 4.5 0 0 1-5.5 4.4A4.5 4.5 0 0 1 12 22V2h2.5z" />
  </svg>
);

export const DbIcon = ({ size, className }: P) => (
  <svg {...base(size)} className={className}>
    <ellipse cx="12" cy="5" rx="8" ry="3" />
    <path d="M4 5v14c0 1.7 3.6 3 8 3s8-1.3 8-3V5M4 12c0 1.7 3.6 3 8 3s8-1.3 8-3" />
  </svg>
);

export const CloudIcon = ({ size, className }: P) => (
  <svg {...base(size)} className={className}>
    <path d="M17.5 19a4.5 4.5 0 0 0 .4-9A7 7 0 0 0 4.3 12.7 4 4 0 0 0 6 19.9z" />
  </svg>
);

export const WaveIcon = ({ size, className }: P) => (
  <svg {...base(size)} className={className}>
    <path d="M2 12h2M6 8v8M10 4v16M14 7v10M18 9v6M22 12h-1" />
  </svg>
);

export const ChatIcon = ({ size, className }: P) => (
  <svg {...base(size)} className={className}>
    <path d="M21 12a8 8 0 0 1-8 8H4l2-3a8 8 0 1 1 15-5z" />
  </svg>
);

export const PowerIcon = ({ size, className }: P) => (
  <svg {...base(size)} className={className}>
    <path d="M12 2v9" />
    <path d="M18.4 6.6a9 9 0 1 1-12.8 0" />
  </svg>
);

export const WarnIcon = ({ size, className }: P) => (
  <svg {...base(size)} className={className}>
    <path d="m12 3 10 18H2z" />
    <path d="M12 10v5M12 18.5v.5" />
  </svg>
);

export const CheckboxIcon = ({ size, className }: P) => (
  <svg {...base(size)} className={className}>
    <rect x="4" y="4" width="16" height="16" rx="2" />
    <path d="m8.5 12 2.5 2.5 5-5" />
  </svg>
);

export const ExternalIcon = ({ size, className }: P) => (
  <svg {...base(size)} className={className}>
    <path d="M14 4h6v6M20 4l-9 9" />
    <path d="M20 14v5a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1V5a1 1 0 0 1 1-1h5" />
  </svg>
);

export const UserIcon = ({ size, className }: P) => (
  <svg {...base(size)} className={className}>
    <circle cx="12" cy="8" r="4" />
    <path d="M4 21c0-4 3.6-6 8-6s8 2 8 6" />
  </svg>
);
