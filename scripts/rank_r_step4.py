# -*- coding: utf-8 -*-
"""段4b: 順位を会社目標基準に揃えたのに合わせ、ダッシュボードに残っていた
旧判定基準（◎上位／○標準／△要支援＝信頼区間 vs 全体平均）の表示を、
現行の4区分（◎達成／○あと一歩／△要改善／✕要支援）に直す。
併せて、旧係数のまま残っていた注記（ピッキング a=92.1秒/社 → 56.05秒/社）を更新する。
"""
import re, sys, zipfile

SRC, DST = sys.argv[1], sys.argv[2]
DASH = 'xl/worksheets/sheet1.xml'
PK, KP = 'xl/worksheets/sheet4.xml', 'xl/worksheets/sheet5.xml'

# 判定4区分: (ダッシュボードの行, 見出し, 見かた, 工程シートのT行)
BINS = [
    (162, '◎ 達成',     '会社目標 1.6分/件 に対する達成率が 100% 以上', 6),
    (163, '○ あと一歩', '達成率 90% 以上 100% 未満', 7),
    (164, '△ 要改善',   '達成率 80% 以上 90% 未満', 8),
    (165, '✕ 要支援',   '達成率 80% 未満', 9),
]

# 文言差し替え: (worksheet, セル, 現行文に含まれるはずの語, 新しい本文)
NOTES = [
    (DASH, 'B234', 'ピッキング a=92.1秒/社',
     '標準時間 ＝ a × 企業数 ＋ b × 件数　'
     '（ピッキング a=56.05秒/社・b=75.6秒/件／梱包 a=92.1秒/社・b=69.5秒/件）'),
    ('xl/worksheets/sheet11.xml', 'C21', '92.1秒/社',
     '1社ごとに必ず発生する時間。ピッキングは 56.05秒/社'
     '（① リストを見る 10秒 ＋ ④ 伝票を挟む 46.05秒）。'),
]


def esc(t):
    return t.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')


def cache_of(xml, ref):
    m = re.search(r'<c r="%s"(?:(?!</c>).)*?</c>' % ref, xml, re.S)
    if not m:
        return None
    mv = re.search(r'<v>([^<]*)</v>', m.group(0))
    return mv.group(1) if mv else None


def main():
    zin = zipfile.ZipFile(SRC)
    parts = {n: zin.read(n) for n in zin.namelist()}
    infos = {i.filename: i for i in zin.infolist()}
    order = zin.namelist()
    zin.close()

    ss = parts['xl/sharedStrings.xml'].decode('utf-8')
    texts = [''.join(re.findall(r'<t[^>]*>(.*?)</t>', b, re.S))
             for b in re.findall(r'<si>(.*?)</si>', ss, re.S)]
    new_sis, next_idx = [], len(texts)

    def add_si(t):
        nonlocal next_idx
        new_sis.append('<si><t xml:space="preserve">%s</t></si>' % esc(t))
        next_idx += 1
        return next_idx - 1

    d = parts[DASH].decode('utf-8')
    pk = parts[PK].decode('utf-8')
    kp = parts[KP].decode('utf-8')

    # --- 判定4区分の見出しと説明 ---
    for row, label, how, trow in BINS:
        cpk = cache_of(pk, 'T%d' % trow) or ''
        ckp = cache_of(kp, 'T%d' % trow) or ''
        i_lbl, i_how = add_si(label), add_si(how)
        cells = ('<c r="B{r}" s="25" t="s"><v>{l}</v></c>'
                 '<c r="C{r}" s="26"><f>ピッキング!$T${t}</f><v>{p}</v></c>'
                 '<c r="D{r}" s="26"><f>梱包!$T${t}</f><v>{k}</v></c>'
                 '<c r="E{r}" s="64" t="s"><v>{h}</v></c>'
                 '<c r="F{r}" s="65"/><c r="G{r}" s="65"/><c r="H{r}" s="65"/>'
                 '<c r="I{r}" s="65"/><c r="J{r}" s="65"/>'
                 ).format(r=row, l=i_lbl, h=i_how, t=trow, p=cpk, k=ckp)
        newrow = ('<row r="%d" spans="2:10" x14ac:dyDescent="0.15">%s</row>' % (row, cells))
        m = re.search(r'<row r="%d"[^>]*>.*?</row>' % row, d, re.S)
        if m:
            d = d[:m.start()] + newrow + d[m.end():]
            print('ダッシュボード %d行: 「%s」 PK=%s 梱包=%s（既存行を更新）' % (row, label, cpk, ckp))
        else:
            anchor = re.search(r'<row r="166"[^>]*>', d)
            d = d[:anchor.start()] + newrow + d[anchor.start():]
            print('ダッシュボード %d行: 「%s」 PK=%s 梱包=%s（新規追加）' % (row, label, cpk, ckp))
    parts[DASH] = d.encode('utf-8')

    # --- 旧係数の注記 ---
    for path, ref, expect, newtext in NOTES:
        w = parts[path].decode('utf-8')
        m = re.search(r'<c r="%s"[^>]*t="s"[^>]*><v>(\d+)</v></c>' % ref, w)
        assert m, '%s %s が共有文字列セルではない' % (path, ref)
        idx = int(m.group(1))
        assert expect in texts[idx], '%s %s の文言が想定と違う: %s' % (path, ref, texts[idx][:70])
        ni = add_si(newtext)
        w = w[:m.start()] + m.group(0).replace('<v>%d</v>' % idx, '<v>%d</v>' % ni) + w[m.end():]
        parts[path] = w.encode('utf-8')
        print('注記 %s %s: si %d → %d  「%s…」' % (path.split('/')[-1], ref, idx, ni, newtext[:40]))

    ss = ss.replace('</sst>', ''.join(new_sis) + '</sst>')
    for attr in ('uniqueCount', 'count'):
        m = re.search(r'<sst[^>]*?\b%s="(\d+)"' % attr, ss)
        ss = ss[:m.start(1)] + str(int(m.group(1)) + len(new_sis)) + ss[m.end(1):]
    parts['xl/sharedStrings.xml'] = ss.encode('utf-8')
    print('共有文字列 %d 件追加' % len(new_sis))

    zout = zipfile.ZipFile(DST, 'w', zipfile.ZIP_DEFLATED)
    for nm in order:
        zi = zipfile.ZipInfo(nm, date_time=infos[nm].date_time)
        zi.compress_type = infos[nm].compress_type
        zi.external_attr = infos[nm].external_attr
        zout.writestr(zi, parts[nm])
    zout.close()


main()
