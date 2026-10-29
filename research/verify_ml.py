"""cand_ml（score = TL-ML-GBM / score2 = TL-ML-Logit）の反証検証  key: ml

python3 verify_ml.py                    # 全部（OMP 1 スレッドで 10〜20 分程度）
python3 verify_ml.py causal repro null  # 一部だけ（既存の results/verify_ml.json にマージ）
  causal  : L.check_causal（n_cuts=30。sp3x / sp3x_close は start 0.3・0.7、nasdaq3x は学習期間外の 0.65・0.7）
            ＋ 学習データ遮断テスト（nasdaq3x の 2011 年以降を壊して学習し直しても、モデル・目盛り・予測が完全に同じか。
            対照として 2010 年末の 30 本を壊すと変わることも確認）＋ train だけの ZigZag が全期間の ZigZag の先頭と一致するか
  repro   : run_all を再実行して results/ml.json と照合。報告文の数字との照合。素の RSI14 の AUC10。
            sp3x/check を学習と同じ時期（1999-07〜2010）と以後（2011〜2018）に分割。表示のなだらかさ。train→CV→test の落ち方
  null    : L.null_test（循環シフト, n=300, seed=1）を score / score2 / baseline_rsi / rsi_matched で
  aucdiff : AUC10 の差（候補 − 素の RSI14 など）のブロック・ブートストラップ（63 本 / 126 本ブロック, 1000 回）
  traincv : cand_ml.run_selection() を再実行して、train CV の数字と 1SE 選択が results/ml.json と一致するか
  sens    : 主要パラメータを ±20〜30% 動かして train だけで学習し直し、test / check_post / oos2019 の崩れ方を見る
  zzsens  : 正解 ZigZag の倍率 1.0 / 1.5 / 2.0（sensitivity.run と同じ手順）
  curve   : 点灯回数を揃えたときの的中率・事前点灯率（評価期間内でしきい値を合わせる記述統計。実運用はできない診断）
  geo     : 追加の帰無「値動きの順番だけ入れ替えた偽の価格」（i.i.d. 入れ替え / 変動率の並びは残して向きだけ乱す鏡映）。
            モデルは固定のまま偽の価格に当て、AUC10 などがどこまで「ZigZag の定義から自動的に出る分」かを測る
  table   : 保存済みの結果から「検証後の数字」の表を作る
cand_ml.py / turnline_lab.py は import するだけで編集しない。
"""
import os

os.environ.setdefault("OMP_NUM_THREADS", "1")   # HGB の過剰スレッドで 50 倍遅くなるのを防ぐ（結果は同一であることを確認済み）

import json  # noqa: E402
import math  # noqa: E402
import sys  # noqa: E402
import time  # noqa: E402
import warnings  # noqa: E402
from pathlib import Path  # noqa: E402

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from sklearn.metrics import roc_auc_score  # noqa: E402

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import turnline_lab as L  # noqa: E402
import cand_ml as M  # noqa: E402

warnings.filterwarnings("ignore")
OUT = HERE / "results" / "verify_ml.json"
REPORTED = json.load(open(HERE / "results" / "ml.json"))
SIDES = ("top", "bot")
METRICS = ("recall_pre", "lead_med", "remain_med", "signals_per_year", "precision", "auc10", "ap10", "base10",
           "n_pivots", "n_signals", "recall_late", "precision_lenient", "lit_frac")
EXTRA_PERIODS = {"sp3x": {"check_pre2011": ("1999-07-01", "2010-12-31"), "check_post": ("2011-01-01", "2018-12-31")}}
EVAL = [("nasdaq3x", "test"), ("sp3x", "check"), ("sp3x", "check_pre2011"), ("sp3x", "check_post"),
        ("sp3x_close", "pre1999"), ("sp3x_close", "oos2019")]
_CACHE = {}


# ---------------------------------------------------------------- 共通
def data(name):
    if name not in _CACHE:
        df = L.load(name)
        _CACHE[name] = (df, L.pivots(df))
    return _CACHE[name]


def period(name, pname):
    per = L.SETS[name][1].get(pname) or EXTRA_PERIODS[name][pname]
    return L.period_mask(data(name)[0], per)


def raw_rsi(df):
    """素の RSI14（0〜100 に切り詰めない。bot は 100−RSI）"""
    r = L.rsi(df.c).fillna(50)
    return pd.DataFrame({"top": r, "bot": 100 - r}, index=df.index)


def raw_logodds(fn_name):
    """候補の 0〜100 に写す前の対数オッズ（0 への切り詰め＝同点が無い。AUC を素の RSI と公平に比べる用）"""
    def _f(df):
        f = M.fitted(fn_name)
        X = M.osc_features(df)
        return pd.DataFrame({s: f[s]["model"].logodds(X) for s in SIDES}, index=df.index)
    return _f


FNS = {"score": M.score, "score2": M.score2, "baseline_rsi": L.baseline_rsi, "rsi_matched": M.rsi_matched,
       "raw_rsi14": raw_rsi, "ideal": None, "score_u": raw_logodds("score"), "score2_u": raw_logodds("score2")}


def scores(fn_name, name):
    key = ("sc", fn_name, name)
    if key not in _CACHE:
        df, piv = data(name)
        _CACHE[key] = L.ideal(df, piv) if fn_name == "ideal" else FNS[fn_name](df)
    return _CACHE[key]


def ev(fn_name, name, pname):
    df, piv = data(name)
    return L.evaluate(scores(fn_name, name), df, piv, period(name, pname))


def fnum(v):
    try:
        v = float(v)
    except (TypeError, ValueError):
        return v
    return None if not np.isfinite(v) else v


def clean(o):
    if isinstance(o, dict):
        return {str(k): clean(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [clean(v) for v in o]
    if isinstance(o, (bool, np.bool_)):
        return bool(o)
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (float, np.floating)):
        return fnum(o)
    return o


def pick(d, keys=METRICS):
    return {k: fnum(d[k]) for k in keys if k in d}


# ---------------------------------------------------------------- (1) 未来参照
def part_causal(quick=False):
    out = {"check_causal": {}, "cutoff_test": {}, "pivot_prefix": {}}
    plan = {"nasdaq3x": (0.65, 0.7), "sp3x": (0.3, 0.7), "sp3x_close": (0.3, 0.7)}
    extra = {"nasdaq3x": (0.3,)}            # 参考: モデルは固定なので学習期間内の切り口でも採点関数の因果性は測れる
    ncut = 8 if quick else 30
    for fn_name in ("score", "score2", "baseline_rsi", "rsi_matched"):
        for name in plan:
            df = data(name)[0]
            for st in plan[name] + extra.get(name, ()):
                t0 = time.time()
                v = L.check_causal(FNS[fn_name], df, n_cuts=ncut, start=st)
                tag = f"{fn_name}/{name}/start{st}" + ("(参考)" if st in extra.get(name, ()) else "")
                out["check_causal"][tag] = v
                print(f"  check_causal {tag:40s} n_cuts={ncut}: {v:.3g}  ({time.time() - t0:.0f}s)", flush=True)
    # 学習データ遮断テスト
    full = data("nasdaq3x")[0]
    ref = {fn: FNS[fn](full).to_numpy(float) for fn in ("score", "score2")}
    ref_anchor = {fn: {s: M.fitted(fn)[s]["anchors"] for s in SIDES} for fn in ("score", "score2")}
    orig_load = L.load

    def corrupt(lo, hi, seed):
        def _load(name):
            df = orig_load(name)
            if name == "nasdaq3x":
                df = df.copy()
                m = (df.index > lo) & (df.index <= hi)
                rng = np.random.default_rng(seed)
                k = np.exp(np.cumsum(rng.normal(0, 0.05, m.sum())))[:, None]
                df.loc[m, ["o", "h", "l", "c"]] = df.loc[m, ["o", "h", "l", "c"]].to_numpy() * k
            return df
        return _load

    for label, lo, hi in (("2011年以降を破壊（変わってはいけない）", "2010-12-31", "2100-01-01"),
                          ("対照: 2010-11-15〜12-31 を破壊（変わるはず）", "2010-11-15", "2010-12-31")):
        L.load = corrupt(lo, hi, 7)
        M._FITTED.clear()
        try:
            res = {}
            for fn in ("score", "score2"):
                f = M.fitted(fn)
                new = M._score(full, fn).to_numpy(float)
                res[fn] = {"max_abs_diff_score_on_real_data": float(np.abs(new - ref[fn]).max()),
                           "anchors_identical": all(np.allclose(np.array(f[s]["anchors"]), np.array(ref_anchor[fn][s]),
                                                                rtol=0, atol=0) for s in SIDES)}
        finally:
            L.load = orig_load
            M._FITTED.clear()
        out["cutoff_test"][label] = res
        print("  cutoff test", label, res, flush=True)
    for fn in ("score", "score2"):          # 元に戻ったことの確認
        assert np.array_equal(FNS[fn](full).to_numpy(float), ref[fn])
    # train だけの ZigZag が全期間の ZigZag の先頭と一致するか（学習の正解が全期間の正解と同じ転換点であること）
    tr = M.train_frame()
    pt = L.pivots(tr)
    pf = data("nasdaq3x")[1]
    pf_pre = pf[pf.confirm < len(tr)].reset_index(drop=True)
    same = len(pt) == len(pf_pre) and (pt[["bar", "kind", "confirm"]].to_numpy() == pf_pre[["bar", "kind", "confirm"]]
                                       .to_numpy()).all()
    f = M.fitted("score")
    out["pivot_prefix"] = {"train_pivots": len(pt), "full_pivots_confirmed_in_train": len(pf_pre), "identical": bool(same),
                           "last_train_label_row": f["top"]["last_row"], "n_train_rows": f["top"]["n_rows"],
                           "embargo_binding": bool(np.flatnonzero(~np.isnan(M.labels_upto(tr, len(tr))["top_10"]))[-1]
                                                   >= len(tr) - M.EMBARGO)}
    print("  pivot prefix", out["pivot_prefix"], flush=True)
    return out


# ---------------------------------------------------------------- (2)(3) 再現と照合
CLAIMS = {  # 報告文の数字（研究担当の報告。文字列の桁数で許容誤差を決める）
    ("score", "nasdaq3x/test", "top"): {"recall_pre": "0.51", "lead_med": "14.5", "precision": "0.26", "auc10": "0.662",
                                        "signals_per_year": "8.3"},
    ("score", "nasdaq3x/test", "bot"): {"recall_pre": "0.80", "lead_med": "4", "precision": "0.86", "auc10": "0.852",
                                        "signals_per_year": "5.5"},
    ("score", "sp3x/check", "top"): {"recall_pre": "0.50", "lead_med": "21", "precision": "0.25", "auc10": "0.657"},
    ("score", "sp3x/check", "bot"): {"recall_pre": "0.87", "lead_med": "6", "precision": "0.72", "auc10": "0.874"},
    ("score", "sp3x_close/oos2019", "top"): {"recall_pre": "0.75", "lead_med": "61", "remain_med": "25",
                                             "precision": "0.24", "auc10": "0.705", "signals_per_year": "10.3"},
    ("score", "sp3x_close/oos2019", "bot"): {"recall_pre": "1.00", "lead_med": "10.5", "precision": "0.46",
                                             "auc10": "0.843"},
    ("score", "sp3x_close/pre1999", "top"): {"auc10": "0.674"},
    ("score2", "nasdaq3x/test", "top"): {"recall_pre": "0.77", "lead_med": "11.5", "precision": "0.37",
                                         "auc10": "0.677", "signals_per_year": "10.8"},
    ("score2", "nasdaq3x/test", "bot"): {"recall_pre": "0.85", "lead_med": "4", "precision": "0.84", "auc10": "0.852",
                                         "signals_per_year": "6.1"},
    ("score2", "sp3x/check", "top"): {"recall_pre": "0.50", "lead_med": "23", "precision": "0.27", "auc10": "0.640"},
    ("score2", "sp3x/check", "bot"): {"recall_pre": "0.83", "lead_med": "6.5", "precision": "0.67", "auc10": "0.867"},
    ("score2", "sp3x_close/oos2019", "top"): {"recall_pre": "0.83", "lead_med": "21.5", "precision": "0.33",
                                              "auc10": "0.734"},
    ("score2", "sp3x_close/oos2019", "bot"): {"recall_pre": "1.00", "lead_med": "10.5", "precision": "0.50",
                                              "auc10": "0.854"},
    ("raw_rsi14", "nasdaq3x/test", "top"): {"auc10": "0.666"}, ("raw_rsi14", "sp3x/check", "top"): {"auc10": "0.625"},
    ("raw_rsi14", "sp3x_close/oos2019", "top"): {"auc10": "0.727"},
    ("raw_rsi14", "sp3x_close/pre1999", "top"): {"auc10": "0.725"},
    ("raw_rsi14", "nasdaq3x/test", "bot"): {"auc10": "0.862"}, ("raw_rsi14", "sp3x/check", "bot"): {"auc10": "0.871"},
    ("raw_rsi14", "sp3x_close/oos2019", "bot"): {"auc10": "0.865"},
    ("rsi_matched", "nasdaq3x/test", "bot"): {"recall_pre": "0.64", "precision": "0.82", "signals_per_year": "4.3"},
    ("baseline_rsi", "nasdaq3x/test", "top"): {"recall_pre": "0.44", "precision": "0.33", "auc10": "0.66"},
    ("baseline_rsi", "nasdaq3x/test", "bot"): {"recall_pre": "0.31", "precision": "0.85", "auc10": "0.83"},
}


def claim_ok(s, v):
    d = len(s.split(".")[1]) if "." in s else 0
    return v is not None and abs(float(s) - v) <= 0.5 * 10 ** -d + 1e-3


def part_repro(quick=False):
    out = {"results": {}, "json_match": {}, "claims": [], "smooth": {}, "train_vs_test": {}}
    for fn_name in ("score", "score2", "baseline_rsi", "rsi_matched", "raw_rsi14", "ideal"):
        for name, (_, periods) in L.SETS.items():
            for pname in list(periods) + list(EXTRA_PERIODS.get(name, {})):
                r = ev(fn_name, name, pname)
                out["results"][f"{fn_name}|{name}/{pname}"] = {s: pick(r[s]) for s in SIDES}
    # results/ml.json との照合（同じ関数を同じハーネスで再実行 → 完全一致するはず）
    rep = {c["function"]: c["results"] for c in REPORTED["candidates"]}
    rep["baseline_rsi"] = REPORTED["references"]["RSI14 (L.baseline_rsi)"]["results"]
    rep["rsi_matched"] = REPORTED["references"]["RSI14 matched (同じ目盛り合わせ・点灯/年)"]["results"]
    rep["ideal"] = REPORTED["references"]["ideal (未来を使う上限)"]["results"]
    for fn_name, rr in rep.items():
        worst = 0.0
        for per, d in rr.items():
            mine = out["results"][f"{fn_name}|{per}"]
            for s in SIDES:
                for k, v in d[s].items():
                    if v is None or mine[s].get(k) is None:
                        continue
                    worst = max(worst, abs(float(v) - mine[s][k]))
        out["json_match"][fn_name] = worst
    print("  results/ml.json との最大差:", out["json_match"], flush=True)
    for (fn_name, per, s), cl in CLAIMS.items():
        mine = out["results"][f"{fn_name}|{per}"][s]
        for k, sv in cl.items():
            out["claims"].append({"fn": fn_name, "set": per, "side": s, "metric": k, "claimed": sv,
                                  "recomputed": mine[k], "ok": claim_ok(sv, mine[k])})
    bad = [c for c in out["claims"] if not c["ok"]]
    print(f"  報告文の数字 {len(out['claims'])} 個中 不一致 {len(bad)}:", bad, flush=True)
    # 表示のなだらかさ（1 日の変化の絶対値）と 25/50/80 以上の日の割合
    for fn_name in ("score", "score2", "baseline_rsi", "rsi_matched", "ideal"):
        for name, pname in [("nasdaq3x", "train")] + EVAL:
            sc = scores(fn_name, name)
            m = period(name, pname)
            row = {}
            for s in SIDES:
                v = sc[s].fillna(0).to_numpy(float)
                d = np.abs(np.diff(v[m]))
                row[s] = {"med_abs_change": float(np.median(d)), "p90_abs_change": float(np.percentile(d, 90)),
                          "frac_ge25": float((v[m] >= 25).mean()), "frac_ge50": float((v[m] >= 50).mean()),
                          "frac_ge80": float((v[m] >= 80).mean())}
            out["smooth"][f"{fn_name}|{name}/{pname}"] = row
    # train（学習に使った期間 = in-sample）→ train CV → test の AUC10 の落ち方（候補 − 素の RSI14 の差も）
    cv = {p: v["pick"]["fold_auc_mean"] for p, v in REPORTED["train_cv"]["picks"].items()}
    rsi_cv = {s: REPORTED["train_cv"]["rsi_cv"][s]["fold_auc_mean"] for s in SIDES}
    for fn_name, fam in (("score", "hgb"), ("score2", "logit")):
        for s in SIDES:
            ins = out["results"][f"{fn_name}|nasdaq3x/train"][s]["auc10"]
            tst = out["results"][f"{fn_name}|nasdaq3x/test"][s]["auc10"]
            rins = out["results"][f"raw_rsi14|nasdaq3x/train"][s]["auc10"]
            rtst = out["results"][f"raw_rsi14|nasdaq3x/test"][s]["auc10"]
            out["train_vs_test"][f"{fn_name}/{s}"] = {
                "train_insample": ins, "train_cv": cv[f"{fam}/{s}"], "test": tst,
                "rsi_train": rins, "rsi_cv": rsi_cv[s], "rsi_test": rtst,
                "edge_vs_rsi_cv": cv[f"{fam}/{s}"] - rsi_cv[s], "edge_vs_rsi_test": tst - rtst}
    print("  train→CV→test:", json.dumps(clean(out["train_vs_test"]), ensure_ascii=False), flush=True)
    return out


# ---------------------------------------------------------------- 帰無検定（循環シフト）
def part_null(quick=False):
    out = {}
    n = 40 if quick else 300
    for fn_name in ("score", "score2", "baseline_rsi", "rsi_matched"):
        for name, pname in EVAL:
            t0 = time.time()
            df, piv = data(name)
            nt = L.null_test(scores(fn_name, name), df, piv, period(name, pname), n=n, seed=1)
            out[f"{fn_name}|{name}/{pname}"] = nt
            print(f"  null {fn_name:12s} {name}/{pname:13s}", {s: {k: tuple(round(float(x), 3) for x in v)
                                                                  for k, v in nt[s].items()} for s in SIDES},
                  f"({time.time() - t0:.0f}s)", flush=True)
    return out


# ---------------------------------------------------------------- AUC10 の差のブロック・ブートストラップ
def fast_auc(y, x):
    """roc_auc_score と同じ値（同点は 0.5）を順位から計算する高速版"""
    from scipy.stats import rankdata
    y = np.asarray(y) > 0.5
    npos = y.sum()
    nneg = len(y) - npos
    r = rankdata(x)
    return (r[y].sum() - npos * (npos + 1) / 2) / (npos * nneg)


def boot_diff(y, a, b, B=1000, BL=63, seed=0):
    n = len(y)
    rng = np.random.default_rng(seed)
    nb = int(math.ceil(n / BL))
    out = []
    for _ in range(B):
        st = rng.integers(0, n - BL + 1, nb)
        ii = (st[:, None] + np.arange(BL)).ravel()[:n]
        yy = y[ii]
        if yy.min() == yy.max():
            continue
        out.append(fast_auc(yy, a[ii]) - fast_auc(yy, b[ii]))
    out = np.array(out)
    assert abs(fast_auc(y, a) - roc_auc_score(y, a)) < 1e-12
    return {"diff": float(roc_auc_score(y, a) - roc_auc_score(y, b)), "ci_lo": float(np.percentile(out, 2.5)),
            "ci_hi": float(np.percentile(out, 97.5)), "p_le0": float(np.mean(out <= 0))}


def part_aucdiff(quick=False):
    out = []
    B = 200 if quick else 1000
    pairs = (("score", "raw_rsi14"), ("score2", "raw_rsi14"), ("score", "baseline_rsi"), ("score2", "baseline_rsi"),
             ("score2", "score"), ("score_u", "raw_rsi14"), ("score2_u", "raw_rsi14"), ("score", "score_u"),
             ("score2", "score2_u"))
    for name, pname in EVAL:
        df, piv = data(name)
        tg = L.targets(piv, len(df))
        m = period(name, pname)
        for s in SIDES:
            y = tg[f"{s}_10"]
            k = np.flatnonzero(m & ~np.isnan(y))
            for a, b in pairs:
                va = scores(a, name)[s].fillna(0).to_numpy(float)[k]
                vb = scores(b, name)[s].fillna(0).to_numpy(float)[k]
                for BL in (63, 126):
                    r = boot_diff(y[k], va, vb, B=B, BL=BL)
                    out.append({"set": f"{name}/{pname}", "side": s, "cmp": f"{a}-{b}", "block": BL, **r})
    tab = pd.DataFrame(out)
    pd.set_option("display.width", 220)
    print(tab[tab.block == 63].round(3).to_string(index=False), flush=True)
    return out


# ---------------------------------------------------------------- train CV の再実行
def part_traincv(quick=False):
    t0 = time.time()
    sel = M.run_selection(verbose=False)
    rep = REPORTED["train_cv"]
    mine = {f"{r['gi']}|{r['side']}": r["fold_auc_mean"] for r in sel["rows"]}
    theirs = {f"{r['gi']}|{r['side']}": r["fold_auc_mean"] for r in rep["rows"]}
    worst = max(abs(mine[k] - theirs[k]) for k in theirs)
    picks_same = all(sel["picks"][k]["pick"]["gi"] == rep["picks"][k]["pick"]["gi"] for k in rep["picks"])
    ev_same = max(abs(float(sel["event_oof"][f][s][k]) - float(rep["event_oof"][f][s][k]))
                  for f in rep["event_oof"] for s in SIDES for k in ("recall_pre", "precision", "auc10"))
    summ = {k: {"best": (v["best"]["kind"], v["best"]["fs"], v["best"]["fold_auc_mean"], v["best"]["se"]),
                "pick": (v["pick"]["kind"], v["pick"]["fs"], v["pick"]["hp"], v["pick"]["fold_auc_mean"]),
                "n_eligible": v["n_eligible"]} for k, v in sel["picks"].items()}
    rsi = {s: sel["rsi_cv"][s]["fold_auc_mean"] for s in SIDES}
    evs = {f: {s: {k: fnum(sel["event_oof"][f][s][k]) for k in ("recall_pre", "precision", "signals_per_year")}
               for s in SIDES} for f in sel["event_oof"]}
    # 4 区間それぞれで候補が RSI14 に勝ったか（区間ごとの AUC10）
    folds = {}
    for k, v in sel["picks"].items():
        s = k.split("/")[1]
        folds[k] = {"cand": v["pick"]["fold_aucs"], "rsi": sel["rsi_cv"][s]["fold_aucs"]}
    out = {"max_abs_diff_fold_auc_mean": worst, "picks_identical": picks_same, "event_oof_max_diff": ev_same,
           "picks": summ, "rsi_cv": rsi, "event_oof": evs, "fold_aucs": folds, "seconds": time.time() - t0,
           "n_settings": sel["n_settings_model"]}
    print("  traincv:", json.dumps(clean(out), ensure_ascii=False), flush=True)
    return out


# ---------------------------------------------------------------- 感度分析（train だけで学習し直す）
def osc_features_p(df, s=1.0):
    """cand_ml.osc_features と同じ式で、窓の長さだけ s 倍（s=1 で完全一致することを確認する）"""
    W = lambda p: max(1, int(round(p * s)))  # noqa: E731
    c = df.c
    lc = np.log(c)
    n = len(df)
    vol = M._vol(lc, W(60)).fillna(0.03)
    vol10 = M._vol(lc, W(10)).fillna(vol)
    thr = pd.Series(L.swing_threshold(df), index=df.index)
    f = {}
    for p in (2, 5, 14, 30):
        f[f"rsi{p}"] = L.rsi(c, max(2, W(p))) - 50
    for p in (5, 20, 60):
        q = W(p)
        f[f"z{p}"] = (lc - lc.ewm(span=q, adjust=False).mean()) / (vol * np.sqrt(q))
    for p in (1, 5, 20, 60):
        q = W(p)
        f[f"ret{p}"] = (lc - lc.shift(q)) / (vol * np.sqrt(q))
    f["vr"] = np.log(vol10 / vol)
    for p in (20, 120):
        q = W(p)
        f[f"dhi{p}"] = np.log(c / c.rolling(q, min_periods=1).max()) / thr
        f[f"dlo{p}"] = np.log(c / c.rolling(q, min_periods=1).min()) / thr
    d = np.sign(c.diff().fillna(0)).to_numpy()
    st = np.zeros(n)
    for i in range(1, n):
        if d[i] > 0:
            st[i] = st[i - 1] + 1 if st[i - 1] > 0 else 1
        elif d[i] < 0:
            st[i] = st[i - 1] - 1 if st[i - 1] < 0 else -1
    f["streak"] = np.clip(st, -W(8), W(8))
    f["trend"] = (lc.ewm(span=W(20), adjust=False).mean() - lc.ewm(span=W(100), adjust=False).mean()) / (
        vol * np.sqrt(W(50)))
    return pd.DataFrame(f, index=df.index)


def calibrate_p(u, mask, base, target, qz, qzone):
    """cand_ml.calibrate_map と同じ手順（0 と 80 を置く分位点だけ変えられる）"""
    ut = u[mask]
    q0, q25, q80, q100 = np.quantile(ut, [qz, 1 - base, qzone, 1.0])
    best = None
    for u50 in np.linspace(q25, q80, 402)[1:-1]:
        anchors = [(q0, 0.0), (q25, 25.0), (u50, 50.0), (q80, 80.0), (q100, 100.0)]
        spy = M.signals_per_year(M.apply_map(u, anchors), mask)
        if best is None or abs(spy - target) < abs(best[1] - target):
            best = (anchors, spy)
    return [(float(a), float(b)) for a, b in best[0]], float(best[1])


_CTX = {}


def fit_variant(kind, hp, fscale=1.0, horizon=10, embargo=M.EMBARGO, tmult=M.TARGET_MULT, qz=M.Q_ZERO,
                qzone=M.Q_ZONE):
    if not _CTX:
        _CTX.update(M.train_context())
    ctx = _CTX
    df, n = ctx["df"], ctx["n"]
    X = osc_features_p(df, fscale)
    tg = ctx["tg"] if horizon == 10 else L.targets(ctx["piv"], n, ks=(horizon,))
    rows = np.zeros(n, bool)
    rows[ctx["i0"]:n - embargo] = True
    out = {"fscale": fscale}
    for s in SIDES:
        y = tg[f"{s}_{horizon}"]
        rr = rows & ~np.isnan(y)
        m = M.Model(kind, "osc", **hp).fit(X[rr], y[rr].astype(int))
        u = m.logodds(X)
        anchors, spy = calibrate_p(u, ctx["trmask"], ctx["base"][s], ctx["target"][s] / M.TARGET_MULT * tmult, qz, qzone)
        out[s] = (m, anchors, spy)
    return out


def score_variant(fv, df):
    X = osc_features_p(df, fv["fscale"])
    return pd.DataFrame({s: M.apply_map(fv[s][0].logodds(X), fv[s][1]) for s in SIDES}, index=df.index)


def part_sens(quick=False):
    hgb0 = dict(M.HGB_FINAL)
    lr0 = {"C": 0.003}
    common = [("feature窓×0.75", {"fscale": 0.75}), ("feature窓×1.25", {"fscale": 1.25}),
              ("学習の正解 8本以内", {"horizon": 8}), ("学習の正解 12本以内", {"horizon": 12}),
              ("目標点灯 ×1.2(1.5→1.2倍)", {"tmult": 1.2}), ("目標点灯 ×1.8(1.5→1.8倍)", {"tmult": 1.8}),
              ("0点 中央値→40%点", {"qz": 0.4}), ("0点 中央値→60%点", {"qz": 0.6}),
              ("80点 97%→96%点", {"qzone": 0.96}), ("80点 97%→98%点", {"qzone": 0.98}),
              ("禁止期間 15本", {"embargo": 15}), ("禁止期間 27本", {"embargo": 27})]
    variants = [("score", "base", "hgb", hgb0, {})]
    for k, fac in (("learning_rate", (0.7, 0.8, 1.2, 1.3)), ("max_iter", (0.7, 1.3)), ("min_samples_leaf", (0.7, 1.3)),
                   ("l2_regularization", (0.7, 1.3))):
        for f in fac:
            hp = dict(hgb0)
            hp[k] = int(round(hgb0[k] * f)) if isinstance(hgb0[k], int) else round(hgb0[k] * f, 6)
            variants.append(("score", f"{k}×{f}", "hgb", hp, {}))
    variants.append(("score", "max_depth 2→3", "hgb", dict(hgb0, max_depth=3), {}))
    variants += [("score", lab, "hgb", hgb0, kw) for lab, kw in common]
    variants.append(("score2", "base", "lr_lin", lr0, {}))
    for f in (0.5, 0.7, 0.8, 1.2, 1.3, 2.0):
        variants.append(("score2", f"C×{f}", "lr_lin", {"C": round(0.003 * f, 6)}, {}))
    variants += [("score2", lab, "lr_lin", lr0, kw) for lab, kw in common]
    if quick:
        variants = variants[:3] + [v for v in variants if v[0] == "score2"][:3]
    # 自前の再実装が本物と一致するか（s=1・既定値で、目盛りと予測が完全一致）
    chk = {}
    for fn_name, kind, hp in (("score", "hgb", hgb0), ("score2", "lr_lin", lr0)):
        fv = fit_variant(kind, hp)
        for name in ("nasdaq3x", "sp3x_close"):
            df = data(name)[0]
            chk[f"{fn_name}/{name}"] = float(np.abs(score_variant(fv, df).to_numpy() - scores(fn_name, name).to_numpy()).max())
    for name in ("nasdaq3x", "sp3x_close"):
        df = data(name)[0]
        a, b = osc_features_p(df, 1.0).to_numpy(), M.osc_features(df).to_numpy()
        chk[f"features/{name}"] = float(np.nanmax(np.abs(a - b))) if (np.isnan(a) == np.isnan(b)).all() else float("inf")
    print("  再実装と本物の差（0 なら一致）:", chk, flush=True)
    rows = []
    sets = [("nasdaq3x", "test"), ("sp3x", "check_post"), ("sp3x_close", "oos2019"), ("sp3x_close", "pre1999")]
    for fn_name, lab, kind, hp, kw in variants:
        t0 = time.time()
        fv = fit_variant(kind, hp, **kw)
        for name, pname in sets:
            df, piv = data(name)
            r = L.evaluate(score_variant(fv, df), df, piv, period(name, pname))
            for s in SIDES:
                rows.append({"fn": fn_name, "variant": lab, "set": f"{name}/{pname}", "side": s,
                             "train_spy": fv[s][2], **pick(r[s], ("recall_pre", "lead_med", "remain_med",
                                                                   "signals_per_year", "precision", "auc10"))})
        print(f"  sens {fn_name} {lab:28s} ({time.time() - t0:.1f}s)", flush=True)
    tab = pd.DataFrame(rows)
    summ = []
    for (fn_name, st, s), g in tab.groupby(["fn", "set", "side"]):
        b = g[g.variant == "base"].iloc[0]
        for k in ("recall_pre", "lead_med", "remain_med", "signals_per_year", "precision", "auc10"):
            v = g[g.variant != "base"][k].astype(float)
            dv = (v - float(b[k])).abs()
            worst = g[g.variant != "base"].iloc[int(np.nanargmax(dv.to_numpy()))]["variant"] if dv.notna().any() else ""
            summ.append({"fn": fn_name, "set": st, "side": s, "metric": k, "base": float(b[k]),
                         "min": float(v.min()), "max": float(v.max()), "max_abs_change": float(dv.max()),
                         "worst_variant": worst})
    sm = pd.DataFrame(summ)
    pd.set_option("display.width", 250, "display.max_rows", 500)
    print(sm.round(3).to_string(index=False), flush=True)
    return {"reimpl_check": chk, "rows": rows, "summary": summ}


# ---------------------------------------------------------------- 正解 ZigZag の倍率
def part_zzsens(quick=False):
    import sensitivity as S
    tab = S.run([("GBM", M.score), ("Logit", M.score2), ("RSI14", L.baseline_rsi), ("ideal", None)])
    pd.set_option("display.width", 220, "display.max_rows", 500)
    print(tab.round(3).to_string(index=False), flush=True)
    return tab.to_dict("records")


# ---------------------------------------------------------------- 点灯回数を揃えた比較（診断）
def at_rate(x, df, piv, mask, side, target, gap=15.0):
    """評価期間内で th を動かし（reset = th − gap）、点灯/年が target に最も近い th での成績"""
    v = np.nan_to_num(x[side].to_numpy(float), nan=0.0)
    years = mask.sum() / 252
    best = None
    for th in np.arange(10, 99.5, 0.5):
        sig = L.crossings_up(v, th, th - gap)
        spy = mask[sig].sum() / years
        if best is None or abs(spy - target) < abs(best[1] - target):
            best = (th, spy)
    r = L.evaluate(x, df, piv, mask, th=best[0], reset=best[0] - gap)[side]
    return {"th": float(best[0]), **pick(r, ("signals_per_year", "recall_pre", "lead_med", "remain_med", "precision"))}


def part_curve(quick=False):
    out = []
    for name, pname in [("nasdaq3x", "test"), ("sp3x", "check_post"), ("sp3x_close", "oos2019")]:
        df, piv = data(name)
        m = period(name, pname)
        for s in SIDES:
            ppy = L.evaluate(scores("baseline_rsi", name), df, piv, m)[s]["pivots_per_year"]
            for mult in ((1.0, 1.5) if not quick else (1.5,)):
                for fn_name in ("score", "score2", "rsi_matched"):
                    r = at_rate(scores(fn_name, name), df, piv, m, s, ppy * mult)
                    out.append({"set": f"{name}/{pname}", "side": s, "rate_mult": mult, "target_spy": ppy * mult,
                                "fn": fn_name, **r})
    tab = pd.DataFrame(out)
    pd.set_option("display.width", 220)
    print(tab.round(3).to_string(index=False), flush=True)
    return out


# ---------------------------------------------------------------- 追加の帰無: 値動きの順番を壊した偽の価格
def load_base(name):
    src = L.SETS[name][0]
    if src == "sp500_close":
        from skfolio.datasets import load_sp500_index
        c = load_sp500_index()["SP500"].astype(float)
        return pd.DataFrame({"o": c, "h": c, "l": c, "c": c})
    from arch.data import nasdaq, sp500
    base = (nasdaq if src == "nasdaq" else sp500).load()[["Open", "High", "Low", "Close"]].astype(float)
    base.columns = ["o", "h", "l", "c"]
    return base


def synth(base, rng, kind):
    """kind='iid': 日ごとの (始値,高値,安値,終値)/前日終値 の組をまるごと並べ替え（自己相関も変動率の偏りも消える）
       kind='mirror': 変動率の並び |r−μ| は残し、日ごとに確率 1/2 で平均 μ のまわりに鏡映（向きの予測可能性だけ消える）"""
    pc = base.c.shift(1)
    rel = np.column_stack([(base[k] / pc - 1).to_numpy() for k in "ohlc"])[1:]
    n = len(rel)
    if kind == "iid":
        rel2 = rel[rng.permutation(n)]
    else:
        mu = rel[:, 3].mean()
        f = rng.random(n) < 0.5
        rel2 = rel.copy()
        rel2[f, 0] = 2 * mu - rel[f, 0]
        rel2[f, 1] = 2 * mu - rel[f, 2]
        rel2[f, 2] = 2 * mu - rel[f, 1]
        rel2[f, 3] = 2 * mu - rel[f, 3]
    c = np.r_[base.c.iat[0], base.c.iat[0] * np.cumprod(1 + rel2[:, 3])]
    p = c[:-1]
    o = np.r_[base.o.iat[0], p * (1 + rel2[:, 0])]
    h = np.r_[base.h.iat[0], p * (1 + rel2[:, 1])]
    lo = np.r_[base.l.iat[0], p * (1 + rel2[:, 2])]
    return pd.DataFrame({"o": o, "h": h, "l": lo, "c": c}, index=base.index)


def part_geo(quick=False):
    nrep = 20 if quick else 150
    ev_fns = ("score", "score2", "baseline_rsi", "rsi_matched")     # 0〜100 の点灯成績も見る
    auc_fns = ("score_u", "score2_u", "raw_rsi14")                    # AUC10 だけ（切り詰め・同点なし）
    keys = ("recall_pre", "precision", "auc10", "lead_med", "remain_med", "signals_per_year", "pivots_per_year")
    out = {}

    def auc(tg, x, m, s):
        y = tg[f"{s}_10"]
        k = m & ~np.isnan(y)
        return float(roc_auc_score(y[k], np.asarray(x, float)[k]))

    for name, pers in (("nasdaq3x", ("test",)), ("sp3x", ("check", "check_post")),
                       ("sp3x_close", ("oos2019", "pre1999"))):
        base = load_base(name)
        assert np.allclose(L.leverage(base).to_numpy(), data(name)[0].to_numpy())
        df0, piv0 = data(name)
        tg0 = L.targets(piv0, len(df0))
        masks = {p: period(name, p) for p in pers}
        real = {}
        for p in pers:
            for f in ev_fns:
                real[(f, p)] = ev(f, name, p)
            for f in auc_fns:
                real[(f, p)] = {s: {"auc10": auc(tg0, scores(f, name)[s].to_numpy(), masks[p], s)} for s in SIDES}
        for kind in ("iid", "mirror"):
            t0 = time.time()
            rng = np.random.default_rng(11 if kind == "iid" else 12)
            acc = {}
            for _ in range(nrep):
                df = L.leverage(synth(base, rng, kind))
                piv = L.pivots(df)
                tg = L.targets(piv, len(df))
                X = M.osc_features(df)
                u = {fn: {s: M.fitted(fn)[s]["model"].logodds(X) for s in SIDES} for fn in ("score", "score2")}
                sc = {fn: pd.DataFrame({s: M.apply_map(u[fn][s], M.fitted(fn)[s]["anchors"]) for s in SIDES})
                      for fn in ("score", "score2")}
                sc["baseline_rsi"] = L.baseline_rsi(df)
                sc["rsi_matched"] = M.rsi_matched(df)
                r14 = L.rsi(df.c).fillna(50).to_numpy()
                raw = {"score_u": u["score"], "score2_u": u["score2"], "raw_rsi14": {"top": r14, "bot": 100 - r14}}
                for p in pers:
                    m = masks[p]
                    for f in ev_fns:
                        r = L.evaluate(sc[f], df, piv, m)
                        for s in SIDES:
                            for k in keys:
                                acc.setdefault((f, p, s, k), []).append(r[s][k])
                    for f in auc_fns:
                        for s in SIDES:
                            acc.setdefault((f, p, s, "auc10"), []).append(auc(tg, raw[f][s], m, s))
            for (f, p, s, k), v in acc.items():
                v = np.array(v, float)
                rv = float(real[(f, p)][s][k])
                out.setdefault(f"{kind}|{f}|{name}/{p}|{s}", {})[k] = {
                    "real": rv, "null_med": float(np.nanmedian(v)), "null_q05": float(np.nanpercentile(v, 5)),
                    "null_q95": float(np.nanpercentile(v, 95)), "p": float(np.nanmean(v >= rv)),
                    "n": int(np.isfinite(v).sum())}
            print(f"  geo {kind} {name} {nrep} 本 ({time.time() - t0:.0f}s)", flush=True)
            for f in ev_fns + auc_fns:
                for p in pers:
                    o = {s: out[f"{kind}|{f}|{name}/{p}|{s}"] for s in SIDES}
                    print("    ", kind, f"{f:12s}", f"{name}/{p:10s}",
                          {s: {k: (round(o[s][k]["real"], 3), round(o[s][k]["null_med"], 3), round(o[s][k]["p"], 3))
                               for k in ("auc10", "precision", "recall_pre", "pivots_per_year") if k in o[s]}
                           for s in SIDES}, flush=True)
    return out


# ---------------------------------------------------------------- 表
def part_table(quick=False):
    saved = json.load(open(OUT)) if OUT.exists() else {}
    res = saved.get("repro", {}).get("value", {}).get("results", {})
    nul = saved.get("null", {}).get("value", {})
    geo = saved.get("geo", {}).get("value", {})
    rows = []
    for fn_name in ("score", "score2", "baseline_rsi", "rsi_matched", "raw_rsi14"):
        for name, pname in EVAL:
            key = f"{fn_name}|{name}/{pname}"
            if key not in res:
                continue
            for s in SIDES:
                d = res[key][s]
                nt = nul.get(key, {}).get(s, {})
                g = geo.get(f"mirror|{fn_name}|{name}/{pname}|{s}", {})
                ev_ok = fn_name != "raw_rsi14"          # 素の RSI は AUC 専用（0〜100 の点灯成績は意味がない）
                rows.append({"fn": fn_name, "set": f"{name}/{pname}", "side": s, "pivots": d.get("n_pivots"),
                             "事前点灯率": d.get("recall_pre") if ev_ok else None,
                             "何本前": d.get("lead_med") if ev_ok else None,
                             "残り値幅%": d.get("remain_med") if ev_ok else None,
                             "点灯/年": d.get("signals_per_year") if ev_ok else None,
                             "的中率": d.get("precision") if ev_ok else None, "AUC10": d.get("auc10"),
                             "p_点灯率": nt.get("recall_pre", [None] * 3)[2], "p_的中率": nt.get("precision", [None] * 3)[2],
                             "p_AUC": nt.get("auc10", [None] * 3)[2],
                             "鏡映帰無AUC": g.get("auc10", {}).get("null_med"), "鏡映p_AUC": g.get("auc10", {}).get("p"),
                             "鏡映帰無的中率": g.get("precision", {}).get("null_med"),
                             "鏡映p_的中率": g.get("precision", {}).get("p")})
    tab = pd.DataFrame(rows)
    pd.set_option("display.width", 260, "display.max_rows", 500)
    print(tab.round(3).to_string(index=False), flush=True)
    return rows


PARTS = {"causal": part_causal, "repro": part_repro, "null": part_null, "aucdiff": part_aucdiff,
         "traincv": part_traincv, "sens": part_sens, "zzsens": part_zzsens, "curve": part_curve, "geo": part_geo,
         "table": part_table}


def save_part(p, value, seconds):
    saved = json.load(open(OUT)) if OUT.exists() else {"key": "ml"}
    saved[p] = {"value": clean(value), "seconds": seconds}
    with open(OUT, "w") as fh:
        json.dump(saved, fh, ensure_ascii=False, indent=1)


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    quick = "--quick" in sys.argv
    todo = args or [p for p in PARTS if p != "table"] + ["table"]
    for p in todo:
        t0 = time.time()
        print(f"==== {p} ====", flush=True)
        v = PARTS[p](quick)
        save_part(p, v, time.time() - t0)
        print(f"  ({p}: {time.time() - t0:.0f}s)", flush=True)
    print(f"saved {OUT}")


if __name__ == "__main__":
    main()
