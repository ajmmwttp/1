# -*- coding: utf-8 -*-
"""段2: ダッシュボードのランキング用列を順位と同じ値に揃える。

V3:V62 = ピッキングの順位k番目の値、X3:X62 = 梱包の同じもの。
参照を L列（縮小後効率）→ R列（目標達成率）に変え、キャッシュも再計算する。
"""
import re, sys, zipfile

SRC, DST = sys.argv[1], sys.argv[2]
DASH = 'xl/worksheets/sheet1.xml'
# 値列 -> (工程シート, シート名, 氏名列)
SRC_SHEETS = {'V': ('xl/worksheets/sheet4.xml', 'ピッキング', 'U'),
              'X': ('xl/worksheets/sheet5.xml', '梱包', 'W')}


def cell_block(xml, ref):
    return re.search(r'<c r="%s"(?:(?!</c>).)*?</c>' % ref, xml, re.S)


def cache(xml, ref):
    m = cell_block(xml, ref)
    if m is None:
        return None
    blk = m.group(0)
    if re.search(r't="(str|s|e|b)"', blk):
        return None
    mv = re.search(r'<v>([^<]*)</v>', blk)
    return float(mv.group(1)) if mv and mv.group(1) else None


def inline_str(xml, ref, shared):
    """氏名セル（t="str" のインライン文字列 or 共有文字列）の中身を返す。"""
    m = cell_block(xml, ref)
    if m is None:
        return None
    blk = m.group(0)
    mv = re.search(r'<v>([^<]*)</v>', blk)
    if not mv or mv.group(1) == '':
        return None
    if 't="s"' in blk:
        return shared[int(mv.group(1))]
    return mv.group(1)


def put_str(xml, ref, text):
    """数式セルのキャッシュを文字列 text（None なら空）に書き換える。"""
    m = cell_block(xml, ref)
    if m is None:
        return xml
    blk = m.group(0)
    blk = re.sub(r' t="(str|s)"', '', blk)
    blk = re.sub(r'(<c r="%s"[^>]*?)>' % ref, r'\1 t="str">', blk, count=1)
    esc = '' if text is None else (text.replace('&', '&amp;')
                                      .replace('<', '&lt;').replace('>', '&gt;'))
    body = '<v/>' if text is None else '<v>%s</v>' % esc
    if re.search(r'<v[^>]*/>|<v>[^<]*</v>', blk):
        blk = re.sub(r'<v[^>]*/>|<v>[^<]*</v>', body, blk)
    else:
        blk = blk.replace('</c>', body + '</c>')
    return xml[:m.start()] + blk + xml[m.end():]


def main():
    zin = zipfile.ZipFile(SRC)
    parts = {n: zin.read(n) for n in zin.namelist()}
    infos = {i.filename: i for i in zin.infolist()}
    order = zin.namelist()
    zin.close()

    shared = re.findall(r'<si>(?:.*?)</si>', parts['xl/sharedStrings.xml'].decode('utf-8'), re.S)
    shared = [''.join(re.findall(r'<t[^>]*>(.*?)</t>', x, re.S)) for x in shared]

    # 各工程シートの 順位 -> (氏名, 目標達成率R)（同順位は先勝ち＝MATCHと同じ）
    lookup = {}
    for col, (path, name, namecol) in SRC_SHEETS.items():
        s = parts[path].decode('utf-8')
        tbl, ntbl = {}, {}
        for r in range(7, 67):
            a, rr = cache(s, 'A%d' % r), cache(s, 'R%d' % r)
            if a is not None and rr is not None:
                tbl.setdefault(int(a), rr)
                ntbl.setdefault(int(a), inline_str(s, 'B%d' % r, shared))
        lookup[col] = (name, tbl, ntbl, namecol)

    d = parts[DASH].decode('utf-8')
    for col, (name, tbl, ntbl, namecol) in lookup.items():
        old_f = 'INDEX(%s!$L$7:$L$66,' % name
        new_f = 'INDEX(%s!$R$7:$R$66,' % name
        n_f = n_v = 0
        for row in range(3, 63):
            ref = '%s%d' % (col, row)
            m = cell_block(d, ref)
            if m is None:
                continue
            blk = m.group(0)
            assert old_f in blk, '%s の式が想定と違う: %s' % (ref, blk[:120])
            blk = blk.replace(old_f, new_f)
            n_f += 1
            val = tbl.get(row - 2)      # T{row} = row-2 位
            if val is None:
                blk = re.sub(r'<v[^>]*/>|<v>[^<]*</v>', '<v/>', blk)
                if not re.search(r't="str"', blk):
                    blk = re.sub(r'(<c r="%s"[^>]*?)>' % ref, r'\1 t="str">', blk, count=1)
            else:
                blk = blk.replace(' t="str"', '')
                txt = repr(val) if isinstance(val, float) else str(val)
                if re.search(r'<v[^>]*/>|<v>[^<]*</v>', blk):
                    blk = re.sub(r'<v[^>]*/>|<v>[^<]*</v>', '<v>%s</v>' % txt, blk)
                else:
                    blk = blk.replace('</c>', '<v>%s</v></c>' % txt)
            n_v += 1
            d = d[:m.start()] + blk + d[m.end():]
        # 氏名列は式は変えないが、順位が変わったのでキャッシュを入れ直す
        n_n = 0
        for row in range(3, 63):
            d = put_str(d, '%s%d' % (namecol, row), ntbl.get(row - 2))
            n_n += 1
        print('%s列（%s）: 式 %d セル / 値キャッシュ %d セル / %s列 氏名キャッシュ %d セル更新'
              '（有効 %d 位分）' % (col, name, n_f, n_v, namecol, n_n, len(tbl)))
    parts[DASH] = d.encode('utf-8')

    zout = zipfile.ZipFile(DST, 'w', zipfile.ZIP_DEFLATED)
    for nm in order:
        zi = zipfile.ZipInfo(nm, date_time=infos[nm].date_time)
        zi.compress_type = infos[nm].compress_type
        zi.external_attr = infos[nm].external_attr
        zout.writestr(zi, parts[nm])
    zout.close()


main()
