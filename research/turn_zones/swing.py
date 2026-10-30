"""E5(日柄)・E6(値幅)共通: 過去データだけで判定するスイング検出 (SD).

x = ln(close). 反転幅 θ = k × (対数 TR の Wilder RMA, 最初の nAtr 本は SMA で初期化).
極値から θ 以上戻したら, その極値を確定したスイングとして記録する.
未来のデータは使わない. Pine の type Swing / method step と同じ手順.
"""
import math

import numpy as np

from .helpers import kc


def log_atr(c, h, l, nAtr=50):
    x = np.log(c)
    lh, ll = np.log(h), np.log(l)
    xp = np.r_[np.nan, x[:-1]]
    trL = np.where(np.isnan(xp), lh - ll, np.maximum.reduce([lh - ll, np.abs(lh - xp), np.abs(ll - xp)]))
    atr = np.full(len(x), np.nan)
    s = np.nan
    acc = 0.0
    cnt = 0
    for i, v in enumerate(trL):
        if math.isnan(s):
            acc += v
            cnt += 1
            if cnt == nAtr:
                s = acc / nAtr
        else:
            s += (v - s) / nAtr
        atr[i] = s
    return atr


def sd_line(c, h, l, k, mode, nAtr=50, K=8, Kmin=3, tau=4.0, handoff=1.0):
    """mode='age' → E5 の生の線, mode='ext' → E6 の生の線. 戻り値 (raw, dir).

    handoff: E6 で線を0まで下げる戻り幅 (θ に対する割合). 1.0 なら反転確定でちょうど0.
    """
    x = np.log(c)
    th = k * log_atr(c, h, l, nAtr)
    n = len(x)
    raw = np.full(n, np.nan)
    dirs = np.zeros(n, int)
    D = {1: [], -1: []}
    A = {1: [], -1: []}
    d = 0
    hX = None

    def scan(frm, t, want_max):
        # [frm, t] の中で最初に現れる最大値(最小値). Pine f_scan と同じく最大999本前まで.
        a = max(frm, t - 999)
        seg = x[a:t + 1]
        j = int(np.argmax(seg) if want_max else np.argmin(seg))
        return seg[j], a + j

    for t in range(n):
        v, hh = x[t], th[t]
        if math.isnan(hh):
            continue
        if d == 0:
            if hX is None:
                hX = hcX = lX = lcX = v
                hB = hcB = lB = lcB = t
            else:
                if v > hX:
                    hX, hB, hcX, hcB = v, t, v, t
                elif v < hcX:
                    hcX, hcB = v, t
                if v < lX:
                    lX, lB, lcX, lcB = v, t, v, t
                elif v > lcX:
                    lcX, lcB = v, t
            if hX - v >= hh:
                d = -1
                pX, pB, eX, eB = hX, hB, hcX, hcB
                cX, cB = scan(eB, t, True)
            elif v - lX >= hh:
                d = 1
                pX, pB, eX, eB = lX, lB, lcX, lcB
                cX, cB = scan(eB, t, False)
        else:
            if d * (v - eX) > 0:
                eX, eB, cX, cB = v, t, v, t
            elif d * (v - cX) < 0:
                cX, cB = v, t
            if d * (eX - v) >= hh:
                D[d].append(float(eB - pB))
                A[d].append(abs(eX - pX))
                if len(D[d]) > K:
                    D[d].pop(0)
                    A[d].pop(0)
                pX, pB, eX, eB = eX, eB, cX, cB
                cX, cB = scan(eB, t, d == 1)
                d = -d
        dirs[t] = d
        if d != 0:
            if mode == "age" and len(D[d]) >= min(Kmin, K):
                raw[t] = 100 * d * kc(eB - pB, D[d], 0.15, 1.0) * math.exp(-((t - eB) / tau) ** 2)
            if mode == "ext" and len(A[d]) >= min(Kmin, K):
                u = min(1.0, max(0.0, d * (eX - v) / (handoff * hh)))
                raw[t] = 100 * d * kc(abs(eX - pX), A[d], 0.15, 0.0) * (1 - u)
    return raw, dirs
