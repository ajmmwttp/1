# -*- coding: utf-8 -*-
"""段1: 設定シートに「時給換算の単価」1,500円/時 を新設（行28、会社目標の表の直下）。"""
import re, sys, zipfile

SRC, DST = sys.argv[1], sys.argv[2]
ST = 'xl/worksheets/sheet10.xml'

ROW = ('<row r="28" spans="2:5" x14ac:dyDescent="0.15">'
       '<c r="B28" s="21" t="inlineStr"><is><t>時給換算の単価</t></is></c>'
       '<c r="C28" s="56"><v>1500</v></c>'
       '<c r="D28" s="21" t="inlineStr"><is><t>円/時</t></is></c>'
       '<c r="E28" s="21" t="inlineStr"><is><t>'
       '金額の列（ピッキング・梱包シート）はこの単価で計算します。変えると全員の金額が追随します'
       '</t></is></c></row>')


def main():
    zin = zipfile.ZipFile(SRC)
    parts = {n: zin.read(n) for n in zin.namelist()}
    infos = {i.filename: i for i in zin.infolist()}
    order = zin.namelist()
    zin.close()

    s = parts[ST].decode('utf-8')
    assert not re.search(r'<row r="28"[ />]', s), '設定の28行は空ではない'
    assert '$C$28' not in s
    anchor = re.search(r'<row r="29"[^>]*>', s)
    s = s[:anchor.start()] + ROW + s[anchor.start():]
    parts[ST] = s.encode('utf-8')
    print('設定 28行: 時給換算の単価 1,500円/時 を追加')

    zout = zipfile.ZipFile(DST, 'w', zipfile.ZIP_DEFLATED)
    for nm in order:
        zi = zipfile.ZipInfo(nm, date_time=infos[nm].date_time)
        zi.compress_type = infos[nm].compress_type
        zi.external_attr = infos[nm].external_attr
        zout.writestr(zi, parts[nm])
    zout.close()


main()
