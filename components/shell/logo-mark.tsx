import { cn } from "@/lib/utils";

/**
 * The Ledger mark. A vertical ledger rule with three shelf bars stepping
 * down off it — stacked shelves read at 20px, a ruled ledger page at 40px.
 * Drawn by hand rather than borrowed from an icon set so the chrome has one
 * thing that belongs only to this product.
 */
export function LedgerMark({ className }: { className?: string }) {
  return (
    <svg
      viewBox="0 0 20 20"
      width={20}
      height={20}
      fill="none"
      aria-hidden
      className={cn("shrink-0", className)}
    >
      {/* the rule */}
      <path
        d="M3.25 2.75v14.5"
        stroke="var(--ink)"
        strokeWidth={1.6}
        strokeLinecap="round"
      />
      {/* shelves, stepping in */}
      <path
        d="M6.5 5.75h10.25"
        stroke="var(--ink)"
        strokeWidth={1.6}
        strokeLinecap="round"
      />
      <path
        d="M6.5 10h7.25"
        stroke="var(--accent)"
        strokeWidth={1.6}
        strokeLinecap="round"
      />
      <path
        d="M6.5 14.25h4.25"
        stroke="var(--ink)"
        strokeWidth={1.6}
        strokeLinecap="round"
        opacity={0.5}
      />
    </svg>
  );
}

/** "Ledger" + the OPS chip. Hidden when the sidebar collapses. */
export function Wordmark({ className }: { className?: string }) {
  return (
    <span className={cn("flex items-center gap-1.5", className)}>
      <span className="font-sans text-[12px] font-semibold tracking-[-0.015em] text-[var(--ink)]">
        Ledger
      </span>
      <span className="rounded-[4px] border border-[var(--accent-line)] bg-[var(--accent-wash)] px-1 py-px font-sans text-[12px] font-semibold uppercase leading-[1.35] tracking-[0.12em] text-[var(--accent)]">
        OPS
      </span>
    </span>
  );
}
