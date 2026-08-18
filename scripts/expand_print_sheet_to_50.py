# -*- coding: utf-8 -*-
"""「印刷用」シートを 50 名分に拡張する。

方針（利用者の選択）:
  - 表は 50 行固定（シート行 5..54）
  - A3 横 1 ページ維持のため、データ行の高さを 21pt → 13.5pt に圧縮
  - グラフ①②③ は静的 50 行参照（定義名は使わない）

openpyxl では往復させない（グラフ16点・図形3点・外部リンクを失うため）。
必要なパートだけ直接書き換えて再梱包する。
"""
import re
import zipfile

SRC, DST = "out.xlsx", "out50.xlsx"

N          = 50      # 表の行数
FIRST      = 5       # 表の先頭行
OLD_LAST   = 33      # 旧・表の最終行 (29名)
NEW_LAST   = FIRST + N - 1          # 54
SHIFT      = NEW_LAST - OLD_LAST    # 21 行下にずれる
OLD_TAIL   = list(range(34, 42))    # 旧 34..41
ROW_H      = "13.5"
SRC_LAST   = 62      # 印刷用データ の最終行
CHART_LAST = 3 + N - 1              # 52 : グラフ参照の最終行
BLANK_DXF  = 7       # 追加する dxf（空欄行用・白塗り）の番号

D = "印刷用データ"

# ---------------------------------------------------------------- helpers
def col_cells(r, cols, style):
    return "".join(f'<c r="{c}{r}" s="{style}"/>' for c in cols)

def idx_formula(k, col):
    return (f'IFERROR(INDEX({D}!${col}$3:${col}${SRC_LAST},'
            f'MATCH(SMALL({D}!$AM$3:$AM${SRC_LAST},{k}),{D}!$AM$3:$AM${SRC_LAST},0)),"")')

def new_row(r, k):
    """k 番目（順位 k）の表データ行。29名しか居ないので値は空。"""
    m = (f'IFERROR(IF(SMALL({D}!$AM$3:$AM${SRC_LAST},{k})&gt;0,{k},""),"")')
    return (
        f'<row r="{r}" spans="2:27" ht="{ROW_H}" customHeight="1" x14ac:dyDescent="0.15">'
        + col_cells(r, ["B","C","D","E","F","G","H","I","J","K","L"], "63")
        + f'<c r="M{r}" s="38" t="str"><f>{m}</f><v/></c>'
        + f'<c r="N{r}" s="34" t="str"><f>{idx_formula(k,"AG")}</f><v/></c>'
        + f'<c r="O{r}" s="34" t="str"><f>{idx_formula(k,"AK")}</f><v/></c>'
        + f'<c r="P{r}" s="35" t="str"><f>{idx_formula(k,"AJ")}</f><v/></c>'
        + f'<c r="Q{r}" s="36" t="str"><f t="shared" si="0"/><v/></c>'
        + f'<c r="R{r}" s="37" t="str"><f>{idx_formula(k,"AL")}</f><v/></c>'
        + "</row>"
    )

def renumber_row(xml, old, new):
    """行 old を new に付け替える（行番号とセル参照の両方）。"""
    xml = re.sub(r'(<row\b[^>]*?\br=")%d(")' % old, r'\g<1>%d\g<2>' % new, xml, count=1)
    xml = re.sub(r'(<c r="[A-Z]{1,3})%d(")' % old, r'\g<1>%d\g<2>' % new, xml)
    return xml

# ---------------------------------------------------------------- sheet2
def patch_sheet(x):
    orig = x

    # 1) 表の既存 29 行: 行高 21 → 13.5
    for r in range(FIRST, OLD_LAST + 1):
        pat = r'(<row r="%d" spans="2:27" ht=")21(")' % r
        assert re.search(pat, x), f"row {r} の ht=21 が見つからない"
        x = re.sub(pat, r'\g<1>%s\g<2>' % ROW_H, x, count=1)

    # 2) ③見出しを T19 → T26 へ移動（行19から T..AA を取り除く）
    head_cells = re.search(r'<c r="T19"[^>]*>.*?</c>(?:<c r="(?:U|V|W|X|Y|Z|AA)19"[^>]*/>)+', x, re.S)
    assert head_cells, "T19..AA19 が見つからない"
    x = x.replace(head_cells.group(0), "", 1)

    t26 = ('<c r="T26" s="86" t="str"><f>'
           f'"③ 改善優先度マトリクス（両工程 "&amp;COUNT({D}!$N$3:$N${SRC_LAST})&amp;"名）"'
           '</f><v>③ 改善優先度マトリクス（両工程 19名）</v></c>'
           + col_cells(26, ["U","V","W","X","Y","Z","AA"], "77"))
    x = re.sub(r'(<c r="R26"[^>]*>.*?</c>)(</row>)', r'\1%s\2' % t26.replace('\\', '\\\\'), x, count=1, flags=re.S)
    assert '<c r="T26"' in x, "T26 の挿入に失敗"

    # 3) 旧 34..41 を 55..62 へ（下から順に、衝突を避ける）
    for old in reversed(OLD_TAIL):
        x = renumber_row(x, old, old + SHIFT)

    # 4) 新しい表の行 34..54（順位 30..50）を、行33の直後に挿入
    add = "".join(new_row(FIRST + i, i + 1) for i in range(OLD_LAST - FIRST + 1, N))
    m33 = re.search(r'<row r="33"[ >].*?</row>', x, re.S)
    assert m33, "row 33 が見つからない"
    x = x[:m33.end()] + add + x[m33.end():]

    # 5) 共有数式 Q5:Q33 → Q5:Q54
    assert 'ref="Q5:Q33"' in x
    x = x.replace('ref="Q5:Q33"', f'ref="Q{FIRST}:Q{NEW_LAST}"', 1)

    # 6) 条件付き書式 M5:M33 → M5:M54
    assert 'sqref="M5:M33"' in x
    x = x.replace('sqref="M5:M33"', f'sqref="M{FIRST}:M{NEW_LAST}"', 1)

    # 6b) 空欄行の順位バッジは無地に（既定の s=38 は緑＝目標達成のため誤読を招く）。
    #     実データが 30..50 位まで入れば通常どおり色が付く。
    x = x.replace('<cfRule type="expression" dxfId="6" priority="1">',
                  '<cfRule type="expression" dxfId="6" priority="2">', 1)
    blank = (f'<conditionalFormatting sqref="M{FIRST}:M{NEW_LAST}">'
             f'<cfRule type="expression" dxfId="{BLANK_DXF}" priority="1" stopIfTrue="1">'
             f'<formula>$M{FIRST}=""</formula></cfRule></conditionalFormatting>')
    i = x.index('<conditionalFormatting ')
    x = x[:i] + blank + x[i:]

    # 7) 結合セル
    x = x.replace('<mergeCell ref="B41:AA41"/>', '<mergeCell ref="B62:AA62"/>', 1)
    x = x.replace('<mergeCell ref="B40:AA40"/>', '<mergeCell ref="B61:AA61"/>', 1)
    x = x.replace('<mergeCell ref="T19:AA19"/>', '<mergeCell ref="T26:AA26"/>', 1)

    # 8) 見出しの人数をベタ書き → 数式（B41 と同じ方式で自動追随）
    heads = {
        'B3':  ('64', f'"① 個人別 総合達成率（全員 "&amp;COUNT({D}!$AS$3:$AS${SRC_LAST})&amp;"名）"',
                '① 個人別 総合達成率（全員 29名）'),
        'M3':  ('64', f'"④ 改善優先順位（全員 "&amp;COUNT({D}!$AS$3:$AS${SRC_LAST})&amp;"名）"',
                '④ 改善優先順位（全員 29名）'),
        'T3':  ('86', f'"② ピッキング・梱包 内訳比較（両工程 "&amp;COUNT({D}!$Q$3:$Q${SRC_LAST})&amp;"名）"',
                '② ピッキング・梱包 内訳比較（両工程 19名）'),
    }
    for ref, (style, f, cached) in heads.items():
        pat = r'<c r="%s" s="%s" t="s"><v>\d+</v></c>' % (ref, style)
        assert re.search(pat, x), f"{ref} が想定の形ではない"
        x = re.sub(pat, f'<c r="{ref}" s="{style}" t="str"><f>{f}</f><v>{cached}</v></c>', x, count=1)

    # 9) dimension
    x = x.replace('<dimension ref="B1:AA41"/>', f'<dimension ref="B1:AA{OLD_TAIL[-1]+SHIFT}"/>', 1)

    assert x != orig
    return x

# ---------------------------------------------------------------- drawing2
def patch_drawing(x):
    """図形のアンカーを新レイアウトへ。値は 0 始まりの行番号。"""
    moves = [
        # (from_row, to_row) → (new_from, new_to)
        ((3, 33),  (3, 54)),    # ① 達成率グラフ: 表と同じ高さに伸ばす
        ((3, 18),  (3, 25)),    # ② 内訳比較
        ((19, 39), (26, 54)),   # ③ 散布図
        ((21, 22), (29, 30)),   # 散布図 上側の象限ラベル ×2
        ((34, 35), (47, 48)),   # 散布図 下側の象限ラベル ×2
        ((34, 39), (55, 60)),   # 読み取り方ボックス
    ]
    anchors = re.findall(r'<xdr:twoCellAnchor\b.*?</xdr:twoCellAnchor>', x, re.S)
    assert len(anchors) == 8, f"アンカー数が想定外: {len(anchors)}"
    out = x
    for a in anchors:
        fr = int(re.search(r'<xdr:from>.*?<xdr:row>(\d+)</xdr:row>', a, re.S).group(1))
        to = int(re.search(r'<xdr:to>.*?<xdr:row>(\d+)</xdr:row>', a, re.S).group(1))
        hit = [n for (o, n) in moves if o == (fr, to)]
        assert hit, f"未対応のアンカー from={fr} to={to}"
        nf, nt = hit[0]
        new = re.sub(r'(<xdr:from>.*?<xdr:row>)\d+(</xdr:row>)', r'\g<1>%d\g<2>' % nf, a, count=1, flags=re.S)
        new = re.sub(r'(<xdr:to>.*?<xdr:row>)\d+(</xdr:row>)',   r'\g<1>%d\g<2>' % nt, new, count=1, flags=re.S)
        out = out.replace(a, new, 1)
    return out

print("script written")

def patch_styles(x):
    """空欄の順位バッジ用に「白塗り」の dxf を1つ追加する。"""
    m = re.search(r'<dxfs count="(\d+)">', x)
    assert m and int(m.group(1)) == BLANK_DXF, f"dxfs count が想定外: {m.group(1) if m else None}"
    x = x.replace(m.group(0), f'<dxfs count="{BLANK_DXF + 1}">', 1)
    dxf = ('<dxf><fill><patternFill patternType="solid">'
           '<fgColor rgb="FFFFFFFF"/><bgColor rgb="FFFFFFFF"/></patternFill></fill></dxf>')
    return x.replace('</dxfs>', dxf + '</dxfs>', 1)

# ---------------------------------------------------------------- charts
def set_ptcount(block, n):
    """cat/val/xVal/yVal ブロック直下のキャッシュ ptCount だけを書き換える。"""
    return re.sub(r'(<c:(?:str|num)Cache><c:formatCode>[^<]*</c:formatCode><c:ptCount val=")\d+(")',
                  r'\g<1>%d\g<2>' % n,
                  re.sub(r'(<c:(?:str|num)Cache><c:ptCount val=")\d+(")',
                         r'\g<1>%d\g<2>' % n, block, count=1),
                  count=1)

def patch_chart(x, ranges):
    """ranges: {'AP': old_last, ...} 列 → 旧の最終行。3:old → 3:CHART_LAST に伸ばす。"""
    for col, old_last in ranges.items():
        old = f'{D}!${col}$3:${col}${old_last}'
        new = f'{D}!${col}$3:${col}${CHART_LAST}'
        assert old in x, f"{old} が見つからない"
        x = x.replace(old, new)
    # 該当する cat/val/xVal/yVal のキャッシュ ptCount を 50 に
    def fix(m):
        block = m.group(0)
        if f'${CHART_LAST}</c:f>' in block:
            return set_ptcount(block, N)
        return block
    x = re.sub(r'<c:(cat|val|xVal|yVal)>.*?</c:\1>', fix, x, flags=re.S)
    return x

DLBL_TMPL = (
    '<c:dLbl><c:idx val="{i}"/><c:tx><c:strRef><c:f>{D}!$K${row}</c:f></c:strRef></c:tx>'
    '<c:spPr/><c:txPr><a:bodyPr/><a:lstStyle/><a:p><a:pPr><a:defRPr sz="900"/></a:pPr>'
    '<a:endParaRPr lang="ja-JP"/></a:p></c:txPr><c:dLblPos val="r"/>'
    '<c:showLegendKey val="0"/><c:showVal val="0"/><c:showCatName val="0"/>'
    '<c:showSerName val="0"/><c:showPercent val="0"/><c:showBubbleSize val="0"/>'
    '<c:extLst><c:ext uri="{{CE6537A1-D6FC-4f65-9D91-7224C49458BB}}" '
    'xmlns:c15="http://schemas.microsoft.com/office/drawing/2012/chart">'
    '<c15:dlblFieldTable><c15:dlblFTEntry>'
    '<c15:txfldGUID>{{{guid}}}</c15:txfldGUID><c15:f>{D}!$K${row}</c15:f>'
    '</c15:dlblFTEntry></c15:dlblFieldTable><c15:showDataLabelsRange val="0"/></c:ext>'
    '<c:ext uri="{{C3380CC4-5D6E-409C-BE32-E72D297353CC}}" '
    'xmlns:c16="http://schemas.microsoft.com/office/drawing/2014/chart">'
    '<c16:uniqueId val="{{{uid:08X}-9A3E-489E-9801-55C342B48382}}"/></c:ext></c:extLst></c:dLbl>'
)

def patch_scatter_labels(x, old_n=19):
    """散布図の点名ラベルを old_n 個 → N 個に増やす。"""
    assert x.count('<c:dLbl>') == old_n
    tail = x.rfind('</c:dLbl>') + len('</c:dLbl>')
    add = "".join(
        DLBL_TMPL.format(i=i, row=3 + i, D=D,
                         guid="PR%06d-0000-4000-8000-%012d" % (i, i),
                         uid=i)
        for i in range(old_n, N)
    )
    x = x[:tail] + add + x[tail:]
    assert x.count('<c:dLbl>') == N
    return x

# ---------------------------------------------------------------- package
DROP = {"xl/calcChain.xml"}

zin = zipfile.ZipFile(SRC)
zout = zipfile.ZipFile(DST, "w", zipfile.ZIP_DEFLATED)
seen = set()
for item in zin.infolist():
    name = item.filename
    if name in DROP:
        continue
    data = zin.read(name)
    if name == "xl/worksheets/sheet2.xml":
        data = patch_sheet(data.decode("utf-8")).encode("utf-8")
    elif name == "xl/styles.xml":
        data = patch_styles(data.decode("utf-8")).encode("utf-8")
    elif name == "xl/drawings/drawing2.xml":
        data = patch_drawing(data.decode("utf-8")).encode("utf-8")
    elif name == "xl/charts/chart8.xml":
        data = patch_chart(data.decode("utf-8"), {"AP": 31, "AS": 31, "AV": 31}).encode("utf-8")
    elif name == "xl/charts/chart9.xml":
        data = patch_chart(data.decode("utf-8"), {"R": 21, "S": 21, "T": 21, "U": 21}).encode("utf-8")
    elif name == "xl/charts/chart10.xml":
        c = patch_chart(data.decode("utf-8"), {"L": 21, "M": 21})
        data = patch_scatter_labels(c).encode("utf-8")
    elif name == "xl/workbook.xml":
        s = data.decode("utf-8")
        old = "印刷用!$A$1:$AA$41"
        assert old in s
        data = s.replace(old, f"印刷用!$A$1:$AA${OLD_TAIL[-1]+SHIFT}", 1).encode("utf-8")
    elif name == "xl/_rels/workbook.xml.rels":
        data = re.sub(r'<Relationship[^>]*calcChain[^>]*/>', '', data.decode("utf-8")).encode("utf-8")
    elif name == "[Content_Types].xml":
        data = re.sub(r'<Override[^>]*calcChain[^>]*/>', '', data.decode("utf-8")).encode("utf-8")
    zout.writestr(item, data)
    seen.add(name)
zin.close(); zout.close()

# 共有文字列の count を実際の参照数に合わせ直す
z = zipfile.ZipFile(DST)
refs = sum(z.read(n).decode("utf-8").count('t="s"') for n in z.namelist()
           if n.startswith("xl/worksheets/sheet"))
sst = z.read("xl/sharedStrings.xml").decode("utf-8")
z.close()
cur = int(re.search(r'<sst[^>]*\bcount="(\d+)"', sst).group(1))
if cur != refs:
    new_sst = re.sub(r'(<sst[^>]*\bcount=")\d+(")', r'\g<1>%d\g<2>' % refs, sst, count=1)
    tmp = DST + ".t"
    zi = zipfile.ZipFile(DST); zo = zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED)
    for it in zi.infolist():
        zo.writestr(it, new_sst.encode("utf-8") if it.filename == "xl/sharedStrings.xml" else zi.read(it.filename))
    zi.close(); zo.close()
    import os; os.replace(tmp, DST)
    print(f"sharedStrings count {cur} → {refs}")

print("wrote", DST)
