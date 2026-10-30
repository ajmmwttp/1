"""10案 (E1〜E10) の Python 版. Pine の各ファイルと同じ式.

各関数は df (Open/High/Low/Close/Volume) を受け取り, dict を返す:
  line: メインライン (-100..+100), U: 高値圏ライン, L: 安値圏ライン
"""
import numpy as np
import pandas as pd
from numpy.lib.stride_tricks import sliding_window_view as swv

from .helpers import ema_p, pnr, rma_p, ss_p, tanh_p, tr_p, wma3
from .swing import sd_line


def _ohlc(df):
    return (df[k].to_numpy(float) for k in ("Open", "High", "Low", "Close"))


def _const(n, v):
    return np.full(n, float(v))


def e01_regression_kairi(df, n=75, kU=2.3, kD=2.6, th=60.0, sm=5):
    """E1 乖離: 75本の対数回帰線からのズレ ÷ 回帰の残差σ.

    仕上げの EMA は 3 → 5 (E2 と日々の動きが似すぎた相関 0.82 → 0.70 にするため).
    """
    _, _, _, c = _ohlc(df)
    y = np.log(c)
    X = np.arange(n, dtype=float)
    xm = X.mean()
    vx = (n * n - 1) / 12.0
    W = swv(y, n)
    ym = W.mean(1)
    b = ((W - ym[:, None]) * (X - xm)).mean(1) / vx
    fit = ym + b * (n - 1 - xm)
    vy = W.var(1)
    sres = np.sqrt(np.maximum(vy - b * b * vx, 0.0))
    zc = np.full(len(y), np.nan)
    zc[n - 1:] = np.where(sres > 0, (y[n - 1:] - fit) / np.where(sres > 0, sres, 1.0), 0.0)
    zsm = ema_p(zc, sm)
    line = np.where(np.isnan(zsm), np.nan, 100 * tanh_p(zsm / np.where(zsm >= 0, kU, kD)))
    return dict(line=line, U=_const(len(c), th), L=_const(len(c), -th))


def e02_tsi_balance(df, r1=6, r2=3, adN=120, adP=90.0, fixT=55.0, adaptive=True):
    """E2 勢い: 上げ幅と下げ幅の綱引き (短期 TSI). ラインは自身の 90/10% 点で自動調整."""
    _, _, _, c = _ohlc(df)
    pc = np.r_[0.0, np.diff(c)]
    num = ema_p(ema_p(pc, r1), r2)
    den = ema_p(ema_p(np.abs(pc), r1), r2)
    line = np.clip(np.where(den > 0, 100 * num / np.where(den > 0, den, 1.0), 0.0), -100, 100)
    if not adaptive:
        return dict(line=line, U=_const(len(c), fixT), L=_const(len(c), -fixT))
    pu = pnr(line, adN, adP)
    pl = pnr(line, adN, 100.0 - adP)
    U = np.where(np.isnan(pu), fixT, np.clip(pu, 35, 75))
    L = np.where(np.isnan(pl), -fixT, np.clip(pl, -75, -35))
    return dict(line=line, U=U, L=L)


def e03_speed_retention(df, P=4, sigN=100, flr=1.0, post=3, th=45.0):
    """E3 加速・失速: 今の脚の最高速度からどれだけ減速したか."""
    _, _, _, c = _ohlc(df)
    r = np.r_[0.0, np.diff(np.log(c))]
    v = ss_p(r, P)
    sig = rma_p(np.abs(v), sigN)
    raw = np.zeros(len(v))
    side = 0
    pk = 0.0
    for t in range(len(v)):
        s = 1 if v[t] > 0 else (-1 if v[t] < 0 else (side if side != 0 else 1))
        if s != side:
            side, pk = s, abs(v[t])
        else:
            pk = max(pk, abs(v[t]))
        den = max(pk, flr * sig[t])
        raw[t] = side * (pk - abs(v[t])) / den if den > 0 else 0.0
    line = ema_p(100 * raw, post)
    return dict(line=line, U=_const(len(c), th), L=_const(len(c), -th))


def e04_volume_cog(df, ln=10, atrLen=14, normLen=252, kk=1.5, th=60.0):
    """E4 出来高: 直近の大商いが高い価格帯と安い価格帯のどちらに集まったか (出来高重心).

    df["Volume"] は売買代金 (Pine の初期設定 = 出来高 × 終値 に相当).
    """
    _, h, l, c = _ohlc(df)
    v = np.nan_to_num(df["Volume"].to_numpy(float))
    w = (v > 0).astype(float)       # 出来高の無い足は, 出来高の重心にも価格の平均にも入れない
    tp = (h + l + c) / 3
    evh = ema_p(v * tp, ln)
    ev = ema_p(v, ln)
    ewh = ema_p(w * tp, ln)
    ew = ema_p(w, ln)
    atr = rma_p(tr_p(h, l, c), atrLen)
    ok = (ev > 0) & (ew > 0) & (atr > 0)
    raw = np.where(ok, (evh / np.where(ok, ev, 1.0) - ewh / np.where(ok, ew, 1.0)) / np.where(ok, atr, 1.0), 0.0)
    rms = np.sqrt(pd.Series(raw * raw).rolling(normLen).mean().to_numpy())
    good = (rms > 0) & (np.cumsum(v > 0) >= normLen)
    line = np.where(good, 100 * tanh_p(raw / np.where(good, rms, 1.0) / kk), np.nan)
    return dict(line=line, U=_const(len(c), th), L=_const(len(c), -th), raw=raw)


def e05_swing_age(df, k=3.0, th=70.0, **kw):
    """E5 日柄: 今の大波が過去の同じ向きの大波と比べて日数的にどれだけ成熟したか."""
    _, h, l, c = _ohlc(df)
    raw, dirs = sd_line(c, h, l, k=k, mode="age", **kw)
    return dict(line=raw, U=_const(len(c), th), L=_const(len(c), -th), dir=dirs)


def e06_swing_extension(df, k=2.0, up=70.0, dn=-55.0, smooth=True, handoff=0.8, **kw):
    """E6 値幅: 今の波の値幅が過去8回の同じ向きの波の何割より大きいか.

    極値から 0.8θ 戻すと線が0になる (最長ゾーン日数を抑えつつ E2 と似すぎないよう 1.0 → 0.8).
    """
    _, h, l, c = _ohlc(df)
    raw, dirs = sd_line(c, h, l, k=k, mode="ext", handoff=handoff, **kw)
    line = wma3(raw) if smooth else raw
    return dict(line=line, U=_const(len(c), up), L=_const(len(c), dn), dir=dirs)


def e07_cycle_phase(df, P=20, z0=0.5, th=85.0):
    """E7 周期: 直近20本を1周期の波 (cos / -sin) と相関させて位相を読む."""
    _, _, _, c = _ohlc(df)
    x = np.log(c)
    i = np.arange(P)
    W = swv(x, P)[:, ::-1]          # 列 i = i 本前
    n = float(P)
    sx = W.sum(1)
    vx = n * (W * W).sum(1) - sx * sx

    def corr(y):
        sy = y.sum()
        vy = n * (y * y).sum() - sy * sy
        return np.where(vx > 0, (n * (W @ y) - sx * sy) / np.sqrt(np.where(vx > 0, vx, 1.0) * vy), 0.0)

    re = corr(np.cos(2 * np.pi * i / P))
    im = corr(-np.sin(2 * np.pi * i / P))
    mag = np.sqrt(re * re + im * im)
    line = np.full(len(x), np.nan)
    line[P - 1:] = 100 * re / np.maximum(mag, z0)
    return dict(line=line, U=_const(len(c), th), L=_const(len(c), -th))


def _run_len(b):
    out = np.zeros(len(b))
    r = 0
    for t, v in enumerate(b):
        r = r + 1 if v else 0
        out[t] = r
    return out


def _hold(f, rho):
    out = np.zeros(len(f))
    m = 0.0
    for t, v in enumerate(f):
        m = max(v, rho * m)
        out[t] = m
    return out


def e08_hhhl_streak(df, N=5, rho=0.5, th=65.0):
    """E8 連続: 高値・安値の切り上げ(切り下げ)が続いた日数の階段."""
    _, h, l, c = _ohlc(df)
    hp, lp = np.r_[np.nan, h[:-1]], np.r_[np.nan, l[:-1]]
    with np.errstate(invalid="ignore"):
        hh, lh = h > hp, h < hp
        hl, ll = l > lp, l < lp

    def F(b):
        return np.minimum(_run_len(b) / N, 1)

    line = 100 * ((_hold(F(hh), rho) - _hold(F(ll), rho)) + (_hold(F(hl), rho) - _hold(F(lh), rho))) / 2
    return dict(line=line, U=_const(len(c), th), L=_const(len(c), -th))


def e09_reversal_impulse(df, pLen=8, sm=3, scale=0.25, th=45.0):
    """E9 ローソク足の形: 高値引けが続いた後の安値引け(逆も)を捉える確認型.

    直前の引け圧力の期間は 5 → 8 (突入が年15回を超えて多すぎたため).
    """
    _, h, l, c = _ohlc(df)
    rng = h - l
    clv = np.where(rng > 0, (2 * c - h - l) / np.where(rng > 0, rng, 1.0), 0.0)
    pN = ema_p(2 * c - h - l, pLen)
    pD = ema_p(rng, pLen)
    P = np.where(pD > 0, pN / np.where(pD > 0, pD, 1.0), np.nan)
    Pp = np.r_[np.nan, P[:-1]]
    r = np.where(np.isnan(Pp), np.nan,
                 np.maximum(Pp, 0) * np.maximum(-clv, 0) - np.maximum(-Pp, 0) * np.maximum(clv, 0))
    line = 100 * tanh_p(ema_p(r, sm) / scale)
    line[:20] = np.nan        # 最初の20本は初期値の影響が大きいので出さない (Pine と同じ)
    return dict(line=line, U=_const(len(c), th), L=_const(len(c), -th))


def e10_vol_term_gauge(df, fL=3, sL=30, gL=5, sh=4.0, wb=0.5, smL=3, kUp=0.45, kDn=0.26, th=60.0):
    """E10 値動きの荒さ: 下げで値幅が急拡大=恐怖(安値圏), 値幅が縮み静かすぎる=慢心(高値圏)."""
    _, h, l, c = _ohlc(df)
    pc = np.r_[np.nan, c[:-1]]
    trp = tr_p(h, l, c) / pc
    vf = rma_p(trp, fL)
    vs = rma_p(trp, sL)
    with np.errstate(invalid="ignore", divide="ignore"):
        vr = np.where(np.isnan(vf) | np.isnan(vs), np.nan,
                      np.where((vf > 0) & (vs > 0), np.log(np.where(vf > 0, vf, 1.0) / np.where(vs > 0, vs, 1.0)), 0.0))
    r = np.r_[0.0, np.diff(np.log(c))]
    up2 = ema_p(np.where(r > 0, r * r, 0.0), gL)
    dn2 = ema_p(np.where(r < 0, r * r, 0.0), gL)
    den = up2 + dn2
    gate = np.where(den > 0, tanh_p(sh * (dn2 - up2) / np.where(den > 0, den, 1.0)), 0.0)
    w = np.where(gate > 0, gate, wb * gate)
    xx = np.where(np.isnan(vr), np.nan, np.where(vr > 0, -vr * w, -vr))
    xs = ema_p(xx, smL)
    line = np.where(np.isnan(xs), np.nan, 100 * tanh_p(xs / np.where(xs >= 0, kUp, kDn)))
    line[:5 * sL] = np.nan    # 最初の 5×基準期間 は初期値の影響が大きいので出さない (Pine と同じ)
    return dict(line=line, U=_const(len(c), th), L=_const(len(c), -th))


# 画面表示用の情報 (名前・種類・Pine ファイル名)
REGISTRY = {
    "E1": dict(fn=e01_regression_kairi, name="回帰トレンド乖離", element="乖離", kind="先行",
               pine="E01_regression_kairi.pine", uses_hl=False),
    "E2": dict(fn=e02_tsi_balance, name="勢いバランス(短期TSI)", element="勢い", kind="先行",
               pine="E02_tsi_balance.pine", uses_hl=False),
    "E3": dict(fn=e03_speed_retention, name="失速率", element="加速・失速", kind="確認寄り",
               pine="E03_speed_retention.pine", uses_hl=False),
    "E4": dict(fn=e04_volume_cog, name="出来高重心", element="出来高", kind="状況",
               pine="E04_volume_cog.pine", uses_hl=True),
    "E5": dict(fn=e05_swing_age, name="日柄成熟度(大波)", element="日柄", kind="先行",
               pine="E05_swing_age_maturity.pine", uses_hl=True),
    "E6": dict(fn=e06_swing_extension, name="値幅達成率", element="値幅", kind="先行",
               pine="E06_swing_extension_pct.pine", uses_hl=True),
    "E7": dict(fn=e07_cycle_phase, name="サイクル位相", element="周期", kind="先行",
               pine="E07_cycle_phase.pine", uses_hl=False),
    "E8": dict(fn=e08_hhhl_streak, name="高値・安値切り上げ連続", element="連続", kind="先行",
               pine="E08_hhhl_streak.pine", uses_hl=True),
    "E9": dict(fn=e09_reversal_impulse, name="反転インパルス", element="ローソク足の形", kind="確認",
               pine="E09_reversal_impulse.pine", uses_hl=True),
    "E10": dict(fn=e10_vol_term_gauge, name="恐怖・慢心ゲージ", element="値動きの荒さ", kind="底は当日/天井は慢心",
                pine="E10_vol_term_gauge.pine", uses_hl=True),
}
