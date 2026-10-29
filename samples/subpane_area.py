"""TurnLine 表示案H：別ウィンドウの「なだらかな山と谷のバー」（サンプルB改良・見た目確認用・合成データ）

1日1本の棒で接近度を描き、棒の頂点を細い輪郭線でつないで途切れない山（赤・上＝天井が近い）と
谷（緑・下＝底が近い）に見せる。棒は高さ方向のグラデーション（0付近も薄く色付き、±100 に近いほど濃い）で、
±25/±50/±80 の白い段が「注意 → そろそろ → 圏」の境目。各脚で初めて ±50 に届いた棒に ● と
「そろそろ高値/安値」の札を付ける。右端の段階スケール（棒と同じ色と段）を ▶ が指し、その横に大きく「いま 値 段階」。

接近度スコアは既知の転換点から逆算した「理想形」であり、的中率は未検証。
"""
import numpy as np
from matplotlib.collections import LineCollection
from matplotlib.colors import LinearSegmentedColormap, to_rgb
from matplotlib.offsetbox import AnchoredOffsetbox, DrawingArea, HPacker, TextArea, VPacker
from matplotlib.patches import Rectangle
from matplotlib.path import Path as MPath
from matplotlib.transforms import blended_transform_factory

from turnline_common import (GRN, GRN_D, OUT, RED, RED_D, TH_CAUTION, TH_SOON, TH_ZONE, crossings,
                             load, make_two_pane, stage, stage_color)

BAR_W = 0.78
STEPS = [sg * t for sg in (1, -1) for t in (TH_CAUTION, TH_SOON, TH_ZONE)]
BANDS = ((TH_CAUTION, TH_SOON), (TH_SOON, TH_ZONE), (TH_ZONE, 100))
NAMES = {1: ("高値に\n注意", "そろそろ\n高値", "高値圏"), -1: ("安値に\n注意", "そろそろ\n安値", "安値圏")}


def tint(c, a):
    return np.array(to_rgb(c)) * a + (1 - a)


def ramp(c, c_d, a0, a1):
    """|接近度| 0→100 の色。中立も薄く色付き、注意→そろそろ→圏の順に濃くなる"""
    return LinearSegmentedColormap.from_list("", [(0, tint(c, a0)), (0.375, tint(c, a1)), (0.65, to_rgb(c)),
                                                  (0.9, to_rgb(c_d)), (1, to_rgb(c_d))])


RAMPS = (ramp(RED, RED_D, 0.24, 0.55), ramp(GRN, GRN_D, 0.2, 0.52))


def color_at(v):
    v = np.asarray(v, float)
    return np.where(v[..., None] >= 0, RAMPS[0](np.abs(v) / 100), RAMPS[1](np.abs(v) / 100))


def gradient(ax, extent):
    yy = np.linspace(-100, 100, 801)
    return ax.imshow(color_at(yy)[:, None], aspect="auto", origin="lower", interpolation="bilinear",
                     extent=extent, zorder=2)


def draw_bars(ax, x, s):
    rects = [Rectangle((i - BAR_W / 2, 0), BAR_W, v) for i, v in zip(x, s)]
    clip = MPath.make_compound_path(*[r.get_patch_transform().transform_path(r.get_path()) for r in rects])
    steps = ax.hlines(STEPS, x[0] - 1, x[-1] + 1, color="white", lw=1.0, zorder=3)
    for a in (gradient(ax, (x[0] - 1, x[-1] + 1, -100, 100)), steps):
        a.set_clip_path(clip, transform=ax.transData)
    ax.axhline(0, color="#999", lw=1.0, zorder=3.5)


def outline(x, s, turns):
    """棒の頂点を結ぶ線。転換バーの右端で垂直に 0 へ落とす（翌日へははみ出さない）"""
    xs, ys = list(map(float, x)), list(s)
    for t, _ in sorted(turns, reverse=True):
        if 0 < t < len(x) - 1:
            xs[t + 1:t + 1], ys[t + 1:t + 1] = [t + BAR_W / 2] * 2, [s[t], 0.0]
    k = np.linspace(0, len(xs) - 1, (len(xs) - 1) * 8 + 1)
    return np.interp(k, np.arange(len(xs)), xs), np.interp(k, np.arange(len(xs)), ys)


def draw_outline(ax, x, s, turns):
    """線の色はその日の棒と同じ（中立＝灰色）"""
    px, py = outline(x, s, turns)
    keep = np.abs(py[:-1]) + np.abs(py[1:]) > 0.1
    seg = np.stack([np.c_[px[:-1], py[:-1]], np.c_[px[1:], py[1:]]], axis=1)[keep]
    v = s[np.rint((px[:-1] + px[1:]) / 2).astype(int)][keep]
    cols = ["#9a9a9a" if abs(a) < TH_CAUTION else color_at(a) for a in v]
    ax.add_collection(LineCollection(seg, colors=cols, lw=1.0, capstyle="round", zorder=4))


def draw_soon(ax, x, s):
    for i in crossings(s):
        sg = 1 if s[i] > 0 else -1
        col, ec, fc = (RED_D, RED, tint(RED, 0.1)) if sg > 0 else (GRN_D, GRN, tint(GRN, 0.1))
        ax.plot(x[i], s[i], "o", ms=7, color=col, mec="white", mew=1.2, zorder=6)
        ax.annotate("そろそろ\n高値" if sg > 0 else "そろそろ\n安値", (x[i], s[i]), xytext=(-8, sg * 5),
                    textcoords="offset points", ha="right", va="center", ma="center", fontsize=9.5,
                    linespacing=1.15, color=col, zorder=6,
                    bbox=dict(boxstyle="round,pad=0.25", fc=fc, ec=ec, lw=1.0))


def draw_now(fig, ax, x, s):
    """最新の棒に ○、そこから右端の段階スケールへ点線と ▶"""
    v = s[-1]
    pt = 1 / (ax.get_position().width * fig.get_figwidth() * 72)
    tr = blended_transform_factory(ax.transAxes, ax.transData)
    ax.plot([x[-1], ax.get_xlim()[1]], [v] * 2, color="#555", lw=1.2, ls=(0, (1, 1.5)), zorder=5)
    ax.plot(x[-1], v, "o", ms=8, mfc="white", mec=stage_color(v), mew=1.6, zorder=6)
    ax.plot(1 - 1.5 * pt, v, ">", ms=9, color="#333", transform=tr, clip_on=False, zorder=7)


def draw_scale(fig, ax, v):
    """右端の段階スケール（棒と同じ色・同じ白い段）。いまの段階の名前の所に大きく「いま 値 段階」"""
    pt = 1 / (ax.get_position().width * fig.get_figwidth() * 72)
    tr = blended_transform_factory(ax.transAxes, ax.transData)
    cax = ax.inset_axes([1 + 3 * pt, -100, 8 * pt, 200], transform=tr)
    gradient(cax, (0, 1, -100, 100))
    cax.hlines(STEPS, 0, 1, color="white", lw=1.0)
    cax.axhline(v, color="#222", lw=2.0)
    cax.set(xlim=(0, 1), ylim=(-100, 100))
    cax.set_axis_off()
    k = sum(abs(v) >= t for t in (TH_CAUTION, TH_SOON, TH_ZONE))
    sv = 1 if v >= 0 else -1
    names = []
    for sg in (1, -1):
        for j, ((lo, hi), name) in enumerate(zip(BANDS, NAMES[sg]), 1):
            if (sg, j) != (sv, k):
                names.append(ax.annotate(name, (1, sg * (lo + hi) / 2), xycoords=tr, xytext=(13, 0),
                                         textcoords="offset points", va="center", fontsize=9.5, linespacing=1.05,
                                         color=RED_D if sg > 0 else GRN_D, annotation_clip=False))
        for t in (TH_CAUTION, TH_SOON, TH_ZONE):
            if abs(sg * t - v) > 6:
                ax.annotate(f"{sg * t:+d}", (1, sg * t), xycoords=tr, xytext=(-2, 0), textcoords="offset points",
                            ha="right", va="center", fontsize=7.5, color="#777")
    if k:
        names.append(ax.annotate("中立", (1, 0), xycoords=tr, xytext=(13, 0), textcoords="offset points",
                                 va="center", fontsize=9.5, color="#666", annotation_clip=False))
    col = stage_color(v)
    box = VPacker(children=[TextArea("いま", textprops=dict(fontsize=12, color="#333")),
                            TextArea(f"{v:+.0f}", textprops=dict(fontsize=16, color=col)),
                            TextArea(NAMES[sv][k - 1] if k else "中立",
                                     textprops=dict(fontsize=12, color=col, linespacing=1.05))],
                  align="left", pad=0, sep=2)
    # 中立は帯の中央、注意/そろそろは外側の境目から 0 側へ、圏は 80 から外側へ伸ばす（次の段階名を隠さない）
    if not k:
        loc, y = "center left", 0
    elif k == 3:
        loc, y = "lower left" if sv > 0 else "upper left", sv * TH_ZONE
    else:
        loc, y = "upper left" if sv > 0 else "lower left", sv * BANDS[k - 1][1]
    ab = AnchoredOffsetbox(loc, child=box, pad=0, borderpad=0, frameon=False,
                           bbox_to_anchor=(1 + 13 * pt, y), bbox_transform=tr)
    ax.add_artist(ab)
    fig.canvas.draw()
    rb = ab.get_window_extent()
    for t in names:  # 大きな「いま」と重なる段階名は隠す（現在値が狭い段階にあるとき）
        t.set_visible(not t.get_window_extent().overlaps(rb))


def header(ax, v):
    sw = DrawingArea(10, 10)
    sw.add_artist(Rectangle((0, 0), 10, 10, fc=color_at(v), ec=stage_color(v), lw=1.0))
    box = HPacker(children=[TextArea("TurnLine 接近度", textprops=dict(fontsize=10, color="#333")), sw,
                            TextArea(f"{v:+.0f}", textprops=dict(fontsize=12, color=stage_color(v))),
                            TextArea(stage(v), textprops=dict(fontsize=10, color=stage_color(v)))],
                  align="center", pad=0, sep=5)
    ab = AnchoredOffsetbox("upper left", child=box, pad=0.25, borderpad=0.2, frameon=True,
                           bbox_to_anchor=(0, 1), bbox_transform=ax.transAxes)
    ab.patch.set(fc="white", ec="none")
    ax.add_artist(ab)


if __name__ == "__main__":
    d = load()
    fig, ax_p, ax = make_two_pane(
        d, "案H　なだらかな山と谷のバー（サンプルB改良）",
        "1日1本の棒。赤い山（上）＝天井が近い／緑の谷（下）＝底が近い。高く濃くなるほど転換が近い",
        height_ratios=(5, 4.0))
    ax.set_autoscale_on(False)
    ax.set_ylim(-108, 126)
    ax.set_yticks([])
    draw_bars(ax, d.x, d.s)
    draw_outline(ax, d.x, d.s, d.turns)
    draw_soon(ax, d.x, d.s)
    draw_now(fig, ax, d.x, d.s)
    header(ax, d.s[-1])
    draw_scale(fig, ax, d.s[-1])
    fig.savefig(OUT / "TurnLine_subpane_area.png")
    print("saved:", OUT / "TurnLine_subpane_area.png")
