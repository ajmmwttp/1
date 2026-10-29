"""TurnLine 候補（担当: 機械学習系, key: ml）

score  = TL-ML-GBM   : HistGradientBoosting（深さ 2・学習率 0.03・100 本・葉の最小 160 件・L2 1.0）
score2 = TL-ML-Logit : L2 正則化ロジスティック回帰（標準化した特徴量・C=0.003）。重み付き和なので式に書ける

どちらも「10 本以内に天井（top_10）/ 底（bot_10）が来る確率」を学習したもので、天井側・底側で別のモデル（同じ設定）。
特徴量はオシレーター 18 本（終値だけで計算。RSI 2/5/14/30、EMA 乖離 z 5/20/60、変動率で割ったリターン 1/5/20/60 本、
短期/長期の変動率比、20/120 本の高値・安値からの距離、連続上昇/下落日数、EMA20-EMA100 のトレンド）。
ZigZag の確定済み転換点の情報（脚の値幅・経過本数・極値からの戻り）と追加 6 本（RSI ダイバージェンス等）も試したが、
train 内の時系列 CV で差が出なかったので、下の選び方（1SE ルール）で使わない方に決まった。

学習・目盛り合わせはすべて nasdaq3x の train 期間（1999-07〜2010-12）だけ:
  - 学習データ: 2010-12-31 で切ったデータだけで ZigZag を計算した正解（確定していない末尾は使わない）。
    さらに末尾 21 本は禁止期間として捨てる。学習済みモデルは固定し、他の期間・他のデータセットにそのまま適用する
  - モデル選び: train 内の前進型時系列 CV（検証 2003-04 / 2005-06 / 2007-08 / 2009-10 の 4 区間。各区間の学習データは
    区間の直前で切ったデータだけで正解を計算し、末尾 21 本を禁止期間）。各系統（HGB / ロジスティック）・各側で
    検証 AUC10 の平均が最良の設定から 1 標準誤差以内で、いちばん単純な設定を選ぶ
  - 0〜100 の目盛り（確率の対数オッズ u を区分線形で写像。定数は train の予測値から決めて固定）:
      0  = train の u の中央値（これ以下は 0）
      25 = 「注意」: train で 25 以上の日の割合が、実際に 10 本以内に転換点がある日の割合（基準率 約 18〜19%）と同じになる位置
      50 = 「そろそろ」: train での点灯（50 到達、35 未満で再点灯可）が転換点の数（年約 5 回）の 1.5 倍になる位置
      80 = 「圏」: train の u の 97% 点（上位 3% の日）
      100 = train の u の最大値（それ以上は 100）

実行: python3 cand_ml.py          → (0) train CV と選択 (a) run_all 表 (b) check_causal (c) null_test(n=200) (d) results/ml.json
      python3 cand_ml.py --quick  → (0) を省略（選択済みの設定を使う）
"""
import argparse
import itertools
import json
import math
import os
import sys
import time
import warnings

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, roc_auc_score
from sklearn.preprocessing import SplineTransformer, StandardScaler

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import turnline_lab as L  # noqa: E402

warnings.filterwarnings("ignore", category=RuntimeWarning)
KEY = "ml"
TRAIN = ("1999-07-01", "2010-12-31")
EMBARGO = 21                       # 学習データ末尾の禁止期間（本）
FOLDS = [("2003-01-01", "2004-12-31"), ("2005-01-01", "2006-12-31"),
         ("2007-01-01", "2008-12-31"), ("2009-01-01", "2010-12-31")]
TARGET_MULT = 1.5                  # train の点灯/年 = 転換点/年 × 1.5
Q_ZERO, Q_ZONE = 0.50, 0.97        # 0 と 80 を置く train の分位点

OSC = ["rsi2", "rsi5", "rsi14", "rsi30", "z5", "z20", "z60", "ret1", "ret5", "ret20", "ret60", "vr",
       "dhi20", "dlo20", "dhi120", "dlo120", "streak", "trend"]
EXTRA = ["rsidd60", "rsidu60", "upfrac20", "acc5", "tsh20", "tsl20"]
ZZ = ["legdir", "leg_move", "retr", "since_ext", "leg_bars", "curmove"]
ZZC = ["leg_move", "retr", "since_ext", "leg_bars", "curmove"]

HGB_FINAL = {"max_depth": 2, "learning_rate": 0.03, "max_iter": 100, "min_samples_leaf": 160, "l2_regularization": 1.0}
FINAL = {
    "score": {"name": "TL-ML-GBM", "kind": "hgb", "fs": "osc", "hp": HGB_FINAL},
    "score2": {"name": "TL-ML-Logit", "kind": "lr_lin", "fs": "osc", "hp": {"C": 0.003}},
}


# ---------------------------------------------------------------- 特徴量（すべて因果的）
def _vol(lc, span):
    """日次対数リターンの変動率（EWMA）"""
    return lc.diff().ewm(span=span, min_periods=min(20, span)).std()


def osc_features(df):
    """オシレーター 18 本。終値だけ（高値・安値は使わない＝終値だけのデータでも同じ意味になる）"""
    c = df.c
    lc = np.log(c)
    n = len(df)
    vol = _vol(lc, 60).fillna(0.03)
    vol10 = _vol(lc, 10).fillna(vol)
    thr = pd.Series(L.swing_threshold(df), index=df.index)    # ZigZag の反転幅（変動率から。因果的）
    f = {}
    for p in (2, 5, 14, 30):
        f[f"rsi{p}"] = L.rsi(c, p) - 50
    for p in (5, 20, 60):
        f[f"z{p}"] = (lc - lc.ewm(span=p, adjust=False).mean()) / (vol * np.sqrt(p))
    for p in (1, 5, 20, 60):
        f[f"ret{p}"] = (lc - lc.shift(p)) / (vol * np.sqrt(p))
    f["vr"] = np.log(vol10 / vol)
    for p in (20, 120):
        f[f"dhi{p}"] = np.log(c / c.rolling(p, min_periods=1).max()) / thr
        f[f"dlo{p}"] = np.log(c / c.rolling(p, min_periods=1).min()) / thr
    d = np.sign(c.diff().fillna(0)).to_numpy()
    st = np.zeros(n)
    for i in range(1, n):
        if d[i] > 0:
            st[i] = st[i - 1] + 1 if st[i - 1] > 0 else 1
        elif d[i] < 0:
            st[i] = st[i - 1] - 1 if st[i - 1] < 0 else -1
    f["streak"] = np.clip(st, -8, 8)
    f["trend"] = (lc.ewm(span=20, adjust=False).mean() - lc.ewm(span=100, adjust=False).mean()) / (vol * np.sqrt(50))
    return pd.DataFrame(f, index=df.index)


def extra_features(df, X):
    """追加 6 本（選択で不採用）: RSI14 の 60 本高値/安値からの差、20 本の上昇日比率、z20 の 5 本変化、20 本高値/安値からの経過"""
    c = df.c
    r14 = L.rsi(c, 14)
    out = pd.DataFrame(index=df.index)
    out["rsidd60"] = r14 - r14.rolling(60, min_periods=1).max()
    out["rsidu60"] = r14 - r14.rolling(60, min_periods=1).min()
    out["upfrac20"] = (c.diff() > 0).astype(float).rolling(20, min_periods=1).mean()
    out["acc5"] = X["z20"] - X["z20"].shift(5)
    out["tsh20"] = c.rolling(20, min_periods=1).apply(lambda a: len(a) - 1 - np.argmax(a), raw=True) / 20
    out["tsl20"] = c.rolling(20, min_periods=1).apply(lambda a: len(a) - 1 - np.argmin(a), raw=True) / 20
    return out


def zz_features(df):
    """ZigZag の状態（選択で不採用）: L.last_confirmed（各バーで確定済みの最新転換点）と、そこから今までの終値だけを使う"""
    n = len(df)
    c = df.c.to_numpy(float)
    piv = L.pivots(df)
    b, k, pr = L.last_confirmed(piv, n)
    ext, t_ext = np.full(n, np.nan), np.full(n, np.nan)
    rows = list(piv.itertuples())
    for j, r in enumerate(rows):
        e = rows[j + 1].confirm if j + 1 < len(rows) else n
        seg = c[r.bar + 1:e]
        sidx = np.arange(r.bar + 1, e)
        if len(seg):
            run = np.maximum.accumulate(seg) if r.kind == "L" else np.minimum.accumulate(seg)
            last_new = np.maximum.accumulate(np.where(seg == run, sidx, -1))
        for t in range(r.confirm, e):
            if t >= r.bar + 1:
                ii = t - (r.bar + 1)
                ext[t], t_ext[t] = run[ii], t - last_new[ii]
            else:                                  # 転換点と確定が同じバー
                ext[t], t_ext[t] = c[t], 0
    th = L.swing_threshold(df)
    up, dn = (k == -1).astype(float), (k == 1).astype(float)
    has = k != 0
    with np.errstate(invalid="ignore", divide="ignore"):
        out = pd.DataFrame({
            "legdir": up - dn,
            "leg_move": np.where(has, np.abs(np.log(ext / pr)) / th, np.nan),
            "retr": np.where(has, np.abs(np.log(ext / c)) / th, np.nan),
            "since_ext": np.where(has, np.log1p(t_ext), np.nan),
            "leg_bars": np.where(has, np.log1p(np.arange(n) - b), np.nan),
            "curmove": np.where(has, np.log(c / pr) * (up - dn) / th, np.nan),
        }, index=df.index)
    return out


def all_features(df):
    X = osc_features(df)
    return pd.concat([X, extra_features(df, X), zz_features(df)], axis=1)


# ---------------------------------------------------------------- モデル
def design(X, fs):
    """ロジスティック回帰に渡す列。ZigZag 列は脚の向き（上昇脚/下降脚）ごとの交互作用にする"""
    out = X[OSC + (EXTRA if fs == "ext" else [])].copy()
    if fs in ("all", "ext"):
        up = (X.legdir == 1).astype(float)
        dn = (X.legdir == -1).astype(float)
        out["up"] = up
        for c in ZZC:
            out[c + "_u"] = X[c].fillna(0) * up
            out[c + "_d"] = X[c].fillna(0) * dn
    return out


class Model:
    """kind: 'lr_lin'（標準化＋L2 ロジスティック）/ 'lr_spl'（スプライン基底＋L2 ロジスティック）/ 'hgb'"""

    def __init__(self, kind, fs, **hp):
        self.kind, self.fs, self.hp = kind, fs, hp

    def _mat(self, X, fit=False):
        if self.kind == "hgb":
            cols = OSC + (EXTRA if self.fs == "ext" else []) + (ZZ if self.fs in ("all", "ext") else [])
            return X[cols].to_numpy(float)
        D = design(X, self.fs)
        if self.kind == "lr_lin":
            A = np.nan_to_num(D.to_numpy(float))
            if fit:
                self.sc = StandardScaler().fit(A)
            return self.sc.transform(A)
        cont = [c for c in D.columns if c != "up"]
        A = np.nan_to_num(D[cont].to_numpy(float))
        if fit:
            self.spl = SplineTransformer(n_knots=5, degree=3, knots="quantile", extrapolation="constant").fit(A)
        B = self.spl.transform(A)
        if "up" in D.columns:
            B = np.column_stack([B, D["up"].to_numpy(float)])
        if fit:
            self.sc = StandardScaler().fit(B)
        return self.sc.transform(B)

    def fit(self, X, y):
        A = self._mat(X, fit=True)
        if self.kind == "hgb":
            self.m = HistGradientBoostingClassifier(random_state=0, early_stopping=False, **self.hp)
        else:
            self.m = LogisticRegression(C=self.hp["C"], max_iter=5000)
        self.m.fit(A, y)
        return self

    def logodds(self, X):
        return logit(self.m.predict_proba(self._mat(X))[:, 1])


def logit(p):
    p = np.clip(np.asarray(p, float), 1e-6, 1 - 1e-6)
    return np.log(p / (1 - p))


# ---------------------------------------------------------------- 0〜100 の目盛り
def apply_map(u, anchors):
    xs = np.array([a for a, _ in anchors], float)
    for i in range(1, len(xs)):
        xs[i] = max(xs[i], xs[i - 1] + 1e-9)
    return np.interp(u, xs, [b for _, b in anchors])


def signals_per_year(score, mask):
    sig = L.crossings_up(np.nan_to_num(score))
    return mask[sig].sum() / (mask.sum() / 252)


def calibrate_map(u, mask, base, target):
    """train の u から目盛りを決める（ラベルは基準率だけ使う）。返り値: (anchors, 点灯/年)"""
    ut = u[mask]
    q0, q25, q80, q100 = np.quantile(ut, [Q_ZERO, 1 - base, Q_ZONE, 1.0])
    best = None
    for u50 in np.linspace(q25, q80, 402)[1:-1]:
        anchors = [(q0, 0.0), (q25, 25.0), (u50, 50.0), (q80, 80.0), (q100, 100.0)]
        spy = signals_per_year(apply_map(u, anchors), mask)
        if best is None or abs(spy - target) < abs(best[1] - target):
            best = (anchors, spy)
    return [(float(a), float(b)) for a, b in best[0]], float(best[1])


# ---------------------------------------------------------------- 学習（nasdaq3x の train だけ）
def train_frame():
    """nasdaq3x を train 期間の終わりで切ったもの（以降のデータは学習に一切渡さない）"""
    df = L.load("nasdaq3x")
    return df[df.index <= TRAIN[1]].copy()


def labels_upto(df, end):
    """df.iloc[:end] だけで ZigZag を計算した正解（end 以降と、まだ確定していない末尾は NaN）"""
    sub = df.iloc[:end]
    tg = L.targets(L.pivots(sub), len(sub))
    out = {}
    for k in ("top_10", "bot_10"):
        v = np.full(len(df), np.nan)
        v[:end] = tg[k]
        out[k] = v
    return out


def train_context():
    df = train_frame()
    n, idx = len(df), df.index
    piv = L.pivots(df)
    tg = L.targets(piv, n)
    trmask = L.period_mask(df, TRAIN)
    leg = L.leg_stats(df, piv, trmask)
    target = {"top": TARGET_MULT * leg["H"]["per_year"], "bot": TARGET_MULT * leg["L"]["per_year"]}
    base = {s: float(np.nanmean(tg[f"{s}_10"][trmask])) for s in ("top", "bot")}
    i0 = int(np.searchsorted(idx, pd.Timestamp(TRAIN[0])))
    return dict(df=df, n=n, idx=idx, piv=piv, tg=tg, trmask=trmask, target=target, base=base, i0=i0)


_FITTED = {}


def fitted(fn_name):
    """最終モデル（学習は 1 回だけ。同じ手順なら毎回同じ結果）"""
    if fn_name in _FITTED:
        return _FITTED[fn_name]
    spec = FINAL[fn_name]
    ctx = train_context()
    df, n = ctx["df"], ctx["n"]
    X = osc_features(df) if spec["fs"] == "osc" else all_features(df)
    lab = labels_upto(df, n)
    rows = np.zeros(n, bool)
    rows[ctx["i0"]:n - EMBARGO] = True
    out = {"spec": spec, "base": ctx["base"], "target": ctx["target"]}
    for side in ("top", "bot"):
        y = lab[f"{side}_10"]
        rr = rows & ~np.isnan(y)
        m = Model(spec["kind"], spec["fs"], **spec["hp"]).fit(X[rr], y[rr].astype(int))
        u = m.logodds(X)
        anchors, spy = calibrate_map(u, ctx["trmask"], ctx["base"][side], ctx["target"][side])
        out[side] = {"model": m, "anchors": anchors, "train_spy": spy, "n_rows": int(rr.sum()),
                     "last_row": str(df.index[np.flatnonzero(rr)[-1]].date())}
    _FITTED[fn_name] = out
    return out


def _score(df, fn_name):
    f = fitted(fn_name)
    X = osc_features(df) if f["spec"]["fs"] == "osc" else all_features(df)
    return pd.DataFrame({side: apply_map(f[side]["model"].logodds(X), f[side]["anchors"]) for side in ("top", "bot")},
                        index=df.index)


def score(df):
    """TL-ML-GBM: HistGradientBoosting の確率 → 0〜100"""
    return _score(df, "score")


def score2(df):
    """TL-ML-Logit: L2 ロジスティック回帰の確率 → 0〜100"""
    return _score(df, "score2")


# ---------------------------------------------------------------- RSI の基準（同じ目盛り合わせ）
_RSI_MAP = {}


def rsi_matched(df):
    """RSI14 を候補と同じ手順（train の分位点・点灯/年）で 0〜100 にしたもの。点灯回数をそろえた比較用"""
    if not _RSI_MAP:
        ctx = train_context()
        r = L.rsi(ctx["df"].c).fillna(50).to_numpy()
        for side, u in (("top", r), ("bot", 100 - r)):
            _RSI_MAP[side] = calibrate_map(u, ctx["trmask"], ctx["base"][side], ctx["target"][side])[0]
    r = L.rsi(df.c).fillna(50).to_numpy()
    return pd.DataFrame({"top": apply_map(r, _RSI_MAP["top"]), "bot": apply_map(100 - r, _RSI_MAP["bot"])},
                        index=df.index)


# ---------------------------------------------------------------- train 内の時系列 CV と選択
def grid():
    g = []
    for fs in ("osc", "all"):
        for C in (0.003, 0.03, 0.3):
            g.append(("lr_lin", fs, {"C": C}))
            g.append(("lr_spl", fs, {"C": C}))
        for d, lr, it, msl in itertools.product((2, 3), (0.03, 0.1), (100, 300), (40, 160)):
            g.append(("hgb", fs, {"max_depth": d, "learning_rate": lr, "max_iter": it,
                                  "min_samples_leaf": msl, "l2_regularization": 1.0}))
    h = lambda msl: {"max_depth": 2, "learning_rate": 0.03, "max_iter": 100, "min_samples_leaf": msl,  # noqa: E731
                     "l2_regularization": 1.0}
    g += [("lr_lin", "ext", {"C": 0.003}), ("lr_lin", "ext", {"C": 0.03}), ("lr_spl", "ext", {"C": 0.003}),
          ("hgb", "ext", h(40)), ("hgb", "ext", h(160))]
    return g


def complexity(kind, fs, hp):
    """単純さの順（小さいほど単純）: 系統 → 特徴量の数 → 木の深さ → 学習率×本数 → 葉の最小件数（大きいほど単純）→ C"""
    nf = {"osc": len(OSC), "all": len(OSC) + len(ZZ), "ext": len(OSC) + len(ZZ) + len(EXTRA)}[fs]
    if kind == "hgb":
        return (2, nf, hp["max_depth"], hp["learning_rate"] * hp["max_iter"], -hp["min_samples_leaf"], 0)
    return ({"lr_lin": 0, "lr_spl": 1}[kind], nf, 0, 0, 0, hp["C"])


def cv_context():
    ctx = train_context()
    df, n, idx = ctx["df"], ctx["n"], ctx["idx"]
    folds = []
    for a, b in FOLDS:
        vs = int(np.searchsorted(idx, pd.Timestamp(a)))
        ve = int(np.searchsorted(idx, pd.Timestamp(b), side="right"))
        trn = np.zeros(n, bool)
        trn[ctx["i0"]:vs - EMBARGO] = True
        folds.append((vs, ve, labels_upto(df, vs), trn))
    oof = np.zeros(n, bool)
    for vs, ve, _, _ in folds:
        oof[vs:ve] = True
    ctx.update(folds=folds, oofmask=oof)
    return ctx


def cv_oof(ctx, X, kind, fs, hp, side):
    """前進型 CV の検証区間の予測（対数オッズ）と区間ごとの AUC10"""
    n = ctx["n"]
    uo = np.full(n, np.nan)
    aucs = []
    yall = ctx["tg"][f"{side}_10"]
    for vs, ve, lab, trn in ctx["folds"]:
        y = lab[f"{side}_10"]
        rr = trn & ~np.isnan(y)
        m = Model(kind, fs, **hp).fit(X[rr], y[rr].astype(int))
        uo[vs:ve] = m.logodds(X.iloc[vs:ve])
        yv = yall[vs:ve]
        k = ~np.isnan(yv)
        aucs.append(roc_auc_score(yv[k], uo[vs:ve][k]))
    return uo, aucs


def oof_event_metrics(ctx, u_top, u_bot):
    """検証区間（2003〜2010）の予測を同じ目盛り合わせ（区間内の分位点・点灯/年）で 0〜100 にして evaluate"""
    sc = {}
    for side, u in (("top", u_top), ("bot", u_bot)):
        uu = np.where(np.isnan(u), np.nanmin(u), u)
        anchors, _ = calibrate_map(uu, ctx["oofmask"], ctx["base"][side], ctx["target"][side])
        sc[side] = np.where(ctx["oofmask"], apply_map(uu, anchors), 0.0)
    return L.evaluate(pd.DataFrame(sc, index=ctx["idx"]), ctx["df"], ctx["piv"], ctx["oofmask"])


def run_selection(verbose=True):
    t0 = time.time()
    ctx = cv_context()
    X = all_features(ctx["df"])
    rows = []
    oofs = {}
    g = grid()
    for gi, (kind, fs, hp) in enumerate(g):
        for side in ("top", "bot"):
            uo, aucs = cv_oof(ctx, X, kind, fs, hp, side)
            oofs[(gi, side)] = uo
            y = ctx["tg"][f"{side}_10"]
            k = ctx["oofmask"] & ~np.isnan(y)
            smooth = pd.Series(uo).ewm(span=3, adjust=False).mean().to_numpy()
            rows.append({"gi": gi, "kind": kind, "fs": fs, "hp": hp, "side": side,
                         "fold_aucs": [float(a) for a in aucs], "fold_auc_mean": float(np.mean(aucs)),
                         "fold_auc_se": float(np.std(aucs, ddof=1) / math.sqrt(len(aucs))),
                         "oof_auc10": float(roc_auc_score(y[k], uo[k])),
                         "oof_auc10_ema3": float(roc_auc_score(y[k], smooth[k])),
                         "oof_ap_lift": float(average_precision_score(y[k], uo[k]) / y[k].mean())})
        if verbose and gi % 8 == 0:
            print(f"  cv {gi + 1}/{len(g)}  {time.time() - t0:.0f}s", flush=True)
    # ensemble（対数オッズの平均。選択の対象外＝参考）
    def find(kind, fs, hp):
        return next(i for i, c in enumerate(g) if c == (kind, fs, hp))
    h40 = {"max_depth": 2, "learning_rate": 0.03, "max_iter": 100, "min_samples_leaf": 40, "l2_regularization": 1.0}
    ens = {"ens(lr_spl osc .003 + hgb osc msl40)": [find("lr_spl", "osc", {"C": 0.003}), find("hgb", "osc", h40)],
           "ens(lr_lin all .03 + hgb all msl40)": [find("lr_lin", "all", {"C": 0.03}), find("hgb", "all", h40)],
           "ens(4 models)": [find("lr_lin", "osc", {"C": 0.003}), find("lr_spl", "osc", {"C": 0.003}),
                             find("hgb", "osc", h40), find("hgb", "all", h40)],
           "ens(lr_lin ext .03 + hgb ext msl40)": [find("lr_lin", "ext", {"C": 0.03}), find("hgb", "ext", h40)]}
    ens_rows = []
    for name, parts in ens.items():
        for side in ("top", "bot"):
            u = np.mean([oofs[(p, side)] for p in parts], axis=0)
            y = ctx["tg"][f"{side}_10"]
            aucs = []
            for vs, ve, _, _ in ctx["folds"]:
                kk = ~np.isnan(y[vs:ve])
                aucs.append(roc_auc_score(y[vs:ve][kk], u[vs:ve][kk]))
            ens_rows.append({"name": name, "side": side, "fold_aucs": [float(a) for a in aucs],
                             "fold_auc_mean": float(np.mean(aucs))})
    # 系統ごとの 1SE ルール
    res = pd.DataFrame(rows)
    picks = {}
    for fam, kinds in (("hgb", ("hgb",)), ("logit", ("lr_lin", "lr_spl"))):
        for side in ("top", "bot"):
            sub = res[(res.side == side) & res.kind.isin(kinds)]
            best = sub.loc[sub.fold_auc_mean.idxmax()]
            ok = sub[sub.fold_auc_mean >= best.fold_auc_mean - best.fold_auc_se]
            ok = ok.assign(cx=[complexity(r.kind, r.fs, r.hp) for r in ok.itertuples()]).sort_values("cx")
            pick = ok.iloc[0]
            picks[(fam, side)] = {"best": {"kind": best.kind, "fs": best.fs, "hp": best.hp,
                                           "fold_auc_mean": best.fold_auc_mean, "se": best.fold_auc_se},
                                  "pick": {"gi": int(pick.gi), "kind": pick.kind, "fs": pick.fs, "hp": pick.hp,
                                           "fold_auc_mean": pick.fold_auc_mean, "fold_aucs": pick.fold_aucs},
                                  "n_eligible": int(len(ok))}
    # RSI14 の CV 値（同じ検証区間）
    r = L.rsi(ctx["df"].c).fillna(50).to_numpy()
    rsi_cv = {}
    for side, u in (("top", r), ("bot", 100 - r)):
        y = ctx["tg"][f"{side}_10"]
        aucs = []
        for vs, ve, _, _ in ctx["folds"]:
            kk = ~np.isnan(y[vs:ve])
            aucs.append(roc_auc_score(y[vs:ve][kk], u[vs:ve][kk]))
        k = ctx["oofmask"] & ~np.isnan(y)
        rsi_cv[side] = {"fold_aucs": [float(a) for a in aucs], "fold_auc_mean": float(np.mean(aucs)),
                        "oof_auc10": float(roc_auc_score(y[k], u[k])),
                        "oof_ap_lift": float(average_precision_score(y[k], u[k]) / y[k].mean())}
    rsi_ev = oof_event_metrics(ctx, r.astype(float), (100 - r).astype(float))
    # 選んだ設定の CV での点灯成績（検証区間の予測を同じ目盛り合わせで）
    pick_ev = {}
    for fam in ("hgb", "logit"):
        pick_ev[fam] = oof_event_metrics(ctx, oofs[(picks[(fam, "top")]["pick"]["gi"], "top")],
                                         oofs[(picks[(fam, "bot")]["pick"]["gi"], "bot")])
    if verbose:
        pd.set_option("display.width", 250, "display.max_colwidth", 90, "display.max_rows", 200)
        show = res.assign(hp=res.hp.map(lambda d: ",".join(f"{k[:3]}={v}" for k, v in d.items())))
        for side in ("top", "bot"):
            print(f"\n[train CV] {side}: 検証 AUC10（4 区間の平均）上位 15 / 全 {len(g)} 設定")
            print(show[show.side == side].sort_values("fold_auc_mean", ascending=False)
                  .head(15)[["kind", "fs", "hp", "fold_auc_mean", "fold_auc_se", "oof_auc10", "oof_auc10_ema3",
                             "oof_ap_lift"]].round(3).to_string(index=False))
        print("\n[train CV] ensemble（参考）:", [(e["name"], e["side"], round(e["fold_auc_mean"], 3)) for e in ens_rows])
        print("[train CV] RSI14:", {s: round(v["fold_auc_mean"], 3) for s, v in rsi_cv.items()})
        for (fam, side), p in picks.items():
            print(f"[選択] {fam:5s} {side}: 最良 {p['best']['kind']}/{p['best']['fs']} {p['best']['hp']} "
                  f"{p['best']['fold_auc_mean']:.3f}±{p['best']['se']:.3f} → 1SE 内で最も単純 "
                  f"{p['pick']['kind']}/{p['pick']['fs']} {p['pick']['hp']} {p['pick']['fold_auc_mean']:.3f}")
        for fam, ev in list(pick_ev.items()) + [("RSI14", rsi_ev)]:
            print(f"[train CV 点灯成績 2003-2010] {fam}: " + " / ".join(
                f"{s} 事前点灯率 {ev[s]['recall_pre']:.2f} 何本前 {ev[s]['lead_med']} 残り {ev[s]['remain_med']:.1f}% "
                f"点灯/年 {ev[s]['signals_per_year']:.1f} 的中率 {ev[s]['precision']:.2f}" for s in ("top", "bot")))
        print(f"  selection done {time.time() - t0:.0f}s")
    return {"n_settings_model": len(g) * 2, "n_settings_smoothing": len(g) * 2, "n_settings_ensemble": len(ens) * 2,
            "folds": FOLDS, "embargo": EMBARGO, "rows": rows, "ensembles": ens_rows,
            "picks": {f"{fam}/{side}": v for (fam, side), v in picks.items()}, "rsi_cv": rsi_cv,
            "event_oof": {"hgb": pick_ev["hgb"], "logit": pick_ev["logit"], "RSI14_matched": rsi_ev}}


# ---------------------------------------------------------------- 実行
def _clean(o):
    if isinstance(o, dict):
        return {str(k): _clean(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [_clean(v) for v in o]
    if isinstance(o, (np.floating, float)):
        return None if not np.isfinite(o) else float(o)
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, np.bool_):
        return bool(o)
    return o


def smoothness(sc, mask):
    out = {}
    for side in ("top", "bot"):
        d = np.abs(np.diff(sc[side].to_numpy(float)[mask]))
        out[side] = {"med_abs_change": float(np.median(d)), "p90_abs_change": float(np.percentile(d, 90)),
                     "frac_ge25": float((sc[side].to_numpy()[mask] >= 25).mean()),
                     "frac_ge80": float((sc[side].to_numpy()[mask] >= 80).mean())}
    return out


def evaluate_fn(fn, label, n_null, null_sets):
    t0 = time.time()
    res = L.run_all(fn)
    tab = L.summary_table(res)
    print(f"\n==== {label} ====")
    print(tab.round(3).to_string(index=False))
    out = {"results": {f"{a}/{b}": v for (a, b), v in res.items()}, "null": {}, "smooth": {}}
    for name, (_, periods) in L.SETS.items():
        df = L.load(name)
        sc = fn(df)
        piv = L.pivots(df)
        for pname, per in periods.items():
            m = L.period_mask(df, per)
            out["smooth"][f"{name}/{pname}"] = smoothness(sc, m)
            if f"{name}/{pname}" in null_sets:
                nt = L.null_test(sc, df, piv, m, n=n_null)
                out["null"][f"{name}/{pname}"] = nt
                print(f"null_test {name}/{pname} (実測, 帰無の中央値, p):")
                for side in ("top", "bot"):
                    print("   ", side, {k: tuple(round(x, 3) for x in v) for k, v in nt[side].items()})
    print(f"  ({time.time() - t0:.0f}s)")
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--quick", action="store_true", help="train CV の再計算を省略")
    ap.add_argument("--n-null", type=int, default=200)
    args = ap.parse_args()
    pd.set_option("display.width", 250, "display.max_columns", 30)
    t0 = time.time()
    sel = None
    if not args.quick:
        print("==== (0) train 内の時系列 CV と 1SE ルールでの選択（nasdaq3x 1999-07〜2010-12 だけ）====")
        sel = run_selection()
        want = {("hgb", "top"): FINAL["score"], ("hgb", "bot"): FINAL["score"],
                ("logit", "top"): FINAL["score2"], ("logit", "bot"): FINAL["score2"]}
        same = all((sel["picks"][f"{f}/{s}"]["pick"]["kind"], sel["picks"][f"{f}/{s}"]["pick"]["fs"],
                    sel["picks"][f"{f}/{s}"]["pick"]["hp"]) == (w["kind"], w["fs"], w["hp"]) for (f, s), w in want.items())
        print("選択の再現 → FINAL と一致:", same)
        if not same:
            raise SystemExit("選択結果が FINAL と違う（設定を確認すること）")
    null_sets = ("nasdaq3x/test", "sp3x_close/oos2019")
    cands = []
    for fn_name, fn in (("score", score), ("score2", score2)):
        spec = FINAL[fn_name]
        f = fitted(fn_name)
        params = {"model": spec["kind"], "features": OSC, "hyperparams": spec["hp"], "embargo": EMBARGO,
                  "train": TRAIN, "target_signals_per_year": f["target"], "train_base_rate": f["base"],
                  "map": {s: {"anchors_logodds_to_score": f[s]["anchors"], "train_signals_per_year": f[s]["train_spy"],
                              "n_train_rows": f[s]["n_rows"], "last_train_row": f[s]["last_row"]} for s in ("top", "bot")}}
        if spec["kind"] == "lr_lin":
            for s in ("top", "bot"):
                m = f[s]["model"]
                w = m.m.coef_[0] / m.sc.scale_
                params["map"][s]["logodds_formula"] = {
                    "intercept": float(m.m.intercept_[0] - np.sum(m.m.coef_[0] * m.sc.mean_ / m.sc.scale_)),
                    "coef": {k: float(v) for k, v in zip(OSC, w)},
                    "coef_standardized": {k: float(v) for k, v in zip(OSC, m.m.coef_[0])}}
        ev = evaluate_fn(fn, f"{spec['name']} ({fn_name})", args.n_null, null_sets)
        causal = {}
        for dname, start in (("nasdaq3x", 0.65), ("sp3x", 0.3), ("sp3x_close", 0.3)):
            causal[dname] = L.check_causal(fn, L.load(dname), start=start)
        causal["nasdaq3x_start0.05_n20"] = L.check_causal(fn, L.load("nasdaq3x"), n_cuts=20, start=0.05, seed=1)
        print("check_causal:", causal)
        desc = {"score": "HistGradientBoosting（深さ2・学習率0.03・100本・葉の最小160・L2 1.0）で、オシレーター18本"
                         "（RSI 2/5/14/30、EMA乖離z 5/20/60、変動率で割ったリターン 1/5/20/60本、短期/長期の変動率比、"
                         "20/120本の高値・安値からの距離、連続上昇/下落日数、EMA20-EMA100）から『10本以内に天井/底』の確率を出す。"
                         "天井側・底側で別モデル。学習は nasdaq3x の train だけ（2010-12-31 で切ったデータの ZigZag を正解、"
                         "末尾21本は禁止期間）。確率の対数オッズを train の分位点で区分線形に 0〜100 へ"
                         "（中央値→0、基準率の分位点→25、点灯 年約7.4回→50、97%点→80、最大→100）",
                "score2": "L2 正則化ロジスティック回帰（C=0.003、train で標準化）で同じオシレーター18本から"
                          "『10本以内に天井/底』の確率を出す（重み付き和なので式に書ける。係数は params.map.*.logodds_formula）。"
                          "天井側・底側で別モデル。学習・目盛り合わせは TL-ML-GBM と同じ"}[fn_name]
        cands.append({"name": spec["name"], "function": fn_name, "description": desc, "params": params,
                      "causal_max_diff": float(max(causal.values())), "causal_by_set": causal,
                      "results": ev["results"], "null": ev["null"], "smoothness": ev["smooth"]})
    refs = {}
    for label, fn, nulls in (("RSI14 (L.baseline_rsi)", L.baseline_rsi, ()),
                             ("RSI14 matched (同じ目盛り合わせ・点灯/年)", rsi_matched, null_sets),
                             ("ideal (未来を使う上限)", L.ideal, ())):
        ev = evaluate_fn(fn, label, args.n_null, nulls)
        refs[label] = {"results": ev["results"], "null": ev["null"], "smoothness": ev["smooth"]}
    refs["RSI14 matched (同じ目盛り合わせ・点灯/年)"]["map"] = {s: _RSI_MAP[s] for s in ("top", "bot")}
    out = {"key": KEY, "candidates": cands, "references": refs}
    if sel is not None:
        out["train_cv"] = sel
    path = os.path.join(HERE, "results", f"{KEY}.json")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as fh:
        json.dump(_clean(out), fh, ensure_ascii=False, indent=1, default=float)
    print(f"\nsaved {path}  ({time.time() - t0:.0f}s)")


if __name__ == "__main__":
    main()
