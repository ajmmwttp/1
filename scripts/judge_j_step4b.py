# -*- coding: utf-8 -*-
"""段4b: 行の色付け（条件付き書式）を4区分に合わせる。

旧: ◎上位=緑(dxf5) / △要支援=薄橙(dxf4)
新: ◎達成=緑(dxf5) / △要改善=薄橙(dxf4) / ✕要支援=赤(dxf8 新設)
"""
import re
import zipfile

SRC, DST = "j4.xlsx", "j5.xlsx"
NEW_DXF = ('<dxf><fill><patternFill patternType="solid">'
           '<fgColor rgb="FFFFC7CE"/><bgColor rgb="FFFFC7CE"/></patternFill></fill></dxf>')

def patch_styles(x):
    m = re.search(r'<dxfs count="(\d+)">', x)
    assert m and int(m.group(1)) == 8, f"dxfs count が想定外: {m.group(1) if m else None}"
    x = x.replace(m.group(0), '<dxfs count="9">', 1)
    return x.replace('</dxfs>', NEW_DXF + '</dxfs>', 1)

def patch_sheet(x):
    # シートごとに dxfId が違う（sheet4: 緑5/橙4, sheet5: 緑3/橙2）ため正規表現で拾う
    pat = re.compile(
        r'<conditionalFormatting sqref="A7:R66">'
        r'<cfRule type="expression" dxfId="(\d+)" priority="1"><formula>\$O7="◎上位"</formula></cfRule>'
        r'<cfRule type="expression" dxfId="(\d+)" priority="2"><formula>\$O7="△要支援"</formula></cfRule>'
        r'</conditionalFormatting>')
    m = pat.search(x)
    assert m, "条件付き書式が想定と違う"
    g_green, g_orange = m.group(1), m.group(2)
    new = ('<conditionalFormatting sqref="A7:R66">'
           f'<cfRule type="expression" dxfId="{g_green}" priority="1"><formula>$O7="◎達成"</formula></cfRule>'
           f'<cfRule type="expression" dxfId="{g_orange}" priority="2"><formula>$O7="△要改善"</formula></cfRule>'
           '<cfRule type="expression" dxfId="8" priority="3"><formula>$O7="✕要支援"</formula></cfRule>'
           '</conditionalFormatting>')
    return x.replace(m.group(0), new, 1)

PATCH = {"xl/styles.xml": patch_styles,
         "xl/worksheets/sheet4.xml": patch_sheet,
         "xl/worksheets/sheet5.xml": patch_sheet}
zi = zipfile.ZipFile(SRC); zo = zipfile.ZipFile(DST, "w", zipfile.ZIP_DEFLATED)
for it in zi.infolist():
    b = zi.read(it.filename)
    fn = PATCH.get(it.filename)
    if fn:
        b = fn(b.decode("utf-8")).encode("utf-8")
    zo.writestr(it, b)
zo.close(); zi.close()
print("wrote", DST)
