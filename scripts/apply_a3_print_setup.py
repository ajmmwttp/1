"""印刷用シートの印刷範囲を A3 横 1 ページに収める設定を書き込む。

openpyxl では往復させない（グラフ16点・図形3点・外部リンクが失われるため）。
xl/worksheets/sheet2.xml だけを直接書き換え、他のパートは元のまま再梱包する。
"""
import re
import shutil
import zipfile

SRC = "work.xlsx"
DST = "out.xlsx"
SHEET = "xl/worksheets/sheet2.xml"   # 印刷用

OLD_PAGESETUP = '<pageSetup paperSize="8" orientation="landscape"/>'
NEW_PAGESETUP = (
    '<pageSetup paperSize="8" orientation="landscape"'
    ' fitToWidth="1" fitToHeight="1"'
    ' horizontalDpi="600" verticalDpi="600"/>'
)
PRINT_OPTIONS = '<printOptions horizontalCentered="1"/>'


def patch_sheet(xml: str) -> str:
    # 1) fitToPage は sheetPr 側に必要（既にあるはずだが無ければ補う）
    if 'fitToPage="1"' not in xml:
        if "<sheetPr>" in xml:
            xml = xml.replace(
                "<sheetPr>", '<sheetPr><pageSetUpPr fitToPage="1"/>', 1
            )
        else:
            xml = re.sub(
                r"(<worksheet\b[^>]*>)",
                r'\1<sheetPr><pageSetUpPr fitToPage="1"/></sheetPr>',
                xml,
                count=1,
            )
        assert 'fitToPage="1"' in xml

    # 2) pageSetup を A3(paperSize=8)・横・1x1 ページに明示
    assert xml.count(OLD_PAGESETUP) == 1, "pageSetup が想定と違う"
    xml = xml.replace(OLD_PAGESETUP, NEW_PAGESETUP, 1)

    # 3) 左右中央に配置（printOptions は pageMargins の直前に置く必要がある）
    assert "<printOptions" not in xml, "printOptions が既にある"
    assert xml.count("<pageMargins") == 1
    xml = xml.replace("<pageMargins", PRINT_OPTIONS + "<pageMargins", 1)
    return xml


shutil.copy(SRC, DST + ".tmp")
zin = zipfile.ZipFile(SRC)
zout = zipfile.ZipFile(DST, "w", zipfile.ZIP_DEFLATED)
patched = False
for item in zin.infolist():
    data = zin.read(item.filename)
    if item.filename == SHEET:
        data = patch_sheet(data.decode("utf-8")).encode("utf-8")
        patched = True
    zout.writestr(item, data)
zin.close()
zout.close()
assert patched, "sheet2.xml が見つからない"
print("wrote", DST)
