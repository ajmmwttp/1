# -*- coding: utf-8 -*-
"""段1: ピッキング/梱包の集計ブロック等を1列右へ（V/W/X/Y → W/X/Y/Z）。

テーブル内に「入力行」キー列（V）を置く場所を空けるための純粋な移動。値は変えない。
ベースはユーザーのExcel保存版（並べ替え・印刷設定を保持）。
"""
import re, sys, zipfile

SRC, DST = sys.argv[1], sys.argv[2]
WORK = {'xl/worksheets/sheet4.xml': 'ピッキング', 'xl/worksheets/sheet5.xml': '梱包'}
REFERRERS = {'xl/worksheets/sheet1.xml': ('ダッシュボード', 36),
             'xl/worksheets/sheet8.xml': ('配置マップ', 120)}
SHIFT = {'V': 'W', 'W': 'X', 'X': 'Y', 'Y': 'Z'}


def edit_cell_formula(s, ref, fn):
    m = re.search(r'<c r="%s"(?:(?!</c>).)*?</c>' % ref, s, re.S)
    assert m, ref + ' が見つからない'
    blk = m.group(0)
    mf = re.search(r'(<f(?: [^>]*)?>)((?:(?!</f>).)*)(</f>)', blk, re.S)
    assert mf, ref + ' に式がない'
    nb = blk[:mf.start(2)] + fn(mf.group(2)) + blk[mf.end(2):]
    return s[:m.start()] + nb + s[m.end():]


def shift_sheet(s, name):
    # 1) S列の式: 短縮helper Y{r} -> Z{r}（各セル6参照×60行）
    n = 0
    for r in range(7, 67):
        def f(fml):
            nonlocal n
            new, k = re.subn(r'(?<![A-Z$!:])Y(\d+)', r'Z\1', fml)
            n += k
            return new
        s = edit_cell_formula(s, 'S%d' % r, f)
    assert n == 360, '%s: S列のY参照が%d件（想定360）' % (name, n)

    # 2) L列の $W$3 -> $X$3
    cnt = s.count('$W$3')
    assert cnt == 120, '%s: $W$3 が%d件（想定120）' % (name, cnt)
    s = s.replace('$W$3', '$X$3')

    # 3) 集計セルの内部参照 W10..W17 -> X10..X17、W3 の SUM(X..) -> SUM(Y..)
    s = edit_cell_formula(s, 'W3', lambda f: f.replace('SUM(X7:X66)', 'SUM(Y7:Y66)'))
    n = 0
    for ref in ('W15', 'W16', 'W17', 'W18', 'W19', 'W20'):
        def f(fml):
            nonlocal n
            new, k = re.subn(r'(?<![A-Z$!:])W(1[0-7])(?![0-9])', r'X\1', fml)
            n += k
            return new
        s = edit_cell_formula(s, ref, f)
    assert n == 11, '%s: 集計内部のW参照が%d件（想定11）' % (name, n)

    # 4) 共有数式の範囲（加重helper X -> Y）
    for old, new in (('ref="X7:X38"', 'ref="Y7:Y38"'), ('ref="X39:X66"', 'ref="Y39:Y66"')):
        assert s.count(old) == 1, '%s: %s が見つからない' % (name, old)
        s = s.replace(old, new)

    # 5) セルの r 属性を移動（移動先Zは空なので衝突しない）
    moved = [0]
    def cell(m):
        moved[0] += 1
        return '<c r="%s%s"' % (SHIFT[m.group(1)], m.group(2))
    s = re.sub(r'<c r="([VWXY])(\d+)"', cell, s)
    assert moved[0] == 19 + 18 + 60 + 60, '%s: 移動セル%d個（想定157）' % (name, moved[0])

    # 6) 列定義 22..25 -> 23..26（降順で処理）
    for old_i in (25, 24, 23, 22):
        pat = '<col min="%d" max="%d"' % (old_i, old_i)
        assert pat in s, '%s: 列定義%dがない' % (name, old_i)
        s = s.replace(pat, '<col min="%d" max="%d"' % (old_i + 1, old_i + 1))

    # 7) dimension / spans
    assert '<dimension ref="A2:Y66"/>' in s
    s = s.replace('<dimension ref="A2:Y66"/>', '<dimension ref="A2:Z66"/>')
    s = s.replace('spans="1:25"', 'spans="1:26"')
    assert not re.search(r'<c r="V\d+"', s), '%s: V列に残留セル' % name
    print('  %s: 157セルを1列右へ移動' % name)
    return s


def main():
    zin = zipfile.ZipFile(SRC)
    parts = {n: zin.read(n) for n in zin.namelist()}
    infos = {i.filename: i for i in zin.infolist()}
    order = zin.namelist()
    zin.close()

    print('集計ブロックの移動 V/W/X/Y -> W/X/Y/Z')
    for path, name in WORK.items():
        parts[path] = shift_sheet(parts[path].decode('utf-8'), name).encode('utf-8')

    print('他シートからの参照の付け替え')
    for path, (name, expect) in REFERRERS.items():
        s = parts[path].decode('utf-8')
        n = s.count('ピッキング!$W$') + s.count('梱包!$W$')
        assert n == expect, '%s: $W$参照%d件（想定%d）' % (name, n, expect)
        s = s.replace('ピッキング!$W$', 'ピッキング!$X$').replace('梱包!$W$', '梱包!$X$')
        parts[path] = s.encode('utf-8')
        print('  %s: %d箇所を $W$ -> $X$ に付け替え' % (name, n))

    zout = zipfile.ZipFile(DST, 'w', zipfile.ZIP_DEFLATED)
    for nm in order:
        zi = zipfile.ZipInfo(nm, date_time=infos[nm].date_time)
        zi.compress_type = infos[nm].compress_type
        zi.external_attr = infos[nm].external_attr
        zout.writestr(zi, parts[nm])
    zout.close()


main()
