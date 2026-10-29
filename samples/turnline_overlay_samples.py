"""TurnLine 表示案サンプル（見た目確認用・合成データ）

サブペインをやめ、メインチャート上で
「そろそろ高値」「そろそろ安値」が事前に・なだらかに分かる表示を3案描画する。

接近度スコアは既知の転換点から逆算した「理想形」であり、的中率は未検証。
"""
import logging
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib import font_manager
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.colors import LinearSegmentedColormap, to_rgb
from matplotlib.path import Path as MPath

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


def stage(v):
    a = abs(v)
    if a >= 80:
        return "高値圏" if v > 0 else "安値圏"
    if a >= 50:
        return "そろそろ高値" if v > 0 else "そろそろ安値"
    if a >= 25:
        return "高値に注意" if v > 0 else "安値に注意"
    return "中立"


def stage_color(v):
    return "#555" if abs(v) < 25 else RED_D if v > 0 else GRN_D


def crossings(s, th=50):
    """|接近度| が th を下から上抜けたバー（転換直後のリセットは除く）"""
    return [i for i in range(1, len(s))
            if abs(s[i]) >= th > abs(s[i - 1]) and np.sign(s[i]) == np.sign(s[i - 1])]


# ---------------------------------------------------------------- 共通描画
def new_fig(title, sub, v):
    fig, ax = plt.subplots(figsize=(7.2, 7.0), dpi=200)
    fig.subplots_adjust(left=0.04, right=0.90, top=0.80, bottom=0.07)
    fig.text(0.04, 0.955, title, fontsize=14)
    fig.text(0.04, 0.918, sub, fontsize=9, color="#555")
    # いまの接近度ゲージ（チャートの外・上部に固定）
    fig.text(0.645, 0.854, f"いまの接近度 {v:+.0f}  {stage(v)}", fontsize=10, color=stage_color(v),
             ha="right", va="center")
    gx = fig.add_axes([0.67, 0.846, 0.23, 0.016])
    gx.imshow(np.linspace(-100, 100, 256)[None, :], aspect="auto", cmap=CMAP, vmin=-100, vmax=100,
              extent=(-100, 100, 0, 1))
    for t in (-50, 50):
        gx.axvline(t, color="white", lw=0.8)
    gx.plot([v], [1.0], marker="v", color="#222", ms=6, clip_on=False, zorder=5)
    gx.set_xlim(-100, 100)
    gx.set_ylim(0, 1)
    gx.set_xticks([-100, -50, 50, 100], ["底", "そろそろ", "そろそろ", "天井"])
    gx.tick_params(labelsize=6.5, length=0, pad=1.5, colors="#555")
    gx.set_yticks([])
    for s in gx.spines.values():
        s.set_visible(False)
    fig.text(0.04, 0.012, "※ 合成データ。接近度は転換点から逆算した理想形（見た目確認用）で、的中率は未検証",
             fontsize=7.5, color="#888")
    return fig, ax


def setup_axes(ax, df, ylim):
    ax.set_xlim(-1, len(df) + 3)
    ax.set_ylim(*ylim)
    ax.set_autoscale_on(False)
    ax.yaxis.tick_right()
    ax.grid(True, color=GRID, lw=0.8, zorder=0)
    ax.set_axisbelow(True)
    for s in ("top", "left"):
        ax.spines[s].set_visible(False)
    ax.spines["right"].set_color("#bbb")
    ax.spines["bottom"].set_color("#bbb")
    months = [i for i in range(1, len(df)) if df.index[i].month != df.index[i - 1].month]
    ax.set_xticks(months, [f"{df.index[i].month}月" for i in months])
    ax.tick_params(colors="#555", labelsize=9, length=0)
    ax.text(0.01, 0.985, "TQQQ・日足（合成データ）", transform=ax.transAxes, fontsize=8.5,
            color="#666", va="top")
    last = df.c.iloc[-1]
    ax.axhline(last, color=UP_C, lw=0.7, ls=":", zorder=2)
    ax.annotate(f"{last:.2f}", (1, last), xycoords=("axes fraction", "data"), xytext=(3, 0),
                textcoords="offset points", va="center", fontsize=8.5, color="white",
                bbox=dict(boxstyle="square,pad=0.2", fc=UP_C, ec="none"))


def draw_candles(ax, df, x):
    up = df.c >= df.o
    for m, col in ((up, UP_C), (~up, DN_C)):
        ax.vlines(x[m], df.l[m], df.h[m], color=col, lw=0.8, zorder=3)
        ax.bar(x[m], (df.c - df.o)[m].abs().clip(lower=0.12), bottom=np.minimum(df.o, df.c)[m],
               width=0.62, color=col, zorder=4)


def draw_turn_labels(ax, df, x, turns, extra=None):
    extra = np.zeros(len(x)) if extra is None else extra
    for i, k in turns:
        if k == "H":
            y, txt, fc, va, dy = df.h.iloc[i] + extra[i], "▼天井確定", RED_D, "bottom", 0.8
        else:
            y, txt, fc, va, dy = df.l.iloc[i] - extra[i], "▲底確定", GRN_D, "top", -0.8
        ax.text(x[i], y + dy, txt, ha="center", va=va, fontsize=8.5, color="white", zorder=8,
                bbox=dict(boxstyle="round,pad=0.25", fc=fc, ec="none"))


def gradient_fill(ax, x, lower, upper, alpha, color, zorder=2):
    """lower〜upper の領域を、x方向に alpha が連続変化する単色で塗る（縞が出ない）"""
    pc = ax.fill_between(x, lower, upper, facecolor="none", edgecolor="none")
    xs = np.linspace(x[0], x[-1], len(x) * 16)
    rgba = np.zeros((1, len(xs), 4))
    rgba[..., :3] = to_rgb(color)
    rgba[..., 3] = np.interp(xs, x, alpha)
    ylo, yhi = min(lower.min(), upper.min()), max(lower.max(), upper.max())
    im = ax.imshow(rgba, aspect="auto", origin="lower", interpolation="bilinear",
                   extent=(x[0], x[-1], ylo, yhi), zorder=zorder)
    im.set_clip_path(MPath.make_compound_path(*pc.get_paths()), transform=ax.transData)


# ---------------------------------------------------------------- 案C: 価格に寄り添う帯
def plan_c(df, x, s, turns):
    fig, ax = new_fig("案C　価格に寄り添う「なだらかな帯」",
                      "天井が近づくと高値の上に赤い帯、底が近づくと安値の下に緑の帯が、だんだん太く濃くなる",
                      s[-1])
    setup_axes(ax, df, (49, 94))
    gap, width = 0.8, 3.0
    extra = np.zeros(len(x))
    edges = {}
    for sign, col, ref in ((1, RED, df.h.rolling(3, center=True, min_periods=1).max()),
                           (-1, GRN, df.l.rolling(3, center=True, min_periods=1).min())):
        v = np.where(np.sign(s) == sign, np.abs(s), 0) / 100
        inner = ref.to_numpy() + sign * gap
        outer = inner + sign * v * width
        gradient_fill(ax, x, inner, outer, np.where(v > 0, 0.12 + 0.78 * v, 0), col)
        extra = np.maximum(extra, gap + v * width)
        edges[sign] = outer
    draw_candles(ax, df, x)
    draw_turn_labels(ax, df, x, turns, extra)
    for i in crossings(s):
        sign = 1 if s[i] > 0 else -1
        y = edges[sign][i]
        col = RED_D if sign > 0 else GRN_D
        ax.plot(x[i], y, "o", ms=3.5, color=col, zorder=6)
        ax.text(x[i] - 0.8, y + sign * 0.3, "そろそろ高値" if sign > 0 else "そろそろ安値",
                ha="right", va="bottom" if sign > 0 else "top", fontsize=7.5, color=col, zorder=6)
    return fig


# ---------------------------------------------------------------- 案D: 背景グラデーション
def plan_d(df, x, s, turns):
    fig, ax = new_fig("案D　背景がじわっと色づく",
                      "チャート背景を接近度で塗る。薄い＝注意 → 濃い＝そろそろ。別ウィンドウ不要",
                      s[-1])
    ylim = (50, 92)
    setup_axes(ax, df, ylim)
    xs = np.linspace(-0.5, len(x) - 0.5, len(x) * 16)
    v = np.interp(xs, x, s)
    rgba = np.zeros((1, len(xs), 4))
    rgba[0, :, :3] = np.where((v > 0)[:, None], to_rgb(RED), to_rgb(GRN))
    rgba[0, :, 3] = np.where(np.abs(v) < 12, 0, 0.04 + 0.30 * (np.abs(v) / 100) ** 1.4)
    ax.imshow(rgba, aspect="auto", origin="lower", interpolation="bilinear",
              extent=(-0.5, len(x) - 0.5, *ylim), zorder=0)
    draw_candles(ax, df, x)
    draw_turn_labels(ax, df, x, turns)
    for i in crossings(s):
        col = RED_D if s[i] > 0 else GRN_D
        ax.text(x[i], ylim[0] + 0.6, "そろそろ", ha="center", va="bottom", fontsize=7, color=col,
                zorder=6, bbox=dict(boxstyle="round,pad=0.15", fc="white", ec="none", alpha=0.75))
    return fig


# ---------------------------------------------------------------- 案E: 下端の温度リボン
def plan_e(df, x, s, turns):
    fig, ax = new_fig("案E　チャート下端の「温度リボン」",
                      "ローソク足の真下に1本のグラデーション帯。色の濃さだけで天井/底の近さが分かる",
                      s[-1])
    setup_axes(ax, df, (45.5, 92))
    y0, h = 46.5, 3.0
    xs = np.linspace(0, len(x) - 1, len(x) * 16)
    ax.imshow(np.interp(xs, x, s)[None, :], aspect="auto", cmap=CMAP, vmin=-100, vmax=100,
              extent=(0, len(x) - 1, y0, y0 + h), zorder=2, interpolation="bilinear")
    ax.add_patch(plt.Rectangle((0, y0), len(x) - 1, h, fill=False, ec="#ccc", lw=0.6, zorder=3))
    ax.text(0.8, y0 + h / 2, "接近度", fontsize=7, ha="left", va="center", color="#777", zorder=5)
    for i in crossings(s):
        col = RED_D if s[i] > 0 else GRN_D
        ax.plot([x[i], x[i]], [y0, y0 + h], color="white", lw=1.2, zorder=4)
        ax.text(x[i], y0 + h + 0.3, "そろそろ高値" if s[i] > 0 else "そろそろ安値", fontsize=7,
                ha="center", va="bottom", color=col)
    draw_candles(ax, df, x)
    draw_turn_labels(ax, df, x, turns)
    return fig


if __name__ == "__main__":
    df, turns = make_prices()
    x = np.arange(len(df))
    s = proximity(len(df), turns)
    figs = {"C_band": plan_c(df, x, s, turns),
            "D_background": plan_d(df, x, s, turns),
            "E_ribbon": plan_e(df, x, s, turns)}
    with PdfPages(OUT / "TurnLine_samples_CDE.pdf") as pdf:
        for name, fig in figs.items():
            fig.savefig(OUT / f"TurnLine_plan{name}.png")
            pdf.savefig(fig)
    print("saved:", *sorted(p.name for p in OUT.iterdir()))
