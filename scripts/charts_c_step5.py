# -*- coding: utf-8 -*-
"""段5: chart4「時間の内訳」ドーナツ → 横棒（emphasis形式）に構成変更。

順序（AZ列）: 0=段取り / 1=移動 / 2=ピック（唯一の付加価値）
配色: ピック=青2E75B6（主役）、段取り・移動=グレー8C8C8C（文脈）。
ドーナツの角度読み取りより、横棒の長さ比較のほうが正確に読める（part-to-whole→bar）。
カテゴリラベル（時間・割合入りの文字列）が凡例の代わりを果たすため凡例は外す。
"""
import json
import re
import zipfile

SRC, DST = "c4.xlsx", "c5.xlsx"
V = json.load(open("chart_cache.json"))

def strcache(vals):
    pts = "".join(f'<c:pt idx="{i}"><c:v>{v}</c:v></c:pt>' for i, v in enumerate(vals))
    return f'<c:strCache><c:ptCount val="{len(vals)}"/>{pts}</c:strCache>'

def numcache(vals):
    pts = "".join(f'<c:pt idx="{i}"><c:v>{v}</c:v></c:pt>' for i, v in enumerate(vals))
    return (f'<c:numCache><c:formatCode>General</c:formatCode>'
            f'<c:ptCount val="{len(vals)}"/>{pts}</c:numCache>')

def dpt(idx, color):
    return (f'<c:dPt><c:idx val="{idx}"/><c:bubble3D val="0"/>'
            f'<c:spPr><a:solidFill><a:srgbClr val="{color}"/></a:solidFill>'
            f'<a:ln><a:solidFill><a:srgbClr val="FFFFFF"/></a:solidFill></a:ln></c:spPr></c:dPt>')

BAR = (
  '<c:plotArea><c:layout/><c:barChart><c:barDir val="bar"/><c:grouping val="clustered"/>'
  '<c:varyColors val="1"/>'
  '<c:ser><c:idx val="0"/><c:order val="0"/><c:tx><c:v>時間</c:v></c:tx>'
  '<c:spPr><a:solidFill><a:srgbClr val="8C8C8C"/></a:solidFill></c:spPr>'
  + dpt(0, "8C8C8C") + dpt(1, "8C8C8C") + dpt(2, "2E75B6") +
  f'<c:cat><c:strRef><c:f>ダッシュボード!$AZ$3:$AZ$5</c:f>{strcache(V["db_mix_lbl"])}</c:strRef></c:cat>'
  f'<c:val><c:numRef><c:f>ダッシュボード!$AX$3:$AX$5</c:f>{numcache(V["db_mix_val"])}</c:numRef></c:val>'
  '</c:ser>'
  '<c:dLbls><c:showLegendKey val="0"/><c:showVal val="0"/><c:showCatName val="0"/>'
  '<c:showSerName val="0"/><c:showPercent val="0"/><c:showBubbleSize val="0"/></c:dLbls>'
  '<c:gapWidth val="60"/><c:axId val="30"/><c:axId val="40"/></c:barChart>'
  '<c:catAx><c:axId val="30"/><c:scaling><c:orientation val="maxMin"/></c:scaling>'
  '<c:delete val="0"/><c:axPos val="l"/><c:majorTickMark val="none"/>'
  '<c:minorTickMark val="none"/><c:tickLblPos val="nextTo"/>'
  '<c:crossAx val="40"/><c:crosses val="autoZero"/><c:auto val="1"/>'
  '<c:lblAlgn val="ctr"/><c:lblOffset val="100"/><c:noMultiLvlLbl val="0"/></c:catAx>'
  '<c:valAx><c:axId val="40"/><c:scaling><c:orientation val="minMax"/></c:scaling>'
  '<c:delete val="0"/><c:axPos val="b"/><c:title><c:tx><c:rich><a:bodyPr/><a:lstStyle/>'
  '<a:p><a:pPr><a:defRPr/></a:pPr><a:r><a:rPr lang="ja-JP" altLang="en-US"/>'
  '<a:t>時間 (h)</a:t></a:r></a:p></c:rich></c:tx><c:overlay val="1"/></c:title>'
  '<c:majorTickMark val="none"/><c:minorTickMark val="none"/><c:tickLblPos val="nextTo"/>'
  '<c:crossAx val="30"/><c:crosses val="autoZero"/><c:crossBetween val="between"/></c:valAx>'
  '</c:plotArea>')

def patch(x):
    m = re.search(r'<c:plotArea>.*?</c:plotArea>', x, re.S)
    assert m and '<c:doughnutChart>' in m.group(0)
    x = x.replace(m.group(0), BAR, 1)
    # ドーナツ用の凡例はカテゴリラベルに置き換わったので除去
    x = re.sub(r'<c:legend>.*?</c:legend>', '', x, count=1, flags=re.S)
    assert '[1]!' not in x
    return x

zi = zipfile.ZipFile(SRC); zo = zipfile.ZipFile(DST, "w", zipfile.ZIP_DEFLATED)
for it in zi.infolist():
    b = zi.read(it.filename)
    if it.filename == "xl/charts/chart4.xml":
        b = patch(b.decode("utf-8")).encode("utf-8")
    zo.writestr(it, b)
zo.close(); zi.close()
print("wrote", DST)
