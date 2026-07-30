import { ArrowUp, Minus, TriangleAlert } from "lucide-react";
import type { LucideIcon } from "lucide-react";
import type { Verdict } from "@/lib/data/warehouse";
import { cn } from "@/lib/utils";

/**
 * Status never rides on colour alone — every verdict ships an icon and a label
 * so it survives greyscale and colour-vision deficiency.
 */
const STYLES: Record<Verdict, { Icon: LucideIcon; className: string }> = {
  上位: {
    Icon: ArrowUp,
    className:
      "border-[color-mix(in_srgb,var(--good-text)_26%,transparent)] bg-[color-mix(in_srgb,var(--good-text)_11%,transparent)] text-[var(--good-text)]",
  },
  標準: {
    Icon: Minus,
    className: "border-[var(--line)] bg-[var(--elevated)] text-[var(--ink-3)]",
  },
  要支援: {
    Icon: TriangleAlert,
    className:
      "border-[color-mix(in_srgb,var(--critical-text)_26%,transparent)] bg-[color-mix(in_srgb,var(--critical-text)_11%,transparent)] text-[var(--critical-text)]",
  },
};

export function VerdictPill({ verdict, className }: { verdict: Verdict; className?: string }) {
  const { Icon, className: tone } = STYLES[verdict];
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 rounded-[6px] border px-1.5 py-[3px] text-[12px] font-medium leading-none whitespace-nowrap",
        tone,
        className,
      )}
    >
      <Icon className="size-3 shrink-0" aria-hidden />
      {verdict}
    </span>
  );
}
