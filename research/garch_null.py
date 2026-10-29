"""GARCH 帰無: 「下げると荒れる」性質（変動率の集まり・非対称）を残し、向きの予測可能性だけを消した偽の価格との比較

評価期間を GJR-GARCH(1,1)-t のフィルター付きヒストリカル・シミュレーション（verify_exhaust.garch_path）に置き換え、
TL-Classic3（cand_classic.score2）と、同じ点灯回数に合わせた RSI14（verify_classic.rsi_rm）の成績を比べる。
鏡映帰無（mirror_null.py）より厳しい帰無で、底側の成績の一部は「急落で変動率が跳ねると ZigZag の底がすぐ付く」性質で説明できる。

python3 garch_null.py [--n 150]  → results/garch_null.txt に保存
"""
import argparse
from pathlib import Path

import numpy as np
import pandas as pd

import turnline_lab as L
import verify_classic as VC
import verify_exhaust as V
from cand_classic import score2

PERIODS = [("nasdaq3x", "2011-18", ("2011-01-01", "2018-12-31"), False),
           ("sp3x", "2011-18", ("2011-01-01", "2018-12-31"), False),
           ("sp3x_close", "2019-22", ("2019-01-01", "2022-12-28"), True),
           ("sp3x_close", "1991-98", ("1991-01-01", "1998-12-31"), True)]
FNS = [("TL-Classic3", score2), ("RSI14(同じ点灯回数)", VC.rsi_rm)]
KEYS = ("precision", "auc10", "recall_pre")


def run(n=150, seed=11):
    rows = []
    for name, label, per, close_only in PERIODS:
        G = V.garch_setup(name)
        df = V.DATA[name]
        m = L.period_mask(df, per)
        real = {lab: L.evaluate(fn(df), df, L.pivots(df), m) for lab, fn in FNS}
        null = {lab: [] for lab, _ in FNS}
        rng = np.random.default_rng(seed)
        for _ in range(n):
            sdf = V.garch_path(G, df, m, rng, close_only)
            piv = L.pivots(sdf)
            for lab, fn in FNS:
                null[lab].append(L.evaluate(fn(sdf), sdf, piv, m))
        for lab, _ in FNS:
            for side in ("top", "bot"):
                row = {"指標": lab, "期間": f"{name}/{label}", "side": side}
                for k in KEYS:
                    v = np.array([e[side][k] for e in null[lab]], float)
                    row[k] = real[lab][side][k]
                    row[f"{k}_偽"] = float(np.nanmedian(v))
                    row[f"{k}_p"] = float(np.mean(v >= real[lab][side][k]))
                rows.append(row)
    return pd.DataFrame(rows)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=150)
    a = ap.parse_args()
    pd.set_option("display.width", 250, "display.max_rows", 200, "display.precision", 3)
    txt = run(a.n).to_string(index=False)
    print(txt)
    (Path(__file__).parent / "results" / "garch_null.txt").write_text(txt + "\n", encoding="utf-8")
