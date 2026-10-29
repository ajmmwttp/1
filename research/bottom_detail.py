"""底側「底が近いかも」（TL-Classic3 の bot が 50 到達）の詳しい成績

期間ごとに: 点灯数と的中（95%区間）、年ごとの的中、点灯から次の底までの追加の下げ、10本後の値動き（単純リターン）、
段階（80 以上）別の10本後、同じ下げの中での点灯回数、札が出ないまま来た底の割合。
（平滑化の比較は点灯回数を合わせ直す必要があるので verify_classic.py の smooth を参照）
python3 bottom_detail.py → results/bottom_detail.txt
"""
from pathlib import Path

import numpy as np
import pandas as pd

import turnline_lab as L
import verify_classic as VC
from cand_classic import score2

PERIODS = [("nasdaq3x", "1999-2010（調整に使った期間）", ("1999-07-01", "2010-12-31")),
           ("nasdaq3x", "2011-18", ("2011-01-01", "2018-12-31")),
           ("sp3x", "2011-18", ("2011-01-01", "2018-12-31")),
           ("sp3x_close", "2019-22", ("2019-01-01", "2022-12-28")),
           ("sp3x_close", "1991-98", ("1991-01-01", "1998-12-31"))]
K = L.K_BARS


def wilson(k, n, z=1.96):
    if n == 0:
        return np.nan, np.nan
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return c - h, c + h


def signals(x, mask):
    s = L.crossings_up(np.nan_to_num(np.asarray(x, float)))
    return s[mask[s]]


def detail(name, label, per):
    df = L.load(name)
    piv = L.pivots(df)
    m = L.period_mask(df, per)
    tg = L.targets(piv, len(df))
    sc = score2(df)
    bot = sc.bot.to_numpy()
    c, lo = df.c.to_numpy(), df.l.to_numpy()
    pb, pk = piv.bar.to_numpy(), piv.kind.to_numpy()
    sig = signals(bot, m)
    hit = (tg["next_kind"][sig] == -1) & (tg["bars_to"][sig] <= K)
    known = tg["next_kind"][sig] != 0
    sig, hit = sig[known], hit[known]
    out = [f"■ {name} {label}"]
    a, b = wilson(hit.sum(), len(sig))
    rr = signals(VC.rsi_rm(df).bot.to_numpy(), m)
    rhit = ((tg["next_kind"][rr] == -1) & (tg["bars_to"][rr] <= K))[tg["next_kind"][rr] != 0]
    out.append(f"  点灯 {len(sig)}回・当たり {hit.sum()}回 = {hit.mean():.0%}（95%区間 {a:.0%}〜{b:.0%}）"
               f" ／ 参考 RSI14（同じ点灯回数）{rhit.mean():.0%}（{len(rhit)}回）")
    yrs = pd.Series(hit, index=df.index[sig].year)
    out.append("  年ごと（当たり/点灯）: " + "  ".join(f"{y}: {int(g.sum())}/{len(g)}" for y, g in yrs.groupby(level=0)))
    for y in sorted(set(df.index[sig].year)):  # 年ごとの詳しい値（点灯3回以上の年）
        s_y = sig[df.index[sig].year == y]
        if len(s_y) < 3:
            continue
        d_y = [1 - lo[pb[j[0]]] / c[t] for t in s_y if len(j := np.flatnonzero((pk == "L") & (pb >= t)))]
        f_y = c[s_y[s_y + 10 < len(c)] + 10] / c[s_y[s_y + 10 < len(c)]] - 1
        out.append(f"    {y}: 当たり {int(hit[df.index[sig].year == y].sum())}/{len(s_y)}・次の底までの追加の下げ 中央値 "
                   f"{np.median(d_y):.1%}（最大 {max(d_y):.1%}）・10本後に上がった {np.mean(f_y > 0):.0%}（中央値 {np.median(f_y):+.1%}）")
    # 点灯から次の底（後から分かる安値）までの追加の下げ
    drops, worst = [], (0.0, None)
    for s in sig:
        j = np.flatnonzero((pk == "L") & (pb >= s))
        if len(j):
            d = lo[pb[j[0]]] / c[s] - 1
            drops.append(d)
            if d < worst[0]:
                worst = (d, df.index[s].date())
    dr = -np.array(drops)
    out.append(f"  点灯から次の底までの追加の下げ: 中央値 {np.median(dr):.1%}・10%以上 {np.mean(dr >= 0.10):.0%}"
               f"・20%以上 {np.mean(dr >= 0.20):.0%}・最大 {dr.max():.1%}（{worst[1]} の点灯）")
    # 10本後の値動き（単純リターン）
    ok = sig[sig + 10 < len(c)]
    f10 = c[ok + 10] / c[ok] - 1
    idx = np.flatnonzero(m)
    idx = idx[idx + 10 < len(c)]
    u10 = c[idx + 10] / c[idx] - 1
    out.append(f"  点灯の10本後: 中央値 {np.median(f10):+.1%}・上がった割合 {np.mean(f10 > 0):.0%}・最悪 {f10.min():+.1%}"
               f" ／ 平常時: 中央値 {np.median(u10):+.1%}・上がった割合 {np.mean(u10 > 0):.0%}")
    # 段階別（その日の bot の値）の10本後
    for lo_, hi_, nm in ((50, 80, "50〜80（底が近いかも）"), (80, 101, "80以上（いちばん濃い段）")):
        d = idx[(bot[idx] >= lo_) & (bot[idx] < hi_)]
        if len(d):
            f = c[d + 10] / c[d] - 1
            out.append(f"  {nm}の日 {len(d)}日: 10本後の中央値 {np.median(f):+.1%}・上がった割合 {np.mean(f > 0):.0%}")
    # 同じ下げ（次の底が同じ）の中での点灯回数
    nxt = [int(pb[np.flatnonzero((pk == "L") & (pb >= s))[0]]) for s in sig if ((pk == "L") & (pb >= s)).any()]
    cnt = pd.Series(nxt).value_counts()
    out.append(f"  同じ下げの中での点灯: 点灯のあった下げ {len(cnt)}回のうち2回以上 {np.mean(cnt >= 2):.0%}・最大 {cnt.max()}回"
               f"（2回目以降の点灯は全体の {1 - len(cnt) / len(nxt):.0%}）")
    # 札が出ないまま来た底（事前点灯なし）
    r = L.evaluate(sc, df, piv, m)["bot"]
    out.append(f"  底のうち、その脚で一度も点灯しなかった割合: {1 - r['recall_pre']:.0%}（底 {r['n_pivots']}回）")
    return out


if __name__ == "__main__":
    lines = []
    for name, label, per in PERIODS:
        lines += detail(name, label, per) + [""]
    # 表示した期間の「最初の点灯から期間内の最安値まで」
    for name, a, b in (("nasdaq3x", "2018-06-01", "2018-12-31"), ("nasdaq3x", "2015-06-01", "2016-03-31"),
                       ("sp3x_close", "2020-01-02", "2020-10-30"), ("sp3x_close", "2022-01-03", "2022-12-28")):
        df = L.load(name)
        m = L.period_mask(df, (a, b))
        sig = signals(score2(df).bot.to_numpy(), m)
        s0 = sig[0]
        low = df.l.to_numpy()[s0:np.flatnonzero(m)[-1] + 1].min()
        lines.append(f"図の期間 {name} {a}〜{b}: 最初の点灯 {df.index[s0].date()}（終値 {df.c.iat[s0]:.1f}）から"
                     f"期間内の最安値まで {low / df.c.iat[s0] - 1:+.0%}")
    txt = "\n".join(lines)
    print(txt)
    (Path(__file__).parent / "results" / "bottom_detail.txt").write_text(txt + "\n", encoding="utf-8")
