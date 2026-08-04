"use client";

import * as React from "react";
import { useReducedMotion } from "framer-motion";

/* ──────────────────────────────────────────────────────────────
   useCountUp — first mount only.

   Returns `null` whenever the figure should simply be its final value:
   reduced motion, no target, or the count has finished. The caller then
   renders the string it was already given, so the last frame of the
   count is the exact formatted value and never a rounding of it.

   Never re-runs: there is no dependency on anything that changes after
   mount, so a filter, a sort or a scroll cannot restart the numbers.
   ────────────────────────────────────────────────────────────── */

const DURATION_MS = 700;

/** Cubic ease-out: fast off the mark, and the last 10% is nearly free. */
const easeOut = (t: number) => 1 - (1 - t) ** 3;

export function useCountUp(target: number | null, delayMs = 0): number | null {
  const reduceMotion = useReducedMotion();
  const [value, setValue] = React.useState<number | null>(null);

  // Layout effect, not effect: the Reveal wrapper is still at opacity 0 on
  // this commit, so the drop to 0 happens while the tile is invisible and
  // the user never sees the final figure flash before the count starts.
  React.useLayoutEffect(() => {
    if (reduceMotion || target === null) return;

    setValue(0);

    let frame = 0;
    let start = 0;

    const tick = (now: number) => {
      if (start === 0) start = now;
      const elapsed = now - start - delayMs;

      if (elapsed >= DURATION_MS) {
        setValue(null);
        return;
      }
      if (elapsed > 0) {
        setValue(target * easeOut(elapsed / DURATION_MS));
      }
      frame = requestAnimationFrame(tick);
    };

    frame = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(frame);
    // Mount-only by construction — these three are constant for a given tile.
  }, [target, delayMs, reduceMotion]);

  return value;
}
