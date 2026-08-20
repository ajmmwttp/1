# -*- coding: utf-8 -*-
"""段1-2: 散布図8枚（chart11-16, chart1-2）の修復＋スタイル。

- [1]!定義名 → 静的ローカル範囲 ＋ numCache（Python算出値）
- 軸 delete=1 → 0（軸を表示。目盛りは recessive のまま）
- マーカー色: PK系=青2E75B6 / 梱包=橙C55A11 / ⑥の生の値=グレー8C8C8C(文脈)・縮小後=青
"""
import json
import re
import zipfile

SRC, DST = "j7.xlsx", "c1.xlsx"
V = json.load(open("chart_cache.json"))

def numcache(vals):
    pts = "".join(f'<c:pt idx="{i}"><c:v>{v}</c:v></c:pt>'
                  for i, v in enumerate(vals) if v is not None and v != '')
    return (f'<c:numCache><c:formatCode>General</c:formatCode>'
            f'<c:ptCount val="{len(vals)}"/>{pts}</c:numCache>')

def swap_ref(x, old_name, new_ref, vals):
    old = f'<c:f>{old_name}</c:f>'
    assert old in x, f"{old_name} が無い"
    return x.replace(old, f'<c:f>{new_ref}</c:f>{numcache(vals)}', 1)

def show_axes(x):
    n = x.count('<c:delete val="1"/>')
    return x.replace('<c:delete val="1"/>', '<c:delete val="0"/>'), n

def set_marker(x, ser_idx, color):
    # 系列 idx=ser_idx の marker 色を差し替え
    sers = re.findall(r'<c:ser>.*?</c:ser>', x, re.S)
    for s in sers:
        if f'<c:idx val="{ser_idx}"/>' in s:
            new = re.sub(r'(<c:marker>.*?)<a:srgbClr val="[0-9A-F]{6}"/>(.*?)<a:srgbClr val="[0-9A-F]{6}"/>(.*?</c:marker>)',
                         rf'\g<1><a:srgbClr val="{color}"/>\g<2><a:srgbClr val="{color}"/>\g<3>',
                         s, count=1, flags=re.S)
            assert new != s or f'val="{color}"' in s, f"marker色を変更できない (idx={ser_idx})"
            return x.replace(s, new, 1)
    raise AssertionError(f"系列 idx={ser_idx} が無い")

D8 = lambda c: f'散布図!${c}$8:${c}$67'
D3 = lambda c: f'ダッシュボード!${c}$3:${c}$62'

JOBS = {
 'chart11': [( '[1]!_s1x', D8('AE'), V['s1x']), ('[1]!_s1y', D8('AF'), V['s1y'])],
 'chart12': [( '[1]!_s2x', D8('AI'), V['s2x']), ('[1]!_s2y', D8('AJ'), V['s2y'])],
 'chart13': [( '[1]!_s3x', D8('AM'), V['s3x']), ('[1]!_s3y', D8('AN'), V['s3y'])],
 'chart14': [( '[1]!_s4x', D8('AQ'), V['s4x']), ('[1]!_s4y', D8('AR'), V['s4y'])],
 'chart15': [( '[1]!_s5x', D8('BE'), V['s5x']), ('[1]!_s5y', D8('BF'), V['s5y'])],
 'chart16': [( '[1]!_s6x', D8('BJ'), V['s6x']), ('[1]!_s6y', D8('BK'), V['s6y']),
             ( '[1]!_s6x', D8('BJ'), V['s6x']), ('[1]!_s6z', D8('BL'), V['s6z'])],
 'chart1':  [( '[1]!_dbS1x', D3('AF'), V['db_s1x']), ('[1]!_dbS1y', D3('AG'), V['db_s1y'])],
 'chart2':  [( '[1]!_dbS2x', D3('AK'), V['db_s2x']), ('[1]!_dbS2y', D3('AL'), V['db_s2y'])],
}
COLORS = {'chart13': [(0, 'C55A11')], 'chart16': [(0, '8C8C8C'), (1, '2E75B6')]}

zi = zipfile.ZipFile(SRC); zo = zipfile.ZipFile(DST, "w", zipfile.ZIP_DEFLATED)
for it in zi.infolist():
    b = zi.read(it.filename)
    m = re.match(r'xl/charts/(chart\d+)\.xml$', it.filename)
    if m and m.group(1) in JOBS:
        x = b.decode("utf-8")
        for old, new, vals in JOBS[m.group(1)]:
            x = swap_ref(x, old, new, vals)
        for idx, color in COLORS.get(m.group(1), []):
            x = set_marker(x, idx, color)
        x, n_ax = show_axes(x)
        print(f"{m.group(1)}: 参照{len(JOBS[m.group(1)])}件差替 / 軸表示化{n_ax}本")
        b = x.encode("utf-8")
    zo.writestr(it, b)
zo.close(); zi.close()
print("wrote", DST)
