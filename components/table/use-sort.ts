"use client";

import { useCallback, useMemo, useState } from "react";
import {
  compareRows,
  DEFAULT_SORT,
  firstDirOf,
  type PickRow,
  type SortState,
  type SortableId,
} from "./columns";

/**
 * Sort state is stored as an *override* of the default ranking, not as an
 * absolute value. `null` means "no override" — the table rests at 効率 desc.
 *
 * Cycle for any inactive column: firstDir → opposite → null (back to default).
 * The default column (効率) is already active while the override is null, so it
 * cycles desc ⇄ asc and its second click lands exactly on the default again.
 */
export function useSort(rows: PickRow[]) {
  const [override, setOverride] = useState<SortState | null>(null);
  const sort = override ?? DEFAULT_SORT;

  const toggle = useCallback((id: SortableId) => {
    setOverride((prev) => {
      const current = prev ?? DEFAULT_SORT;
      const first = firstDirOf(id);
      if (current.id !== id) return { id, dir: first };
      if (current.dir === first) return { id, dir: first === "asc" ? "desc" : "asc" };
      return null;
    });
  }, []);

  const reset = useCallback(() => setOverride(null), []);

  const sorted = useMemo(
    () => rows.slice().sort((a, b) => compareRows(a, b, sort.id, sort.dir)),
    [rows, sort],
  );

  return { sort, sorted, toggle, reset, isDefault: override === null };
}
