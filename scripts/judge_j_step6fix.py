# -*- coding: utf-8 -*-
"""段6fix: R列の幅を 2（旧スペーサー）→ 10 に。step1で追加した重複定義は削除。"""
import zipfile

SRC, DST = "j6.xlsx", "j7.xlsx"

def patch(x):
    old = '<col min="18" max="18" width="2" customWidth="1"/>'
    assert old in x
    return x.replace(old, '<col min="18" max="18" width="10" customWidth="1"/>', 1)

zi = zipfile.ZipFile(SRC); zo = zipfile.ZipFile(DST, "w", zipfile.ZIP_DEFLATED)
for it in zi.infolist():
    b = zi.read(it.filename)
    if it.filename in ("xl/worksheets/sheet4.xml", "xl/worksheets/sheet5.xml"):
        b = patch(b.decode("utf-8")).encode("utf-8")
    zo.writestr(it, b)
zo.close(); zi.close()
print("wrote", DST)
