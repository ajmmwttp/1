"use client";

import * as React from "react";
import { ChevronDown, ChevronUp, Info, SearchX } from "lucide-react";
import type { Role, Verdict } from "@/lib/data/warehouse";
import { dec, int } from "@/lib/format";
import { cn } from "@/lib/utils";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import {
  buildRows,
  COLUMNS,
  ROLE_OPTIONS,
  VERDICT_OPTIONS,
  roleLabel,
  type Column,
  type PickRow,
  type SortState,
  type SortableId,
} from "./columns";
import { TableToolbar } from "./table-toolbar";
import { useSort } from "./use-sort";
import { VerdictPill } from "./verdict-pill";

const ROWS = buildRows();
const TOTAL = ROWS.length;
/** Bar scale is pinned to the whole roster so filtering never rescales it. */
const MAX_ITEMS_PER_COMPANY = Math.max(...ROWS.map((r) => r.pick.itemsPerCompany));

const CELL = "h-10 border-b border-[var(--line)] px-2 align-middle whitespace-nowrap";
const HEAD =
  "sticky top-0 z-10 h-[34px] whitespace-nowrap bg-[var(--card)] px-2 text-[11px] font-medium";

/* ── header ───────────────────────────────────────────────── */

function SortChevron({ active, dir, hint }: { active: boolean; dir: "asc" | "desc"; hint: "asc" | "desc" }) {
  const Icon = (active ? dir : hint) === "asc" ? ChevronUp : ChevronDown;
  return (
    <Icon
      aria-hidden
      className={cn(
        "size-3 shrink-0 transition-opacity duration-150",
        active
          ? "text-[var(--ink-2)] opacity-100"
          : "text-[var(--ink-3)] opacity-0 group-hover/head:opacity-40 group-focus-within/head:opacity-40",
      )}
    />
  );
}

function HeaderCell({
  column,
  sort,
  onToggle,
}: {
  column: Column;
  sort: SortState;
  onToggle: (id: SortableId) => void;
}) {
  const sortId = column.sortId;
  const active = sortId !== undefined && sortId === sort.id;
  const right = column.align === "right";

  const label = sortId ? (
    <button
      type="button"
      onClick={() => onToggle(sortId)}
      aria-label={`${column.label}で並べ替え`}
      className={cn(
        "inline-flex items-center gap-1 rounded-[4px] transition-colors",
        active ? "text-[var(--ink)]" : "text-[var(--ink-3)] hover:text-[var(--ink-2)]",
      )}
    >
      {right && <SortChevron active={active} dir={sort.dir} hint={column.firstDir ?? "desc"} />}
      <span>{column.label}</span>
      {!right && <SortChevron active={active} dir={sort.dir} hint={column.firstDir ?? "desc"} />}
    </button>
  ) : (
    <span className="text-[var(--ink-3)]">{column.label}</span>
  );

  return (
    <th
      scope="col"
      aria-sort={active ? (sort.dir === "asc" ? "ascending" : "descending") : "none"}
      className={cn(
        HEAD,
        "group/head",
        column.width,
        right ? "text-right" : "text-left",
        "after:absolute after:inset-x-0 after:bottom-0 after:h-px after:bg-[var(--line)] after:content-['']",
      )}
    >
      <span className={cn("inline-flex items-center gap-1", right && "justify-end")}>
        {label}
        {column.hint && (
          <Tooltip>
            <TooltipTrigger asChild>
              <button
                type="button"
                aria-label={`${column.label}とは`}
                className="rounded-[4px] text-[var(--ink-4)] transition-colors hover:text-[var(--ink-2)]"
              >
                <Info className="size-3" aria-hidden />
              </button>
            </TooltipTrigger>
            <TooltipContent side="top" className="max-w-[220px] leading-[1.6]">
              {column.hint}
            </TooltipContent>
          </Tooltip>
        )}
      </span>
    </th>
  );
}

/* ── cells ────────────────────────────────────────────────── */

function Cell({ row, column }: { row: PickRow; column: Column }) {
  const p = row.pick;
  const right = column.align === "right";
  const base = cn(CELL, right ? "text-right" : "text-left");

  switch (column.id) {
    case "rank":
      return (
        <td className={cn(base, "relative pr-1 pl-3")}>
          <span
            aria-hidden
            className="pointer-events-none absolute inset-y-0 left-0 w-[2px] bg-[var(--accent)] opacity-0 transition-opacity duration-150 group-hover:opacity-100 group-focus-visible:opacity-100 group-aria-selected:opacity-100"
          />
          <span className="tnum text-[var(--ink-4)]">{row.rank}</span>
        </td>
      );

    case "name":
      return (
        <td className={base}>
          <span className="flex items-center gap-1.5">
            <span className="min-w-0 truncate text-[var(--ink)]">{row.name}</span>
            <Badge tone="outline" className="shrink-0 px-1 py-[2px] text-[10px] text-[var(--ink-3)]">
              {roleLabel(row.role)}
            </Badge>
          </span>
        </td>
      );

    case "items":
      return <td className={cn(base, "tnum text-[var(--ink-2)]")}>{int(p.items)}</td>;

    case "companies":
      return <td className={cn(base, "tnum text-[var(--ink-2)]")}>{int(p.companies)}</td>;

    case "itemsPerCompany": {
      const ratio = Math.round(
        Math.max(p.itemsPerCompany / MAX_ITEMS_PER_COMPANY, 0.04) * 1000,
      ) / 1000;
      return (
        <td className={cn(base, "relative")}>
          <span
            aria-hidden
            className="pointer-events-none absolute inset-y-[9px] right-2 rounded-[3px] bg-[var(--accent-wash)]"
            style={{ width: `calc(${ratio} * (100% - 16px))` }}
          />
          <span className="tnum relative text-[var(--ink-2)]">{dec(p.itemsPerCompany, 2)}</span>
        </td>
      );
    }

    case "rawSecPerItem":
      return <td className={cn(base, "tnum text-[var(--ink-3)]")}>{dec(p.rawSecPerItem, 1)}</td>;

    case "pureSecPerItem":
      return <td className={cn(base, "tnum text-[var(--ink)]")}>{dec(p.pureSecPerItem, 1)}</td>;

    case "shrunk":
      return (
        <td className={cn(base, "tnum font-medium text-[var(--ink)]")}>{dec(p.shrunk, 1)}%</td>
      );

    case "verdict":
      return (
        <td className={base}>
          <VerdictPill verdict={row.verdict} />
        </td>
      );

    default:
      return null;
  }
}

/* ── empty state (in-table) ───────────────────────────────── */

function EmptyRow({ onClear }: { onClear: () => void }) {
  return (
    <tr>
      <td colSpan={COLUMNS.length} className="border-b border-[var(--line)] px-5 py-12">
        <div className="flex flex-col items-center gap-3 text-center">
          <span className="flex size-10 items-center justify-center rounded-[8px] bg-[var(--elevated)]">
            <SearchX className="size-4 text-[var(--ink-3)]" aria-hidden />
          </span>
          <span className="flex flex-col gap-1">
            <span className="text-[12.5px] font-medium text-[var(--ink)]">
              該当する担当者がいません
            </span>
            <span className="text-[11.5px] text-[var(--ink-3)]">
              検索語や絞り込みを変えてください。
            </span>
          </span>
          <Button variant="outline" size="sm" onClick={onClear}>
            クリア
          </Button>
        </div>
      </td>
    </tr>
  );
}

/* ── table ────────────────────────────────────────────────── */

export function WorkerTable() {
  const [query, setQuery] = React.useState("");
  const [verdicts, setVerdicts] = React.useState<Verdict[]>(VERDICT_OPTIONS);
  const [roles, setRoles] = React.useState<Role[]>(ROLE_OPTIONS.map((r) => r.id));
  const [selected, setSelected] = React.useState<string | null>(null);

  const filtered = React.useMemo(() => {
    const q = query.trim().toLowerCase();
    return ROWS.filter(
      (r) =>
        (q === "" || r.name.toLowerCase().includes(q)) &&
        verdicts.includes(r.verdict) &&
        roles.includes(r.role),
    );
  }, [query, verdicts, roles]);

  const { sort, sorted, toggle } = useSort(filtered);

  const activeCount =
    (query.trim() === "" ? 0 : 1) +
    (verdicts.length === VERDICT_OPTIONS.length ? 0 : 1) +
    (roles.length === ROLE_OPTIONS.length ? 0 : 1);

  const clear = React.useCallback(() => {
    setQuery("");
    setVerdicts(VERDICT_OPTIONS);
    setRoles(ROLE_OPTIONS.map((r) => r.id));
  }, []);

  const toggleVerdict = React.useCallback((v: Verdict) => {
    setVerdicts((prev) =>
      prev.includes(v) ? prev.filter((x) => x !== v) : VERDICT_OPTIONS.filter((x) => x === v || prev.includes(x)),
    );
  }, []);

  const toggleRole = React.useCallback((r: Role) => {
    setRoles((prev) =>
      prev.includes(r)
        ? prev.filter((x) => x !== r)
        : ROLE_OPTIONS.map((o) => o.id).filter((x) => x === r || prev.includes(x)),
    );
  }, []);

  return (
    <TooltipProvider delayDuration={120}>
      <Card>
        <CardHeader className="flex-col items-stretch gap-0">
          <div>
            <CardTitle>担当者ランキング（ピッキング）</CardTitle>
            <CardDescription>
              縮小後効率で順位づけ。記録日数が少ない人のブレを平均側へ寄せています。
            </CardDescription>
          </div>
          <div className="mt-4">
            <TableToolbar
              query={query}
              onQueryChange={setQuery}
              verdicts={verdicts}
              onToggleVerdict={toggleVerdict}
              roles={roles}
              onToggleRole={toggleRole}
              activeCount={activeCount}
              onClear={clear}
            />
          </div>
        </CardHeader>

        <CardContent className="px-0 pb-0">
          <div className="max-h-[560px] overflow-auto">
            <table className="w-full min-w-[880px] border-separate border-spacing-0 text-[12.5px]">
              <caption className="sr-only">
                ピッキング担当者26名の件数・企業数・件/社・素の秒/件・純速度・効率・判定。既定は効率の降順。
              </caption>
              <thead>
                <tr>
                  {COLUMNS.map((c) => (
                    <HeaderCell key={c.id} column={c} sort={sort} onToggle={toggle} />
                  ))}
                </tr>
              </thead>
              <tbody>
                {sorted.length === 0 && <EmptyRow onClear={clear} />}
                {sorted.map((row) => (
                  <tr
                    key={row.name}
                    tabIndex={0}
                    aria-selected={selected === row.name}
                    aria-label={`${row.rank}位 ${row.name}、${roleLabel(row.role)}、件数${int(
                      row.pick.items,
                    )}件、企業数${int(row.pick.companies)}社、効率${dec(row.pick.shrunk, 1)}%、判定${
                      row.verdict
                    }`}
                    onClick={() => setSelected((s) => (s === row.name ? null : row.name))}
                    onKeyDown={(e) => {
                      if (e.key === "Enter") {
                        e.preventDefault();
                        setSelected((s) => (s === row.name ? null : row.name));
                      } else if (e.key === "Escape") {
                        setSelected(null);
                      }
                    }}
                    className="group cursor-default transition-colors duration-150 hover:bg-[var(--elevated)] focus-visible:bg-[var(--elevated)] aria-selected:bg-[var(--elevated)]"
                  >
                    {COLUMNS.map((c) => (
                      <Cell key={c.id} row={row} column={c} />
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </CardContent>

        <CardFooter className="justify-between gap-4">
          <span>
            全<span className="tnum">{TOTAL}</span>名中 <span className="tnum">{sorted.length}</span>
            名を表示
          </span>
          <span className="text-[var(--ink-4)]">効率 = 標準時間 ÷ 実測時間 × 100</span>
        </CardFooter>
      </Card>
    </TooltipProvider>
  );
}
