"""TurnLine 候補（担当: オシレーター・サイクル系, key: classic）

score  = TL-Blend    : 古典オシレーター 7〜8 本をロジスティック回帰で合成（nasdaq3x の train 期間だけで学習）
score2 = TL-Classic3 : RSI・ストキャスティクス・移動平均乖離 z の 3 本を等重みで合成（重みの学習なし）

どちらも価格（o,h,l,c）だけを使い、ZigZag の転換点情報（pivots / last_confirmed）は使わない。
各バーの値はそのバーの終値までの情報だけで決まる（再帰フィルター・過去窓のみ）。
定数（標準化の平均・標準偏差、回帰係数、0〜100 への目盛り）はすべて nasdaq3x/train（1999-07〜2010-12）だけで決め、
下の CONST に固定値として書き込んである。`python3 cand_classic.py --fit` で同じ手順の再計算結果を表示する。

目盛り（0〜100）: score = 100 / (1 + exp(-(raw - theta) / s))
  - 25（注意）は train の raw の 80% 点
  - 50（そろそろ）は train で「点灯」（50 到達、35 未満で再点灯可）が年 7.5 回（転換点 年約 5 回の 1.5 倍）になる位置
  - 80（圏）は theta + ln(4) s

実行: python3 cand_classic.py  → (a) 各候補の run_all 表 (b) check_causal (c) null_test(n=200) (d) results/classic.json
"""
import argparse
import json
import os
import sys

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import turnline_lab as L  # noqa: E402

KEY = "classic"
TARGET_SPY = 7.5     # train での点灯/年の目標（転換点 年約 5 回の 1.5 倍）
Q_CAUTION = 0.80     # 25（注意）を置く train 分位点


# ---------------------------------------------------------------- 特徴量（すべて因果的）
def dvol(df, span=60):
    """日次の対数リターンの変動率（EWMA）"""
    return np.log(df.c).diff().ewm(span=span, min_periods=20).std()


def f_rsi(df, n):
    """RSI(n) - 50（Wilder 平滑）"""
    return L.rsi(df.c, n) - 50


def f_stoch(df, n):
    """ストキャスティクス %K(n) - 50（高値・安値の n 本窓。終値だけのデータでは終値の窓になる）"""
    hh = df.h.rolling(n, min_periods=n).max()
    ll = df.l.rolling(n, min_periods=n).min()
    return 100 * (df.c - ll) / (hh - ll).replace(0, np.nan) - 50


def f_z(df, n):
    """移動平均乖離の z: (log 終値 - EMA_n(log 終値)) / (日次変動率 × √n)"""
    lc = np.log(df.c)
    return (lc - lc.ewm(span=n, adjust=False).mean()) / (dvol(df) * np.sqrt(n))


def f_rise(df, n):
    """過去 n 本の安値からの上昇幅（対数）を 10 日分の変動率で割ったもの"""
    return np.log(df.c / df.l.rolling(n, min_periods=1).min()) / (dvol(df) * np.sqrt(10))


def f_trend200(df):
    """200 日移動平均からの乖離（日次変動率の何倍か）"""
    lc = np.log(df.c)
    return (lc - lc.rolling(200, min_periods=100).mean()) / dvol(df)


def f_macdh(df):
    """MACD(12,26,9) ヒストグラム（対数価格・変動率で正規化）"""
    lc = np.log(df.c)
    m = (lc.ewm(span=12, adjust=False).mean() - lc.ewm(span=26, adjust=False).mean()) / dvol(df)
    return m - m.ewm(span=9, adjust=False).mean()


FEATURES = {
    "rsi5": lambda d: f_rsi(d, 5), "rsi7": lambda d: f_rsi(d, 7), "rsi14": lambda d: f_rsi(d, 14),
    "stoch10": lambda d: f_stoch(d, 10), "stoch14": lambda d: f_stoch(d, 14),
    "stoch21": lambda d: f_stoch(d, 21), "stoch60": lambda d: f_stoch(d, 60),
    "z10": lambda d: f_z(d, 10), "z20": lambda d: f_z(d, 20), "z50": lambda d: f_z(d, 50), "z100": lambda d: f_z(d, 100),
    "rise60": lambda d: f_rise(d, 60), "trend200": f_trend200, "macdh": f_macdh,
}

BLEND_COLS = {"top": ["stoch10", "rsi5", "z10", "z50", "rise60", "stoch60", "trend200"],
              "bot": ["z10", "z20", "rsi5", "stoch21", "rsi14", "trend200", "z100", "macdh"]}
CLASSIC_COLS = {"top": ["rsi5", "stoch10", "z10"], "bot": ["rsi7", "stoch14", "z20"]}


def features(df, cols):
    """必要な特徴量だけ計算（先頭の計算できない区間は 0 = 中立）"""
    return pd.DataFrame({c: FEATURES[c](df) for c in cols}, index=df.index).fillna(0.0)


def logistic(raw, theta, s):
    z = (np.asarray(raw, float) - theta) / s
    return 100 / (1 + np.exp(-np.clip(z, -60, 60)))


# ---------------------------------------------------------------- 固定定数（--fit で再計算できる。nasdaq3x/train のみ）
# `python3 cand_classic.py --fit` の出力をそのまま貼ったもの（nasdaq3x/train だけから計算）
CONST = {'blend': {'top': {'cols': ['stoch10', 'rsi5', 'z10', 'z50', 'rise60', 'stoch60', 'trend200'],
                   'mean': [3.8592116331638557,
                            2.1516978433682046,
                            0.008522591434242366,
                            0.0358683685950936,
                            2.2585464832635656,
                            2.1478022664279006,
                            0.5578668122664447],
                   'scale': [33.08614582280322,
                             20.209294757095993,
                             0.43274472750300963,
                             0.499817673698727,
                             1.5919867623362982,
                             33.76507114477971,
                             8.832796873208304],
                   'coef': [0.6341650055498284,
                            0.19307427988485765,
                            0.1621294525395147,
                            -0.3441667379392605,
                            0.4393522336298494,
                            -0.5324619713383589,
                            0.4783226916011894],
                   'intercept': -1.7610116307240917,
                   'theta': -0.5835692721049084,
                   's': 0.2857804907103797,
                   'train_spy': 7.486010362694301},
           'bot': {'cols': ['z10', 'z20', 'rsi5', 'stoch21', 'rsi14', 'trend200', 'z100', 'macdh'],
                   'mean': [0.008522591434242366,
                            0.018924204977421075,
                            2.1516978433682046,
                            3.6075885078646563,
                            1.2399151453148254,
                            0.5578668122664447,
                            0.03978917276609446,
                            0.0016603718097435466],
                   'scale': [0.43274472750300963,
                             0.4654796442172596,
                             20.209294757095993,
                             33.092086794564636,
                             12.196376338839308,
                             8.832796873208304,
                             0.5218990045824623,
                             0.31708832064954967],
                   'coef': [-0.39710225472636207,
                            -0.6477151005435328,
                            0.023045969521584792,
                            -0.3948587635123187,
                            -0.45567710227689723,
                            0.519434759816611,
                            -0.14278019659420027,
                            -0.3960294733718365],
                   'intercept': -2.4098306025418994,
                   'theta': 0.3715733649371775,
                   's': 0.7822122433474248,
                   'train_spy': 7.486010362694301}},
 'classic': {'top': {'cols': ['rsi5', 'stoch10', 'z10'],
                     'mean': [2.1516978433682046, 3.8592116331638557, 0.008522591434242366],
                     'sd': [20.209294757095993, 33.08614582280322, 0.43274472750300963],
                     'theta': 1.3341101827624768,
                     's': 0.31171618479730795,
                     'train_spy': 7.486010362694301},
             'bot': {'cols': ['rsi7', 'stoch14', 'z20'],
                     'mean': [1.8389249849317046, 3.728382477514776, 0.018924204977421075],
                     'sd': [17.088589362428145, 33.110473050885645, 0.4654796442172596],
                     'theta': 1.49737256581331,
                     's': 0.4587532601305911,
                     'train_spy': 7.486010362694301}}}


def blend_raw(df, side, c):
    X = features(df, BLEND_COLS[side]).to_numpy(float)
    return c["intercept"] + ((X - np.array(c["mean"])) / np.array(c["scale"])) @ np.array(c["coef"])


def classic_raw(df, side, c):
    X = features(df, CLASSIC_COLS[side]).to_numpy(float)
    zz = (X - np.array(c["mean"])) / np.array(c["sd"])
    return (1 if side == "top" else -1) * zz.mean(axis=1)


def score(df):
    """TL-Blend: top/bot = 古典オシレーターのロジスティック合成を 0〜100 に写像"""
    out = {}
    for side in ("top", "bot"):
        c = CONST["blend"][side]
        out[side] = logistic(blend_raw(df, side, c), c["theta"], c["s"])
    return pd.DataFrame(out, index=df.index)


def score2(df):
    """TL-Classic3: top = mean(z(RSI5), z(Stoch10), z(MA乖離z10)), bot = -mean(z(RSI7), z(Stoch14), z(MA乖離z20))"""
    out = {}
    for side in ("top", "bot"):
        c = CONST["classic"][side]
        out[side] = logistic(classic_raw(df, side, c), c["theta"], c["s"])
    return pd.DataFrame(out, index=df.index)


# ---------------------------------------------------------------- 定数の学習（nasdaq3x/train だけ）
def _calibrate(raw, train, years, target=TARGET_SPY, q25=Q_CAUTION):
    """25 を train の q25 分位に置き、train の点灯/年が target になる theta を二分探索"""
    x = np.asarray(raw, float)
    xt = x[train & np.isfinite(x)]
    qc = float(np.quantile(xt, q25))
    lo, hi, best = q25 + 0.005, 0.9995, None
    for _ in range(30):
        u = (lo + hi) / 2
        th = float(np.quantile(xt, u))
        s = (th - qc) / np.log(3)
        sig = L.crossings_up(logistic(x, th, s))
        spy = train[sig].sum() / years
        if best is None or abs(spy - target) < abs(best[2] - target):
            best = (th, s, spy)
        lo, hi = (u, hi) if spy > target else (lo, u)
    return best


def fit_constants():
    from sklearn.linear_model import LogisticRegression
    from sklearn.preprocessing import StandardScaler
    df = L.load("nasdaq3x")
    piv = L.pivots(df)
    train = L.period_mask(df, L.SETS["nasdaq3x"][1]["train"])
    years = train.sum() / 252
    tg = L.targets(piv, len(df))   # 正解ラベル（未来の情報）は学習の目的変数にだけ使う
    out = {"blend": {}, "classic": {}}
    for side in ("top", "bot"):
        y = tg[f"{side}_10"]
        rows = np.flatnonzero(train & ~np.isnan(y))
        X = features(df, BLEND_COLS[side]).to_numpy(float)
        sc = StandardScaler().fit(X[rows])
        lr = LogisticRegression(C=0.05, max_iter=3000).fit(sc.transform(X[rows]), y[rows])
        c = {"cols": BLEND_COLS[side], "mean": sc.mean_.tolist(), "scale": sc.scale_.tolist(),
             "coef": lr.coef_[0].tolist(), "intercept": float(lr.intercept_[0])}
        th, s, spy = _calibrate(blend_raw(df, side, c), train, years)
        c.update(theta=th, s=s, train_spy=spy)
        out["blend"][side] = c
        Xc = features(df, CLASSIC_COLS[side]).to_numpy(float)
        cc = {"cols": CLASSIC_COLS[side], "mean": Xc[train].mean(0).tolist(), "sd": Xc[train].std(0).tolist()}
        th, s, spy = _calibrate(classic_raw(df, side, cc), train, years)
        cc.update(theta=th, s=s, train_spy=spy)
        out["classic"][side] = cc
    return out


# ---------------------------------------------------------------- 実行
def _summ(res):
    t = L.summary_table(res)
    with pd.option_context("display.width", 250, "display.max_columns", 30):
        print(t.round(3).to_string(index=False))


def _jsonable(o):
    if isinstance(o, dict):
        return {str(k): _jsonable(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [_jsonable(v) for v in o]
    if isinstance(o, (np.floating, float)):
        return None if not np.isfinite(o) else float(o)
    if isinstance(o, (np.integer,)):
        return int(o)
    return o


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--fit", action="store_true", help="nasdaq3x/train で定数を再計算して表示するだけ")
    ap.add_argument("--n-null", type=int, default=200)
    args = ap.parse_args()
    if args.fit:
        print(json.dumps(fit_constants(), indent=1))
        return

    cands = [
        ("TL-Blend", "score", score,
         "古典オシレーターのロジスティック合成。天井: Stoch10, RSI5, MA乖離z10, MA乖離z50, 60日安値からの上昇幅(変動率単位), "
         "Stoch60, 200日線乖離 / 底: MA乖離z10, z20, RSI5, Stoch21, RSI14, 200日線乖離, MA乖離z100, MACDヒストグラム。"
         "係数は nasdaq3x/train で『10本以内に天井(底)』を目的変数に L2 ロジスティック回帰（C=0.05, 標準化）で学習。"
         "線形予測値をロジスティックで 0〜100 に写像（25=train の 80% 点, 50=train で点灯 年7.5回）。平滑化なし。"),
        ("TL-Classic3", "score2", score2,
         "RSI・ストキャスティクス・移動平均乖離 z の等重み合成（重みの学習なし）。天井: RSI5, Stoch10, MA乖離z10 / "
         "底: RSI7, Stoch14, MA乖離z20 を train の平均・標準偏差で標準化して平均（底は符号反転）。"
         "目盛りは TL-Blend と同じ方式（25=train の 80% 点, 50=train で点灯 年7.5回）。"),
    ]
    data = {name: L.load(name) for name in L.SETS}
    pivs = {name: L.pivots(df) for name, df in data.items()}
    out = {"key": KEY, "candidates": [], "references": {}}

    print("=== 参考: L.baseline_rsi（RSI14 の写像）")
    res = L.run_all(L.baseline_rsi)
    _summ(res)
    out["references"]["baseline_rsi"] = {f"{k[0]}/{k[1]}": v for k, v in res.items()}

    # 同じ点灯頻度での比較用: RSI14 を候補と同じ方式（train で年 7.5 回）で 0〜100 に写像したもの
    d0 = data["nasdaq3x"]
    tr0 = L.period_mask(d0, L.SETS["nasdaq3x"][1]["train"])
    r14 = (L.rsi(d0.c, 14) - 50).to_numpy()
    cal = {side: _calibrate(sg * r14, tr0, tr0.sum() / 252)[:2] for side, sg in (("top", 1), ("bot", -1))}

    def rsi_rate_matched(df):
        r = (L.rsi(df.c, 14) - 50).to_numpy()
        return pd.DataFrame({side: np.nan_to_num(logistic(sg * r, *cal[side]))
                             for side, sg in (("top", 1), ("bot", -1))}, index=df.index)

    print("\n=== 参考: RSI14（候補と同じ目盛り方式で train の点灯 年7.5回に合わせたもの）")
    res = L.run_all(rsi_rate_matched)
    _summ(res)
    out["references"]["rsi14_rate_matched"] = {"theta_s": cal, "results": {f"{k[0]}/{k[1]}": v for k, v in res.items()}}

    for name, fname, fn, desc in cands:
        print(f"\n=== {name} ({fname})")
        res = L.run_all(fn)
        _summ(res)
        causal = {}
        for dname, df in data.items():
            causal[dname] = L.check_causal(fn, df)
        print("check_causal:", {k: float(v) for k, v in causal.items()})
        nulls = {}
        for dname, pname in (("nasdaq3x", "test"), ("sp3x_close", "oos2019")):
            df = data[dname]
            m = L.period_mask(df, L.SETS[dname][1][pname])
            nt = L.null_test(fn(df), df, pivs[dname], m, n=args.n_null)
            nulls[f"{dname}/{pname}"] = nt
            print(f"null_test {dname}/{pname} (real, null_median, p):")
            for side in ("top", "bot"):
                print("  ", side, {k: tuple(round(float(x), 3) for x in v) for k, v in nt[side].items()})
        group = "blend" if fname == "score" else "classic"
        out["candidates"].append({
            "name": name, "function": fname, "description": desc,
            "params": CONST[group],
            "causal_max_diff": float(max(causal.values())),
            "causal_by_set": {k: float(v) for k, v in causal.items()},
            "results": {f"{k[0]}/{k[1]}": v for k, v in res.items()},
            "null": nulls,
        })
    os.makedirs(os.path.join(HERE, "results"), exist_ok=True)
    path = os.path.join(HERE, "results", f"{KEY}.json")
    with open(path, "w") as f:
        json.dump(_jsonable(out), f, ensure_ascii=False, indent=1, default=float)
    print("\nsaved", path)


if __name__ == "__main__":
    main()
