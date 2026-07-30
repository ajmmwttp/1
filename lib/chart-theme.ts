/**
 * Chart tokens.
 *
 * The categorical slots are assigned in a FIXED order and never cycled.
 * They were validated against both surfaces with the palette validator:
 *   dark  (surface #0F0F12) — worst all-pairs CVD ΔE 9.4, normal-vision 20.9
 *   light (surface #FFFFFF) — worst all-pairs CVD ΔE 9.2, normal-vision 24.0
 * A fourth categorical hue FAILS the all-pairs gate (yellow↔orange, CVD 4.8 /
 * normal-vision 10.6), which is why any part-to-whole view caps at three
 * slices and folds the remainder into a neutral "その他".
 *
 * Light-mode aqua sits at 2.82:1 against white, so the relief rule applies:
 * every chart ships direct labels or a legend carrying values, never colour
 * alone.
 */

export const series = {
  1: "var(--series-1)",
  2: "var(--series-2)",
  3: "var(--series-3)",
  other: "var(--series-other)",
} as const;

export const SERIES_ORDER = [series[1], series[2], series[3]] as const;

export const status = {
  good: "var(--good)",
  warning: "var(--warning)",
  serious: "var(--serious)",
  critical: "var(--critical)",
} as const;

export const axis = {
  stroke: "var(--grid)",
  tick: { fill: "var(--axis)", fontSize: 11 },
  line: false as const,
};

/** Recharts margin that leaves room for labels without wasting canvas. */
export const chartMargin = { top: 8, right: 8, bottom: 0, left: -8 };

export const MARK = {
  lineWidth: 2,
  dotSize: 8,
  barRadius: [4, 4, 0, 0] as [number, number, number, number],
  barRadiusH: [0, 4, 4, 0] as [number, number, number, number],
  /** 2px surface gap between adjacent fills. */
  gap: 2,
};

export const verdictTone: Record<string, { color: string; label: string }> = {
  上位: { color: status.good, label: "上位" },
  標準: { color: "var(--ink-3)", label: "標準" },
  要支援: { color: status.critical, label: "要支援" },
};
