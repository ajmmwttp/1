# -*- coding: utf-8 -*-
"""段1: ③マトリクスの見やすさ改善（シート側）。

  - 基準線の端点を新しい軸（横40〜160）に合わせる
  - 軸外検知のしきい値を横軸だけ 10/190 → 40/160 に
  - 片方工程の帯の段間隔を 5 → 6 に広げる（6段のまま。プロット領域が
    ほぼ正方形なので、5段にすると同じ段に並ぶ人のラベルが横で重なる）
数式・定数だけを直し、キャッシュは後段でまとめて更新する。
"""
import re, sys, zipfile

SRC, DST = sys.argv[1], sys.argv[2]
PD = 'xl/worksheets/sheet12.xml'

# 基準線の端点（定数セル）: セル -> (現在値, 新しい値)
CONSTS = {'X2': ('40', '10'),    # 縦線(x=100)を下端まで引き切る
          'Y2': ('40', '40'),    # 横線(y=100)の左端 … 新しい軸の下限と同じ
          'Y3': ('190', '160')}  # 横線(y=100)の右端 … 新しい軸の上限

OLD_BAND = 'CHOOSE(MOD($AY{r}-1,6)+1,12,17,22,27,32,37)'
NEW_BAND = 'CHOOSE(MOD($AY{r}-1,6)+1,12,18,24,30,36,42)'


def set_const(s, ref, old, new):
    m = re.search(r'<c r="%s"(?:(?!</c>).)*?</c>' % ref, s, re.S)
    assert m, ref + ' が見つからない'
    blk = m.group(0)
    assert '<v>%s</v>' % old in blk, '%s の値が %s ではない: %s' % (ref, old, blk[:90])
    return s[:m.start()] + blk.replace('<v>%s</v>' % old, '<v>%s</v>' % new) + s[m.end():]


def edit_formula(s, ref, fn):
    m = re.search(r'<c r="%s"(?:(?!</c>).)*?</c>' % ref, s, re.S)
    assert m, ref + ' が見つからない'
    blk = m.group(0)
    mf = re.search(r'(<f[^>]*>)((?:(?!</f>).)*)(</f>)', blk, re.S)
    assert mf, ref + ' に式がない'
    new = fn(mf.group(2))
    return s[:m.start()] + blk[:mf.start(2)] + new + blk[mf.end(2):] + s[m.end():]


def main():
    zin = zipfile.ZipFile(SRC)
    parts = {n: zin.read(n) for n in zin.namelist()}
    infos = {i.filename: i for i in zin.infolist()}
    order = zin.namelist()
    zin.close()

    s = parts[PD].decode('utf-8')
    s_holder = [None]

    for ref, (old, new) in CONSTS.items():
        if old != new:
            s = set_const(s, ref, old, new)
            print('基準線 %s: %s → %s' % (ref, old, new))
    s_holder[0] = s

    # BD / AW / AX は共有数式。ホスト（行3 と 行35）の式だけ直せば全行に効く
    n = 0
    for col, hosts in (('BD', (3, 35)), ('AW', (3, 35)), ('AX', (3, 35))):
        for r in hosts:
            def fix(f, col=col, r=r):
                if col == 'BD':
                    old = 'OR($AH{r}&lt;10,$AH{r}&gt;190)'.format(r=r)
                    new = 'OR($AH{r}&lt;40,$AH{r}&gt;160)'.format(r=r)
                else:
                    old, new = OLD_BAND.format(r=r), NEW_BAND.format(r=r)
                assert old in f, '%s%d の式が想定と違う: %s' % (col, r, f[:120])
                return f.replace(old, new)
            s2 = edit_formula(s_holder[0], '%s%d' % (col, r), fix)
            s_holder[0] = s2
            n += 1
    s = s_holder[0]
    print('軸外検知 BD / 帯 AW・AX: 共有数式のホスト %d 件を更新（各行に反映）' % n)

    parts[PD] = s.encode('utf-8')

    zout = zipfile.ZipFile(DST, 'w', zipfile.ZIP_DEFLATED)
    for nm in order:
        zi = zipfile.ZipInfo(nm, date_time=infos[nm].date_time)
        zi.compress_type = infos[nm].compress_type
        zi.external_attr = infos[nm].external_attr
        zout.writestr(zi, parts[nm])
    zout.close()


main()
