"""TurnLine サンプル共通部品（合成データ・接近度・ローソク足描画）

接近度スコアは既知の転換点から逆算した「理想形」であり、的中率は未検証。
"""
import logging
from pathlib import Path
from types import SimpleNamespace

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib import font_manager
from matplotlib.colors import LinearSegmentedColormap

OUT = Path(__file__).parent / "out"
OUT.mkdir(exist_ok=True)

logging.getLogger("matplotlib.font_manager").setLevel(logging.ERROR)
for f in ("Noto Sans CJK JP", "IPAGothic", "IPAPGothic"):
    if any(f == x.name for x in font_manager.fontManager.ttflist):
        plt.rcParams["font.family"] = f
        break

RED, RED_D = "#d9534f", "#8e1c1c"
GRN, GRN_D = "#26a269", "#145a32"
UP_C, DN_C = "#26a69a", "#ef5350"
GRID = "#ececec"
CMAP = LinearSegmentedColormap.from_list(
    "turn", [(0, GRN_D), (0.25, GRN), (0.5, "#f4f4f4"), (0.75, RED), (1, RED_D)])

# 段階のしきい値（|接近度|）: 注意 / そろそろ / 圏
TH_CAUTION, TH_SOON, TH_ZONE = 25, 50, 80

# ---------------------------------------------------------------- 合成データ
# (日付, 価格, 種別)  種別: H=天井 L=底 None=通過点
ANCHORS = [
    ("2026-06-08", 68.0, "L"), ("2026-07-01", 79.5, "H"),
    ("2026-07-28", 57.5, "L"), ("2026-08-18", 77.8, "H"),
    ("2026-08-25", 67.8, None), ("2026-09-02", 73.0, None),
    ("2026-09-14", 66.3, "L"), ("2026-10-01", 85.5, "H"),
    ("2026-10-19", 67.2, "L"), ("2026-10-29", 72.6, None),
]


def make_prices(seed=7):
    rng = np.random.default_rng(seed)
    days = pd.bdate_range(ANCHORS[0][0], ANCHORS[-1][0])
    ax = pd.to_datetime([a[0] for a in ANCHORS])
    idx = np.array([days.get_indexer([d], method="nearest")[0] for d in ax])
    base = np.interp(np.arange(len(days)), idx, [a[1] for a in ANCHORS])
    noise = np.convolve(rng.normal(0, 0.9, len(days)), np.ones(3) / 3, "same")
    noise[idx] = 0
    close = base + noise
    open_ = np.r_[close[0], close[:-1]] + rng.normal(0, 0.5, len(days))
    hi = np.maximum(open_, close) + np.abs(rng.normal(0.5, 0.35, len(days)))
    lo = np.minimum(open_, close) - np.abs(rng.normal(0.5, 0.35, len(days)))
    for i, (_, p, k) in zip(idx, ANCHORS):
        if k == "H":
            hi[i] = p + 0.6
        elif k == "L":
            lo[i] = p - 0.6
    df = pd.DataFrame({"o": open_, "h": hi, "l": lo, "c": close}, index=days)
    turns = [(i, k) for i, (_, _, k) in zip(idx, ANCHORS) if k]
    return df, turns


def proximity(n, turns):
    """-100(底が近い) 〜 +100(天井が近い)。脚の後半からなだらかに立ち上がる理想形。"""
    s = np.zeros(n)
    pts = turns + [(n - 1, None)]
    for (i0, k0), (i1, k1) in zip(pts[:-1], pts[1:]):
        sign = 1 if k0 == "L" else -1
        length = i1 - i0 if k1 else 18  # 進行中の脚は想定長で
        for i in range(i0 + 1, i1 + 1):
            p = (i - i0) / length
            x = np.clip((p - 0.30) / 0.70, 0, 1)
            s[i] = sign * 100 * x * x * (3 - 2 * x)  # smoothstep
    return s


def load():
    """df(OHLC) / turns[(bar, 'H'|'L')] / x(バー番号) / s(接近度) をまとめて返す"""
    df, turns = make_prices()
    return SimpleNamespace(df=df, turns=turns, x=np.arange(len(df)), s=proximity(len(df), turns))


def stage(v):
    a = abs(v)
    if a >= TH_ZONE:
        return "高値圏" if v > 0 else "安値圏"
    if a >= TH_SOON:
        return "そろそろ高値" if v > 0 else "そろそろ安値"
    if a >= TH_CAUTION:
        return "高値に注意" if v > 0 else "安値に注意"
    return "中立"


def stage_color(v):
    return "#555" if abs(v) < TH_CAUTION else RED_D if v > 0 else GRN_D


def crossings(s, th=TH_SOON):
    """|接近度| が th を下から上抜けたバー（転換直後のリセットは除く）"""
    return [i for i in range(1, len(s))
            if abs(s[i]) >= th > abs(s[i - 1]) and np.sign(s[i]) == np.sign(s[i - 1])]


# ---------------------------------------------------------------- 描画部品
def style_axes(ax, df, months=True):
    """右目盛り・薄いグリッド・月ラベル（months=False で月ラベルを隠す）"""
    ax.set_xlim(-1, len(df) + 3)
    ax.yaxis.tick_right()
    ax.grid(True, color=GRID, lw=0.8)
    ax.set_axisbelow(True)
    for s in ("top", "left"):
        ax.spines[s].set_visible(False)
    for s in ("right", "bottom"):
        ax.spines[s].set_color("#bbb")
    month_idx = [i for i in range(1, len(df)) if df.index[i].month != df.index[i - 1].month]
    ax.set_xticks(month_idx, [f"{df.index[i].month}月" for i in month_idx])
    ax.tick_params(colors="#555", labelsize=9, length=0, labelbottom=months)


def price_tag(ax, last):
    ax.axhline(last, color=UP_C, lw=0.7, ls=":", zorder=2)
    ax.annotate(f"{last:.2f}", (1, last), xycoords=("axes fraction", "data"), xytext=(3, 0),
                textcoords="offset points", va="center", fontsize=8.5, color="white",
                bbox=dict(boxstyle="square,pad=0.2", fc=UP_C, ec="none"))


def setup_price_axes(ax, df, ylim, months=True, label="TQQQ・日足（合成データ）"):
    style_axes(ax, df, months)
    ax.set_ylim(*ylim)
    ax.set_autoscale_on(False)
    ax.text(0.01, 0.985, label, transform=ax.transAxes, fontsize=8.5, color="#666", va="top")
    price_tag(ax, df.c.iloc[-1])


def draw_candles(ax, df, x, min_body=0.12):
    up = df.c >= df.o
    for m, col in ((up, UP_C), (~up, DN_C)):
        ax.vlines(x[m], df.l[m], df.h[m], color=col, lw=0.8, zorder=3)
        ax.bar(x[m], (df.c - df.o)[m].abs().clip(lower=min_body), bottom=np.minimum(df.o, df.c)[m],
               width=0.62, color=col, zorder=4)


def draw_turn_labels(ax, df, x, turns, extra=None, gap=0.8, texts=("▼天井確定", "▲底確定")):
    """turns の各バーに札を付ける。gap は高値/安値から札までの距離（価格単位）"""
    extra = np.zeros(len(x)) if extra is None else extra
    for i, k in turns:
        if k == "H":
            y, txt, fc, va, dy = df.h.iloc[i] + extra[i], texts[0], RED_D, "bottom", gap
        else:
            y, txt, fc, va, dy = df.l.iloc[i] - extra[i], texts[1], GRN_D, "top", -gap
        ax.text(x[i], y + dy, txt, ha="center", va=va, fontsize=8.5, color="white", zorder=8,
                bbox=dict(boxstyle="round,pad=0.25", fc=fc, ec="none"))


NOTE_SYNTH = "※ 合成データ。接近度は転換点から逆算した理想形（見た目確認用）で、的中率は未検証"


def footer(fig, y=0.012, text=NOTE_SYNTH):
    fig.text(0.04, y, text, fontsize=7.5, color="#888")


def make_two_pane(d, title, sub, height_ratios=(5, 3.2), figsize=(7.2, 9.6), price_ylim=(52, 90),
                  label="TQQQ・日足（合成データ）", note=NOTE_SYNTH, candles=True):
    """上: ローソク足（描画済み） / 下: 別ウィンドウ（空。月ラベルのみ）を返す。
    price_ylim=None なら価格の範囲から自動で決め、札の距離も値幅に合わせる（実データ用）。
    candles=False なら終値の線で描く（高値・安値のないデータ用）"""
    gap, body = 0.8, 0.12
    if price_ylim is None:
        lo, hi = d.df.l.min(), d.df.h.max()
        price_ylim, gap, body = (lo - 0.12 * (hi - lo), hi + 0.12 * (hi - lo)), 0.021 * (hi - lo), 0.003 * (hi - lo)
    fig = plt.figure(figsize=figsize, dpi=200)
    gs = fig.add_gridspec(2, 1, height_ratios=height_ratios, hspace=0.06,
                          left=0.04, right=0.88, top=0.915, bottom=0.05)
    ax_p = fig.add_subplot(gs[0])
    ax_s = fig.add_subplot(gs[1], sharex=ax_p)
    fig.text(0.04, 0.972, title, fontsize=14)
    fig.text(0.04, 0.946, sub, fontsize=9, color="#555")
    setup_price_axes(ax_p, d.df, price_ylim, months=False, label=label)
    if candles:
        draw_candles(ax_p, d.df, d.x, min_body=body)
    else:
        ax_p.plot(d.x, d.df.c, color="#333", lw=1.1, zorder=4)
    draw_turn_labels(ax_p, d.df, d.x, d.turns, gap=gap)
    style_axes(ax_s, d.df, months=True)
    footer(fig, text=note)
    return fig, ax_p, ax_s
