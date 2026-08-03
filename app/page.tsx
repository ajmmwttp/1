import { CalendarRange, Download } from "lucide-react";
import { KpiRow } from "@/components/kpi/kpi-row";
import {
  SetupScatterContaminated,
  SetupScatterCorrected,
} from "@/components/charts/setup-scatter";
import { ThroughputChart } from "@/components/charts/throughput-chart";
import { WorkerSpeedChart } from "@/components/charts/worker-speed-chart";
import { TimeMixChart } from "@/components/charts/time-mix-chart";
import { WorkerTable } from "@/components/table/worker-table";
import { Button } from "@/components/ui/button";
import { dataWindow, model, totals } from "@/lib/data/warehouse";
import { dec, int } from "@/lib/format";

export default function Page() {
  return (
    <>
      <header className="mb-6 flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="text-[12px] font-medium uppercase tracking-[0.09em] text-[var(--ink-4)]">
            オペレーション概要
          </p>
          <h1 className="mt-1.5 text-[16px] font-medium tracking-[-0.02em] text-[var(--ink)]">
            2026年4月　庫内作業レビュー
          </h1>
          <p className="mt-1.5 max-w-[62ch] text-[12px] leading-relaxed text-[var(--ink-3)]">
            ピッキングと梱包を、段取り時間を切り分けて評価しています。件数だけで並べると、
            1社1個のリストを多く引いた人ほど不利に出ます。
          </p>
        </div>

        <div className="flex items-center gap-2">
          <div className="flex h-8 items-center gap-1.5 rounded-[8px] border border-[var(--line)] bg-[var(--card)] px-2.5 text-[12px] text-[var(--ink-2)]">
            <CalendarRange className="size-3.5 text-[var(--ink-4)]" />
            <span className="tnum">
              {dataWindow.start.replaceAll("-", "/")} – {dataWindow.end.replaceAll("-", "/")}
            </span>
            <span className="ml-1 rounded-[4px] bg-[var(--elevated)] px-1.5 py-0.5 text-[12px] text-[var(--ink-4)]">
              <span className="tnum">{dataWindow.totalDays}</span> 日
            </span>
          </div>
          <Button variant="outline" size="default">
            <Download />
            エクスポート
          </Button>
        </div>
      </header>

      <div data-section className="space-y-4">
        <KpiRow />

        {/* Position 2: this pair is the argument the whole console makes. */}
        <section
          data-section
          aria-label="段取りの混入と、その補正"
          className="grid grid-cols-1 items-stretch gap-4 md:grid-cols-2 md:grid-rows-[auto_auto_1fr_auto]"
        >
          <SetupScatterContaminated />
          <SetupScatterCorrected />
        </section>

        <section
          data-section
          aria-label="推移と内訳"
          className="grid grid-cols-1 items-stretch gap-4 xl:grid-cols-12"
        >
          <div className="flex xl:col-span-8">
            <ThroughputChart />
          </div>
          <div className="flex xl:col-span-4">
            <TimeMixChart />
          </div>
        </section>

        <section data-section aria-label="担当者別の速度">
          <WorkerSpeedChart />
        </section>

        <section data-section aria-label="担当者ランキング">
          <WorkerTable />
        </section>
      </div>

      <footer className="mt-8 flex flex-wrap items-center justify-between gap-3 border-t border-[var(--line)] pt-4 text-[12px] text-[var(--ink-4)]">
        <p>
          標準時間 ＝ a × 企業数 ＋ b × 件数　（ピッキング a=
          <span className="tnum">{dec(model.pick.a, 1)}</span> 秒/社・b=
          <span className="tnum">{dec(model.pick.b, 1)}</span> 秒/件／梱包 a=
          <span className="tnum">{dec(model.pack.a, 1)}</span> 秒/社・b=
          <span className="tnum">{dec(model.pack.b, 1)}</span> 秒/件）
        </p>
        <p>
          対象 <span className="tnum">{totals.headcount}</span> 名・
          <span className="tnum">{int(totals.totalItems)}</span> 件・完全記録{" "}
          <span className="tnum">{dataWindow.completeDays}</span> 日分
        </p>
      </footer>
    </>
  );
}
