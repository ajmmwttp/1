import * as React from "react";
import { cn } from "@/lib/utils";

export const Input = React.forwardRef<
  HTMLInputElement,
  React.InputHTMLAttributes<HTMLInputElement>
>(({ className, type = "text", ...props }, ref) => (
  <input
    ref={ref}
    type={type}
    className={cn(
      "h-8 w-full rounded-[8px] border border-[var(--line)] bg-[var(--elevated)] px-2.5 text-[12.5px] text-[var(--ink)] transition-colors",
      "placeholder:text-[var(--ink-4)] hover:border-[var(--line-strong)]",
      "focus:border-[var(--accent-line)] focus:bg-[var(--card)]",
      "disabled:cursor-not-allowed disabled:opacity-45",
      className,
    )}
    {...props}
  />
));
Input.displayName = "Input";
