"use client";

import * as React from "react";
import {
  CartesianGrid,
  ResponsiveContainer,
  Scatter,
  ScatterChart,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

// REVEAL_STEPS lives in ladder.ts, not reveal.tsx: reveal.tsx is
// "use client", and its exports reach a server component as client
// references rather than values.
import { REVEAL_STEPS } from "@/components/motion/ladder";
import { series } from "@/lib/chart-theme";
import { workers } from "@/lib/data/warehouse";
import { dec, int } from "@/lib/format";

import { ChartFrame } from "./chart-frame";
import { ChartTooltip, type ChartTooltipRow } from "./chart-tooltip";

/* ──────────────────────────────────────────────────────────────
   SetupScatter — the pair that carries the whole argument.

   ① y = 素の秒/件   tilts with x   (r=+0.490, p=0.011)
   ② y = 純速度      does not       (r=+0.061, p=0.768)

   Same x, same domains, same box. The two panels are only comparable
   because NOTHING varies between them except the y measure, so the
   domains are hand-fixed constants shared by both — never per-panel
   auto-scaling, which would silently magnify ②'s residual tilt until
   it looked like signal.

   AXIS ORIGIN — decided, not defaulted:
   · x = 企業数 ÷ 件数 is a density with a true zero and a meaningful
     ceiling of 1.00 ("every list is one company, one item" — the
     pathological case this dashboard exists to explain). Truncating it
     would hide how far the floor sits from that ceiling. Zero origin.
   · y = 秒/件 is a duration per item, a ratio quantity. The vertical
     gap between the two clouds IS the setup time, and that reading is
     only quantitative against a common zero. Zero origin.

   OUTLIERS cannot stretch the scale because the domains are round
   constants, not dataMax-derived. Dot area encodes 件数, so the two
   extremes read as the smallest samples they are (n=66, n=160) rather
   than as strong evidence.
   ────────────────────────────────────────────────────────────── */

const X_DOMAIN: [number, number] = [0, 0.8];
const Y_DOMAIN: [number, number] = [0, 200];
const X_TICKS = [0, 0.2, 0.4, 0.6, 0.8];
const Y_TICKS = [0, 50, 100, 150, 200];

interface Point {
  name: string;
  x: number;
  raw: number;
  pure: number;
  items: number;
  /** 0–1 on √items — drives both radius and fill opacity. */
  weight: number;
}

const RAW: Omit<Point, "weight">[] = workers.flatMap((w) =>
  w.pick
    ? [
        {
          name: w.name,
          x: w.pick.companies / w.pick.items,
          raw: w.pick.rawSecPerItem,
          pure: w.pick.pureSecPerItem,
          items: w.pick.items,
        },
      ]
    : [],
);

const ROOTS = RAW.map((p) => Math.sqrt(p.items));
const ROOT_MIN = Math.min(...ROOTS);
const ROOT_MAX = Math.max(...ROOTS);

const POINTS: Point[] = RAW.map((p) => ({
  ...p,
  weight: (Math.sqrt(p.items) - ROOT_MIN) / (ROOT_MAX - ROOT_MIN),
}));

const R_MIN = 3.5;
const R_MAX = 9;
const OPACITY_MIN = 0.35;
const OPACITY_MAX = 0.7;

interface DotProps {
  cx?: number;
  cy?: number;
  payload?: Point;
  fill?: string;
}

/** Area-encoded dot. Overlaps read as a darker lens; the stroke keeps
 *  every point's outline intact where two land on each other. */
function Dot({ cx, cy, payload, fill }: DotProps) {
  if (cx === undefined || cy === undefined || !payload) return null;
  const w = payload.weight;
  return (
    <circle
      cx={cx}
      cy={cy}
      r={R_MIN + w * (R_MAX - R_MIN)}
      fill={fill}
      fillOpacity={OPACITY_MIN + w * (OPACITY_MAX - OPACITY_MIN)}
      stroke={fill}
      strokeOpacity={0.9}
      strokeWidth={1.25}
    />
  );
}

interface PanelProps {
  yKey: "raw" | "pure";
  title: React.ReactNode;
  description: string;
  stat: string;
  color: string;
  yLabel: string;
  revealStep: number;
}

function Panel({ yKey, title, description, stat, color, yLabel, revealStep }: PanelProps) {
  const rows = React.useCallback(
    (datum: Record<string, unknown>): ChartTooltipRow[] => {
      const p = datum as unknown as Point;
      return [
        { label: "担当者", value: p.name },
        { color, label: yLabel, value: `${dec(p[yKey], 1)} 秒` },
        { label: "社 / 件", value: dec(p.x, 2) },
        { label: "件数", value: `${int(p.items)} 件` },
      ];
    },
    [color, yKey, yLabel],
  );

  return (
    <ChartFrame
      revealStep={revealStep}
      subgrid
      title={title}
      description={description}
      action={
        <span className="shrink-0 whitespace-nowrap text-[12px] text-[var(--ink-3)]">
          秒 / 件
        </span>
      }
      footer={stat}
    >
      {/* aspect-ratio, not a pixel height: the box stays proportional at
          every width and ResponsiveContainer still gets a definite size. */}
      <div className="aspect-[4/3] w-full">
        <ResponsiveContainer width="100%" height="100%">
          <ScatterChart margin={{ top: 8, right: 12, bottom: 4, left: -6 }}>
            <CartesianGrid stroke="var(--grid)" />
            <XAxis
              type="number"
              dataKey="x"
              domain={X_DOMAIN}
              ticks={X_TICKS}
              tickFormatter={(v: number) => dec(v, 1)}
              tickLine={false}
              axisLine={false}
              tickMargin={8}
              tick={{ fill: "var(--axis)", fontSize: 12 }}
            />
            <YAxis
              type="number"
              dataKey={yKey}
              domain={Y_DOMAIN}
              ticks={Y_TICKS}
              tickFormatter={(v: number) => int(v)}
              tickLine={false}
              axisLine={false}
              tickMargin={6}
              width={40}
              tick={{ fill: "var(--axis)", fontSize: 12 }}
            />
            <Tooltip
              cursor={{ stroke: "var(--line-strong)", strokeWidth: 1 }}
              content={<ChartTooltip rows={rows} />}
            />
            <Scatter
              data={POINTS}
              fill={color}
              shape={<Dot />}
              isAnimationActive={false}
            />
          </ScatterChart>
        </ResponsiveContainer>
      </div>
      {/* Axis name as HTML, not an SVG <Label> — SVG labels are the thing
          that clips silently, and this codebase has already been bitten. */}
      <p className="mt-1 text-center text-[12px] text-[var(--ink-3)]">
        企業数 ÷ 件数（社 / 件）
      </p>
    </ChartFrame>
  );
}

export function SetupScatterContaminated() {
  return (
    <Panel
      revealStep={REVEAL_STEPS.scatterRow}
      yKey="raw"
      title="① 素の秒/件 は、リストの構成で決まってしまう"
      description="右にいる人ほど「1社1個」のリストを多く引いた人。右上がりなら、速さではなく担当したリストの中身が数字を決めている。"
      stat="r = +0.490 ・ p = 0.011 ・ n = 26　右上がりは偶然では説明できない"
      color={series[2]}
      yLabel="素の秒/件"
    />
  );
}

export function SetupScatterCorrected() {
  return (
    <Panel
      revealStep={REVEAL_STEPS.scatterRow}
      yKey="pure"
      title="② 段取りを除くと、その傾きが消える"
      description="横軸は①と全く同じ。縦軸だけ純速度に替えたもの。傾きが消えれば、担当リストの偏りを取り除けたことになる。"
      stat="r = +0.061 ・ p = 0.768 ・ n = 26　傾きは無いと言ってよい"
      color={series[1]}
      yLabel="純速度"
    />
  );
}
