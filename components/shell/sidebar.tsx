"use client";

import { AnimatePresence, motion } from "framer-motion";
import { PanelLeftClose, PanelLeftOpen } from "lucide-react";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { cn } from "@/lib/utils";
import { LedgerMark, Wordmark } from "./logo-mark";
import { NavList } from "./nav-list";
import { SetupStat } from "./setup-stat";
import { UserMenu } from "./user-menu";
import {
  FADE_TRANSITION,
  NO_TRANSITION,
  SHELL_TRANSITION,
} from "./motion-tokens";

export const SIDEBAR_WIDTH = 240;
export const SIDEBAR_WIDTH_COLLAPSED = 56;

interface SidebarProps {
  collapsed: boolean;
  onToggle: () => void;
  active: string;
  onNavigate: (href: string) => void;
  /** False on the first commit so a restored collapse state does not animate. */
  animated: boolean;
}

export function Sidebar({
  collapsed,
  onToggle,
  active,
  onNavigate,
  animated,
}: SidebarProps) {
  const toggleLabel = collapsed
    ? "サイドバーを展開"
    : "サイドバーを折りたたむ";

  return (
    <motion.aside
      initial={false}
      animate={{ width: collapsed ? SIDEBAR_WIDTH_COLLAPSED : SIDEBAR_WIDTH }}
      transition={animated ? SHELL_TRANSITION : NO_TRANSITION}
      className={cn(
        "sticky top-0 z-40 hidden h-dvh shrink-0 flex-col border-r border-[var(--line)] lg:flex",
        "bg-[color-mix(in_srgb,var(--page)_72%,transparent)] backdrop-blur-xl",
      )}
    >
      <div className="flex h-full flex-col overflow-hidden">
        <div
          className={cn(
            "flex h-14 shrink-0 items-center border-b border-[var(--line)]",
            collapsed ? "justify-center px-0" : "gap-2 px-3",
          )}
        >
          <LedgerMark />
          <AnimatePresence initial={false}>
            {!collapsed && (
              <motion.span
                key="wordmark"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                transition={FADE_TRANSITION}
                className="overflow-hidden"
              >
                <Wordmark />
              </motion.span>
            )}
          </AnimatePresence>
        </div>

        <div className="flex-1 overflow-y-auto overflow-x-hidden px-2 py-3">
          <NavList
            collapsed={collapsed}
            active={active}
            onNavigate={onNavigate}
            railId="shell-rail-desktop"
          />
        </div>

        <AnimatePresence initial={false}>
          {!collapsed && (
            <motion.div
              key="setup-stat"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              transition={FADE_TRANSITION}
              className="shrink-0 overflow-hidden border-t border-[var(--line)]"
            >
              <SetupStat />
            </motion.div>
          )}
        </AnimatePresence>

        <div className="shrink-0 border-t border-[var(--line)] p-2">
          <UserMenu
            variant={collapsed ? "avatar" : "full"}
            className={collapsed ? "w-full" : undefined}
          />
        </div>
      </div>

      <Tooltip>
        <TooltipTrigger asChild>
          <button
            type="button"
            onClick={onToggle}
            aria-label={toggleLabel}
            aria-expanded={!collapsed}
            className={cn(
              "absolute -right-3 top-[43px] z-10 flex size-6 items-center justify-center rounded-full",
              "border border-[var(--line)] bg-[var(--card)] text-[var(--ink-3)] shadow-[var(--shadow-flat)]",
              "transition-colors duration-150 hover:border-[var(--line-strong)] hover:text-[var(--ink)]",
            )}
          >
            {collapsed ? (
              <PanelLeftOpen className="size-3.5" strokeWidth={1.75} />
            ) : (
              <PanelLeftClose className="size-3.5" strokeWidth={1.75} />
            )}
          </button>
        </TooltipTrigger>
        <TooltipContent side="right">{toggleLabel}</TooltipContent>
      </Tooltip>
    </motion.aside>
  );
}
