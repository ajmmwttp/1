"use client";

import Link from "next/link";
import { AnimatePresence, motion } from "framer-motion";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { cn } from "@/lib/utils";
import { NAV_GROUPS, NAV_ITEMS, type NavItem } from "./nav-items";
import { FADE_TRANSITION, RAIL_TRANSITION } from "./motion-tokens";

interface NavListProps {
  /** Icon-only rail. */
  collapsed?: boolean;
  /** href of the current destination. */
  active: string;
  onNavigate: (href: string) => void;
  /**
   * layoutId for the sliding gold rail. Desktop and the mobile drawer render
   * two independent copies of the nav, so they must not share an id.
   */
  railId: string;
  className?: string;
}

export function NavList({
  collapsed = false,
  active,
  onNavigate,
  railId,
  className,
}: NavListProps) {
  return (
    <nav
      aria-label="メインナビゲーション"
      className={cn("flex flex-col gap-4", className)}
    >
      {NAV_GROUPS.map((group, gi) => (
        <div key={group} className="flex flex-col">
          {collapsed && gi > 0 && (
            <span aria-hidden className="mx-auto mb-2 h-px w-5 bg-[var(--line)]" />
          )}
          <AnimatePresence initial={false}>
            {!collapsed && (
              <motion.span
                key="group-label"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                transition={FADE_TRANSITION}
                className="mb-1.5 truncate whitespace-nowrap px-2.5 text-[10.5px] uppercase tracking-[0.09em] text-[var(--ink-4)]"
              >
                {group}
              </motion.span>
            )}
          </AnimatePresence>

          <ul className="flex flex-col gap-0.5">
            {NAV_ITEMS.filter((item) => item.group === group).map((item) => (
              <NavRow
                key={item.href}
                item={item}
                collapsed={collapsed}
                active={active === item.href}
                onNavigate={onNavigate}
                railId={railId}
              />
            ))}
          </ul>
        </div>
      ))}
    </nav>
  );
}

function NavRow({
  item,
  collapsed,
  active,
  onNavigate,
  railId,
}: {
  item: NavItem;
  collapsed: boolean;
  active: boolean;
  onNavigate: (href: string) => void;
  railId: string;
}) {
  const Icon = item.icon;

  const row = (
    <Link
      href={item.href}
      aria-current={active ? "page" : undefined}
      aria-label={collapsed ? item.label : undefined}
      onClick={(event) => {
        // Only "/" is mounted today; the rest move the rail without a 404.
        if (!item.ready) event.preventDefault();
        onNavigate(item.href);
      }}
      className={cn(
        "relative flex h-8 items-center gap-2.5 overflow-hidden rounded-[8px] px-2.5 text-[12.5px] transition-colors duration-150 ease-[cubic-bezier(.16,1,.3,1)]",
        // The drawer is a touch surface by definition; 32px rows are not.
        "pointer-coarse:h-10",
        collapsed && "justify-center",
        active
          ? "bg-[var(--elevated)] font-medium text-[var(--ink)]"
          : "text-[var(--ink-3)] hover:bg-[var(--elevated)] hover:text-[var(--ink)]",
      )}
    >
      <Icon className="size-4 shrink-0" strokeWidth={1.75} />
      <AnimatePresence initial={false}>
        {!collapsed && (
          <motion.span
            key="label"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={FADE_TRANSITION}
            className="truncate whitespace-nowrap"
          >
            {item.label}
          </motion.span>
        )}
      </AnimatePresence>
    </Link>
  );

  return (
    <li className="relative">
      {active && (
        <motion.span
          layoutId={railId}
          transition={RAIL_TRANSITION}
          aria-hidden
          className="absolute inset-y-1.5 left-0 z-10 w-[2px] rounded-full bg-[var(--accent)]"
        />
      )}
      {collapsed ? (
        <Tooltip>
          <TooltipTrigger asChild>{row}</TooltipTrigger>
          <TooltipContent side="right">{item.label}</TooltipContent>
        </Tooltip>
      ) : (
        row
      )}
    </li>
  );
}
