# -*- coding: utf-8 -*-
"""検証用コピーを作る: 外部リンク（recalc.py が拒否する）を取り除く。"""
import re, sys, zipfile
SRC, DST = sys.argv[1], sys.argv[2]
zin = zipfile.ZipFile(SRC)
parts = {n: zin.read(n) for n in zin.namelist()}
zin.close()
drop = [n for n in parts if n.startswith('xl/externalLinks/')]
for n in drop:
    del parts[n]
wb = parts['xl/workbook.xml'].decode('utf-8')
wb = re.sub(r'<externalReferences>.*?</externalReferences>', '', wb, flags=re.S)
parts['xl/workbook.xml'] = wb.encode('utf-8')
rel = parts['xl/_rels/workbook.xml.rels'].decode('utf-8')
rel = re.sub(r'<Relationship[^>]*externalLink[^>]*/>', '', rel)
parts['xl/_rels/workbook.xml.rels'] = rel.encode('utf-8')
ct = parts['[Content_Types].xml'].decode('utf-8')
ct = re.sub(r'<Override[^>]*externalLink[^>]*/>', '', ct)
parts['[Content_Types].xml'] = ct.encode('utf-8')
z = zipfile.ZipFile(DST, 'w', zipfile.ZIP_DEFLATED)
for n, b in parts.items():
    z.writestr(n, b)
z.close()
print('外部リンク %d パートを除去 -> %s' % (len(drop), DST))
