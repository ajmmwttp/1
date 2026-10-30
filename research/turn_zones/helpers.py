"""Pine 側のヘルパーと同じ計算を Python で再現する.

再帰する計算は pandas の ewm/rolling を使わず for ループで書く
(初期化と na の扱いを Pine と完全に揃えるため).
"""
import math

import numpy as np
import pandas as pd


def ema_p(x, n, alpha=None):
    """Pine f_ema: 最初の非 na 値で初期化し, na が来たら次の値で再初期化."""
    a = 2.0 / (n + 1) if alpha is None else alpha
    out = np.full(len(x), np.nan)
    s = np.nan
    for t, v in enumerate(np.asarray(x, float)):
        s = v if math.isnan(s) else a * v + (1 - a) * s
        out[t] = s
    return out


def rma_p(x, n):
    """Pine f_rma (alpha = 1/n, 初期化は ema_p と同じ)."""
    return ema_p(x, n, 1.0 / n)


def tanh_p(x):
    """Pine f_tanh: オーバーフローしない tanh. na は na のまま."""
    x = np.asarray(x, float)
    e = np.exp(-2 * np.abs(x))
    return np.sign(x) * (1 - e) / (1 + e)


def ss_p(x, P):
    """Ehlers 2極 SuperSmoother. 最初の2本は入力をそのまま通す."""
    a1 = math.exp(-math.sqrt(2) * math.pi / P)
    c2 = 2 * a1 * math.cos(math.sqrt(2) * math.pi / P)
    c3 = -a1 * a1
    c1 = 1 - c2 - c3
    x = np.asarray(x, float)
    y = x.copy()
    for t in range(2, len(y)):
        y[t] = c1 * (x[t] + x[t - 1]) / 2 + c2 * y[t - 1] + c3 * y[t - 2]
    return y


def pnr(x, n, p):
    """Pine f_pnr: 直近 n 個の非 na 値(当日含む)を昇順に並べた ceil(p*n/100) 番目."""
    out = np.full(len(x), np.nan)
    buf = []
    k = math.ceil(p * n / 100.0) - 1
    for t, v in enumerate(x):
        if not math.isnan(v):
            buf.append(v)
            if len(buf) > n:
                buf.pop(0)
        if len(buf) == n:
            out[t] = sorted(buf)[k]
    return out


def wma3(x):
    """(3x_t + 2x_{t-1} + x_{t-2}) / 6. どれかが na なら na."""
    s = pd.Series(np.asarray(x, float))
    return ((3 * s + 2 * s.shift(1) + s.shift(2)) / 6).to_numpy()


def tr_p(h, l, c):
    """ta.tr(true): 0本目は H-L."""
    pc = np.r_[np.nan, c[:-1]]
    return np.where(np.isnan(pc), h - l, np.maximum(h, pc) - np.minimum(l, pc))


def kc(v, a, rho, c0):
    """なめらかなパーセンタイル: v が過去の値 a_j より大きい度合いの平均 (0..1)."""
    a = np.asarray(a, float)
    z = np.clip(-(v - a) / (rho * a + c0), -50, 50)
    return float(np.mean(1 / (1 + np.exp(z))))


def zones(line, U, L, hyst=0.0):
    """Pine のゾーン状態機械と同一. 戻り値: 状態(+1/0/-1) と 4種類のイベント."""
    n = len(line)
    st = np.zeros(n, int)
    z = 0
    ev = {k: np.zeros(n, bool) for k in ("topIn", "topOut", "botIn", "botOut")}
    for t in range(n):
        p = z
        if not (np.isnan(line[t]) or np.isnan(U[t]) or np.isnan(L[t])):
            if z == 1 and line[t] <= U[t] - hyst:
                z = 0
            elif z == -1 and line[t] >= L[t] + hyst:
                z = 0
            if z == 0:
                z = 1 if line[t] > U[t] else (-1 if line[t] < L[t] else 0)
        st[t] = z
        ev["topIn"][t] = z == 1 and p != 1
        ev["topOut"][t] = p == 1 and z != 1
        ev["botIn"][t] = z == -1 and p != -1
        ev["botOut"][t] = p == -1 and z != -1
    return st, ev
