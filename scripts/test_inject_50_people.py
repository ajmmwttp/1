# -*- coding: utf-8 -*-
"""入力シートに50名分のテストデータを投入する（連動確認用）。

openpyxl では保存しない（グラフ16点・図形・外部リンクが壊れるため）。
xl/worksheets/sheet3.xml（入力）だけを直接書き換える。
"""
import random
import re
import zipfile

SRC, DST = "base.xlsx", "test50.xlsx"
FIRST, N = 10, 50          # 入力の先頭行 / 投入人数
N_BOTH, N_PK, N_PACK = 40, 8, 2
assert N_BOTH + N_PK + N_PACK == N

rnd = random.Random(20260418)          # 再現できるよう種を固定

def make(i):
    """i 番目(0始まり)の1行分。工程の内訳は 両方40 / PKのみ8 / 梱包のみ2。"""
    name = f"検証{i+1:02d}"
    pk   = (rnd.randint(400, 2500), rnd.randint(700, 2600),
            rnd.randint(150, 700),  rnd.randint(10, 20))
    pack = (rnd.randint(400, 2500), rnd.randint(700, 2600),
            rnd.randint(150, 700),  rnd.randint(10, 20))
    if i < N_BOTH:            proc = "両方"
    elif i < N_BOTH + N_PK:   proc, pack = "PKのみ",   None
    else:                     proc, pk   = "梱包のみ", None
    return name, pk, pack, proc

def row_xml(r, name, pk, pack):
    def numc(ref, v):
        return f'<c r="{ref}" s="43">{f"<v>{v}</v>" if v is not None else ""}</c>'
    cells = [f'<c r="A{r}" s="41"><f>IF(B{r}="","",COUNTA($B$10:B{r}))</f><v/></c>',
             f'<c r="B{r}" s="42" t="inlineStr"><is><t>{name}</t></is></c>']
    for col, v in zip("CDEF", pk   or (None,)*4): cells.append(numc(f"{col}{r}", v))
    for col, v in zip("GHIJ", pack or (None,)*4): cells.append(numc(f"{col}{r}", v))
    return (f'<row r="{r}" spans="1:10" x14ac:dyDescent="0.15">'
            + "".join(cells) + "</row>")

people = [make(i) for i in range(N)]

def patch_input(x):
    for i, (name, pk, pack, _) in enumerate(people):
        r = FIRST + i
        m = re.search(r'<row\b[^>]*\br="%d"[^>]*?(?:/>|>.*?</row>)' % r, x, re.S)
        assert m, f"入力 行{r} が無い"
        keep = re.search(r'<c r="L%d".*?</c>' % r, m.group(0), re.S)   # 説明文は残す
        new = row_xml(r, name, pk, pack)
        if keep:
            new = new.replace("</row>", keep.group(0) + "</row>")
        x = x[:m.start()] + new + x[m.end():]
    # 51行目以降は空にする（前回の29名分が残らないように）
    for r in range(FIRST + N, 70):
        m = re.search(r'<row\b[^>]*\br="%d"[^>]*?(?:/>|>.*?</row>)' % r, x, re.S)
        if not m: continue
        blank = (f'<row r="{r}" spans="1:10" x14ac:dyDescent="0.15">'
                 f'<c r="A{r}" s="41" t="str"><f>IF(B{r}="","",COUNTA($B$10:B{r}))</f><v/></c>'
                 + "".join(f'<c r="{c}{r}" s="{42 if c=="B" else 43}"/>' for c in "BCDEFGHIJ")
                 + "</row>")
        x = x[:m.start()] + blank + x[m.end():]
    return x

# 外部リンクは検証の邪魔になるので、テスト用コピーからは外す
zi = zipfile.ZipFile(SRC); zo = zipfile.ZipFile(DST, "w", zipfile.ZIP_DEFLATED)
for it in zi.infolist():
    n = it.filename
    if n.startswith("xl/externalLinks/"):
        continue
    d = zi.read(n)
    if n == "xl/worksheets/sheet3.xml":
        d = patch_input(d.decode("utf-8")).encode("utf-8")
    elif n == "xl/workbook.xml":
        d = re.sub(r"<externalReferences>.*?</externalReferences>", "",
                   d.decode("utf-8"), flags=re.S).encode("utf-8")
    elif n == "xl/_rels/workbook.xml.rels":
        d = re.sub(r"<Relationship[^>]*externalLink[^>]*/>", "", d.decode("utf-8")).encode("utf-8")
    elif n == "[Content_Types].xml":
        d = re.sub(r"<Override[^>]*externalLink[^>]*/>", "", d.decode("utf-8")).encode("utf-8")
    zo.writestr(it, d)
zo.close(); zi.close()

from collections import Counter
print("投入:", Counter(p[3] for p in people))
print("wrote", DST)
