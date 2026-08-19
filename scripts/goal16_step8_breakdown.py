# -*- coding: utf-8 -*-
"""段8: 会社目標に対する未達を「速さ由来」と「リスト構成由来」に分けて示す。

  実測(秒/件) − 標準(秒/件)  = 速さ由来       … 本人の改善余地
  標準(秒/件) − 目標96秒     = リスト構成由来 … 1社あたり件数で決まる分
"""
import re
import zipfile

import openpyxl

SRC, DST = "s5.xlsx", "s8.xlsx"
D = "印刷用データ"

wv = openpyxl.load_workbook(SRC, data_only=True)
st, d = wv["設定"], wv[D]
A, B, GOAL_SEC = st["E6"].value, st["E7"].value, st["C26"].value * 60
pk_cnt, pk_comp, pk_act = d["BL3"].value, d["BL4"].value, d["BL5"].value

actual = pk_act * 60 / pk_cnt                 # 実測 秒/件
std    = A * pk_comp / pk_cnt + B             # 標準 秒/件
speed  = actual - std                         # 速さ由来
mix    = std - GOAL_SEC                       # リスト構成由来
print("=== ピッキングの未達内訳（Python 計算）===")
print(f"  実測 {actual:.2f} 秒/件 − 目標 {GOAL_SEC:.0f} 秒 = 未達 {actual-GOAL_SEC:.2f} 秒/件")
print(f"    速さ由来       = 実測 {actual:.2f} − 標準 {std:.2f} = {speed:.2f} 秒 "
      f"({speed/(actual-GOAL_SEC)*100:.0f}%)")
print(f"    リスト構成由来 = 標準 {std:.2f} − 目標 {GOAL_SEC:.0f} = {mix:.2f} 秒 "
      f"({mix/(actual-GOAL_SEC)*100:.0f}%)")

NEW = {
    14: ("PK 実測(秒/件)",      f'IF($BL$3=0,"",$BL$5*60/$BL$3)',                    actual),
    15: ("PK 標準(秒/件)",      f'IF($BL$3=0,"",設定!$E$6*$BL$4/$BL$3+設定!$E$7)',    std),
    16: ("PK 未達 速さ由来",    f'IF($BL$3=0,"",$BL$14-$BL$15)',                     speed),
    17: ("PK 未達 構成由来",    f'IF($BL$3=0,"",$BL$15-設定!$E$26)',                 mix),
    18: ("PK 未達 合計",        f'IF($BL$3=0,"",$BL$14-設定!$E$26)',                 actual-GOAL_SEC),
}

CACHED = (f"■ 会社目標（工程ごと 1.6分/件）に対する達成率は ピッキング {d['BL6'].value:.1f}％・"
          f"梱包 {d['BL13'].value:.1f}％。ピッキングの未達 {actual-GOAL_SEC:.1f} 秒/件の内訳は、"
          f"速さ由来 {speed:.1f} 秒・リスト構成由来 {mix:.1f} 秒"
          f"（1社あたり {d['BL7'].value:.2f} 件のため。1.6分には {d['BL9'].value:.2f} 件が必要）。")
print(f"\n注記（{len(CACHED)}文字・上限約165）:\n  {CACHED}")

FORMULA = ('"■ 会社目標（工程ごと 1.6分/件）に対する達成率は ピッキング "'
           f'&amp;TEXT({D}!$BL$6,"0.0")&amp;"％・梱包 "&amp;TEXT({D}!$BL$13,"0.0")'
           f'&amp;"％。ピッキングの未達 "&amp;TEXT({D}!$BL$18,"0.0")&amp;" 秒/件の内訳は、速さ由来 "'
           f'&amp;TEXT({D}!$BL$16,"0.0")&amp;" 秒・リスト構成由来 "&amp;TEXT({D}!$BL$17,"0.0")'
           f'&amp;" 秒（1社あたり "&amp;TEXT({D}!$BL$7,"0.00")&amp;" 件のため。1.6分には "'
           f'&amp;TEXT({D}!$BL$9,"0.00")&amp;" 件が必要）。"')

def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

def patch_data(x):
    assert '<c r="BL14"' not in x
    for r, (label, f, v) in NEW.items():
        cells = (f'<c r="BK{r}" s="39" t="inlineStr"><is><t>{label}</t></is></c>'
                 f'<c r="BL{r}" s="62"><f>{f}</f><v>{v!r}</v></c>')
        m = re.search(r'(<row r="%d"[ >].*?)(</row>)' % r, x, re.S)
        assert m, f"行{r} が無い"
        x = x[:m.start(2)] + cells + x[m.start(2):]
    return x

def patch_sheet(x):
    m = re.search(r'<c r="B63" s="85" t="str"><f>.*?</f><v>.*?</v></c>', x, re.S)
    assert m, "B63 が見つからない"
    return x.replace(m.group(0),
                     f'<c r="B63" s="85" t="str"><f>{FORMULA}</f><v>{esc(CACHED)}</v></c>', 1)

PATCH = {"xl/worksheets/sheet12.xml": patch_data, "xl/worksheets/sheet2.xml": patch_sheet}
zi = zipfile.ZipFile(SRC); zo = zipfile.ZipFile(DST, "w", zipfile.ZIP_DEFLATED)
for it in zi.infolist():
    b = zi.read(it.filename)
    fn = PATCH.get(it.filename)
    if fn:
        b = fn(b.decode("utf-8")).encode("utf-8")
    zo.writestr(it, b)
zo.close(); zi.close()
print("\nwrote", DST)
