/* ──────────────────────────────────────────────────────────────
   The entrance ladder.

   Deliberately NOT in reveal.tsx: that file is "use client", and every
   export of a "use client" module reaches a server component as a client
   reference, not as a value. KpiRow is a server component, so importing
   REVEAL_STEPS from there gave `undefined` and shipped `delay: NaN` to
   the browser. Plain module, no directive, imported by both sides.
   ────────────────────────────────────────────────────────────── */

/** Matches --ease-out-expo in globals.css. */
export const REVEAL_EASE: [number, number, number, number] = [0.16, 1, 0.3, 1];
export const REVEAL_DURATION = 0.32;
export const REVEAL_STEP = 0.04;

/**
 * Reading order. The KPI tiles take steps 0–3, then the chart row, the bar
 * chart and the table get one beat each. The last element starts at 240ms
 * and its 320ms travel ends at 560ms — but on the expo curve every element
 * is past 95% of its distance within ~130ms of its own start, so the page
 * reads as assembled at roughly 370ms and the tail is only the settle.
 */
export const REVEAL_STEPS = {
  /** Add the tile index (0–3). The section lede shares tile 0's beat. */
  kpiTile: 0,
  /** 日次の効率推移 + ピッキング時間の内訳 — one row, one beat. */
  chartRow: 4,
  barChart: 5,
  table: 6,
} as const;

export const revealDelay = (step: number) => step * REVEAL_STEP;
