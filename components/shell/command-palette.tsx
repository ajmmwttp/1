"use client";

import * as React from "react";
// The vendored SheetContent is an edge drawer; a command palette needs a
// centred surface, so the same Dialog primitive is composed directly here.
import * as DialogPrimitive from "@radix-ui/react-dialog";
import { CornerDownLeft, Search, type LucideIcon } from "lucide-react";
import { Input } from "@/components/ui/input";
import {
  SheetDescription,
  SheetTitle,
  VisuallyHidden,
} from "@/components/ui/sheet";
import { dec } from "@/lib/format";
import { workers, type Role } from "@/lib/data/warehouse";
import { cn } from "@/lib/utils";
import { NAV_ITEMS } from "./nav-items";

type Row =
  | {
      kind: "nav";
      key: string;
      label: string;
      icon: LucideIcon;
      href: string;
      meta: string;
    }
  | {
      kind: "worker";
      key: string;
      label: string;
      meta: string;
      efficiency: number | null;
    };

const GROUP_LABEL: Record<Row["kind"], string> = {
  nav: "画面",
  worker: "担当者",
};

const roleLabel = (role: Role) => (role === "staff" ? "社員" : "パート");

export function CommandPalette({
  open,
  onOpenChange,
  onNavigate,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onNavigate: (href: string) => void;
}) {
  const [query, setQuery] = React.useState("");
  const [index, setIndex] = React.useState(0);
  const listRef = React.useRef<HTMLDivElement>(null);

  const rows = React.useMemo<Row[]>(() => {
    const q = query.trim().toLowerCase();

    const navRows: Row[] = NAV_ITEMS.filter(
      (item) =>
        !q ||
        item.label.toLowerCase().includes(q) ||
        item.href.includes(q) ||
        item.keywords.some((k) => k.includes(q)),
    ).map((item) => ({
      kind: "nav",
      key: `nav:${item.href}`,
      label: item.label,
      icon: item.icon,
      href: item.href,
      meta: item.group,
    }));

    const workerRows: Row[] = workers
      .filter(
        (worker) =>
          !q ||
          worker.name.toLowerCase().includes(q) ||
          roleLabel(worker.role).includes(q),
      )
      .map((worker) => {
        const stats = worker.pick ?? worker.pack;
        const process = worker.pick ? "ピッキング" : worker.pack ? "梱包" : "—";
        return {
          kind: "worker" as const,
          key: `worker:${worker.name}`,
          label: worker.name,
          meta: `${roleLabel(worker.role)} · ${process}`,
          efficiency: stats ? stats.efficiency : null,
        };
      });

    return [...navRows, ...workerRows];
  }, [query]);

  // A fresh palette every time, and the highlight never dangles past the list.
  React.useEffect(() => {
    if (!open) return;
    setQuery("");
    setIndex(0);
  }, [open]);

  React.useEffect(() => {
    setIndex(0);
  }, [query]);

  React.useEffect(() => {
    listRef.current
      ?.querySelector<HTMLElement>(`[data-idx="${index}"]`)
      ?.scrollIntoView({ block: "nearest" });
  }, [index, rows]);

  const select = React.useCallback(
    (row: Row | undefined) => {
      if (!row) return;
      if (row.kind === "nav") onNavigate(row.href);
      onOpenChange(false);
    },
    [onNavigate, onOpenChange],
  );

  function handleKeyDown(event: React.KeyboardEvent<HTMLDivElement>) {
    // Never steal keys while an IME candidate window is open.
    if (event.nativeEvent.isComposing) return;
    if (rows.length === 0) return;

    if (event.key === "ArrowDown") {
      event.preventDefault();
      setIndex((i) => (i + 1) % rows.length);
    } else if (event.key === "ArrowUp") {
      event.preventDefault();
      setIndex((i) => (i - 1 + rows.length) % rows.length);
    } else if (event.key === "Home") {
      event.preventDefault();
      setIndex(0);
    } else if (event.key === "End") {
      event.preventDefault();
      setIndex(rows.length - 1);
    } else if (event.key === "Enter") {
      event.preventDefault();
      select(rows[index]);
    }
  }

  return (
    <DialogPrimitive.Root open={open} onOpenChange={onOpenChange}>
      <DialogPrimitive.Portal>
        <DialogPrimitive.Overlay
          className={cn(
            "fixed inset-0 z-50 bg-black/55 backdrop-blur-[2px]",
            "data-[state=open]:animate-in data-[state=closed]:animate-out data-[state=closed]:fade-out-0 data-[state=open]:fade-in-0",
          )}
        />
        <DialogPrimitive.Content
          onKeyDown={handleKeyDown}
          className={cn(
            "fixed left-1/2 top-[14vh] z-50 w-[min(560px,calc(100vw-2rem))] -translate-x-1/2",
            "overflow-hidden rounded-[12px] border border-[var(--line)] bg-[var(--card)] shadow-[var(--shadow-pop)] outline-none",
            "data-[state=open]:animate-in data-[state=closed]:animate-out data-[state=closed]:fade-out-0 data-[state=open]:fade-in-0 data-[state=open]:zoom-in-95",
          )}
        >
          <VisuallyHidden>
            <SheetTitle>コマンドパレット</SheetTitle>
            <SheetDescription>
              担当者と画面を検索して移動します。
            </SheetDescription>
          </VisuallyHidden>

          <div className="flex h-12 items-center gap-2.5 border-b border-[var(--line)] px-3.5">
            <Search className="size-4 shrink-0 text-[var(--ink-4)]" />
            <Input
              autoFocus
              aria-label="担当者・工程を検索"
              placeholder="担当者・工程を検索"
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              className="h-12 rounded-none border-0 bg-transparent px-0 text-[13px] hover:border-0 focus:bg-transparent"
            />
            <kbd className="hidden shrink-0 rounded-[4px] border border-[var(--line)] bg-[var(--elevated)] px-1.5 py-0.5 text-[10px] text-[var(--ink-4)] sm:inline-block">
              esc
            </kbd>
          </div>

          <div ref={listRef} className="max-h-[46vh] overflow-y-auto p-1.5">
            {rows.length === 0 && (
              <p className="px-2.5 py-6 text-center text-[12.5px] text-[var(--ink-3)]">
                該当する項目がありません
              </p>
            )}

            {rows.map((row, i) => {
              const showHeader = i === 0 || rows[i - 1].kind !== row.kind;
              const activeRow = i === index;
              return (
                <React.Fragment key={row.key}>
                  {showHeader && (
                    <div className="px-2.5 pb-1 pt-2 text-[10.5px] uppercase tracking-[0.09em] text-[var(--ink-4)]">
                      {GROUP_LABEL[row.kind]}
                    </div>
                  )}
                  <button
                    type="button"
                    data-idx={i}
                    onMouseMove={() => setIndex(i)}
                    onClick={() => select(row)}
                    className={cn(
                      "relative flex h-9 w-full items-center gap-2.5 rounded-[8px] px-2.5 text-left text-[12.5px] outline-none transition-colors duration-100",
                      activeRow
                        ? "bg-[var(--elevated)] text-[var(--ink)]"
                        : "text-[var(--ink-2)]",
                    )}
                  >
                    {activeRow && (
                      <span
                        aria-hidden
                        className="absolute inset-y-1.5 left-0 w-[2px] rounded-full bg-[var(--accent)]"
                      />
                    )}
                    {row.kind === "nav" ? (
                      <row.icon
                        className="size-4 shrink-0 text-[var(--ink-3)]"
                        strokeWidth={1.75}
                      />
                    ) : (
                      <span className="tnum flex size-4 shrink-0 items-center justify-center rounded-[4px] bg-[var(--sunken)] text-[9px] text-[var(--ink-3)]">
                        {row.label.slice(0, 1)}
                      </span>
                    )}
                    <span className="truncate">{row.label}</span>
                    <span className="ml-auto flex shrink-0 items-center gap-2 text-[10.5px] text-[var(--ink-4)]">
                      <span className="hidden sm:inline">{row.meta}</span>
                      {row.kind === "worker" && row.efficiency !== null && (
                        <span>
                          効率{" "}
                          <span className="tnum text-[var(--ink-3)]">
                            {dec(row.efficiency, 1)}%
                          </span>
                        </span>
                      )}
                      {activeRow && (
                        <CornerDownLeft className="size-3 text-[var(--ink-4)]" />
                      )}
                    </span>
                  </button>
                </React.Fragment>
              );
            })}
          </div>

          <div className="flex items-center justify-between border-t border-[var(--line)] bg-[var(--sunken)] px-3.5 py-2 text-[10.5px] text-[var(--ink-4)]">
            <span className="flex items-center gap-3">
              <span>
                <kbd className="text-[var(--ink-3)]">↑↓</kbd> 移動
              </span>
              <span>
                <kbd className="text-[var(--ink-3)]">⏎</kbd> 決定
              </span>
              <span>
                <kbd className="text-[var(--ink-3)]">esc</kbd> 閉じる
              </span>
            </span>
            <span>
              <span className="tnum">{rows.length}</span> 件
            </span>
          </div>
        </DialogPrimitive.Content>
      </DialogPrimitive.Portal>
    </DialogPrimitive.Root>
  );
}
