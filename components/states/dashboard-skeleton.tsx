import * as React from "react";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";

/* ──────────────────────────────────────────────────────────────
   Loading skeletons.

   These trace the real layout — same grid shapes, same heights, same
   card padding — so the page does not reflow when data lands. Every
   visual part is aria-hidden; the outermost element of each exported
   skeleton is the single live region that says 読み込み中です.
   ────────────────────────────────────────────────────────────── */

const BAR = "rounded-[4px]";

function StatusRegion({
  className,
  children,
}: {
  className?: string;
  children: React.ReactNode;
}) {
  return (
    <div role="status" aria-live="polite" aria-busy="true" className={className}>
      <span className="sr-only">読み込み中です</span>
      {children}
    </div>
  );
}

/**
 * `.skeleton` paints its own background, which would bury the chart
 * silhouette. So we float a transparent copy on top instead: the ::after
 * shimmer still runs, and the reduced-motion bypass in globals.css still
 * switches it off.
 *
 * position/inset/background are inline because `.skeleton` is declared
 * outside any cascade layer in globals.css, and unlayered rules outrank
 * every Tailwind utility — `absolute` alone would lose to its `relative`.
 */
function ShimmerOverlay() {
  return (
    <div
      aria-hidden
      className="skeleton pointer-events-none rounded-[8px]"
      style={{ position: "absolute", inset: 0, background: "transparent" }}
    />
  );
}

/* ── KPI row ──────────────────────────────────────────────── */

function KpiCardSkeleton() {
  return (
    <Card className="p-4">
      <Skeleton className={cn("h-[11px] w-20", BAR)} />
      <Skeleton className="mt-3 h-[30px] w-28 rounded-[6px]" />
      <div className="mt-4 flex items-center justify-between">
        <Skeleton className="h-4 w-16 rounded-[6px]" />
        <Skeleton className="h-6 w-[72px] rounded-[6px]" />
      </div>
    </Card>
  );
}

function KpiRowBody({ className }: { className?: string }) {
  return (
    <div
      aria-hidden
      className={cn("grid gap-3 sm:grid-cols-2 xl:grid-cols-4", className)}
    >
      {[0, 1, 2, 3].map((i) => (
        <KpiCardSkeleton key={i} />
      ))}
    </div>
  );
}

export function KpiRowSkeleton({ className }: { className?: string }) {
  return (
    <StatusRegion className={className}>
      <KpiRowBody />
    </StatusRegion>
  );
}

/* ── Chart ────────────────────────────────────────────────── */

/** A plausible trend, not a rectangle: rising with the wobble real days have. */
const CURVE =
  "M0 150C30 150 30 132 60 132C90 132 90 140 120 140C150 140 150 104 180 104C210 104 210 118 240 118C270 118 270 76 300 76C330 76 330 92 360 92C390 92 390 58 420 58C450 58 450 74 480 74C510 74 510 44 540 44C570 44 570 60 600 60";
const AREA = `${CURVE}L600 200L0 200Z`;

const GRID_LINES = [20, 40, 60, 80];
const BAR_WIDTHS = [92, 78, 71, 63, 55, 46, 36, 24];

function AreaPlot() {
  return (
    <>
      <svg
        aria-hidden
        focusable="false"
        viewBox="0 0 600 200"
        preserveAspectRatio="none"
        className="absolute inset-0 h-full w-full"
      >
        <path d={AREA} fill="var(--elevated)" />
        <path
          d={CURVE}
          fill="none"
          stroke="var(--line-strong)"
          strokeWidth={1}
          vectorEffect="non-scaling-stroke"
        />
      </svg>
      {GRID_LINES.map((top) => (
        <div
          key={top}
          aria-hidden
          className="absolute inset-x-0 h-px bg-[var(--line)]"
          style={{ top: `${top}%` }}
        />
      ))}
    </>
  );
}

function BarsPlot() {
  return (
    <div className="flex h-full flex-col justify-between py-1">
      {BAR_WIDTHS.map((width, i) => (
        <Skeleton
          key={i}
          className={cn("h-2.5", BAR)}
          style={{ width: `${width}%` }}
        />
      ))}
    </div>
  );
}

interface ChartBodyProps {
  height: number;
  bars: boolean;
  className?: string;
}

function ChartBody({ height, bars, className }: ChartBodyProps) {
  return (
    <Card aria-hidden className={className}>
      <CardHeader>
        <div className="w-full">
          <Skeleton className={cn("h-3.5 w-32", BAR)} />
          <Skeleton className={cn("mt-2 h-2.5 w-56", BAR)} />
        </div>
      </CardHeader>
      <CardContent>
        <div className="relative overflow-hidden rounded-[8px]" style={{ height }}>
          {bars ? (
            <BarsPlot />
          ) : (
            <>
              <AreaPlot />
              <ShimmerOverlay />
            </>
          )}
        </div>
      </CardContent>
    </Card>
  );
}

export interface ChartSkeletonProps {
  height?: number;
  bars?: boolean;
  className?: string;
}

export function ChartSkeleton({
  height = 280,
  bars = false,
  className,
}: ChartSkeletonProps) {
  return (
    <StatusRegion className={className}>
      {/* h-full so the card fills a stretched grid row, as the real card does */}
      <ChartBody height={height} bars={bars} className="h-full" />
    </StatusRegion>
  );
}

/* ── Table ────────────────────────────────────────────────── */

const TABLE_GRID = "grid grid-cols-[1.6fr_1fr_1fr_1fr_1fr_0.9fr] gap-4 px-5";

/** Numeric columns are tnum in the real table, so their widths barely move;
 *  only the name column varies row to row. */
const TABLE_COLS = [
  { head: "w-14", cell: "w-28", end: false },
  { head: "w-10", cell: "w-16", end: true },
  { head: "w-12", cell: "w-12", end: true },
  { head: "w-10", cell: "w-20", end: true },
  { head: "w-12", cell: "w-14", end: true },
  { head: "w-8", cell: "w-10", end: true },
];

const NAME_WIDTHS = ["w-28", "w-24", "w-32", "w-20", "w-28", "w-24"];

function TableBody({ rows, className }: { rows: number; className?: string }) {
  return (
    <Card aria-hidden className={className}>
      <CardHeader>
        <div className="w-full">
          <Skeleton className={cn("h-3.5 w-32", BAR)} />
          <Skeleton className={cn("mt-2 h-2.5 w-56", BAR)} />
        </div>
      </CardHeader>

      <div className={cn(TABLE_GRID, "h-9 items-center")}>
        {TABLE_COLS.map((col, i) => (
          <div key={i} className={cn("flex", col.end && "justify-end")}>
            <Skeleton className={cn("h-2", BAR, col.head)} />
          </div>
        ))}
      </div>

      {Array.from({ length: rows }, (_, row) => (
        <div
          key={row}
          className={cn(
            TABLE_GRID,
            "h-10 items-center border-t border-[var(--line)]",
          )}
        >
          {TABLE_COLS.map((col, i) => (
            <div key={i} className={cn("flex", col.end && "justify-end")}>
              <Skeleton
                className={cn(
                  "h-2.5",
                  BAR,
                  i === 0 ? NAME_WIDTHS[row % NAME_WIDTHS.length] : col.cell,
                )}
              />
            </div>
          ))}
        </div>
      ))}
    </Card>
  );
}

export interface TableSkeletonProps {
  rows?: number;
  className?: string;
}

export function TableSkeleton({ rows = 8, className }: TableSkeletonProps) {
  return (
    <StatusRegion className={className}>
      <TableBody rows={rows} className="h-full" />
    </StatusRegion>
  );
}

/* ── Whole page ───────────────────────────────────────────── */

export function DashboardSkeleton({ className }: { className?: string }) {
  return (
    <StatusRegion className={cn("flex flex-col gap-4", className)}>
      <KpiRowBody />
      <div className="grid grid-cols-1 gap-4 xl:grid-cols-12">
        <ChartBody height={340} bars={false} className="xl:col-span-8" />
        <ChartBody height={260} bars className="xl:col-span-4" />
      </div>
      <TableBody rows={8} />
    </StatusRegion>
  );
}
