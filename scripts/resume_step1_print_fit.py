# -*- coding: utf-8 -*-
"""段1: 印刷用シートの「A3 横・幅1ページ×縦2ページ」設定を復元する。

判定4区分化（d157892）以降のベースに使った Excel 保存版では、印刷用シートの
<sheetPr><pageSetUpPr fitToPage="1"/></sheetPr> が失われ、pageSetup が
scale="120" fitToHeight="2" だけになっていた。fitToPage が無いと Excel は
fitToWidth/fitToHeight を無視して「拡大縮小 120%」で印刷するため、
A3 横 2 ページの設計（行36の改ページ・印刷タイトル行4）が成立しない
（LibreOffice で描画すると 2×3 の 6 ページに割れる）。

  - sheetPr/pageSetUpPr fitToPage="1" を復元
  - pageSetup に fitToWidth="1" を明示（fitToHeight="2" はそのまま）
  - scale="120" と r:id（プリンタ設定）は Excel が書いたものなので残す

ピッキング・梱包シートは fitToPage="1" が残っているので触らない。
"""
import re, sys, zipfile

SRC, DST = sys.argv[1], sys.argv[2]
PD = 'xl/worksheets/sheet2.xml'


def main():
    zin = zipfile.ZipFile(SRC)
    parts = {n: zin.read(n) for n in zin.namelist()}
    infos = {i.filename: i for i in zin.infolist()}
    order = zin.namelist()
    zin.close()

    s = parts[PD].decode('utf-8')
    assert '<sheetPr' not in s, '印刷用に sheetPr が既にある'
    s = s.replace('<dimension ', '<sheetPr><pageSetUpPr fitToPage="1"/></sheetPr><dimension ', 1)
    assert '<sheetPr><pageSetUpPr fitToPage="1"/></sheetPr><dimension ' in s
    print('印刷用: sheetPr/pageSetUpPr fitToPage="1" を復元')

    m = re.search(r'<pageSetup [^>]*/>', s)
    assert m, 'pageSetup がない'
    ps = m.group(0)
    assert 'fitToHeight="2"' in ps and 'paperSize="8"' in ps and 'orientation="landscape"' in ps, ps
    assert 'fitToWidth' not in ps
    ps2 = ps.replace('fitToHeight="2"', 'fitToWidth="1" fitToHeight="2"', 1)
    s = s[:m.start()] + ps2 + s[m.end():]
    print('印刷用: pageSetup %s' % ps2)

    parts[PD] = s.encode('utf-8')
    zout = zipfile.ZipFile(DST, 'w', zipfile.ZIP_DEFLATED)
    for nm in order:
        zi = zipfile.ZipInfo(nm, date_time=infos[nm].date_time)
        zi.compress_type = infos[nm].compress_type
        zi.external_attr = infos[nm].external_attr
        zout.writestr(zi, parts[nm])
    zout.close()


main()
