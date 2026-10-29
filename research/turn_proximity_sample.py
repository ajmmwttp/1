"""TurnLine 改良案: 「天井/底 接近度」のサンプル描画と簡易検証.

ネットワーク制限で実データを取得できないため, TQQQ 風の合成日足で検証する.
実データの CSV (Date,Open,High,Low,Close) を引数に渡せばそちらを使う.
"""
import sys
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap

plt.rcParams["font.family"] = "IPAGothic"
OUT = sys.argv[2] if len(sys.argv) > 2 else "research"


def synthetic(n=260, seed=7):
    rng = np.random.default_rng(seed)
    drift, left, rets = 0.0, 0, []
    for _ in range(n):
        if left == 0:
            left = rng.integers(14, 32)
            drift = rng.choice([1, -1]) * rng.uniform(0.006, 0.012)
        left -= 1
        rets.append(drift + rng.normal(0, 0.028))
    close = 55 * np.exp(np.cumsum(rets))
    open_ = np.r_[close[0], close[:-1]] * np.exp(rng.normal(0, 0.006, n))
    high = np.maximum(open_, close) * np.exp(np.abs(rng.normal(0, 0.012, n)))
    low = np.minimum(open_, close) * np.exp(-np.abs(rng.normal(0, 0.012, n)))
    idx = pd.bdate_range(end="2026-10-28", periods=n)
    return pd.DataFrame(dict(Open=open_, High=high, Low=low, Close=close), index=idx)


def load():
    if len(sys.argv) > 1 and sys.argv[1] != "-":
        return pd.read_csv(sys.argv[1], parse_dates=["Date"], index_col="Date")
    return synthetic()


def rma(s, n):
    return s.ewm(alpha=1 / n, adjust=False).mean()


def proximity(df, n=14):
    """天井接近度 / 底接近度 (0-100). Pine にそのまま移植できる計算のみ使う."""
    c, h, l = df.Close, df.High, df.Low
    tr = pd.concat([h - l, (h - c.shift()).abs(), (l - c.shift()).abs()], axis=1).max(axis=1)
    atr = rma(tr, n)
    # 1) 伸び: EMA20 からの乖離 (ATR 単位)
    stretch = (c - c.ewm(span=20, adjust=False).mean()) / atr
    # 2) RSI
    d = c.diff()
    rsi = 100 - 100 / (1 + rma(d.clip(lower=0), n) / rma((-d).clip(lower=0), n))
    # 3) レンジ内位置 (ストキャス)
    k = (c - l.rolling(n).min()) / (h.rolling(n).max() - l.rolling(n).min())
    # 4) 勢いの鈍化: 上昇中なのに上昇速度が落ちている → 天井が近い
    mom = (c.ewm(span=5, adjust=False).mean().diff(3)) / atr
    decel = -(mom.diff(2))

    clip = lambda x: x.clip(0, 1)
    # 伸び切り度 (トレンドが強いほど高い) × 失速度 (勢いが鈍るほど高い)
    # 失速を掛けることで, 一方的なトレンド中にずっと「そろそろ」が出続けるのを抑える
    top_base = 0.45 * clip((stretch - 0.3) / 2.2) + 0.35 * clip((rsi - 50) / 25) + 0.20 * clip((k - 0.5) / 0.5)
    bot_base = 0.45 * clip((-stretch - 0.3) / 2.2) + 0.35 * clip((50 - rsi) / 25) + 0.20 * clip((0.5 - k) / 0.5)
    top_ex = clip(decel / 0.5).ewm(span=5, adjust=False).mean()
    bot_ex = clip(-decel / 0.5).ewm(span=5, adjust=False).mean()
    top = top_base * (0.55 + 0.45 * top_ex) / 0.9
    bot = bot_base * (0.55 + 0.45 * bot_ex) / 0.9
    sm = lambda x: (100 * x).ewm(span=4, adjust=False).mean()  # なだらかにする
    return sm(top).fillna(0), sm(bot).fillna(0)


def zigzag(c, pct=0.10):
    """後知恵の天井/底 (検証用の正解ラベル)."""
    piv, last_i, last_p, trend = [], 0, c.iloc[0], 1
    for i, p in enumerate(c):
        if trend > 0 and p > last_p or trend < 0 and p < last_p:
            last_i, last_p = i, p
        elif trend > 0 and p < last_p * (1 - pct):
            piv.append((last_i, "top")); trend, last_i, last_p = -1, i, p
        elif trend < 0 and p > last_p * (1 + pct):
            piv.append((last_i, "bot")); trend, last_i, last_p = 1, i, p
    return piv


def evaluate(top, bot, piv, warn=60, win=10):
    rows = []
    for i, kind in piv:
        s = (top if kind == "top" else bot).values
        lead = None
        for j in range(i, max(i - 25, 0), -1):  # ピーク直前の連続警戒区間の開始
            if s[j] >= warn:
                lead = i - j
            elif lead is not None:
                break
        rows.append((kind, lead))
    # 誤警報: warn を上抜けたのに win 本以内に同種の転換が無い
    false = total = 0
    for s, kind in ((top, "top"), (bot, "bot")):
        ups = np.where((s.values[1:] >= warn) & (s.values[:-1] < warn))[0] + 1
        pk = [i for i, k in piv if k == kind]
        for u in ups:
            total += 1
            false += not any(0 <= p - u <= win for p in pk)
    return rows, false, total


CMAP_TOP = LinearSegmentedColormap.from_list("t", ["#e8e8e8", "#f6c28b", "#e0703a", "#b3261e"])
CMAP_BOT = LinearSegmentedColormap.from_list("b", ["#e8e8e8", "#a8d5b0", "#4caf6a", "#1b6b3a"])


def heat(t, b):
    """接近度の強い方の色. 両方弱ければグレー."""
    return CMAP_TOP(t / 100) if t >= b else CMAP_BOT(b / 100)


def candles(ax, df, colors=None):
    x = np.arange(len(df))
    for i, (o, h, l, c) in enumerate(df[["Open", "High", "Low", "Close"]].values):
        col = colors[i] if colors is not None else ("#26a69a" if c >= o else "#ef5350")
        ax.vlines(i, l, h, color=col, lw=0.8)
        ax.add_patch(plt.Rectangle((i - 0.35, min(o, c)), 0.7, max(abs(c - o), 1e-6), color=col))
    ax.set_xlim(-1, len(df) + 6)
    ax.margins(y=0.08)
    ticks = [i for i in x if i > 5 and df.index[i].month != df.index[i - 1].month]
    ax.set_xticks(ticks, [f"{df.index[i].month}月" for i in ticks])
    ax.grid(alpha=0.25)
    ax.yaxis.tick_right()


def stage(v):
    return "間近" if v >= 80 else "そろそろ" if v >= 60 else "注意" if v >= 40 else "—"


def sample_a(df, top, bot, piv, path):
    """案A: 別ウィンドウ無し. ローソク足の色 + 下端の接近度リボン + 現在値ゲージ."""
    fig, ax = plt.subplots(figsize=(7.2, 9))
    cols = [heat(t, b) for t, b in zip(top, bot)]
    candles(ax, df, cols)
    lo, hi = ax.get_ylim()
    rib = lo - (hi - lo) * 0.06
    for i, c in enumerate(cols):
        ax.add_patch(plt.Rectangle((i - 0.5, rib), 1, (hi - lo) * 0.045, color=c, lw=0))
    ax.set_ylim(rib - (hi - lo) * 0.01, hi)
    ax.text(0, rib + (hi - lo) * 0.05, "接近度リボン (色が濃い=転換が近い)", fontsize=8, color="#555")
    for i, kind in piv:
        y = df.High.iloc[i] if kind == "top" else df.Low.iloc[i]
        ax.annotate("天井" if kind == "top" else "底", (i, y), xytext=(0, 10 if kind == "top" else -16),
                    textcoords="offset points", ha="center", fontsize=8,
                    color="#b3261e" if kind == "top" else "#1b6b3a")
    t, b = top.iloc[-1], bot.iloc[-1]
    side, v, c = ("天井", t, "#b3261e") if t >= b else ("底", b, "#1b6b3a")
    ax.text(0.02, 0.97, f"{side}接近度 {v:.0f}%  {stage(v)}", transform=ax.transAxes, va="top",
            fontsize=13, color="white", bbox=dict(fc=c, ec="none", boxstyle="round,pad=0.4"))
    gx = ax.inset_axes([0.02, 0.83, 0.42, 0.035])
    gx.imshow(np.linspace(0, 1, 100)[None], aspect="auto", cmap=CMAP_TOP if t >= b else CMAP_BOT, extent=(0, 100, 0, 1))
    gx.axvline(v, color="black", lw=2.5)
    gx.set_xticks([40, 60, 80], ["注意", "そろそろ", "間近"], fontsize=7)
    gx.set_yticks([])
    ax.set_title("案A: 価格チャート上に表示 (サブウィンドウ不要)", fontsize=12, loc="left")
    fig.tight_layout(); fig.savefig(path, dpi=150); plt.close(fig)


def sample_b(df, top, bot, piv, path):
    """案B: サブウィンドウを1本のなだらかな山に整理."""
    fig, (ax, ox) = plt.subplots(2, 1, figsize=(7.2, 10), sharex=True,
                                 gridspec_kw=dict(height_ratios=[1.7, 1], hspace=0.04))
    candles(ax, df)
    x = np.arange(len(df))
    for lv, name in ((40, "注意"), (60, "そろそろ"), (80, "間近")):
        ox.axhspan(lv, 100 if lv == 80 else lv + 20, color="#b3261e", alpha=0.03 + lv / 2000, lw=0)
        ox.axhspan(-lv - (20 if lv < 80 else 20), -lv, color="#1b6b3a", alpha=0.03 + lv / 2000, lw=0)
        ox.axhline(lv, color="#b3261e", lw=0.6, ls=":"); ox.axhline(-lv, color="#1b6b3a", lw=0.6, ls=":")
        ox.text(2, lv + 2, name, fontsize=7, color="#b3261e")
        ox.text(2, -lv + 2, name, fontsize=7, color="#1b6b3a")
    ox.bar(x, top, width=1.0, color=[CMAP_TOP(v / 100) for v in top], lw=0)
    ox.bar(x, -bot, width=1.0, color=[CMAP_BOT(v / 100) for v in bot], lw=0)
    ox.plot(x, top, color="#b3261e", lw=1.2); ox.plot(x, -bot, color="#1b6b3a", lw=1.2)
    for i, kind in piv:
        ax.axvline(i, color="#b3261e" if kind == "top" else "#1b6b3a", lw=0.6, alpha=0.4)
        ox.axvline(i, color="#b3261e" if kind == "top" else "#1b6b3a", lw=0.6, alpha=0.4)
    ox.set_ylim(-100, 100); ox.set_yticks([-100, 0, 100], ["底100", "0", "天井100"])
    ox.yaxis.tick_right(); ox.grid(alpha=0.2)
    ox.text(len(df) * 0.35, 92, "↑ 天井接近度", fontsize=9, color="#b3261e", va="top")
    ox.text(len(df) * 0.35, -96, "↓ 底接近度", fontsize=9, color="#1b6b3a")
    ax.set_title("案B: サブウィンドウ整理版 (縦線=実際の天井/底)", fontsize=12, loc="left")
    fig.subplots_adjust(left=0.03, right=0.9, top=0.95, bottom=0.04)
    fig.savefig(path, dpi=150); plt.close(fig)


def main():
    df = load()
    top, bot = proximity(df)
    piv = zigzag(df.Close)
    rows, false, total = evaluate(top, bot, piv)
    print("転換点ごとの事前警告 (60%超えが何本前から続いたか):")
    for (kind, lead), (i, _) in zip(rows, piv):
        print(f"  {df.index[i].date()} {'天井' if kind == 'top' else '底  '}  "
              + (f"{lead}本前から" if lead is not None else "警告なし"))
    hit = sum(l is not None for _, l in rows)
    print(f"検出 {hit}/{len(rows)}, 平均リード {np.mean([l for _, l in rows if l is not None]):.1f}本, "
          f"誤警報 {false}/{total}")
    sample_a(df, top, bot, piv, f"{OUT}/sample_A_price_overlay.png")
    sample_b(df, top, bot, piv, f"{OUT}/sample_B_subpane.png")


if __name__ == "__main__":
    main()
