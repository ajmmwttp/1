"""TurnLine 表示案サンプル：メインチャート重ね表示版（見た目確認用・合成データ）

サブペインをやめ、メインチャート上で
「そろそろ高値」「そろそろ安値」が事前に・なだらかに分かる表示を3案描画する。

接近度スコアは既知の転換点から逆算した「理想形」であり、的中率は未検証。
"""

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.colors import to_rgb
from matplotlib.path import Path as MPath

from turnline_common import (CMAP, GRN, GRN_D, OUT, RED, RED_D, crossings, draw_candles,
                             draw_turn_labels, footer, load, setup_price_axes, stage,
                             stage_color)


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
    footer(fig)
    return fig, ax


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
    setup_price_axes(ax, df, (49, 94))
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
    setup_price_axes(ax, df, ylim)
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
    setup_price_axes(ax, df, (45.5, 92))
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
    d = load()
    df, turns, x, s = d.df, d.turns, d.x, d.s
    figs = {"C_band": plan_c(df, x, s, turns),
            "D_background": plan_d(df, x, s, turns),
            "E_ribbon": plan_e(df, x, s, turns)}
    with PdfPages(OUT / "TurnLine_samples_CDE.pdf", metadata={"CreationDate": None}) as pdf:
        for name, fig in figs.items():
            fig.savefig(OUT / f"TurnLine_plan{name}.png")
            pdf.savefig(fig)
    print("saved:", *sorted(p.name for p in OUT.iterdir()))
