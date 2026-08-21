# -*- coding: utf-8 -*-
"""段3+段4: グラフ題・軸ラベルと、順位の根拠を説明する文言を更新する。

文言は共有文字列を「その場で書き換える」のではなく、新しい <si> を末尾に足して
対象セルだけを付け替える。他セルと共有していても巻き添えにしないため。
"""
import re, sys, zipfile

SRC, DST = sys.argv[1], sys.argv[2]

CHART_TEXT = [
    ('xl/charts/chart6.xml',
     'ピッキング　縮小後効率ランキング（100 ＝ 標準どおり）',
     'ピッキング　目標達成率ランキング（100 ＝ 目標 1.6分/件）'),
    ('xl/charts/chart7.xml',
     '梱包　縮小後効率ランキング（100 ＝ 標準どおり）',
     '梱包　目標達成率ランキング（100 ＝ 目標 1.6分/件）'),
    ('xl/charts/chart6.xml', '効率 %', '目標達成率 %'),
    ('xl/charts/chart7.xml', '効率 %', '目標達成率 %'),
]

# (worksheet, セル, 期待する現行文の一部, 新しい本文)
TEXT_EDITS = [
    ('xl/worksheets/sheet1.xml', 'B148', '担当者ランキング',
     '8. 担当者ランキング　※ 目標達成率＝会社目標 1.6分/件 に対する達成率。'
     '順位も判定も、この同じ値で付けています'),
    ('xl/worksheets/sheet10.xml', 'B12', '順位づけ用の値',
     '記録日数の少ない人は数字がブレます。ブレの大きさを見積もって、'
     '参考値（縮小後効率）と信頼区間を計算します。順位づけには使いません。'),
    ('xl/worksheets/sheet11.xml', 'C11', '縮小後効率のランキング',
     None),   # 部分置換（下で処理）
    ('xl/worksheets/sheet11.xml', 'C28', '順位づけに使う',
     '記録日数が少ない人は数字がブレるため、平均側へ寄せた参考値。順位づけには使わない。'),
    ('xl/worksheets/sheet11.xml', 'C30', '全体平均',
     '会社目標 1.6分/件 に対する達成率で4区分。100%以上＝◎達成、90%以上＝○あと一歩、'
     '80%以上＝△要改善、80%未満＝✕要支援。'),
]
PARTIAL = {'C11': ('縮小後効率のランキング', '目標達成率のランキング')}


def esc(t):
    return t.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')


def si_texts(ss):
    return [''.join(re.findall(r'<t[^>]*>(.*?)</t>', b, re.S))
            for b in re.findall(r'<si>(.*?)</si>', ss, re.S)]


def main():
    zin = zipfile.ZipFile(SRC)
    parts = {n: zin.read(n) for n in zin.namelist()}
    infos = {i.filename: i for i in zin.infolist()}
    order = zin.namelist()
    zin.close()

    for path, old, new in CHART_TEXT:
        s = parts[path].decode('utf-8')
        assert '<a:t>%s</a:t>' % old in s, '%s に「%s」が見つからない' % (path, old)
        s = s.replace('<a:t>%s</a:t>' % old, '<a:t>%s</a:t>' % esc(new), 1)
        parts[path] = s.encode('utf-8')
        print('グラフ %s: 「%s」→「%s」' % (path.split('/')[-1], old[:22], new[:26]))

    ss = parts['xl/sharedStrings.xml'].decode('utf-8')
    texts = si_texts(ss)
    new_sis = []
    next_idx = len(texts)

    for path, ref, expect, newtext in TEXT_EDITS:
        w = parts[path].decode('utf-8')
        m = re.search(r'<c r="%s"[^>]*t="s"[^>]*><v>(\d+)</v></c>' % ref, w)
        assert m, '%s %s が共有文字列セルではない' % (path, ref)
        idx = int(m.group(1))
        cur = texts[idx]
        assert expect in cur, '%s %s の文言が想定と違う: %s' % (path, ref, cur[:60])
        if newtext is None:
            a, b = PARTIAL[ref]
            newtext = cur.replace(a, b)
        new_sis.append('<si><t xml:space="preserve">%s</t></si>' % esc(newtext))
        w = w[:m.start()] + m.group(0).replace('<v>%d</v>' % idx, '<v>%d</v>' % next_idx) + w[m.end():]
        parts[path] = w.encode('utf-8')
        print('文言 %s %s: si %d → %d  「%s…」' % (path.split('/')[-1], ref, idx, next_idx, newtext[:34]))
        next_idx += 1

    ss = ss.replace('</sst>', ''.join(new_sis) + '</sst>')
    mc = re.search(r'<sst[^>]*uniqueCount="(\d+)"', ss)
    ss = ss[:mc.start(1)] + str(int(mc.group(1)) + len(new_sis)) + ss[mc.end(1):]
    mt = re.search(r'<sst[^>]*?count="(\d+)"', ss)
    ss = ss[:mt.start(1)] + str(int(mt.group(1)) + len(new_sis)) + ss[mt.end(1):]
    parts['xl/sharedStrings.xml'] = ss.encode('utf-8')
    print('共有文字列: %d 件追加（uniqueCount %s → %d）'
          % (len(new_sis), mc.group(1), int(mc.group(1)) + len(new_sis)))

    zout = zipfile.ZipFile(DST, 'w', zipfile.ZIP_DEFLATED)
    for nm in order:
        zi = zipfile.ZipInfo(nm, date_time=infos[nm].date_time)
        zi.compress_type = infos[nm].compress_type
        zi.external_attr = infos[nm].external_attr
        zout.writestr(zi, parts[nm])
    zout.close()


main()
