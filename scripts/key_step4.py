# -*- coding: utf-8 -*-
"""段4+5: chart10（印刷用③）の描画されない帯境界2系列を削除し、使い方に並べ替えの注記を足す。"""
import re, sys, zipfile

SRC, DST = sys.argv[1], sys.argv[2]

NOTES = [
    ('97', '・ピッキング・梱包シートの表は、並べ替えても「印刷用・散布図・配置マップ」との'
           '人の対応は崩れません（入力シートの行番号で引き当てています）。'),
    ('96', '・そのため同姓同名の方がいても正しく対応します。隠し列「入力行」は削除しないでください。'),
]


def main():
    zin = zipfile.ZipFile(SRC)
    parts = {n: zin.read(n) for n in zin.namelist()}
    infos = {i.filename: i for i in zin.infolist()}
    order = zin.namelist()
    zin.close()

    # --- chart10: AZ/BB 系列（1点しかなく線が描画されない残骸）を削除 ---
    c = parts['xl/charts/chart10.xml'].decode('utf-8')
    removed = 0
    for marker in ('$AZ$2:$AZ$3', '$BB$2:$BB$3'):
        m = None
        for mm in re.finditer(r'<c:ser>(?:(?!</c:ser>).)*?</c:ser>', c, re.S):
            if marker in mm.group(0):
                m = mm
                break
        assert m, 'chart10 に %s 系列がない' % marker
        c = c[:m.start()] + c[m.end():]
        removed += 1
    parts['xl/charts/chart10.xml'] = c.encode('utf-8')
    print('chart10: 帯境界の残骸 %d 系列を削除' % removed)

    # --- 使い方: 44行の後に注記2行を追加 ---
    s = parts['xl/worksheets/sheet11.xml'].decode('utf-8')
    assert not re.search(r'<row r="4[56]"[ />]', s)
    rows = ''
    for i, (style, text) in enumerate(NOTES):
        r = 45 + i
        filler = ''.join('<c r="%s%d" s="79"/>' % (col, r) for col in 'CDEFG')
        rows += ('<row r="%d" spans="2:7" x14ac:dyDescent="0.15">'
                 '<c r="B%d" s="%s" t="inlineStr"><is><t>%s</t></is></c>%s</row>'
                 % (r, r, style, text, filler))
    m = re.search(r'<row r="44"[^>]*>.*?</row>', s, re.S)
    s = s[:m.end()] + rows + s[m.end():]
    s = s.replace('<dimension ref="B2:G44"/>', '<dimension ref="B2:G46"/>')
    mc = re.search(r'<mergeCells count="(\d+)">', s)
    s = (s[:mc.start()] + '<mergeCells count="%d">' % (int(mc.group(1)) + 2)
         + '<mergeCell ref="B45:G45"/><mergeCell ref="B46:G46"/>' + s[mc.end():])
    parts['xl/worksheets/sheet11.xml'] = s.encode('utf-8')
    print('使い方: 45〜46行に並べ替えの注記を追加')

    zout = zipfile.ZipFile(DST, 'w', zipfile.ZIP_DEFLATED)
    for nm in order:
        zi = zipfile.ZipInfo(nm, date_time=infos[nm].date_time)
        zi.compress_type = infos[nm].compress_type
        zi.external_attr = infos[nm].external_attr
        zout.writestr(zi, parts[nm])
    zout.close()


main()
