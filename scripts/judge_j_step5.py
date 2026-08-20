# -*- coding: utf-8 -*-
"""段5: τ² と信頼性を新係数・最新データで再推定した値に更新する。

  ピッキング τ² 215.1 → 124.8 / 信頼性 0.61 → 0.40
  梱包       τ² 809.8 → 901.8 / 信頼性 0.89 → 0.87
（推定式: τ² = 効率の観測分散 − σ²×mean(1/記録日数)。σ² は据え置き）
影響するのは L（縮小後効率）・M/N（参考CI）・A列順位のみ。判定(O列)は不変。
説明文 B12 の下に再推定の注記を追記する。
"""
import re
import zipfile

SRC, DST = "j5.xlsx", "j6.xlsx"
NEW = {"D14": ("215.1", "124.8"), "D16": ("0.61", "0.4"),
       "D17": ("809.8", "901.8"), "D19": ("0.89", "0.87")}

def patch(x):
    for ref, (old, new) in NEW.items():
        pat = f'<c r="{ref}" s="56"><v>{old}</v></c>'
        if pat not in x:                       # スタイル番号が違う場合に備える
            m = re.search(r'<c r="%s" s="(\d+)"><v>%s</v></c>' % (ref, re.escape(old)), x)
            assert m, f"{ref} が想定と違う"
            pat = m.group(0)
            x = x.replace(pat, pat.replace(f"<v>{old}</v>", f"<v>{new}</v>"), 1)
        else:
            x = x.replace(pat, pat.replace(f"<v>{old}</v>", f"<v>{new}</v>"), 1)
    # 注記: E16 の説明を差し替え（「2026年4月・a=56.05 で再推定」）
    m = re.search(r'<c r="E16" s="(\d+)" t="s"><v>\d+</v></c>', x)
    assert m, "E16 が想定と違う"
    x = x.replace(m.group(0),
                  f'<c r="E16" s="{m.group(1)}" t="inlineStr"><is>'
                  '<t>順位の再現性。1に近いほど安定。2026年4月実績・a=56.05秒 で再推定</t></is></c>', 1)
    return x

zi = zipfile.ZipFile(SRC); zo = zipfile.ZipFile(DST, "w", zipfile.ZIP_DEFLATED)
for it in zi.infolist():
    b = zi.read(it.filename)
    if it.filename == "xl/worksheets/sheet10.xml":
        b = patch(b.decode("utf-8")).encode("utf-8")
    zo.writestr(it, b)
zo.close(); zi.close()
print("wrote", DST)
