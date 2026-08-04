"use client";

import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetTitle,
  VisuallyHidden,
} from "@/components/ui/sheet";
import { LedgerMark, Wordmark } from "./logo-mark";
import { NavList } from "./nav-list";
import { SetupStat } from "./setup-stat";
import { UserMenu } from "./user-menu";

export function MobileNav({
  open,
  onOpenChange,
  active,
  onNavigate,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  active: string;
  onNavigate: (href: string) => void;
}) {
  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent side="left" className="lg:hidden">
        <VisuallyHidden>
          <SheetTitle>ナビゲーション</SheetTitle>
          <SheetDescription>
            オペレーションと管理の各画面へ移動します。
          </SheetDescription>
        </VisuallyHidden>

        <div className="flex h-14 shrink-0 items-center gap-2 border-b border-[var(--line)] px-3">
          <LedgerMark />
          <Wordmark />
        </div>

        <div className="flex-1 overflow-y-auto px-2 py-3">
          <NavList
            active={active}
            railId="shell-rail-mobile"
            onNavigate={(href) => {
              onNavigate(href);
              onOpenChange(false);
            }}
          />
        </div>

        <div className="shrink-0 border-t border-[var(--line)]">
          <SetupStat />
        </div>
        <div className="shrink-0 border-t border-[var(--line)] p-2">
          <UserMenu variant="full" />
        </div>
      </SheetContent>
    </Sheet>
  );
}
