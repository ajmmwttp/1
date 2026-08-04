"use client";

import * as React from "react";

import { cn } from "@/lib/utils";

/* ──────────────────────────────────────────────────────────────
   ChartTooltip — the single tooltip surface for every chart.

   Recharts 3 types its injected content props loosely (payload is
   `any[]`), so this component declares its own narrow props and does
   the one and only cast at the boundary — the datum is narrowed to
   Record<string, unknown> and every field is checked before use.
   Nothing downstream ever sees an untyped value.
   ────────────────────────────────────────────────────────────── */

/** The slice of a Recharts payload entry we actually read. */
export interface ChartTooltipEntry {
  dataKey?: string | number;
  name?: string | number;
  value?: number | string | null;
  color?: string;
  payload?: Record<string, unknown>;
}

export interface ChartTooltipRow {
  /** Series token for the swatch. Omit for a derived row (差, 合計 …). */
  color?: string;
  label: string;
  value: React.ReactNode;
  /** A row with no reading — renders recessive, in var(--ink-4). */
  muted?: boolean;
}

export interface ChartTooltipProps {
  /* injected by Recharts */
  active?: boolean;
  label?: string | number;
  payload?: readonly ChartTooltipEntry[];
  /* ours */
  heading?: (label: string) => React.ReactNode;
  /**
   * Builds the rows from the raw datum. Given explicitly so a series
   * whose value is null still gets a row (記録なし) instead of vanishing.
   */
  rows?: (
    datum: Record<string, unknown>,
    entries: readonly ChartTooltipEntry[],
  ) => ChartTooltipRow[];
  className?: string;
}

export function ChartTooltip({
  active,
  label,
  payload,
  heading,
  rows,
  className,
}: ChartTooltipProps) {
  if (!active || !payload || payload.length === 0) return null;

  const datum = (payload[0]?.payload ?? {}) as Record<string, unknown>;
  const items: ChartTooltipRow[] = rows
    ? rows(datum, payload)
    : payload.map((entry) => ({
        color: entry.color,
        label: String(entry.name ?? entry.dataKey ?? ""),
        value:
          entry.value === null || entry.value === undefined
            ? "—"
            : String(entry.value),
        muted: entry.value === null || entry.value === undefined,
      }));

  const title =
    label === undefined || label === null
      ? null
      : heading
        ? heading(String(label))
        : String(label);

  return (
    <div
      className={cn(
        "min-w-[150px] rounded-[10px] border border-[var(--line)] bg-[var(--elevated)] px-2.5 py-2 shadow-[var(--shadow-pop)]",
        className,
      )}
    >
      {title ? (
        <div className="mb-1.5 text-[12px] leading-none text-[var(--ink-3)]">
          {title}
        </div>
      ) : null}

      <div className="flex flex-col gap-1">
        {items.map((row) => (
          <div key={row.label} className="flex items-center gap-2">
            <span
              aria-hidden
              className="size-2 shrink-0 rounded-[3px]"
              style={{ backgroundColor: row.color ?? "transparent" }}
            />
            <span className="text-[12px] leading-none text-[var(--ink-2)]">
              {row.label}
            </span>
            <span
              className={cn(
                "ml-auto pl-3 text-[12px] leading-none",
                row.muted
                  ? "text-[var(--ink-4)]"
                  : "tnum text-[var(--ink)]",
              )}
            >
              {row.value}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}
