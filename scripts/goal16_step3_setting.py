# -*- coding: utf-8 -*-
"""段3: 設定シートを更新する。

1) ピッキングの段取り a を 92.1 → 56.05 秒/社 に変更
   （リストを見る 46.05秒 → 10秒。伝票を挟む 46.05秒 は据え置き）
2) 会社目標（ピッキング 1.6分/件・梱包 1.6分/件）を追記し、
   ツール側から数式で参照できるようにする
"""
import re
import zipfile

SRC, DST = "cur4.xlsx", "s3.xlsx"
A_NEW = 56.05          # = 伝票を挟む 46.05 ＋ リストを見る 10.0
GOAL_MIN = 1.6         # 会社目標 分/件（両工程とも）

def inline(ref, text, s="21"):
    return f'<c r="{ref}" s="{s}" t="inlineStr"><is><t>{text}</t></is></c>'

def patch(x):
    # --- 1) 係数の値 ---
    old = '<c r="E6" s="56"><v>92.1</v></c>'
    assert old in x, "設定!E6 が想定と違う"
    x = x.replace(old, f'<c r="E6" s="56"><v>{A_NEW}</v></c>', 1)

    # --- 内訳テキスト（共有文字列 364）を差し替え ---
    # 共有文字列は他でも使われうるので、セルをインライン文字列に置き換える
    oldg = '<c r="G6" s="24" t="s"><v>364</v></c>'
    assert oldg in x
    x = x.replace(oldg, inline("G6", "① リストを見る 10.0 ＋ ④ 伝票を挟む 46.05", "24"), 1)

    # --- 2) 会社目標セクションを追記（行23〜26）---
    assert '<c r="B23"' not in x, "行23 が既にある"
    rows = (
        f'<row r="23" spans="2:7" x14ac:dyDescent="0.15">{inline("B23","会社目標","20")}</row>'
        f'<row r="24" spans="2:7" x14ac:dyDescent="0.15">'
        f'{inline("B24","会社が定めた1件あたりの目標時間です。工程ごとにそれぞれ 1.6 分。ここは変更しない前提の数字です。","24")}</row>'
        f'<row r="25" spans="2:7" x14ac:dyDescent="0.15">'
        f'{inline("B25","工程","20")}{inline("C25","目標","20")}{inline("D25","単位","20")}'
        f'{inline("E25","秒に直すと","20")}</row>'
        f'<row r="26" spans="2:7" x14ac:dyDescent="0.15">'
        f'{inline("B26","ピッキング","21")}<c r="C26" s="56"><v>{GOAL_MIN}</v></c>'
        f'{inline("D26","分/件","21")}<c r="E26" s="56"><f>C26*60</f><v>{GOAL_MIN*60}</v></c></row>'
        f'<row r="27" spans="2:7" x14ac:dyDescent="0.15">'
        f'{inline("B27","梱包","21")}<c r="C27" s="56"><v>{GOAL_MIN}</v></c>'
        f'{inline("D27","分/件","21")}<c r="E27" s="56"><f>C27*60</f><v>{GOAL_MIN*60}</v></c></row>'
    )
    m = re.search(r'<row r="21"[ >].*?</row>', x, re.S)
    assert m, "行21 が無い"
    x = x[:m.end()] + rows + x[m.end():]
    x = x.replace('<dimension ref="B2:G21"/>', '<dimension ref="B2:G27"/>', 1)
    return x

zi = zipfile.ZipFile(SRC); zo = zipfile.ZipFile(DST, "w", zipfile.ZIP_DEFLATED)
for it in zi.infolist():
    d = zi.read(it.filename)
    if it.filename == "xl/worksheets/sheet10.xml":
        d = patch(d.decode("utf-8")).encode("utf-8")
    zo.writestr(it, d)
zo.close(); zi.close()
print("wrote", DST)
