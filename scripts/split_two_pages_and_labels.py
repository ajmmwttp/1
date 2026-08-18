# -*- coding: utf-8 -*-
"""印刷用シートを A3 横 2 ページ構成に戻し、③散布図の氏名を全点表示する。

利用者の選択:
  - ④の表: 行高を 21pt に戻して 2 ページに分割（游ゴシック 10pt の切れも解消）
  - ③の散布図: 氏名ラベルを小さくして全 50 点に表示

1ページ目 = 行1-36（①②③のグラフ＋表 順位1-32）
2ページ目 = 行37-62（表 順位33-50＋読み取り方＋注記）
"""
import re
import zipfile

SRC, DST = "out50.xlsx", "out2p.xlsx"
BREAK   = 36        # 1ページ目の最終行
ROW_H   = "21"      # データ行の高さ（游ゴシック10ptが切れない高さ）
LBL_SZ  = "600"     # ③の氏名ラベル 6pt

# ---------------------------------------------------------------- sheet2
def patch_sheet(x):
    # 1) データ行 5-54 の高さを 13.5 → 21 に戻す
    n = 0
    for r in range(5, 55):
        pat = r'(<row r="%d" spans="2:27" ht=")13\.5(")' % r
        assert re.search(pat, x), f"row {r} の ht=13.5 が無い"
        x = re.sub(pat, r'\g<1>%s\g<2>' % ROW_H, x, count=1)
        n += 1
    assert n == 50

    # 2) ③見出しを T26 → T17 へ（1ページ目に収めるため）
    blk = re.search(r'<c r="T26"[^>]*>.*?</c>(?:<c r="(?:U|V|W|X|Y|Z|AA)26"[^>]*/>)+', x, re.S)
    assert blk, "T26..AA26 が無い"
    moved = re.sub(r'(<c r="[A-Z]{1,3})26(")', r'\g<1>17\g<2>', blk.group(0))
    x = x.replace(blk.group(0), "", 1)
    x = re.sub(r'(<c r="R17"[^>]*>.*?</c>)(</row>)', lambda m: m.group(1) + moved + m.group(2),
               x, count=1, flags=re.S)
    assert '<c r="T17"' in x, "T17 の挿入に失敗"
    x = x.replace('<mergeCell ref="T26:AA26"/>', '<mergeCell ref="T17:AA17"/>', 1)

    # 3) 縦は 2 ページ（横は 1 ページのまま）
    assert 'fitToHeight="1"' in x
    x = x.replace('fitToHeight="1"', 'fitToHeight="2"', 1)

    # 4) 改ページを行 BREAK の後ろに明示（グラフを分断しない位置）
    assert '<rowBreaks' not in x
    brk = (f'<rowBreaks count="1" manualBreakCount="1">'
           f'<brk id="{BREAK}" max="16383" man="1"/></rowBreaks>')
    i = x.index('<drawing ')          # rowBreaks は pageSetup の後・drawing の前
    x = x[:i] + brk + x[i:]
    return x

# ---------------------------------------------------------------- drawing2
def patch_drawing(x):
    moves = {
        (3, 54):  (4, 36),    # ① 達成率     → 行5-36（印刷タイトル行4を避ける）
        (3, 25):  (4, 16),    # ② 内訳比較   → 行5-16
        (26, 54): (17, 36),   # ③ 散布図     → 行18-36（見出しは行17）
        (29, 30): (19, 20),   # ③ 上側の象限ラベル ×2
        (31, 32): (31, 32),   # （下側ラベルは移動後の位置と同じ）
        (47, 48): (31, 32),   # ③ 下側の象限ラベル ×2
        (55, 60): (55, 60),   # 読み取り方ボックス（据え置き）
    }
    anchors = re.findall(r'<xdr:twoCellAnchor\b.*?</xdr:twoCellAnchor>', x, re.S)
    assert len(anchors) == 8, f"アンカー数が想定外: {len(anchors)}"
    for a in anchors:
        fr = int(re.search(r'<xdr:from>.*?<xdr:row>(\d+)</xdr:row>', a, re.S).group(1))
        to = int(re.search(r'<xdr:to>.*?<xdr:row>(\d+)</xdr:row>',   a, re.S).group(1))
        assert (fr, to) in moves, f"未対応のアンカー from={fr} to={to}"
        nf, nt = moves[(fr, to)]
        new = re.sub(r'(<xdr:from>.*?<xdr:row>)\d+(</xdr:row>)', r'\g<1>%d\g<2>' % nf, a, count=1, flags=re.S)
        new = re.sub(r'(<xdr:to>.*?<xdr:row>)\d+(</xdr:row>)',   r'\g<1>%d\g<2>' % nt, new, count=1, flags=re.S)
        x = x.replace(a, new, 1)
    return x

# ---------------------------------------------------------------- chart10
def patch_scatter(x):
    """氏名ラベルを 9pt → 6pt にし、追加した点は表示位置を散らす。"""
    dlbls = re.findall(r'<c:dLbl>.*?</c:dLbl>', x, re.S)
    assert len(dlbls) == 50, f"dLbl 数が想定外: {len(dlbls)}"
    POS = ["r", "t", "l", "b"]
    for a in dlbls:
        idx = int(re.search(r'<c:idx val="(\d+)"/>', a).group(1))
        new = a.replace('sz="900"', f'sz="{LBL_SZ}"')
        if idx >= 19:   # 今回追加した点は位置を循環させて重なりを減らす
            new = re.sub(r'<c:dLblPos val="[a-z]+"/>',
                         f'<c:dLblPos val="{POS[idx % len(POS)]}"/>', new, count=1)
        x = x.replace(a, new, 1)
    assert 'sz="900"' not in re.search(r'<c:dLbls>.*?</c:dLbls>', x, re.S).group(0)
    return x

def patch_bar(x):
    """①のカテゴリ軸フォントを 10pt → 8pt に。
    行5-36 = 672pt を 50 名で割ると 13.4pt/件。10pt では収まらず 1つおきに
    間引かれる。8pt なら全員分が並ぶことを実測で確認した（9pt では不足、
    7pt まで下げると値軸ラベルが斜めになるため 8pt が最適）。"""
    m = re.search(r'<c:catAx>.*?</c:catAx>', x, re.S)
    assert m and 'sz="1000"' in m.group(0), "①のカテゴリ軸が想定と違う"
    return x.replace(m.group(0), m.group(0).replace('sz="1000"', 'sz="800"', 1), 1)

# ---------------------------------------------------------------- workbook
def patch_workbook(x):
    """2ページ目にも表の見出し行が出るよう、印刷タイトルに行4を指定。"""
    assert 'Print_Titles' not in x
    anchor = '<definedName name="_xlnm.Print_Area" localSheetId="1">印刷用!$A$1:$AA$62</definedName>'
    assert anchor in x
    titles = '<definedName name="_xlnm.Print_Titles" localSheetId="1">印刷用!$4:$4</definedName>'
    return x.replace(anchor, anchor + titles, 1)

# ---------------------------------------------------------------- package
PATCH = {
    "xl/worksheets/sheet2.xml": patch_sheet,
    "xl/drawings/drawing2.xml": patch_drawing,
    "xl/charts/chart8.xml":     patch_bar,
    "xl/charts/chart10.xml":    patch_scatter,
    "xl/workbook.xml":          patch_workbook,
}
zin = zipfile.ZipFile(SRC); zout = zipfile.ZipFile(DST, "w", zipfile.ZIP_DEFLATED)
for item in zin.infolist():
    data = zin.read(item.filename)
    fn = PATCH.get(item.filename)
    if fn:
        data = fn(data.decode("utf-8")).encode("utf-8")
    zout.writestr(item, data)
zin.close(); zout.close()
print("wrote", DST)
