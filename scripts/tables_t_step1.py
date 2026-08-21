# -*- coding: utf-8 -*-
"""ピッキング・梱包の表（A6:R66）を Excel テーブル（ListObject）にする。

ユーザー決定: 縞模様なし（判定の行色を優先）・集計行なし。
- xl/tables/table1.xml / table2.xml を新設
- sheet4/sheet5 の rels を新規作成し tableParts を挿入
- 列名は見出しセルの文字列（改行含む）と完全一致させる
"""
import re
import zipfile

import openpyxl

SRC, DST = "c7.xlsx", "t1.xlsx"

wv = openpyxl.load_workbook(SRC, data_only=True)
HEADERS = {}
for nm, key in [("ピッキング", "sheet4"), ("梱包", "sheet5")]:
    HEADERS[key] = [wv[nm].cell(6, c).value for c in range(1, 19)]
    assert all(HEADERS[key]) and len(set(HEADERS[key])) == 18

def esc(s):
    return (s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
             .replace('"', "&quot;").replace("\n", "&#10;"))

def table_xml(tid, name, headers):
    cols = "".join(f'<tableColumn id="{i+1}" name="{esc(h)}"/>'
                   for i, h in enumerate(headers))
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<table xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
        f'id="{tid}" name="{name}" displayName="{name}" ref="A6:R66" '
        'headerRowCount="1" totalsRowShown="0">'
        '<autoFilter ref="A6:R66"/>'
        f'<tableColumns count="18">{cols}</tableColumns>'
        '<tableStyleInfo showFirstColumn="0" showLastColumn="0" '
        'showRowStripes="0" showColumnStripes="0"/></table>')

RELS = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" '
        'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/table" '
        'Target="../tables/table{n}.xml"/></Relationships>')

def patch_sheet(x):
    # r 名前空間の宣言を確認（無ければ追加）
    m = re.match(r'(<\?xml[^>]*\?>\s*)(<worksheet[^>]*>)', x)
    assert m, "worksheet 開始タグが想定と違う"
    if 'xmlns:r=' not in m.group(2):
        x = x.replace(m.group(2), m.group(2)[:-1]
                      + ' xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">', 1)
    assert '<tableParts' not in x
    return x.replace('</worksheet>',
                     '<tableParts count="1"><tablePart r:id="rId1"/></tableParts></worksheet>', 1)

def patch_ct(x):
    assert 'table+xml' not in x
    ov = ('<Override PartName="/xl/tables/table1.xml" '
          'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.table+xml"/>'
          '<Override PartName="/xl/tables/table2.xml" '
          'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.table+xml"/>')
    return x.replace('</Types>', ov + '</Types>', 1)

zi = zipfile.ZipFile(SRC); zo = zipfile.ZipFile(DST, "w", zipfile.ZIP_DEFLATED)
for it in zi.infolist():
    b = zi.read(it.filename)
    if it.filename in ("xl/worksheets/sheet4.xml", "xl/worksheets/sheet5.xml"):
        b = patch_sheet(b.decode("utf-8")).encode("utf-8")
    elif it.filename == "[Content_Types].xml":
        b = patch_ct(b.decode("utf-8")).encode("utf-8")
    zo.writestr(it, b)
zo.writestr("xl/tables/table1.xml", table_xml(1, "Tbl_PK", HEADERS["sheet4"]).encode("utf-8"))
zo.writestr("xl/tables/table2.xml", table_xml(2, "Tbl_KP", HEADERS["sheet5"]).encode("utf-8"))
zo.writestr("xl/worksheets/_rels/sheet4.xml.rels", RELS.format(n=1).encode("utf-8"))
zo.writestr("xl/worksheets/_rels/sheet5.xml.rels", RELS.format(n=2).encode("utf-8"))
zo.close(); zi.close()
print("wrote", DST)
