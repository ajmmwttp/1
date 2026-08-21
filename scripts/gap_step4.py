# -*- coding: utf-8 -*-
"""段6: 使い方シートの用語表に新しい2列の説明を足し、旧信頼性(0.61)の記述を現行値に直す。"""
import re, sys, zipfile

SRC, DST = sys.argv[1], sys.argv[2]
USE = 'xl/worksheets/sheet11.xml'

NEW_TERMS = [
    (33, '目標まで あと',
     '1件あたりの実測秒と、会社目標 96秒（1.6分）との差。'
     '到達している人は「達成済み」と出ます。'),
    (34, '目標到達で増やせる件数',
     '同じ時間で目標ペースなら処理できたはずの件数と、実績との差。'
     'マイナスは、目標ペースより先行している分です。'),
]
# 係数見直し後の値に合わない記述（ピッキングの信頼性は 0.61 → 0.40）
STALE = [
    ('C32', '0.61', '順位の再現性。1に近いほど順位が安定。ピッキング 0.40／梱包 0.87。'),
    ('B39', '0.61', '・ピッキングは信頼性 0.40 と低めです。'
                    '1か月の順位だけで人を決めず、数か月ならして見てください。'),
]


def esc(t):
    return t.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')


def main():
    zin = zipfile.ZipFile(SRC)
    parts = {n: zin.read(n) for n in zin.namelist()}
    infos = {i.filename: i for i in zin.infolist()}
    order = zin.namelist()
    zin.close()

    s = parts[USE].decode('utf-8')
    ss = parts['xl/sharedStrings.xml'].decode('utf-8')
    texts = [''.join(re.findall(r'<t[^>]*>(.*?)</t>', b, re.S))
             for b in re.findall(r'<si>(.*?)</si>', ss, re.S)]

    # --- 用語行の追加（33・34行は未使用。既存行はずらさない）---
    for row, term, desc in NEW_TERMS:
        assert not re.search(r'<row r="%d"[ />]' % row, s), '%d行は空ではない' % row
        xml = ('<row r="%d" spans="2:7" x14ac:dyDescent="0.15">'
               '<c r="B%d" s="29" t="inlineStr"><is><t>%s</t></is></c>'
               '<c r="C%d" s="93" t="inlineStr"><is><t>%s</t></is></c>'
               '<c r="D%d" s="74"/><c r="E%d" s="74"/><c r="F%d" s="74"/>'
               '<c r="G%d" s="75"/></row>'
               % (row, row, esc(term), row, esc(desc), row, row, row, row))
        anchor = re.search(r'<row r="35"[^>]*>', s)
        s = s[:anchor.start()] + xml + s[anchor.start():]
        print('使い方 %d行: 「%s」を追加' % (row, term))

    # --- 結合セル（C列の説明は C:G を結合するのが既存の作り）---
    merges = ''.join('<mergeCell ref="C%d:G%d"/>' % (r, r) for r, _, _ in NEW_TERMS)
    m = re.search(r'<mergeCells count="(\d+)">', s)
    s = (s[:m.start()] + '<mergeCells count="%d">' % (int(m.group(1)) + len(NEW_TERMS))
         + merges + s[m.end():])
    print('結合セル: %s → %d' % (m.group(1), int(m.group(1)) + len(NEW_TERMS)))

    # --- 旧い数値の記述を差し替え（共有文字列は末尾に足して付け替える）---
    new_sis, next_idx = [], len(texts)
    for ref, expect, newtext in STALE:
        mc = re.search(r'<c r="%s"[^>]*t="s"[^>]*><v>(\d+)</v></c>' % ref, s)
        assert mc, '使い方 %s が共有文字列セルではない' % ref
        idx = int(mc.group(1))
        assert expect in texts[idx], '使い方 %s の文言が想定と違う: %s' % (ref, texts[idx][:60])
        new_sis.append('<si><t xml:space="preserve">%s</t></si>' % esc(newtext))
        s = s[:mc.start()] + mc.group(0).replace('<v>%d</v>' % idx,
                                                 '<v>%d</v>' % next_idx) + s[mc.end():]
        print('使い方 %s: si %d → %d  「%s…」' % (ref, idx, next_idx, newtext[:34]))
        next_idx += 1

    ss = ss.replace('</sst>', ''.join(new_sis) + '</sst>')
    for attr in ('uniqueCount', 'count'):
        ma = re.search(r'<sst[^>]*?\b%s="(\d+)"' % attr, ss)
        ss = ss[:ma.start(1)] + str(int(ma.group(1)) + len(new_sis)) + ss[ma.end(1):]
    parts['xl/sharedStrings.xml'] = ss.encode('utf-8')
    parts[USE] = s.encode('utf-8')

    zout = zipfile.ZipFile(DST, 'w', zipfile.ZIP_DEFLATED)
    for nm in order:
        zi = zipfile.ZipInfo(nm, date_time=infos[nm].date_time)
        zi.compress_type = infos[nm].compress_type
        zi.external_attr = infos[nm].external_attr
        zout.writestr(zi, parts[nm])
    zout.close()


main()
