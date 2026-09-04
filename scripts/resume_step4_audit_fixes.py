# -*- coding: utf-8 -*-
"""段4: ブック全体の監査で確定した不整合を直す。

  A. 散布図!AY（記録日数）が 入力 シートを「行位置」で参照していた。
     同じ行の他の列（T/AZ/BA…）は ピッキング の行を読むが、ピッキングの表は
     並べ替え済みなので、⑥のグラフと統計（C54:C59）が別人の日数と組になっていた。
     → 他の結合と同じく 入力行キー（ピッキング!V）で引く。
  B. ダッシュボード「時間の内訳」（chart4・AX3:AX5）が旧係数 a=92.1 時代の固定値
     （段取り 233.2h）のまま。現行は ピッキング!X13 = 141.6h。
     → AX3:AX5 を数式にし、B8/B18/B98/F18/G3/B13/B150/D150/B235 の固定文も
       数式で組み立てて入力に追随させる。根拠データの無い「前週比」4セルは消す。
  C. 印刷用!B62 の軸外注記が「縦横とも 10〜190%」のまま（横軸は 40〜160）。
     梱包のみの人は左の帯（x=12〜42）に置く設計だったが、横軸 40〜160 では
     範囲外で描かれない。→ 梱包のみは x=0（軸外）にして描かず、軸外検知 BD で
     数えて【要確認】に出す。51 人目以降が印刷用に載らないことも注記に足す。
  D. 古い判定・古い統計値を書いた説明文を直す
     （入力!L16「日数未入力」、散布図 B53/B148/B150/B152〜B155、設定!B11、
       配置マップ C7/D7、要員予測 E10、chart11 の題 a=92.1）。
  E. 要員予測!C10/D10（想定効率）を「いまの全体平均」の数式にする。
  F. chart3 の目標100%線が 印刷用データ!AV3:AV23（人数に依存）を借りていた
     → 21点の定数（numLit）に置き換える。

数式のキャッシュは後段（LibreOffice 再計算 → cache_step1/2）でまとめて更新する。
"""
import re, sys, zipfile

SRC, DST = sys.argv[1], sys.argv[2]


def esc(t):
    return t.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')


def cell_block(s, ref):
    m = re.search(r'<c r="%s"(?:(?: [^>]*?)?/>|(?: [^>]*)?>(?:(?!</c>).)*</c>)' % ref, s, re.S)
    assert m, ref + ' が見つからない'
    return m


def style_of(block):
    m = re.search(r' s="(\d+)"', block)
    return ' s="%s"' % m.group(1) if m else ''


def set_formula(s, ref, formula, value=None):
    """任意のセルを数式セルに置き換える（文字列結果なら t="str"）。"""
    m = cell_block(s, ref)
    st = style_of(m.group(0))
    if formula.startswith('='):          # セルに書く式は先頭の = を持たない
        formula = formula[1:]
    if isinstance(value, (int, float)):
        new = '<c r="%s"%s><f>%s</f><v>%r</v></c>' % (ref, st, esc(formula), value)
    else:
        new = '<c r="%s"%s t="str"><f>%s</f>%s</c>' % (
            ref, st, esc(formula), '<v>%s</v>' % esc(value) if value else '<v/>')
    return s[:m.start()] + new + s[m.end():]


def clear_cell(s, ref):
    m = cell_block(s, ref)
    assert '<f' not in m.group(0), ref + ' は数式セル'
    return s[:m.start()] + '<c r="%s"%s/>' % (ref, style_of(m.group(0))) + s[m.end():]


def edit_formula(s, ref, old, new):
    m = cell_block(s, ref)
    blk = m.group(0)
    mf = re.search(r'(<f[^>]*>)((?:(?!</f>).)*)(</f>)', blk, re.S)
    assert mf, ref + ' に式がない'
    assert old in mf.group(2), '%s の式が想定と違う: %s' % (ref, mf.group(2)[:150])
    blk2 = blk[:mf.start(2)] + mf.group(2).replace(old, new) + blk[mf.end(2):]
    return s[:m.start()] + blk2 + s[m.end():]


class Strings:
    """共有文字列: 新しい <si> を末尾に足し、対象セルだけ付け替える。"""
    def __init__(self, parts):
        self.parts = parts
        self.ss = parts['xl/sharedStrings.xml'].decode('utf-8')
        self.texts = [''.join(re.findall(r'<t[^>]*>(.*?)</t>', b, re.S))
                      for b in re.findall(r'<si>(.*?)</si>', self.ss, re.S)]
        self.new, self.next, self.refs_added, self.refs_removed = [], len(self.texts), 0, 0

    def replace(self, s, ref, expect, newtext):
        m = re.search(r'<c r="%s"([^>]*)t="s"([^>]*)><v>(\d+)</v></c>' % ref, s)
        assert m, ref + ' が共有文字列セルではない'
        cur = self.texts[int(m.group(3))]
        assert expect in cur, '%s の文言が想定と違う: %s' % (ref, cur[:80])
        self.new.append('<si><t xml:space="preserve">%s</t></si>' % esc(newtext))
        idx = self.next
        self.next += 1
        self.refs_added += 1
        self.refs_removed += 1
        return s[:m.start()] + '<c r="%s"%st="s"%s><v>%d</v></c>' % (ref, m.group(1), m.group(2), idx) + s[m.end():]

    def note_removed(self, n):
        self.refs_removed += n

    def flush(self):
        ss = self.ss.replace('</sst>', ''.join(self.new) + '</sst>')
        mc = re.search(r'<sst[^>]*uniqueCount="(\d+)"', ss)
        ss = ss[:mc.start(1)] + str(int(mc.group(1)) + len(self.new)) + ss[mc.end(1):]
        mt = re.search(r'<sst[^>]*?count="(\d+)"', ss)
        ss = ss[:mt.start(1)] + str(int(mt.group(1)) + self.refs_added - self.refs_removed) + ss[mt.end(1):]
        self.parts['xl/sharedStrings.xml'] = ss.encode('utf-8')
        print('共有文字列: %d 件追加' % len(self.new))


def main():
    zin = zipfile.ZipFile(SRC)
    parts = {n: zin.read(n) for n in zin.namelist()}
    infos = {i.filename: i for i in zin.infolist()}
    order = zin.namelist()
    zin.close()
    S = Strings(parts)

    # ---------------- A. 散布図!AY 記録日数をキー結合に ----------------
    s = parts['xl/worksheets/sheet7.xml'].decode('utf-8')
    n = 0
    for r in range(8, 68):
        p = r - 1
        old = 'IF(AND(ISNUMBER(入力!$F$%d),入力!$F$%d&gt;0),入力!$F$%d,"")' % (p + 3, p + 3, p + 3)
        new = ('IFERROR(IF(INDEX(入力!$F:$F,ピッキング!$V$%d)&gt;0,'
               'INDEX(入力!$F:$F,ピッキング!$V$%d),""),"")' % (p, p))
        m = cell_block(s, 'AY%d' % r)
        assert old in m.group(0), 'AY%d の式が想定と違う: %s' % (r, m.group(0)[:160])
        s = s[:m.start()] + m.group(0).replace(old, new) + s[m.end():]
        n += 1
    print('散布図 AY8:AY67: %d セルを入力行キー結合に変更' % n)
    # 散布図の固定文 → 生きた統計値を参照する式
    s = set_formula(s, 'B53',
        '="横軸 記録日数　縦軸 引き寄せ量。相関 r="&TEXT(C55,"0.00")&"（p="&TEXT(C59,"0.00")&"）。'
        '引き寄せ量は「記録日数」と「平均からの距離」の両方で決まるため、一直線にはなりません。"', '')
    S.note_removed(1)
    s = S.replace(s, 'B148', '記録3日の人は 12.5ポイント',
        '　 記録日数が少ない人ほど大きく動きます（縦軸が動いた量）。少ない日数の数字で人を評価しないための補正です。')
    s = set_formula(s, 'B150',
        '="　 日数との相関は r="&TEXT(C55,"0.00")&"。日数が少ないほど大きく動きますが、一直線にはなりません。"', '')
    S.note_removed(1)
    s = S.replace(s, 'B152', '②の p 値は', '※ ②の p 値は、このブックの「入力」シートの企業数からその場で計算しています。')
    s = set_formula(s, 'B153',
        '="　 現在の値は r="&TEXT(C19,"0.00")&"、p="&TEXT(C23,"0.00")&"。0.05 を上回るので、統計的には「傾きは無いと言ってよい」範囲です。"', '')
    S.note_removed(1)
    s = S.replace(s, 'B154', '0.64〜0.65', '　 ただし相関が完全には消えていない分は、補正しきれていない可能性として説明書にも書いています。')
    s = S.replace(s, 'B155', 'どの取り方でも', '　 入力データを差し替えると、この r・p も自動で計算し直されます。')
    parts['xl/worksheets/sheet7.xml'] = s.encode('utf-8')
    print('散布図: B53/B150/B153 を数式に、B148/B152/B154/B155 の文言を更新')

    # ---------------- B. ダッシュボード ----------------
    s = parts['xl/worksheets/sheet1.xml'].decode('utf-8')
    for ref, old in (('AX3', '233.2'), ('AX4', '223.1'), ('AX5', '223.1')):
        m = cell_block(s, ref)
        assert '<v>%s</v>' % old in m.group(0), ref
    s = set_formula(s, 'AX3', '=ピッキング!$X$13/60', 141.6)
    s = set_formula(s, 'AX4', '=設定!$E$7/2*ピッキング!$X$10/3600', 223.1)
    s = set_formula(s, 'AX5', '=設定!$E$7/2*ピッキング!$X$10/3600', 223.1)
    TXT = [
        ('B8', '="●　1社ごとの段取りが "&TEXT(AX3,"0.0")&" 時間。ピッキング標準時間の "&TEXT(AY3,"0.0%")&" を占めています。"'),
        ('B18', '="段取り "&TEXT(ピッキング!$X$13/60,"0.0")&"h ÷ ピッキング実働 "&TEXT(ピッキング!$X$12/60,"0.0")&"h。下がるのは良いこと"'),
        ('B98', '="ピッキングの標準時間 "&TEXT(ピッキング!$X$14/60,"0.0")&" 時間を作業単位で分解。手を動かしているのは約"&TEXT(AY5*10,"0")&"割です。（移動とピックは b="&設定!$E$7&"秒/件 を半分ずつと仮定した内訳で、実測ではありません）"'),
        ('F18', '="ピッキング "&TEXT(ピッキング!$X$12/60,"0.0")&"h ＋ 梱包 "&TEXT(梱包!$X$12/60,"0.0")&"h"'),
        ('G3', '="対象 "&ピッキング!$X$5&"名・"&TEXT(ピッキング!$X$10+梱包!$X$10,"#,##0")&"件・完全記録 "&COUNT(日次!$P$8:$P$28)&"日分"'),
        ('B13', '="ピッキング "&TEXT(ピッキング!$X$10,"#,##0")&"件 ＋ 梱包 "&TEXT(梱包!$X$10,"#,##0")&"件。物量は需要であって成績ではない"'),
        ('B150', '="→ ピッキング "&ピッキング!$X$5&"名の明細"'),
        ('D150', '="→ 梱包 "&梱包!$X$5&"名の明細"'),
        ('B235', '="対象 "&ピッキング!$X$5&"名・"&TEXT(ピッキング!$X$10+梱包!$X$10,"#,##0")&"件・完全記録 "&COUNT(日次!$P$8:$P$28)&"日分　／　梱包の a="&設定!$E$8&" は統計的に0と区別できない（値より不安定さが実態）"'),
    ]
    for ref, f in TXT:
        assert 't="s"' in cell_block(s, ref).group(0), ref + ' が共有文字列セルではない'
        s = set_formula(s, ref, f, '')
    S.note_removed(len(TXT))
    for ref in ('B12', 'F12', 'B17', 'F17'):
        s = clear_cell(s, ref)
    parts['xl/worksheets/sheet1.xml'] = s.encode('utf-8')
    print('ダッシュボード: AX3:AX5 と固定文 %d 件を数式に、前週比 4 セルを消去' % len(TXT))

    # ---------------- C. 印刷用!B62 と 印刷用データ ----------------
    s = parts['xl/worksheets/sheet2.xml'].decode('utf-8')
    s = edit_formula(s, 'B62',
        '③ でもう一方の実績が無い "&amp;(COUNT(印刷用データ!AS3:AS62)-COUNT(印刷用データ!N3:N62))&amp;" 名は、下の帯に灰色の三角で並べています。',
        '③ でピッキングの実績しか無い "&amp;COUNTIF(印刷用データ!AK3:AK62,"PKのみ")&amp;" 名は、下の帯に灰色の三角で並べています。')
    s = edit_formula(s, 'B62',
        '③ は縦横とも 10〜190% の範囲で描いています。範囲外のため図に出ていない人が "&amp;SUM(印刷用データ!BD3:BD62)&amp;" 名います。","")',
        '③ は横 40〜160%・縦 10〜190% の範囲で描いています。範囲外または梱包のみのため図に出ていない人が "&amp;SUM(印刷用データ!BD3:BD62)&amp;" 名います。","")'
        '&amp;IF(COUNT(印刷用データ!AS3:AS62)&gt;50,"　【要確認】印刷用の表とグラフに載るのは 50 名までです。51 人目以降は載りません。","")')
    parts['xl/worksheets/sheet2.xml'] = s.encode('utf-8')
    print('印刷用 B62: 軸範囲の注記を 横40〜160/縦10〜190 に、梱包のみ・51人目以降の注記を追加')

    s = parts['xl/worksheets/sheet12.xml'].decode('utf-8')
    for r in (3, 35):
        s = edit_formula(s, 'AW%d' % r,
            'CHOOSE(MOD($AY%d-1,6)+1,12,18,24,30,36,42)' % r, '0')
        s = edit_formula(s, 'BD%d' % r,
            'AND(ISNUMBER($AI{r}),OR($AI{r}&lt;10,$AI{r}&gt;190)))'.format(r=r),
            'AND(ISNUMBER($AI{r}),OR($AI{r}&lt;10,$AI{r}&gt;190)),$AK{r}="梱包のみ")'.format(r=r))
    parts['xl/worksheets/sheet12.xml'] = s.encode('utf-8')
    print('印刷用データ: 梱包のみ を軸外(x=0)にし、BD の軸外検知で数える（共有数式ホスト 行3・行35）')

    # ---------------- D. 説明文 ----------------
    s = parts['xl/worksheets/sheet3.xml'].decode('utf-8')
    s = S.replace(s, 'L16', '日数未入力',
        '記録日数が空欄の人は、縮小後効率と95%信頼区間が出ません（判定は達成率だけで付きます）。')
    s = S.replace(s, 'B3', '最大60名',
        '黄色のセルだけ入力してください。空欄の行は自動で無視されます（最大60名。印刷用の表とグラフに載るのは50名まで）。')
    parts['xl/worksheets/sheet3.xml'] = s.encode('utf-8')
    s = parts['xl/worksheets/sheet10.xml'].decode('utf-8')
    s = S.replace(s, 'B11', '判定の設定', '参考値（縮小後効率・信頼区間）の設定')
    parts['xl/worksheets/sheet10.xml'] = s.encode('utf-8')
    s = parts['xl/worksheets/sheet8.xml'].decode('utf-8')
    s = S.replace(s, 'C7', 'PK効率', 'PK 縮小後効率')
    s = S.replace(s, 'D7', '梱包効率', '梱包 縮小後効率')
    parts['xl/worksheets/sheet8.xml'] = s.encode('utf-8')
    s = parts['xl/worksheets/sheet9.xml'].decode('utf-8')
    s = S.replace(s, 'E10', 'いまの全体平均', 'いまの全体平均（自動）。改善を織り込むなら数字を上書き')
    # E. 想定効率を数式に
    for ref, old, f, v in (('C10', '103.4', '=ROUND(ピッキング!$X$3,1)', 89.7),
                           ('D10', '109.2', '=ROUND(梱包!$X$3,1)', 109.4)):
        assert '<v>%s</v>' % old in cell_block(s, ref).group(0), ref
        s = set_formula(s, ref, f, v)
    parts['xl/worksheets/sheet9.xml'] = s.encode('utf-8')
    print('説明文: 入力 L16/B3、設定 B11、配置マップ C7/D7、要員予測 E10 を更新、要員予測 C10/D10 を数式に')

    c = parts['xl/charts/chart11.xml'].decode('utf-8')
    assert '<a:t>a=92.1 b=75.6</a:t>' in c
    c = c.replace('<a:t>a=92.1 b=75.6</a:t>', '<a:t>a=56.05 b=75.6</a:t>', 1)
    parts['xl/charts/chart11.xml'] = c.encode('utf-8')
    print('chart11: 題の係数を a=56.05 に')

    # ---------------- F. chart3 目標線 ----------------
    c = parts['xl/charts/chart3.xml'].decode('utf-8')
    m = re.search(r'<c:val><c:numRef><c:f>印刷用データ!\$AV\$3:\$AV\$23</c:f>(?:(?!</c:val>).)*</c:val>', c, re.S)
    assert m, 'chart3 の目標線が想定と違う'
    lit = ('<c:val><c:numLit><c:formatCode>General</c:formatCode><c:ptCount val="21"/>'
           + ''.join('<c:pt idx="%d"><c:v>100</c:v></c:pt>' % i for i in range(21))
           + '</c:numLit></c:val>')
    c = c[:m.start()] + lit + c[m.end():]
    parts['xl/charts/chart3.xml'] = c.encode('utf-8')
    print('chart3: 目標100%線を 21 点の定数に')

    S.flush()
    zout = zipfile.ZipFile(DST, 'w', zipfile.ZIP_DEFLATED)
    for nm in order:
        zi = zipfile.ZipInfo(nm, date_time=infos[nm].date_time)
        zi.compress_type = infos[nm].compress_type
        zi.external_attr = infos[nm].external_attr
        zout.writestr(zi, parts[nm])
    zout.close()


main()
