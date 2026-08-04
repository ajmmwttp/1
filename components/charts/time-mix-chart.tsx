"use client";

import * as React from "react";
import {
  Cell,
  Pie,
  PieChart,
  ResponsiveContainer,
  Sector,
  type PieSectorShapeProps,
} from "recharts";

import { REVEAL_STEPS } from "@/components/motion/ladder";
import { series, SERIES_ORDER } from "@/lib/chart-theme";
import { timeMix, totals, type MixSlice } from "@/lib/data/warehouse";
import { dec, hours, minutesToHours, pct } from "@/lib/format";
import { cn } from "@/lib/utils";

import { ChartFrame } from "./chart-frame";

/* ──────────────────────────────────────────────────────────────
   TimeMixChart — ピッキング時間の内訳.

   Three hues, in fixed order, and never a fourth: a 4th categorical
   hue fails the all-pairs colour-vision gate (measured: CVD ΔE 4.8).
   `foldToThree` enforces that at the data boundary — anything past
   the third slice collapses into a neutral その他.

   The legend below carries hours and share, which is what discharges
   the low-contrast relief rule; it is not decoration and must ship.
   ────────────────────────────────────────────────────────────── */

interface MixDatum {
  label: string;
  detail: string;
  hours: number;
  color: string;
  share: number;
}

function foldToThree(slices: readonly MixSlice[]): MixSlice[] {
  if (slices.length <= 3) return [...slices];
  const head = slices.slice(0, 3);
  const rest = slices.slice(3);
  return [
    ...head,
    {
      label: "その他",
      detail: `${rest.length}項目をまとめて表示`,
      hours: rest.reduce((sum, slice) => sum + slice.hours, 0),
    },
  ];
}

const SLICES = foldToThree(timeMix);
/** Shares are taken against the slice sum so they close at 100%. */
const SLICE_HOURS = SLICES.reduce((sum, slice) => sum + slice.hours, 0);
/** The headline total comes from the source minutes, not the rounded slices. */
const PICK_HOURS = minutesToHours(totals.pickMinutes);

const DATA: MixDatum[] = SLICES.map((slice, index) => ({
  ...slice,
  color: index < SERIES_ORDER.length ? SERIES_ORDER[index] : series.other,
  share: (slice.hours / SLICE_HOURS) * 100,
}));

/** 付加価値作業 = the only slice where a hand actually touches product. */
const VALUE_ADDING = DATA.find((slice) => slice.label === "ピック");
const VALUE_ADDING_SHARE = VALUE_ADDING ? VALUE_ADDING.share : 0;

const HOVER_GROWTH = 3;

export function TimeMixChart() {
  const [activeIndex, setActiveIndex] = React.useState<number | null>(null);

  const renderSector = React.useCallback(
    (props: PieSectorShapeProps) => {
      const grow = props.index === activeIndex ? HOVER_GROWTH : 0;
      return (
        <Sector
          cx={props.cx}
          cy={props.cy}
          innerRadius={props.innerRadius}
          outerRadius={props.outerRadius + grow}
          startAngle={props.startAngle}
          endAngle={props.endAngle}
          cornerRadius={props.cornerRadius}
          fill={props.fill}
          stroke="var(--card)"
          strokeWidth={2}
        />
      );
    },
    [activeIndex],
  );

  return (
    <ChartFrame
      revealStep={REVEAL_STEPS.chartRow}
      title="ピッキング時間の内訳"
      description={`${dec(PICK_HOURS, 0)}時間を作業単位で分解。手を動かしているのは3割だけ。`}
      footer="段取りは1社ごとに一度だけ発生します。件数で割ると人の速さに見えてしまう部分です。"
    >
      {/* md → lg is the band where this card is full-bleed: at xl it sits in
          4 of 12 and the stack is right, but from md to lg the same stack left
          a 260px donut floating in a ~680px box with the legend stranded
          underneath. Splitting it 5/7 on the same 12-column vocabulary fills
          that band and takes ~150px of dead height off the page. */}
      <div className="grid grid-cols-1 items-center gap-4 md:grid-cols-12 xl:grid-cols-1">
        <div className="relative h-[260px] w-full md:col-span-5 xl:col-span-1">
          <ResponsiveContainer width="100%" height="100%">
            <PieChart>
              <Pie
                data={DATA}
                dataKey="hours"
                nameKey="label"
                innerRadius="62%"
                outerRadius="88%"
                paddingAngle={2}
                cornerRadius={3}
                stroke="var(--card)"
                strokeWidth={2}
                shape={renderSector}
                // The donut arrives with its card and nothing else. Recharts
                // sweeps the angles over 1500ms by default, and because the
                // sectors re-render on every hover that sweep can restart under
                // the cursor. The card's own reveal is the entrance here.
                isAnimationActive={false}
                onMouseEnter={(_, index: number) => setActiveIndex(index)}
                onMouseLeave={() => setActiveIndex(null)}
              >
                {DATA.map((slice) => (
                  <Cell key={slice.label} fill={slice.color} />
                ))}
              </Pie>
            </PieChart>
          </ResponsiveContainer>

          <div className="pointer-events-none absolute inset-0 flex flex-col items-center justify-center">
            <span className="tnum text-[30px] leading-none text-[var(--ink)]">
              {pct(VALUE_ADDING_SHARE)}
            </span>
            <span className="mt-2 text-[12px] uppercase tracking-[0.09em] text-[var(--ink-4)]">
              付加価値作業
            </span>
          </div>
        </div>

        <ul className="mt-3 flex flex-col gap-0.5 md:col-span-7 md:mt-0 xl:col-span-1 xl:mt-3">
          {DATA.map((slice, index) => (
            <li
              key={slice.label}
              onMouseEnter={() => setActiveIndex(index)}
              onMouseLeave={() => setActiveIndex(null)}
              className={cn(
                "flex items-start gap-2.5 rounded-[6px] px-2 py-1.5 transition-colors duration-150",
                activeIndex === index ? "bg-[var(--elevated)]" : "bg-transparent",
              )}
            >
              <span
                aria-hidden
                className="mt-1 size-2 shrink-0 rounded-[3px]"
                style={{ backgroundColor: slice.color }}
              />
              {/* Label and detail stack so the detail is never clipped — this
                  legend carries the values that discharge the low-contrast
                  relief rule, so it must stay fully readable. */}
              <span className="min-w-0 flex-1">
                <span className="block text-[12px] leading-none text-[var(--ink-2)]">
                  {slice.label}
                </span>
                <span className="mt-1 block text-[12px] leading-[1.4] text-[var(--ink-4)]">
                  {slice.detail}
                </span>
              </span>
              <span className="tnum shrink-0 pl-2 text-[12px] leading-none text-[var(--ink)]">
                {hours(slice.hours)}
              </span>
              <span className="tnum w-12 shrink-0 text-right text-[12px] leading-none text-[var(--ink-3)]">
                {pct(slice.share)}
              </span>
            </li>
          ))}
        </ul>
      </div>
    </ChartFrame>
  );
}
