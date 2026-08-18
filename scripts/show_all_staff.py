# -*- coding: utf-8 -*-
"""②③を「片方の工程しかない人」も含む全員表示にする。

利用者の選択:
  ② … 全員（良い順 AP/AQ/AR/AV）に切り替え。梱包が無い人は梱包の棒が出ないだけ。
  ③ … 案A（軸を下げて専用の帯を作る）＋ 片方のみは灰色の三角で区別。

③ の仕組み:
  - 「両方」の人 : x=AH(PK効率)  y=AI(梱包効率)   → 通常の四象限に配置（青丸）
  - 「片方のみ」 : x=AW  y=AX（新設の補助列）      → 帯に配置（灰色三角）
      PKのみ → x は実際のPK効率、y は帯（30）
      梱包のみ → x は帯（30）、y は実際の梱包効率
  どちらの列も数式なので、月次でデータを入れ替えれば自動で振り分けられる。
"""
import re
import zipfile
from collections import Counter

SRC, DST = "cur.xlsx", "out4.xlsx"
D        = "印刷用データ"
N        = 50
SRC_LAST = 62
BAND_LV  = (12.0, 17.0, 22.0, 27.0, 32.0, 37.0)   # 帯の6段（名前の重なりを避ける）
AX_MIN   = 10.0          # 軸下限（旧 40）… 10〜40 が帯
AX_MAX   = 190.0
LBL_SZ   = "600"

BLUE, GRAY = "2E75B6", "7F7F7F"

# ---------------------------------------------------------------- 補助列
def patch_data_sheet(x, rows, seqs):
    """印刷用データ に AW/AX（帯の座標）と AZ..BC（帯の境界線）を追加。"""
    assert '<c r="AW' not in x, "AW 列が既にある"

    def cell(ref, style, formula=None, value=None, tstr=False):
        t = ' t="str"' if tstr else ''
        f = f'<f>{formula}</f>' if formula else ''
        v = f'<v>{value}</v>' if value is not None else ('<v/>' if formula else '')
        return f'<c r="{ref}" s="{style}"{t}>{f}{v}</c>'

    def inline(ref, text):
        return f'<c r="{ref}" s="39" t="inlineStr"><is><t>{text}</t></is></c>'

    # 見出し（row 2）と帯の境界線の定数（row 2,3）
    x = x.replace('<c r="AV2" s="39" t="s"><v>443</v></c></row>',
                  '<c r="AV2" s="39" t="s"><v>443</v></c>'
                  + inline("AW2", "片方x") + inline("AX2", "片方y") + inline("AY2", "片方通番")
                  + '<c r="AZ2" s="39"><v>10</v></c><c r="BA2" s="39"><v>40</v></c>'
                  + '<c r="BB2" s="39"><v>40</v></c><c r="BC2" s="39"><v>10</v></c></row>', 1)
    assert '<c r="AW2"' in x

    x = x.replace('<c r="Z1" s="39" t="s"><v>427</v></c></row>',
                  '<c r="Z1" s="39" t="s"><v>427</v></c>'
                  + inline("AZ1", "帯線横X") + inline("BA1", "帯線横Y")
                  + inline("BB1", "帯線縦X") + inline("BC1", "帯線縦Y") + '</row>', 1)

    # 各行に AW/AX（row 3 には帯の境界線の2点目も）
    for r in range(3, SRC_LAST + 1):
        # XML なので < と & はエスケープして書く
        ay = (f'IF($AK{r}="PKのみ",COUNTIFS($AK$3:$AK${SRC_LAST},"PKのみ",'
              f'$AH$3:$AH${SRC_LAST},"&lt;"&amp;$AH{r})+1,'
              f'IF($AK{r}="梱包のみ",COUNTIFS($AK$3:$AK${SRC_LAST},"梱包のみ",'
              f'$AI$3:$AI${SRC_LAST},"&lt;"&amp;$AI{r})+1,""))')
        lv = (f'CHOOSE(MOD($AY{r}-1,{len(BAND_LV)})+1,'
              + ",".join(f"{v:g}" for v in BAND_LV) + ')')
        aw = f'IF($AY{r}="","",IF($AK{r}="PKのみ",$AH{r},{lv}))'
        ax = f'IF($AY{r}="","",IF($AK{r}="PKのみ",{lv},$AI{r}))'
        got = rows.get(r)
        seq = seqs.get(r)
        add = (cell(f"AW{r}", "62", aw, got[0] if got else None, tstr=not got)
               + cell(f"AX{r}", "62", ax, got[1] if got else None, tstr=not got)
               + cell(f"AY{r}", "62", ay, seq, tstr=seq is None))
        if r == 3:
            add += ('<c r="AZ3" s="39"><v>190</v></c><c r="BA3" s="39"><v>40</v></c>'
                    '<c r="BB3" s="39"><v>40</v></c><c r="BC3" s="39"><v>190</v></c>')
        m = re.search(r'(<row r="%d"[ >].*?)(</row>)' % r, x, re.S)
        assert m, f"row {r} が無い"
        x = x[:m.start(2)] + add + x[m.start(2):]

    # dimension / spans / cols を新しい最終列 BC(55) に合わせる
    x = x.replace('<dimension ref="A1:AV62"/>', '<dimension ref="A1:BC62"/>', 1)
    x = x.replace('spans="1:48"', 'spans="1:55"')
    x = x.replace('<col min="1" max="48" width="11" customWidth="1"/>',
                  '<col min="1" max="55" width="11" customWidth="1"/>', 1)
    return x

# ---------------------------------------------------------------- ラベル配置
PT_X, PT_Y = (AX_MAX - AX_MIN) / 290.0, (AX_MAX - AX_MIN) / 300.0
GAP = 5 * PT_Y
ORDER = ["t", "b", "r", "l"]

def rect(x, y, pos, name):
    w, h = len(name) * 6 * PT_X, 8 * PT_Y
    if pos == "t": return (x - w/2, y + GAP, x + w/2, y + GAP + h)
    if pos == "b": return (x - w/2, y - GAP - h, x + w/2, y - GAP)
    if pos == "r": return (x + GAP, y - h/2, x + GAP + w, y + h/2)
    return (x - GAP - w, y - h/2, x - GAP, y + h/2)

def free(a, b): return a[2] <= b[0] or b[2] <= a[0] or a[3] <= b[1] or b[3] <= a[1]
def inside(r):  return r[0] >= AX_MIN and r[2] <= AX_MAX and r[1] >= AX_MIN and r[3] <= AX_MAX

def assign(points):
    placed, out = [], {}
    for k in sorted(points, key=lambda k: -points[k][1]):
        x, y, nm = points[k]
        for pos in ORDER:
            r = rect(x, y, pos, nm)
            if inside(r) and all(free(r, p) for p in placed):
                out[k] = pos; placed.append(r); break
        else:
            out[k] = "t"; placed.append(rect(x, y, "t", nm))
    return out

# ---------------------------------------------------------------- データ読み込み
import openpyxl
_wb = openpyxl.load_workbook(SRC, data_only=True)
_ws = _wb[D]
PEOPLE = {}                      # 行 -> (氏名, PK, 梱包, 工程)
for r in range(3, SRC_LAST + 1):
    nm = _ws[f"AG{r}"].value
    if nm:
        PEOPLE[r] = (nm, _ws[f"AH{r}"].value, _ws[f"AI{r}"].value, _ws[f"AK{r}"].value)
BAR = {}                         # ②用（良い順・全員）
for r in range(3, SRC_LAST + 1):
    nm = _ws[f"AP{r}"].value
    if nm:
        BAR[r] = (nm, _ws[f"AQ{r}"].value, _ws[f"AR{r}"].value, _ws[f"AV{r}"].value)
print(f"全員 {len(PEOPLE)} 名 / 工程内訳 {Counter(v[3] for v in PEOPLE.values())}")

BAND_XY, BAND_SEQ = {}, {}       # 行 -> (AW, AX) / 帯内の並び順
for proc, key in (("PKのみ", 1), ("梱包のみ", 2)):
    grp = [r for r in PEOPLE if PEOPLE[r][3] == proc]
    for rank, r in enumerate(sorted(grp, key=lambda k: PEOPLE[k][key]), start=1):
        BAND_SEQ[r] = rank
        lv = BAND_LV[(rank - 1) % len(BAND_LV)]
        BAND_XY[r] = (PEOPLE[r][1], lv) if proc == "PKのみ" else (lv, PEOPLE[r][2])

# ラベル位置は「実際に描かれる座標」で衝突を解く
eff = {r: (v[1], v[2], v[0]) for r, v in PEOPLE.items() if v[3] == "両方"}
POS = assign(eff)
for r in BAND_XY:          # 帯の点は段で分離済み。ラベルは右に置き、縦幅を節約する
    POS[r] = "r"
print("ラベル位置:", Counter(POS.values()))

# ---------------------------------------------------------------- ③ chart10
def num(ref, val):
    pt = f'<c:pt idx="0"><c:v>{val!r}</c:v></c:pt>' if val is not None else ""
    return (f'<c:numRef><c:f>{ref}</c:f><c:numCache>'
            f'<c:formatCode>0.0"%"</c:formatCode><c:ptCount val="1"/>{pt}</c:numCache></c:numRef>')

def point_series(i, idx, xcol, ycol, colour, symbol, xv, yv):
    r = 3 + i
    nm = PEOPLE.get(r, (None,))[0]
    txc = (f'<c:strCache><c:ptCount val="1"/><c:pt idx="0"><c:v>{nm}</c:v></c:pt></c:strCache>'
           if nm else "")
    return (
        f'<c:ser><c:idx val="{idx}"/><c:order val="{idx}"/>'
        f'<c:tx><c:strRef><c:f>{D}!$AG${r}</c:f>{txc}</c:strRef></c:tx>'
        '<c:spPr><a:ln><a:noFill/><a:prstDash val="solid"/></a:ln></c:spPr>'
        f'<c:marker><c:symbol val="{symbol}"/><c:size val="7"/><c:spPr>'
        f'<a:solidFill><a:srgbClr val="{colour}"/></a:solidFill>'
        '<a:ln><a:prstDash val="solid"/></a:ln></c:spPr></c:marker>'
        '<c:dLbls><c:spPr><a:noFill/><a:ln><a:noFill/></a:ln></c:spPr>'
        f'<c:txPr><a:bodyPr/><a:lstStyle/><a:p><a:pPr><a:defRPr sz="{LBL_SZ}"/></a:pPr>'
        '<a:endParaRPr lang="ja-JP"/></a:p></c:txPr>'
        f'<c:dLblPos val="{POS.get(r, "t")}"/>'
        '<c:showLegendKey val="0"/><c:showVal val="0"/><c:showCatName val="0"/>'
        '<c:showSerName val="1"/><c:showPercent val="0"/><c:showBubbleSize val="0"/></c:dLbls>'
        f'<c:xVal>{num(f"{D}!${xcol}${r}", xv)}</c:xVal>'
        f'<c:yVal>{num(f"{D}!${ycol}${r}", yv)}</c:yVal>'
        '<c:smooth val="0"/></c:ser>')

def line_series(idx, name, xref, yref, xs, ys, dash="dash"):
    def two(ref, vals):
        pts = "".join(f'<c:pt idx="{k}"><c:v>{v}</c:v></c:pt>' for k, v in enumerate(vals))
        return (f'<c:numRef><c:f>{ref}</c:f><c:numCache><c:formatCode>General</c:formatCode>'
                f'<c:ptCount val="2"/>{pts}</c:numCache></c:numRef>')
    return (f'<c:ser><c:idx val="{idx}"/><c:order val="{idx}"/><c:tx><c:v>{name}</c:v></c:tx>'
            f'<c:spPr><a:ln w="10000"><a:solidFill><a:srgbClr val="595959"/></a:solidFill>'
            f'<a:prstDash val="{dash}"/></a:ln></c:spPr>'
            '<c:marker><c:symbol val="none"/></c:marker>'
            f'<c:xVal>{two(xref, xs)}</c:xVal><c:yVal>{two(yref, ys)}</c:yVal>'
            '<c:smooth val="1"/></c:ser>')

def build_chart10(x):
    sers = re.findall(r"<c:ser>.*?</c:ser>", x, re.S)
    assert len(sers) == 52, f"系列数が想定外: {len(sers)}"
    body = []
    for i in range(N):                                   # 両方の人（青丸）
        r = 3 + i
        p = PEOPLE.get(r)
        xv, yv = (p[1], p[2]) if p and p[3] == "両方" else (None, None)
        body.append(point_series(i, i, "AH", "AI", BLUE, "circle", xv, yv))
    for i in range(N):                                   # 片方のみ（灰色三角）
        r = 3 + i
        xv, yv = BAND_XY.get(r, (None, None))
        body.append(point_series(i, N + i, "AW", "AX", GRAY, "triangle", xv, yv))
    body.append(line_series(2*N,   "基準線(縦)", f"{D}!$W$2:$W$3", f"{D}!$X$2:$X$3", [100, 100], [40, 190]))
    body.append(line_series(2*N+1, "基準線(横)", f"{D}!$Y$2:$Y$3", f"{D}!$Z$2:$Z$3", [40, 190], [100, 100]))
    body.append(line_series(2*N+2, "帯の境界(横)", f"{D}!$AZ$2:$AZ$3", f"{D}!$BA$2:$BA$3",
                            [10, 190], [40, 40], dash="solid"))
    body.append(line_series(2*N+3, "帯の境界(縦)", f"{D}!$BB$2:$BB$3", f"{D}!$BC$2:$BC$3",
                            [40, 40], [10, 190], dash="solid"))
    out = x.replace("".join(sers), "".join(body), 1)
    assert out != x
    out = out.replace('<c:max val="190"/><c:min val="40"/>',
                      f'<c:max val="190"/><c:min val="{AX_MIN:g}"/>')   # 両軸とも
    return out

# ---------------------------------------------------------------- ② chart9
def build_chart9(x):
    """両工程(R/S/T/U) → 全員(AP/AQ/AR/AV) に切り替え、キャッシュも入れ替える。"""
    order = sorted(BAR)                                   # 行3..（良い順）
    def cache(vals, fmt, strs=False):
        pts = "".join(f'<c:pt idx="{k}"><c:v>{v}</c:v></c:pt>'
                      for k, v in enumerate(vals) if v is not None)
        tag = "str" if strs else "num"
        fc = "" if strs else f"<c:formatCode>{fmt}</c:formatCode>"
        return f'<c:{tag}Cache>{fc}<c:ptCount val="{N}"/>{pts}</c:{tag}Cache>'
    repl = {
        "R": ("AP", [BAR[r][0] for r in order], True,  ""),
        "S": ("AQ", [BAR[r][1] for r in order], False, '0.0"%"'),
        "T": ("AR", [BAR[r][2] for r in order], False, '0.0"%"'),
        "U": ("AV", [BAR[r][3] for r in order], False, "General"),
    }
    for old, (new, vals, strs, fmt) in repl.items():
        oref, nref = f"{D}!${old}$3:${old}$52", f"{D}!${new}$3:${new}$52"
        assert oref in x, f"{oref} が無い"
        x = x.replace(oref, nref)
        # 直後のキャッシュを差し替え
        pat = re.compile(r'(<c:f>%s</c:f>)<c:(?:str|num)Cache>.*?</c:(?:str|num)Cache>'
                         % re.escape(nref), re.S)
        x, n = pat.subn(lambda m: m.group(1) + cache(vals, fmt, strs), x)
        assert n >= 1, f"{nref} のキャッシュ差し替え失敗"
    return x

# ---------------------------------------------------------------- 見出し
def patch_sheet2(x):
    subs = [
        ('② ピッキング・梱包 内訳比較（両工程 ', '② ピッキング・梱包 内訳比較（全員 ',
         f'COUNT({D}!$Q$3:$Q${SRC_LAST})', f'COUNT({D}!$AS$3:$AS${SRC_LAST})'),
        ('③ 改善優先度マトリクス（両工程 ', '③ 改善優先度マトリクス（全員 ',
         f'COUNT({D}!$N$3:$N${SRC_LAST})', f'COUNT({D}!$AS$3:$AS${SRC_LAST})'),
    ]
    for old_t, new_t, old_c, new_c in subs:
        assert old_t in x and old_c in x, old_t
        x = x.replace(old_t, new_t, 1).replace(old_c, new_c, 1)
    x = x.replace("（両工程 19名）", "（全員 29名）")          # キャッシュ表示
    old_note = ('"※ ①④ は実績のある全員 "&amp;COUNT(印刷用データ!AS3:AS62)&amp;" 名。'
                '「工程」が PKのみ の人は、その工程だけの標準時間 ÷ 実測時間です。'
                '②③ は両工程に実績のある "&amp;COUNT(印刷用データ!N3:N62)&amp;" 名。出典: 2026年4月 実績。"')
    assert old_note in x, "注記の数式が想定と違う"
    new_note = ('"※ ①〜④ は実績のある全員 "&amp;COUNT(印刷用データ!AS3:AS62)&amp;" 名。'
                '「工程」が PKのみ／梱包のみ の人は、その工程だけの標準時間 ÷ 実測時間です。'
                '③ でもう一方の実績が無い "&amp;(COUNT(印刷用データ!AS3:AS62)-COUNT(印刷用データ!N3:N62))&amp;'
                '" 名は、下の帯に灰色の三角で並べています。出典: 2026年4月 実績。"')
    x = x.replace(old_note, new_note, 1)
    x = x.replace("※ ①④ は実績のある全員 29 名。「工程」が PKのみ の人は、その工程だけの標準時間 ÷ 実測時間です。"
                  "②③ は両工程に実績のある 19 名。出典: 2026年4月 実績。",
                  "※ ①〜④ は実績のある全員 29 名。「工程」が PKのみ／梱包のみ の人は、その工程だけの標準時間 ÷ 実測時間です。"
                  "③ でもう一方の実績が無い 10 名は、下の帯に灰色の三角で並べています。出典: 2026年4月 実績。", 1)
    return x


# ---------------------------------------------------------------- 図形
BAND_LABEL = (
    '<xdr:twoCellAnchor editAs="oneCell">'
    '<xdr:from><xdr:col>25</xdr:col><xdr:colOff>0</xdr:colOff>'
    '<xdr:row>31</xdr:row><xdr:rowOff>19050</xdr:rowOff></xdr:from>'
    '<xdr:to><xdr:col>27</xdr:col><xdr:colOff>0</xdr:colOff>'
    '<xdr:row>32</xdr:row><xdr:rowOff>38100</xdr:rowOff></xdr:to>'
    '<xdr:sp macro="" textlink=""><xdr:nvSpPr>'
    '<xdr:cNvPr id="9007" name="TextBox 9007"/><xdr:cNvSpPr txBox="1"/></xdr:nvSpPr>'
    '<xdr:spPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="0" cy="0"/></a:xfrm>'
    '<a:prstGeom prst="rect"><a:avLst/></a:prstGeom>'
    '<a:solidFill><a:srgbClr val="FFFFFF"><a:alpha val="88000"/></a:srgbClr></a:solidFill>'
    '<a:ln w="9525"><a:solidFill><a:srgbClr val="7F7F7F"/></a:solidFill></a:ln></xdr:spPr>'
    '<xdr:txBody><a:bodyPr vertOverflow="clip" horzOverflow="clip" wrap="square" '
    'lIns="14000" tIns="8000" rIns="14000" bIns="8000" anchor="ctr"/><a:lstStyle/>'
    '<a:p><a:pPr algn="ctr"/><a:r><a:rPr lang="ja-JP" sz="600" b="1">'
    '<a:solidFill><a:srgbClr val="595959"/></a:solidFill>'
    '<a:latin typeface="游ゴシック"/><a:ea typeface="游ゴシック"/></a:rPr>'
    '<a:t>▲ もう一方の工程は実績なし</a:t></a:r></a:p></xdr:txBody></xdr:sp>'
    '<xdr:clientData/></xdr:twoCellAnchor>')

def patch_drawing(x):
    """帯を作ったぶん、下側の四象限ラベル2つを上へ逃がし、帯の説明を足す。"""
    moved = 0
    for a in re.findall(r"<xdr:twoCellAnchor\b.*?</xdr:twoCellAnchor>", x, re.S):
        nm = re.search(r'name="([^"]*)"', a)
        if not nm or nm.group(1) not in ("TextBox 9003", "TextBox 9004"):
            continue
        new = a.replace("<xdr:row>31</xdr:row>", "<xdr:row>29</xdr:row>", 1)
        new = new.replace("<xdr:row>32</xdr:row>", "<xdr:row>30</xdr:row>", 1)
        assert new != a, nm.group(1)
        x = x.replace(a, new, 1); moved += 1
    assert moved == 2, f"移動できた図形が {moved} 個"
    assert 'name="TextBox 9007"' not in x
    return x.replace("</xdr:wsDr>", BAND_LABEL + "</xdr:wsDr>", 1)

# ---------------------------------------------------------------- 梱包
PATCH = {
    "xl/worksheets/sheet12.xml": lambda s: patch_data_sheet(s, BAND_XY, BAND_SEQ),
    "xl/charts/chart10.xml":     build_chart10,
    "xl/charts/chart9.xml":      build_chart9,
    "xl/worksheets/sheet2.xml":  patch_sheet2,
    "xl/drawings/drawing2.xml":  patch_drawing,
}
zi = zipfile.ZipFile(SRC); zo = zipfile.ZipFile(DST, "w", zipfile.ZIP_DEFLATED)
for it in zi.infolist():
    d = zi.read(it.filename)
    fn = PATCH.get(it.filename)
    if fn:
        d = fn(d.decode("utf-8")).encode("utf-8")
    zo.writestr(it, d)
zo.close(); zi.close()
print("wrote", DST)
