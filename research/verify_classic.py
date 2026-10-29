"""cand_classic（score = TL-Blend / score2 = TL-Classic3）の反証検証  key: classic

python3 verify_classic.py                    # 全部（数分）
python3 verify_classic.py causal repro null  # 一部だけ（results/verify_classic.json にマージ）
  audit  : ソースの静的走査 / --fit の再計算と CONST の一致 / 学習期間より後のデータを差し替えたときの定数の変化
           （正解ラベルの境界漏れの大きさ）と、境界を除いて学習し直したときの test 成績
  causal : L.check_causal(n_cuts=30, start=0.3/0.7。nasdaq3x は 0.65 も) / 未来差し替え検査（cut より後を別の値動きに
           置き換えても cut までの全バーの値が変わらないか）/ pandas を使わない numpy ループでの独立実装との一致
  repro  : run_all（score, score2, L.baseline_rsi, RSI14 同頻度, L.ideal）を再実行して results/classic.json と照合。
           指標（AUC10・的中率・事前点灯率・何本前）を自前の実装でも計算して照合。sp3x/check を学習と同時期/以後に分割
  null   : L.null_test（循環シフト, n=300, seed=1）
  paired : AUC10 差の循環ブロック・ブートストラップ（63 本, B=2000, seed=1）: vs RSI14 / vs 部品単体 / Blend vs Classic3
  timing : 「いま上げ脚か下げ脚か」だけの基準（last_confirmed）/ 脚の中での AUC（タイミングの力）/
           上げ脚の中の基準率 / 同じ点灯回数（期間内で揃える）での的中率・事前点灯率
  sens   : 窓長・変動率 span・C・点灯目標・25 の分位・ラベル幅を ±20〜30%、係数ノイズ、1 特徴抜き → train で学習し直して
           test / check / pre1999 / oos2019 の崩れ方
  smooth : EMA 平滑 1/2/3/5 の AUC となだらかさ（train で決めた目盛り）
  fwd    : 「そろそろ」点灯後 10/20 本の騰落（3 倍近似の終値）と循環シフト帰無
  table  : 検証後の数字の表を表示
cand_classic.py / turnline_lab.py は import するだけで編集しない。
"""
import fcntl
import json
import re
import sys
import time
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.preprocessing import StandardScaler

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import turnline_lab as L  # noqa: E402
import cand_classic as C  # noqa: E402

warnings.filterwarnings("ignore")
OUT = HERE / "results" / "verify_classic.json"
REPORTED = HERE / "results" / "classic.json"
TRAIN = L.SETS["nasdaq3x"][1]["train"]
EXTRA = {"sp3x": {"check_overlap": ("1999-07-01", "2010-12-31"), "check_post": ("2011-01-01", "2018-12-31")}}
PERIODS = [("nasdaq3x", "train"), ("nasdaq3x", "test"), ("sp3x", "check"), ("sp3x_close", "pre1999"),
           ("sp3x_close", "oos2019")]
OOS = [("nasdaq3x", "test"), ("sp3x", "check"), ("sp3x_close", "pre1999"), ("sp3x_close", "oos2019")]
KEYS = ("n_pivots", "recall_pre", "recall_late", "lead_med", "lead_q1", "lead_q3", "remain_med", "signals_per_year",
        "precision", "precision_lenient", "auc5", "auc10", "ap10", "base10", "lit_frac")

DATA = {name: L.load(name) for name in L.SETS}
PIVS = {name: L.pivots(df) for name, df in DATA.items()}
TG = {name: L.targets(PIVS[name], len(df)) for name, df in DATA.items()}


def mask_of(name, pname):
    per = L.SETS[name][1].get(pname) or EXTRA[name][pname]
    return L.period_mask(DATA[name], per)


TRM = mask_of("nasdaq3x", "train")
TRY = TRM.sum() / 252


def fnum(v):
    try:
        v = float(v)
    except (TypeError, ValueError):
        return v
    return v if np.isfinite(v) else None


def clean(o):
    if isinstance(o, dict):
        return {str(k): clean(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [clean(v) for v in o]
    if isinstance(o, (np.floating, float, np.integer)):
        return fnum(o)
    if isinstance(o, np.ndarray):
        return clean(o.tolist())
    return o


def save_part(p, value, seconds):
    OUT.parent.mkdir(exist_ok=True)
    with open(str(OUT) + ".lock", "w") as lk:
        fcntl.flock(lk, fcntl.LOCK_EX)
        store = json.load(open(OUT)) if OUT.exists() else {}
        store[p] = clean(value)
        store.setdefault("_seconds", {})[p] = round(seconds, 1)
        json.dump(store, open(OUT, "w"), ensure_ascii=False, indent=1)


def logistic(raw, th, s):
    return 100 / (1 + np.exp(-np.clip((np.asarray(raw, float) - th) / s, -60, 60)))


# ------------------------------------------------------------------ 基準: RSI14 を候補と同じ方式で train の点灯 年7.5回に
_R14 = (L.rsi(DATA["nasdaq3x"].c, 14) - 50).to_numpy()
RSI_CAL = {side: C._calibrate(sg * _R14, TRM, TRY)[:2] for side, sg in (("top", 1), ("bot", -1))}


def rsi_rm(df):
    r = (L.rsi(df.c, 14) - 50).to_numpy()
    return pd.DataFrame({side: np.nan_to_num(logistic(sg * r, *RSI_CAL[side])) for side, sg in (("top", 1), ("bot", -1))},
                        index=df.index)


FNS = {"score": C.score, "score2": C.score2, "rsi14_rm": rsi_rm, "baseline_rsi": L.baseline_rsi}
_SC_CACHE = {}


def sc(fname, name):
    k = (fname, name)
    if k not in _SC_CACHE:
        _SC_CACHE[k] = L.ideal(DATA[name], PIVS[name]) if fname == "ideal" else FNS[fname](DATA[name])
    return _SC_CACHE[k]


def ev(score_df, name, pname):
    return L.evaluate(score_df, DATA[name], PIVS[name], mask_of(name, pname))


def pick(e):
    return {s: {k: fnum(e[s][k]) for k in KEYS} for s in ("top", "bot")}


# ================================================================== audit
def part_audit(quick=False):
    out = {}
    src = (HERE / "cand_classic.py").read_text().splitlines()
    pats = {"shift(-": r"shift\(\s*-", "bfill/backfill": r"bfill|backfill|fillna\(method", "center=True": r"center\s*=\s*True",
            "pivots/last_confirmed/targets": r"pivots\(|last_confirmed|targets\(", "quantile": r"quantile",
            "全体の mean/std": r"\.mean\(|\.std\(", "iloc/[-": r"iloc\[|\[-1\]", "period_mask": r"period_mask"}
    hits = {}
    for k, p in pats.items():
        hits[k] = [f"{i + 1}: {ln.strip()[:120]}" for i, ln in enumerate(src) if re.search(p, ln)]
    out["static_scan"] = hits
    print("[audit] static scan")
    for k, v in hits.items():
        print(f"  {k}: {len(v)}")
        for x in v:
            print("     ", x)

    # --fit の再計算と CONST の一致
    fit = C.fit_constants()
    md = 0.0
    for g in ("blend", "classic"):
        for s in ("top", "bot"):
            for k, v in C.CONST[g][s].items():
                if k != "cols":
                    md = max(md, float(np.max(np.abs(np.asarray(fit[g][s][k], float) - np.asarray(v, float)))))
    out["refit_vs_CONST_maxdiff"] = md
    print("[audit] refit vs CONST max diff:", md)

    # 学習期間より後のデータ（2011 以降）を別の値動きに差し替えて学習し直す → 定数が変わるか（ラベルの境界漏れ）
    df0 = DATA["nasdaq3x"]
    end = np.flatnonzero(TRM)[-1]
    rng = np.random.default_rng(7)
    alt = df0.copy()
    k = len(df0) - end - 1
    fac = np.exp(np.cumsum(rng.normal(0, 0.03, k)))
    for col in ("o", "h", "l", "c"):
        alt.iloc[end + 1:, alt.columns.get_loc(col)] = df0[col].iat[end] * fac * (df0[col].iloc[end + 1:].to_numpy() /
                                                                                   df0.c.iloc[end + 1:].to_numpy())
    orig_load = L.load
    try:
        L.load = lambda name: alt if name == "nasdaq3x" else orig_load(name)
        fit_alt = C.fit_constants()
    finally:
        L.load = orig_load
    diffs = {}
    for g in ("blend", "classic"):
        for s in ("top", "bot"):
            diffs[f"{g}/{s}"] = {kk: float(np.max(np.abs(np.asarray(fit_alt[g][s][kk], float) - np.asarray(v, float))))
                                 for kk, v in C.CONST[g][s].items() if kk != "cols"}
    out["post_train_swap_const_diff"] = diffs
    print("[audit] post-train data swapped -> const diff:", json.dumps(clean(diffs))[:600])

    # 学習期間の中で「正解ラベルが学習期間後のデータで決まる」行の数
    piv_tr = L.pivots(df0.iloc[:end + 1])  # 学習期間末までのデータだけで確定した転換点
    last_bar = int(piv_tr.bar.iloc[-1])
    piv_full = PIVS["nasdaq3x"]
    same = piv_full.iloc[:len(piv_tr)][["bar", "kind", "confirm"]].reset_index(drop=True).equals(
        piv_tr[["bar", "kind", "confirm"]].reset_index(drop=True))
    leak_rows = int(TRM[last_bar + 1:].sum())
    out["train_label_boundary"] = {"last_pivot_confirmed_in_train": str(df0.index[last_bar].date()),
                                   "rows_with_label_from_post_train": leak_rows, "train_rows": int(TRM.sum()),
                                   "pivots_online_consistent": bool(same)}
    print("[audit] label boundary:", out["train_label_boundary"])

    # 境界の行を除いて学習し直す → test などの成績が変わるか
    tg = TG["nasdaq3x"]
    purge = TRM.copy()
    purge[last_bar + 1:] = False
    res = {}
    for side in ("top", "bot"):
        y = tg[f"{side}_10"]
        rows = np.flatnonzero(purge & ~np.isnan(y))
        X = C.features(df0, C.BLEND_COLS[side]).to_numpy(float)
        scl = StandardScaler().fit(X[rows])
        lr = LogisticRegression(C=0.05, max_iter=3000).fit(scl.transform(X[rows]), y[rows])
        c = {"cols": C.BLEND_COLS[side], "mean": scl.mean_.tolist(), "scale": scl.scale_.tolist(),
             "coef": lr.coef_[0].tolist(), "intercept": float(lr.intercept_[0])}
        th, s, spy = C._calibrate(C.blend_raw(df0, side, c), TRM, TRY)
        c.update(theta=th, s=s)
        res[side] = {"coef_maxdiff": float(np.max(np.abs(np.array(c["coef"]) - np.array(C.CONST["blend"][side]["coef"])))),
                     "theta_diff": th - C.CONST["blend"][side]["theta"], "const": c}
    out["purged_refit"] = {s: {k: v for k, v in res[s].items() if k != "const"} for s in res}

    def purged_score(df):
        return pd.DataFrame({s: logistic(C.blend_raw(df, s, res[s]["const"]), res[s]["const"]["theta"], res[s]["const"]["s"])
                             for s in ("top", "bot")}, index=df.index)

    pr = {}
    for name, pname in OOS:
        e = ev(purged_score(DATA[name]), name, pname)
        b = ev(sc("score", name), name, pname)
        pr[f"{name}/{pname}"] = {s: {k: (fnum(e[s][k]), fnum(b[s][k])) for k in ("auc10", "precision", "recall_pre")}
                                 for s in ("top", "bot")}
    out["purged_refit_oos(purged, original)"] = pr
    print("[audit] purged refit:", json.dumps(clean(out["purged_refit"])))
    print("[audit] purged refit oos (purged, original):", json.dumps(clean(pr))[:900])
    return out


# ================================================================== causal
def ewm_std_adjust(x, span, minp):
    a = 2.0 / (span + 1.0)
    out = np.full(len(x), np.nan)
    for t in range(1, len(x)):
        v = x[1:t + 1]
        if len(v) < minp:
            continue
        w = (1 - a) ** np.arange(len(v) - 1, -1, -1)
        sw, sw2 = w.sum(), (w * w).sum()
        mu = (w * v).sum() / sw
        out[t] = np.sqrt((w * (v - mu) ** 2).sum() / sw * sw * sw / (sw * sw - sw2))
    return out


def ema_rec(x, alpha):
    out = np.full(len(x), np.nan)
    y = np.nan
    for i, v in enumerate(x):
        if not np.isnan(v):
            y = v if np.isnan(y) else (1 - alpha) * y + alpha * v
        out[i] = y
    return out


def rsi_loop(c, n):
    d = np.r_[np.nan, np.diff(c)]
    up = ema_rec(np.where(np.isnan(d), np.nan, np.maximum(d, 0)), 1.0 / n)
    dn = ema_rec(np.where(np.isnan(d), np.nan, np.maximum(-d, 0)), 1.0 / n)
    with np.errstate(divide="ignore", invalid="ignore"):
        return 100 - 100 / (1 + up / dn)


def roll(x, n, f, minp):
    out = np.full(len(x), np.nan)
    for i in range(len(x)):
        a = max(0, i - n + 1)
        if i - a + 1 >= minp:
            out[i] = f(x[a:i + 1])
    return out


def indep_scores(df):
    """候補の説明文どおりの式を、各バーで過去の値だけを見るループで書き直したもの（pandas 不使用）"""
    c, h, l = df.c.to_numpy(float), df.h.to_numpy(float), df.l.to_numpy(float)
    lc = np.log(c)
    dv = ewm_std_adjust(np.r_[np.nan, np.diff(lc)], 60, 20)
    F = {}
    for n in (5, 7, 14):
        F[f"rsi{n}"] = rsi_loop(c, n) - 50
    for n in (10, 14, 21, 60):
        hh, ll = roll(h, n, np.max, n), roll(l, n, np.min, n)
        with np.errstate(divide="ignore", invalid="ignore"):
            F[f"stoch{n}"] = np.where(hh - ll == 0, np.nan, 100 * (c - ll) / (hh - ll)) - 50
    for n in (10, 20, 50, 100):
        F[f"z{n}"] = (lc - ema_rec(lc, 2.0 / (n + 1))) / (dv * np.sqrt(n))
    F["rise60"] = np.log(c / roll(l, 60, np.min, 1)) / (dv * np.sqrt(10))
    F["trend200"] = (lc - roll(lc, 200, np.mean, 100)) / dv
    m = (ema_rec(lc, 2 / 13) - ema_rec(lc, 2 / 27)) / dv
    F["macdh"] = m - ema_rec(m, 2 / 10)
    F = {k: np.nan_to_num(v, nan=0.0, posinf=0.0, neginf=0.0) for k, v in F.items()}
    out = {}
    for side in ("top", "bot"):
        cb = C.CONST["blend"][side]
        X = np.column_stack([F[k] for k in cb["cols"]])
        out[("score", side)] = logistic(cb["intercept"] + ((X - cb["mean"]) / np.array(cb["scale"])) @ np.array(cb["coef"]),
                                        cb["theta"], cb["s"])
        cc = C.CONST["classic"][side]
        X2 = np.column_stack([F[k] for k in cc["cols"]])
        out[("score2", side)] = logistic((1 if side == "top" else -1) * ((X2 - cc["mean"]) / np.array(cc["sd"])).mean(1),
                                         cc["theta"], cc["s"])
    return out


def future_swap(fn, df, cuts, seed=0):
    """cut より後の値動きを乱数の値動きに置き換えても、cut までの全バーの値が変わらないか（最大差）"""
    full = fn(df)[["top", "bot"]].to_numpy(float)
    rng = np.random.default_rng(seed)
    worst = 0.0
    for cut in cuts:
        alt = df.copy()
        k = len(df) - cut - 1
        fac = np.exp(np.cumsum(rng.normal(0, 0.04, k)))
        for col in ("o", "h", "l", "c"):
            alt.iloc[cut + 1:, alt.columns.get_loc(col)] = df.c.iat[cut] * fac * rng.uniform(0.97, 1.03, k)
        alt["h"] = alt[["o", "h", "l", "c"]].max(axis=1)
        alt["l"] = alt[["o", "h", "l", "c"]].min(axis=1)
        part = fn(alt)[["top", "bot"]].to_numpy(float)[:cut + 1]
        d = np.abs(part - full[:cut + 1])
        if (np.isnan(part) != np.isnan(full[:cut + 1])).any():
            return float("inf")
        worst = max(worst, float(np.nanmax(d)))
    return worst


def part_causal(quick=False):
    out = {"check_causal": {}, "future_swap": {}, "indep_impl_maxdiff": {}}
    n_cuts = 8 if quick else 30
    for fname in ("score", "score2"):
        fn = FNS[fname]
        for name, df in DATA.items():
            starts = (0.3, 0.65, 0.7) if name == "nasdaq3x" else (0.3, 0.7)
            for st in starts:
                for seed in (0, 1):
                    v = L.check_causal(fn, df, n_cuts=n_cuts, start=st, seed=seed)
                    out["check_causal"][f"{fname}/{name}/start{st}/seed{seed}"] = v
                    print(f"[causal] check_causal {fname} {name} start={st} seed={seed}: {v:.3g}", flush=True)
            cuts = (np.array([0.3, 0.5, 0.65, 0.8, 0.95]) * len(df)).astype(int)
            v = future_swap(fn, df, cuts)
            out["future_swap"][f"{fname}/{name}"] = v
            print(f"[causal] future_swap {fname} {name}: {v:.3g}", flush=True)
    for name, df in DATA.items():
        mine = indep_scores(df)
        for (fname, side), v in mine.items():
            d = float(np.max(np.abs(v - sc(fname, name)[side].to_numpy())))
            out["indep_impl_maxdiff"][f"{fname}/{name}/{side}"] = d
        print(f"[causal] independent numpy impl vs candidate {name}:",
              {k: f"{v:.2g}" for k, v in out["indep_impl_maxdiff"].items() if f"/{name}/" in k}, flush=True)
    return out


# ================================================================== 自前の評価（照合用）
def auc_rank(y, x):
    y = np.asarray(y, bool)
    r = pd.Series(np.asarray(x, float)).rank(method="average").to_numpy()
    n1, n0 = y.sum(), (~y).sum()
    return (r[y].sum() - n1 * (n1 + 1) / 2) / (n1 * n0)


def my_metrics(score_df, name, pname, K=10, th=50, reset=35):
    df, piv, m = DATA[name], PIVS[name], mask_of(name, pname)
    n = len(df)
    pb, pk = piv.bar.to_numpy(), piv.kind.to_numpy()
    nxt = np.searchsorted(pb, np.arange(n), side="left")  # 次の転換点（そのバー自身を含む）
    known = nxt < len(pb)
    nk = np.where(known, np.where(pk[np.minimum(nxt, len(pb) - 1)] == "H", 1, -1), 0)
    bt = np.where(known, pb[np.minimum(nxt, len(pb) - 1)] - np.arange(n), 10 ** 9)
    out = {}
    for side, kind, sg in (("top", "H", 1), ("bot", "L", -1)):
        x = np.nan_to_num(score_df[side].to_numpy(float))
        y = (nk == sg) & (bt <= K)
        ok = m & known
        auc = auc_rank(y[ok], x[ok])
        sig, armed = [], True
        for i in range(n):
            if armed and x[i] >= th:
                sig.append(i)
                armed = False
            elif (not armed) and x[i] < reset:
                armed = True
        sig = np.array([s for s in sig if m[s] and known[s]], int)
        prec = float(np.mean((nk[sig] == sg) & (bt[sig] <= K))) if len(sig) else np.nan
        hits, leads = [], []
        for j in range(1, len(pb)):
            if pk[j] != kind or not m[pb[j]]:
                continue
            w = np.flatnonzero(x[pb[j - 1] + 1:pb[j] + 1] >= th)
            hits.append(len(w) > 0)
            if len(w):
                leads.append(pb[j] - (pb[j - 1] + 1 + w[0]))
        out[side] = {"auc10": auc, "precision": prec, "recall_pre": float(np.mean(hits)),
                     "lead_med": float(np.median(leads)) if leads else np.nan, "n_signals": len(sig)}
    return out


# ================================================================== repro
def part_repro(quick=False):
    J = json.load(open(REPORTED))
    rep = {c["function"]: c["results"] for c in J["candidates"]}
    rep["baseline_rsi"] = J["references"]["baseline_rsi"]
    rep["rsi14_rm"] = J["references"]["rsi14_rate_matched"]["results"]
    out = {"tables": {}, "maxdiff_vs_reported": {}, "my_metrics_maxdiff": {}, "rsi_cal": RSI_CAL,
           "rsi_cal_reported": J["references"]["rsi14_rate_matched"]["theta_s"]}
    for fname in ("score", "score2", "baseline_rsi", "rsi14_rm", "ideal"):
        res = {}
        for name, pname in PERIODS + [("sp3x", "check_overlap"), ("sp3x", "check_post")]:
            e = ev(sc(fname, name), name, pname)
            res[f"{name}/{pname}"] = pick(e)
        out["tables"][fname] = res
        if fname in rep:
            md = 0.0
            worst = None
            for key, r in rep[fname].items():
                for s in ("top", "bot"):
                    for k in KEYS:
                        a, b = r[s].get(k), res[key][s][k]
                        if a is None and b is None:
                            continue
                        d = abs((a if a is not None else np.nan) - (b if b is not None else np.nan))
                        if not np.isfinite(d):
                            d = float("inf")
                        if d > md:
                            md, worst = d, (key, s, k, a, b)
            out["maxdiff_vs_reported"][fname] = {"maxdiff": md, "worst": worst}
            print(f"[repro] {fname}: max |mine - reported| = {md:.3g}  {worst}", flush=True)
        # 自前の指標実装との照合
        mm = 0.0
        for name, pname in PERIODS:
            mine = my_metrics(sc(fname, name), name, pname)
            for s in ("top", "bot"):
                for k in ("auc10", "precision", "recall_pre", "lead_med"):
                    a, b = mine[s][k], res[f"{name}/{pname}"][s][k]
                    if a is None or b is None or (isinstance(a, float) and np.isnan(a)):
                        continue
                    mm = max(mm, abs(a - b))
        out["my_metrics_maxdiff"][fname] = mm
        print(f"[repro] {fname}: own metric implementation vs L.evaluate max diff = {mm:.3g}", flush=True)
    t = []
    for fname in ("score", "score2", "rsi14_rm", "baseline_rsi", "ideal"):
        for key, r in out["tables"][fname].items():
            for s in ("top", "bot"):
                d = r[s]
                t.append({"fn": fname, "set": key, "side": s, "recall": d["recall_pre"], "lead": d["lead_med"],
                          "q1": d["lead_q1"], "q3": d["lead_q3"], "remain": d["remain_med"], "spy": d["signals_per_year"],
                          "prec": d["precision"], "auc10": d["auc10"], "lift": (d["ap10"] or np.nan) / (d["base10"] or np.nan)})
    with pd.option_context("display.width", 250, "display.max_rows", 400):
        print(pd.DataFrame(t).round(3).to_string(index=False))
    return out


# ================================================================== null
def part_null(quick=False):
    out = {}
    n = 60 if quick else 300
    for fname in ("score", "score2", "rsi14_rm"):
        for name, pname in OOS:
            t0 = time.time()
            nt = L.null_test(sc(fname, name), DATA[name], PIVS[name], mask_of(name, pname), n=n, seed=1)
            out[f"{fname}/{name}/{pname}"] = nt
            print(f"[null] {fname} {name}/{pname} (real, null_med, p): " +
                  json.dumps({s: {k: [round(float(x), 3) for x in v] for k, v in nt[s].items()} for s in nt}),
                  f"{time.time() - t0:.0f}s", flush=True)
    return out


# ================================================================== paired
def cbb_idx(n, block, rng):
    nb = int(np.ceil(n / block))
    st = rng.integers(0, n, nb)
    return ((st[:, None] + np.arange(block)[None, :]) % n).ravel()[:n]


def raw_feature(name, col, sign):
    return sign * C.features(DATA[name], [col])[col].to_numpy(float)


def part_paired(quick=False):
    B = 300 if quick else 2000
    out = {}
    comps = {"top": [("rsi14", lambda nm: (L.rsi(DATA[nm].c, 14) - 50).to_numpy()),
                     ("stoch10", lambda nm: raw_feature(nm, "stoch10", 1)),
                     ("rsi5", lambda nm: raw_feature(nm, "rsi5", 1)),
                     ("z10", lambda nm: raw_feature(nm, "z10", 1)),
                     ("score2", lambda nm: sc("score2", nm)["top"].to_numpy())],
             "bot": [("rsi14", lambda nm: -(L.rsi(DATA[nm].c, 14) - 50).to_numpy()),
                     ("z20", lambda nm: raw_feature(nm, "z20", -1)),
                     ("z10", lambda nm: raw_feature(nm, "z10", -1)),
                     ("rsi7", lambda nm: raw_feature(nm, "rsi7", -1)),
                     ("stoch14", lambda nm: raw_feature(nm, "stoch14", -1)),
                     ("score2", lambda nm: sc("score2", nm)["bot"].to_numpy())]}
    for name, pname in OOS + [("sp3x", "check_post")]:
        m = mask_of(name, pname)
        for side in ("top", "bot"):
            y = TG[name][f"{side}_10"]
            idx = np.flatnonzero(m & ~np.isnan(y))
            yy = y[idx].astype(bool)
            cands = {"score": sc("score", name)[side].to_numpy(), "score2": sc("score2", name)[side].to_numpy()}
            refs = {k: np.nan_to_num(f(name))[idx] for k, f in comps[side]}
            rng = np.random.default_rng(1)
            boots = [cbb_idx(len(idx), 63, rng) for _ in range(B)]
            for cn, cv in cands.items():
                a = cv[idx]
                for rn, rv in refs.items():
                    if rn == cn:
                        continue
                    base = auc_rank(yy, a) - auc_rank(yy, rv)
                    ds = np.array([auc_rank(yy[b], a[b]) - auc_rank(yy[b], rv[b]) for b in boots if 0 < yy[b].mean() < 1])
                    lo, hi = np.percentile(ds, [2.5, 97.5])
                    out[f"{name}/{pname}/{side}/{cn}-{rn}"] = {"diff": base, "lo": lo, "hi": hi,
                                                               "p_le0": float((ds <= 0).mean()),
                                                               "auc_cand": auc_rank(yy, a), "auc_ref": auc_rank(yy, rv)}
            print(f"[paired] {name}/{pname} {side}: " + ", ".join(
                f"{k.split('/')[-1]} {v['diff']:+.3f}[{v['lo']:+.3f},{v['hi']:+.3f}]" for k, v in out.items()
                if k.startswith(f"{name}/{pname}/{side}/")), flush=True)
    return out


# ================================================================== timing
def part_timing(quick=False):
    out = {}
    for name, pname in PERIODS:
        df, piv, m = DATA[name], PIVS[name], mask_of(name, pname)
        n = len(df)
        tg = TG[name]
        bar, kind, _ = L.last_confirmed(piv, n)
        age = np.where(bar >= 0, np.arange(n) - bar, 0)
        rec = {}
        for side, sg in (("top", 1), ("bot", -1)):
            y = tg[f"{side}_10"]
            ok = m & ~np.isnan(y)
            # 「いま上げ脚（天井側）/下げ脚（底側）と分かっている」だけの基準（確定済みの転換点だけ使う＝未来参照なし）
            state = (kind == -sg).astype(float)
            r = {"auc_state_only": auc_rank(y[ok] == 1, state[ok]),
                 "auc_state_plus_age": auc_rank(y[ok] == 1, state[ok] + 1e-4 * np.minimum(age[ok], 999))}
            # 上げ脚の中（次の転換点が天井＝後知恵で区切った評価用の部分集合）でのタイミングの力
            leg = ok & (tg["next_kind"] == sg)
            r["base_rate_all"] = float(np.nanmean(y[ok]))
            r["base_rate_in_leg"] = float(np.nanmean(y[leg]))
            for fname in ("score", "score2", "rsi14_rm", "ideal"):
                x = sc(fname, name)[side].to_numpy(float)
                r[f"auc_all/{fname}"] = auc_rank(y[ok] == 1, x[ok])
                r[f"auc_in_leg/{fname}"] = auc_rank(y[leg] == 1, x[leg])
                # 点灯したバーのうち、次の転換点が同じ側（＝上げ脚の中で点灯）だった割合
                sig = L.crossings_up(np.nan_to_num(x))
                sig = sig[m[sig] & (tg["next_kind"][sig] != 0)]
                r[f"sig_in_right_leg/{fname}"] = float(np.mean(tg["next_kind"][sig] == sg)) if len(sig) else np.nan
                inleg = sig[tg["next_kind"][sig] == sg]
                r[f"prec_given_right_leg/{fname}"] = float(np.mean(tg["bars_to"][inleg] <= 10)) if len(inleg) else np.nan
            rec[side] = r
        out[f"{name}/{pname}"] = rec
        print(f"[timing] {name}/{pname}: " + json.dumps(clean(rec))[:1400], flush=True)

    # 同じ点灯回数（期間の中で揃える＝記述統計。実運用では使えない合わせ方）での的中率・事前点灯率
    def at_rate(raw, name, pname, rate, s):
        m = mask_of(name, pname)
        yrs = m.sum() / 252
        xt = raw[m]
        lo, hi = 0.5, 0.9995
        best = None
        for _ in range(28):
            u = (lo + hi) / 2
            th = np.quantile(xt, u)
            sc_ = logistic(raw, th, s)
            sig = L.crossings_up(sc_)
            spy = m[sig].sum() / yrs
            if best is None or abs(spy - rate) < abs(best[1] - rate):
                best = (th, spy)
            lo, hi = (u, hi) if spy > rate else (lo, u)
        return logistic(raw, best[0], s), best[1]

    def raw_of(fname, name, side):
        df = DATA[name]
        if fname == "score":
            return C.blend_raw(df, side, C.CONST["blend"][side]), C.CONST["blend"][side]["s"]
        if fname == "score2":
            return C.classic_raw(df, side, C.CONST["classic"][side]), C.CONST["classic"][side]["s"]
        r = np.nan_to_num((L.rsi(df.c, 14) - 50).to_numpy()) * (1 if side == "top" else -1)
        return r, RSI_CAL[side][1]

    eq = {}
    for name, pname in OOS:
        for side in ("top", "bot"):
            for rate in (4.0, 6.0, 8.0):
                row = {}
                for fname in ("score", "score2", "rsi14"):
                    raw, s = raw_of(fname, name, side)
                    x, spy = at_rate(raw, name, pname, rate, s)
                    S = pd.DataFrame({"top": x if side == "top" else 0.0, "bot": x if side == "bot" else 0.0},
                                     index=DATA[name].index)
                    e = ev(S, name, pname)[side]
                    row[fname] = {"spy": spy, "precision": e["precision"], "recall_pre": e["recall_pre"],
                                  "lead_med": e["lead_med"], "remain_med": e["remain_med"]}
                eq[f"{name}/{pname}/{side}/{rate:g}"] = row
            print(f"[timing] equal-rate {name}/{pname} {side}: " + "; ".join(
                f"{k.split('/')[-1]}/yr " + ", ".join(f"{f} p{v[f]['precision']:.2f} r{v[f]['recall_pre']:.2f}" for f in v)
                for k, v in eq.items() if k.startswith(f"{name}/{pname}/{side}/")), flush=True)
    out["equal_rate"] = eq
    return out


# ================================================================== sens（train で学習し直す）
def dvol_p(df, span):
    return np.log(df.c).diff().ewm(span=span, min_periods=20).std()


def feat_p(df, kind, w, span=60):
    lc = np.log(df.c)
    if kind == "rsi":
        return L.rsi(df.c, max(2, int(round(w)))) - 50
    if kind == "stoch":
        w = max(2, int(round(w)))
        hh, ll = df.h.rolling(w, min_periods=w).max(), df.l.rolling(w, min_periods=w).min()
        return 100 * (df.c - ll) / (hh - ll).replace(0, np.nan) - 50
    if kind == "z":
        w = max(2, int(round(w)))
        return (lc - lc.ewm(span=w, adjust=False).mean()) / (dvol_p(df, span) * np.sqrt(w))
    if kind == "rise":
        w = max(2, int(round(w)))
        return np.log(df.c / df.l.rolling(w, min_periods=1).min()) / (dvol_p(df, span) * np.sqrt(10))
    if kind == "trend":
        w = max(4, int(round(w)))
        return (lc - lc.rolling(w, min_periods=w // 2).mean()) / dvol_p(df, span)
    if kind == "macdh":
        f, s, g = (max(2, int(round(v))) for v in w)
        mm = (lc.ewm(span=f, adjust=False).mean() - lc.ewm(span=s, adjust=False).mean()) / dvol_p(df, span)
        return mm - mm.ewm(span=g, adjust=False).mean()
    raise ValueError(kind)


SPEC = {"blend": {"top": [("stoch", 10), ("rsi", 5), ("z", 10), ("z", 50), ("rise", 60), ("stoch", 60), ("trend", 200)],
                  "bot": [("z", 10), ("z", 20), ("rsi", 5), ("stoch", 21), ("rsi", 14), ("trend", 200), ("z", 100),
                          ("macdh", (12, 26, 9))]},
        "classic": {"top": [("rsi", 5), ("stoch", 10), ("z", 10)], "bot": [("rsi", 7), ("stoch", 14), ("z", 20)]}}


def scale_w(w, f):
    return tuple(v * f for v in w) if isinstance(w, tuple) else w * f


def build_X(df, spec, span):
    return np.column_stack([np.nan_to_num(feat_p(df, k, w, span).to_numpy(float)) for k, w in spec])


def fit_variant(group, side, spec, span=60, Creg=0.05, target=7.5, q=0.8, K=10, wnoise=None):
    """train だけで学習し直し、各データセットのスコア（0〜100）を返す"""
    df = DATA["nasdaq3x"]
    X = build_X(df, spec, span)
    if group == "blend":
        y = L.targets(PIVS["nasdaq3x"], len(df), ks=(K,))[f"{side}_{K}"]
        rows = np.flatnonzero(TRM & ~np.isnan(y))
        scl = StandardScaler().fit(X[rows])
        lr = LogisticRegression(C=Creg, max_iter=3000).fit(scl.transform(X[rows]), y[rows])
        coef = lr.coef_[0] * (wnoise if wnoise is not None else 1.0)
        mu, sd, b0 = scl.mean_, scl.scale_, float(lr.intercept_[0])

        def raw_fn(d):
            return b0 + ((build_X(d, spec, span) - mu) / sd) @ coef
    else:
        mu, sd = X[TRM].mean(0), X[TRM].std(0)
        wts = np.ones(len(spec)) if wnoise is None else wnoise
        sg = 1 if side == "top" else -1

        def raw_fn(d):
            return sg * (((build_X(d, spec, span) - mu) / sd) * wts).sum(1) / wts.sum()
    th, s, spy = C._calibrate(raw_fn(df), TRM, TRY, target, q)
    return {name: logistic(raw_fn(DATA[name]), th, s) for name in DATA}, {"theta": th, "s": s, "train_spy": spy}


def eval_variant(scores, side):
    res = {}
    for name, pname in PERIODS:
        x = scores[name]
        S = pd.DataFrame({"top": x if side == "top" else 0.0, "bot": x if side == "bot" else 0.0}, index=DATA[name].index)
        e = ev(S, name, pname)[side]
        res[f"{name}/{pname}"] = {k: fnum(e[k]) for k in ("recall_pre", "lead_med", "remain_med", "signals_per_year",
                                                          "precision", "auc10")}
    return res


def variants(group, side, quick=False):
    base = SPEC[group][side]
    V = [("base", {})]
    for f in (0.7, 0.8, 1.2, 1.3):
        V.append((f"all_windows x{f}", {"spec": [(k, scale_w(w, f)) for k, w in base]}))
    for i, (k, w) in enumerate(base):
        for f in (0.75, 1.25):
            sp = list(base)
            sp[i] = (k, scale_w(w, f))
            V.append((f"{k}{w if not isinstance(w, tuple) else ''} x{f}", {"spec": sp}))
    for f in (0.75, 1.25):
        V.append((f"dvol_span x{f}", {"span": int(round(60 * f))}))
    for f in (0.75, 1.25):
        V.append((f"target_spy x{f}", {"target": 7.5 * f}))
    for qq in (0.7, 0.9):
        V.append((f"q_caution {qq}", {"q": qq}))
    if group == "blend":
        for cc in (0.01, 0.0375, 0.0625, 0.2):
            V.append((f"C {cc}", {"Creg": cc}))
        for K in (8, 12):
            V.append((f"label K={K}", {"K": K}))
        for i, (k, w) in enumerate(base):
            V.append((f"drop {k}{w if not isinstance(w, tuple) else ''}", {"spec": base[:i] + base[i + 1:]}))
    rng = np.random.default_rng(11)
    for j in range(10 if quick else 40):
        V.append((f"weights noise #{j}", {"wnoise": rng.uniform(0.7, 1.3, len(base))}))
    return V


def part_sens(quick=False):
    out = {}
    for group in ("blend", "classic"):
        for side in ("top", "bot"):
            rows = {}
            for label, kw in variants(group, side, quick):
                spec = kw.pop("spec", SPEC[group][side])
                scores, cal = fit_variant(group, side, spec, **kw)
                rows[label] = {"cal": cal, "res": eval_variant(scores, side)}
            # 基準（base）が候補そのものと一致するか
            base_s = rows["base"]["res"]
            cand = "score" if group == "blend" else "score2"
            chk = max(abs(base_s[f"{n}/{p}"]["auc10"] - ev(sc(cand, n), n, p)[side]["auc10"]) for n, p in PERIODS)
            summ = {}
            for per in [f"{n}/{p}" for n, p in PERIODS]:
                for met in ("auc10", "precision", "recall_pre", "signals_per_year", "lead_med", "remain_med"):
                    vals = {lab: r["res"][per][met] for lab, r in rows.items()}
                    vv = {k: v for k, v in vals.items() if v is not None}
                    b = vals["base"]
                    lo_k = min(vv, key=vv.get)
                    hi_k = max(vv, key=vv.get)
                    nonnoise = {k: v for k, v in vv.items() if not k.startswith("weights")}
                    noise = [v for k, v in vv.items() if k.startswith("weights")]
                    summ[f"{per}/{met}"] = {"base": b, "min": vv[lo_k], "min_at": lo_k, "max": vv[hi_k], "max_at": hi_k,
                                            "param_min": min(nonnoise.values()), "param_max": max(nonnoise.values()),
                                            "noise_p05": float(np.percentile(noise, 5)),
                                            "noise_p95": float(np.percentile(noise, 95))}
            out[f"{group}/{side}"] = {"base_matches_candidate_auc_maxdiff": chk, "summary": summ,
                                      "rows": {k: v["res"] for k, v in rows.items()}}
            print(f"[sens] {group}/{side}: base reproduces candidate (auc maxdiff {chk:.2g}); n_variants={len(rows)}",
                  flush=True)
            for per in ("nasdaq3x/train", "nasdaq3x/test", "sp3x/check", "sp3x_close/pre1999", "sp3x_close/oos2019"):
                s_ = {met: summ[f"{per}/{met}"] for met in ("auc10", "precision", "recall_pre", "signals_per_year")}
                print(f"   {per}: " + "; ".join(
                    f"{met} base {v['base']:.3f} param[{v['param_min']:.3f},{v['param_max']:.3f}] "
                    f"noise90%[{v['noise_p05']:.3f},{v['noise_p95']:.3f}] min@{v['min_at']}"
                    for met, v in s_.items()), flush=True)
    return out


# ================================================================== smooth
def part_smooth(quick=False):
    out = {}
    for group, raw_f in (("blend", C.blend_raw), ("classic", C.classic_raw)):
        for side in ("top", "bot"):
            cst = C.CONST[group][side]
            rows = {}
            for span in (1, 2, 3, 5):
                raws = {nm: pd.Series(raw_f(DATA[nm], side, cst)).ewm(span=span, adjust=False).mean().to_numpy()
                        if span > 1 else raw_f(DATA[nm], side, cst) for nm in DATA}
                th, s, spy = C._calibrate(raws["nasdaq3x"], TRM, TRY)
                r = {}
                for name, pname in PERIODS:
                    x = logistic(raws[name], th, s)
                    m = mask_of(name, pname)
                    S = pd.DataFrame({"top": x if side == "top" else 0.0, "bot": x if side == "bot" else 0.0},
                                     index=DATA[name].index)
                    e = ev(S, name, pname)[side]
                    d = np.abs(np.diff(x))[m[1:]]
                    flips = ((x[1:] >= 50) != (x[:-1] >= 50))[m[1:]].sum() / (m.sum() / 252)
                    r[f"{name}/{pname}"] = {"auc10": e["auc10"], "precision": e["precision"], "recall_pre": e["recall_pre"],
                                            "spy": e["signals_per_year"], "mean_abs_step": float(d.mean()),
                                            "p90_abs_step": float(np.percentile(d, 90)), "cross50_per_year": float(flips)}
                rows[f"ema{span}"] = r
            out[f"{group}/{side}"] = rows
            print(f"[smooth] {group}/{side}: " + "; ".join(
                f"ema{sp[3:]} train auc {v['nasdaq3x/train']['auc10']:.3f} test auc {v['nasdaq3x/test']['auc10']:.3f} "
                f"step {v['nasdaq3x/test']['mean_abs_step']:.1f} x50/yr {v['nasdaq3x/test']['cross50_per_year']:.0f}"
                for sp, v in rows.items()), flush=True)
    # 参考: 理想形・RSI14 のなだらかさ
    ref = {}
    for fname in ("ideal", "rsi14_rm"):
        for side in ("top", "bot"):
            x = sc(fname, "nasdaq3x")[side].to_numpy()
            m = mask_of("nasdaq3x", "test")
            d = np.abs(np.diff(x))[m[1:]]
            ref[f"{fname}/{side}"] = {"mean_abs_step": float(d.mean()), "cross50_per_year":
                                      float(((x[1:] >= 50) != (x[:-1] >= 50))[m[1:]].sum() / (m.sum() / 252))}
    out["reference_test"] = ref
    print("[smooth] reference (nasdaq3x/test):", json.dumps(clean(ref)), flush=True)
    return out


# ================================================================== fwd
def part_fwd(quick=False):
    out = {}
    nnull = 200 if quick else 1000
    for name, pname in OOS:
        df, m = DATA[name], mask_of(name, pname)
        lc = np.log(df.c.to_numpy())
        n = len(df)
        seg = np.flatnonzero(m)
        a, b = seg[0], seg[-1] + 1
        for H in (10, 20):
            fwd = np.full(n, np.nan)
            fwd[:n - H] = lc[H:] - lc[:n - H]
            uncond = float(np.nanmean(fwd[m]))
            for fname in ("score", "score2", "rsi14_rm"):
                for side in ("top", "bot"):
                    x = np.nan_to_num(sc(fname, name)[side].to_numpy(float))
                    sig = L.crossings_up(x)
                    sig = sig[m[sig] & ~np.isnan(fwd[sig])]
                    if not len(sig):
                        continue
                    real = float(np.mean(fwd[sig]))
                    rng = np.random.default_rng(1)
                    nulls = []
                    for _ in range(nnull):
                        v = x.copy()
                        v[a:b] = np.roll(v[a:b], int(rng.integers(60, b - a - 60)))
                        s2 = L.crossings_up(v)
                        s2 = s2[m[s2] & ~np.isnan(fwd[s2])]
                        if len(s2):
                            nulls.append(np.mean(fwd[s2]))
                    nulls = np.array(nulls)
                    p = float(np.mean(nulls <= real)) if side == "top" else float(np.mean(nulls >= real))
                    out[f"{name}/{pname}/H{H}/{fname}/{side}"] = {
                        "n": int(len(sig)), "mean_fwd_pct": 100 * (np.exp(real) - 1), "median_fwd_pct":
                        100 * (np.exp(np.median(fwd[sig])) - 1), "frac_down": float(np.mean(fwd[sig] < 0)),
                        "uncond_mean_pct": 100 * (np.exp(uncond) - 1), "null_median_pct": 100 * (np.exp(np.median(nulls)) - 1),
                        "p_one_sided": p}
            print(f"[fwd] {name}/{pname} H={H}: " + "; ".join(
                f"{k.split('/')[-2]}/{k.split('/')[-1]} n{v['n']} mean {v['mean_fwd_pct']:+.1f}% (uncond {v['uncond_mean_pct']:+.1f}%,"
                f" null {v['null_median_pct']:+.1f}%, p {v['p_one_sided']:.3f}) down {v['frac_down']:.2f}"
                for k, v in out.items() if k.startswith(f"{name}/{pname}/H{H}/")), flush=True)
    return out


# ================================================================== traincv（報告の train 内 CV と C の安定性）
def part_traincv(quick=False):
    df = DATA["nasdaq3x"]
    tg = TG["nasdaq3x"]
    idx = np.flatnonzero(TRM)
    folds = np.array_split(idx, 4)
    out = {}
    for side in ("top", "bot"):
        y = tg[f"{side}_10"]
        X = C.features(df, C.BLEND_COLS[side]).to_numpy(float)
        oof = np.full(len(df), np.nan)
        fa = []
        for f in folds:
            trn = np.setdiff1d(idx, np.arange(f[0] - 20, f[-1] + 21))
            trn = trn[~np.isnan(y[trn])]
            te = f[~np.isnan(y[f])]
            scl = StandardScaler().fit(X[trn])
            lr = LogisticRegression(C=0.05, max_iter=3000).fit(scl.transform(X[trn]), y[trn])
            oof[te] = lr.decision_function(scl.transform(X[te]))
            fa.append(roc_auc_score(y[te], oof[te]))
        ok = ~np.isnan(oof)
        # Classic3 は学習なしなので CV 不要（in-sample = 学習なし）。比較用に同じ fold での RSI14 の AUC も
        r14 = (1 if side == "top" else -1) * (L.rsi(df.c, 14) - 50).to_numpy()
        out[side] = {"cv_auc_pooled": roc_auc_score(y[ok], oof[ok]), "cv_auc_folds": fa,
                     "insample_auc": ev(sc("score", "nasdaq3x"), "nasdaq3x", "train")[side]["auc10"],
                     "rsi14_auc_same_rows": roc_auc_score(y[ok], r14[ok])}
        rows = np.flatnonzero(TRM & ~np.isnan(y))
        scl = StandardScaler().fit(X[rows])
        coefs = {}
        for cc in (0.005, 0.01, 0.02, 0.05, 0.1, 0.2, 1.0):
            coefs[cc] = LogisticRegression(C=cc, max_iter=5000).fit(scl.transform(X[rows]), y[rows]).coef_[0]
        base = coefs[0.05]
        out[side]["coef_by_C"] = {str(k): v.tolist() for k, v in coefs.items()}
        out[side]["coef_max_absdiff_vs_C0.05"] = {str(k): float(np.max(np.abs(v - base))) for k, v in coefs.items()}
        out[side]["sign_flips_vs_C0.05"] = {str(k): int((np.sign(v) != np.sign(base)).sum()) for k, v in coefs.items()}
        print(f"[traincv] {side}: " + json.dumps(clean({k: v for k, v in out[side].items() if k != 'coef_by_C'})), flush=True)
        print("   cols", C.BLEND_COLS[side])
        for k, v in coefs.items():
            print(f"   C={k}: " + " ".join(f"{x:+.3f}" for x in v))
    return out


# ================================================================== leg（転換点の直前 10 本以内に 50 へ届いたか）
def leg_hits(x, piv, m, kind, W=10, th=50):
    pb, pk = piv.bar.to_numpy(), piv.kind.to_numpy()
    last, at = [], []
    for j in range(1, len(pb)):
        if pk[j] != kind or not m[pb[j]]:
            continue
        a = max(pb[j - 1] + 1, pb[j] - W)
        last.append(bool((x[a:pb[j] + 1] >= th).any()))
        at.append(bool(x[pb[j]] >= th))
    return float(np.mean(last)), float(np.mean(at))


def part_leg(quick=False):
    out = {}
    n = 60 if quick else 300
    for fname in ("score", "score2", "rsi14_rm", "ideal"):
        for name, pname in OOS:
            m = mask_of(name, pname)
            seg = np.flatnonzero(m)
            a, b = seg[0], seg[-1] + 1
            r = {}
            for side, kind in (("top", "H"), ("bot", "L")):
                x = np.nan_to_num(sc(fname, name)[side].to_numpy(float))
                real_last, real_at = leg_hits(x, PIVS[name], m, kind)
                rng = np.random.default_rng(1)
                nl, na = [], []
                for _ in range(n):
                    v = x.copy()
                    v[a:b] = np.roll(v[a:b], int(rng.integers(60, b - a - 60)))
                    u = leg_hits(v, PIVS[name], m, kind)
                    nl.append(u[0])
                    na.append(u[1])
                r[side] = {"hit_last10": real_last, "hit_last10_null_med": float(np.median(nl)),
                           "p_last10": float(np.mean(np.array(nl) >= real_last)), "lit_at_pivot": real_at,
                           "lit_at_pivot_null_med": float(np.median(na)), "p_at_pivot": float(np.mean(np.array(na) >= real_at))}
            out[f"{fname}/{name}/{pname}"] = r
            print(f"[leg] {fname} {name}/{pname}: " + json.dumps(clean(r)), flush=True)
    return out


# ================================================================== table
def part_table(quick=False):
    S = json.load(open(OUT))
    tab = S["repro"]["tables"]
    nul = S.get("null", {})
    tim = S.get("timing", {})
    leg = S.get("leg", {})
    rows = []
    for fname in ("score", "score2", "rsi14_rm", "baseline_rsi"):
        for key in ("nasdaq3x/test", "sp3x/check", "sp3x/check_post", "sp3x_close/pre1999", "sp3x_close/oos2019"):
            for side in ("top", "bot"):
                d = tab[fname][key][side]
                nt = nul.get(f"{fname}/{key}", {}).get(side, {})
                tm = tim.get(key, {}).get(side, {})
                lg = leg.get(f"{fname}/{key}", {}).get(side, {})
                rows.append({"fn": fname, "set": key, "side": side, "事前点灯率": d["recall_pre"], "何本前": d["lead_med"],
                             "残り値幅%": d["remain_med"], "点灯/年": d["signals_per_year"], "的中率": d["precision"],
                             "AUC10": d["auc10"], "p点灯": (nt.get("recall_pre") or [None] * 3)[2],
                             "p的中": (nt.get("precision") or [None] * 3)[2], "pAUC": (nt.get("auc10") or [None] * 3)[2],
                             "脚内AUC": tm.get(f"auc_in_leg/{fname}"), "直前10本": lg.get("hit_last10"),
                             "p直前10": lg.get("p_last10")})
    with pd.option_context("display.width", 250, "display.max_rows", 200):
        print(pd.DataFrame(rows).round(3).to_string(index=False))
    return {"rows": rows}


PARTS = {"audit": part_audit, "causal": part_causal, "repro": part_repro, "null": part_null, "paired": part_paired,
         "timing": part_timing, "sens": part_sens, "smooth": part_smooth, "fwd": part_fwd, "traincv": part_traincv,
         "leg": part_leg, "table": part_table}


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    quick = "--quick" in sys.argv
    todo = args or [p for p in PARTS if p != "table"] + ["table"]
    for p in todo:
        t0 = time.time()
        print(f"===== {p}", flush=True)
        v = PARTS[p](quick)
        if p != "table":
            save_part(p, v, time.time() - t0)
        print(f"===== {p} done {time.time() - t0:.0f}s", flush=True)


if __name__ == "__main__":
    main()
