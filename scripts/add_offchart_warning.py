# -*- coding: utf-8 -*-
"""③の軸範囲(10〜190%)の外にいる人を検知して注記に出す。

軸を自動にすると帯の位置（12〜37 という絶対値）がずれて成立しないため、
軸は固定のまま「図に出ていない人が何名いるか」を数式で知らせる方式にする。
"""
import re
import zipfile

SRC, DST = "base.xlsx", "out5.xlsx"
D, LAST = "印刷用データ", 62
LO, HI = 10, 190          # ③ の軸範囲

import openpyxl
_ws = openpyxl.load_workbook(SRC, data_only=True)[D]
def _cached(r):
    """現データでの軸外判定（0/1）。人が居ない行は空文字。"""
    if not _ws[f"AG{r}"].value:
        return None
    def out(v):
        return isinstance(v, (int, float)) and not (LO <= v <= HI)
    return 1 if (out(_ws[f"AH{r}"].value) or out(_ws[f"AI{r}"].value)) else 0

def patch_data(x):
    assert '<c r="BD' not in x, "BD 列が既にある"
    x = x.replace('<c r="AY2" s="39" t="inlineStr"><is><t>片方通番</t></is></c>',
                  '<c r="AY2" s="39" t="inlineStr"><is><t>片方通番</t></is></c>'
                  '<c r="BD2" s="39" t="inlineStr"><is><t>軸外</t></is></c>', 1)
    assert '<c r="BD2"' in x
    for r in range(3, LAST + 1):
        f = (f'IF($AG{r}="","",IF(OR('
             f'AND(ISNUMBER($AH{r}),OR($AH{r}&lt;{LO},$AH{r}&gt;{HI})),'
             f'AND(ISNUMBER($AI{r}),OR($AI{r}&lt;{LO},$AI{r}&gt;{HI}))),1,0))')
        m = re.search(r'(<row r="%d"[ >].*?)(</row>)' % r, x, re.S)
        assert m, f"行{r} が無い"
        v = _cached(r)
        cell = (f'<c r="BD{r}" s="62"><f>{f}</f><v>{v}</v></c>' if v is not None
                else f'<c r="BD{r}" s="62" t="str"><f>{f}</f><v/></c>')
        x = x[:m.start(2)] + cell + x[m.start(2):]
    x = x.replace('<dimension ref="A1:BC62"/>', '<dimension ref="A1:BD62"/>', 1)
    x = x.replace('spans="1:55"', 'spans="1:56"')
    x = x.replace('<col min="1" max="55" width="11" customWidth="1"/>',
                  '<col min="1" max="56" width="11" customWidth="1"/>', 1)
    return x

def patch_sheet2(x):
    tail = '&amp;" 名は、下の帯に灰色の三角で並べています。出典: 2026年4月 実績。"'
    assert tail in x, "注記の数式が想定と違う"
    warn = (f'&amp;IF(SUM({D}!BD3:BD{LAST})&gt;0,'
            f'"　【要確認】③ は縦横とも {LO}〜{HI}% の範囲で描いています。'
            f'範囲外のため図に出ていない人が "&amp;SUM({D}!BD3:BD{LAST})&amp;" 名います。","")')
    x = x.replace(tail, tail.replace('。"', '。"') + warn, 1)
    assert warn in x
    return x

PATCH = {"xl/worksheets/sheet12.xml": patch_data, "xl/worksheets/sheet2.xml": patch_sheet2}
zi = zipfile.ZipFile(SRC); zo = zipfile.ZipFile(DST, "w", zipfile.ZIP_DEFLATED)
for it in zi.infolist():
    d = zi.read(it.filename)
    fn = PATCH.get(it.filename)
    if fn:
        d = fn(d.decode("utf-8")).encode("utf-8")
    zo.writestr(it, d)
zo.close(); zi.close()
print("wrote", DST)
