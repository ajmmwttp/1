"""cand_exhaust（score / score2）の反証検証  key: exhaust

python3 verify_exhaust.py                       # 全部（数分〜十数分）
python3 verify_exhaust.py causal repro null     # 一部だけ（既存の results/verify_exhaust.json にマージ）
  causal : L.check_causal（n_cuts=30, 複数 start, 3 データセット）＋ swing 特徴量の総当たり独立実装との照合
  repro  : run_all を再実行して results/exhaust.json と照合。基準 RSI・期間の分割（check の学習同時期/以後）・
           素の RSI の AUC・点灯バー割合・1日の平均変動・80 到達・確率の当てはまり（calibration）
  null   : L.null_test（循環シフト, n=300, seed=1）
  rw     : cand_exhaust.rw_null（値動きの順番入れ替え）を別 seed で再実行
  garch  : 追加の帰無。GJR-GARCH(1,1)-t のフィルター付きヒストリカル・シミュレーション（変動率の偏り・
           下げで変動率が上がる性質は残し、方向の予測可能性だけ消す）
           garch_cond = 実現変動率が実データの 0.8〜1.25 倍の経路だけ / garch_check, rw_check = sp3x/check でも実行
           garch_diag = 帰無モデルの転換点の統計・日次の性質が実データに近いか
  zzstate: ZigZag の状態だけの指標（確定済みの最新転換点が天井なら bot=100）＝学習なしの幾何だけの基準
  aucdiff: AUC10 の差（score − 素の RSI）のブロック・ブートストラップ（63 本ブロック）
  traincv: train 内の主張（4分割ブロック CV・脚のハザード・下降脚の振幅）の再計算
  sens   : パラメータを ±20〜30% 動かして train で学習し直し、test / oos2019 / check_post の崩れ方を見る
  curve  : 点灯回数を揃えたときの的中率・事前点灯率（score vs RSI。しきい値は各期間内で合わせた記述統計）
  fwd    : 点灯後10本の騰落と、点灯時刻をずらした帰無
  table  : 保存済みの結果から「検証後の数字」の表を作る
cand_exhaust.py / turnline_lab.py は import するだけで編集しない。
"""
import json
import sys
import time
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, roc_auc_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import SplineTransformer, StandardScaler

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import turnline_lab as L  # noqa: E402
import cand_exhaust as X  # noqa: E402

warnings.filterwarnings("ignore")
OUT = HERE / "results" / "verify_exhaust.json"
TRAIN = L.SETS["nasdaq3x"][1]["train"]
# 追加の評価期間: sp3x/check は学習（NASDAQ 1999-07〜2010-12）と同じ時期を含むので、時期で分けて見る
EXTRA = {"sp3x": {"check_overlap": ("1999-07-01", "2010-12-31"), "check_post": ("2011-01-01", "2018-12-31")}}
MAIN = [("nasdaq3x", "test"), ("sp3x", "check"), ("sp3x_close", "oos2019")]
KEYS = ("recall_pre", "lead_med", "remain_med", "signals_per_year", "precision", "auc10", "ap10", "base10", "lit_frac")

DATA = {name: L.load(name) for name in L.SETS}
PIVS = {name: L.pivots(df) for name, df in DATA.items()}


def period(name, pname):
    per = L.SETS[name][1].get(pname) or EXTRA[name][pname]
    return L.period_mask(DATA[name], per)


def fnum(v):
    v = float(v)
    return v if np.isfinite(v) else None


def clean(o):
    if isinstance(o, dict):
        return {str(k): clean(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [clean(v) for v in o]
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (np.bool_,)):
        return bool(o)
    if isinstance(o, (float, np.floating)):
        return fnum(o)
    return o


FNS = {"score": X.score, "score2": X.score2, "rsi_baseline": L.baseline_rsi, "rsi_matched": X.rsi_matched}


# ================================================================ 1. 未来参照
def swing_bruteforce(d):
    """d の最終バー t の swing 特徴量を d だけから一から計算する（cand_exhaust の逐次更新とは別の書き方）。
    確定済みの最新転換点 = d で計算した ZigZag の最後の転換点（確定バー <= t）"""
    t = len(d) - 1
    h, l, c = d.h.to_numpy(float), d.l.to_numpy(float), d.c.to_numpy(float)
    pct = L.swing_threshold(d)
    piv = L.pivots(d)
    if len(piv) == 0:
        return None
    b, kind, p = int(piv.bar.iat[-1]), piv.kind.iat[-1], float(piv.price.iat[-1])
    assert int(piv.confirm.iat[-1]) <= t

    def amax(a):
        return len(a) - 1 - int(np.argmax(a[::-1]))

    def amin(a):
        return len(a) - 1 - int(np.argmin(a[::-1]))

    if kind == "L":       # 確定底 → 暫定高値 a1 → その後の安値 a2
        seg = h[b + 1:t + 1]
        a1 = b + 1 + amax(seg) if len(seg) else t
        x1 = h[a1]
        seg2 = l[a1 + 1:t + 1]
        a2 = a1 + 1 + amin(seg2) if len(seg2) else t
        e2 = l[a2] if len(seg2) else c[t]
        return {"R_up": (x1 / p - 1) / pct[b], "G_top": (1 - c[t] / x1) / pct[a1], "age_up": t - b,
                "R_dn": (1 - e2 / x1) / pct[a1], "G_bot": (c[t] / e2 - 1) / pct[a2], "age_dn": t - a1}
    seg = l[b + 1:t + 1]  # 確定天井 → 暫定安値 a1 → その後の高値 a2
    a1 = b + 1 + amin(seg) if len(seg) else t
    x1 = l[a1]
    seg2 = h[a1 + 1:t + 1]
    a2 = a1 + 1 + amax(seg2) if len(seg2) else t
    e2 = h[a2] if len(seg2) else c[t]
    return {"R_dn": (1 - x1 / p) / pct[b], "G_bot": (c[t] / x1 - 1) / pct[a1], "age_dn": t - b,
            "R_up": (e2 / x1 - 1) / pct[a1], "G_top": (1 - c[t] / e2) / pct[a2], "age_up": t - a1}


def part_causal(quick=False):
    out = {"check_causal": {}, "bruteforce": {}}
    starts = {"nasdaq3x": (0.65, 0.7), "sp3x": (0.3, 0.7), "sp3x_close": (0.3, 0.7)}
    for fname in ("score", "score2", "rsi_baseline"):
        for name, ss in starts.items():
            for s in ss:
                v = L.check_causal(FNS[fname], DATA[name], n_cuts=30, start=s, seed=0)
                out["check_causal"][f"{fname}|{name}|start={s}"] = v
                print(f"  check_causal {fname:12s} {name:10s} start={s}: {v:.3g}", flush=True)
        # 参考: 学習期間内の切断も含む（モデルは固定なので特徴量の因果性だけを見る）
        v = L.check_causal(FNS[fname], DATA["nasdaq3x"], n_cuts=30, start=0.3, seed=1)
        out["check_causal"][f"{fname}|nasdaq3x|start=0.3(ref)"] = v
        print(f"  check_causal {fname:12s} nasdaq3x   start=0.3 (参考): {v:.3g}", flush=True)
    # 総当たり: 途中で切ったデータから swing 特徴量を一から計算し、全期間で計算した値と比べる。
    # 同じ切断で score / score2 の最終バーも比べる（check_causal より多い切断点）
    rng = np.random.default_rng(7)
    for name, df in DATA.items():
        full = X.swing_state(df)
        sc_full = {f: FNS[f](df)[["top", "bot"]].to_numpy(float) for f in ("score", "score2")}
        cuts = np.sort(rng.choice(np.arange(300, len(df) - 1), 40 if quick else 150, replace=False))
        worst_bf, worst_sc, n_ok = 0.0, {"score": 0.0, "score2": 0.0}, 0
        for t in cuts:
            d = df.iloc[:t + 1]
            bf = swing_bruteforce(d)
            if bf is None:
                continue
            n_ok += 1
            for k, v in bf.items():
                worst_bf = max(worst_bf, abs(v - full[k].iat[t]))
            for f in ("score", "score2"):
                part = FNS[f](d)[["top", "bot"]].to_numpy(float)[-1]
                worst_sc[f] = max(worst_sc[f], float(np.max(np.abs(part - sc_full[f][t]))))
        out["bruteforce"][name] = {"n_cuts": int(n_ok), "swing_feature_max_diff": worst_bf,
                                   "score_last_bar_max_diff": worst_sc["score"],
                                   "score2_last_bar_max_diff": worst_sc["score2"]}
        print(f"  bruteforce {name}: {out['bruteforce'][name]}", flush=True)
    return out


# ================================================================ 2. 数字の再現と追加の記述統計
def calib_table(p, y, ok, bins=(0, .1, .2, .3, .4, .5, .6, .7, 1.01)):
    rows = []
    for a, b in zip(bins[:-1], bins[1:]):
        s = ok & (p >= a) & (p < b)
        if s.sum():
            rows.append({"p_bin": f"{a:.1f}-{min(b, 1):.1f}", "n": int(s.sum()), "p_mean": float(p[s].mean()),
                         "y_rate": float(y[s].mean())})
    return rows


def part_repro(quick=False):
    J = json.load(open(HERE / "results" / "exhaust.json"))
    reported = {c["function"]: c["results"] for c in J["candidates"]}
    reported.update({k: v["results"] for k, v in J["reference"].items()})
    out = {"diff_vs_reported": {}, "results": {}, "extra": {}}
    for fname, fn in FNS.items():
        res = L.run_all(fn)
        worst = 0.0
        for (name, pname), r in res.items():
            rep = reported[fname][f"{name}/{pname}"]
            for side in ("top", "bot"):
                for k, v in r[side].items():
                    rv = rep[side][k]
                    if rv is None or not np.isfinite(float(v)):
                        if (rv is None) != (not np.isfinite(float(v))):
                            worst = np.inf
                        continue
                    worst = max(worst, abs(float(v) - float(rv)))
        out["diff_vs_reported"][fname] = worst
        # 追加の期間（check の分割）も含めて保存
        sc = {name: fn(df) for name, df in DATA.items()}
        allp = [(n_, p_) for n_ in L.SETS for p_ in L.SETS[n_][1]] + [("sp3x", p_) for p_ in EXTRA["sp3x"]]
        for name, pname in allp:
            r = L.evaluate(sc[name], DATA[name], PIVS[name], period(name, pname))
            for side in ("top", "bot"):
                out["results"][f"{fname}|{name}/{pname}|{side}"] = {k: fnum(r[side][k]) for k in KEYS}
        print(f"  {fname}: 報告値との最大差 {worst:.3g}", flush=True)
    # 追加の記述統計: 素の RSI の AUC（基準 RSI は 50 未満を 0 に切るので同順位が多い）、
    # 1日の平均変動、80 到達、確率の当てはまり
    rs = {name: L.rsi(df.c).to_numpy() for name, df in DATA.items()}
    fit = X.fitted()
    for name, pname in MAIN + [("sp3x", "check_post"), ("sp3x", "check_overlap"), ("sp3x_close", "pre1999"),
                               ("nasdaq3x", "train")]:
        df, m = DATA[name], period(name, pname)
        tg = L.targets(PIVS[name], len(df))
        F = X.features(df)
        ex = {}
        for side, sgn in (("top", 1), ("bot", -1)):
            y = tg[f"{side}_10"]
            ok = m & ~np.isnan(y) & ~np.isnan(rs[name])
            ex[f"auc10_raw_rsi_{side}"] = float(roc_auc_score(y[ok], sgn * rs[name][ok]))
            ex[f"ap10_raw_rsi_{side}"] = float(average_precision_score(y[ok], sgn * rs[name][ok]))
            for fname in ("score", "score2", "rsi_baseline"):
                s = FNS[fname](df)[side].to_numpy(float)
                ex[f"mean_abs_daily_change_{fname}_{side}"] = float(np.mean(np.abs(np.diff(s[m]))))
                ex[f"frac_bars_ge80_{fname}_{side}"] = float(np.mean(s[m] >= 80))
                ex[f"max_{fname}_{side}"] = float(np.max(s[m]))
                sig80 = L.crossings_up(s, th=80, reset=L.RESET)
                ex[f"signals80_per_year_{fname}_{side}"] = float(m[sig80].sum() / (m.sum() / 252))
            for cand in ("score", "score2"):
                f = fit[cand][side]
                p = X.predict(f["model"], F[f["cols"]].to_numpy(float))
                okp = m & ~np.isnan(y) & ~np.isnan(p)
                ex[f"calib_{cand}_{side}"] = calib_table(p, y, okp)
                ex[f"brier_{cand}_{side}"] = float(np.mean((p[okp] - y[okp]) ** 2))
                ex[f"brier_base_{side}"] = float(np.mean((y[okp].mean() - y[okp]) ** 2))
                ex[f"mean_p_{cand}_{side}"] = float(p[okp].mean())
                ex[f"y_rate_{side}"] = float(y[okp].mean())
        out["extra"][f"{name}/{pname}"] = ex
    # ideal の 1日の平均変動（参考）
    for name, pname in MAIN:
        idl = L.ideal(DATA[name], PIVS[name])
        m = period(name, pname)
        out["extra"][f"{name}/{pname}"]["mean_abs_daily_change_ideal"] = {
            s: float(np.mean(np.abs(np.diff(idl[s].to_numpy()[m])))) for s in ("top", "bot")}
    return out


# ================================================================ 3. 循環シフト帰無（n=300, seed=1）
def part_null(quick=False):
    n = 60 if quick else 300
    out = {}
    targets = MAIN + [("sp3x", "check_post"), ("sp3x_close", "pre1999")]
    for fname in ("score", "score2", "rsi_baseline", "rsi_matched"):
        for name, pname in targets:
            df = DATA[name]
            nt = L.null_test(FNS[fname](df), df, PIVS[name], period(name, pname), n=n, seed=1)
            out[f"{fname}|{name}/{pname}"] = nt
            print(f"  null {fname:12s} {name}/{pname}: " + " ".join(
                f"{s}:" + ",".join(f"{k}={v[0]:.3f}/{v[1]:.3f}/p{v[2]:.3f}" for k, v in nt[s].items())
                for s in ("top", "bot")), flush=True)
    return out


# ================================================================ 4. ランダムウォーク帰無（別 seed で再実行）
def part_rw(quick=False, cases=(("nasdaq3x", "test"), ("sp3x_close", "oos2019"), ("sp3x_close", "pre1999"))):
    n = 30 if quick else 200
    out = {}
    for fname in ("score", "score2", "rsi_baseline"):
        for name, pname in cases:
            df = DATA[name]
            rw = X.rw_null(FNS[fname], df, period(name, pname), n=n, seed=2)
            out[f"{fname}|{name}/{pname}"] = rw
            print(f"  rw {fname:12s} {name}/{pname}: " + " ".join(
                f"{s}:" + ",".join(f"{k}={v[0]:.3f}/{v[1]:.3f}/p{v[2]:.2f}" for k, v in rw[s].items()
                                   if k in ("precision", "auc10", "recall_pre")) for s in ("top", "bot")), flush=True)
    return out


# ================================================================ 5. GARCH 帰無（変動率の偏りは残し、方向の予測可能性を消す）
def garch_setup(name):
    from arch import arch_model
    df = DATA[name]
    lprev = np.r_[np.nan, df.c.to_numpy(float)[:-1]]
    base = {k: (df[k].to_numpy(float) / lprev - 1) / 3 for k in ("o", "h", "l")}   # レバレッジ前の日中の動き
    base["c"] = (df.c.to_numpy(float) / lprev - 1 + L.EXPENSE / 252) / 3
    r = 100 * base["c"][1:]
    res = arch_model(r, mean="Constant", vol="GARCH", p=1, o=1, q=1, dist="t").fit(disp="off")
    prm = res.params
    return {"base": base, "mu": prm["mu"], "om": prm["omega"], "al": prm["alpha[1]"], "ga": prm["gamma[1]"],
            "be": prm["beta[1]"], "sig": np.r_[np.nan, np.asarray(res.conditional_volatility)],
            "z": np.r_[np.nan, np.asarray(res.std_resid)], "params": {k: float(v) for k, v in prm.items()},
            "rmin": float(np.nanmin(r)), "rmax": float(np.nanmax(r))}   # 実データの日次騰落の最小/最大（%）


CLIPPED = [0, 0]   # GARCH 帰無で止めた日数 / 生成した日数


def garch_path(G, df, mask, rng, close_only, clip=True):
    """評価期間 [a, b) を GJR-GARCH のフィルター付きヒストリカル・シミュレーションに置き換えた系列。
    標準化残差（評価期間内の実際の日）を無作為に引き、その日の日中の形も変動率比で伸縮して使う。
    b 以降は実際の日次の動きをそのままつなぐ（cand_exhaust.shuffled と同じ扱い）"""
    seg = np.flatnonzero(mask)
    a, b = seg[0], seg[-1] + 1
    pool = np.arange(a, b)
    o, h, l, c = (df[k].to_numpy(float).copy() for k in ("o", "h", "l", "c"))
    ratios = df[["o", "h", "l", "c"]].to_numpy(float) / np.r_[np.nan, df.c.to_numpy(float)[:-1]][:, None]
    s2, lp = G["sig"][a] ** 2, c[a - 1]
    draws = pool[rng.integers(0, len(pool), b - a)]
    for i, t in enumerate(range(a, len(df))):
        if t < b:
            s = draws[i]
            st = np.sqrt(s2)
            eps = st * G["z"][s]
            if clip:   # 実データで一度も起きていない大きさの日次騰落（3倍で -100% など）は実データの最大/最小で止める
                e2 = float(np.clip(eps, G["rmin"] - G["mu"], G["rmax"] - G["mu"]))
                CLIPPED[0] += int(e2 != eps)
                CLIPPED[1] += 1
                eps = e2
            k = st / G["sig"][s]
            ct = lp * max(1 + 3 * (G["mu"] + eps) / 100 - L.EXPENSE / 252, 1e-6)
            if close_only:
                ot = ht = lt = ct
            else:
                ot, ht, lt = (lp * max(1 + 3 * G["base"][x][s] * k, 1e-6) for x in ("o", "h", "l"))
                ht, lt = max(ht, ot, ct), min(lt, ot, ct)
            s2 = G["om"] + (G["al"] + G["ga"] * (eps < 0)) * eps ** 2 + G["be"] * s2
        else:
            ot, ht, lt, ct = (lp * ratios[t, j] for j in range(4))
        o[t], h[t], l[t], c[t] = ot, ht, lt, ct
        lp = ct
    return pd.DataFrame({"o": o, "h": h, "l": l, "c": c}, index=df.index)


def part_garch(quick=False, cond=False, cases=None):
    """cond=True: 評価期間の実現変動率（日次騰落の標準偏差）が実データの 0.8〜1.25 倍の経路だけを使う
    （GARCH の経路は実データより荒れやすいので、変動率の水準を揃えた帰無も見る）"""
    n = 30 if quick else 150
    keys = ("recall_pre", "precision", "auc10", "lead_med", "remain_med", "signals_per_year")
    out = {}
    cases = cases or [("nasdaq3x", "test", False), ("nasdaq3x", "test", True), ("sp3x_close", "oos2019", True),
             ("sp3x_close", "pre1999", True)]
    Gs = {}
    for name, pname, close_only in cases:
        if name not in Gs:
            Gs[name] = garch_setup(name)
            out[f"params|{name}"] = Gs[name]["params"]
        G = Gs[name]
        df0, m = DATA[name], period(name, pname)
        df = df0.copy()
        if close_only:
            df[["o", "h", "l"]] = np.repeat(df.c.to_numpy()[:, None], 3, axis=1)
        tag = f"{name}/{pname}" + ("|close_only" if close_only else "|ohlc")
        for fname in ("score", "score2", "rsi_baseline"):
            fn = FNS[fname]
            real = L.evaluate(fn(df), df, L.pivots(df), m)
            rng = np.random.default_rng(11)
            null = {s: {k: [] for k in keys} for s in ("top", "bot")}
            seg = np.flatnonzero(m)
            a, b = seg[0], seg[-1] + 1
            rv_real = np.std(np.diff(np.log(df.c.to_numpy()[a - 1:b])))
            acc = tries = 0
            while acc < n and tries < 8 * n:
                tries += 1
                sdf = garch_path(G, df, m, rng, close_only)
                if cond:
                    rv = np.std(np.diff(np.log(sdf.c.to_numpy()[a - 1:b]))) / rv_real
                    if not 0.8 <= rv <= 1.25:
                        continue
                acc += 1
                e = L.evaluate(fn(sdf), sdf, L.pivots(sdf), m)
                for s in null:
                    for k in keys:
                        null[s][k].append(e[s][k])
            out[f"accepted|{fname}|{tag}"] = [acc, tries]
            out[f"clipped_frac|{fname}|{tag}"] = CLIPPED[0] / max(CLIPPED[1], 1)
            CLIPPED[0] = CLIPPED[1] = 0
            out[f"{fname}|{tag}"] = {s: {k: (fnum(real[s][k]), fnum(np.nanmedian(null[s][k])),
                                             fnum(np.mean(np.array(null[s][k], float) >= real[s][k])))
                                         for k in keys} for s in null}
            print(f"  garch {fname:12s} {tag}: " + " ".join(
                f"{s}:" + ",".join(f"{k}={v[0]:.3f}/{v[1]:.3f}/p{v[2]:.2f}" for k, v in out[f'{fname}|{tag}'][s].items()
                                   if k in ("precision", "auc10", "recall_pre")) for s in ("top", "bot")), flush=True)
    return out


# ================================================================ 6. パラメータ感度（train で学習し直す）
def exhaust_feats_p(df, span=60, w=1.0):
    """cand_exhaust.exhaust_feats と同じ式で、窓の長さを w 倍、変動率の EWMA を span にしたもの（w=1, span=60 で一致）"""
    r_ = lambda x: max(2, int(round(x * w)))
    c, h, l = df.c, df.h, df.l
    lr = np.log(c).diff()
    vol = lr.ewm(span=span, min_periods=20).std()
    up = (c > c.shift(1)).astype(float)
    dn = (c < c.shift(1)).astype(float)
    cu = up.groupby((up == 0).cumsum()).cumsum()
    cd = dn.groupby((dn == 0).cumsum()).cumsum()
    tr = pd.concat([h - l, (h - c.shift(1)).abs(), (l - c.shift(1)).abs()], axis=1).max(axis=1) / c.shift(1)
    a5, a20 = r_(5), r_(20)
    atr_ratio = tr.ewm(span=a5, min_periods=a5).mean() / tr.ewm(span=a20, min_periods=a20).mean()
    k5, k10 = r_(5), r_(10)
    z5 = np.log(c / c.shift(k5)) / (vol * np.sqrt(k5))
    z10 = np.log(c / c.shift(k10)) / (vol * np.sqrt(k10))
    hw = r_(20)
    near_hi = np.log(h.rolling(hw, min_periods=hw).max() / c) / vol
    fw = r_(20)
    fade_top = z5.rolling(fw, min_periods=max(2, fw // 2)).max() - z5
    up10 = up.rolling(r_(10)).sum()
    dn10 = dn.rolling(r_(10)).sum()
    ac = lr.abs()
    shrink = ac.rolling(r_(3)).mean() / ac.rolling(r_(15)).mean()
    return pd.DataFrame({"cu": cu, "cd": cd, "atr_ratio": atr_ratio, "z5": z5, "z10": z10, "near_hi": near_hi,
                         "fade_top": fade_top, "up10": up10, "dn10": dn10, "shrink": shrink}, index=df.index)


def td_setup_p(df, lb=4):
    c = df.c.to_numpy(float)
    n = len(c)
    ss, bs = np.zeros(n), np.zeros(n)
    for t in range(lb, n):
        ss[t] = ss[t - 1] + 1 if c[t] > c[t - lb] else 0
        bs[t] = bs[t - 1] + 1 if c[t] < c[t - lb] else 0
    return pd.DataFrame({"td_ss": ss, "td_bs": bs}, index=df.index)


def swing_state_p(df, mult=1.5):
    """cand_exhaust.swing_state をそのまま呼ぶ。物差し θ の倍率だけ変えたいときは L.swing_threshold を一時的に差し替える
    （特徴量の計算中だけ。正解ラベルと評価は標準の ZigZag のまま）"""
    if mult == L.ZZ_MULT:
        return X.swing_state(df)
    orig = L.swing_threshold
    try:
        L.swing_threshold = lambda d, mult_=mult, **kw: orig(d, mult=mult_)
        return X.swing_state(df)
    finally:
        L.swing_threshold = orig


def features_p(df, cfg):
    F = pd.concat([swing_state_p(df, cfg["theta_mult"]), td_setup_p(df, cfg["td_lb"]),
                   exhaust_feats_p(df, cfg["vol_span"], cfg["win"])], axis=1)
    s = cfg["clip"]
    for k, (a, b) in X.CLIP.items():
        lo = a / s if a > 0 else a * s
        F[k] = F[k].clip(lo, b * s)
    return F


BASE_CFG = {"rate": X.TARGET_RATE, "c_mult": 1.0, "knots": 4, "horizon": X.HORIZON, "clip": 1.0,
            "theta_mult": L.ZZ_MULT, "vol_span": 60, "win": 1.0, "td_lb": 4, "p50_mult": 1.0}


def fit_cfg(cfg):
    d = DATA["nasdaq3x"].loc[:TRAIN[1]]
    piv = L.pivots(d)                       # 正解は常に標準の ZigZag（train 末尾で切ったデータ）
    m = L.period_mask(d, TRAIN)
    hz = cfg["horizon"]
    tg = L.targets(piv, len(d), ks=(hz,))
    F = features_p(d, cfg)
    models = {}
    for cand in ("score", "score2"):
        for side in ("top", "bot"):
            cols, C = X.SPECS[cand][side]["cols"], X.SPECS[cand][side]["C"] * cfg["c_mult"]
            y = tg[f"{side}_{hz}"]
            Xm = F[cols].to_numpy(float)
            ok = m & ~np.isnan(y) & ~np.isnan(Xm).any(axis=1)
            mdl = make_pipeline(SplineTransformer(n_knots=cfg["knots"], degree=3, extrapolation="constant"),
                                StandardScaler(), LogisticRegression(C=C, max_iter=5000)).fit(Xm[ok], y[ok].astype(int))
            p = X.predict(mdl, Xm)
            p50, rate = X.calibrate(p, m, target=cfg["rate"])
            models[(cand, side)] = (mdl, cols, p50 * cfg["p50_mult"])
    return models


def score_cfg(models, cfg, df, cand):
    F = features_p(df, cfg)
    return pd.DataFrame({side: X.to_score(X.predict(models[(cand, side)][0], F[models[(cand, side)][1]].to_numpy(float)),
                                          models[(cand, side)][2]) for side in ("top", "bot")}, index=df.index)


SENS = [("base", {}),
        ("target_rate x0.75", {"rate": 7.0 * 0.75}), ("target_rate x1.25", {"rate": 7.0 * 1.25}),
        ("C x0.7", {"c_mult": 0.7}), ("C x1.3", {"c_mult": 1.3}),
        ("n_knots 3", {"knots": 3}), ("n_knots 5", {"knots": 5}),
        ("horizon 7", {"horizon": 7}), ("horizon 13", {"horizon": 13}),
        ("clip x0.75", {"clip": 0.75}), ("clip x1.25", {"clip": 1.25}),
        ("theta x0.8 (feature ZigZag 1.2)", {"theta_mult": 1.2}), ("theta x1.2 (feature ZigZag 1.8)", {"theta_mult": 1.8}),
        ("vol_span 45", {"vol_span": 45}), ("vol_span 75", {"vol_span": 75}),
        ("windows x0.75", {"win": 0.75, "td_lb": 3}), ("windows x1.25", {"win": 1.25, "td_lb": 5}),
        ("p50 x0.75 (no refit)", {"p50_mult": 0.75}), ("p50 x1.25 (no refit)", {"p50_mult": 1.25})]


def part_sens(quick=False):
    out = {"rows": [], "base_equals_original": {}}
    evals = [("nasdaq3x", "test"), ("sp3x_close", "oos2019"), ("sp3x", "check_post")]
    cache = {}
    for label, upd in (SENS[:3] if quick else SENS):
        cfg = dict(BASE_CFG, **upd)
        key = tuple(sorted((k, v) for k, v in cfg.items() if k != "p50_mult"))
        models = fit_cfg(cfg)
        for cand in ("score", "score2"):
            for name, pname in evals:
                df = DATA[name]
                sc = score_cfg(models, cfg, df, cand)
                if label == "base":
                    orig = FNS[cand](df)[["top", "bot"]].to_numpy(float)
                    out["base_equals_original"][f"{cand}|{name}"] = float(np.max(np.abs(sc.to_numpy(float) - orig)))
                r = L.evaluate(sc, df, PIVS[name], period(name, pname))
                for side in ("top", "bot"):
                    row = {"config": label, "cand": cand, "set": f"{name}/{pname}", "side": side,
                           "p50": models[(cand, side)][2]}
                    row.update({k: fnum(r[side][k]) for k in KEYS})
                    out["rows"].append(row)
        print(f"  sens {label} done", flush=True)
    R = pd.DataFrame(out["rows"])
    out["table"] = R.round(4).to_dict(orient="records")
    return out


# ================================================================ 7. 点灯回数を揃えた比較（score vs RSI）
def part_curve(quick=False):
    out = {}
    fit = X.fitted()
    rates = (1.5, 2.5, 4.0, 5.5, 7.0, 8.5)
    for name, pname in [("nasdaq3x", "test"), ("sp3x_close", "oos2019"), ("sp3x", "check_post"), ("sp3x_close", "pre1999")]:
        df, m, piv = DATA[name], period(name, pname), PIVS[name]
        F = X.features(df)
        r = L.rsi(df.c).to_numpy()
        yrs = m.sum() / 252
        for side, sgn in (("top", 1), ("bot", -1)):
            curves = {}
            for cand in ("score", "score2"):
                f = fit[cand][side]
                p = X.predict(f["model"], F[f["cols"]].to_numpy(float))
                qs = np.unique(np.quantile(p[m & ~np.isnan(p)], np.linspace(0.5, 0.9995, 120 if not quick else 30)))
                curves[cand] = [(X.to_score(p, q), q) for q in qs]
            lv = np.arange(50, 95.01, 0.5) if sgn > 0 else np.arange(50, 5, -0.5)
            curves["rsi"] = [(np.nan_to_num(np.clip(50 + sgn * 2.5 * (r - x), 0, 100)), x) for x in lv]
            res = {}
            for nm, cv in curves.items():
                pts = []
                for s, th in cv:
                    S = pd.DataFrame({"top": s if side == "top" else 0.0, "bot": s if side == "bot" else 0.0}, index=df.index)
                    e = L.evaluate(S, df, piv, m)[side]
                    pts.append((e["signals_per_year"], e["precision"], e["recall_pre"], e["lead_med"], e["remain_med"], th))
                pts = np.array(pts, float)
                rr = {}
                for tr in rates:
                    j = int(np.nanargmin(np.abs(pts[:, 0] - tr)))
                    rr[str(tr)] = {"rate": pts[j, 0], "precision": pts[j, 1], "recall_pre": pts[j, 2],
                                   "lead_med": pts[j, 3], "remain_med": pts[j, 4], "threshold": pts[j, 5]}
                res[nm] = rr
            out[f"{name}/{pname}|{side}"] = res
            print(f"  curve {name}/{pname} {side}: " + " | ".join(
                f"{nm}: " + " ".join(f"{k}/yr→{v['rate']:.1f}:{v['precision']:.2f},{v['recall_pre']:.2f}"
                                     for k, v in res[nm].items() if k in ("2.5", "4.0", "7.0")) for nm in res), flush=True)
    return out


# ================================================================ 8. 点灯後の騰落と時刻ずらし帰無
def part_fwd(quick=False):
    n = 60 if quick else 300
    out = {}
    for fname in ("score", "score2", "rsi_baseline", "rsi_matched"):
        for name, pname in [("nasdaq3x", "test"), ("sp3x", "check_post"), ("sp3x_close", "pre1999"),
                            ("sp3x_close", "oos2019"), ("nasdaq3x", "train")]:
            df, m = DATA[name], period(name, pname)
            c = df.c.to_numpy(float)
            fr = np.full(len(c), np.nan)
            fr[:-10] = np.log(c[10:] / c[:-10]) * 100
            sc = FNS[fname](df)
            seg = np.flatnonzero(m)
            a, b = seg[0], seg[-1] + 1
            rng = np.random.default_rng(5)
            res = {"all_mean": float(np.nanmean(fr[m]))}
            for side in ("top", "bot"):
                x = np.nan_to_num(sc[side].to_numpy(float))

                def mean_after(xx):
                    sig = L.crossings_up(xx)
                    sig = sig[m[sig]]
                    v = fr[sig]
                    v = v[~np.isnan(v)]
                    return (float(v.mean()) if len(v) else np.nan), len(v)
                real, cnt = mean_after(x)
                null = []
                for _ in range(n):
                    xx = x.copy()
                    xx[a:b] = np.roll(xx[a:b], int(rng.integers(60, b - a - 60)))
                    null.append(mean_after(xx)[0])
                null = np.array(null, float)
                # 天井側は「点灯後に下がる」ほど良い → p = 帰無が実測以下の割合。底側は逆
                p = float(np.mean(null <= real)) if side == "top" else float(np.mean(null >= real))
                res[side] = {"n": cnt, "mean": real, "null_median": float(np.nanmedian(null)), "p_better": p}
            out[f"{fname}|{name}/{pname}"] = res
            print(f"  fwd {fname:12s} {name}/{pname}: all {res['all_mean']:+.2f} | top {res['top']['mean']:+.2f} "
                  f"(null {res['top']['null_median']:+.2f}, p {res['top']['p_better']:.2f}) | bot {res['bot']['mean']:+.2f} "
                  f"(null {res['bot']['null_median']:+.2f}, p {res['bot']['p_better']:.2f})", flush=True)
    return out


# ================================================================ 9. 帰無モデルの妥当性（転換点の統計が実データに近いか）
def part_garch_diag(quick=False):
    n = 10 if quick else 40
    out = {}
    for name, pname, close_only in (("nasdaq3x", "test", False), ("sp3x_close", "oos2019", True),
                                    ("sp3x_close", "pre1999", True)):
        G = garch_setup(name)
        df, m = DATA[name], period(name, pname)
        rows = {"real": L.leg_stats(df, PIVS[name], m)}
        rng = np.random.default_rng(21)
        for kind, gen in (("garch", lambda: garch_path(G, df, m, rng, close_only)),
                          ("rw", lambda: X.shuffled(df, m, rng))):
            acc = {"H": [], "L": []}
            for _ in range(n):
                sdf = gen()
                st = L.leg_stats(sdf, L.pivots(sdf), m)
                for k in acc:
                    acc[k].append(st[k])
            rows[kind] = {k: {f: float(np.median([a[f] for a in v])) for f in v[0]} for k, v in acc.items()}
        # 日次の値動きの性質: |r| の自己相関（変動率の偏り）、r と翌日 |r| の相関（下げで変動率が上がる）
        def dyn(c):
            r = np.diff(np.log(c))
            a = np.abs(r)
            return {"acf_abs_lag1_20": float(np.mean([np.corrcoef(a[:-k], a[k:])[0, 1] for k in range(1, 21)])),
                    "corr_r_next_abs": float(np.corrcoef(r[:-1], a[1:])[0, 1]),
                    "acf_r_lag1": float(np.corrcoef(r[:-1], r[1:])[0, 1])}
        seg = np.flatnonzero(m)
        rows["dyn_real"] = dyn(df.c.to_numpy()[seg[0] - 1:seg[-1] + 1])
        rng = np.random.default_rng(22)
        rows["dyn_garch"] = {k: float(np.median([dyn(garch_path(G, df, m, rng, close_only).c.to_numpy()[seg[0] - 1:seg[-1] + 1])[k]
                                                 for _ in range(10)])) for k in ("acf_abs_lag1_20", "corr_r_next_abs", "acf_r_lag1")}
        rows["dyn_rw"] = {k: float(np.median([dyn(X.shuffled(df, m, rng).c.to_numpy()[seg[0] - 1:seg[-1] + 1])[k]
                                              for _ in range(10)])) for k in ("acf_abs_lag1_20", "corr_r_next_abs", "acf_r_lag1")}
        rows["garch_params"] = G["params"]
        out[f"{name}/{pname}"] = rows
        print(f"  garch_diag {name}/{pname}: " + json.dumps(clean(rows), ensure_ascii=False)[:1500], flush=True)
    return out


# ================================================================ 10. AUC の差（score − 素の RSI）のブロック・ブートストラップ
def part_aucdiff(quick=False):
    reps = 200 if quick else 2000
    out = {}
    for name, pname in [("nasdaq3x", "test"), ("sp3x", "check_post"), ("sp3x_close", "oos2019"), ("sp3x_close", "pre1999")]:
        df, m = DATA[name], period(name, pname)
        tg = L.targets(PIVS[name], len(df))
        r = L.rsi(df.c).to_numpy()
        sc = {f: FNS[f](df) for f in ("score", "score2")}
        for side, sgn in (("top", 1), ("bot", -1)):
            y = tg[f"{side}_10"]
            idx = np.flatnonzero(m & ~np.isnan(y) & ~np.isnan(r))
            rng = np.random.default_rng(3)
            B = 63
            nb = int(np.ceil(len(idx) / B))
            res = {}
            for f in ("score", "score2"):
                s = sc[f][side].to_numpy(float)
                d0 = roc_auc_score(y[idx], s[idx]) - roc_auc_score(y[idx], sgn * r[idx])
                ds = []
                for _ in range(reps):
                    starts = rng.integers(0, len(idx) - B, nb)
                    j = idx[(starts[:, None] + np.arange(B)[None, :]).ravel()[:len(idx)]]
                    if 0 < y[j].mean() < 1:
                        ds.append(roc_auc_score(y[j], s[j]) - roc_auc_score(y[j], sgn * r[j]))
                ds = np.array(ds)
                res[f] = {"auc_score": float(roc_auc_score(y[idx], s[idx])), "auc_raw_rsi": float(roc_auc_score(y[idx], sgn * r[idx])),
                          "diff": float(d0), "ci95": [float(np.percentile(ds, 2.5)), float(np.percentile(ds, 97.5))],
                          "p_diff_le_0": float(np.mean(ds <= 0))}
            out[f"{name}/{pname}|{side}"] = res
            print(f"  aucdiff {name}/{pname} {side}: " + " ".join(
                f"{f}: {v['auc_score']:.3f}-{v['auc_raw_rsi']:.3f}={v['diff']:+.3f} CI[{v['ci95'][0]:+.3f},{v['ci95'][1]:+.3f}]"
                for f, v in res.items()), flush=True)
    return out


# ================================================================ 11. ZigZag の状態だけの指標（幾何だけでどこまで行くか）
def zz_state_only(df):
    """確定済みの最新転換点が底なら top=100、天井なら bot=100（それ以外 0）。値動きの情報は一切使わない"""
    _, lk, _ = L.last_confirmed(L.pivots(df), len(df))
    return pd.DataFrame({"top": np.where(lk == -1, 100.0, 0.0), "bot": np.where(lk == 1, 100.0, 0.0)}, index=df.index)


def zz_state_drawdown(df):
    """ZigZag の状態＋今の脚の進み（R_up / R_dn）だけ。θ の 1 倍で 50、2 倍で 100（学習なし）"""
    S = X.swing_state(df)
    up = np.where(S.kind.to_numpy() == -1, S.R_up.to_numpy(), 0.0)
    dn = np.where(S.kind.to_numpy() == 1, S.R_dn.to_numpy(), 0.0)
    return pd.DataFrame({"top": np.clip(np.nan_to_num(up) * 50, 0, 100), "bot": np.clip(np.nan_to_num(dn) * 50, 0, 100)},
                        index=df.index)


def part_zzstate(quick=False):
    out = {}
    for fname, fn in (("zz_state_only", zz_state_only), ("zz_state_drawdown", zz_state_drawdown)):
        res = L.run_all(fn)
        for (name, pname), r in res.items():
            for side in ("top", "bot"):
                out[f"{fname}|{name}/{pname}|{side}"] = {k: fnum(r[side][k]) for k in KEYS}
        print(f"  {fname}:")
        print(L.summary_table(res).round(3).to_string(), flush=True)
    return out


# ================================================================ 12. train 内の主張（CV・脚のハザード・下降脚の振幅）の再計算
def part_traincv(quick=False):
    out = {"train_cv": {c: X.train_cv(c) for c in ("score", "score2", "rsi_matched")}}
    d, piv, tg, m = X.train_data()
    pb, pk, pp = piv.bar.to_numpy(), piv.kind.to_numpy(), piv.price.to_numpy()
    pct = L.swing_threshold(d)
    legs = [(pk[j], pb[j] - pb[j - 1], abs(pp[j] / pp[j - 1] - 1) / pct[pb[j - 1]]) for j in range(1, len(piv)) if m[pb[j]]]
    for kind, nm in (("H", "up_leg(ends at top)"), ("L", "down_leg(ends at bottom)")):
        dur = np.array([x[1] for x in legs if x[0] == kind])
        amp = np.array([x[2] for x in legs if x[0] == kind])
        haz = {}
        for a in (0, 5, 10, 15, 20, 30, 40, 60):
            s = dur >= a
            if s.sum() >= 5:
                haz[str(a)] = [int(s.sum()), float(np.mean(dur[s] <= a + 10))]
        out[nm] = {"n": int(len(dur)), "hazard_end_within10_given_age": haz,
                   "amp_theta_p10_p90": [float(np.percentile(amp, 10)), float(np.percentile(amp, 90))]}
    print("  " + json.dumps(clean(out), ensure_ascii=False)[:3000], flush=True)
    return out


# ================================================================ 13. 検証後の数字の表（保存済みの JSON から組み立てるだけ）
def part_table(quick=False):
    S = json.load(open(OUT))
    rows = []
    for fname in ("score", "score2", "rsi_baseline"):
        for name, pname in MAIN + [("sp3x", "check_post"), ("sp3x_close", "pre1999")]:
            for side in ("top", "bot"):
                r = S["repro"]["results"][f"{fname}|{name}/{pname}|{side}"]
                cn = S["null"][f"{fname}|{name}/{pname}"][side]
                rw = S.get("rw", {}).get(f"{fname}|{name}/{pname}") or S.get("rw_check", {}).get(f"{fname}|{name}/{pname}")
                tag = f"{name}/{pname}|" + ("close_only" if name == "sp3x_close" else "ohlc")
                ga = S.get("garch", {}).get(f"{fname}|{tag}") or S.get("garch_check", {}).get(f"{fname}|{tag}")
                row = {"cand": fname, "set": f"{name}/{pname}", "side": side, "recall_pre": r["recall_pre"],
                       "lead_med": r["lead_med"], "remain_med": r["remain_med"], "precision": r["precision"],
                       "auc10": r["auc10"], "sig/yr": r["signals_per_year"],
                       "p_circ(rec/prec/auc)": "/".join(f"{cn[k][2]:.3f}" for k in ("recall_pre", "precision", "auc10")),
                       "p_rw(prec/auc)": "/".join(f"{rw[side][k][2]:.2f}" for k in ("precision", "auc10")) if rw else "-",
                       "p_garch(prec/auc)": "/".join(f"{ga[side][k][2]:.2f}" for k in ("precision", "auc10")) if ga else "-"}
                rows.append(row)
    T = pd.DataFrame(rows)
    with pd.option_context("display.width", 250, "display.max_rows", 200):
        print(T.round(3).to_string(index=False))
    return {"rows": rows}


PARTS = {"causal": part_causal, "repro": part_repro, "traincv": part_traincv, "null": part_null, "rw": part_rw,
         "rw_check": lambda quick=False: part_rw(quick, cases=(("sp3x", "check"), ("sp3x", "check_post"))),
         "garch": part_garch,
         "garch_cond": lambda quick=False: part_garch(quick, cond=True),
         "garch_check": lambda quick=False: part_garch(quick, cases=[("sp3x", "check", False), ("sp3x", "check_post", False)]),
         "garch_diag": part_garch_diag, "zzstate": part_zzstate, "aucdiff": part_aucdiff,
         "sens": part_sens, "curve": part_curve, "fwd": part_fwd,
         "table": part_table}   # table は保存済みの結果から表を作るだけなので最後


def save_part(p, value, seconds):
    """部分ごとに results/verify_exhaust.json へマージ（複数プロセスで並行実行しても壊れないようにロック）"""
    import fcntl
    import tempfile
    OUT.parent.mkdir(exist_ok=True)
    with open(Path(tempfile.gettempdir()) / "verify_exhaust.lock", "w") as lk:
        fcntl.flock(lk, fcntl.LOCK_EX)
        store = json.load(open(OUT)) if OUT.exists() else {}
        store[p] = value
        store[p + "_seconds"] = seconds
        tmp = OUT.with_suffix(".tmp")
        with open(tmp, "w") as fh:
            json.dump(store, fh, ensure_ascii=False, indent=1)
        tmp.replace(OUT)
        fcntl.flock(lk, fcntl.LOCK_UN)


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    quick = "--quick" in sys.argv
    parts = args or list(PARTS)
    for p in parts:
        t0 = time.time()
        print(f"==== {p}", flush=True)
        value = clean(PARTS[p](quick))
        save_part(p, value, round(time.time() - t0, 1))
        print(f"==== {p} done ({time.time() - t0:.0f}s)", flush=True)


if __name__ == "__main__":
    main()
