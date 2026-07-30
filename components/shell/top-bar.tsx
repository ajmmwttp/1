"use client";

import { Calendar, ChevronRight, Menu, Search } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { cn } from "@/lib/utils";
import { NAV_ITEMS } from "./nav-items";
import { Notifications } from "./notifications";
import { ThemeToggle } from "./theme-toggle";
import { UserMenu } from "./user-menu";

interface TopBarProps {
  active: string;
  onOpenMobileNav: () => void;
  onOpenPalette: () => void;
}

export function TopBar({
  active,
  onOpenMobileNav,
  onOpenPalette,
}: TopBarProps) {
  const current = NAV_ITEMS.find((item) => item.href === active) ?? NAV_ITEMS[0];

  return (
    <header
      className={cn(
        "sticky top-0 z-30 flex h-14 shrink-0 items-center gap-1.5 border-b border-[var(--line)] px-3 sm:px-4 lg:px-6",
        "bg-[color-mix(in_srgb,var(--page)_72%,transparent)] backdrop-blur-xl",
      )}
    >
      <Button
        variant="ghost"
        size="icon-sm"
        onClick={onOpenMobileNav}
        aria-label="メニューを開く"
        // 28px is a cursor target; every icon button in the bar grows to 40
        // on a coarse pointer. The 56px bar already has the room.
        className="lg:hidden pointer-coarse:size-10"
      >
        <Menu />
      </Button>

      <nav
        aria-label="パンくずリスト"
        className="flex min-w-0 items-center gap-1.5"
      >
        <span className="hidden truncate text-[12px] text-[var(--ink-3)] sm:block">
          {current.group}
        </span>
        <ChevronRight
          aria-hidden
          className="hidden size-3.5 shrink-0 text-[var(--ink-4)] sm:block"
        />
        <span
          aria-current="page"
          className="truncate text-[12px] font-medium text-[var(--ink)]"
        >
          {current.label}
        </span>
      </nav>

      <span aria-hidden className="mx-1.5 hidden h-4 w-px bg-[var(--line)] md:block" />

      <span className="hidden h-7 shrink-0 items-center gap-1.5 rounded-[6px] border border-[var(--line)] bg-[var(--elevated)] px-2 text-[12px] text-[var(--ink-2)] md:inline-flex">
        <Calendar className="size-3.5 shrink-0 text-[var(--ink-3)]" strokeWidth={1.75} />
        <span className="tnum">2026</span>年<span className="tnum">4</span>月
      </span>

      <div className="ml-auto flex shrink-0 items-center gap-1">
        <button
          type="button"
          onClick={onOpenPalette}
          className={cn(
            "hidden h-8 w-[240px] items-center gap-2 rounded-[8px] border border-[var(--line)] bg-[var(--elevated)] px-2.5",
            "pointer-coarse:h-10",
            "text-[12px] text-[var(--ink-4)] transition-colors duration-150 md:flex",
            "hover:border-[var(--line-strong)] hover:text-[var(--ink-3)]",
          )}
        >
          <Search className="size-3.5 shrink-0" strokeWidth={1.75} />
          <span className="truncate">担当者・工程を検索</span>
          <kbd className="tnum ml-auto shrink-0 rounded-[4px] border border-[var(--line)] bg-[var(--card)] px-1 py-px text-[12px] leading-[1.6] text-[var(--ink-4)]">
            ⌘K
          </kbd>
        </button>

        <Tooltip>
          <TooltipTrigger asChild>
            <Button
              variant="ghost"
              size="icon-sm"
              onClick={onOpenPalette}
              aria-label="担当者・工程を検索"
              className="md:hidden pointer-coarse:size-10"
            >
              <Search />
            </Button>
          </TooltipTrigger>
          <TooltipContent>検索</TooltipContent>
        </Tooltip>

        <Notifications />
        <ThemeToggle />
        <UserMenu variant="avatar" />
      </div>
    </header>
  );
}
