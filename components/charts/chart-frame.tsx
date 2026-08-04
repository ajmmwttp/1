"use client";

import * as React from "react";

import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Reveal } from "@/components/motion/reveal";
import { cn } from "@/lib/utils";

/* ──────────────────────────────────────────────────────────────
   ChartFrame — the one shell every chart in the console sits in.
   Header (title + description left, action right), an optional
   legend row directly beneath it with no divider, the plot, and
   an optional hairline-separated footer for provenance notes.
   ────────────────────────────────────────────────────────────── */

export interface ChartLegendItem {
  /** A series token — var(--series-1|2|3|other). Never a raw hex, never the accent. */
  color: string;
  label: string;
}

export interface ChartLegendProps {
  items: ChartLegendItem[];
  className?: string;
}

/**
 * Swatch + label pairs at 11px. The label always wears an ink token:
 * the mark carries identity, the text never does.
 */
export function ChartLegend({ items, className }: ChartLegendProps) {
  return (
    <ul className={cn("flex flex-wrap items-center gap-x-4 gap-y-1", className)}>
      {items.map((item) => (
        <li key={item.label} className="flex items-center gap-1.5">
          <span
            aria-hidden
            className="size-2 shrink-0 rounded-[3px]"
            style={{ backgroundColor: item.color }}
          />
          <span className="text-[12px] leading-none text-[var(--ink-2)]">
            {item.label}
          </span>
        </li>
      ))}
    </ul>
  );
}

export interface ChartFrameProps {
  title: React.ReactNode;
  description?: React.ReactNode;
  /** ≥2 series ⇒ always pass a legend. */
  legend?: React.ReactNode;
  /** Controls that belong to the chart: range switchers, unit labels. */
  action?: React.ReactNode;
  footer?: React.ReactNode;
  className?: string;
  contentClassName?: string;
  /** Legend row alignment. Defaults to the start edge, under the title. */
  legendAlign?: "start" | "end";
  /** Step on the shared entrance ladder — see REVEAL_STEPS. */
  revealStep: number;
  /**
   * Opt into row-level alignment with sibling cards. The card claims four
   * subgrid rows (header / legend / plot / footer) so a title that wraps in
   * one card cannot push its plot out of line with the card beside it.
   * Empty slots still render, otherwise the row counts diverge.
   */
  subgrid?: boolean;
  children: React.ReactNode;
}

export function ChartFrame({
  title,
  description,
  legend,
  action,
  footer,
  className,
  contentClassName,
  legendAlign = "start",
  revealStep,
  subgrid = false,
  children,
}: ChartFrameProps) {
  return (
    // The Reveal wrapper is the grid child, so it has to stretch too —
    // otherwise the Card cannot fill the row and sibling cards end up
    // different heights.
    <Reveal
      step={revealStep}
      className={cn("flex w-full", subgrid && "md:row-span-4 md:grid md:grid-rows-subgrid")}
    >
      <Card
        data-card
        className={cn(
          "flex w-full flex-col overflow-hidden",
          subgrid && "md:row-span-4 md:grid md:grid-rows-subgrid",
          // Hover: a hairline lift, nothing else. No scale, no shadow bloom —
          // a card the cursor merely passes over should not move.
          "transition-colors duration-150 ease-out hover:border-[var(--line-strong)]",
          className,
        )}
      >
        <CardHeader className={legend ? "pb-2" : undefined}>
          <div className="min-w-0">
            <CardTitle>{title}</CardTitle>
            {description ? <CardDescription>{description}</CardDescription> : null}
          </div>
          {action ? <div className="shrink-0 pt-0.5">{action}</div> : null}
        </CardHeader>

        {legend || subgrid ? (
          <div
            className={cn(
              "flex px-5 pb-3",
              legendAlign === "end" ? "justify-end" : "justify-start",
            )}
          >
            {legend}
          </div>
        ) : null}

        <CardContent className={cn("flex flex-1 flex-col", contentClassName)}>
          {children}
        </CardContent>

        {footer || subgrid ? <CardFooter>{footer}</CardFooter> : null}
      </Card>
    </Reveal>
  );
}
