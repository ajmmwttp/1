"use client";

import * as React from "react";
import { ChevronDown, ChevronUp, Info, SearchX } from "lucide-react";
import type { Role, Verdict } from "@/lib/data/warehouse";
import { dec, int } from "@/lib/format";
import { cn } from "@/lib/utils";
import { REVEAL_STEPS } from "@/components/motion/ladder";
import { Reveal } from "@/components/motion/reveal";
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
  "sticky top-0 z-10 h-[34px] pointer-coarse:h-11 whitespace-nowrap bg-[var(--card)] px-2 text-[12px] font-medium";

/* ── frozen identity column ───────────────────────────────────
   On a phone the table is 880px inside a ~356px window, so the reader is
   always scrolling numbers past a name they can no longer see. # and 担当者
   are pinned to the left edge instead: the identity stays put and only the
   measures move. Both cells carry an opaque surface (otherwise the scrolled
   columns show straight through) and repeat the row's hover / focus / selected
   surface so a pinned row still reads as one row.

   The name column's offset is the rank column's rendered width, which is NOT
   its declared 32px: the table's auto layout stretches every declared width
   proportionally to reach min-w-[880px]. Measuring it is the only way to make
   the two cells tile exactly, so a ResizeObserver feeds --frozen-x below. */
const FROZEN =
  "sticky z-[1] bg-[var(--card)] group-hover:bg-[var(--elevated)] group-focus-visible:bg-[var(--elevated)] group-aria-selected:bg-[var(--elevated)]";
/** Marks the seam while the numbers are scrolled under it. */
const FROZEN_EDGE =
  "border-r border-[var(--line)] shadow-[6px_0_10px_-8px_var(--line-strong)]";

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
  stuck,
}: {
  column: Column;
  sort: SortState;
  onToggle: (id: SortableId) => void;
  /** True while the reader has scrolled the measures under the frozen pair. */
  stuck: boolean;
}) {
  const sortId = column.sortId;
  const active = sortId !== undefined && sortId === sort.id;
  const right = column.align === "right";
  const frozen = column.id === "rank" || column.id === "name";

  const label = sortId ? (
    <button
      type="button"
      onClick={() => onToggle(sortId)}
      aria-label={`${column.label}で並べ替え`}
      className={cn(
        "inline-flex items-center gap-1 rounded-[4px] transition-colors",
        // A 17px-tall text button is a mouse target. On touch it fills the
        // taller header row and holds a 40px minimum on the short labels.
        "pointer-coarse:h-10 pointer-coarse:min-w-10",
        right && "pointer-coarse:justify-end",
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
        // z-20 so the frozen pair wins the corner against the rest of the
        // header (z-10), which in turn wins against the frozen body cells.
        frozen && "z-20",
        frozen && (column.id === "rank" ? "left-0" : "left-[var(--frozen-x)]"),
        frozen && stuck && column.id === "name" && FROZEN_EDGE,
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
                className="flex size-4 items-center justify-center rounded-[4px] text-[var(--ink-4)] transition-colors pointer-coarse:size-10 hover:text-[var(--ink-2)]"
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

function Cell({ row, column, stuck }: { row: PickRow; column: Column; stuck: boolean }) {
  const p = row.pick;
  const right = column.align === "right";
  const base = cn(CELL, right ? "text-right" : "text-left");

  switch (column.id) {
    case "rank":
      return (
        // sticky is itself a positioned box, so the rail below still anchors
        // to this cell — `relative` would only fight it for the position slot.
        <td className={cn(base, FROZEN, "left-0 pr-1 pl-3")}>
          {/* Grows from the vertical centre rather than fading: a rail that
              fades reads as a highlight appearing, one that draws itself
              reads as the row being picked out. 180ms on the expo curve.
              Reduced motion zeroes the duration in globals.css — the rail
              still marks the row, it just arrives at once. */}
          <span
            aria-hidden
            className="pointer-events-none absolute inset-y-0 left-0 w-[2px] origin-center scale-y-0 bg-[var(--accent)] transition-transform duration-[180ms] ease-[var(--ease-out-expo)] group-hover:scale-y-100 group-focus-visible:scale-y-100 group-aria-selected:scale-y-100"
          />
          <span className="tnum text-[var(--ink-4)]">{row.rank}</span>
        </td>
      );

    case "name":
      return (
        <td className={cn(base, FROZEN, "left-[var(--frozen-x)]", stuck && FROZEN_EDGE)}>
          <span className="flex items-center gap-1.5">
            <span className="min-w-0 truncate text-[var(--ink)]">{row.name}</span>
            <Badge tone="outline" className="shrink-0 px-1 py-[2px] text-[12px] text-[var(--ink-3)]">
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
            <span className="text-[12px] font-medium text-[var(--ink)]">
              該当する担当者がいません
            </span>
            <span className="text-[12px] text-[var(--ink-3)]">
              検索語や絞り込みを変えてください。
            </span>
          </span>
          <Button
            variant="outline"
            size="sm"
            onClick={onClear}
            className="pointer-coarse:h-10 pointer-coarse:px-4"
          >
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

  /* Frozen-column plumbing. `frozenX` is the rank column's rendered width, so
     the 担当者 cells butt up against it with no seam and no overlap at any
     table width; 32 is the declared width, which is right until the auto
     layout stretches the table to its 880px minimum. `stuck` only turns the
     seam on once there is something scrolled beneath it. */
  const scrollRef = React.useRef<HTMLDivElement>(null);
  const tableRef = React.useRef<HTMLTableElement>(null);
  const [frozenX, setFrozenX] = React.useState(32);
  const [stuck, setStuck] = React.useState(false);

  React.useEffect(() => {
    const head = tableRef.current?.querySelector("thead th");
    if (!head) return;
    const measure = () => setFrozenX(head.getBoundingClientRect().width);
    measure();
    const observer = new ResizeObserver(measure);
    observer.observe(head);
    return () => observer.disconnect();
  }, []);

  const handleScroll = React.useCallback((event: React.UIEvent<HTMLDivElement>) => {
    setStuck(event.currentTarget.scrollLeft > 0);
  }, []);

  return (
    <TooltipProvider delayDuration={120}>
      <Reveal step={REVEAL_STEPS.table}>
        <Card data-card>
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
            <div ref={scrollRef} onScroll={handleScroll} className="max-h-[560px] overflow-auto">
              <table
                ref={tableRef}
                style={{ "--frozen-x": `${frozenX}px` } as React.CSSProperties}
                className="w-full min-w-[880px] border-separate border-spacing-0 text-[12px]"
              >
                <caption className="sr-only">
                  ピッキング担当者26名の件数・企業数・件/社・素の秒/件・純速度・効率・判定。既定は効率の降順。
                </caption>
                <thead>
                  <tr>
                    {COLUMNS.map((c) => (
                      <HeaderCell key={c.id} column={c} sort={sort} onToggle={toggle} stuck={stuck} />
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
                        <Cell key={c.id} row={row} column={c} stuck={stuck} />
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </CardContent>

          <CardFooter className="justify-between gap-4">
            <span>
              全<span className="tnum">{TOTAL}</span>名中{" "}
              <span className="tnum">{sorted.length}</span>
              名を表示
            </span>
            <span className="text-[var(--ink-4)]">効率 = 標準時間 ÷ 実測時間 × 100</span>
          </CardFooter>
        </Card>
      </Reveal>
    </TooltipProvider>
  );
}
