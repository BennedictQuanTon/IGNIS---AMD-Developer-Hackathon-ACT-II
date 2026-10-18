import type { SVGProps } from "react";

// Inline line icons (16px grid, 1.5 stroke). No icon font or external set.
const base: SVGProps<SVGSVGElement> = {
  width: 16,
  height: 16,
  viewBox: "0 0 16 16",
  fill: "none",
  stroke: "currentColor",
  strokeWidth: 1.5,
  strokeLinecap: "round",
  strokeLinejoin: "round",
  "aria-hidden": true,
};

const paths: Record<string, string> = {
  upload: "M8 10.5V2.5M5 5.5l3-3 3 3M2.5 10v2.5a1 1 0 0 0 1 1h9a1 1 0 0 0 1-1V10",
  spans: "M2 4h12M2 8h5M9.5 8H14M2 12h8M4 6.5v-.01M11.5 10.5v-.01",
  review: "M6 7.5a2.5 2.5 0 1 0 0-5 2.5 2.5 0 0 0 0 5ZM1.5 13.5c.6-2.3 2.4-3.5 4.5-3.5 1 0 1.9.3 2.6.8M10 12l1.5 1.5L14.5 10",
  calc: "M3.5 1.5h9a1 1 0 0 1 1 1v11a1 1 0 0 1-1 1h-9a1 1 0 0 1-1-1v-11a1 1 0 0 1 1-1ZM5 4.5h6M5 8h.01M8 8h.01M11 8h.01M5 11h.01M8 11h.01M11 11h.01",
  filter: "M2 3h12l-4.5 5.5V13l-3 1.5v-6L2 3Z",
  report: "M9.5 1.5H4a1 1 0 0 0-1 1v11a1 1 0 0 0 1 1h8a1 1 0 0 0 1-1V5L9.5 1.5ZM9.5 1.5V5H13M5.5 9l1.5 1.5 3-3",
  arrow: "M3 8h10M9 4l4 4-4 4",
  external: "M6 3H3.5a1 1 0 0 0-1 1v8.5a1 1 0 0 0 1 1H12a1 1 0 0 0 1-1V10M9 2.5h4.5V7M13.5 2.5 7 9",
  check: "M3 8.5l3 3 7-7",
  dash: "M4 8h8",
  close: "M4 4l8 8M12 4l-8 8",
  menu: "M2.5 4.5h11M2.5 8h11M2.5 11.5h11",
  panel: "M2.5 3h11v10h-11zM10 3v10",
  copy: "M5.5 5.5V3a1 1 0 0 1 1-1H13a1 1 0 0 1 1 1v6.5a1 1 0 0 1-1 1h-2.5M3 5.5h6.5a1 1 0 0 1 1 1V13a1 1 0 0 1-1 1H3a1 1 0 0 1-1-1V6.5a1 1 0 0 1 1-1Z",
  alert: "M8 5.5v3M8 11h.01M7.1 2.4 1.7 12a1 1 0 0 0 .9 1.5h10.8a1 1 0 0 0 .9-1.5L8.9 2.4a1 1 0 0 0-1.8 0Z",
  replay: "M2.5 8a5.5 5.5 0 1 0 1.6-3.9M2.5 2.5v2.4h2.4M6.8 5.9l3.2 2.1-3.2 2.1V5.9Z",
  live: "M9 1.5 3.5 9h4L7 14.5 12.5 7h-4L9 1.5Z",
  flask: "M6 1.5h4M6.5 1.5v4L2.8 12.4a1.4 1.4 0 0 0 1.2 2.1h8a1.4 1.4 0 0 0 1.2-2.1L9.5 5.5v-4M4.5 10h7",
  doc: "M9.5 1.5H4a1 1 0 0 0-1 1v11a1 1 0 0 0 1 1h8a1 1 0 0 0 1-1V5L9.5 1.5ZM9.5 1.5V5H13M5.5 8.5h5M5.5 11h3",
  lock: "M5 7V5a3 3 0 0 1 6 0v2M3.5 7h9v6.5h-9V7Z",
  play: "M5 3v10l8-5-8-5Z",
  pause: "M5.5 3.5v9M10.5 3.5v9",
  step: "M3.5 3v10l7-5-7-5ZM12.5 3v10",
};

export type IconName = keyof typeof paths | "github";

export function Icon({ name, className, size = 16 }: { name: IconName; className?: string; size?: number }) {
  if (name === "github") {
    return (
      <svg width={size} height={size} viewBox="0 0 16 16" fill="currentColor" aria-hidden className={className}>
        <path d="M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38 0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82.64-.18 1.32-.27 2-.27.68 0 1.36.09 2 .27 1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.013 8.013 0 0 0 16 8c0-4.42-3.58-8-8-8Z" />
      </svg>
    );
  }
  return (
    <svg {...base} width={size} height={size} className={className}>
      <path d={paths[name]} />
    </svg>
  );
}
