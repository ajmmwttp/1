# -*- coding: utf-8 -*-
"""②内訳比較グラフを「改善優先の上位N名」に絞る。

領域は 列T:AA × 行5-16 = 約 5.08×3.5in で固定。ここに 50名×2本＝100本を
入れると1本3.7ptになり、氏名も値ラベルも出せない。実験の結果、上位20名
（1本 9.2pt）なら両方読めることを確認したので、その形にする。

N は実人数に応じて自動: MIN(20, 実人数)。
並びは④の表と同じ「改善優先順（達成率の低い順）」。
"""
import re
import zipfile

import openpyxl

SRC, DST = "cur3.xlsx", "out7.xlsx"
D, LAST = "印刷用データ", 62
TOPN = 20                    # ②に載せる上限人数
COLS = {"BF": "AG", "BG": "AH", "BH": "AI"}      # 出力列 -> 参照元（氏名/PK/梱包）

# --- 現データでのキャッシュ値（④の表と同じ並び＝達成率の低い順）---
_ws = openpyxl.load_workbook(SRC, data_only=True)[D]
_people = [(_ws[f"AM{r}"].value, _ws[f"AG{r}"].value, _ws[f"AH{r}"].value, _ws[f"AI{r}"].value)
           for r in range(3, LAST + 1) if _ws[f"AG{r}"].value]
_order = [p for p in sorted(_people, key=lambda p: p[0])]
print(f"実人数 {len(_order)} 名 → ②に載せるのは {min(TOPN, len(_order))} 名")

def patch_data(x):
    assert '<c r="BF' not in x, "BF 列が既にある"
    x = x.replace('<c r="BD2" s="39" t="inlineStr"><is><t>軸外</t></is></c>',
                  '<c r="BD2" s="39" t="inlineStr"><is><t>軸外</t></is></c>'
                  '<c r="BF2" s="39" t="inlineStr"><is><t>優先順 氏名</t></is></c>'
                  '<c r="BG2" s="39" t="inlineStr"><is><t>優先順 PK</t></is></c>'
                  '<c r="BH2" s="39" t="inlineStr"><is><t>優先順 梱包</t></is></c>'
                  '<c r="BI2" s="39" t="inlineStr"><is><t>目標</t></is></c>', 1)
    assert '<c r="BF2"' in x
    for k in range(1, TOPN + 1):
        r = 2 + k
        got = _order[k - 1] if k <= len(_order) else None
        cells = []
        for out, src in COLS.items():
            f = (f'IFERROR(INDEX(${src}$3:${src}${LAST},'
                 f'MATCH(SMALL($AM$3:$AM${LAST},ROW()-2),$AM$3:$AM${LAST},0)),"")')
            v = None
            if got:
                v = {"BF": got[1], "BG": got[2], "BH": got[3]}[out]
            if isinstance(v, str) or v is None:
                cells.append(f'<c r="{out}{r}" s="61" t="str"><f>{f}</f>'
                             + (f'<v>{v}</v>' if v else '<v/>') + '</c>')
            else:
                cells.append(f'<c r="{out}{r}" s="62"><f>{f}</f><v>{v!r}</v></c>')
        goal = f'IF($BF{r}="","",100)'
        cells.append(f'<c r="BI{r}" s="62"><f>{goal}</f>'
                     + (f'<v>100</v>' if got else '<v/>') + '</c>')
        m = re.search(r'(<row r="%d"[ >].*?)(</row>)' % r, x, re.S)
        assert m, f"行{r} が無い"
        x = x[:m.start(2)] + "".join(cells) + x[m.start(2):]
    x = x.replace('<dimension ref="A1:BD62"/>', '<dimension ref="A1:BI62"/>', 1)
    x = x.replace('spans="1:56"', 'spans="1:61"')
    x = x.replace('<col min="1" max="56" width="11" customWidth="1"/>',
                  '<col min="1" max="61" width="11" customWidth="1"/>', 1)
    return x

def patch_chart9(x):
    """参照を 全員50行 → 優先順20行 に付け替え、キャッシュも入れ替える。"""
    vals = {
        "BF": [_order[k][1] if k < len(_order) else None for k in range(TOPN)],
        "BG": [_order[k][2] if k < len(_order) else None for k in range(TOPN)],
        "BH": [_order[k][3] if k < len(_order) else None for k in range(TOPN)],
        "BI": [100 if k < len(_order) else None for k in range(TOPN)],
    }
    fmt = {"BF": None, "BG": '0.0"%"', "BH": '0.0"%"', "BI": "General"}
    for old, new in (("AP", "BF"), ("AQ", "BG"), ("AR", "BH"), ("AV", "BI")):
        oref, nref = f"{D}!${old}$3:${old}$52", f"{D}!${new}$3:${new}${2+TOPN}"
        assert oref in x, f"{oref} が無い"
        x = x.replace(oref, nref)
        strs = new == "BF"
        pts = "".join(f'<c:pt idx="{i}"><c:v>{v}</c:v></c:pt>'
                      for i, v in enumerate(vals[new]) if v is not None)
        tag = "str" if strs else "num"
        fc = "" if strs else f"<c:formatCode>{fmt[new]}</c:formatCode>"
        cache = f'<c:{tag}Cache>{fc}<c:ptCount val="{TOPN}"/>{pts}</c:{tag}Cache>'
        pat = re.compile(r'(<c:f>%s</c:f>)<c:(?:str|num)Cache>.*?</c:(?:str|num)Cache>'
                         % re.escape(nref), re.S)
        x, n = pat.subn(lambda m: m.group(1) + cache, x)
        assert n >= 1, f"{nref} のキャッシュ差し替え失敗"
    return x

def patch_sheet2(x):
    """②の見出しと、下の注記を新しい対象範囲に合わせる。"""
    old_h = f'"② ピッキング・梱包 内訳比較（全員 "&amp;COUNT({D}!$AS$3:$AS${LAST})&amp;"名）"'
    assert old_h in x, "②の見出しが想定と違う"
    new_h = (f'"② ピッキング・梱包 内訳比較（改善優先 上位 "&amp;'
             f'MIN({TOPN},COUNT({D}!$AS$3:$AS${LAST}))&amp;"名）"')
    x = x.replace(old_h, new_h, 1)
    x = x.replace("② ピッキング・梱包 内訳比較（全員 29名）",
                  f"② ピッキング・梱包 内訳比較（改善優先 上位 {min(TOPN,len(_order))}名）", 1)

    old_n = '"※ ①〜④ は実績のある全員 "'
    assert old_n in x, "注記が想定と違う"
    x = x.replace(old_n, '"※ ①③④ は実績のある全員 "', 1)
    ins = '&amp;" 名。'
    j = x.index('"※ ①③④ は実績のある全員 "')
    k = x.index(ins, j) + len(ins)
    x = (x[:k] + f'② は改善優先の上位 "&amp;MIN({TOPN},COUNT({D}!$AS$3:$AS${LAST}))'
         f'&amp;" 名です（全員の順位は④の表）。' + x[k:])
    x = x.replace("※ ①〜④ は実績のある全員 29 名。",
                  f"※ ①③④ は実績のある全員 29 名。② は改善優先の上位 {min(TOPN,len(_order))} 名です（全員の順位は④の表）。", 1)
    return x

PATCH = {"xl/worksheets/sheet12.xml": patch_data,
         "xl/charts/chart9.xml": patch_chart9,
         "xl/worksheets/sheet2.xml": patch_sheet2}
zi = zipfile.ZipFile(SRC); zo = zipfile.ZipFile(DST, "w", zipfile.ZIP_DEFLATED)
for it in zi.infolist():
    d = zi.read(it.filename)
    fn = PATCH.get(it.filename)
    if fn:
        d = fn(d.decode("utf-8")).encode("utf-8")
    zo.writestr(it, d)
zo.close(); zi.close()
print("wrote", DST)
