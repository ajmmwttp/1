"use client";

import * as React from "react";
import { cn } from "@/lib/utils";

/**
 * `tone` is a VERDICT, not a direction — "up" means "this movement is good",
 * whichever way the line happens to point. StatTile derives it; see stat-tile.tsx.
 */
export type SparkTone = "up" | "down" | "neutral";

const TONE_INK: Record<SparkTone, string> = {
  up: "var(--good)",
  down: "var(--critical)",
  neutral: "var(--ink-3)",
};

const W = 72;
const H = 24;
const PAD_X = 2.5; // room for the r=2 terminal dot at the right edge
const PAD_Y = 3; // room for the 1.5px stroke top and bottom

/**
 * A 72×24 trend mark. Hand-built SVG rather than Recharts: it renders four
 * times per row, carries no axis, no tooltip and no interaction, so a chart
 * runtime would be pure weight. Decorative context for the figure above it —
 * `aria-hidden`, because the delta chip already states the movement in words.
 */
export function Sparkline({
  data,
  tone = "neutral",
  className,
}: {
  data: number[];
  tone?: SparkTone;
  className?: string;
}) {
  // Colons from useId are legal in an id attribute but trip up url(#…) lookups
  // in some engines, so strip them.
  const gradientId = `spark-${React.useId().replace(/:/g, "")}`;

  const geom = React.useMemo(() => {
    const n = data.length;
    if (n === 0) return null;

    const min = Math.min(...data);
    const max = Math.max(...data);
    const innerW = W - PAD_X * 2;
    const innerH = H - PAD_Y * 2;

    const pts = data.map((v, i) => {
      const x = n === 1 ? W / 2 : PAD_X + (i / (n - 1)) * innerW;
      // A flat series sits on the mid-line instead of collapsing onto the floor.
      const t = max === min ? 0.5 : (v - min) / (max - min);
      return [x, H - PAD_Y - t * innerH] as const;
    });

    const line = pts
      .map(([x, y], i) => `${i === 0 ? "M" : "L"}${x.toFixed(2)} ${y.toFixed(2)}`)
      .join(" ");
    const first = pts[0];
    const last = pts[n - 1];
    const area = `${line} L${last[0].toFixed(2)} ${H} L${first[0].toFixed(2)} ${H} Z`;

    return { line, area, last };
  }, [data]);

  if (!geom) return null;

  return (
    <svg
      aria-hidden="true"
      focusable="false"
      role="presentation"
      width={W}
      height={H}
      viewBox={`0 0 ${W} ${H}`}
      preserveAspectRatio="none"
      className={cn("block h-6 w-[72px] shrink-0 overflow-visible", className)}
      style={{ color: TONE_INK[tone] }}
    >
      <defs>
        <linearGradient id={gradientId} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="currentColor" stopOpacity={0.14} />
          <stop offset="100%" stopColor="currentColor" stopOpacity={0} />
        </linearGradient>
      </defs>

      <path d={geom.area} fill={`url(#${gradientId})`} />
      <path
        d={geom.line}
        fill="none"
        stroke="currentColor"
        strokeWidth={1.5}
        strokeLinecap="round"
        strokeLinejoin="round"
        // Keeps the stroke a true 1.5px when the box is stretched by the
        // preserveAspectRatio="none" scaling.
        vectorEffect="non-scaling-stroke"
      />
      <circle cx={geom.last[0]} cy={geom.last[1]} r={2} fill="currentColor" />
    </svg>
  );
}
