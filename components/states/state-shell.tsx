import * as React from "react";
import type { LucideIcon } from "lucide-react";
import { cn } from "@/lib/utils";

export type StateTone = "neutral" | "critical";

export interface StateShellProps {
  icon: LucideIcon;
  title: string;
  description: string;
  /** Actions row. Omit for a purely informational state. */
  children?: React.ReactNode;
  tone?: StateTone;
  className?: string;
}

/**
 * The frame every empty / error screen sits in: icon plate, title, one line
 * of body copy, optional actions. Tone only ever colours the plate and the
 * icon — the title stays in ink so meaning never rests on colour alone.
 */
export function StateShell({
  icon: Icon,
  title,
  description,
  children,
  tone = "neutral",
  className,
}: StateShellProps) {
  const critical = tone === "critical";

  return (
    <div
      className={cn(
        "flex flex-col items-center justify-center px-6 py-14 text-center",
        className,
      )}
    >
      <div
        className="flex size-11 items-center justify-center rounded-[12px] border border-[var(--line)] bg-[var(--elevated)]"
        style={
          critical
            ? {
                borderColor:
                  "color-mix(in oklab, var(--critical) 42%, var(--line-strong))",
              }
            : undefined
        }
      >
        <Icon
          aria-hidden
          strokeWidth={1.75}
          className={cn(
            "size-5",
            critical ? "text-[var(--critical)]" : "text-[var(--ink-3)]",
          )}
        />
      </div>

      <h2 className="mt-4 text-[12px] font-medium tracking-[-0.01em] text-[var(--ink)]">
        {title}
      </h2>

      <p className="mt-1.5 max-w-[38ch] text-[12px] leading-relaxed text-[var(--ink-3)]">
        {description}
      </p>

      {children ? (
        <div className="mt-5 flex flex-wrap items-center justify-center gap-2">
          {children}
        </div>
      ) : null}
    </div>
  );
}
