# -*- coding: utf-8 -*-
"""段5b: ユーザー設定の印刷範囲を列移動に追随させる（$A$1:$W$35 → $A$1:$X$35）。
集計の値列が1列右（X）へ移ったため、そのままだと印刷で値が切れる。"""
import sys, zipfile

SRC, DST = sys.argv[1], sys.argv[2]

zin = zipfile.ZipFile(SRC)
parts = {n: zin.read(n) for n in zin.namelist()}
infos = {i.filename: i for i in zin.infolist()}
order = zin.namelist()
zin.close()

wb = parts['xl/workbook.xml'].decode('utf-8')
for sheet in ('ピッキング', '梱包'):
    old = '%s!$A$1:$W$35' % sheet
    assert wb.count(old) == 1, old + ' が見つからない'
    wb = wb.replace(old, '%s!$A$1:$X$35' % sheet)
    print('Print_Area %s → $A$1:$X$35' % sheet)
parts['xl/workbook.xml'] = wb.encode('utf-8')

zout = zipfile.ZipFile(DST, 'w', zipfile.ZIP_DEFLATED)
for nm in order:
    zi = zipfile.ZipInfo(nm, date_time=infos[nm].date_time)
    zi.compress_type = infos[nm].compress_type
    zi.external_attr = infos[nm].external_attr
    zout.writestr(zi, parts[nm])
zout.close()
