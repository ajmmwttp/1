# -*- coding: utf-8 -*-
"""段5: 印刷用の改ページを Excel の自動改ページと一致させ、③の注記枠を見出しに移す。

  1) 1ページ目（行1〜36）は高さ 760pt だが、A3 横で上下余白 0.748in（標準）だと
     印刷可能な高さは 734pt しかない。Excel の「次のページ数に合わせて印刷（1×2）」は
     手動改ページより自動改ページを優先することがあり、その場合 行34 の後ろで
     切れて ①③ のグラフが分断される。上下余白を 0.5in にすると印刷可能高さが
     770pt になり、行36 の後ろで自動改ページも一致する（2ページ目 560pt も収まる）。
  2) 「▲ もう一方の工程は実績なし」のテキスト枠（白 88% 塗り）が帯の右端
     （PK効率 128% 以上）を覆い、そこに来た人の三角が隠れる。
     → 枠を消し、③の見出し（T17）に「▲＝梱包の実績が無い人（下の帯）」を足す。
  3) 印刷用データ!BD（軸外検知）を「実際に描く座標 AW/AX」でも判定するように広げる
     （段4で梱包のみを x=0 にしたので、これで梱包のみも自動的に数えられる）。
"""
import re, sys, zipfile

SRC, DST = sys.argv[1], sys.argv[2]


def edit_formula(s, ref, old, new):
    m = re.search(r'<c r="%s"[^>]*>(?:(?!</c>).)*</c>' % ref, s, re.S)
    assert m, ref + ' が見つからない'
    blk = m.group(0)
    mf = re.search(r'(<f[^>]*>)((?:(?!</f>).)*)(</f>)', blk, re.S)
    assert mf and old in mf.group(2), '%s の式が想定と違う: %s' % (ref, (mf.group(2) if mf else blk)[:150])
    blk2 = blk[:mf.start(2)] + mf.group(2).replace(old, new) + blk[mf.end(2):]
    return s[:m.start()] + blk2 + s[m.end():]


def main():
    zin = zipfile.ZipFile(SRC)
    parts = {n: zin.read(n) for n in zin.namelist()}
    infos = {i.filename: i for i in zin.infolist()}
    order = zin.namelist()
    zin.close()

    # 1) 余白
    s = parts['xl/worksheets/sheet2.xml'].decode('utf-8')
    m = re.search(r'<pageMargins [^>]*/>', s)
    assert m and 'top="0.74803149606299213"' in m.group(0), m.group(0) if m else None
    pm = m.group(0).replace('top="0.74803149606299213"', 'top="0.5"').replace('bottom="0.74803149606299213"', 'bottom="0.5"')
    s = s[:m.start()] + pm + s[m.end():]
    print('印刷用: 上下余白 0.748in → 0.5in（1ページ目 760pt が印刷可能高さ 770pt に収まる）')

    # 2) 見出しに凡例を足す
    s = edit_formula(s, 'T17',
        '"③ 改善優先度マトリクス（全員 "&amp;COUNT(印刷用データ!$AS$3:$AS$62)&amp;"名）"',
        '"③ 改善優先度マトリクス（全員 "&amp;COUNT(印刷用データ!$AS$3:$AS$62)&amp;"名）　▲＝梱包の実績が無い人（下の帯）"')
    parts['xl/worksheets/sheet2.xml'] = s.encode('utf-8')

    d = parts['xl/drawings/drawing2.xml'].decode('utf-8')
    anchors = re.findall(r'<xdr:twoCellAnchor\b.*?</xdr:twoCellAnchor>', d, re.S)
    box = [a for a in anchors if 'name="TextBox 9007"' in a and 'もう一方の工程は実績なし' in a]
    assert len(box) == 1, 'TextBox 9007 が %d 個' % len(box)
    d = d.replace(box[0], '', 1)
    assert len(re.findall(r'<xdr:twoCellAnchor\b', d)) == len(anchors) - 1
    parts['xl/drawings/drawing2.xml'] = d.encode('utf-8')
    print('印刷用: 「▲ もう一方の工程は実績なし」の枠を削除し、③見出しに凡例を追加')

    # 3) 軸外検知を描画座標でも
    s = parts['xl/worksheets/sheet12.xml'].decode('utf-8')
    for r in (3, 35):
        s = edit_formula(s, 'BD%d' % r,
            ',$AK{r}="梱包のみ")'.format(r=r),
            ',AND(ISNUMBER($AW{r}),OR($AW{r}&lt;40,$AW{r}&gt;160)),AND(ISNUMBER($AX{r}),OR($AX{r}&lt;10,$AX{r}&gt;190)))'.format(r=r))
    parts['xl/worksheets/sheet12.xml'] = s.encode('utf-8')
    print('印刷用データ BD: 描画座標 AW/AX でも軸外を判定（共有数式ホスト 行3・行35）')

    zout = zipfile.ZipFile(DST, 'w', zipfile.ZIP_DEFLATED)
    for nm in order:
        zi = zipfile.ZipInfo(nm, date_time=infos[nm].date_time)
        zi.compress_type = infos[nm].compress_type
        zi.external_attr = infos[nm].external_attr
        zout.writestr(zi, parts[nm])
    zout.close()


main()
