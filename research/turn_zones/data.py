"""検証用データ: 実指数の日足から3倍レバレッジ相当を合成する.

- NQ3x: NASDAQ総合 1999-2018 (arch パッケージ同梱) → TQQQ 相当
- SP3x: S&P500 1999-2018 (arch パッケージ同梱) → SPXL 相当
- GOOG3x / GOOG1x: GOOG 2004-2013 (backtesting パッケージ同梱)

3倍合成は日々リセット(手数料なし): 前日終値に対する O/H/L/C の変化率を3倍する.
出来高は原資産の売買代金 (出来高 × 原資産の終値) をそのまま使う.
"""
import numpy as np
import pandas as pd


def _std(df):
    df = df[["Open", "High", "Low", "Close", "Volume"]].astype(float).copy()
    df.index = pd.to_datetime(df.index)
    df.index.name = "Date"
    return df


def synth(df, lev=3.0, base=100.0):
    o, h, l, c = (df[k].to_numpy() for k in ("Open", "High", "Low", "Close"))
    pc = np.r_[np.nan, c[:-1]]
    c3 = np.empty(len(c))
    c3[0] = base
    for t in range(1, len(c)):
        c3[t] = c3[t - 1] * (1 + lev * (c[t] / pc[t] - 1))
    prev3 = np.r_[np.nan, c3[:-1]]
    out = pd.DataFrame(index=df.index)
    for name, x in (("Open", o), ("High", h), ("Low", l)):
        y = prev3 * (1 + lev * (x / pc - 1))
        y[0] = base * x[0] / c[0]
        out[name] = y
    out["Close"] = c3
    out["Volume"] = df["Volume"].to_numpy() * c   # 原資産の売買代金
    assert (out[["Open", "High", "Low", "Close"]] > 0).all().all()
    assert (out["High"] >= out[["Open", "Close"]].max(axis=1) - 1e-9).all()
    assert (out["Low"] <= out[["Open", "Close"]].min(axis=1) + 1e-9).all()
    return out


def load_all():
    import arch.data.nasdaq as nq
    import arch.data.sp500 as sp
    from backtesting.test import GOOG

    nq_, sp_, gg = _std(nq.load()), _std(sp.load()), _std(GOOG)
    g1 = gg.copy()
    g1["Volume"] = gg["Volume"] * gg["Close"]
    return {
        "NQ3x": synth(nq_),
        "SP3x": synth(sp_),
        "GOOG3x": synth(gg),
        "GOOG1x": g1,
    }


# S&P500 の 1999-2006 年は始値が前日終値で埋められており, 高値・安値も当てにならない.
# 高値・安値を使う案はこの期間を採点しない.
HL_RELIABLE_FROM = {"SP3x": "2007-01-01"}
