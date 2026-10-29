"""TurnLine 実データでの見え方（理想形との違い・改良版 案F'・的中率の比較）

- fig_ideal_vs_real.png      同じ期間で、サンプルと同じ「理想形」と実際の指標 TL-Classic3 を並べる
- fig_planF_prime_2018/2015  改良版 案F'（底側が主役。上向きの棒は「過熱」として控えめに）を実データの2期間で
- fig_planF_prime_2020/2022  同じ案F' を、空振りが多かった期間（コロナ急落・2022年の下落、終値だけのデータ）で
- fig_scorecard.png          「そろそろ」点灯の的中率: 理想形 / TL-Classic3 / 偽の価格（鏡映帰無の中央値）
- fig_summary.png            答えのページ（PDF の1枚目）
- TurnLine_verification.pdf  上の7枚をまとめた PDF（答え → 的中率 → 空振りの多い期間 → 当たりの多い期間 → 理想形との違い）

点灯・答え合わせ・確定バー・何本前などはすべて turnline_lab の関数から計算する（的中率の表 HITS だけは検証結果をそのまま使う）。
未来の情報を使うのは 理想形・答え合わせ ○/×・後から分かる ▼/▲ の3つだけで、図の中にそう書く。
python3 realdata_view.py
"""
import sys
from pathlib import Path
from types import SimpleNamespace

import matplotlib.pyplot as plt
import numpy as np
from matplotlib import font_manager
from matplotlib.offsetbox import AnchoredOffsetbox, DrawingArea, HPacker, TextArea, VPacker
from matplotlib.patches import Polygon, Rectangle
from matplotlib.transforms import blended_transform_factory
from PIL import Image

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE.parent / "samples"))
import subpane_hist as F  # noqa: E402
import turnline_lab as L  # noqa: E402
from cand_classic import score2  # noqa: E402
from turnline_common import (GRN, GRN_D, RED_D, TH_CAUTION, TH_SOON, draw_candles, make_two_pane,  # noqa: E402
                             setup_price_axes, style_axes)

if plt.rcParams["font.family"] == ["IPAGothic"] and any(f.name == "IPAPGothic" for f in font_manager.fontManager.ttflist):
    plt.rcParams["font.family"] = "IPAPGothic"  # 同じ書体のプロポーショナル版（数字の 0 に斜線が入らない）

OUT = HERE / "out"
OUT.mkdir(exist_ok=True)
WINDOWS = {"2018": ("nasdaq3x", "2018-06-01", "2018-12-31"), "2015": ("nasdaq3x", "2015-06-01", "2016-03-31"),
           "2020": ("sp3x_close", "2020-01-02", "2020-10-30"), "2022": ("sp3x_close", "2022-01-03", "2022-12-28")}
# データごとの 価格欄の見出し / 注記での呼び方
SOURCE = {"nasdaq3x": ("NASDAQ×3 近似・日足", "NASDAQ総合の日足を3倍した近似"),
          "sp3x_close": ("S&P500×3 近似・終値だけ", "S&P500の終値を3倍した近似。高値・安値のないデータ")}
K = L.K_BARS

# 的中率（点灯後 K 本以内に同じ側の転換点）: 期間, データ, side -> (TL-Classic3, 偽の価格の中央値, 理想形)。検証結果の表をそのまま
HITS = [("2011-18", "NASDAQ×3", {"top": (0.31, 0.44, 0.59), "bot": (0.88, 0.57, 0.90)}),
        ("2011-18", "S&P500×3", {"top": (0.21, 0.41, 0.58), "bot": (0.86, 0.53, 0.84)}),
        ("2019-22", "S&P500×3・終値", {"top": (0.26, 0.37, 0.33), "bot": (0.50, 0.50, 0.83)}),
        ("1991-98", "S&P500×3・終値", {"top": (0.27, 0.30, 0.50), "bot": (0.74, 0.50, 0.65)})]
# 底側の偶然の水準をもう一つ: 「下げると荒れる」性質を残した偽の価格（GARCH 帰無の中央値。results/garch_null.txt）
GARCH_FAKE_BOT = {"2011-18 NASDAQ×3": 0.69, "2011-18 S&P500×3": 0.68, "2019-22": 0.59, "1991-98": 0.56}
# 上の各行のデータと期間（何本前・残りの値動きを L.evaluate で計算する）
EVAL = [("nasdaq3x", ("2011-01-01", "2018-12-31")), ("sp3x", ("2011-01-01", "2018-12-31")),
        ("sp3x_close", ("2019-01-01", "2022-12-28")), ("sp3x_close", ("1991-01-01", "1998-12-31"))]

def note_real(src="nasdaq3x"):
    return f"※ 実データ（{SOURCE[src][1]}。TQQQ 本体ではない）。指標は TL-Classic3（その日の終値までの情報だけで計算）"
TOP_MUTED = ("#ebe6e1", "#e5d9cd", "#e0c6ab", "#d9ad86")  # 案F' の上向きの棒（過熱）: 中立 / 25 / 50 / 80
MUTED_INK = "#8a6e55"
INK, INK2, INK3 = "#333", "#555", "#888"


# ---------------------------------------------------------------- データ
def load_windows():
    """各データを全期間で計算してから、表示期間を切り出す（ウォームアップ込み）。
    long（確定の遅れ・棒の変化の目安）はどの図でも 2011〜18年の nasdaq3x の値"""
    data = {}
    for src in dict.fromkeys(v[0] for v in WINDOWS.values()):
        df = L.load(src)
        piv = L.pivots(df)
        data[src] = (df, piv, score2(df), L.ideal(df, piv), L.targets(piv, len(df)))
    df, piv, sc, idl, _ = data["nasdaq3x"]
    test = L.period_mask(df, EVAL[0][1])
    ls = L.leg_stats(df, piv, test)
    move = [np.abs(np.diff(s[test])).mean() for s in (idl.top - idl.bot, signed(sc.top, sc.bot))]
    lag = {k: ls[k]["confirm_lag_med"] for k in "HL"}
    lag_by_src = {"nasdaq3x": ("2011〜18年", lag)}  # 確定までの待ちの目安（同じデータの長い期間の中央値）
    if "sp3x_close" in data:
        d2, p2 = data["sp3x_close"][:2]
        ls2 = L.leg_stats(d2, p2, L.period_mask(d2, EVAL[2][1]))
        lag_by_src["sp3x_close"] = ("2019〜22年全体", {k: ls2[k]["confirm_lag_med"] for k in "HL"})
    long = SimpleNamespace(lag=lag, move=move, lag_by_src=lag_by_src)
    out = {}
    for key, (src, a, b) in WINDOWS.items():
        df, piv, sc, idl, tg = data[src]
        i0, i1 = np.flatnonzero(L.period_mask(df, (a, b)))[[0, -1]]
        sl = slice(i0, i1 + 1)
        p = piv[(piv.bar >= i0) & (piv.bar <= i1)]
        sig = {}
        for name, s in (("real", sc), ("ideal", idl)):
            for side in ("top", "bot"):
                c = L.crossings_up(s[side].to_numpy(float), TH_SOON, L.RESET)  # 全期間で数えて期間内だけ使う
                sig[name, side] = c[(c >= i0) & (c <= i1)] - i0
        out[key] = SimpleNamespace(
            key=key, src=src, a=a, b=b, df=df.iloc[sl], x=np.arange(i1 - i0 + 1), turns=[], long=long,
            pb=p.bar.to_numpy() - i0, pk=p.kind.to_numpy(), pc=p.confirm.to_numpy() - i0,
            top=sc.top.to_numpy()[sl], bot=sc.bot.to_numpy()[sl], itop=idl.top.to_numpy()[sl],
            ibot=idl.bot.to_numpy()[sl], sig=sig, hit={s: tg[f"{s}_{K}"][sl] for s in ("top", "bot")})
    return out


def eval_rows():
    """HITS の各行で TL-Classic3 を L.evaluate（何本前・残りの値動き・表との照合用の的中率）。
    あわせて底側の点灯1回ごとの「次の底までの追加の下げ」（中央値%, 10%以上の割合%）"""
    cache, out, drops = {}, [], []
    for name, per in EVAL:
        if name not in cache:
            df = L.load(name)
            cache[name] = (df, L.pivots(df), score2(df))
        df, piv, sc = cache[name]
        m = L.period_mask(df, per)
        out.append(L.evaluate(sc, df, piv, m))
        sig = L.crossings_up(sc.bot.to_numpy(float), TH_SOON, L.RESET)
        sig = sig[m[sig]]
        pb, pk, lo, c = piv.bar.to_numpy(), piv.kind.to_numpy(), df.l.to_numpy(), df.c.to_numpy()
        d = [1 - lo[pb[j[0]]] / c[s] for s in sig if len(j := np.flatnonzero((pk == "L") & (pb >= s)))]
        drops.append((100 * float(np.median(d)), 100 * float(np.mean(np.array(d) >= 0.10))))
    return out, drops


def signed(top, bot):
    """1日1本の棒: 大きい側を符号付きで（上=天井側 +、下=底側 -）。両側が同時に 5 を超える日はほぼない"""
    return np.where(top >= bot, top, -bot)


def judge(w, side, i):
    v = w.hit[side][i]
    return "？" if np.isnan(v) else "○" if v else "×"


def tally(w, name, side):
    js = [judge(w, side, i) for i in w.sig[name, side]]
    return len(js), js.count("○"), js.count("×")


def lags(w, kind):
    return w.pc[w.pk == kind] - w.pb[w.pk == kind]


def memo(w):
    """この期間の底側の点灯の答え合わせ、点灯から次の底（後から分かる）までの追加の下げ（最大）、
    最初の点灯から期間内の最安値までの下げ"""
    n, o, x = tally(w, "real", "bot")
    sig = w.sig["real", "bot"]
    drops = []
    for i in sig:
        j = np.flatnonzero((w.pk == "L") & (w.pb >= i))
        if len(j):
            drops.append(w.df.l.iat[w.pb[j[0]]] / w.df.c.iat[i] - 1)
    s = f"この期間: 点灯{n}回（○{o} ×{x}）"
    if drops and min(drops) < 0:
        s += f"・次の底までさらに最大{abs(min(drops)):.0%}"
    if len(sig):
        s += f"・最初の点灯から期間の最安値まで{w.df.l.iloc[sig[0]:].min() / w.df.c.iat[sig[0]] - 1:.0%}"
    return s


def wari(p):
    return f"約{round(p * 10)}割"


def wari_span(ps):
    lo, hi = round(min(ps) * 10), round(max(ps) * 10)
    return f"{lo}割" if lo == hi else f"{lo}〜{hi}割"


VERDICTS = ("偶然より上", "偶然よりやや上", "偶然と同じ", "偶然より下")


def verdict(real, fake):
    """的中率の本物と偽の価格の差から: +10pt 以上 / +5pt 以上 / ±5pt 未満 / -5pt 以下"""
    d = real - fake
    return VERDICTS[0 if d >= 0.10 else 1 if d >= 0.05 else 2 if d > -0.05 else 3]


def span(vals, unit):
    lo, hi = min(vals), max(vals)
    return f"{lo:.0f}{unit}" if round(lo) == round(hi) else f"{lo:.0f}〜{hi:.0f}{unit}"


def period_jp(w):
    a, b = w.df.index[0], w.df.index[-1]
    return f"{a.year}年{a.month}〜{b.month}月" if a.year == b.year else f"{a.year}年{a.month}月〜{b.year}年{b.month}月"


# ---------------------------------------------------------------- 描画部品
def text_pt(fig, s, size):
    t = fig.text(0, 0, s, fontsize=size)
    wpt = t.get_window_extent(fig.canvas.get_renderer()).width * 72 / fig.dpi
    t.remove()
    return wpt


def place(axes, top, ratios, gaps, bottom, right=F.RIGHT, left=0.04):
    """縦に並んだ軸の位置を決め直す（gaps は軸と軸の間、図の高さに対する比）"""
    h = (top - bottom - sum(gaps)) / sum(ratios)
    y = top
    for a, r, g in zip(axes, ratios, list(gaps) + [0]):
        a.set_position([left, y - r * h, right - left, r * h])
        y -= r * h + g


def lines(fig, x, y, rows, size=7.5, color=INK3, step=1.5):
    """複数行の注記（y は1行目のベースライン、図の高さ比）"""
    dy = size * step / (fig.get_figheight() * 72)
    for k, s in enumerate(rows):
        fig.text(x, y - k * dy, s, fontsize=size, color=color)


def turn_marks(fig, ax, w, confirm):
    """転換点に小さな ▼/▲（後から分かる位置）。confirm=True なら確定バーに「確定」札を置き、転換点から点線でつなぐ。
    札は 点の右 → 点の上（底は下）の順に、ローソク足・印・ほかの札と重ならない所へ（だめなら値動きから離す）"""
    px, py = F.per_pt(fig, ax)
    x0, x1 = ax.get_xlim()
    bpt = (x1 - x0) * px
    tw, th = text_pt(fig, "確定", 7.5) + 3.3, 11.5  # 札の幅・高さ（pt）
    hi, lo = w.df.h.to_numpy(), w.df.l.to_numpy()
    marks, held = [], []
    uw = text_pt(fig, "未確定", 7.5) * bpt
    for b, k, c in zip(w.pb, w.pk, w.pc):
        up = k == "H"
        y = (hi[b] + 5 * py) if up else (lo[b] - 5 * py)
        marks.append((w.x[b], y, up))
        col = RED_D if up else GRN_D
        pending = confirm and c >= len(w.x)  # 画面の最後の日にはまだ確定していない
        ax.plot(w.x[b], y, "v" if up else "^", ms=4.5, color=col, mfc="white" if pending else col,
                mec=col if pending else "white", mew=0.8 if pending else 0.6, zorder=7)
        if pending:  # 印の外側（天井は上・底は下）に小さく。札の置き場所探しでは障害物として扱う
            yt = y + (4 if up else -4) * py
            ax.text(w.x[b], yt, "未確定", ha="right", va="bottom" if up else "top", fontsize=7.5, color=col, zorder=7)
            held.append((w.x[b] - uw, w.x[b], yt, yt + 10 * py) if up else (w.x[b] - uw, w.x[b], yt - 10 * py, yt))
    if not confirm:
        return
    boxes = [(x - 3 * bpt, x + 3 * bpt, y - 3 * py, y + 3 * py) for x, y, _ in marks] + held

    def free(bx):
        xa, xb, ya, yb = bx
        if xa < x0 + 0.3 or xb > x1 - 0.3:
            return False
        j = np.arange(max(int(np.floor(xa - 0.5)), 0), min(int(np.ceil(xb + 0.5)), len(hi) - 1) + 1)
        if ((hi[j] + py >= ya) & (lo[j] - py <= yb)).any():
            return False
        return not any(xa < c and xb > a and ya < d and yb > cc for a, c, cc, d in boxes)

    for (xp, y, up), c in zip(marks, w.pc):
        if c >= len(w.x):
            continue
        sg, col = (1, RED_D) if up else (-1, GRN_D)
        xc = w.x[c]
        if c > xp:
            ax.plot([xp, xc], [y, y], color=col, lw=0.9, ls=(0, (1, 1.4)), zorder=6)
            ax.plot(xc, y, "o", ms=2.6, color=col, zorder=7)
        right = lambda yy: (xc + 4 * bpt, xc + (4 + tw) * bpt, yy - th / 2 * py, yy + th / 2 * py)
        above = (xc - tw / 2 * bpt, xc + tw / 2 * bpt) + ((y + 4 * py, y + (4 + th) * py) if up else
                                                         (y - (4 + th) * py, y - 4 * py))
        for bx in (right(y), above):
            if free(bx):
                break
        else:
            yy = y
            for _ in range(60):  # 値動きから離れる向きへ少しずつ
                yy += sg * 2 * py
                bx = right(yy)
                if free(bx):
                    break
            ax.plot([xc, xc], [y, yy], color=col, lw=0.9, ls=(0, (1, 1.4)), zorder=6)
        boxes.append(bx)
        ax.text((bx[0] + bx[1]) / 2, (bx[2] + bx[3]) / 2, "確定", ha="center", va="center", fontsize=7.5,
                color="white", zorder=8, bbox=dict(boxstyle="round,pad=0.22", fc=col, ec="none"))


def guides(ax, w):
    """転換点の日（後から分かる）に薄い縦線"""
    for b, k in zip(w.pb, w.pk):
        ax.axvline(w.x[b], color="#f4cfcd" if k == "H" else "#cde8d8", lw=0.9, zorder=0)


def panel_header(ax, rows):
    """軸の左上に白地の見出し。rows = [[(文字, 大きさ, 色) または DrawingArea, ...], ...]"""
    box = VPacker(children=[HPacker(children=[TextArea(c[0], textprops=dict(fontsize=c[1], color=c[2]))
                                              if isinstance(c, tuple) else c for c in r],
                                    align="center", pad=0, sep=5) for r in rows], align="left", pad=0, sep=4)
    ab = AnchoredOffsetbox("upper left", child=box, pad=0.25, borderpad=0.2, frameon=True,
                           bbox_to_anchor=(0, 1), bbox_transform=ax.transAxes)
    ab.patch.set(fc="white", ec="none")
    ax.add_artist(ab)


def dot(ax, x, y, c, ms=5.5):
    ax.plot(x, y, "o", ms=ms, color=c, mec="white", mew=1.0, zorder=6)


def glyph(ax, x, y, s, c):
    """答え合わせの ○/×（白地つき。縦線が透けない）"""
    ax.text(x, y, s, ha="center", va="center", fontsize=8.5, color=c, zorder=7,
            bbox=dict(boxstyle="circle,pad=0.02", fc="white", ec="none"))


def month_ticks(ax, w):
    """1月の目盛りに年を添える"""
    pos = ax.get_xticks()
    labs = [t.get_text() for t in ax.get_xticklabels()]
    ax.set_xticks(pos, [f"{w.df.index[int(p)].year}年1月" if s == "1月" else s for p, s in zip(pos, labs)])


# ---------------------------------------------------------------- 1. 理想形と実際の指標
LANE1 = 114


def fig_ideal_vs_real(w):
    fig = plt.figure(figsize=(7.2, 12.2), dpi=200)
    axes = [fig.add_subplot(3, 1, 1)]
    axes += [fig.add_subplot(3, 1, k, sharex=axes[0]) for k in (2, 3)]
    ax_p, ax_i, ax_r = axes
    place(axes, 0.912, (4.0, 3.6, 3.6), (0.012, 0.012), 0.083, right=0.88)
    fig.text(0.04, 0.975, "理想形（サンプル）と実際の指標の違い", fontsize=14)
    lines(fig, 0.04, 0.953, [f"NASDAQ×3 近似の日足・{period_jp(w)}。中段＝サンプル画像と同じ作り方の「理想形」、",
                             f"下段＝実際に計算できる TL-Classic3。どちらも {TH_SOON} に届いた日（そろそろ）に ● を付けた"],
          size=9, color=INK2)
    lo, hi = w.df.l.min(), w.df.h.max()
    setup_price_axes(ax_p, w.df, (lo - 0.10 * (hi - lo), hi + 0.12 * (hi - lo)), months=False,
                     label="NASDAQ×3 近似・日足（実データ）　▼▲＝天井/底（後から分かる位置）")
    draw_candles(ax_p, w.df, w.x, min_body=0.003 * (hi - lo))
    turn_marks(fig, ax_p, w, confirm=False)

    for ax, name in ((ax_i, "ideal"), (ax_r, "real")):
        style_axes(ax, w.df, months=ax is ax_r)
        ax.set_ylim(-128, 178)
        ax.set_yticks([-100, -50, 0, 50, 100], ["100", "50", "0", "50", "100"])
        ax.tick_params(axis="y", labelsize=8, colors="#999")
        guides(ax, w)
        src = {"top": w.itop, "bot": w.ibot} if name == "ideal" else {"top": w.top, "bot": w.bot}
        F.bars(ax, w.x, src["top"] - src["bot"] if name == "ideal" else signed(w.top, w.bot))
        _, py = F.per_pt(fig, ax)
        for side, sg, c in (("top", 1, RED_D), ("bot", -1, GRN_D)):
            for i in w.sig[name, side]:
                v = sg * src[side][i]
                if name == "real":
                    ax.plot([w.x[i]] * 2, [v, sg * (LANE1 - 6 * py)], color=c, lw=0.9, zorder=5)
                    glyph(ax, w.x[i], sg * LANE1, judge(w, side, i), c)
                dot(ax, w.x[i], v, c)
    month_ticks(ax_r, w)

    nt, nb = len(w.sig["ideal", "top"]), len(w.sig["ideal", "bot"])
    panel_header(ax_i, [[("理想形（サンプルと同じ作り方）", 10, INK), ("↑天井が近い", 8.5, RED_D), ("↓底が近い", 8.5, GRN_D)],
                        [(f"未来の転換点から逆算するので、長い山・谷ほど手前でなだらかに {TH_SOON} を超える（● 天井側{nt}回・底側{nb}回）",
                          8, INK2)]])
    (rt, ot, xt), (rb, ob, xb) = tally(w, "real", "top"), tally(w, "real", "bot")
    top, bot = HITS[0][2]["top"], HITS[0][2]["bot"]
    rows = [[("TL-Classic3（実際の指標・その日までの情報だけ）", 10, INK)],
            [(f"● 天井側{rt}回（○{ot} ×{xt}）・底側{rb}回（○{ob} ×{xb}）　"
              f"○＝{K}本以内に同じ側の転換点が来た　×＝空振り", 8, INK2)]]
    if rt and ot / rt > top[0] + 0.15:  # 表示期間がたまたま当たった方なら、そう書く
        rows.append([(f"※ 天井側はこの期間がたまたま当たった方。2011〜18年の全体では {top[0]:.0%}（偽の価格でも {top[1]:.0%}）",
                      8, RED_D)])
    panel_header(ax_r, rows)
    mi, mr = w.long.move
    lines(fig, 0.04, 0.042, [
        f"※ 2011〜18年の全体では、的中率 天井側 {top[0]:.0%}（偽の価格でも {top[1]:.0%}）・底側 {bot[0]:.0%}（偽の価格 {bot[1]:.0%}）。"
        f"棒の長さの日々の変化は理想形の約{mr / mi:.1f}倍（天井・底をまとめた棒、2011〜18年 NASDAQ×3）。",
        note_real() + "。",
        "※ 未来の情報を使っているのは 理想形・○×（答え合わせ）・▼▲と縦の細線（後から分かる天井/底）だけ。"])
    return fig


# ---------------------------------------------------------------- 2. 改良版 案F'（底側が主役）
STAGES_BOT = ("中立", "安値に注意", "底が近いかも", "急落中")  # 80 以上の段が確かとは言えないので「急落中」
TAG = "底が近いかも"
GLY, LANE = -110, -127  # ○/× の段・札の段
YLIM_P = (-140, 150)


def tier(v):
    return sum(abs(v) >= t for t in F.THS)


def shade_p(v):
    return (TOP_MUTED if v >= 0 else F.SHADES[-1])[tier(v)]


def stage_bot(b):
    return STAGES_BOT[tier(b)]


def ink_bot(b):
    return GRN_D if b >= TH_CAUTION else INK2


def bars_p(ax, x, s):
    ax.bar(x, s, width=F.BAR_W, color=[shade_p(v) for v in s], linewidth=0, zorder=2)
    for t in F.THS:
        m = np.abs(s) > t + 2
        ax.hlines(np.sign(s[m]) * t, x[m] - F.BAR_W / 2, x[m] + F.BAR_W / 2, color="white", lw=1.0, zorder=3)
    ax.axhline(-TH_SOON, color=GRN, lw=1.0, ls=(0, (4, 3)), alpha=0.45, zorder=1)
    ax.axhline(0, color="#999", lw=1.0, zorder=3)


def spread(want, step, lo, hi):
    """1次元の札の配置: 希望位置 want（昇順）に間隔 step 以上で並べる（ずれの二乗和が最小。重なる札は塊で動かす）"""
    blocks = []  # [先頭の番号, 個数, 先頭の位置]
    for k in range(len(want)):
        blocks.append([k, 1, 0.0])
        while True:
            s, n, _ = blocks[-1]
            b = np.mean(np.asarray(want[s:s + n]) - step * np.arange(n))
            blocks[-1][2] = min(max(b, lo), hi - (n - 1) * step)
            if len(blocks) > 1 and blocks[-2][2] + blocks[-2][1] * step > blocks[-1][2]:
                ps, pn, _ = blocks.pop(-2)
                blocks[-1] = [ps, pn + n, 0.0]
                continue
            break
    return [b + step * j for s, n, b in blocks for j in range(n)]


def soon_tags(fig, ax, w):
    """底側の 50 到達（ヒステリシス付き）に ●、線の先に答え合わせ ○/×、その下に「底が近いかも」札。
    札は点灯ごとに1枚、重ならないよう左右にずらす。ずれが札の幅の 1/4 を超えるときだけ、
    いちばん近い点灯どうしを1枚にまとめる（● と ○/× は1つずつ）"""
    x0, x1 = ax.get_xlim()
    px, py = F.per_pt(fig, ax)
    bpt = (x1 - x0) * px
    hw = (text_pt(fig, f"{TAG}（9回）", 9) / 2 + 0.3 * 9 + 1) * bpt  # まとめた札は「（n回）」付き
    xs = w.x
    groups = [[i] for i in w.sig["real", "bot"]]
    lo, hi = x0 + hw + 0.5, x1 - hw - 0.5
    while groups:
        mid = [(xs[g[0]] + xs[g[-1]]) / 2 for g in groups]
        cs = spread(mid, 2 * hw + 1, lo, hi)
        # 軸の端に寄せたぶんのずれは数えない（端の札をまとめてしまわないように）
        bad = {k for k, (c, m) in enumerate(zip(cs, mid)) if abs(c - min(max(m, lo), hi)) > hw / 2}
        pairs = [k for k in range(len(groups) - 1) if k in bad or k + 1 in bad]
        if not pairs:
            break
        k = min(pairs, key=lambda k: xs[groups[k + 1][0]] - xs[groups[k][-1]])
        groups[k:k + 2] = [groups[k] + groups[k + 1]]
    gw, last = 7.5 * bpt, -np.inf  # ○/× の字面の幅
    for idx, c in zip(groups, cs if groups else []):
        ax.text(c, LANE, TAG if len(idx) == 1 else f"{TAG}（{len(idx)}回）", ha="center", va="center", fontsize=9,
                color=GRN_D, zorder=7, bbox=dict(boxstyle="round,pad=0.3", fc="#e6f4ec", ec=GRN, lw=1.0))
        for i in idx:
            xi, v = w.x[i], -w.bot[i]
            xg = max(xi, last + gw)  # ○/× が重なるほど近いときは少し右へ
            ax.plot([xi, xi, xg], [v, GLY + 9 * py, GLY + 5 * py], color=GRN_D, lw=1.0, zorder=5)
            dot(ax, xi, v, GRN_D, ms=6)
            glyph(ax, xg, GLY, judge(w, "bot", i), GRN_D)
            last = xg


def now_p(ax, w, s, b):
    """最新の棒を枠で囲み、右端の段階帯の「いま」（底接近度）へ点線で結ぶ"""
    x, v = w.x[-1], s[-1]
    lo, hi = min(v, 0) - 6, max(v, 0) + 6
    ax.add_patch(Rectangle((x - 0.62, lo), 1.24, hi - lo, fill=False, ec=INK, lw=1.2, zorder=5))
    d = w.df.index[-1]
    ax.text(x + 0.62, lo - 3 if v >= 0 else hi + 3, f"{d.month}/{d.day}", ha="right",
            va="top" if v >= 0 else "bottom", fontsize=8.5, color=INK)
    ax.plot([x + 0.62, ax.get_xlim()[1]], [-b, -b], color="#444", lw=1.2, ls=(0, (1, 1.2)), zorder=5)


def scale_p(fig, ax, b):
    """右端の段階帯（棒と同じ色）と段階名（いつも全部出す）。いまの底接近度に ▶ と針（読み値は左上の見出し）"""
    px, py = F.per_pt(fig, ax)
    tr = blended_transform_factory(ax.transAxes, ax.transData)
    sx, sw, lx = 1 + 7 * px, 6 * px, 1 + 17 * px
    for sg, shades in ((1, TOP_MUTED), (-1, F.SHADES[-1])):
        for (lo, hi), fc in zip(F.BANDS, shades):
            ax.add_patch(Rectangle((sx, sg * lo), sw, sg * (hi - lo), transform=tr, fc=fc, ec="none", clip_on=False))
        for t in F.THS:
            ax.plot([sx, sx + sw], [sg * t] * 2, color="white", lw=1.0, transform=tr, clip_on=False)
    v = -b
    ax.plot([sx - px, sx + sw + px], [v, v], color="#222", lw=1.8, transform=tr, clip_on=False, zorder=7)
    ax.plot(1 + 3.5 * px, v, ">", ms=7, color=INK, transform=tr, clip_on=False, zorder=7)
    names = [(0, "中立", "#666")] + [(-(a + c) / 2, nm, GRN_D) for (a, c), nm in zip(F.BANDS[1:], STAGES_BOT[1:])]
    names += [((TH_SOON + 100) / 2, "過熱", MUTED_INK)]
    for y, name, c in names:
        ax.text(lx, y, name, transform=tr, fontsize=10, va="center", color=c)
    for k, txt in enumerate(("天井の予告には", "使えません。", "売りの合図でもない")):
        ax.text(lx, TH_SOON - 2 * py - k * 10 * py, txt, transform=tr, fontsize=7.5, va="top", color=MUTED_INK)


def header_p(ax, b, t):
    sw = DrawingArea(10, 10)
    sw.add_artist(Rectangle((0, 0), 10, 10, fc=shade_p(-b), ec=ink_bot(b), lw=1.0))
    row1 = [("TurnLine 底接近度　いま", 10, INK), sw, (f"{b:.0f}", 13, ink_bot(b)), (stage_bot(b), 11, ink_bot(b))]
    if t >= TH_CAUTION:
        row1.append((f"（過熱 {t:.0f}）", 9, MUTED_INK))
    real = [d["bot"][0] for _, _, d in HITS]
    fake = [d["bot"][1] for _, _, d in HITS] + list(GARCH_FAKE_BOT.values())
    panel_header(ax, [row1, [(f"過去の的中 {wari_span(real)}（時期で大きく違う。偶然でも{wari_span(fake)}）"
                              f"　○×＝{K}本（約2週間）以内に底が来たか", 8, INK2)]])


def fig_plan_f_prime(w):
    d = w.df.index[-1]
    fig, ax_p, ax = make_two_pane(
        w, f"案F'　底接近度ヒストグラム（実データ・{period_jp(w)}）",
        f"下向きの緑の棒＝底接近度（主役）。{TH_SOON} に届いたら「{TAG}」。上向きの薄い棒＝過熱（札は出さない）",
        height_ratios=(5, 4.9), figsize=(7.2, 11.4), price_ylim=None,
        label=f"{SOURCE[w.src][0]}（{d.year}年{d.month}月{d.day}日の時点で見た画面。値は TQQQ の株価ではない）", note="",
        candles=w.src != "sp3x_close")
    place([ax_p, ax], 0.876, (5, 4.9), (0.036,), 0.098)  # 価格の下に注記2行ぶんの間
    dy = 9 * 1.5 / (fig.get_figheight() * 72)
    lines(fig, 0.04, 0.927, ["棒と札はその日の終値までの情報だけ。▼▲ と ○× は後から分かる答え合わせ"], size=9, color=INK2)
    lines(fig, 0.04, 0.927 - dy, [f"「{TAG}」は買いの合図ではありません。急落中は何度も点灯し、そのあとさらに大きく下げることがあります"],
          size=9, color=RED_D)
    lines(fig, 0.04, 0.927 - 2 * dy, [memo(w)], size=9, color=INK2)
    turn_marks(fig, ax_p, w, confirm=True)
    hl, ll = np.median(lags(w, "H")), np.median(lags(w, "L"))
    ref, lag = w.long.lag_by_src[w.src]
    lines(fig, 0.04, ax_p.get_position().y0 - 0.013, [
        "▼▲＝天井/底（後から分かる位置）　確定＝リアルタイムで天井/底と分かる最初の日（点線＝待った日数）",
        f"確定までの待ち（中央値）: この期間 天井{hl:g}本・底{ll:g}本 ／ {ref} 天井{lag['H']:g}本・底{lag['L']:g}本"],
          size=7.5, color=INK2)
    ax.set_ylim(*YLIM_P)
    ax.set_yticks([])
    s = signed(w.top, w.bot)
    bars_p(ax, w.x, s)
    soon_tags(fig, ax, w)
    now_p(ax, w, s, w.bot[-1])
    scale_p(fig, ax, w.bot[-1])
    header_p(ax, w.bot[-1], w.top[-1])
    month_ticks(ax, w)
    lines(fig, 0.04, 0.054, [
        f"※ 実データ（{SOURCE[w.src][1]}）。TQQQ 本体ではない。",
        "※ 指標は TL-Classic3（その日の終値までの情報だけで計算）。未来の情報は ▼▲ と ○×（答え合わせ）だけ。",
        f"※ ○＝点灯後{K}本（約2週間）以内に底が来た　×＝空振り"], size=8.5, color=INK2)
    return fig


# ---------------------------------------------------------------- 3. 的中率の比較
C_REAL, C_FAKE, C_IDEAL = "#2a78d6", "#898781", "#52514e"


def hbar(ax, y, v, h, fc, ec="none", lw=0.0, r_pt=2.5):
    """右端（データ側）だけ角丸の横棒。左（基線側）は角"""
    px, py = F.per_pt(ax.figure, ax)
    x0, x1 = ax.get_xlim()
    rx, ry = min(r_pt * px * (x1 - x0), v / 2), min(r_pt * abs(py), h / 2)
    t = np.linspace(0, np.pi / 2, 10)
    y0, y1 = y - h / 2, y + h / 2
    pts = ([(0, y0), (0, y1)] + list(zip(v - rx + rx * np.sin(t), y1 - ry + ry * np.cos(t)))
           + list(zip(v - rx + rx * np.cos(t), y0 + ry - ry * np.sin(t))))
    ax.add_patch(Polygon(pts, closed=True, fc=fc, ec=ec, lw=lw, joinstyle="round", zorder=3))


def fig_scorecard(ev, drops):
    fig = plt.figure(figsize=(7.2, 10.4), dpi=200)
    fig.text(0.04, 0.966, "「そろそろ」点灯の的中率", fontsize=14)
    lines(fig, 0.04, 0.941, [f"点灯（{TH_SOON} 到達）のあと{K}本以内に、同じ側の転換点（底・天井）が本当に来た割合。",
                             "偽の価格＝値動きの向きだけをでたらめにした価格。そこで出る的中率が「偶然でも出る水準」"],
          size=9, color=INK2)
    keys = [(C_REAL, "TL-Classic3（実際の指標）"), (C_FAKE, "偽の価格（偶然の水準）"), (C_IDEAL, "理想形（サンプル・未来を使う）")]
    x = 0.04
    for c, s in keys:
        fig.patches.append(Rectangle((x, 0.8835), 0.024, 0.0085, transform=fig.transFigure,
                                     fc="white" if c == C_IDEAL else c, ec=c if c == C_IDEAL else "none", lw=1.0))
        fig.text(x + 0.031, 0.8878, s, fontsize=8.5, color=INK, va="center")
        x += 0.031 + text_pt(fig, s, 8.5) / (7.2 * 72) + 0.04
    H = 0.23
    for k, (side, title, word, move) in enumerate((("bot", "底側「底が近いかも」（旧: そろそろ安値）", "底", "下げる"),
                                                   ("top", "天井側「そろそろ高値」（案F' では札を出さない）", "天井", "上がる"))):
        vs = [verdict(*d[side][:2]) for _, _, d in HITS]
        by = {v: "・".join(dict.fromkeys(p + ("（コロナ急落・2022年の下落を含む）" if p == "2019-22" and side == "bot" else "")
                                         for (p, _, _), u in zip(HITS, vs) if u == v)) for v in VERDICTS}
        lead, rem = [e[side]["lead_med"] for e in ev], [e[side]["remain_med"] for e in ev]
        note = ["、".join(f"{by[v]}は{v}" for v in dict.fromkeys(vs)) + "。"]
        if side == "bot":
            g = list(GARCH_FAKE_BOT.values())
            med, big = [d[0] for d in drops], [d[1] for d in drops]
            note += [f"下げで荒れる性質を残した偽の価格（GARCH）だと偶然でも{min(g):.0%}〜{max(g):.0%}出て、"
                     f"はっきり上回ったのは2011-18だけ。",
                     f"点灯のあとも次の底まで中央値{span(med, '%')}さらに下げ、10%以上下げた点灯も{span(big, '%')}ある"]
        else:
            note += [f"点灯は{word}の中央{span(lead, '本')}前で、そのあとも中央値{span(rem, '%')}さらに{move}"]
        y1 = 0.80 - k * 0.400
        ax = fig.add_axes([0.30, y1 - 0.31, 0.50, 0.30])
        fig.text(0.04, y1 + 0.052, title, fontsize=12, color=INK)
        lines(fig, 0.04, y1 + 0.032, note, size=8.5, color=INK2, step=1.4)
        ax.set_xlim(0, 100)
        ax.set_ylim(len(HITS) - 0.45, -0.62)
        for s in ("top", "right", "left"):
            ax.spines[s].set_visible(False)
        ax.spines["bottom"].set_color("#c3c2b7")
        ax.set_xticks([0, 25, 50, 75, 100], ["0%", "25%", "50%", "75%", "100%"])
        ax.tick_params(colors=INK3, labelsize=8, length=0)
        ax.set_yticks([])
        ax.grid(True, axis="x", color="#e1e0d9", lw=0.8)
        ax.set_axisbelow(True)
        tr = blended_transform_factory(fig.transFigure, ax.transData)
        for g, (per, data, d) in enumerate(HITS):
            for j, (v, c) in enumerate(zip(d[side], (C_REAL, C_FAKE, C_IDEAL))):
                y = g + (j - 1) * H
                if v is None:
                    ax.text(1, y, "―（表になし）", va="center", fontsize=8, color=INK3)
                    continue
                hbar(ax, y, 100 * v, H * 0.72, "white" if c == C_IDEAL else c, ec=c if c == C_IDEAL else "none",
                     lw=1.0 if c == C_IDEAL else 0.0)
                ax.text(100 * v + 1.5, y, f"{v:.0%}", va="center", fontsize=8.5, color=INK)
            fig.text(0.04, g - 0.03, per, fontsize=10.5, color=INK, va="bottom", transform=tr)
            fig.text(0.04, g + 0.05, data, fontsize=8, color=INK2, va="top", transform=tr)
            fig.text(0.825, g, vs[g], fontsize=9.5, color=INK, va="center", transform=tr)
    lines(fig, 0.04, 0.054, [
        "※ 2011-18 NASDAQ×3 は指標を決めたあとの検証期間。S&P500×3 は別の指数での確認（2019-22・1991-98 は終値だけのデータ）。",
        "※ 偽の価格（灰）は値動きの向きだけをでたらめにした価格の中央値。判定は本物との差（±5pt）による目安で、検定ではない。",
        "※ 理想形は未来の転換点から逆算した目安で、実際には作れない（「10本以内」で数えるため、脚の長い期間では低く出ることがある）。",
        "※ 何本前・さらに下げる/上がる幅は TL-Classic3 の値（3倍の価格での％。下げ幅は点灯1回ごと）。"], size=7.5)
    return fig


# ---------------------------------------------------------------- 実行
# ---------------------------------------------------------------- 0. 答えのページ（PDF の1枚目）
SUMMARY = [
    ("答え: 案F をそのまま作るのは勧めません", 15, RED_D, 0),
    ("別ウィンドウに1日1本の棒を出す形は使えます。", 10.5, INK, 0),
    ("ただし、中身と札の意味を変えた「案F'」にしてください。", 10.5, INK, 0),
    ("", 6, INK, 0),
    ("①「そろそろ高値」は出さない", 12, INK, 0),
    ("当たりは2〜3割で、値動きの向きをでたらめにした偽の価格より低い。", 9.5, INK2, 1),
    ("上向きの棒は「過熱」の参考表示だけにする（売りの合図でもない）。", 9.5, INK2, 1),
    ("②「そろそろ安値」は「底が近いかも」に弱める", 12, INK, 0),
    ("当たりは時期によって5〜9割。でも偶然でも5〜7割は出る。", 9.5, INK2, 1),
    ("はっきり偶然より上だったのは2011〜18年だけで、", 9.5, INK2, 1),
    ("2000〜02年・2008年・2020年・2022年のような下げでは外れが多い。", 9.5, INK2, 1),
    ("③「底が近いかも」は買いの合図ではない", 12, RED_D, 0),
    ("急落中は何度も点灯する。2020年（コロナ急落）は最初の点灯から", 9.5, INK2, 1),
    ("さらに最大73%（3倍換算）下げた。", 9.5, INK2, 1),
    ("④ 棒はなだらかには伸びない", 12, INK, 0),
    ("日々ギザギザに動く。天井・底の「確定」は4〜17営業日（中央値）遅れて出る。", 9.5, INK2, 1),
    ("", 6, INK, 0),
    ("次にすること", 12, INK, 0),
    ("1. 案F' は「見るだけの表示」として作ってよい（売買の判断には使わない）", 9.5, INK2, 1),
    ("2. TQQQ 本体の日足 CSV（2010年〜今日）があれば、同じ方法で検証し直す", 9.5, INK2, 1),
    ("3. 急落中の札の出し方を検証してから、売買の参考にするかを決める", 9.5, INK2, 1),
    ("", 6, INK, 0),
    ("※ データは NASDAQ総合・S&P500 を日次3倍にした近似（1990〜2022年）。TQQQ 本体ではない。", 8, INK3, 0),
    ("※ 次のページから: 的中率のまとめ → 空振りの多かった2020年・2022年 → 当たりの多かった2018年・2015年 → 理想形との違い", 8, INK3, 0),
]


def fig_summary():
    fig = plt.figure(figsize=(7.2, 9.6), dpi=200)
    fig.text(0.06, 0.945, "TurnLine 検証の答え", fontsize=18, color=INK)
    fig.text(0.06, 0.918, "実データ（指数×3 の近似）で、未来の情報を使わずに検証した結果", fontsize=9, color=INK2)
    y = 0.865
    for text, size, color, indent in SUMMARY:
        if text:
            fig.text(0.06 + 0.035 * indent, y, text, fontsize=size, color=color)
        y -= size * 1.75 / (fig.get_figheight() * 72)
    return fig


def main():
    ws = load_windows()
    ev, drops = eval_rows()
    for (per, data, d), e in zip(HITS, ev):  # 表の TL-Classic3 の値と L.evaluate の照合
        for side in ("top", "bot"):
            if abs(d[side][0] - e[side]["precision"]) > 0.005:
                print(f"! 表と不一致: {per} {data} {side} 表={d[side][0]} 計算={e[side]['precision']:.3f}")
    figs = [("fig_summary.png", fig_summary()),
            ("fig_scorecard.png", fig_scorecard(ev, drops)),
            ("fig_planF_prime_2020.png", fig_plan_f_prime(ws["2020"])),
            ("fig_planF_prime_2022.png", fig_plan_f_prime(ws["2022"])),
            ("fig_planF_prime_2018.png", fig_plan_f_prime(ws["2018"])),
            ("fig_planF_prime_2015.png", fig_plan_f_prime(ws["2015"])),
            ("fig_ideal_vs_real.png", fig_ideal_vs_real(ws["2018"]))]
    for name, fig in figs:
        fig.savefig(OUT / name)
        plt.close(fig)
        print("saved:", OUT / name)
    imgs = [Image.open(OUT / name).convert("RGB") for name, _ in figs]
    pdf = OUT / "TurnLine_verification.pdf"
    imgs[0].save(pdf, save_all=True, append_images=imgs[1:], resolution=200, quality=92,
                 creationDate=None, modDate=None)
    print("saved:", pdf)
    for w in ws.values():
        print(f"[{w.key}] {w.a}〜{w.b}: {len(w.x)}本 / 転換点 天井{(w.pk == 'H').sum()}・底{(w.pk == 'L').sum()}"
              f" / 確定の遅れ 天井{lags(w, 'H').tolist()}・底{lags(w, 'L').tolist()}")
        for name in ("ideal", "real"):
            for side in ("top", "bot"):
                n, o, x = tally(w, name, side)
                print(f"   {name:5s} {side}: 点灯{n}回 ○{o} ×{x}  {[str(w.df.index[i].date()) for i in w.sig[name, side]]}")
        print(f"   いま: top={w.top[-1]:.1f} bot={w.bot[-1]:.1f}")


if __name__ == "__main__":
    main()
