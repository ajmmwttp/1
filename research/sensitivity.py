"""正解の定義（ZigZag の反転幅）を変えても結論が変わらないかの確認

python3 sensitivity.py [モジュール名:関数名 ...]   例: python3 sensitivity.py cand_classic:score
引数なしなら基準（RSI・理想形）だけを評価する。
"""
import importlib
import sys

import pandas as pd

import turnline_lab as L

MULTS = (1.0, 1.5, 2.0)  # 反転幅 = 倍率 × 10日分の変動率（1.5 が標準）
SETS = [("nasdaq3x", "test"), ("sp3x", "check"), ("sp3x_close", "oos2019")]


def resolve(spec):
    mod, fn = spec.split(":")
    return spec, getattr(importlib.import_module(mod), fn)


def run(fns):
    rows = []
    for name, period in SETS:
        df = L.load(name)
        mask = L.period_mask(df, L.SETS[name][1][period])
        for mult in MULTS:
            piv = L.pivots(df, L.swing_threshold(df, mult=mult))
            for label, fn in fns:
                sc = fn(df) if label != "ideal" else L.ideal(df, piv)
                r = L.evaluate(sc, df, piv, mask)
                for side in ("top", "bot"):
                    d = r[side]
                    rows.append({"set": f"{name}/{period}", "倍率": mult, "指標": label, "side": side,
                                 "転換点/年": d["pivots_per_year"], "事前点灯率": d["recall_pre"],
                                 "何本前": d["lead_med"], "的中率": d["precision"], "AUC10": d["auc10"]})
    return pd.DataFrame(rows)


if __name__ == "__main__":
    fns = [("RSI14", L.baseline_rsi), ("ideal", None)] + [resolve(s) for s in sys.argv[1:]]
    pd.set_option("display.width", 220, "display.max_rows", 500, "display.precision", 2)
    tab = run(fns)
    print(tab.to_string(index=False))
