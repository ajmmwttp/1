# -*- coding: utf-8 -*-
"""段2: 「入力行」キー列 V をピッキング/梱包のテーブル内に追加する。

各行の B列の式が参照している 入力!$B$n から n を取り、V{r}==ROW(入力!$B$n) とする。
テーブル内のセルなので、以後の並べ替えで行と一緒に動き、常に
「この行は入力シートの何行目の人か」を保持する（同姓同名でも一意）。
"""
import re, sys, zipfile
import openpyxl

SRC, DST = sys.argv[1], sys.argv[2]
SHEETS = {'xl/worksheets/sheet4.xml': ('ピッキング', 'xl/tables/table1.xml'),
          'xl/worksheets/sheet5.xml': ('梱包', 'xl/tables/table2.xml')}


def insert_cells(rowxml, newcells):
    m = re.match(r'(<row [^>]*>)(.*)(</row>)$', rowxml, re.S)
    head, body, tail = m.groups()
    cells = re.findall(r'<c r="[A-Z]+\d+"[^>]*/>|<c r="[A-Z]+\d+"[^>]*>.*?</c>', body, re.S)
    cells.extend(newcells)
    return head + ''.join(sorted(cells, key=lambda c: openpyxl.utils.column_index_from_string(
        re.match(r'<c r="([A-Z]+)', c).group(1)))) + tail


def main():
    zin = zipfile.ZipFile(SRC)
    parts = {n: zin.read(n) for n in zin.namelist()}
    infos = {i.filename: i for i in zin.infolist()}
    order = zin.namelist()
    zin.close()

    for path, (name, tpath) in SHEETS.items():
        s = parts[path].decode('utf-8')

        # 各行の入力行 n を B列の式から取る
        keys = {}
        for r in range(7, 67):
            m = re.search(r'<c r="B%d"(?:(?!</c>).)*?<f[^>]*>IF\(入力!\$B\$(\d+)=' % r, s, re.S)
            assert m, '%s B%d の式から入力行を特定できない' % (name, r)
            keys[r] = int(m.group(1))
        ks = sorted(keys.values())
        assert len(set(ks)) == 60 and ks == list(range(ks[0], ks[0] + 60)), \
            '%s: キーが一意な連番集合でない: %s…' % (name, ks[:5])

        # 見出しとキー列セル
        head = '<c r="V6" s="20" t="inlineStr"><is><t>入力行</t></is></c>'
        m = re.search(r'<row r="6"[^>]*>.*?</row>', s, re.S)
        s = s[:m.start()] + insert_cells(m.group(0), [head]) + s[m.end():]
        for r in range(7, 67):
            cell = '<c r="V%d"><f>ROW(入力!$B$%d)</f><v>%d</v></c>' % (r, keys[r], keys[r])
            m = re.search(r'<row r="%d"[^>]*>.*?</row>' % r, s, re.S)
            s = s[:m.start()] + insert_cells(m.group(0), [cell]) + s[m.end():]

        # 隠し列の定義（22列目は移動後は未定義）
        assert '<col min="22" max="22"' not in s
        s = s.replace('<col min="23"',
                      '<col min="22" max="22" width="6" hidden="1" customWidth="1"/><col min="23"', 1)
        parts[path] = s.encode('utf-8')

        # テーブル定義の拡張
        t = parts[tpath].decode('utf-8')
        for old, new, cnt in (('ref="A6:U66"', 'ref="A6:V66"', 2),
                              ('<sortState ref="A7:U66"', '<sortState ref="A7:V66"', 1)):
            assert t.count(old) == cnt, '%s: %s が%d件' % (tpath, old, t.count(old))
            t = t.replace(old, new)
        t = t.replace('<tableColumns count="21">', '<tableColumns count="22">')
        t = t.replace('</tableColumns>', '<tableColumn id="22" name="入力行"/></tableColumns>')
        parts[tpath] = t.encode('utf-8')
        print('%s: キー列V(入力行 %d〜%d)を追加、テーブル A6:V66・22列へ' % (name, ks[0], ks[-1]))

    zout = zipfile.ZipFile(DST, 'w', zipfile.ZIP_DEFLATED)
    for nm in order:
        zi = zipfile.ZipInfo(nm, date_time=infos[nm].date_time)
        zi.compress_type = infos[nm].compress_type
        zi.external_attr = infos[nm].external_attr
        zout.writestr(zi, parts[nm])
    zout.close()


main()
