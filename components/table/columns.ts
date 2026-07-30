import type { ProcessStats, Role, Verdict, Worker } from "@/lib/data/warehouse";
import { workers } from "@/lib/data/warehouse";

/* ──────────────────────────────────────────────────────────────
   Row model. Only the 26 workers with picking records take part;
   rank is fixed to 縮小後効率 (shrunk) desc so the ordinal keeps its
   meaning even when the reader sorts the table by something else.
   ────────────────────────────────────────────────────────────── */

export interface PickRow {
  rank: number;
  name: string;
  role: Role;
  verdict: Verdict;
  pick: ProcessStats;
}

type PickWorker = Worker & { pick: ProcessStats };

export function buildRows(): PickRow[] {
  return workers
    .filter((w): w is PickWorker => w.pick !== null)
    .slice()
    .sort((a, b) => b.pick.shrunk - a.pick.shrunk || a.name.localeCompare(b.name, "ja"))
    .map((w, i) => ({
      rank: i + 1,
      name: w.name,
      role: w.role,
      verdict: w.pick.verdict,
      pick: w.pick,
    }));
}

/* ── columns ──────────────────────────────────────────────── */

export type ColumnId =
  | "rank"
  | "name"
  | "items"
  | "companies"
  | "itemsPerCompany"
  | "rawSecPerItem"
  | "pureSecPerItem"
  | "shrunk"
  | "verdict";

/** Everything numeric, plus 担当者. 順位 mirrors 効率 and 判定 has its own filter. */
export type SortableId = Exclude<ColumnId, "rank" | "verdict">;

export type SortDir = "asc" | "desc";

export interface SortState {
  id: SortableId;
  dir: SortDir;
}

export interface Column {
  id: ColumnId;
  label: string;
  align: "left" | "right";
  /** Tailwind width class — the table is fixed-ish so figures stay in columns. */
  width: string;
  sortId?: SortableId;
  /** Direction applied on the first click of an inactive header. */
  firstDir?: SortDir;
  hint?: string;
}

export const COLUMNS: Column[] = [
  { id: "rank", label: "#", align: "right", width: "w-[32px]" },
  { id: "name", label: "担当者", align: "left", width: "w-[188px]", sortId: "name", firstDir: "asc" },
  { id: "items", label: "件数", align: "right", width: "w-[76px]", sortId: "items", firstDir: "desc" },
  {
    id: "companies",
    label: "企業数",
    align: "right",
    width: "w-[104px]",
    sortId: "companies",
    firstDir: "desc",
    hint: "リスト枚数。段取りはこの回数だけ発生します。",
  },
  {
    id: "itemsPerCompany",
    label: "件/社",
    align: "right",
    width: "w-[88px]",
    sortId: "itemsPerCompany",
    firstDir: "desc",
  },
  {
    id: "rawSecPerItem",
    label: "素の秒/件",
    align: "right",
    width: "w-[96px]",
    sortId: "rawSecPerItem",
    firstDir: "asc",
  },
  {
    id: "pureSecPerItem",
    label: "純速度",
    align: "right",
    width: "w-[84px]",
    sortId: "pureSecPerItem",
    firstDir: "asc",
  },
  { id: "shrunk", label: "効率", align: "right", width: "w-[80px]", sortId: "shrunk", firstDir: "desc" },
  { id: "verdict", label: "判定", align: "left", width: "w-[104px]" },
];

/** Ranking order is the resting state of the table. */
export const DEFAULT_SORT: SortState = { id: "shrunk", dir: "desc" };

export function firstDirOf(id: SortableId): SortDir {
  return COLUMNS.find((c) => c.sortId === id)?.firstDir ?? "desc";
}

function numeric(row: PickRow, id: Exclude<SortableId, "name">): number {
  return row.pick[id];
}

export function compareRows(a: PickRow, b: PickRow, id: SortableId, dir: SortDir): number {
  const sign = dir === "asc" ? 1 : -1;
  if (id === "name") return sign * a.name.localeCompare(b.name, "ja");
  const delta = numeric(a, id) - numeric(b, id);
  // Ties fall back to the ranking order so sorts stay deterministic.
  return delta === 0 ? a.rank - b.rank : sign * delta;
}

/* ── filter vocabulary ────────────────────────────────────── */

export const VERDICT_OPTIONS: Verdict[] = ["上位", "標準", "要支援"];

export const ROLE_OPTIONS: { id: Role; label: string }[] = [
  { id: "staff", label: "社員" },
  { id: "parttime", label: "パート" },
];

export function roleLabel(role: Role): string {
  return role === "staff" ? "社員" : "パート";
}
