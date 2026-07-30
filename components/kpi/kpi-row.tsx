import { dec, int } from "@/lib/format";
import { days, deltas, timeMix, totals } from "@/lib/data/warehouse";
import { REVEAL_STEPS } from "@/components/motion/ladder";
import { Reveal } from "@/components/motion/reveal";
import { StatTile } from "./stat-tile";

/* ────────────────────────────────────────────────────────────────
   TONE AT THE CALL SITE

   All four metrics fell over the last 7 days, so all four get tone="down".
   What differs is what falling MEANS, and that is what `invert` / `judged`
   encode — never the arrow, which always follows the sign of the delta:

     総処理件数  down · judged={false} → neutral. Volume is demand, not
                 performance; colouring it red would blame the floor for the
                 order book.
     平均効率    down · judged                → bad  (red).   Lower is worse.
     段取り比率  down · invert                → good (green). Lower is better —
                 this is the number the whole product exists to push down.
     稼働時間    down · judged={false} → neutral. Hours track volume.
   ──────────────────────────────────────────────────────────────── */

// ピッキング実働 504.6h のうち、段取りが 212.8h。timeMix が実測、式は保険。
const pickHours = totals.pickMinutes / 60;
const setupHours =
  timeMix.find((s) => s.label === "段取り")?.hours ??
  pickHours * (totals.pickSetupRatio / 100);

// pickEff は 04-24 以降が欠測（実在の記録欠落）。欠測日は線を引かず落とす。
const pickEffSeries = days
  .map((d) => d.pickEff)
  .filter((v): v is number => v !== null);

export function KpiRow() {
  return (
    <section data-kpi-row data-section aria-label="主要指標" data-probe={JSON.stringify(REVEAL_STEPS)}>
      {/* Entrance ladder: the lede shares the first tile's beat, then one
          40ms step per tile. Delays are hard-coded here because page.tsx is
          a server component and cannot orchestrate. */}
      <Reveal step={REVEAL_STEPS.kpiTile} className="mb-3 flex items-center gap-2">
        <span
          aria-hidden
          className="size-[6px] shrink-0 rounded-[1px] bg-[var(--accent)]"
        />
        <p className="text-[12px] leading-[1.5] text-[var(--ink-2)]">
          1社ごとの段取りが{" "}
          <span className="tnum text-[var(--ink)]">{dec(setupHours, 1)}</span>{" "}
          時間。ピッキング総時間の{" "}
          <span className="tnum text-[var(--ink)]">
            {dec(totals.pickSetupRatio, 1)}%
          </span>{" "}
          を占めています。
        </p>
      </Reveal>

      <div className="grid grid-cols-2 gap-4 xl:grid-cols-4">
        <Reveal step={REVEAL_STEPS.kpiTile + 0} className="h-full">
          <StatTile
            label="総処理件数"
            value={int(totals.totalItems)}
            unit="件"
            delta={deltas.items}
            deltaLabel="前週比"
            spark={days.map((d) => d.totalItems)}
            tone="down"
            judged={false}
            hint="ピッキング 15,942件 ＋ 梱包 24,449件"
            countTo={totals.totalItems}
            countDecimals={0}
            countDelay={0}
            className="h-full"
          />
        </Reveal>

        <Reveal step={REVEAL_STEPS.kpiTile + 1} className="h-full">
          <StatTile
            label="平均効率"
            value={dec(totals.avgEff, 1)}
            unit="%"
            delta={deltas.eff}
            deltaLabel="前週比"
            spark={pickEffSeries}
            tone="down"
            hint="標準時間 ÷ 実測時間。100 が標準どおり"
            footnote="ピッキング 99.8 ／ 梱包 100.0"
            countTo={totals.avgEff}
            countDelay={40}
            className="h-full"
          />
        </Reveal>

        <Reveal step={REVEAL_STEPS.kpiTile + 2} className="h-full">
          <StatTile
            label="段取り比率"
            value={dec(totals.pickSetupRatio, 1)}
            unit="%"
            delta={deltas.setup}
            deltaLabel="前週比"
            spark={days.map((d) => d.setupMinutes)}
            tone="down"
            invert
            hint="ピッキング時間のうち、1社ごとの段取りが占める割合"
            footnote={`${dec(setupHours, 1)}h / ${dec(pickHours, 1)}h`}
            countTo={totals.pickSetupRatio}
            countDelay={80}
            className="h-full"
          />
        </Reveal>

        <Reveal step={REVEAL_STEPS.kpiTile + 3} className="h-full">
          <StatTile
            label="稼働時間"
            value={dec(totals.totalHours, 1)}
            unit="h"
            delta={deltas.hours}
            deltaLabel="前週比"
            spark={days.map((d) => d.totalHours)}
            tone="down"
            judged={false}
            hint="ピッキング＋梱包の実働合計"
            footnote="26名 ／ 17日分の完全記録"
            countTo={totals.totalHours}
            countDelay={120}
            className="h-full"
          />
        </Reveal>
      </div>
    </section>
  );
}
