# -*- coding: utf-8 -*-
"""段2: ③マトリクスの見やすさ改善（チャート側 chart10）。

  - 横軸（ピッキング効率）を 10〜190 → 40〜160 に。100%が中央のままなので
    四隅の象限ラベル・帯・基準線はそのまま使える
  - 全系列に名前ラベルを持たせる（点は出るのに名前が出ていない人がいたため）
  - ラベルを 6pt → 7pt。位置は「100%を境に外向き」（梱包効率100%以上なら
    点の上、未満なら点の下）。データが変わっても崩れない規則で重なりを減らす
"""
import re, sys, zipfile
import openpyxl

SRC, DST, VALS = sys.argv[1], sys.argv[2], sys.argv[3]
CHART = 'xl/charts/chart10.xml'
NEW_MIN, NEW_MAX, FONT = '40', '160', '700'

DLBLS = ('<c:dLbls><c:spPr><a:noFill/><a:ln><a:noFill/></a:ln></c:spPr>'
         '<c:txPr><a:bodyPr/><a:lstStyle/><a:p><a:pPr><a:defRPr sz="%s"/></a:pPr>'
         '<a:endParaRPr lang="ja-JP"/></a:p></c:txPr><c:dLblPos val="%s"/>'
         '<c:showLegendKey val="0"/><c:showVal val="0"/><c:showCatName val="0"/>'
         '<c:showSerName val="1"/><c:showPercent val="0"/><c:showBubbleSize val="0"/>'
         '<c:showLeaderLines val="0"/></c:dLbls>')


def main():
    ws = openpyxl.load_workbook(VALS, data_only=True)['印刷用データ']
    zin = zipfile.ZipFile(SRC)
    parts = {n: zin.read(n) for n in zin.namelist()}
    infos = {i.filename: i for i in zin.infolist()}
    order = zin.namelist()
    zin.close()

    s = parts[CHART].decode('utf-8')

    # --- 横軸（1本目の valAx = ピッキング効率）の min/max ---
    m = re.search(r'<c:valAx>(?:(?!</c:valAx>).)*?</c:valAx>', s, re.S)
    ax = m.group(0)
    assert 'ピッキング効率' in ax, '1本目の軸が横軸ではない'
    assert '<c:min val="10"/>' in ax and '<c:max val="190"/>' in ax
    ax2 = (ax.replace('<c:min val="10"/>', '<c:min val="%s"/>' % NEW_MIN)
             .replace('<c:max val="190"/>', '<c:max val="%s"/>' % NEW_MAX))
    s = s[:m.start()] + ax2 + s[m.end():]
    print('横軸（ピッキング効率）: 10〜190 → %s〜%s' % (NEW_MIN, NEW_MAX))

    # --- 系列のラベル ---
    out, pos_end = [], 0
    n_add = n_font = n_flip = 0
    for m in re.finditer(r'<c:ser>(?:(?!</c:ser>).)*?</c:ser>', s, re.S):
        ser = m.group(0)
        fs = re.findall(r'<c:f>([^<]*)</c:f>', ser)
        out.append(s[pos_end:m.start()])
        pos_end = m.end()
        if len(fs) < 3:                       # 基準線2本は対象外
            out.append(ser)
            continue
        band = 'AW' in fs[1]
        row = int(re.search(r'\$(\d+)$', fs[0]).group(1))
        # 混み合う中央を避けてラベルを外向きに置く。
        #   帯 … グラフ下端に近いので必ず点の上（下だと軸の目盛に重なる）
        #   両方組 … 梱包効率 100%以上は上、60%未満も上（下だと帯にぶつかる）、
        #            その間は下。データが変わっても崩れない固定の規則
        y = ws.cell(row, 35).value
        want = 't' if (band or not isinstance(y, (int, float))
                       or y >= 100 or y < 60) else 'b'
        if want == 'b':
            n_flip += 1
        block = DLBLS % (FONT, want)
        md = re.search(r'<c:dLbls>(?:(?!</c:dLbls>).)*?</c:dLbls>', ser, re.S)
        if md:
            ser = ser[:md.start()] + block + ser[md.end():]
            n_font += 1
        else:
            # dLbls は <c:spPr> の直後（無ければ <c:tx> の直後）に置く
            anchor = re.search(r'</c:spPr>', ser) or re.search(r'</c:tx>', ser)
            ser = ser[:anchor.end()] + block + ser[anchor.end():]
            n_add += 1
        out.append(ser)
    out.append(s[pos_end:])
    s = ''.join(out)
    print('ラベル: 既存 %d 件を %spt に / 新規付与 %d 件（点は出るのに名前が無かった系列）'
          % (n_font, int(FONT) / 100, n_add))
    print('        うち %d 系列は点の下側に配置（100%%未満のため外向き）' % n_flip)

    parts[CHART] = s.encode('utf-8')
    zout = zipfile.ZipFile(DST, 'w', zipfile.ZIP_DEFLATED)
    for nm in order:
        zi = zipfile.ZipInfo(nm, date_time=infos[nm].date_time)
        zi.compress_type = infos[nm].compress_type
        zi.external_attr = infos[nm].external_attr
        zout.writestr(zi, parts[nm])
    zout.close()


main()
