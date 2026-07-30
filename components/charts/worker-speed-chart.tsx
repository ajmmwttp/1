"use client";

import { useReducedMotion } from "framer-motion";
import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { REVEAL_STEPS } from "@/components/motion/ladder";
import { MARK, series } from "@/lib/chart-theme";
import { workers } from "@/lib/data/warehouse";
import { dec, int } from "@/lib/format";

import { ChartFrame, ChartLegend } from "./chart-frame";
import { ChartTooltip, type ChartTooltipRow } from "./chart-tooltip";

/* ──────────────────────────────────────────────────────────────
   WorkerSpeedChart — the thesis in one picture.

   Two bars, one scale, same unit (秒/件). The orange bar is the old
   unfair number: it charges every list's setup to whoever happened
   to pull many one-item lists. The blue bar removes setup and shows
   the actual pace. The distance between them IS the argument.
   ────────────────────────────────────────────────────────────── */

interface SpeedRow {
  name: string;
  raw: number;
  pure: number;
  items: number;
}

/** Top 12 by volume — below that the bars stop meaning anything — then ranked by true speed. */
const DATA: SpeedRow[] = workers
  .flatMap((worker) =>
    worker.pick
      ? [
          {
            name: worker.name,
            raw: worker.pick.rawSecPerItem,
            pure: worker.pick.pureSecPerItem,
            items: worker.pick.items,
          },
        ]
      : [],
  )
  .sort((a, b) => b.items - a.items)
  .slice(0, 12)
  .sort((a, b) => a.pure - b.pure);

const LEGEND = [
  { color: series[2], label: "素の秒/件" },
  { color: series[1], label: "純速度" },
];

const sec = (value: number) => `${dec(value, 1)} 秒`;

function buildRows(datum: Record<string, unknown>): ChartTooltipRow[] {
  const raw = typeof datum.raw === "number" ? datum.raw : null;
  const pure = typeof datum.pure === "number" ? datum.pure : null;
  const rows: ChartTooltipRow[] = [
    {
      color: series[2],
      label: "素の秒/件",
      value: raw === null ? "記録なし" : sec(raw),
      muted: raw === null,
    },
    {
      color: series[1],
      label: "純速度",
      value: pure === null ? "記録なし" : sec(pure),
      muted: pure === null,
    },
  ];
  if (raw !== null && pure !== null) {
    rows.push({ label: "差", value: `${dec(raw - pure, 1)} 秒` });
  }
  if (typeof datum.items === "number") {
    rows.push({ label: "件数", value: int(datum.items) });
  }
  return rows;
}

export function WorkerSpeedChart() {
  const reduceMotion = useReducedMotion();

  return (
    <ChartFrame
      revealStep={REVEAL_STEPS.barChart}
      title="ピッキング速度：素の秒/件 と 純速度"
      description="素の秒/件は、1社1個のリストを多く引いた人ほど不利に出ます。純速度は段取りを除いた実力です。"
      legend={<ChartLegend items={LEGEND} />}
      legendAlign="end"
      action={
        <span className="text-[10.5px] uppercase tracking-[0.09em] text-[var(--ink-4)]">
          秒 / 件
        </span>
      }
      footer="件数上位12名。バーが短いほど速い。"
    >
      <div className="h-[340px] w-full">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart
            data={DATA}
            layout="vertical"
            barGap={2}
            barCategoryGap="28%"
            margin={{ top: 4, right: 12, bottom: 0, left: 0 }}
          >
            <CartesianGrid horizontal={false} stroke="var(--grid)" />

            <XAxis
              type="number"
              tickLine={false}
              axisLine={false}
              tickMargin={8}
              tick={{ fill: "var(--axis)", fontSize: 11 }}
              tickFormatter={(value: number) => String(Math.round(value))}
            />
            <YAxis
              type="category"
              dataKey="name"
              width={78}
              tickLine={false}
              axisLine={false}
              tickMargin={6}
              tick={{ fill: "var(--ink-2)", fontSize: 11 }}
            />

            <Tooltip
              cursor={{ fill: "var(--elevated)", fillOpacity: 0.55 }}
              content={<ChartTooltip rows={buildRows} />}
            />

            {/* 600ms, not the 1500ms default: the bars should finish growing
                while the card is still settling, not a second after it. */}
            <Bar
              dataKey="raw"
              name="素の秒/件"
              fill={series[2]}
              barSize={9}
              radius={MARK.barRadiusH}
              isAnimationActive={!reduceMotion}
              animationDuration={600}
              animationEasing="ease-out"
            />
            <Bar
              dataKey="pure"
              name="純速度"
              fill={series[1]}
              barSize={9}
              radius={MARK.barRadiusH}
              isAnimationActive={!reduceMotion}
              animationDuration={600}
              animationEasing="ease-out"
            />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </ChartFrame>
  );
}
