"""10案の検証: python -m research.turn_zones.validate

- 正解: 後から見て確定する ZigZag (3倍データは終値15%反転, 大波は25%, GOOG1x は10%)
- 各案の成績・合格判定・10案どうしが似ていないか (相関・ゾーンの重なり) を計算し,
  results/ に metrics.csv, distinctness.csv, summary.json, summary.md を出す.
"""
import json
import math
import os
from itertools import combinations

import numpy as np
import pandas as pd

from .data import HL_RELIABLE_FROM, load_all
from .helpers import rma_p, tr_p, zones
from .indicators import REGISTRY

OUT = os.path.join(os.path.dirname(__file__), "results")
PRIMARY = ["NQ3x", "SP3x", "GOOG3x"]
CONFIRM_TYPES = {"E3", "E9"}
WARMUP = 300


def zigzag(c, pct):
    """終値ベースの ZigZag. 確定したピボットだけを [(index, +1=天井 / -1=底)] で返す."""
    piv = []
    hi = lo = 0
    trend = 0
    for i in range(1, len(c)):
        if trend == 0:
            if c[i] > c[hi]:
                hi = i
            if c[i] < c[lo]:
                lo = i
            if c[i] >= c[lo] * (1 + pct):
                piv.append((lo, -1)); trend, hi = 1, i
            elif c[i] <= c[hi] * (1 - pct):
                piv.append((hi, 1)); trend, lo = -1, i
        elif trend == 1:
            if c[i] > c[hi]:
                hi = i
            elif c[i] <= c[hi] * (1 - pct):
                piv.append((hi, 1)); trend, lo = -1, i
        else:
            if c[i] < c[lo]:
                lo = i
            elif c[i] >= c[lo] * (1 + pct):
                piv.append((lo, -1)); trend, hi = 1, i
    return piv


def episodes(st, side):
    """state == side が続く区間 [(start, end)]."""
    m = np.r_[False, st == side, False]
    d = np.diff(m.astype(int))
    return list(zip(np.where(d == 1)[0], np.where(d == -1)[0] - 1))


def scored_mask(df, key, ds, period=None):
    m = np.zeros(len(df), bool)
    m[WARMUP:] = True
    start = HL_RELIABLE_FROM.get(ds)
    if start and REGISTRY[key]["uses_hl"]:
        m &= df.index >= pd.Timestamp(start)
    if period:
        m &= (df.index >= pd.Timestamp(period[0])) & (df.index <= pd.Timestamp(period[1]))
    return m


def side_metrics(st, ev_in, line, c, atrp, piv, side, mask, rng):
    idx = np.where(mask)[0]
    lo_i, hi_i = idx[0], idx[-1]
    pv = [p for p, s in piv if s == side and lo_i + 10 <= p <= hi_i - 10]
    opp = [p for p, s in piv if s == -side]
    ins = (st == side)
    eps = [(a, b) for a, b in episodes(st, side) if lo_i <= a <= hi_i]
    span = hi_i - lo_i + 1
    out = dict(n_pivots=len(pv), zone_share=100 * ins[mask].mean(),
               entries_per_year=len(eps) / (span / 252))

    def hit(p, a, b, s=None):
        s = ins if s is None else s
        return bool(s[max(p + a, 0):p + b + 1].any())

    for name, (a, b) in dict(lead=(-5, 0), conf=(1, 3), comb=(-5, 3)).items():
        real = np.mean([hit(p, a, b) for p in pv]) if pv else np.nan
        # 偶然の基準: ゾーン系列を採点区間の中で 200 通りに循環シフト
        sub = ins[lo_i:hi_i + 1]
        base = []
        for off in rng.integers(50, max(span - 50, 51), 200):
            sh = np.zeros_like(ins)
            sh[lo_i:hi_i + 1] = np.roll(sub, off)
            base.append(np.mean([hit(p, a, b, sh) for p in pv]) if pv else np.nan)
        mb = np.nanmean(base) if pv else np.nan
        out[f"hit_{name}"] = 100 * real
        out[f"lift_{name}"] = real / mb if pv and mb > 0 else np.nan

    leads, dist_pct, dist_atr, exit_lag, giveback = [], [], [], [], []
    for p in pv:
        cand = [e for e in eps if e[0] <= p + 3 and e[1] >= p - 5]
        if not cand:
            continue
        a, b = min(cand, key=lambda e: 0 if e[0] <= p <= e[1] else min(abs(e[0] - p), abs(e[1] - p)))
        leads.append(p - a)
        dist_pct.append(100 * abs(math.log(c[a] / c[p])))
        dist_atr.append(abs(math.log(c[a] / c[p])) / atrp[a] if atrp[a] > 0 else np.nan)
        x = min(b + 1, len(c) - 1)
        exit_lag.append(x - p)
        giveback.append(100 * abs(c[p] - c[x]) / c[p])
    false = wrong = 0
    for a, b in eps:
        false += not any(a - 2 <= p <= b + 5 for p, s in piv if s == side)
        wrong += any(a <= p <= a + 5 for p in opp)
    # 線の山(谷)と価格の山(谷)のずれ. 線が頭打ちで横ばいの時は, 山の高さ-1以内で価格の極値に一番近い足を採る
    offs = []
    for p in pv:
        w = side * line[p - 10:p + 11]
        if np.all(np.isnan(w)):
            continue
        top = np.where(w >= np.nanmax(w) - 1.0)[0] - 10
        offs.append(np.min(np.abs(top)))
    offs = np.asarray(offs)
    out.update(lead_median=np.median(leads) if leads else np.nan,
               dist_pct_median=np.median(dist_pct) if dist_pct else np.nan,
               dist_atr_median=np.nanmedian(dist_atr) if dist_atr else np.nan,
               exit_lag_median=np.median(exit_lag) if exit_lag else np.nan,
               giveback_median=np.median(giveback) if giveback else np.nan,
               false_rate=100 * false / len(eps) if eps else np.nan,
               wrong_rate=100 * wrong / len(eps) if eps else np.nan,
               peak_off_median=np.median(offs) if len(offs) else np.nan,
               peak_within2=100 * np.mean(offs <= 2) if len(offs) else np.nan)
    return out


def line_metrics(line, st, mask):
    x = line[mask]
    d = np.diff(x)
    sg = np.sign(d[~np.isnan(d)])
    sg = sg[sg != 0]
    runs = [b - a + 1 for s in (1, -1) for a, b in episodes(np.where(mask, st, 0), s)]
    return dict(dirchg_per100=100 * np.sum(sg[1:] != sg[:-1]) / max(len(x), 1),
                mean_abs_step=np.nanmean(np.abs(d)),
                saturation=100 * np.nanmean(np.abs(x) >= 95),
                longest_run=max(runs) if runs else 0)


def evaluate(data, keys=None, params=None, period=None):
    """period=(開始, 終了) を渡すと採点だけその期間に絞る (指標は全期間で計算)."""
    keys = keys or list(REGISTRY)
    params = params or {}
    rng = np.random.default_rng(0)
    rows, series = [], {}
    for ds, df in data.items():
        c = df["Close"].to_numpy()
        h, l = df["High"].to_numpy(), df["Low"].to_numpy()
        atrp = rma_p(tr_p(h, l, c), 14) / c
        pct = 0.10 if ds == "GOOG1x" else 0.15
        piv = zigzag(c, pct)
        piv_major = zigzag(c, 0.25)
        for key in keys:
            out = REGISTRY[key]["fn"](df, **params.get(key, {}))
            line, U, L = out["line"], out["U"], out["L"]
            st, ev = zones(line, U, L)
            series[(ds, key)] = dict(line=line, U=U, L=L, st=st, ev=ev, dir=out.get("dir"))
            mask = scored_mask(df, key, ds, period)
            if mask.sum() < 252:
                continue
            lm = line_metrics(line, st, mask)
            for side, nm in ((1, "top"), (-1, "bot")):
                m = side_metrics(st, ev["topIn" if side == 1 else "botIn"], line, c, atrp, piv, side, mask, rng)
                mj = side_metrics(st, None, line, c, atrp, piv_major, side, mask, rng)
                rows.append(dict(ds=ds, key=key, side=nm, **m, **lm,
                                 hit_comb_major=mj["hit_comb"], lift_comb_major=mj["lift_comb"]))
    return pd.DataFrame(rows), series


def pass_check(met):
    """合格基準 (計画の通り). 3つの主要データのうち2つ以上で満たせば合格."""
    res = {}
    for key, g in met[met.ds.isin(PRIMARY)].groupby("key"):
        ok_ds, reasons = 0, {}
        for ds, gg in g.groupby("ds"):
            t, b = gg[gg.side == "top"].iloc[0], gg[gg.side == "bot"].iloc[0]
            win = "comb" if key in CONFIRM_TYPES else "lead"
            lifts = sorted([t[f"lift_{win}"], b[f"lift_{win}"]])
            cond = {
                "滞在率10-25%": 10 <= t.zone_share + b.zone_share <= 25,
                "片側3%以上": min(t.zone_share, b.zone_share) >= 3,
                "リフト": (lifts[0] >= 1.3) if key in CONFIRM_TYPES else (lifts[1] >= 1.2 and lifts[0] >= 1.0),
                "山のずれ≤2本": np.nanmedian([t.peak_off_median, b.peak_off_median]) <= 2,
                "逆側≤20%": max(t.wrong_rate, b.wrong_rate) <= 20,
                "最長≤25本": t.longest_run <= 25,
                "張り付き≤12%": t.saturation <= 12,
                "なめらかさ": t.dirchg_per100 <= (50 if key in ("E8", "E9") else 45),
                "突入 年2-15回": all(2 <= x <= 15 for x in (t.entries_per_year, b.entries_per_year)),
            }
            ok_ds += all(cond.values())
            reasons[ds] = [k for k, v in cond.items() if not v]
        res[key] = dict(passed=ok_ds >= 2, ok_datasets=ok_ds, fails=reasons)
    return res


def distinctness(data, series, keys):
    rows = []
    for ds in PRIMARY:
        df = data[ds]
        m = np.zeros(len(df), bool)
        m[WARMUP:] = True
        if ds in HL_RELIABLE_FROM:
            m &= df.index >= pd.Timestamp(HL_RELIABLE_FROM[ds])
        for a, b in combinations(keys, 2):
            A, B = series[(ds, a)], series[(ds, b)]
            ok = m & ~np.isnan(A["line"]) & ~np.isnan(B["line"])
            la, lb = A["line"][ok], B["line"][ok]
            rL = np.corrcoef(la, lb)[0, 1]
            da, db = np.diff(A["line"]), np.diff(B["line"])
            okd = ok[1:] & ok[:-1]
            rD = np.corrcoef(da[okd], db[okd])[0, 1]
            js = []
            for s in (1, -1):
                x, y = (A["st"] == s) & ok, (B["st"] == s) & ok
                u = (x | y).sum()
                js.append((x & y).sum() / u if u else 0.0)
            ov = []
            for P, Q in ((A, B), (B, A)):
                hits = tot = 0
                for k in ("topIn", "botIn"):
                    e1 = np.where(P["ev"][k] & ok)[0]
                    e2 = np.where(Q["ev"][k] & ok)[0]
                    tot += len(e1)
                    hits += sum(np.any(np.abs(e2 - e) <= 2) for e in e1)
                ov.append(hits / tot if tot else 0.0)
            rows.append(dict(ds=ds, a=a, b=b, r_level=rL, r_change=rD, jaccard=np.mean(js), overlap=np.mean(ov)))
    d = pd.DataFrame(rows)
    # 線の形とゾーンの重なりで「似ている」を判定する. 突入が同じ足に重なる割合 (overlap) は,
    # どの案も同じ天井・底を狙う以上高くなりやすい (偶然でも約2割) ので参考値として注意扱いにする.
    d["hard"] = (d.r_level.abs() > 0.80) | (d.r_change.abs() > 0.80) | (d.jaccard > 0.30)
    d["soft"] = (d.r_level.abs() > 0.70) | (d.jaccard > 0.20) | (d.overlap > 0.40)
    return d


def score(met):
    out = {}
    for key, g in met[met.ds.isin(PRIMARY)].groupby("key"):
        win = "comb" if key in CONFIRM_TYPES else "lead"
        vals = []
        for ds, gg in g.groupby("ds"):
            lift = gg[f"lift_{win}"].mean()
            vals.append(0.5 * lift + 0.2 * (1 - gg.false_rate.mean() / 100)
                        + 0.15 * gg.peak_within2.mean() / 100
                        + 0.15 * (1 - min(gg.dirchg_per100.iloc[0] / 60, 1)))
        out[key] = float(np.mean(vals))
    return out


def coverage(data, series, keys):
    res = {}
    for ds in PRIMARY:
        c = data[ds]["Close"].to_numpy()
        piv = [(p, s) for p, s in zigzag(c, 0.15) if p >= WARMUP + 10 and p < len(c) - 10]
        if ds in HL_RELIABLE_FROM:
            t0 = data[ds].index.get_indexer([pd.Timestamp(HL_RELIABLE_FROM[ds])], method="bfill")[0]
            piv = [(p, s) for p, s in piv if p >= t0]
        n = [sum(bool((series[(ds, k)]["st"][p - 5:p + 4] == s).any()) for k in keys) for p, s in piv]
        n = np.array(n)
        res[ds] = dict(pivots=len(piv), any1=100 * np.mean(n >= 1), any3=100 * np.mean(n >= 3))
    return res


def main():
    os.makedirs(OUT, exist_ok=True)
    data = load_all()
    keys = list(REGISTRY)
    met, series = evaluate(data, keys)
    met.to_csv(os.path.join(OUT, "metrics.csv"), index=False, float_format="%.3f")
    pc = pass_check(met)
    dist = distinctness(data, series, keys)
    dist.to_csv(os.path.join(OUT, "distinctness.csv"), index=False, float_format="%.3f")
    sc = score(met)
    cov = coverage(data, series, keys)

    # 似ている組: 2つ以上のデータで上限超え
    hard = dist[dist.hard].groupby(["a", "b"]).size()
    hard_pairs = [list(k) for k, v in hard.items() if v >= 2]
    soft = dist[dist.soft & ~dist.hard].groupby(["a", "b"]).size()
    soft_pairs = [list(k) for k, v in soft.items() if v >= 2]

    summary = dict(passes=pc, score=sc, coverage=cov, hard_pairs=hard_pairs, soft_pairs=soft_pairs)
    json.dump(summary, open(os.path.join(OUT, "summary.json"), "w"), ensure_ascii=False, indent=1, default=float)

    # 調整用(1999-2010)と確認用(2011-2018)で成績が崩れていないか
    split = []
    for nm, per in (("calib", ("1999-01-01", "2010-12-31")), ("check", ("2011-01-01", "2018-12-31"))):
        m2, _ = evaluate({k: data[k] for k in PRIMARY}, keys, period=per)
        g = m2.groupby(["key", "ds"]).agg(zone=("zone_share", "sum"), lift_lead=("lift_lead", "mean"),
                                          lift_comb=("lift_comb", "mean")).reset_index()
        g["period"] = nm
        split.append(g)
    split = pd.concat(split)
    split.to_csv(os.path.join(OUT, "split_check.csv"), index=False, float_format="%.3f")

    pd.set_option("display.width", 250)
    pd.set_option("display.max_columns", 40)
    show = met[met.ds.isin(PRIMARY + ["GOOG1x"])].pivot_table(
        index="key", columns=["ds", "side"], values=["zone_share", "lift_lead", "lift_comb"], aggfunc="first")
    print(show.round(2).to_string())
    print()
    for k in keys:
        print(k, "合格" if pc[k]["passed"] else "不合格", pc[k]["ok_datasets"], "/3", pc[k]["fails"], f"score={sc[k]:.3f}")
    print("hard pairs:", hard_pairs)
    print("soft pairs:", soft_pairs)
    print("coverage:", cov)
    print(split.pivot_table(index="key", columns=["period"], values=["zone", "lift_lead", "lift_comb"], aggfunc="mean").round(2).to_string())
    print(dist.groupby(["a", "b"])[["r_level", "r_change", "jaccard", "overlap"]].max().sort_values("r_level", ascending=False).head(12).round(2).to_string())


if __name__ == "__main__":
    main()
