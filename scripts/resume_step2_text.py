# -*- coding: utf-8 -*-
"""段2: 現行仕様と食い違っていた説明文3か所を直す。

  ピッキング!B4・梱包!B4 … 「判定は信頼区間が全体平均をまたぐかどうか」→ 旧判定の説明。
                            現行は会社目標 1.6分/件 に対する達成率の4区分（設定!D31:D33）。
  ダッシュボード!K6        … 「⑧ 印刷用（A4・1枚）」→ 現行は A3 横 2 枚。
  使い方!B43               … 「A4 横 1 枚に収まる設定済み」→ 同上。

文言は共有文字列を書き換えず、新しい <si> を末尾に足して対象セルだけ付け替える
（rank_r_step3 と同じ流儀）。
"""
import re, sys, zipfile

SRC, DST = sys.argv[1], sys.argv[2]

# (worksheet, セル, 現行文に含まれるはずの文字列, 新しい本文)
TEXT_EDITS = [
    ('xl/worksheets/sheet4.xml', 'B4', '判定は信頼区間が全体平均をまたぐかどうか',
     '自動計算です。入力は「入力」シートで行ってください。'
     '判定は会社目標（1.6分/件）に対する達成率で決めます（◎○△の境目は「設定」シート）。'),
    ('xl/worksheets/sheet5.xml', 'B4', '判定は信頼区間が全体平均をまたぐかどうか',
     '自動計算です。入力は「入力」シートで行ってください。'
     '判定は会社目標（1.6分/件）に対する達成率で決めます（◎○△の境目は「設定」シート）。'),
    ('xl/worksheets/sheet1.xml', 'K6', 'A4・1枚',
     '⑧ 印刷用（A3横・2枚）'),
    ('xl/worksheets/sheet11.xml', 'B43', 'A4 横 1 枚',
     '・「印刷用」シートを開いて印刷してください。A3 横 2 枚に収まる設定済みです'
     '（1枚目にグラフ①②③と順位1〜32、2枚目に残りの順位と注記）。'),
]


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

    ss = parts['xl/sharedStrings.xml'].decode('utf-8')
    texts = si_texts(ss)
    new_sis, cache = [], {}
    next_idx = len(texts)

    for path, ref, expect, newtext in TEXT_EDITS:
        w = parts[path].decode('utf-8')
        m = re.search(r'<c r="%s"[^>]*t="s"[^>]*><v>(\d+)</v></c>' % ref, w)
        assert m, '%s %s が共有文字列セルではない' % (path, ref)
        idx = int(m.group(1))
        cur = texts[idx]
        assert expect in cur, '%s %s の文言が想定と違う: %s' % (path, ref, cur[:60])
        if newtext not in cache:                 # 同じ新文言は 1 つの si を共有
            cache[newtext] = next_idx
            new_sis.append('<si><t xml:space="preserve">%s</t></si>' % esc(newtext))
            next_idx += 1
        w = (w[:m.start()]
             + m.group(0).replace('<v>%d</v>' % idx, '<v>%d</v>' % cache[newtext])
             + w[m.end():])
        parts[path] = w.encode('utf-8')
        print('文言 %s %s: si %d → %d  「%s…」'
              % (path.split('/')[-1], ref, idx, cache[newtext], newtext[:30]))

    ss = ss.replace('</sst>', ''.join(new_sis) + '</sst>')
    mc = re.search(r'<sst[^>]*uniqueCount="(\d+)"', ss)
    ss = ss[:mc.start(1)] + str(int(mc.group(1)) + len(new_sis)) + ss[mc.end(1):]
    mt = re.search(r'<sst[^>]*?count="(\d+)"', ss)
    ss = ss[:mt.start(1)] + str(int(mt.group(1)) + len(TEXT_EDITS)) + ss[mt.end(1):]
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
