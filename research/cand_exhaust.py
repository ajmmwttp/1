"""TurnLine 候補: 疲れ・時間・ハザード系 (key: exhaust)

score  : 脚ハザード＋勢い … ZigZag の「確定済み転換点」から見た今の脚の進み具合（反転幅 θ の何倍動いたか・
         極値からの戻り・経過本数）に、勢い（10日騰落の変動率比）と値幅の広がり（ATR5/ATR20）を足した
         「10本以内に転換点が来る確率」（離散時間ハザード＝ロジスティック回帰＋3次スプライン）。
score2 : 疲れ指標だけ … TD セットアップ数・連続陽線/陰線日数・勢いの衰え・値幅の縮み/広がり・20日高値からの距離
         （ZigZag は使わない）で同じ確率を推定したもの。

学習・しきい値（p50）・目盛り合わせはすべて nasdaq3x の train 期間（1999-07〜2010-12）だけで行う。
目的変数（10本以内に天井/底）は train 末尾で切ったデータの ZigZag から作る（test 期間の値動きを使わない）。
出力は top/bot とも 0〜100。確率 p を [0, p50/2, p50, (1+p50)/2, 1] → [0, 25, 50, 80, 100] の折れ線で写像し、
p50 は train で「50 到達（35 でリセット）」が年 7 回（転換点 年約5回の 1.4 倍）になる値。

python3 cand_exhaust.py で (a) run_all の表 (b) check_causal (c) null_test(n=200) を表示し results/exhaust.json に保存。
追加の参考情報: RSI を同じ点灯回数に合わせた基準、ランダムウォーク帰無（日次の値動きの順番だけを入れ替えた系列で
同じ指標を評価＝「上がった/下がった後に転換点が来る」という ZigZag の幾何だけで出る成績）、点灯後10本の騰落、
train 内 4 分割ブロック CV（学習に使っていない区間での成績）。
"""
import json
import sys
import time
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import SplineTransformer, StandardScaler

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import turnline_lab as L  # noqa: E402

warnings.filterwarnings("ignore")
KEY = "exhaust"
TRAIN = L.SETS["nasdaq3x"][1]["train"]
TARGET_RATE = 7.0          # train での「そろそろ」点灯回数/年（転換点 約5回/年 の 1.4 倍＝許容幅 1〜2 倍の中央）
HORIZON = L.K_BARS         # 10 本以内に転換点 を目的変数にする

# 特徴量のクリップ範囲（外れ値でスプラインが暴れないように。範囲は train を見て決めた固定値）
CLIP = {"R_up": (0, 6), "R_dn": (0, 3), "age_up": (0, 120), "age_dn": (0, 60), "G_top": (0, 1), "G_bot": (0, 1),
        "td_ss": (0, 15), "td_bs": (0, 15), "cu": (0, 7), "cd": (0, 7), "z5": (-4, 4), "z10": (-4, 4),
        "near_hi": (0, 25), "atr_ratio": (0.3, 3), "fade_top": (0, 6), "shrink": (0, 4), "up10": (0, 10), "dn10": (0, 10)}

SPECS = {
    "score": {
        "name": "脚ハザード＋勢い（ZigZag の脚の進み具合）",
        "top": {"cols": ["R_up", "G_top"], "C": 1.0},
        "bot": {"cols": ["R_dn", "G_bot", "age_dn", "z10", "atr_ratio"], "C": 0.1},
    },
    "score2": {
        "name": "疲れ指標だけ（TD・連続日数・勢いの衰え、ZigZag 不使用）",
        "top": {"cols": ["z5", "near_hi", "fade_top"], "C": 1.0},
        "bot": {"cols": ["td_bs", "cd", "z10", "near_hi", "atr_ratio", "fade_top", "dn10"], "C": 0.1},
    },
}


# ---------------------------------------------------------------- 特徴量（すべてそのバーの終値までの情報だけ）
def swing_state(df):
    """確定済みの最新転換点（L.last_confirmed）を起点にした「今の脚」の状態。
    上昇スイング = 直近の安値（確定済みの底、または確定天井の後の暫定安値）から今までの最高値まで
      R_up  : 上昇幅 /θ（θ = swing_threshold = 正解 ZigZag の反転幅。安値のバーの値）
      G_top : 最高値からの押し（終値）/θ（最高値のバーの値）。1 に達すると天井が確定する目安
      age_up: 安値からの経過本数
    下降スイング = 直近の高値（確定済みの天井、または確定底の後の暫定高値）から今までの最安値まで
      R_dn, G_bot, age_dn: 上の上下反対
    暫定の極値は「確定済みの転換点以降の最高値/最安値」なので、確定の遅れ（数本〜十数本）を待たずに毎バー計算できる。"""
    n = len(df)
    h, l, c = df.h.to_numpy(float), df.l.to_numpy(float), df.c.to_numpy(float)
    pct = L.swing_threshold(df)
    lb, lk, lp = L.last_confirmed(L.pivots(df), n)
    cols = ["R_up", "G_top", "age_up", "R_dn", "G_bot", "age_dn", "kind"]
    out = {k: np.full(n, np.nan) for k in cols}
    a1 = -1; x1 = np.nan      # 主の暫定極値（確定底の後は最高値、確定天井の後は最安値）
    a2 = -1; x2 = np.nan      # 主の暫定極値の後の反対側の極値
    for t in range(n):
        k = lk[t]
        if k == 0:
            continue
        b = lb[t]
        if t == 0 or lb[t] != lb[t - 1] or lk[t] != lk[t - 1]:      # 新しい転換点が確定したバー: (b, t] で作り直す
            if k == -1:
                seg = h[b + 1:t + 1]
                a1 = b + 1 + (len(seg) - 1 - int(np.argmax(seg[::-1]))) if len(seg) else t
                x1 = h[a1]
                seg2 = l[a1 + 1:t + 1]
                if len(seg2):
                    a2 = a1 + 1 + (len(seg2) - 1 - int(np.argmin(seg2[::-1]))); x2 = l[a2]
                else:
                    a2, x2 = -1, np.nan
            else:
                seg = l[b + 1:t + 1]
                a1 = b + 1 + (len(seg) - 1 - int(np.argmin(seg[::-1]))) if len(seg) else t
                x1 = l[a1]
                seg2 = h[a1 + 1:t + 1]
                if len(seg2):
                    a2 = a1 + 1 + (len(seg2) - 1 - int(np.argmax(seg2[::-1]))); x2 = h[a2]
                else:
                    a2, x2 = -1, np.nan
        elif k == -1:
            if h[t] >= x1:
                a1, x1, a2, x2 = t, h[t], -1, np.nan
            elif a2 < 0 or l[t] <= x2:
                a2, x2 = t, l[t]
        else:
            if l[t] <= x1:
                a1, x1, a2, x2 = t, l[t], -1, np.nan
            elif a2 < 0 or h[t] >= x2:
                a2, x2 = t, h[t]
        out["kind"][t] = k
        e2, ab = (x2, a2) if a2 >= 0 else (c[t], t)
        if k == -1:   # 確定底 (b) → 暫定高値 (a1) → その後の安値 (a2)
            out["R_up"][t] = (x1 / lp[t] - 1) / pct[b]
            out["G_top"][t] = (1 - c[t] / x1) / pct[a1]
            out["age_up"][t] = t - b
            out["R_dn"][t] = (1 - e2 / x1) / pct[a1]
            out["G_bot"][t] = (c[t] / e2 - 1) / pct[ab]
            out["age_dn"][t] = t - a1
        else:         # 確定天井 (b) → 暫定安値 (a1) → その後の高値 (a2)
            out["R_dn"][t] = (1 - x1 / lp[t]) / pct[b]
            out["G_bot"][t] = (c[t] / x1 - 1) / pct[a1]
            out["age_dn"][t] = t - b
            out["R_up"][t] = (e2 / x1 - 1) / pct[a1]
            out["G_top"][t] = (1 - c[t] / e2) / pct[ab]
            out["age_up"][t] = t - a1
    return pd.DataFrame(out, index=df.index)


def td_setup(df):
    """TD セットアップ数（終値 > 4本前の終値 が何本連続か = 売りセットアップ、< が買いセットアップ。9 で打ち止めにしない）"""
    c = df.c.to_numpy(float)
    n = len(c)
    ss, bs = np.zeros(n), np.zeros(n)
    for t in range(4, n):
        ss[t] = ss[t - 1] + 1 if c[t] > c[t - 4] else 0
        bs[t] = bs[t - 1] + 1 if c[t] < c[t - 4] else 0
    return pd.DataFrame({"td_ss": ss, "td_bs": bs}, index=df.index)


def exhaust_feats(df):
    """連続日数・勢い・値幅の特徴量（すべて後ろ向きの rolling / ewm）"""
    c, h, l = df.c, df.h, df.l
    lr = np.log(c).diff()
    vol = lr.ewm(span=60, min_periods=20).std()                     # 日次変動率（swing_threshold と同じ作り）
    up = (c > c.shift(1)).astype(float)
    dn = (c < c.shift(1)).astype(float)
    cu = up.groupby((up == 0).cumsum()).cumsum()                    # 連続上昇日数
    cd = dn.groupby((dn == 0).cumsum()).cumsum()                    # 連続下落日数
    tr = pd.concat([h - l, (h - c.shift(1)).abs(), (l - c.shift(1)).abs()], axis=1).max(axis=1) / c.shift(1)
    atr_ratio = tr.ewm(span=5, min_periods=5).mean() / tr.ewm(span=20, min_periods=20).mean()  # 値幅の広がり/縮み
    z5 = np.log(c / c.shift(5)) / (vol * np.sqrt(5))                # 5日騰落 / 変動率
    z10 = np.log(c / c.shift(10)) / (vol * np.sqrt(10))
    near_hi = np.log(h.rolling(20, min_periods=20).max() / c) / vol  # 20日高値からの下げ / 日次変動率
    fade_top = z5.rolling(20, min_periods=10).max() - z5            # 勢いが直近20本の最高からどれだけ落ちたか
    up10 = up.rolling(10).sum()
    dn10 = dn.rolling(10).sum()
    ac = lr.abs()
    shrink = ac.rolling(3).mean() / ac.rolling(15).mean()            # 直近3本の値動きの大きさ / 15本平均（<1 で縮み）
    return pd.DataFrame({"cu": cu, "cd": cd, "atr_ratio": atr_ratio, "z5": z5, "z10": z10, "near_hi": near_hi,
                         "fade_top": fade_top, "up10": up10, "dn10": dn10, "shrink": shrink}, index=df.index)


def features(df):
    F = pd.concat([swing_state(df), td_setup(df), exhaust_feats(df)], axis=1)
    for k, (a, b) in CLIP.items():
        F[k] = F[k].clip(a, b)
    return F


# ---------------------------------------------------------------- 学習（nasdaq3x train だけ）
def make_model(C):
    return make_pipeline(SplineTransformer(n_knots=4, degree=3, extrapolation="constant"), StandardScaler(),
                         LogisticRegression(C=C, max_iter=5000))


def to_score(p, p50):
    """確率 → 0〜100（単調な折れ線。25=注意 は p50 の半分、80=圏 は p50 と 1 の中間）"""
    return np.interp(np.nan_to_num(p, nan=0.0), [0.0, p50 / 2, p50, (1 + p50) / 2, 1.0], [0, 25, 50, 80, 100])


def signal_rate(s, mask):
    sig = L.crossings_up(s)
    return mask[sig].sum() / (mask.sum() / 252)


def calibrate(p, mask, target=TARGET_RATE):
    """50 到達（35 でリセット）が target 回/年 に最も近くなる p50（同率なら回数の少ない側）"""
    grid = np.unique(np.quantile(p[mask & ~np.isnan(p)], np.linspace(0.3, 0.999, 700)))
    best = None
    for q in grid[::-1]:
        r = signal_rate(to_score(p, q), mask)
        if best is None or abs(r - target) < abs(best[1] - target) - 1e-12:
            best = (float(q), float(r))
    return best


def train_data():
    """train 末尾で切ったデータ・その ZigZag・目的変数（test 期間の値動きは使わない）"""
    df = L.load("nasdaq3x")
    d = df.loc[:TRAIN[1]]
    piv = L.pivots(d)
    return d, piv, L.targets(piv, len(d)), L.period_mask(d, TRAIN)


_FIT = {}


def fitted():
    if _FIT:
        return _FIT
    d, piv, tg, m = train_data()
    F = features(d)
    for cand, spec in SPECS.items():
        _FIT[cand] = {}
        for side in ("top", "bot"):
            cols, C = spec[side]["cols"], spec[side]["C"]
            y = tg[f"{side}_{HORIZON}"]
            X = F[cols].to_numpy(float)
            ok = m & ~np.isnan(y) & ~np.isnan(X).any(axis=1)
            mdl = make_model(C).fit(X[ok], y[ok].astype(int))
            p = predict(mdl, X)
            p50, rate = calibrate(p, m)
            _FIT[cand][side] = {"model": mdl, "cols": cols, "p50": p50, "train_rate": rate, "n_train": int(ok.sum()),
                                "n_pos": int(y[ok].sum())}
    return _FIT


def predict(mdl, X):
    p = np.full(len(X), np.nan)
    ok = ~np.isnan(X).any(axis=1)
    if ok.any():
        p[ok] = mdl.predict_proba(X[ok])[:, 1]
    return p


def _score(df, cand):
    fit = fitted()[cand]
    F = features(df)
    out = {}
    for side in ("top", "bot"):
        f = fit[side]
        out[side] = to_score(predict(f["model"], F[f["cols"]].to_numpy(float)), f["p50"])  # 準備期間（NaN）は 0
    return pd.DataFrame(out, index=df.index)


def score(df):
    """候補1: 脚ハザード＋勢い"""
    return _score(df, "score")


def score2(df):
    """候補2: 疲れ指標だけ（ZigZag 不使用）"""
    return _score(df, "score2")


# ---------------------------------------------------------------- 参考: RSI を同じ点灯回数に合わせたもの
_RSI = {}


def rsi_matched(df):
    """RSI(14) を基準と同じ傾き（RSI 1 ポイント = 2.5）で写像し、50 の位置だけ train で年 7 回点灯に合わせたもの"""
    if not _RSI:
        d, piv, tg, m = train_data()
        r = L.rsi(d.c).to_numpy()
        for side, sgn in (("top", 1), ("bot", -1)):
            best = None
            for x in np.arange(50.0, 90.01, 0.25) if sgn > 0 else np.arange(50.0, 10.0, -0.25):
                s = np.clip(50 + sgn * 2.5 * (r - x), 0, 100)
                rate = signal_rate(np.nan_to_num(s), m)
                if best is None or abs(rate - TARGET_RATE) < abs(best[1] - TARGET_RATE) - 1e-12:
                    best = (float(x), float(rate))
            _RSI[side] = best
    r = L.rsi(df.c)
    return pd.DataFrame({"top": (50 + 2.5 * (r - _RSI["top"][0])).clip(0, 100),
                         "bot": (50 - 2.5 * (r - _RSI["bot"][0])).clip(0, 100)}, index=df.index)


# ---------------------------------------------------------------- 追加の検証
def train_cv(cand, n_folds=4, embargo=20):
    """train 内の時系列ブロック CV（学習に使っていない区間の成績）。p50 も CV 予測から年 7 回に合わせ直す"""
    d, piv, tg, m = train_data()
    F = features(d)
    folds = np.array_split(np.flatnonzero(m), n_folds)
    sc = {}
    for side in ("top", "bot"):
        if cand == "rsi_matched":
            r = L.rsi(d.c).to_numpy() / 100
            p = r if side == "top" else 1 - r
        else:
            cols, C = SPECS[cand][side]["cols"], SPECS[cand][side]["C"]
            y = tg[f"{side}_{HORIZON}"]
            X = F[cols].to_numpy(float)
            p = np.full(len(d), np.nan)
            for te in folds:
                trn = m & ~np.isnan(y) & ~np.isnan(X).any(axis=1)
                trn[max(0, te[0] - embargo):te[-1] + embargo + 1] = False
                mdl = make_model(C).fit(X[trn], y[trn].astype(int))
                p[te] = predict(mdl, X[te])
        sc[side] = p
    out = {}
    for side in ("top", "bot"):
        p = sc[side]
        if cand == "rsi_matched":
            s = rsi_matched(d)[side].to_numpy()
        else:
            s = to_score(p, calibrate(p, m)[0])
        S = pd.DataFrame({"top": s if side == "top" else 0.0, "bot": s if side == "bot" else 0.0}, index=d.index)
        e = L.evaluate(S, d, piv, m)[side]
        y = tg[f"{side}_{HORIZON}"]
        ok = m & ~np.isnan(y) & ~np.isnan(p)
        out[side] = {"auc10_oof": float(roc_auc_score(y[ok], p[ok])), "recall_pre": e["recall_pre"],
                     "precision": e["precision"], "signals_per_year": e["signals_per_year"], "lead_med": e["lead_med"],
                     "remain_med": e["remain_med"]}
    return out


def shuffled(df, mask, rng):
    """評価期間の中だけ日次の値動き（前日終値比の o/h/l/c）の順番を入れ替えた系列＝自己相関のないランダムウォーク"""
    pc = df.c.shift(1).to_numpy()
    rr = df[["o", "h", "l", "c"]].to_numpy() / pc[:, None]
    seg = np.flatnonzero(mask)
    a, b = seg[0], seg[-1] + 1
    rr[a:b] = rr[a:b][rng.permutation(b - a)]
    o, h, l, c = (df[k].to_numpy().copy() for k in ("o", "h", "l", "c"))
    c[a:] = c[a - 1] * np.cumprod(rr[a:, 3])
    prev = np.r_[c[a - 1], c[a:-1]]
    o[a:], h[a:], l[a:] = prev * rr[a:, 0], prev * rr[a:, 1], prev * rr[a:, 2]
    return pd.DataFrame({"o": o, "h": h, "l": l, "c": c}, index=df.index)


def rw_null(fn, df, mask, n=100, seed=1, keys=("recall_pre", "precision", "auc10", "lead_med", "remain_med")):
    """ランダムウォーク帰無: 同じ指標を「順番を入れ替えた値動き」に当てたときの成績の分布。
    循環シフト帰無は時刻の対応だけを壊すので「上がった後に天井が来る」という幾何の効果は残る。こちらはそれも込みの帰無。
    返り値: side -> key -> (実測, 帰無の中央値, p値=帰無が実測以上の割合)"""
    rng = np.random.default_rng(seed)
    real = L.evaluate(fn(df), df, L.pivots(df), mask)
    null = {s: {k: [] for k in keys} for s in ("top", "bot")}
    for _ in range(n):
        sdf = shuffled(df, mask, rng)
        e = L.evaluate(fn(sdf), sdf, L.pivots(sdf), mask)
        for s in null:
            for k in keys:
                null[s][k].append(e[s][k])
    return {s: {k: (float(real[s][k]), float(np.nanmedian(null[s][k])),
                    float(np.mean(np.array(null[s][k], float) >= real[s][k]))) for k in keys} for s in null}


def fwd_returns(sc, df, mask, k=10):
    """点灯（50 到達）後 k 本の騰落（3倍系列の対数リターン %）。基準 = 期間内の全バーの平均"""
    c = df.c.to_numpy(float)
    fr = np.full(len(c), np.nan)
    fr[:-k] = np.log(c[k:] / c[:-k]) * 100
    base = fr[mask & ~np.isnan(fr)]
    out = {"all_mean": float(base.mean()), "all_up_frac": float((base > 0).mean())}
    for side in ("top", "bot"):
        sig = L.crossings_up(np.nan_to_num(sc[side].to_numpy(float)))
        sig = sig[mask[sig]]
        v = fr[sig]
        v = v[~np.isnan(v)]
        out[side] = {"n": int(len(v)), "mean": float(v.mean()) if len(v) else None,
                     "median": float(np.median(v)) if len(v) else None,
                     "up_frac": float((v > 0).mean()) if len(v) else None}
    return out


def clean(o):
    """JSON 用: numpy 型 → Python 型、NaN/inf → None"""
    if isinstance(o, dict):
        return {str(k): clean(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [clean(v) for v in o]
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (float, np.floating)):
        return None if not np.isfinite(o) else float(o)
    return o


DESCRIPTIONS = {
    "score": (
        "【共通】正解 ZigZag と同じ反転幅 θ（swing_threshold：日次変動率 EWMA(60)×√10×1.5、10〜60%）を物差しにする。"
        "各バーで L.last_confirmed から『確定済みの最新転換点』を取り、それ以降の最高値/最安値を暫定の極値として今の脚を測る"
        "（確定の遅れを待たずに毎バー計算できる。暫定の極値が更新されれば測り直し）。"
        "【天井側 top】直近の安値（確定済みの底、または確定天井の後の暫定安値）から今までの最高値までの上昇幅 R_up（θ の何倍か）と、"
        "その最高値からの終値の押し G_top（θ の何割か）の2変数を、それぞれ3次スプライン（4ノット）に展開したロジスティック回帰（C=1）で"
        "『10本以内に天井』の確率 p にする。"
        "【底側 bot】直近の高値（確定済みの天井、または確定底の後の暫定高値）からの下落幅 R_dn（θ 倍）、その最安値からの戻り G_bot（θ 割）、"
        "高値からの経過本数 age_dn、10日騰落率÷(日次変動率×√10) z10、ATR(5)/ATR(20) の5変数を同様に（C=0.1）『10本以内に底』の確率にする。"
        "【目盛り】p を [0, p50/2, p50, (1+p50)/2, 1] → [0, 25, 50, 80, 100] の折れ線で写像。p50 は nasdaq3x train で"
        "50 到達（35 でリセット）が年 7 回になる値（params 参照）。学習・p50 とも nasdaq3x train（1999-07〜2010-12）のみ、"
        "目的変数は train 末尾で切ったデータの ZigZag から作成。"),
    "score2": (
        "ZigZag を使わない『疲れ指標』だけの版。"
        "【天井側 top】5日騰落÷(日次変動率×√5) z5、20日高値からの下げ÷日次変動率 near_hi、"
        "勢いの衰え fade_top（z5 の直近20本の最高値−今の z5）の3変数（train CV で TD 売りセットアップ数・連続上昇日数・"
        "値動きの縮み等を足しても改善しなかったため外した）。"
        "【底側 bot】TD 買いセットアップ数、連続下落日数、10日騰落÷(日次変動率×√10) z10、near_hi、ATR(5)/ATR(20)、fade_top、"
        "直近10本の下落日数の7変数。"
        "それぞれ3次スプライン（4ノット）＋ロジスティック回帰（天井 C=1、底 C=0.1）で『10本以内に天井/底』の確率にし、"
        "score と同じ折れ線（p50 で 50）で 0〜100 に写像。学習・p50 とも nasdaq3x train のみ。"),
}


def main():
    t0 = time.time()
    pd.set_option("display.width", 250)
    pd.set_option("display.max_columns", 30)
    fit = fitted()
    data = {name: L.load(name) for name in L.SETS}
    pivs = {name: L.pivots(df) for name, df in data.items()}
    null_targets = [("nasdaq3x", "test"), ("sp3x_close", "oos2019")]
    out = {"key": KEY, "candidates": []}
    fns = {"score": score, "score2": score2}
    for cand, fn in fns.items():
        print(f"\n==================== {cand}: {SPECS[cand]['name']}")
        for side in ("top", "bot"):
            f = fit[cand][side]
            print(f"  {side}: p50={f['p50']:.4f}  train 点灯/年={f['train_rate']:.2f}  学習バー={f['n_train']} (正例 {f['n_pos']})")
        res = L.run_all(fn)
        print(L.summary_table(res).round(3).to_string())
        causal = {name: L.check_causal(fn, df) for name, df in data.items()}
        print("check_causal:", {k: float(v) for k, v in causal.items()})
        nulls, rwn, fwd = {}, {}, {}
        for name, pname in null_targets:
            df = data[name]
            mask = L.period_mask(df, L.SETS[name][1][pname])
            sc = fn(df)
            nt = L.null_test(sc, df, pivs[name], mask, n=200)
            nulls[f"{name}/{pname}"] = nt
            print(f"null_test {name}/{pname} (実測, 帰無中央値, p):")
            for s in ("top", "bot"):
                print("   ", s, {k: tuple(round(x, 3) for x in v) for k, v in nt[s].items()})
            rw = rw_null(fn, df, mask)
            rwn[f"{name}/{pname}"] = rw
            print(f"rw_null {name}/{pname} (実測, ランダムウォーク中央値, p):")
            for s in ("top", "bot"):
                print("   ", s, {k: tuple(round(x, 3) for x in v) for k, v in rw[s].items()})
        for (name, pname) in res:
            df = data[name]
            fwd[f"{name}/{pname}"] = fwd_returns(fn(df), df, L.period_mask(df, L.SETS[name][1][pname]))
        cv = train_cv(cand)
        print("train 4分割ブロックCV:", {s: {k: round(v, 3) for k, v in cv[s].items()} for s in cv})
        out["candidates"].append({
            "name": SPECS[cand]["name"], "function": cand, "description": DESCRIPTIONS[cand],
            "params": {side: {"features": fit[cand][side]["cols"], "C": SPECS[cand][side]["C"],
                              "spline": "n_knots=4, degree=3", "p50": fit[cand][side]["p50"],
                              "train_signals_per_year": fit[cand][side]["train_rate"], "horizon": HORIZON,
                              "clip": {k: CLIP[k] for k in fit[cand][side]["cols"] if k in CLIP}}
                       for side in ("top", "bot")} | {"target_rate": TARGET_RATE, "train": list(TRAIN)},
            "causal_max_diff": max(causal.values()),
            "causal_by_set": causal,
            "results": {f"{k[0]}/{k[1]}": v for k, v in res.items()},
            "null": nulls,
            "rw_null": rwn,
            "fwd10": fwd,
            "train_cv": cv,
        })
    # 参考: RSI（基準の写像そのまま）と、同じ点灯回数に合わせた RSI
    print("\n==================== 参考: RSI を train で年7回点灯に合わせたもの", _RSI if _RSI else "")
    ref = {}
    for rname, rfn in (("rsi_baseline", L.baseline_rsi), ("rsi_matched", rsi_matched)):
        res = L.run_all(rfn)
        print(rname, {k: v for k, v in _RSI.items()} if rname == "rsi_matched" else "")
        print(L.summary_table(res).round(3).to_string())
        r = {"results": {f"{k[0]}/{k[1]}": v for k, v in res.items()}, "rw_null": {}, "fwd10": {}}
        for name, pname in null_targets:
            df = data[name]
            mask = L.period_mask(df, L.SETS[name][1][pname])
            r["rw_null"][f"{name}/{pname}"] = rw_null(rfn, df, mask)
            print(f"rw_null {rname} {name}/{pname}:")
            for s in ("top", "bot"):
                print("   ", s, {k: tuple(round(x, 3) for x in v) for k, v in r["rw_null"][f'{name}/{pname}'][s].items()})
        for (name, pname) in res:
            df = data[name]
            r["fwd10"][f"{name}/{pname}"] = fwd_returns(rfn(df), df, L.period_mask(df, L.SETS[name][1][pname]))
        if rname == "rsi_matched":
            r["rsi_level_at_50"] = {k: v[0] for k, v in _RSI.items()}
            r["train_cv"] = train_cv("rsi_matched")
        ref[rname] = r
    out["reference"] = ref
    out["notes"] = ("results の train 期間は学習に使った区間（楽観的）。train_cv は train 内の未学習区間での成績。"
                    "rw_null は評価期間内の日次値動きの順番を入れ替えたランダムウォークで同じ指標を評価した帰無"
                    "（ZigZag の幾何だけで出る成績）。fwd10 は点灯後10本の3倍系列の対数騰落%。")
    path = HERE / "results" / f"{KEY}.json"
    path.parent.mkdir(exist_ok=True)
    with open(path, "w") as fh:
        json.dump(clean(out), fh, ensure_ascii=False, indent=1, default=float)
    print(f"\nsaved {path}  ({time.time() - t0:.0f}s)")


if __name__ == "__main__":
    main()
