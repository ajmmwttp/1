"use client";

import * as React from "react";
import { Slot } from "@radix-ui/react-slot";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

const buttonVariants = cva(
  "inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-[8px] text-[12px] font-medium transition-[background-color,border-color,color,box-shadow,transform] duration-150 ease-[cubic-bezier(.16,1,.3,1)] disabled:pointer-events-none disabled:opacity-45 active:translate-y-px [&_svg]:pointer-events-none [&_svg]:shrink-0",
  {
    variants: {
      variant: {
        default:
          "bg-[var(--accent)] text-[var(--accent-ink)] shadow-[var(--shadow-flat)] hover:bg-[var(--accent-bright)]",
        outline:
          "border border-[var(--line-strong)] bg-[var(--card)] text-[var(--ink)] hover:bg-[var(--elevated)] hover:border-[var(--line-strong)]",
        ghost:
          "text-[var(--ink-2)] hover:bg-[var(--elevated)] hover:text-[var(--ink)]",
        subtle:
          "bg-[var(--elevated)] text-[var(--ink)] hover:bg-[var(--sunken)]",
        danger:
          "bg-[var(--critical)] text-white hover:brightness-110",
        link: "text-[var(--accent)] underline-offset-4 hover:underline",
      },
      size: {
        sm: "h-7 px-2.5 [&_svg]:size-3.5",
        default: "h-8 px-3 [&_svg]:size-4",
        lg: "h-10 px-4 text-[12px] [&_svg]:size-4",
        icon: "size-8 [&_svg]:size-4",
        "icon-sm": "size-7 [&_svg]:size-3.5",
      },
    },
    defaultVariants: { variant: "default", size: "default" },
  },
);

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {
  asChild?: boolean;
}

export const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant, size, asChild = false, ...props }, ref) => {
    const Comp = asChild ? Slot : "button";
    return (
      <Comp
        ref={ref}
        className={cn(buttonVariants({ variant, size }), className)}
        {...props}
      />
    );
  },
);
Button.displayName = "Button";

export { buttonVariants };
