"""TurnLine 表示案F：別ウィンドウの「グラデーション・ヒストグラム」（見た目確認用・合成データ）

1日1本の棒で接近度を描く。天井が近いほど上向きの赤い棒が、底が近いほど下向きの緑の棒が、
なだらかに伸びて濃くなる（色は 中立→注意→そろそろ→圏 の4段、棒の中の白い切れ目は 25/50/80）。
各脚で初めて ±25 に届いた棒に ○注意、±50 に届いた棒に ● と「そろそろ高値/安値」札を付け、
最新の棒は枠で囲んで右端の段階帯の「いま」へ点線で結ぶ。

接近度スコアは既知の転換点から逆算した「理想形」であり、的中率は未検証。
"""
import numpy as np
from matplotlib.offsetbox import AnchoredOffsetbox, DrawingArea, HPacker, TextArea
from matplotlib.patches import Rectangle
from matplotlib.transforms import blended_transform_factory

from turnline_common import (GRN, GRN_D, OUT, RED, RED_D, TH_CAUTION, TH_SOON, TH_ZONE, crossings,
                             load, make_two_pane, stage, stage_color)

# 段階ごとの棒の色: 中立 / 注意 / そろそろ / 圏
SHADES = {1: ("#efb3b0", "#e4807b", RED, RED_D), -1: ("#b9e0cb", "#6fc196", GRN, GRN_D)}
THS = (TH_CAUTION, TH_SOON, TH_ZONE)
BANDS = ((0, TH_CAUTION), (TH_CAUTION, TH_SOON), (TH_SOON, TH_ZONE), (TH_ZONE, 100))
NAMES = {1: ("中立", "高値に注意", "そろそろ高値", "高値圏"), -1: (None, "安値に注意", "そろそろ安値", "安値圏")}
BAR_W = 0.92
LANE = 112  # 「そろそろ」札を並べる段（±100 の外側）
YLIM = (-126, 148)
RIGHT = 0.835  # 右端の段階帯と読み値のぶん、軸の右端を内側へ


def sgn(v):
    return 1 if v >= 0 else -1


def shade(v):
    return SHADES[sgn(v)][sum(abs(v) >= t for t in THS)]


def dark(v):
    return RED_D if v >= 0 else GRN_D


def per_pt(fig, ax):
    """1pt の長さ（x は軸の幅に対する比、y はデータ単位）"""
    pos = ax.get_position()
    y0, y1 = ax.get_ylim()
    return 1 / (pos.width * fig.get_figwidth() * 72), (y1 - y0) / (pos.height * fig.get_figheight() * 72)


def bars(ax, x, s):
    ax.bar(x, s, width=BAR_W, color=[shade(v) for v in s], linewidth=0, zorder=2)
    for t in THS:  # 棒の中の白い切れ目（25/50/80 の目盛り）
        m = np.abs(s) > t + 2
        ax.hlines(np.sign(s[m]) * t, x[m] - BAR_W / 2, x[m] + BAR_W / 2, color="white", lw=1.0, zorder=3)
    for sg, c in ((1, RED), (-1, GRN)):
        ax.axhline(sg * TH_SOON, color=c, lw=1.0, ls=(0, (4, 3)), alpha=0.4, zorder=1)
    ax.axhline(0, color="#999", lw=1.0, zorder=3)


def marks(fig, ax, x, s):
    """○注意（±25 に初めて届いた棒）と ●そろそろ（±50）。札は ±100 の外の段に置き、線で棒と結ぶ"""
    for i in crossings(s, TH_CAUTION):
        ax.plot(x[i], s[i], "o", ms=5.5, mfc="white", mec=dark(s[i]), mew=1.2, zorder=6)
        ax.annotate("注意", (x[i], s[i]), xytext=(-5, 0), textcoords="offset points",
                    ha="right", va="bottom" if s[i] > 0 else "top", fontsize=9.5, color=dark(s[i]), zorder=6)
    x0, x1 = ax.get_xlim()
    hw = 34 * (x1 - x0) * per_pt(fig, ax)[0]  # 札の半幅
    for i in crossings(s):
        sg, c = sgn(s[i]), dark(s[i])
        ax.plot([x[i]] * 2, [s[i], sg * LANE], color=c, lw=1.0, zorder=5)
        ax.plot(x[i], s[i], "o", ms=6.5, color=c, mec="white", mew=1.2, zorder=6)
        ax.text(np.clip(x[i], x0 + hw, x1 - hw), sg * LANE, "そろそろ高値" if sg > 0 else "そろそろ安値",
                ha="center", va="center", fontsize=10, color=c, zorder=7,
                bbox=dict(boxstyle="round,pad=0.3", fc="#fdeceb" if sg > 0 else "#e6f4ec",
                          ec=RED if sg > 0 else GRN, lw=1.0))


def now(ax, x, v):
    """最新の棒を枠で囲み、右端の段階帯へ点線で結ぶ（「今日」は棒と反対側）"""
    lo, hi = min(v, 0) - 6, max(v, 0) + 6
    ax.add_patch(Rectangle((x[-1] - 0.62, lo), 1.24, hi - lo, fill=False, ec="#333", lw=1.2, zorder=5))
    ax.text(x[-1], lo - 2 if v >= 0 else hi + 2, "今日", ha="center", va="top" if v >= 0 else "bottom",
            fontsize=9.5, color="#333")
    ax.plot([x[-1] + 0.62, ax.get_xlim()[1]], [v, v], color="#444", lw=1.2, ls=(0, (1, 1.2)), zorder=5)


def scale(fig, ax, v):
    """右端の段階帯（棒と同じ色・同じ高さ）と段階名。いまの位置に ▶ と針、その右に読み値"""
    px, py = per_pt(fig, ax)
    tr = blended_transform_factory(ax.transAxes, ax.transData)
    sx, sw, lx = 1 + 7 * px, 6 * px, 1 + 17 * px
    for sg in (1, -1):
        for (lo, hi), fc in zip(BANDS, SHADES[sg]):
            ax.add_patch(Rectangle((sx, sg * lo), sw, sg * (hi - lo), transform=tr, fc=fc, ec="none",
                                   clip_on=False))
        for t in THS:
            ax.plot([sx, sx + sw], [sg * t] * 2, color="white", lw=1.0, transform=tr, clip_on=False)
    ax.plot([sx - px, sx + sw + px], [v, v], color="#222", lw=1.8, transform=tr, clip_on=False, zorder=7)
    ax.plot(1 + 3.5 * px, v, ">", ms=7, color="#333", transform=tr, clip_on=False, zorder=7)
    top, bot = v + 11 * py, v - 27 * py  # 読み値の上端・下端（重なる段階名は出さない）
    for sg in (1, -1):
        for (lo, hi), name in zip(BANDS, NAMES[sg]):
            y = sg * (lo + hi) / 2 if lo else 0
            if name and not (y - 6 * py < top and y + 6 * py > bot):
                ax.text(lx, y, name, transform=tr, fontsize=10, va="center",
                        color=stage_color(y) if lo else "#666")
    t = ax.annotate("いま", (lx, v), xycoords=tr, va="center", fontsize=12, color="#333",
                    annotation_clip=False)
    n = ax.annotate(f"{v:+.0f}", (1, 0.5), xycoords=t, xytext=(3, 0), textcoords="offset points",
                    va="center", fontsize=17, color=stage_color(v), annotation_clip=False)
    ax.annotate(stage(v), (0, 0), xycoords=(t, n), xytext=(0, -1), textcoords="offset points", va="top",
                fontsize=min(12, 63 / len(stage(v))), color=stage_color(v), annotation_clip=False)


def header(ax, v):
    sw = DrawingArea(10, 10)
    sw.add_artist(Rectangle((0, 0), 10, 10, fc=shade(v), ec=stage_color(v), lw=1.0))
    box = HPacker(children=[TextArea("TurnLine 接近度　いま", textprops=dict(fontsize=10, color="#333")), sw,
                            TextArea(f"{v:+.0f}", textprops=dict(fontsize=13, color=stage_color(v))),
                            TextArea(stage(v), textprops=dict(fontsize=11, color=stage_color(v))),
                            DrawingArea(8, 1),
                            TextArea("↑天井が近い", textprops=dict(fontsize=9, color=RED_D)),
                            TextArea("↓底が近い", textprops=dict(fontsize=9, color=GRN_D))],
                  align="center", pad=0, sep=5)
    ab = AnchoredOffsetbox("upper left", child=box, pad=0.25, borderpad=0.2, frameon=True,
                           bbox_to_anchor=(0, 1), bbox_transform=ax.transAxes)
    ab.patch.set(fc="white", ec="none")
    ax.add_artist(ab)


def plan_f(d):
    x, s = d.x, d.s
    fig, ax_p, ax = make_two_pane(
        d, "案F　グラデーション・ヒストグラム",
        "1日1本の棒。天井が近いほど赤い棒が上へ、底が近いほど緑の棒が下へ、なだらかに伸びて濃くなる",
        height_ratios=(5, 4.2))
    for a in (ax_p, ax):
        p = a.get_position()
        a.set_position([p.x0, p.y0, RIGHT - p.x0, p.height])
    ax.set_ylim(*YLIM)
    ax.set_yticks([])
    bars(ax, x, s)
    marks(fig, ax, x, s)
    now(ax, x, s[-1])
    scale(fig, ax, s[-1])
    header(ax, s[-1])
    return fig


if __name__ == "__main__":
    fig = plan_f(load())
    fig.savefig(OUT / "TurnLine_subpane_hist.png")
    print("saved:", OUT / "TurnLine_subpane_hist.png")
