# -*- coding: utf-8 -*-
"""①④の見出しが左端で切れる問題を直す。

原因: ②③の見出し（T3:AA3 / T17:AA17）は結合されているのに、
①(B3)と④(M3)は結合されていない。中央揃えのため幅4.25／4.5文字の
セルを基準に中央寄せされ、テキストが左へはみ出して切れていた。

対処: ①を B3:K3（グラフ幅）、④を M3:R3（表幅）に結合する。
あわせて ④ の帯が M3 の1セルしか塗られていなかったので N3:R3 にも
同じ塗り(s=64)を入れる。結合時の塗りの扱いに依存しないようにするため。
"""
import re
import zipfile

SRC, DST = "cur2.xlsx", "out6.xlsx"
MERGES = ["B3:K3", "M3:R3"]      # ① / ④
BAND_TAIL = "NOPQR"              # ④ の帯を広げる列

def patch(x):
    m = re.search(r'<mergeCells count="(\d+)">', x)
    assert m, "mergeCells が無い"
    for ref in MERGES:
        assert f'ref="{ref}"' not in x, f"{ref} は既に結合済み"
    n = int(m.group(1))
    x = x.replace(m.group(0),
                  f'<mergeCells count="{n + len(MERGES)}">'
                  + "".join(f'<mergeCell ref="{r}"/>' for r in MERGES), 1)
    for c in BAND_TAIL:
        old = f'<c r="{c}3" s="63"/>'
        assert old in x, f"{c}3 が想定の形ではない"
        x = x.replace(old, f'<c r="{c}3" s="64"/>', 1)
    return x

zi = zipfile.ZipFile(SRC); zo = zipfile.ZipFile(DST, "w", zipfile.ZIP_DEFLATED)
for it in zi.infolist():
    d = zi.read(it.filename)
    if it.filename == "xl/worksheets/sheet2.xml":
        d = patch(d.decode("utf-8")).encode("utf-8")
    zo.writestr(it, d)
zo.close(); zi.close()
print("wrote", DST)
