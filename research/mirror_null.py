"""鏡映帰無: 値動きの「向き」だけをでたらめにした偽の価格で、指標の成績がどれだけ出るか

日ごとの値動き（前日終値比の始値・高値・安値・終値）を、確率 1/2 で平均のまわりに裏返す。
変動率の大きさの並び（荒れた日が続く性質）と平均の伸びは本物と同じで、向きの予測可能性だけが消える。
本物の成績が偽の価格の成績を上回らなければ、その成績は「ZigZag の定義と変動率」から自動的に出る分で、予測力ではない。

python3 mirror_null.py [モジュール名:関数名 ...] [--n 100]   例: python3 mirror_null.py cand_classic:score2
"""
import argparse
import importlib

import numpy as np
import pandas as pd

import turnline_lab as L

PERIODS = [("nasdaq3x", "test", ("2011-01-01", "2018-12-31")),
           ("sp3x", "check_post", ("2011-01-01", "2018-12-31")),
           ("sp3x_close", "oos2019", ("2019-01-01", "2022-12-28")),
           ("sp3x_close", "pre1999", ("1991-01-01", "1998-12-31"))]
KEYS = ("recall_pre", "precision", "auc10")


def mirror(base, rng):
    """向きだけを確率 1/2 で裏返した偽の指数 OHLC"""
    pc = base.c.shift(1)
    rel = np.column_stack([(base[k] / pc - 1).to_numpy() for k in "ohlc"])[1:]
    mu = rel[:, 3].mean()
    f = rng.random(len(rel)) < 0.5
    rel2 = rel.copy()
    rel2[f, 0] = 2 * mu - rel[f, 0]
    rel2[f, 1] = 2 * mu - rel[f, 2]  # 裏返すと高値と安値が入れ替わる
    rel2[f, 2] = 2 * mu - rel[f, 1]
    rel2[f, 3] = 2 * mu - rel[f, 3]
    c = np.r_[base.c.iat[0], base.c.iat[0] * np.cumprod(1 + rel2[:, 3])]
    p = c[:-1]
    return pd.DataFrame({"o": np.r_[base.o.iat[0], p * (1 + rel2[:, 0])], "h": np.r_[base.h.iat[0], p * (1 + rel2[:, 1])],
                         "l": np.r_[base.l.iat[0], p * (1 + rel2[:, 2])], "c": c}, index=base.index)


def run(fns, n=100, seed=12):
    rows = []
    for name in dict.fromkeys(p[0] for p in PERIODS):
        pers = [(pn, per) for nm, pn, per in PERIODS if nm == name]
        base = L.load_base(name)
        df0 = L.leverage(base)
        piv0 = L.pivots(df0)
        real = {(lab, pn): L.evaluate(fn(df0), df0, piv0, L.period_mask(df0, per)) for lab, fn in fns for pn, per in pers}
        null = {k: [] for k in real}
        rng = np.random.default_rng(seed)
        for _ in range(n):
            df = L.leverage(mirror(base, rng))
            piv = L.pivots(df)
            scores = {lab: fn(df) for lab, fn in fns}
            for lab, _ in fns:
                for pn, per in pers:
                    null[(lab, pn)].append(L.evaluate(scores[lab], df, piv, L.period_mask(df, per)))
        for (lab, pn), r in real.items():
            for side in ("top", "bot"):
                row = {"指標": lab, "期間": f"{name}/{pn}", "side": side}
                for k in KEYS:
                    v = np.array([e[side][k] for e in null[(lab, pn)]], float)
                    row[k] = r[side][k]
                    row[f"{k}_偽"] = float(np.nanmedian(v))
                    row[f"{k}_p"] = float(np.mean(v >= r[side][k]))
                rows.append(row)
    return pd.DataFrame(rows)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("fns", nargs="*")
    ap.add_argument("--n", type=int, default=100)
    a = ap.parse_args()
    fns = [("RSI14", L.baseline_rsi)]
    for spec in a.fns:
        mod, fn = spec.split(":")
        fns.append((spec, getattr(importlib.import_module(mod), fn)))
    pd.set_option("display.width", 250, "display.max_rows", 200, "display.precision", 3)
    print(run(fns, a.n).to_string(index=False))
