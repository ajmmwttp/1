# -*- coding: utf-8 -*-
"""段1: ピッキング/梱包 A列「順位」の参照を 縮小後効率L → 目標達成率R に変更。

A列は共有数式（si=0: A7:A38 / si=9: A39:A66）。ホストの式だけ書き換え、
キャッシュ <v> は Python で RANK(R,…,0) を再計算して全セルに書き戻す。
openpyxl 往復は使わず zip 内の worksheet XML を直接編集する。
"""
import re, sys, zipfile

SRC, DST = sys.argv[1], sys.argv[2]
SHEETS = {'xl/worksheets/sheet4.xml': 'ピッキング', 'xl/worksheets/sheet5.xml': '梱包'}
HOSTS = {'A7': 7, 'A39': 39}


def cell_block(xml, ref):
    m = re.search(r'<c r="%s"(?:(?!</c>).)*?</c>' % ref, xml, re.S)
    return m


def numeric_cache(xml, ref):
    """セルのキャッシュ値。数値なら float、文字列/空/エラーなら None。"""
    m = cell_block(xml, ref)
    if m is None:
        return None
    blk = m.group(0)
    if re.search(r't="(str|s|e|b)"', blk):
        return None
    mv = re.search(r'<v>([^<]*)</v>', blk)
    if not mv or mv.group(1) == '':
        return None
    return float(mv.group(1))


def excel_rank_desc(vals):
    nums = [v for v in vals.values() if v is not None]
    return {r: (1 + sum(1 for w in nums if w > v)) if v is not None else None
            for r, v in vals.items()}


def set_cell(xml, ref, rank):
    """A{ref} のキャッシュを rank（None なら空文字）に更新して返す。"""
    m = cell_block(xml, ref)
    if m is None:
        return xml, False
    blk = m.group(0)
    if rank is None:
        blk = re.sub(r'<v[^>]*/>|<v>[^<]*</v>', '<v/>', blk)
        if not re.search(r't="str"', blk):
            blk = re.sub(r'(<c r="%s"[^>]*?)>' % ref, r'\1 t="str">', blk, count=1)
    else:
        blk = blk.replace(' t="str"', '')
        if re.search(r'<v[^>]*/>|<v>[^<]*</v>', blk):
            blk = re.sub(r'<v[^>]*/>|<v>[^<]*</v>', '<v>%d</v>' % rank, blk)
        else:
            blk = blk.replace('</c>', '<v>%d</v></c>' % rank)
    return xml[:m.start()] + blk + xml[m.end():], True


def main():
    zin = zipfile.ZipFile(SRC)
    parts = {n: zin.read(n) for n in zin.namelist()}
    infos = {i.filename: i for i in zin.infolist()}
    order = zin.namelist()
    zin.close()

    for path, name in SHEETS.items():
        s = parts[path].decode('utf-8')

        # 1) ホストの式を差し替え
        for host, row in HOSTS.items():
            old = 'IF(L{r}="","",RANK(L{r},$L$7:$L$66,0))'.format(r=row)
            new = 'IF(R{r}="","",RANK(R{r},$R$7:$R$66,0))'.format(r=row)
            assert old in s, '%s %s の式が想定と違う' % (name, host)
            s = s.replace(old, new, 1)

        # 2) R列のキャッシュから順位を再計算
        rvals = {r: numeric_cache(s, 'R%d' % r) for r in range(7, 67)}
        ranks = excel_rank_desc(rvals)

        # 3) A列のキャッシュを書き戻す
        n = 0
        for r in range(7, 67):
            s, ok = set_cell(s, 'A%d' % r, ranks[r])
            n += 1 if ok else 0

        parts[path] = s.encode('utf-8')
        live = sum(1 for v in rvals.values() if v is not None)
        print('%s: ホスト式2件を差し替え / A列キャッシュ %d セル更新 / 順位が付く人 %d名'
              % (name, n, live))

    zout = zipfile.ZipFile(DST, 'w', zipfile.ZIP_DEFLATED)
    for nm in order:
        zi = zipfile.ZipInfo(nm, date_time=infos[nm].date_time)
        zi.compress_type = infos[nm].compress_type
        zi.external_attr = infos[nm].external_attr
        zout.writestr(zi, parts[nm])
    zout.close()


main()
