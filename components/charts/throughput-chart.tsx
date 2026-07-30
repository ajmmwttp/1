"use client";

import * as React from "react";
import { motion, useReducedMotion } from "framer-motion";
import {
  Area,
  CartesianGrid,
  ComposedChart,
  ReferenceArea,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { Button } from "@/components/ui/button";
import { REVEAL_STEPS } from "@/components/motion/ladder";
import { series } from "@/lib/chart-theme";
import { dataWindow, days, recordGap, type DayPoint } from "@/lib/data/warehouse";
import { longDate, pct, shortDate } from "@/lib/format";
import { cn } from "@/lib/utils";

import { ChartFrame, ChartLegend } from "./chart-frame";
import { ChartTooltip, type ChartTooltipRow } from "./chart-tooltip";
import { usePlotWidth } from "./use-plot-width";

/* ──────────────────────────────────────────────────────────────
   ThroughputChart — 日次の効率推移.

   Both series are percentages against the same standard-time model,
   so they legally share one y-axis. The recording gap in pickEff
   (2026-04-24 →) is drawn as a hatched, labelled region: a missing
   measurement is information, not something to paper over.
   ────────────────────────────────────────────────────────────── */

const PICK_FILL = "throughput-pick-fill";
const PACK_FILL = "throughput-pack-fill";
const GAP_HATCH = "throughput-gap-hatch";

interface RangeOption {
  id: string;
  label: string;
  /** Trailing record count, null = 全期間. */
  take: number | null;
}

const RANGES: readonly RangeOption[] = [
  { id: "all", label: "全期間", take: null },
  { id: "d14", label: "直近14日", take: 14 },
  { id: "d7", label: "直近7日", take: 7 },
];

const LEGEND = [
  { color: series[1], label: "ピッキング効率" },
  { color: series[2], label: "梱包効率" },
];

/** Width the y-axis and the right margin take away from the plot box. */
const AXIS_GUTTER = 54;
/** "4/14" at 11px measures ~26px; 10px of air keeps the row from reading as one word. */
const DATE_TICK_SLOT = 36;

/**
 * Density at desktop widths — unchanged, this is the tuned resting state.
 */
function tickInterval(n: number): number {
  if (n > 10) return 2;
  if (n > 7) return 1;
  return 0;
}

/**
 * Thins the date axis until the labels fit, and never the other way: the
 * result is `max(desktop interval, what the box can hold)`, so a narrow
 * phone drops ticks while a wide card keeps the tuned spacing.
 *
 * Type size is left alone on purpose — 11px is already the floor the brief
 * allows, so density is the only lever.
 */
function fittedInterval(n: number, plotWidth: number): number {
  const roomy = tickInterval(n);
  if (plotWidth <= 0) return roomy; // not measured yet — assume the wide case
  const usable = Math.max(plotWidth - AXIS_GUTTER, 0);
  const maxTicks = Math.max(Math.floor(usable / DATE_TICK_SLOT), 2);
  if (n <= maxTicks) return roomy;
  return Math.max(roomy, Math.ceil(n / maxTicks) - 1);
}

/** Recharts' y-domain tuple, kept out of the JSX so the cast stays in one place. */
const Y_DOMAIN: [number, string] = [40, "dataMax + 10"];

function effValue(raw: unknown): ChartTooltipRow["value"] {
  return typeof raw === "number" ? pct(raw) : "記録なし";
}

function buildRows(datum: Record<string, unknown>): ChartTooltipRow[] {
  const pick = datum.pickEff;
  const pack = datum.packEff;
  return [
    {
      color: series[1],
      label: "ピッキング効率",
      value: effValue(pick),
      muted: typeof pick !== "number",
    },
    {
      color: series[2],
      label: "梱包効率",
      value: effValue(pack),
      muted: typeof pack !== "number",
    },
  ];
}

export function ThroughputChart() {
  const [rangeId, setRangeId] = React.useState<string>("all");
  const reduceMotion = useReducedMotion();
  const [plotRef, plotWidth] = usePlotWidth();

  const range = RANGES.find((r) => r.id === rangeId) ?? RANGES[0];

  const data: DayPoint[] = React.useMemo(
    () => (range.take === null ? days : days.slice(-range.take)),
    [range.take],
  );

  /* The hatch has to snap to categories that actually exist in the
     current window, otherwise Recharts drops the band silently. */
  const gap = React.useMemo(() => {
    const inGap = data.filter(
      (d) => d.date >= recordGap.start && d.date <= recordGap.end,
    );
    if (inGap.length < 2) return null;
    return { x1: inGap[0].date, x2: inGap[inGap.length - 1].date };
  }, [data]);

  /* Below this the band is too slim to hold a centred caption clear of the
     梱包 line, which keeps plotting straight through the gap. */
  const narrowBand = plotWidth > 0 && plotWidth < 460;

  return (
    <ChartFrame
      revealStep={REVEAL_STEPS.chartRow}
      title="日次の効率推移"
      description="標準時間 ÷ 実測時間。100 が標準どおり。"
      legend={<ChartLegend items={LEGEND} />}
      action={
        <div className="flex items-center gap-0.5 rounded-[8px] border border-[var(--line)] bg-[var(--sunken)] p-0.5">
          {RANGES.map((option) => {
            const selected = option.id === range.id;
            return (
              <Button
                key={option.id}
                type="button"
                variant="ghost"
                size="sm"
                aria-pressed={selected}
                onClick={() => setRangeId(option.id)}
                className={cn(
                  // 24px is a mouse-sized pill; a finger needs 40. Width is
                  // already ≥49px for every label, so only height moves.
                  "relative h-6 rounded-[6px] px-2 text-[11px] font-medium pointer-coarse:h-10 hover:bg-transparent",
                  selected
                    ? "text-[var(--ink)]"
                    : "text-[var(--ink-3)] hover:text-[var(--ink-2)]",
                )}
              >
                {selected ? (
                  <motion.span
                    aria-hidden
                    layoutId="throughput-range-pill"
                    className="absolute inset-0 rounded-[6px] bg-[var(--elevated)] shadow-[var(--shadow-flat)]"
                    transition={
                      reduceMotion
                        ? { duration: 0 }
                        : { type: "spring", stiffness: 460, damping: 38 }
                    }
                  />
                ) : null}
                <span className="relative">{option.label}</span>
              </Button>
            );
          })}
        </div>
      }
      footer={`記録が揃っているのは ${shortDate(dataWindow.completeThrough)} まで（${dataWindow.completeDays}日分）。以降は PK 実働時間が未記録。`}
    >
      {/* Heights step on the 4px rhythm. The dip at md is deliberate: from md
          to lg this card is full-bleed, so it needs far less height than it
          does in the 8-of-12 slot at xl to keep the same reading angle, and
          the band between them was the emptiest part of the page. */}
      <div
        ref={plotRef}
        className="h-[260px] w-full sm:h-[300px] md:h-[280px] xl:h-[340px]"
      >
        <ResponsiveContainer width="100%" height="100%">
          <ComposedChart
            data={data}
            margin={{ top: 10, right: 14, bottom: 0, left: -8 }}
          >
            <defs>
              <linearGradient id={PICK_FILL} x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor={series[1]} stopOpacity={0.22} />
                <stop offset="100%" stopColor={series[1]} stopOpacity={0} />
              </linearGradient>
              <linearGradient id={PACK_FILL} x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor={series[2]} stopOpacity={0.22} />
                <stop offset="100%" stopColor={series[2]} stopOpacity={0} />
              </linearGradient>
              <pattern
                id={GAP_HATCH}
                width="4"
                height="4"
                patternUnits="userSpaceOnUse"
                patternTransform="rotate(45)"
              >
                <line
                  x1="0"
                  y1="0"
                  x2="0"
                  y2="4"
                  stroke="var(--line-strong)"
                  strokeWidth="1"
                />
              </pattern>
            </defs>

            <CartesianGrid vertical={false} stroke="var(--grid)" />

            <XAxis
              dataKey="date"
              tickFormatter={shortDate}
              tickLine={false}
              axisLine={false}
              tickMargin={10}
              minTickGap={4}
              interval={fittedInterval(data.length, plotWidth)}
              tick={{ fill: "var(--axis)", fontSize: 11 }}
            />
            <YAxis
              domain={Y_DOMAIN}
              // 3 digits at 11px need 40px; at 34 the top tick rendered "26"
              // instead of "126" — silently clipped, not wrapped.
              width={40}
              tickLine={false}
              axisLine={false}
              tickMargin={6}
              tick={{ fill: "var(--axis)", fontSize: 11 }}
              tickFormatter={(value: number) => String(Math.round(value))}
            />

            {gap ? (
              <ReferenceArea
                x1={gap.x1}
                x2={gap.x2}
                fill={`url(#${GAP_HATCH})`}
                fillOpacity={0.45}
                stroke="none"
                /* Centred, the caption lands on ~100% — exactly where the
                   梱包 line runs through the gap. On a phone there is no room
                   to dodge sideways, so it moves to the top of the band where
                   nothing is plotted. */
                label={{
                  value: "記録なし",
                  position: narrowBand ? "insideTop" : "center",
                  fill: "var(--ink-4)",
                  fontSize: 10.5,
                  dy: narrowBand ? 4 : 0,
                }}
              />
            ) : null}

            <ReferenceLine
              y={100}
              stroke="var(--line-strong)"
              strokeDasharray="3 3"
              label={{
                value: "標準",
                position: "insideTopRight",
                fill: "var(--ink-3)",
                fontSize: 10.5,
                dy: -4,
              }}
            />

            <Tooltip
              cursor={{ stroke: "var(--line-strong)", strokeWidth: 1 }}
              content={
                <ChartTooltip
                  heading={(label) => longDate(label)}
                  rows={buildRows}
                />
              }
            />

            {/* Recharts defaults to a 1500ms sweep, which lands long after the
                card that holds it has finished appearing. 600ms keeps the
                draw legible on a range switch without dragging the page. */}
            <Area
              type="monotone"
              dataKey="pickEff"
              name="ピッキング効率"
              stroke={series[1]}
              strokeWidth={2}
              fill={`url(#${PICK_FILL})`}
              connectNulls={false}
              dot={false}
              isAnimationActive={!reduceMotion}
              animationDuration={600}
              animationEasing="ease-out"
              activeDot={{
                r: 4,
                fill: series[1],
                stroke: "var(--card)",
                strokeWidth: 2,
              }}
            />
            <Area
              type="monotone"
              dataKey="packEff"
              name="梱包効率"
              stroke={series[2]}
              strokeWidth={2}
              fill={`url(#${PACK_FILL})`}
              connectNulls={false}
              dot={false}
              isAnimationActive={!reduceMotion}
              animationDuration={600}
              animationEasing="ease-out"
              activeDot={{
                r: 4,
                fill: series[2],
                stroke: "var(--card)",
                strokeWidth: 2,
              }}
            />
          </ComposedChart>
        </ResponsiveContainer>
      </div>
    </ChartFrame>
  );
}
