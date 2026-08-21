# -*- coding: utf-8 -*-
"""段1: ピッキング/梱包の集計ブロックと補助列を S/T/U → V/W/X へ移す。

表（A6:R66）の右隣を空けて、新しい2列を表の中に入れられるようにする。
値も表示も変えない純粋な移動。openpyxl 往復は使わず zip 内の XML を直接編集。
"""
import re, sys, zipfile

SRC, DST = sys.argv[1], sys.argv[2]
WORK = {'xl/worksheets/sheet4.xml': 'ピッキング', 'xl/worksheets/sheet5.xml': '梱包'}
REFERRERS = {'xl/worksheets/sheet1.xml': 'ダッシュボード',
             'xl/worksheets/sheet8.xml': '配置マップ'}
SHIFT = {'S': 'V', 'T': 'W', 'U': 'X'}

# 移動対象の列を参照している文字列と、想定される出現回数（調査で全件確認済み）
FIXES = [
    ('IFERROR(SUM(U7:U66)/SUMIF(I7:I66,"&gt;0",C7:C66),"")',
     'IFERROR(SUM(X7:X66)/SUMIF(I7:I66,"&gt;0",C7:C66),"")', 1),   # W3 全体平均
    ('IFERROR(T13/T14,"")', 'IFERROR(W13/W14,"")', 1),             # W15 段取り比率
    ('IFERROR(T10/T11,"")', 'IFERROR(W10/W11,"")', 1),             # W16 平均 件/社
    ('IFERROR(T12*60/T10,"")', 'IFERROR(W12*60/W10,"")', 1),       # W17 1件あたり実測
    ('$T$3', '$W$3', 120),                                         # L7:L66（1式に2回）
    ('ref="U7:U38"', 'ref="X7:X38"', 1),                           # 共有数式の範囲
    ('ref="U39:U66"', 'ref="X39:X66"', 1),
]


def shift_sheet(s, name):
    for old, new, cnt in FIXES:
        found = s.count(old)
        assert found == cnt, '%s: 「%s」が %d 件（想定 %d 件）' % (name, old, found, cnt)
        s = s.replace(old, new)

    n = [0]

    def cell(m):
        n[0] += 1
        return '<c r="%s%s"' % (SHIFT[m.group(1)], m.group(2))
    s = re.sub(r'<c r="([STU])(\d+)"', cell, s)

    for old_i, new_i in ((19, 22), (20, 23), (21, 24)):
        pat = '<col min="%d" max="%d"' % (old_i, old_i)
        assert pat in s, '%s: 列定義 %d が見つからない' % (name, old_i)
        s = s.replace(pat, '<col min="%d" max="%d"' % (new_i, new_i))

    # 新設する Y列(=25) まで見込んで広げておく
    assert '<dimension ref="A2:U66"/>' in s, '%s: dimension が想定と違う' % name
    s = s.replace('<dimension ref="A2:U66"/>', '<dimension ref="A2:Y66"/>')
    s = s.replace('spans="1:21"', 'spans="1:25"')

    assert not re.search(r'<c r="[STU]\d+"', s), '%s: 移動漏れのセルがある' % name
    print('  %s: セル %d 個を移動' % (name, n[0]))
    return s


def main():
    zin = zipfile.ZipFile(SRC)
    parts = {n: zin.read(n) for n in zin.namelist()}
    infos = {i.filename: i for i in zin.infolist()}
    order = zin.namelist()
    zin.close()

    print('集計ブロックの移動 S/T/U -> V/W/X')
    for path, name in WORK.items():
        parts[path] = shift_sheet(parts[path].decode('utf-8'), name).encode('utf-8')

    print('他シートからの参照の付け替え')
    for path, name in REFERRERS.items():
        s = parts[path].decode('utf-8')
        n = 0
        for sheet in ('ピッキング', '梱包'):
            n += s.count('%s!$T$' % sheet)
            s = s.replace('%s!$T$' % sheet, '%s!$W$' % sheet)
            assert '%s!$S$' % sheet not in s and '%s!$U$' % sheet not in s, \
                '%s に %s の S/U 列参照が残っている' % (name, sheet)
        parts[path] = s.encode('utf-8')
        print('  %s: %d 箇所を $T$ -> $W$ に付け替え' % (name, n))

    zout = zipfile.ZipFile(DST, 'w', zipfile.ZIP_DEFLATED)
    for nm in order:
        zi = zipfile.ZipInfo(nm, date_time=infos[nm].date_time)
        zi.compress_type = infos[nm].compress_type
        zi.external_attr = infos[nm].external_attr
        zout.writestr(zi, parts[nm])
    zout.close()


main()
