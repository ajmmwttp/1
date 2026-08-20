# -*- coding: utf-8 -*-
"""段3: chart3 日次折れ線の修復＋目標100%線の追加。"""
import json
import re
import zipfile

SRC, DST = "c1.xlsx", "c3.xlsx"
V = json.load(open("chart_cache.json"))
N = len(V["dy_label"])          # 21日

def strcache(vals):
    pts = "".join(f'<c:pt idx="{i}"><c:v>{v}</c:v></c:pt>' for i, v in enumerate(vals))
    return f'<c:strCache><c:ptCount val="{len(vals)}"/>{pts}</c:strCache>'

def numcache(vals):
    pts = "".join(f'<c:pt idx="{i}"><c:v>{v}</c:v></c:pt>'
                  for i, v in enumerate(vals) if v is not None)
    return (f'<c:numCache><c:formatCode>General</c:formatCode>'
            f'<c:ptCount val="{len(vals)}"/>{pts}</c:numCache>')

CAT = f'<c:strRef><c:f>日次!$C$8:$C$28</c:f>{strcache(V["dy_label"])}</c:strRef>'

def patch(x):
    old_cat = '<c:multiLvlStrRef><c:f>[1]!_dyLabel</c:f></c:multiLvlStrRef>'
    assert x.count(old_cat) == 2
    x = x.replace(old_cat, CAT)
    x = x.replace('<c:numRef><c:f>[1]!_dyPickEff</c:f></c:numRef>',
                  f'<c:numRef><c:f>日次!$G$8:$G$28</c:f>{numcache(V["dy_pick"])}</c:numRef>', 1)
    x = x.replace('<c:numRef><c:f>[1]!_dyPackEff</c:f></c:numRef>',
                  f'<c:numRef><c:f>日次!$K$8:$K$28</c:f>{numcache(V["dy_pack"])}</c:numRef>', 1)
    assert '[1]!' not in x

    # 目標100% 線（リテラル値・グレー破線・マーカー無し）
    lits = "".join(f'<c:pt idx="{i}"><c:v>100</c:v></c:pt>' for i in range(N))
    goal = ('<c:ser><c:idx val="2"/><c:order val="2"/><c:tx><c:v>目標 100%</c:v></c:tx>'
            '<c:spPr><a:ln w="12000"><a:solidFill><a:srgbClr val="595959"/></a:solidFill>'
            '<a:prstDash val="dash"/></a:ln></c:spPr>'
            '<c:marker><c:symbol val="none"/></c:marker>'
            f'<c:cat>{CAT}</c:cat>'
            f'<c:val><c:numLit><c:formatCode>General</c:formatCode>'
            f'<c:ptCount val="{N}"/>{lits}</c:numLit></c:val>'
            '<c:smooth val="0"/></c:ser>')
    i = x.rfind('</c:ser>') + len('</c:ser>')
    x = x[:i] + goal + x[i:]

    # 軸を表示に
    x = x.replace('<c:delete val="1"/>', '<c:delete val="0"/>')
    return x

zi = zipfile.ZipFile(SRC); zo = zipfile.ZipFile(DST, "w", zipfile.ZIP_DEFLATED)
for it in zi.infolist():
    b = zi.read(it.filename)
    if it.filename == "xl/charts/chart3.xml":
        b = patch(b.decode("utf-8")).encode("utf-8")
    zo.writestr(it, b)
zo.close(); zi.close()
print("wrote", DST)
