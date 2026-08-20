# -*- coding: utf-8 -*-
"""段2: 設定シートに「判定のしきい値」ブロック（行29〜33）を追加する。

  D31 = ◎達成 の下限 = 100（会社目標そのもの・据え置き前提）
  D32 = ○あと一歩 の下限 = 90（黄色・変更可）
  D33 = △要改善 の下限 = 80（黄色・変更可）
これ未満は ✕要支援。ピッキング/梱包の O列判定がここを参照する。
"""
import re
import zipfile

SRC, DST = "j1.xlsx", "j2.xlsx"

def inline(ref, text, s):
    return f'<c r="{ref}" s="{s}" t="inlineStr"><is><t>{text}</t></is></c>'

def patch(x):
    assert '<c r="B29"' not in x, "行29 が既にある"
    rows = (
        '<row r="29" spans="2:7" x14ac:dyDescent="0.15">'
        + inline("B29", "判定のしきい値（ピッキング・梱包シートの「判定」列）", "20") + '</row>'
        '<row r="30" spans="2:7" x14ac:dyDescent="0.15">'
        + inline("B30", "判定は会社目標（1.6分/件）に対する達成率で行います。◎の下限100は会社目標そのもの。○△の下限（黄色）は変更できます。", "24") + '</row>'
        '<row r="31" spans="2:7" x14ac:dyDescent="0.15">'
        + inline("B31", "◎ 達成", "21") + inline("C31", "の下限", "21")
        + '<c r="D31" s="21"><v>100</v></c>'
        + inline("E31", "達成率% ＝ 会社目標そのもの", "24") + '</row>'
        '<row r="32" spans="2:7" x14ac:dyDescent="0.15">'
        + inline("B32", "○ あと一歩", "21") + inline("C32", "の下限", "21")
        + '<c r="D32" s="56"><v>90</v></c>'
        + inline("E32", "達成率% ＝ ここ以上100未満が ○", "24") + '</row>'
        '<row r="33" spans="2:7" x14ac:dyDescent="0.15">'
        + inline("B33", "△ 要改善", "21") + inline("C33", "の下限", "21")
        + '<c r="D33" s="56"><v>80</v></c>'
        + inline("E33", "達成率% ＝ ここ以上90未満が △。これ未満は ✕要支援", "24") + '</row>'
    )
    m = re.search(r'<row r="27"[ >].*?</row>', x, re.S)
    assert m, "行27 が無い"
    x = x[:m.end()] + rows + x[m.end():]
    x = x.replace('<dimension ref="B2:G27"/>', '<dimension ref="B2:G33"/>', 1)
    return x

zi = zipfile.ZipFile(SRC); zo = zipfile.ZipFile(DST, "w", zipfile.ZIP_DEFLATED)
for it in zi.infolist():
    b = zi.read(it.filename)
    if it.filename == "xl/worksheets/sheet10.xml":
        b = patch(b.decode("utf-8")).encode("utf-8")
    zo.writestr(it, b)
zo.close(); zi.close()
print("wrote", DST)
