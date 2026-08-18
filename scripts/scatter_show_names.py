# -*- coding: utf-8 -*-
"""③改善優先度マトリクスに全員の氏名を表示する。

利用者の選択:
  - 「1人1系列」方式（系列名をセル参照にするため、人数・氏名の変更に自動追随）
  - ラベルは上下左右に振り分けて重なりを減らす

背景:
  元の実装は 1系列19点に対して <c:dLbl><c:tx><c:strRef> でセルを参照し、
  さらに c15:showDataLabelsRange="0"・showVal等も全て 0 だったため、
  ラベルが一切描画されなかった。系列名（<c:ser><c:tx><c:strRef>）＋
  showSerName="1" は標準 OOXML で、描画されることを実測で確認済み。
"""
import re
import zipfile

SRC, DST = "out2p.xlsx", "out3.xlsx"
N        = 50          # 収容人数
D        = "印刷用データ"
LBL_SZ   = "600"       # 6pt
AX_MIN, AX_MAX = 40.0, 190.0

SER_FMT = ('<c:spPr><a:ln><a:noFill/><a:prstDash val="solid"/></a:ln></c:spPr>'
           '<c:marker><c:symbol val="circle"/><c:size val="7"/><c:spPr>'
           '<a:solidFill><a:srgbClr val="2E75B6"/></a:solidFill>'
           '<a:ln><a:prstDash val="solid"/></a:ln></c:spPr></c:marker>')

# ------------------------------------------------------------ 配置の決定
# プロット領域はおよそ 290pt(横) × 300pt(縦)。軸は 40〜190 なので
# 1pt ≒ 0.52(横) / 0.50(縦) データ単位。6pt の全角文字は 1文字 6pt。
PT_X, PT_Y = (AX_MAX - AX_MIN) / 290.0, (AX_MAX - AX_MIN) / 300.0
GAP = 5 * PT_Y                      # マーカー(7pt)分の逃がし
ORDER = ["t", "b", "r", "l"]        # 既定は真上、ぶつかれば下・右・左

def rect(x, y, pos, name):
    w = len(name) * 6 * PT_X        # ラベル幅（データ単位）
    h = 8 * PT_Y                    # ラベル高
    if pos == "t": return (x - w/2, y + GAP,     x + w/2, y + GAP + h)
    if pos == "b": return (x - w/2, y - GAP - h, x + w/2, y - GAP)
    if pos == "r": return (x + GAP, y - h/2,     x + GAP + w, y + h/2)
    return              (x - GAP - w, y - h/2,   x - GAP,     y + h/2)

def overlaps(a, b):
    return not (a[2] <= b[0] or b[2] <= a[0] or a[3] <= b[1] or b[3] <= a[1])

def inside(r):
    return r[0] >= AX_MIN and r[2] <= AX_MAX and r[1] >= AX_MIN and r[3] <= AX_MAX

def assign(points):
    """points: {idx: (x, y, name)} → {idx: pos}。上から順に貪欲に決める。"""
    placed, out = [], {}
    for i in sorted(points, key=lambda k: -points[k][1]):
        x, y, nm = points[i]
        chosen = None
        for pos in ORDER:
            r = rect(x, y, pos, nm)
            if inside(r) and not any(overlaps(r, p) for p in placed):
                chosen = pos; placed.append(r); break
        if chosen is None:                      # どこも空かない場合
            chosen = "t"; placed.append(rect(x, y, "t", nm))
        out[i] = chosen
    return out

# ------------------------------------------------------------ 組み立て
src = zipfile.ZipFile(SRC).read("xl/charts/chart10.xml").decode("utf-8")
sers = re.findall(r"<c:ser>.*?</c:ser>", src, re.S)
assert len(sers) == 3, f"系列数が想定外: {len(sers)}"
main, guides = sers[0], sers[1] + sers[2]

def cache(tag):
    b = re.search(r"<c:%s>.*?</c:%s>" % (tag, tag), main, re.S).group(0)
    return {int(m.group(1)): float(m.group(2))
            for m in re.finditer(r'<c:pt idx="(\d+)"[^>]*><c:v>([\d.]+)</c:v>', b)}

X, Y = cache("xVal"), cache("yVal")
NAMES = {}
for l in re.findall(r"<c:dLbl>.*?</c:dLbl>", src, re.S):
    i = int(re.search(r'<c:idx val="(\d+)"/>', l).group(1))
    m = re.search(r"<c:strCache>.*?<c:v>(.*?)</c:v>", l, re.S)
    if m:
        NAMES[i] = m.group(1)
print(f"既存の点: {len(X)}  氏名: {len(NAMES)}")

pos = assign({i: (X[i], Y[i], NAMES[i]) for i in X if i in NAMES})
for i in range(N):                              # データが無い系列は循環で散らす
    pos.setdefault(i, ORDER[i % len(ORDER)])
from collections import Counter
print("ラベル位置の内訳(実データ19点):", Counter(pos[i] for i in sorted(X)))

def series(i):
    r = 3 + i
    nm = NAMES.get(i)
    txc = (f'<c:strCache><c:ptCount val="1"/><c:pt idx="0"><c:v>{nm}</c:v></c:pt></c:strCache>'
           if nm else "")
    xc = f'<c:pt idx="0"><c:v>{X[i]!r}</c:v></c:pt>' if i in X else ""
    yc = f'<c:pt idx="0"><c:v>{Y[i]!r}</c:v></c:pt>' if i in Y else ""
    return (
        f'<c:ser><c:idx val="{i}"/><c:order val="{i}"/>'
        f'<c:tx><c:strRef><c:f>{D}!$K${r}</c:f>{txc}</c:strRef></c:tx>'
        + SER_FMT +
        '<c:dLbls><c:spPr><a:noFill/><a:ln><a:noFill/></a:ln></c:spPr>'
        '<c:txPr><a:bodyPr/><a:lstStyle/><a:p><a:pPr>'
        f'<a:defRPr sz="{LBL_SZ}"/></a:pPr><a:endParaRPr lang="ja-JP"/></a:p></c:txPr>'
        f'<c:dLblPos val="{pos[i]}"/>'
        '<c:showLegendKey val="0"/><c:showVal val="0"/><c:showCatName val="0"/>'
        '<c:showSerName val="1"/><c:showPercent val="0"/><c:showBubbleSize val="0"/></c:dLbls>'
        f'<c:xVal><c:numRef><c:f>{D}!$L${r}</c:f><c:numCache>'
        f'<c:formatCode>0.0"%"</c:formatCode><c:ptCount val="1"/>{xc}</c:numCache></c:numRef></c:xVal>'
        f'<c:yVal><c:numRef><c:f>{D}!$M${r}</c:f><c:numCache>'
        f'<c:formatCode>0.0"%"</c:formatCode><c:ptCount val="1"/>{yc}</c:numCache></c:numRef></c:yVal>'
        '<c:smooth val="0"/></c:ser>')

g = guides
for old, new in ((1, N), (2, N + 1)):           # ガイド線2本を後ろへ
    g = g.replace(f'<c:idx val="{old}"/><c:order val="{old}"/>',
                  f'<c:idx val="{new}"/><c:order val="{new}"/>', 1)
out = src.replace(main + guides, "".join(series(i) for i in range(N)) + g, 1)
assert out != src and out.count("<c:ser>") == N + 2

zi = zipfile.ZipFile(SRC); zo = zipfile.ZipFile(DST, "w", zipfile.ZIP_DEFLATED)
for it in zi.infolist():
    zo.writestr(it, out.encode("utf-8") if it.filename == "xl/charts/chart10.xml"
                else zi.read(it.filename))
zo.close(); zi.close()
print("wrote", DST, "系列数:", out.count("<c:ser>"))
