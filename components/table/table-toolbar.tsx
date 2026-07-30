"use client";

import * as React from "react";
import { ChevronDown, Search, X } from "lucide-react";
import type { Role, Verdict } from "@/lib/data/warehouse";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuCheckboxItem,
  DropdownMenuContent,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Input } from "@/components/ui/input";
import { ROLE_OPTIONS, VERDICT_OPTIONS } from "./columns";

interface TableToolbarProps {
  query: string;
  onQueryChange: (value: string) => void;
  verdicts: Verdict[];
  onToggleVerdict: (verdict: Verdict) => void;
  roles: Role[];
  onToggleRole: (role: Role) => void;
  activeCount: number;
  onClear: () => void;
}

interface FilterTriggerProps extends React.ComponentPropsWithoutRef<typeof Button> {
  label: string;
  selected: number;
  total: number;
}

/** Forwards ref + props so DropdownMenuTrigger asChild can drive it. */
const FilterTrigger = React.forwardRef<HTMLButtonElement, FilterTriggerProps>(
  ({ label, selected, total, ...props }, ref) => (
    <Button
      ref={ref}
      variant="outline"
      size="sm"
      className="gap-1.5 font-normal pointer-coarse:h-10 pointer-coarse:px-3"
      {...props}
    >
      {label}
      {selected < total && (
        <span className="tnum text-[11px] text-[var(--accent)]">
          {selected}/{total}
        </span>
      )}
      <ChevronDown className="text-[var(--ink-4)]" aria-hidden />
    </Button>
  ),
);
FilterTrigger.displayName = "FilterTrigger";

export function TableToolbar({
  query,
  onQueryChange,
  verdicts,
  onToggleVerdict,
  roles,
  onToggleRole,
  activeCount,
  onClear,
}: TableToolbarProps) {
  return (
    <div className="flex flex-wrap items-center gap-2">
      {/* On a phone the 196px field left a ragged 40px gutter beside it and
          pushed the two filters onto their own row anyway; letting it take the
          full row is both tidier and a bigger tap target. */}
      <div className="relative w-full sm:w-auto">
        <Search
          className="pointer-events-none absolute top-1/2 left-2.5 size-3.5 -translate-y-1/2 text-[var(--ink-4)]"
          aria-hidden
        />
        <Input
          value={query}
          onChange={(e) => onQueryChange(e.target.value)}
          placeholder="担当者を検索"
          aria-label="担当者を検索"
          className="w-full pl-[30px] pointer-coarse:h-10 sm:w-[196px]"
        />
      </div>

      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <FilterTrigger label="判定" selected={verdicts.length} total={VERDICT_OPTIONS.length} />
        </DropdownMenuTrigger>
        <DropdownMenuContent align="start">
          <DropdownMenuLabel>判定</DropdownMenuLabel>
          <DropdownMenuSeparator />
          {VERDICT_OPTIONS.map((v) => (
            <DropdownMenuCheckboxItem
              key={v}
              checked={verdicts.includes(v)}
              onCheckedChange={() => onToggleVerdict(v)}
              onSelect={(e) => e.preventDefault()}
            >
              {v}
            </DropdownMenuCheckboxItem>
          ))}
        </DropdownMenuContent>
      </DropdownMenu>

      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <FilterTrigger label="雇用区分" selected={roles.length} total={ROLE_OPTIONS.length} />
        </DropdownMenuTrigger>
        <DropdownMenuContent align="start">
          <DropdownMenuLabel>雇用区分</DropdownMenuLabel>
          <DropdownMenuSeparator />
          {ROLE_OPTIONS.map((r) => (
            <DropdownMenuCheckboxItem
              key={r.id}
              checked={roles.includes(r.id)}
              onCheckedChange={() => onToggleRole(r.id)}
              onSelect={(e) => e.preventDefault()}
            >
              {r.label}
            </DropdownMenuCheckboxItem>
          ))}
        </DropdownMenuContent>
      </DropdownMenu>

      {activeCount > 0 && (
        <div className="flex items-center gap-1.5">
          <Badge tone="accent" aria-live="polite">
            絞り込み <span className="tnum">{activeCount}</span>
          </Badge>
          <Button
            variant="ghost"
            size="sm"
            onClick={onClear}
            className="gap-1 font-normal pointer-coarse:h-10 pointer-coarse:px-3"
          >
            <X />
            クリア
          </Button>
        </div>
      )}
    </div>
  );
}
