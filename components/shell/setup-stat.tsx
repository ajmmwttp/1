"use client";

import { motion } from "framer-motion";
import { dec } from "@/lib/format";
import { totals } from "@/lib/data/warehouse";
import { EASE_EXPO } from "./motion-tokens";

/**
 * 段取り比率 lives in the chrome, not in a card: setup is paid per company
 * list rather than per item, and it eats this much of picking. The whole
 * product argues from this number, so it is always on screen.
 */
export function SetupStat() {
  return (
    <div className="flex flex-col gap-1.5 whitespace-nowrap px-3 py-3">
      <div className="flex items-baseline justify-between gap-2">
        <span className="text-[10.5px] uppercase tracking-[0.09em] text-[var(--ink-4)]">
          段取り比率
        </span>
        <span className="tnum text-[13px] font-medium leading-none text-[var(--ink)]">
          {dec(totals.pickSetupRatio, 1)}%
        </span>
      </div>
      <div
        role="img"
        aria-label={`ピッキング実働時間に占める段取りの割合 ${dec(totals.pickSetupRatio, 1)}パーセント`}
        className="h-[3px] w-full overflow-hidden rounded-full bg-[var(--sunken)]"
      >
        <motion.div
          initial={{ width: 0 }}
          animate={{ width: `${totals.pickSetupRatio}%` }}
          transition={{ duration: 0.72, ease: EASE_EXPO }}
          className="h-full rounded-full bg-[var(--accent)]"
        />
      </div>
      <span className="text-[10.5px] leading-none text-[var(--ink-4)]">
        ピッキング実働のうち段取り
      </span>
    </div>
  );
}
