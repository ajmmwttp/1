"""10案のスマホ向け画像: python -m research.turn_zones.gallery

- results/E01_*.png … 各案1枚 (上: 価格, 下: 別ウィンドウ). TradingView での見た目を再現
- results/compare_all.png: 同じ期間で10案を縦に並べたもの
- results/similarity.png: 10案どうしの似ている度合い (線の相関・ゾーンの重なり)
"""
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.collections import LineCollection
from matplotlib.colors import to_rgb

from .data import load_all
from .helpers import zones
from .indicators import REGISTRY
from .validate import OUT, zigzag

plt.rcParams["font.family"] = "IPAGothic"
RED, ORG, GRY, LGRN, GRN = "#d32f2f", "#f57c00", "#9e9e9e", "#66bb6a", "#2e7d32"
UPC, DNC = "#26a69a", "#ef5350"
WIN = ("2018-01-01", "2018-12-31")
COOL = {"E9": 5}
NO_EXIT = {"E9"}
SFX = {"E3": ("(失速)", "(失速)"), "E4": ("(出来高)", "(出来高)"), "E5": ("(日柄)", "(日柄)"),
       "E6": ("(値幅)", "(値幅)"), "E7": ("(周期)", "(周期)"), "E8": ("(連続)", "(連続)"),
       "E9": ("(天井確認)", "(底確認)"), "E10": ("(慢心)", "(恐怖)")}
TAG = {"E1": "E1乖離", "E2": "E2勢い", "E3": "E3失速", "E4": "E4出来高", "E5": "E5日柄", "E6": "E6値幅",
       "E7": "E7周期", "E8": "E8連続", "E9": "E9足形", "E10": "E10ボラ"}


def _mix(a, b, f):
    a, b = np.array(to_rgb(a)), np.array(to_rgb(b))
    return tuple(a + (b - a) * min(max(f, 0.0), 1.0))


def level_color(v, u, l):
    """Pine と同じ色分け: ラインに近づくほどグレー→オレンジ(上)/薄緑(下)."""
    if np.isnan(v):
        return (0, 0, 0, 0)
    if v > u:
        return to_rgb(RED)
    if v < l:
        return to_rgb(GRN)
    if v >= 0:
        return _mix(GRY, ORG, (v - 0.3 * u) / (0.7 * u))
    return _mix(LGRN, GRY, (v - l) / (0.3 * l - l))


def candles(ax, df, piv):
    o, h, l, c = (df[k].to_numpy() for k in ("Open", "High", "Low", "Close"))
    for i in range(len(df)):
        col = UPC if c[i] >= o[i] else DNC
        ax.vlines(i, l[i], h[i], color=col, lw=0.7)
        ax.add_patch(plt.Rectangle((i - 0.35, min(o[i], c[i])), 0.7, max(abs(c[i] - o[i]), 1e-9), color=col, lw=0))
    for p, s in piv:
        if s == 1:
            ax.annotate("天井", (p, h[p]), xytext=(0, 6), textcoords="offset points", ha="center", fontsize=7, color=RED)
        else:
            ax.annotate("底", (p, l[p]), xytext=(0, -12), textcoords="offset points", ha="center", fontsize=7, color=GRN)
    ax.set_xlim(-2, len(df) + 1)
    ax.margins(y=0.1)
    ax.yaxis.tick_right()
    ax.grid(alpha=0.2)


def month_ticks(ax, idx):
    t = [i for i in range(1, len(idx)) if idx[i].month != idx[i - 1].month]
    ax.set_xticks(t, [f"{idx[i].month}月" for i in t], fontsize=8)


def pane(ax, key, line, U, L, st, ev, labels=True, status=True, small=False):
    n = len(line)
    x = np.arange(n)
    ax.fill_between(x, U, 100, color=RED, alpha=0.06, lw=0, step="mid")
    ax.fill_between(x, -100, L, color=GRN, alpha=0.06, lw=0, step="mid")
    ax.plot(x, U, color=RED, lw=0.9)
    ax.plot(x, L, color=GRN, lw=0.9)
    ax.axhline(0, color=GRY, lw=0.6, ls=":")
    ok = ~np.isnan(line)
    ax.fill_between(x, line, U, where=ok & (line > U), color=RED, alpha=0.38, lw=0, interpolate=True)
    ax.fill_between(x, line, L, where=ok & (line < L), color=GRN, alpha=0.38, lw=0, interpolate=True)
    pts = np.column_stack([x, line])
    segs = np.stack([pts[:-1], pts[1:]], axis=1)
    cols = [level_color(line[i + 1], U[i + 1], L[i + 1]) for i in range(n - 1)]
    ax.add_collection(LineCollection(segs, colors=cols, linewidths=1.3 if small else 2.0))
    ax.set_ylim(-108, 108)
    ax.set_xlim(-2, n + 1)
    ax.yaxis.tick_right()
    ax.set_yticks([-100, 0, 100])
    ax.tick_params(labelsize=7)
    if labels:
        # Pine と同じく同じ側のラベルは cool 本空ける. 画像では文字が重ならないよう近いラベルを段違いにする
        cool = COOL.get(key, 3)
        last = {1: -99, -1: -99}
        prev_x = {1: -99, -1: -99}
        lvl = {1: 0, -1: 0}
        lbld = {1: True, -1: True}   # 間隔で突入ラベルを省いたゾーンは離脱の印も出さない (Pine と同じ)
        fs = 6 if small else 6.8
        gap = 22 if small else 16
        for t in range(n):
            if not small and key not in NO_EXIT:
                if ev["topOut"][t] and lbld[1]:
                    ax.plot(t, U[t], marker="v", ms=3, color=RED, alpha=0.6)
                if ev["botOut"][t] and lbld[-1]:
                    ax.plot(t, L[t], marker="^", ms=3, color=GRN, alpha=0.6)
            for side, k_in, col in ((1, "topIn", RED), (-1, "botIn", GRN)):
                if ev[k_in][t]:
                    lbld[side] = t - last[side] > cool
                if ev[k_in][t] and lbld[side]:
                    lvl[side] = (lvl[side] + 1) % 3 if t - prev_x[side] < gap else 0
                    # ラベルはライン上に付け, 本体は中立側 (上ラインの下 / 下ラインの上) に出す → 画面外に切れない
                    off = -side * (6 + 11 * lvl[side])
                    ax.annotate("高値圏突入" if side == 1 else "安値圏突入", (t, U[t] if side == 1 else L[t]),
                                xytext=(0, off), textcoords="offset points", ha="center",
                                va="top" if side == 1 else "bottom",
                                fontsize=fs, color="white", bbox=dict(boxstyle="round,pad=0.18", fc=col, ec="none"),
                                arrowprops=dict(arrowstyle="-", color=col, lw=0.5) if lvl[side] else None)
                    last[side] = prev_x[side] = t
    if status:
        z, v, u, l = st[-1], line[-1], U[-1], L[-1]
        zb = 0
        for s in st[::-1]:
            if s != z or z == 0:
                break
            zb += 1
        if z == 1:
            txt = f"高値圏 {zb}本目 / 上ライン超え +{v - u:.0f}"
        elif z == -1:
            txt = f"安値圏 {zb}本目 / 下ライン超え {v - l:.0f}"
        elif v >= 0.75 * u:
            txt = f"上ライン接近 / 上ラインまで {u - v:.0f}"
        elif v <= 0.75 * l:
            txt = f"下ライン接近 / 下ラインまで {v - l:.0f}"
        else:
            txt = f"中立 / {'上ラインまで ' + format(u - v, '.0f') if v >= 0 else '下ラインまで ' + format(v - l, '.0f')}"
        col = RED if z == 1 else GRN if z == -1 else "#333333"
        ax.text(0.99, 0.97, f"【{TAG[key]}】状態: {txt}", transform=ax.transAxes, ha="right", va="top",
                fontsize=6 if small else 7.5, color=col, bbox=dict(fc="white", ec="#dddddd", alpha=0.85, pad=2))


def metrics_text(met, key):
    m = met[(met.ds == "NQ3x") & (met.key == key)].set_index("side")
    t, b = m.loc["top"], m.loc["bot"]
    win = "comb" if key in ("E3", "E9") else "lead"
    wtxt = "5本前〜3本後" if win == "comb" else "5本前〜当日"
    return (f"NASDAQ×3合成 1999-2018 の成績（15%以上の波, {wtxt}にゾーン内だった割合）\n"
            f"天井 {t[f'hit_{win}']:.0f}%（偶然の{t[f'lift_{win}']:.1f}倍）  底 {b[f'hit_{win}']:.0f}%（偶然の{b[f'lift_{win}']:.1f}倍）"
            f"  ゾーン滞在 {t.zone_share + b.zone_share:.0f}%  突入 年{t.entries_per_year:.0f}回/{b.entries_per_year:.0f}回")


def compute(df, key):
    out = REGISTRY[key]["fn"](df)
    st, ev = zones(out["line"], out["U"], out["L"])
    return out["line"], out["U"], out["L"], st, ev


def window(df, arrs):
    m = (df.index >= WIN[0]) & (df.index <= WIN[1])
    i0, i1 = np.where(m)[0][[0, -1]]
    return slice(i0, i1 + 1)


def main():
    data = load_all()
    df = data["NQ3x"]
    met = pd.read_csv(os.path.join(OUT, "metrics.csv"))
    sl = window(df, None)
    w = df.iloc[sl].copy()
    scale = 100 / w["Close"].iloc[0]
    for k in ("Open", "High", "Low", "Close"):
        w[k] = w[k] * scale
    piv_all = zigzag(df["Close"].to_numpy(), 0.15)
    piv = [(p - sl.start, s) for p, s in piv_all if sl.start <= p < sl.stop]
    res = {k: compute(df, k) for k in REGISTRY}

    for i, (key, info) in enumerate(REGISTRY.items(), 1):
        line, U, L, st, ev = (a[sl] if isinstance(a, np.ndarray) else {kk: vv[sl] for kk, vv in a.items()} for a in res[key])
        fig = plt.figure(figsize=(7.2, 10.2))
        gs = fig.add_gridspec(3, 1, height_ratios=[1.55, 1.15, 0.13], hspace=0.06, left=0.03, right=0.9, top=0.91, bottom=0.04)
        ax1, ax2 = fig.add_subplot(gs[0]), fig.add_subplot(gs[1])
        candles(ax1, w, piv)
        ax1.set_xticks([])
        ax1.text(0.01, 0.98, "価格: NASDAQ×3合成（TQQQ相当, 2018年初=100）", transform=ax1.transAxes, fontsize=7.5,
                 va="top", color="#555555")
        pane(ax2, key, line, U, L, st, ev)
        month_ticks(ax2, w.index)
        fig.suptitle(f"{key}  {info['name']}", x=0.03, ha="left", fontsize=15, y=0.985)
        fig.text(0.03, 0.935, f"要素: {info['element']}　種類: {info['kind']}　ライン: {U[-1]:+.0f} / {L[-1]:+.0f}"
                 + ("（自動調整）" if key == "E2" else ""), fontsize=9.5, color="#333333")
        fig.text(0.03, 0.012, metrics_text(met, key), fontsize=7.2, color="#333333")
        st_t, sb = SFX.get(key, ("", ""))
        ax2.text(0.01, 0.03, "ラベル: 高値圏突入" + st_t + " / 安値圏突入" + sb
                 + ("" if key in NO_EXIT else "　小さな▼▲ = 離脱"), transform=ax2.transAxes, fontsize=6.5, color="#666666")
        fig.savefig(os.path.join(OUT, f"{info['pine'].replace('.pine', '')}.png"), dpi=150)
        plt.close(fig)

    # 比較図: 価格 + 10ウィンドウ
    fig = plt.figure(figsize=(7.2, 25))
    gs = fig.add_gridspec(11, 1, height_ratios=[2.2] + [1] * 10, hspace=0.12, left=0.03, right=0.88, top=0.975, bottom=0.015)
    ax = fig.add_subplot(gs[0])
    candles(ax, w, piv)
    ax.set_xticks([])
    fig.suptitle("10案の比較（同じ期間・同じ目盛り）", x=0.03, ha="left", fontsize=15, y=0.995)
    for j, key in enumerate(REGISTRY, 1):
        line, U, L, st, ev = (a[sl] if isinstance(a, np.ndarray) else {kk: vv[sl] for kk, vv in a.items()} for a in res[key])
        a2 = fig.add_subplot(gs[j], sharex=ax)
        pane(a2, key, line, U, L, st, ev, labels=True, status=False, small=True)
        a2.text(0.005, 0.96, f"{key} {REGISTRY[key]['name']}（{REGISTRY[key]['element']}）", transform=a2.transAxes,
                fontsize=8, va="top", bbox=dict(fc="white", ec="none", alpha=0.8, pad=1))
        for p, s in piv:
            a2.axvline(p, color=RED if s == 1 else GRN, lw=0.6, alpha=0.35)
        if j < 10:
            a2.tick_params(labelbottom=False)
        else:
            month_ticks(a2, w.index)
    fig.savefig(os.path.join(OUT, "compare_all.png"), dpi=120)
    plt.close(fig)

    # 似ている度合い
    dist = pd.read_csv(os.path.join(OUT, "distinctness.csv"))
    keys = list(REGISTRY)
    M = pd.DataFrame(np.eye(10), index=keys, columns=keys)
    J = pd.DataFrame(np.eye(10), index=keys, columns=keys)
    for (a, b), g in dist.groupby(["a", "b"]):
        M.loc[a, b] = M.loc[b, a] = g.r_level.abs().max()
        J.loc[a, b] = J.loc[b, a] = g.jaccard.max()
    fig, axs = plt.subplots(2, 1, figsize=(7.2, 12.5))
    for ax, mat, title, lim in ((axs[0], M, "線どうしの相関（3データの最大値, 上限0.80）", 0.8),
                                (axs[1], J, "ゾーンの重なり Jaccard（3データの最大値, 上限0.30）", 0.3)):
        im = ax.imshow(mat.values, cmap="Reds", vmin=0, vmax=1 if lim > 0.5 else 0.5)
        ax.set_xticks(range(10), keys, fontsize=8)
        ax.set_yticks(range(10), [f"{k} {REGISTRY[k]['element']}" for k in keys], fontsize=8)
        for r in range(10):
            for c_ in range(10):
                if r != c_:
                    v = mat.values[r, c_]
                    ax.text(c_, r, f"{v:.2f}", ha="center", va="center", fontsize=6.5,
                            color="white" if v > (0.6 if lim > 0.5 else 0.25) else "black",
                            weight="bold" if v > lim * 0.9 else None)
        ax.set_title(title, fontsize=11, loc="left")
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, "similarity.png"), dpi=130)
    plt.close(fig)
    print("saved images to", OUT)


if __name__ == "__main__":
    main()
