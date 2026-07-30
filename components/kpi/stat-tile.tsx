"use client";

import * as React from "react";
import { ArrowDownRight, ArrowUpRight, Info, Minus } from "lucide-react";
import { Card } from "@/components/ui/card";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { signedPct } from "@/lib/format";
import { cn } from "@/lib/utils";
import { Sparkline, type SparkTone } from "./sparkline";

/* ────────────────────────────────────────────────────────────────
   TONE vs INVERT — the thing that is easy to get wrong.

   `tone` states which way the number MOVED (the shape of the data).
   `invert` states that LOWER IS BETTER for this metric.
   `judged` states whether the metric deserves a verdict at all.

   From those three we derive one `sentiment` (good | bad | neutral), and the
   two channels are driven separately:
     · the ARROW follows the sign of `delta`   — what happened
     · the COLOUR follows `sentiment`          — whether that is good news

   So 段取り比率 falling reads "↘ −24.9%" in GREEN, while 平均効率 falling reads
   "↘ −12.8%" in RED, and 総処理件数 — a volume, i.e. demand rather than
   performance — reads "↘ −23.0%" in plain ink, because nobody on the floor
   earned or lost that.
   ──────────────────────────────────────────────────────────────── */

type Sentiment = "good" | "bad" | "neutral";

/** Chip ink. Neutral stays in the ink ramp so only true verdicts carry colour. */
const SENTIMENT_INK: Record<Sentiment, string> = {
  good: "var(--good)",
  bad: "var(--critical)",
  neutral: "var(--ink-2)",
};

const SENTIMENT_SPARK: Record<Sentiment, SparkTone> = {
  good: "up",
  bad: "down",
  neutral: "neutral",
};

export type StatTileProps = {
  /** Japanese micro-label, e.g. 総処理件数 */
  label: string;
  /** Already formatted by @/lib/format — the tile never formats numbers itself. */
  value: string;
  /** Small trailing unit: 件 / % / h */
  unit?: string;
  /** Percent change vs the compared period. `null` when there is nothing to compare. */
  delta: number | null;
  /** Names the comparison, e.g. 前週比 */
  deltaLabel: string;
  spark: number[];
  /** Direction the metric moved. NOT a verdict — see the note above. */
  tone: "up" | "down" | "neutral";
  /** true when a FALLING number is the good outcome (段取り比率). */
  invert?: boolean;
  /** false for volumes that carry no good/bad verdict (件数, 稼働時間). */
  judged?: boolean;
  /** Tooltip body on an Info affordance in the label row. */
  hint?: string;
  /** One short line of provenance under the delta. */
  footnote?: string;
  className?: string;
};

/** Wraps every numeric run in `.tnum` so figures inside prose still align. */
function tnum(text: string): React.ReactNode[] {
  return text.split(/(\d[\d,.]*)/g).map((part, i) =>
    i % 2 === 1 ? (
      <span key={i} className="tnum">
        {part}
      </span>
    ) : (
      <React.Fragment key={i}>{part}</React.Fragment>
    ),
  );
}

export function StatTile({
  label,
  value,
  unit,
  delta,
  deltaLabel,
  spark,
  tone,
  invert = false,
  judged = true,
  hint,
  footnote,
  className,
}: StatTileProps) {
  const sentiment: Sentiment =
    !judged || tone === "neutral"
      ? "neutral"
      : (tone === "up") !== invert
        ? "good"
        : "bad";

  const ink = SENTIMENT_INK[sentiment];

  // Direction of travel comes from the datum, never from `tone`, so the arrow
  // can never disagree with the sign printed beside it.
  const dir = delta === null ? 0 : Math.sign(delta);
  const DeltaIcon = dir > 0 ? ArrowUpRight : dir < 0 ? ArrowDownRight : Minus;

  return (
    <Card
      className={cn(
        "group relative overflow-hidden p-4",
        "transition-[border-color,box-shadow] duration-150 ease-out",
        "hover:border-[var(--line-strong)] hover:shadow-[var(--shadow-lift)]",
        className,
      )}
    >
      {/* Gold hairline drawing itself across the top edge on hover. Transform
          lives on this child, never on the card, so a parent Framer Motion
          stagger keeps sole ownership of the card's own transform. */}
      <div
        aria-hidden
        className="pointer-events-none absolute inset-x-0 top-0 h-px origin-left scale-x-0 bg-[var(--accent)] transition-transform duration-[260ms] ease-[var(--ease-out-expo)] group-hover:scale-x-100"
      />

      <div className="flex items-start justify-between gap-2">
        <span className="text-[10.5px] leading-none font-medium tracking-[0.09em] text-[var(--ink-4)] uppercase">
          {label}
        </span>

        {hint ? (
          <TooltipProvider delayDuration={140}>
            <Tooltip>
              <TooltipTrigger asChild>
                <button
                  type="button"
                  aria-label={`${label}の補足`}
                  className="-mt-1 -mr-1 rounded-[4px] p-1 text-[var(--ink-4)] transition-colors duration-150 hover:text-[var(--ink-2)]"
                >
                  <Info size={12} strokeWidth={2} aria-hidden />
                </button>
              </TooltipTrigger>
              <TooltipContent side="top" align="end" className="max-w-[248px] leading-[1.6]">
                {tnum(hint)}
              </TooltipContent>
            </Tooltip>
          </TooltipProvider>
        ) : null}
      </div>

      <div className="mt-3 flex items-baseline gap-1">
        <span
          className="tnum text-[32px] leading-none font-medium text-[var(--ink)]"
          // Inline: globals.css sets .tnum letter-spacing outside Tailwind's
          // layers, so a tracking-* utility would lose to it.
          style={{ letterSpacing: "-0.02em" }}
        >
          {value}
        </span>
        {unit ? (
          <span className="text-[13px] leading-none text-[var(--ink-3)]">{unit}</span>
        ) : null}
      </div>

      <div className="mt-3.5 flex items-end justify-between gap-3">
        <div className="min-w-0">
          {/* Never colour alone: the arrow glyph and the printed sign both
              carry the direction, and 前週比 names the comparison. */}
          <span
            className="inline-flex items-center gap-1 rounded-[6px] px-1.5 py-[3px] text-[11.5px] leading-none"
            style={{
              color: ink,
              backgroundColor: `color-mix(in oklab, ${ink} 8%, transparent)`,
            }}
          >
            <DeltaIcon size={12} strokeWidth={2.25} aria-hidden />
            <span className="tnum font-medium">
              {delta === null ? "—" : signedPct(delta)}
            </span>
            <span className="text-[var(--ink-4)]">{deltaLabel}</span>
          </span>

          {footnote ? (
            <p className="mt-1.5 truncate text-[11px] leading-none text-[var(--ink-4)]">
              {tnum(footnote)}
            </p>
          ) : null}
        </div>

        <Sparkline data={spark} tone={SENTIMENT_SPARK[sentiment]} />
      </div>
    </Card>
  );
}
