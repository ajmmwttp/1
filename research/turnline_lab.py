"""TurnLine 実データ検証ハーネス

- データ: arch 同梱の NASDAQ 総合 / S&P500 日足 OHLC（1999-2018）、skfolio 同梱の S&P500 終値（1990-2022）。
  TQQQ 本体はこの環境のネットワーク制限で取得できないため、指数の日次値動きを 3 倍した近似系列で代用する。
- 正解: 高値/安値ベースの ZigZag で求めた転換点。反転幅は変動率に応じて可変（通常の TQQQ 相当でおよそ 15%）。
  確定バー（反転幅に達したバー）も持つ。
- 評価: 「そろそろ」(50) の事前点灯率・何本前か・空振り率・AUC など。インジケーターは
  fn(df) -> DataFrame[top, bot]（0〜100。top=天井が近い, bot=底が近い。各バーの値はそのバーの終値までの情報だけで計算）。
"""
import numpy as np
import pandas as pd
from sklearn.metrics import average_precision_score, roc_auc_score

EXPENSE = 0.0095   # 年率コスト（TQQQ の経費率相当）
ZZ_MULT, ZZ_FLOOR, ZZ_CAP = 1.5, 0.10, 0.60  # 正解 ZigZag の反転幅 = 1.5×(10日分の変動率)。通常の TQQQ 相当でおよそ 15%
TH_CAUTION, TH_SOON, TH_ZONE = 25, 50, 80
RESET = 35         # 「そろそろ」が再点灯できるようになる下限（ヒステリシス）
K_BARS = 10        # 「そろそろ」点灯から何本以内に転換すれば当たりとするか

# name: (元データ, {評価期間名: (開始, 終了)})。計算は全期間で行い、評価だけ期間で切る
SETS = {
    "nasdaq3x": ("nasdaq", {"train": ("1999-07-01", "2010-12-31"), "test": ("2011-01-01", "2018-12-31")}),
    "sp3x": ("sp500", {"check": ("1999-07-01", "2018-12-31")}),
    "sp3x_close": ("sp500_close", {"pre1999": ("1991-01-01", "1998-12-31"), "oos2019": ("2019-01-01", "2022-12-28")}),
}


# ---------------------------------------------------------------- データ
def leverage(base, k=3.0, expense=EXPENSE):
    """日次 k 倍レバレッジ ETF の近似 OHLC（前日終値基準で日中の値動きも k 倍）"""
    prev = base.c.shift(1)
    r = (base.c / prev - 1).fillna(0).to_numpy()
    lc = 100 * np.cumprod(np.maximum(1 + k * r - expense / 252, 1e-6))
    lprev = np.r_[100.0, lc[:-1]]
    rel = lambda s: np.maximum(1 + k * (s / prev - 1).fillna(0).to_numpy(), 1e-6)
    out = pd.DataFrame({"o": lprev * rel(base.o), "h": lprev * rel(base.h), "l": lprev * rel(base.l), "c": lc},
                       index=base.index)
    out["h"] = out[["o", "h", "c"]].max(axis=1)
    out["l"] = out[["o", "l", "c"]].min(axis=1)
    return out


def load_base(name):
    """レバレッジをかける前の指数 OHLC（列 o,h,l,c）。sp3x_close は終値のみ（o=h=l=c）"""
    src = SETS[name][0]
    if src == "sp500_close":
        from skfolio.datasets import load_sp500_index
        c = load_sp500_index()["SP500"].astype(float)
        return pd.DataFrame({"o": c, "h": c, "l": c, "c": c})
    from arch.data import nasdaq, sp500
    base = (nasdaq if src == "nasdaq" else sp500).load()[["Open", "High", "Low", "Close"]].astype(float)
    base.columns = ["o", "h", "l", "c"]
    return base


def load(name):
    """3倍レバレッジ近似の OHLC（列 o,h,l,c / DatetimeIndex）。sp3x_close は終値のみ（o=h=l=c）"""
    return leverage(load_base(name))


def period_mask(df, period):
    a, b = period
    return np.asarray((df.index >= a) & (df.index <= b))


# ---------------------------------------------------------------- 正解（ZigZag）
def swing_threshold(df, mult=ZZ_MULT, floor=ZZ_FLOOR, cap=ZZ_CAP):
    """各バーの反転幅（割合）= mult × 日次変動率（EWMA, span 60）× √10。荒れた相場ほど大きな値動きだけを山/谷とみなす"""
    vol = np.log(df.c).diff().ewm(span=60, min_periods=20).std().fillna(0.03)  # 最初の 20 本は既定値（未来は使わない）
    return np.clip(mult * vol.to_numpy() * np.sqrt(10), floor, cap)


def zigzag(h, l, pct):
    """高値/安値の ZigZag。確定した転換点だけを返す。pct は一定値か、バーごとの配列（極値のバーの値を使う）。
    confirm = 反転幅に達してその転換点が確定したバー（リアルタイムで「確定」と言える最速のバー）"""
    h, l = np.asarray(h, float), np.asarray(l, float)
    pct = np.broadcast_to(np.asarray(pct, float), h.shape)
    piv, trend, hi, lo = [], 0, 0, 0
    for i in range(1, len(h)):
        hi, lo = (i if hi < 0 else hi), (i if lo < 0 else lo)  # 転換点と同じバーは次の脚に含めない
        if trend >= 0 and h[i] >= h[hi]:
            hi = i
        if trend <= 0 and l[i] <= l[lo]:
            lo = i
        if trend == 0:
            if lo < hi and h[hi] >= l[lo] * (1 + pct[lo]):
                piv.append((lo, "L", l[lo], i))
                trend = 1
            elif hi < lo and l[lo] <= h[hi] * (1 - pct[hi]):
                piv.append((hi, "H", h[hi], i))
                trend = -1
        elif trend == 1 and l[i] <= h[hi] * (1 - pct[hi]):
            piv.append((hi, "H", h[hi], i))
            trend, lo = -1, (i if hi < i else -1)
        elif trend == -1 and h[i] >= l[lo] * (1 + pct[lo]):
            piv.append((lo, "L", l[lo], i))
            trend, hi = 1, (i if lo < i else -1)
    return pd.DataFrame(piv, columns=["bar", "kind", "price", "confirm"])


def pivots(df, pct=None):
    """正解の転換点。pct 省略時は変動率に応じた反転幅（swing_threshold）"""
    return zigzag(df.h, df.l, swing_threshold(df) if pct is None else pct)


def last_confirmed(piv, n):
    """各バー t で「t までに確定済み」の最新の転換点（bar, kind=+1 天井/-1 底/0 なし, price）。特徴量づくり用"""
    bar, kind, price = np.full(n, -1), np.zeros(n, int), np.full(n, np.nan)
    rows = list(piv.itertuples())
    for j, r in enumerate(rows):
        end = rows[j + 1].confirm if j + 1 < len(rows) else n
        bar[r.confirm:end], kind[r.confirm:end], price[r.confirm:end] = r.bar, 1 if r.kind == "H" else -1, r.price
    return bar, kind, price


def targets(piv, n, ks=(5, K_BARS)):
    """評価用の正解（未来の情報）。next_kind=+1 次の転換点は天井 / -1 底 / 0 未確定。
    bars_to=次の転換点までの本数。top_k/bot_k=k 本以内に天井/底（未確定区間は NaN）"""
    nk, bt = np.zeros(n, int), np.full(n, np.nan)
    prev = -1
    for b, k in zip(piv.bar, piv.kind):
        nk[prev + 1:b + 1] = 1 if k == "H" else -1
        bt[prev + 1:b + 1] = b - np.arange(prev + 1, b + 1)
        prev = b
    out = {"next_kind": nk, "bars_to": bt}
    for k in ks:
        known = nk != 0
        out[f"top_{k}"] = np.where(known, (nk == 1) & (bt <= k), np.nan)
        out[f"bot_{k}"] = np.where(known, (nk == -1) & (bt <= k), np.nan)
    return out


# ---------------------------------------------------------------- 評価
def crossings_up(x, th=TH_SOON, reset=RESET):
    """x が th 以上になったバー（一度点灯したら reset 未満に下がるまで再点灯しない）"""
    sig, armed = [], True
    for i, v in enumerate(x):
        if armed and v >= th:
            sig.append(i)
            armed = False
        elif not armed and v < reset:
            armed = True
    return np.array(sig, int)


def evaluate(score, df, piv, mask, th=TH_SOON, reset=RESET, K=K_BARS):
    """期間 mask の中で、top（天井）/bot（底）それぞれの成績を返す。
    recall_pre  : 転換点のうち、その脚の中（前の転換点の翌バー〜転換点）で th に届いた割合（＝事前に点灯）
    recall_late : 事前には届かず、転換点の翌バー〜確定バーの間に届いた割合（＝遅れて点灯）
    lead_*      : 事前点灯が転換点の何本前だったか（最初に届いたバー基準）
    remain_med  : 事前点灯の終値から実際の高値/安値までの残りの値動き（%）。大きいほど早すぎ
    precision   : 点灯（ヒステリシス付き）のうち、K 本以内に同じ側の転換点が来た割合
    precision_lenient : 上に加え、3 本以内の「直後」点灯も当たりとした割合
    auc5/auc10, ap10/base10 : 各バーのスコアで「k 本以内に転換点」を当てる力（0.5=でたらめ）
    lit_frac    : th 以上で点灯しているバーの割合"""
    n = len(df)
    tg = targets(piv, n)
    pb, pk, pc = piv.bar.to_numpy(), piv.kind.to_numpy(), piv.confirm.to_numpy()
    years = mask.sum() / 252
    res = {}
    for side, kind, sgn in (("top", "H", 1), ("bot", "L", -1)):
        x = np.nan_to_num(score[side].to_numpy(float), nan=0.0)
        hits, leads, remain, late = [], [], [], 0
        for j in range(1, len(piv)):
            if pk[j] != kind or not mask[pb[j]]:
                continue
            q, p, cf = pb[j - 1], pb[j], pc[j]
            w = np.flatnonzero(x[q + 1:p + 1] >= th)
            if len(w):
                first = q + 1 + w[0]
                ref = df.h.iat[p] if kind == "H" else df.l.iat[p]
                hits.append(1)
                leads.append(p - first)
                remain.append(abs(ref / df.c.iat[first] - 1) * 100)
            else:
                hits.append(0)
                late += int((x[p + 1:cf + 1] >= th).any())
        sig = crossings_up(x, th, reset)
        sig = sig[mask[sig]]
        nk, bt = tg["next_kind"][sig], tg["bars_to"][sig]
        known = nk != 0
        ok = (nk == sgn) & (bt <= K)
        j_prev = np.searchsorted(pb, sig) - 1
        just = np.array([jp >= 0 and pk[jp] == kind and 0 < s - pb[jp] <= 3 for jp, s in zip(j_prev, sig)], bool)
        y5, y10 = tg[f"{side}_5"], tg[f"{side}_{K}"]
        m = mask & ~np.isnan(y10)
        npv = len(hits)
        res[side] = {
            "n_pivots": npv,
            "pivots_per_year": npv / years,
            "recall_pre": np.mean(hits) if npv else np.nan,
            "recall_late": late / npv if npv else np.nan,
            "lead_med": float(np.median(leads)) if leads else np.nan,
            "lead_q1": float(np.percentile(leads, 25)) if leads else np.nan,
            "lead_q3": float(np.percentile(leads, 75)) if leads else np.nan,
            "remain_med": float(np.median(remain)) if remain else np.nan,
            "n_signals": int(known.sum()),
            "signals_per_year": known.sum() / years,
            "signals_per_pivot": known.sum() / npv if npv else np.nan,
            "precision": ok[known].mean() if known.any() else np.nan,
            "precision_lenient": (ok | just)[known].mean() if known.any() else np.nan,
            "auc5": roc_auc_score(y5[m], x[m]) if 0 < np.nanmean(y5[m]) < 1 else np.nan,
            "auc10": roc_auc_score(y10[m], x[m]) if 0 < y10[m].mean() < 1 else np.nan,
            "ap10": average_precision_score(y10[m], x[m]) if 0 < y10[m].mean() < 1 else np.nan,
            "base10": y10[m].mean(),
            "lit_frac": (x[mask] >= th).mean(),
        }
    return res


def null_test(score, df, piv, mask, n=200, seed=0, keys=("recall_pre", "precision", "auc10")):
    """評価期間の中でスコアを循環シフト（自己相関は保ったまま時刻の対応だけ壊す）した帰無分布と比べる。
    返り値: side -> key -> (実測値, 帰無の中央値, p値=帰無が実測以上になった割合)"""
    rng = np.random.default_rng(seed)
    real = evaluate(score, df, piv, mask)
    seg = np.flatnonzero(mask)
    a, b = seg[0], seg[-1] + 1
    null = {s: {k: [] for k in keys} for s in ("top", "bot")}
    for _ in range(n):
        shift = int(rng.integers(60, b - a - 60))
        sh = score[["top", "bot"]].copy()
        for col in ("top", "bot"):
            v = sh[col].to_numpy(float).copy()
            v[a:b] = np.roll(v[a:b], shift)
            sh[col] = v
        e = evaluate(sh, df, piv, mask)
        for s in null:
            for k in keys:
                null[s][k].append(e[s][k])
    return {s: {k: (real[s][k], float(np.nanmedian(null[s][k])),
                    float(np.mean(np.array(null[s][k]) >= real[s][k]))) for k in keys} for s in null}


def check_causal(fn, df, n_cuts=8, start=0.5, seed=0):
    """未来の値を使っていないかの検査: 途中までのデータで計算した最終バーの値が、全期間で計算した同じバーの値と一致するか。
    返り値: 不一致の最大値（0 なら OK。NaN の有無が食い違う場合は inf）"""
    full = fn(df)[["top", "bot"]].to_numpy(float)
    rng = np.random.default_rng(seed)
    worst = 0.0
    for c in sorted(rng.integers(int(len(df) * start), len(df) - 1, n_cuts)):
        part = fn(df.iloc[:c + 1])[["top", "bot"]].to_numpy(float)[-1]
        a, b = part, full[c]
        if (np.isnan(a) != np.isnan(b)).any():
            return float("inf")
        d = np.abs(a - b)[~np.isnan(a)]
        worst = max(worst, float(d.max()) if len(d) else 0.0)
    return worst


def leg_stats(df, piv, mask):
    """転換点の基本統計: 年あたり個数、脚の長さ（本）、値幅（%）、確定までの遅れ（本）"""
    out = {}
    pb, pk, pp, pc = piv.bar.to_numpy(), piv.kind.to_numpy(), piv.price.to_numpy(), piv.confirm.to_numpy()
    years = mask.sum() / 252
    for kind in ("H", "L"):
        j = [i for i in range(1, len(piv)) if pk[i] == kind and mask[pb[i]]]
        dur = [pb[i] - pb[i - 1] for i in j]
        amp = [abs(pp[i] / pp[i - 1] - 1) * 100 for i in j]
        lag = [pc[i] - pb[i] for i in j]
        out[kind] = {"per_year": len(j) / years, "dur_med": float(np.median(dur)), "dur_q1": float(np.percentile(dur, 25)),
                     "dur_q3": float(np.percentile(dur, 75)), "amp_med": float(np.median(amp)),
                     "confirm_lag_med": float(np.median(lag)), "confirm_lag_q1": float(np.percentile(lag, 25)),
                     "confirm_lag_q3": float(np.percentile(lag, 75))}
    return out


def run_all(fn, name_filter=None):
    """全データセット・全評価期間で fn を評価する。返り値: {(set, period): evaluate(...)}"""
    out = {}
    for name, (_, periods) in SETS.items():
        if name_filter and name not in name_filter:
            continue
        df = load(name)
        piv = pivots(df)
        sc = fn(df)
        for pname, per in periods.items():
            out[(name, pname)] = evaluate(sc, df, piv, period_mask(df, per))
    return out


def summary_table(results):
    """run_all の結果を見やすい表に"""
    rows = []
    for (name, pname), r in results.items():
        for side in ("top", "bot"):
            d = r[side]
            rows.append({"set": name, "period": pname, "side": side, "pivots": d["n_pivots"],
                         "事前点灯率": d["recall_pre"], "遅れ点灯率": d["recall_late"], "何本前(中央)": d["lead_med"],
                         "残り値幅%": d["remain_med"], "点灯/年": d["signals_per_year"], "的中率": d["precision"],
                         "的中率(直後込)": d["precision_lenient"], "AUC10": d["auc10"], "AP10/基準": d["ap10"] / d["base10"]})
    return pd.DataFrame(rows)


# ---------------------------------------------------------------- 比較用の基準
def rsi(c, n=14):
    d = c.diff()
    up = d.clip(lower=0).ewm(alpha=1 / n, adjust=False).mean()
    dn = (-d.clip(upper=0)).ewm(alpha=1 / n, adjust=False).mean()
    return 100 - 100 / (1 + up / dn)


def baseline_rsi(df):
    """RSI(14) をそのまま写像: RSI 70 → top 50, RSI 90 → top 100（底は対称）"""
    r = rsi(df.c)
    return pd.DataFrame({"top": ((r - 50) * 2.5).clip(0, 100), "bot": ((50 - r) * 2.5).clip(0, 100)}, index=df.index)


def ideal(df, piv=None):
    """サンプル画像と同じ『理想形』（未来の転換点を使う＝実際には作れない上限）"""
    piv = pivots(df) if piv is None else piv
    top, bot = np.zeros(len(df)), np.zeros(len(df))
    pb, pk = piv.bar.to_numpy(), piv.kind.to_numpy()
    for j in range(1, len(piv)):
        q, p = pb[j - 1], pb[j]
        t = (np.arange(q + 1, p + 1) - q) / (p - q)
        x = np.clip((t - 0.3) / 0.7, 0, 1)
        (top if pk[j] == "H" else bot)[q + 1:p + 1] = 100 * x * x * (3 - 2 * x)
    return pd.DataFrame({"top": top, "bot": bot}, index=df.index)
