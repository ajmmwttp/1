# -*- coding: utf-8 -*-
"""段4: 棒3枚（chart5 Top12 / chart6 PKランキング / chart7 梱包ランキング）の修復。

- 参照を静的範囲＋キャッシュへ（ランキング2枚はフル60行）
- chart5 の「素の秒/件」を橙→グレー（橙は梱包のエンティティ色。生の値は文脈なので
  emphasis 形式でグレー、主役の「純速度」が青）
- 軸を表示（カテゴリ軸＝氏名が読めるように）
"""
import json
import re
import zipfile

SRC, DST = "c3.xlsx", "c4.xlsx"
V = json.load(open("chart_cache.json"))

def strcache(vals):
    pts = "".join(f'<c:pt idx="{i}"><c:v>{v}</c:v></c:pt>'
                  for i, v in enumerate(vals) if v not in (None, ''))
    return f'<c:strCache><c:ptCount val="{len(vals)}"/>{pts}</c:strCache>'

def numcache(vals):
    pts = "".join(f'<c:pt idx="{i}"><c:v>{v}</c:v></c:pt>'
                  for i, v in enumerate(vals) if v is not None and v != '')
    return (f'<c:numCache><c:formatCode>General</c:formatCode>'
            f'<c:ptCount val="{len(vals)}"/>{pts}</c:numCache>')

D3 = lambda c, r1: f'ダッシュボード!${c}$3:${c}${r1}'

def swap_cat(x, old_name, new_ref, vals, count):
    old = f'<c:multiLvlStrRef><c:f>{old_name}</c:f></c:multiLvlStrRef>'
    assert x.count(old) == count, f"{old_name}: {x.count(old)}"
    return x.replace(old, f'<c:strRef><c:f>{new_ref}</c:f>{strcache(vals)}</c:strRef>')

def swap_val(x, old_name, new_ref, vals):
    old = f'<c:numRef><c:f>{old_name}</c:f></c:numRef>'
    assert old in x, old_name
    return x.replace(old, f'<c:numRef><c:f>{new_ref}</c:f>{numcache(vals)}</c:numRef>', 1)

def patch5(x):
    x = swap_cat(x, '[1]!_dbTopName', D3('AS', 14), V['db_top_name'], 2)
    x = swap_val(x, '[1]!_dbTopRaw',  D3('AT', 14), V['db_top_raw'])
    x = swap_val(x, '[1]!_dbTopPure', D3('AU', 14), V['db_top_pure'])
    x = x.replace('<a:srgbClr val="C55A11"/>', '<a:srgbClr val="8C8C8C"/>', 1)  # 素の秒/件→グレー
    return x.replace('<c:delete val="1"/>', '<c:delete val="0"/>')

def patch6(x):
    x = swap_cat(x, '[1]!_dbPkName', D3('U', 62), V['db_pk_name'], 1)
    x = swap_val(x, '[1]!_dbPkVal',  D3('V', 62), V['db_pk_val'])
    return x.replace('<c:delete val="1"/>', '<c:delete val="0"/>')

def patch7(x):
    x = swap_cat(x, '[1]!_dbKpName', D3('W', 62), V['db_kp_name'], 1)
    x = swap_val(x, '[1]!_dbKpVal',  D3('X', 62), V['db_kp_val'])
    return x.replace('<c:delete val="1"/>', '<c:delete val="0"/>')

PATCH = {"xl/charts/chart5.xml": patch5, "xl/charts/chart6.xml": patch6,
         "xl/charts/chart7.xml": patch7}
zi = zipfile.ZipFile(SRC); zo = zipfile.ZipFile(DST, "w", zipfile.ZIP_DEFLATED)
for it in zi.infolist():
    b = zi.read(it.filename)
    fn = PATCH.get(it.filename)
    if fn:
        x = fn(b.decode("utf-8"))
        assert '[1]!' not in x
        b = x.encode("utf-8")
    zo.writestr(it, b)
zo.close(); zi.close()
print("wrote", DST)
