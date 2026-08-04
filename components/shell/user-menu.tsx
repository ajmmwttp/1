"use client";

import { ChevronsUpDown, LogOut, Settings, SlidersHorizontal } from "lucide-react";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuGroup,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { cn } from "@/lib/utils";

export const USER = {
  name: "水野 健一",
  role: "倉庫課 / 管理者",
  initials: "MK",
};

interface UserMenuProps {
  /** "full" = the sidebar row; "avatar" = collapsed rail and the header. */
  variant?: "full" | "avatar";
  className?: string;
}

export function UserMenu({ variant = "full", className }: UserMenuProps) {
  const isFull = variant === "full";

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <button
          type="button"
          aria-label={`${USER.name} のメニュー`}
          className={cn(
            "flex items-center rounded-[8px] transition-colors duration-150 outline-none",
            "hover:bg-[var(--elevated)] data-[state=open]:bg-[var(--elevated)]",
            isFull
              ? "w-full gap-2 overflow-hidden p-1.5 text-left"
              // The avatar variant sits at 36px, just under the touch floor.
              : "justify-center p-1 pointer-coarse:size-10 pointer-coarse:p-1.5",
            className,
          )}
        >
          <Avatar className="size-7">
            <AvatarFallback className="tnum tracking-[0.02em]">
              {USER.initials}
            </AvatarFallback>
          </Avatar>
          {isFull && (
            <>
              <span className="flex min-w-0 flex-1 flex-col whitespace-nowrap">
                <span className="truncate text-[12px] font-medium leading-[1.35] text-[var(--ink)]">
                  {USER.name}
                </span>
                <span className="truncate text-[12px] leading-[1.35] text-[var(--ink-3)]">
                  {USER.role}
                </span>
              </span>
              <ChevronsUpDown className="size-3.5 shrink-0 text-[var(--ink-4)]" />
            </>
          )}
        </button>
      </DropdownMenuTrigger>

      <DropdownMenuContent
        side={isFull ? "top" : "bottom"}
        align={isFull ? "start" : "end"}
        className="w-56"
      >
        <DropdownMenuLabel className="flex flex-col gap-0.5 normal-case tracking-normal">
          <span className="text-[12px] font-medium text-[var(--ink)]">
            {USER.name}
          </span>
          <span className="text-[12px] text-[var(--ink-3)]">{USER.role}</span>
        </DropdownMenuLabel>
        <DropdownMenuSeparator />
        <DropdownMenuGroup>
          <DropdownMenuItem>
            <Settings />
            アカウント設定
          </DropdownMenuItem>
          <DropdownMenuItem>
            <SlidersHorizontal />
            表示設定
          </DropdownMenuItem>
        </DropdownMenuGroup>
        <DropdownMenuSeparator />
        <DropdownMenuItem>
          <LogOut />
          ログアウト
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
