"""検証結果を日本語の表にまとめる: python -m research.turn_zones.report → results/summary.md"""
import json
import os

import numpy as np
import pandas as pd

from .indicators import REGISTRY
from .validate import CONFIRM_TYPES, OUT, PRIMARY


def build():
    met = pd.read_csv(os.path.join(OUT, "metrics.csv"))
    dist = pd.read_csv(os.path.join(OUT, "distinctness.csv"))
    summ = json.load(open(os.path.join(OUT, "summary.json")))
    split = pd.read_csv(os.path.join(OUT, "split_check.csv"))
    rows = []
    for key, info in REGISTRY.items():
        m = met[(met.key == key) & met.ds.isin(PRIMARY)]
        win = "comb" if key in CONFIRM_TYPES else "lead"
        t, b = m[m.side == "top"], m[m.side == "bot"]
        d = dist[(dist.a == key) | (dist.b == key)].copy()
        d["other"] = np.where(d.a == key, d.b, d.a)
        near = d.groupby("other").r_level.apply(lambda s: s.abs().max()).sort_values(ascending=False)
        p = summ["passes"][key]
        fails = sorted({f for v in p["fails"].values() for f in v})
        sp = split[split.key == key].groupby("period")[f"lift_{win}"].mean()
        rows.append(dict(
            key=key, name=info["name"], element=info["element"], kind=info["kind"],
            passed="合格" if p["passed"] else "—", ok=f"{p['ok_datasets']}/3", fails="、".join(fails) or "なし",
            top_hit=t[f"hit_{win}"].mean(), top_lift=t[f"lift_{win}"].mean(),
            bot_hit=b[f"hit_{win}"].mean(), bot_lift=b[f"lift_{win}"].mean(),
            zone=(t.zone_share.values + b.zone_share.values).mean(),
            entries=(t.entries_per_year.values + b.entries_per_year.values).mean(),
            peak=np.nanmedian(np.r_[t.peak_off_median.values, b.peak_off_median.values]),
            near=f"{near.index[0]}（{near.iloc[0]:.2f}）",
            calib=sp.get("calib", np.nan), check=sp.get("check", np.nan),
            score=summ["score"][key], pine=info["pine"]))
    return pd.DataFrame(rows), summ


def main():
    df, summ = build()
    L = ["# 別ウィンドウ型「高値圏/安値圏ライン」10案 — 検証結果", "",
         "- データ: NASDAQ総合・S&P500（1999-2018）と GOOG（2004-2013）の日足を **3倍レバ相当に合成**（TQQQ・SPXL 相当）。実際の TQQQ ではない。",
         "- 正解: 後から見て確定する 15% 以上の天井・底（ZigZag）。",
         "- 捕捉率: 先行型は「天井(底)の5本前〜当日」、確認型（E3・E9）は「5本前〜3本後」にゾーン内だった割合。"
         "倍率は、ゾーンの位置をでたらめにずらした場合（偶然）と比べて何倍か（1.0 = 偶然と同じ）。",
         "- 3データ（NQ3x・SP3x・GOOG3x）の平均。合格 = 計画の合格基準を3データ中2つ以上で満たす。", "",
         "| 案 | 要素 | 種類 | 天井 捕捉率（倍率） | 底 捕捉率（倍率） | ゾーン滞在 | 突入 回/年 | 山のずれ（本） | 一番似ている相手（相関） | 判定 |",
         "|---|---|---|---|---|---|---|---|---|---|"]
    for r in df.itertuples():
        L.append(f"| {r.key} {r.name} | {r.element} | {r.kind} | {r.top_hit:.0f}%（{r.top_lift:.1f}倍） | "
                 f"{r.bot_hit:.0f}%（{r.bot_lift:.1f}倍） | {r.zone:.0f}% | {r.entries:.0f} | {r.peak:.1f} | {r.near} | "
                 f"{r.passed} {r.ok}" + ("" if r.passed == "合格" else f"（{r.fails}）") + " |")
    cov = summ["coverage"]
    L += ["", "## 10案の組み合わせ",
          "- 15%以上の天井・底のうち、10案のどれか1つ以上がゾーン内だった割合（5本前〜3本後）: "
          + "、".join(f"{k} {v['any1']:.0f}%" for k, v in cov.items()),
          "- 3つ以上が同時にゾーン内だった割合: " + "、".join(f"{k} {v['any3']:.0f}%" for k, v in cov.items()),
          "", "## 似ていないかの確認",
          "- 上限（2つ以上のデータで超えたら「似ている」）: 線の相関 0.80、日々の変化の相関 0.80、ゾーンの重なり 0.30。",
          "- 上限を超えた組: " + ("なし" if not summ["hard_pairs"] else "、".join("-".join(p) for p in summ["hard_pairs"])),
          "- 注意（相関0.70超・重なり0.20超・突入が同じ足に重なる割合0.40超）: "
          + "、".join("-".join(p) for p in summ["soft_pairs"]),
          "- 突入が同じ足に重なる割合は、どの案も同じ天井・底を狙うので高くなりやすい（偶然でも約2割）。そのため参考値とした。",
          "", "## 期間を分けた確認（過学習のチェック）",
          "| 案 | 1999-2010 の倍率 | 2011-2018 の倍率 |", "|---|---|---|"]
    for r in df.itertuples():
        L.append(f"| {r.key} | {r.calib:.2f} | {r.check:.2f} |")
    L += ["", "## 検証で変えた設定（設計時の値から）",
          "- E1: 仕上げEMA 3→5（E2 と日々の動きが似すぎていた: 相関 0.82→0.70）",
          "- E6: 0に戻る戻り幅 1.0θ→0.8θ、高値圏ライン 65→70（高値圏に30本以上居座るのを抑えた）",
          "- E9: 直前の引け圧力の期間 5→8（突入が年15回を超えて多すぎた）",
          "", f"ファイル: `pine/` に10本（{', '.join(df.pine)}）。"]
    open(os.path.join(OUT, "summary.md"), "w").write("\n".join(L) + "\n")
    df.to_json(os.path.join(OUT, "table.json"), orient="records", force_ascii=False, indent=1)
    print("\n".join(L))


if __name__ == "__main__":
    main()
