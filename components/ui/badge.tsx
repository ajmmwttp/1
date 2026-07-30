import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

const badgeVariants = cva(
  "inline-flex items-center gap-1.5 rounded-[6px] border px-1.5 py-0.5 text-[12px] font-medium leading-none whitespace-nowrap",
  {
    variants: {
      tone: {
        neutral:
          "border-[var(--line)] bg-[var(--elevated)] text-[var(--ink-2)]",
        accent:
          "border-[var(--accent-line)] bg-[var(--accent-wash)] text-[var(--accent)]",
        good: "border-transparent bg-[color-mix(in_srgb,var(--good)_16%,transparent)] text-[var(--good)]",
        critical:
          "border-transparent bg-[color-mix(in_srgb,var(--critical)_16%,transparent)] text-[var(--critical)]",
        warning:
          "border-transparent bg-[color-mix(in_srgb,var(--warning)_18%,transparent)] text-[color-mix(in_srgb,var(--warning)_78%,var(--ink))]",
        outline: "border-[var(--line-strong)] bg-transparent text-[var(--ink-2)]",
      },
    },
    defaultVariants: { tone: "neutral" },
  },
);

export interface BadgeProps
  extends React.HTMLAttributes<HTMLSpanElement>,
    VariantProps<typeof badgeVariants> {}

export function Badge({ className, tone, ...props }: BadgeProps) {
  return <span className={cn(badgeVariants({ tone }), className)} {...props} />;
}

export { badgeVariants };
