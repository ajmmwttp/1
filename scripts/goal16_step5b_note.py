# -*- coding: utf-8 -*-
"""段5(修正版): 会社目標の分析を独立した注記行(63行目)として追加する。

1行の上限は実測で約165文字。既存のB61に追記すると末尾
（「1.6分に収めるには1社あたり N 件が必要です」）が切れたため、
行を分ける。数値はすべて 印刷用データ の集計セル参照で自動追随する。
"""
import re
import zipfile

import openpyxl

SRC, DST = "s4.xlsx", "s5.xlsx"
D = "印刷用データ"
NEWROW = 63

wv = openpyxl.load_workbook(SRC, data_only=True)
d = wv[D]
pk_rate, pk_per, pk_setup, pk_need, pa_rate = (
    d["BL6"].value, d["BL7"].value, d["BL8"].value, d["BL9"].value, d["BL13"].value)

CACHED = (f"■ 会社目標（工程ごと 1.6分/件）に対する達成率は ピッキング {pk_rate:.1f}％・"
          f"梱包 {pa_rate:.1f}％。ピッキングは1社あたり {pk_per:.2f} 件のため段取りだけで "
          f"{pk_setup:.1f} 秒/件かかり、1.6分に収めるには1社あたり {pk_need:.2f} 件が必要です。")
print("追加する文言（%d文字・上限約165）:" % len(CACHED))
print("  " + CACHED)

FORMULA = ('"■ 会社目標（工程ごと 1.6分/件）に対する達成率は ピッキング "'
           f'&amp;TEXT({D}!$BL$6,"0.0")&amp;"％・梱包 "&amp;TEXT({D}!$BL$13,"0.0")'
           f'&amp;"％。ピッキングは1社あたり "&amp;TEXT({D}!$BL$7,"0.00")'
           f'&amp;" 件のため段取りだけで "&amp;TEXT({D}!$BL$8,"0.0")'
           f'&amp;" 秒/件かかり、1.6分に収めるには1社あたり "&amp;TEXT({D}!$BL$9,"0.00")'
           f'&amp;" 件が必要です。"')

def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

def patch_sheet(x):
    # 注記行を1行追加（B63:AA63 を結合、書式は既存の注記と同じ s=85 / s=77）
    assert f'<row r="{NEWROW}"' not in x, f"行{NEWROW} が既にある"
    cells = (f'<c r="B{NEWROW}" s="85" t="str"><f>{FORMULA}</f><v>{esc(CACHED)}</v></c>'
             + "".join(f'<c r="{c}{NEWROW}" s="77"/>' for c in
                       ["C","D","E","F","G","H","I","J","K","L","M","N","O","P","Q","R","S",
                        "T","U","V","W","X","Y","Z","AA"]))
    row = (f'<row r="{NEWROW}" spans="2:27" ht="15.95" customHeight="1" '
           f'x14ac:dyDescent="0.35">{cells}</row>')
    m = re.search(r'<row r="62"[ >].*?</row>', x, re.S)
    assert m, "行62 が無い"
    x = x[:m.end()] + row + x[m.end():]

    mc = re.search(r'<mergeCells count="(\d+)">', x)
    n = int(mc.group(1))
    x = x.replace(mc.group(0),
                  f'<mergeCells count="{n+1}"><mergeCell ref="B{NEWROW}:AA{NEWROW}"/>', 1)
    x = x.replace('<dimension ref="B1:AA62"/>', f'<dimension ref="B1:AA{NEWROW}"/>', 1)
    return x

def patch_workbook(x):
    old = "印刷用!$A$1:$AA$62"
    assert old in x, "印刷範囲が想定と違う"
    return x.replace(old, f"印刷用!$A$1:$AA${NEWROW}", 1)

PATCH = {"xl/worksheets/sheet2.xml": patch_sheet, "xl/workbook.xml": patch_workbook}
zi = zipfile.ZipFile(SRC); zo = zipfile.ZipFile(DST, "w", zipfile.ZIP_DEFLATED)
for it in zi.infolist():
    b = zi.read(it.filename)
    fn = PATCH.get(it.filename)
    if fn:
        b = fn(b.decode("utf-8")).encode("utf-8")
    zo.writestr(it, b)
zo.close(); zi.close()
print("\nwrote", DST)
