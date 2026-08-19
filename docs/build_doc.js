const fs = require("fs");
const {
  Document, Packer, Paragraph, TextRun, HeadingLevel, AlignmentType,
  Table, TableRow, TableCell, WidthType, ShadingType, BorderStyle,
} = require("docx");

const JP = "游ゴシック";
const W = 9000;                         // 本文幅(DXA) A4縦・余白1インチ

const P = (text, opt = {}) => new Paragraph({
  alignment: opt.align,
  spacing: { before: opt.before ?? 0, after: opt.after ?? 120, line: 300 },
  indent: opt.indent,
  children: [new TextRun({ text, font: JP, size: opt.size ?? 21, bold: opt.bold,
                           color: opt.color })],
});

const H1 = (text) => new Paragraph({
  heading: HeadingLevel.HEADING_1,
  spacing: { before: 320, after: 160 },
  border: { bottom: { style: BorderStyle.SINGLE, size: 10, color: "17375E", space: 4 } },
  children: [new TextRun({ text, font: JP, size: 26, bold: true, color: "17375E" })],
});

const BULLET = (text, bold) => new Paragraph({
  spacing: { after: 100, line: 300 },
  indent: { left: 340, hanging: 200 },
  children: [
    new TextRun({ text: "・", font: JP, size: 21 }),
    new TextRun({ text, font: JP, size: 21, bold }),
  ],
});

// 強調ボックス（1行1セルの表）
const BOX = (lines, fill) => new Table({
  columnWidths: [W],
  width: { size: W, type: WidthType.DXA },
  rows: [new TableRow({ children: [new TableCell({
    width: { size: W, type: WidthType.DXA },
    shading: { type: ShadingType.CLEAR, fill: fill ?? "F2F6FA" },
    margins: { top: 120, bottom: 120, left: 180, right: 180 },
    children: lines.map((t, i) => new Paragraph({
      spacing: { after: i === lines.length - 1 ? 0 : 80, line: 300 },
      alignment: AlignmentType.CENTER,
      children: [new TextRun({ text: t.t ?? t, font: JP, size: t.size ?? 21,
                               bold: t.bold ?? false, color: t.color })],
    })),
  })] })],
});

const cell = (text, { bold, fill, align, width, color } = {}) => new TableCell({
  width: { size: width, type: WidthType.DXA },
  shading: fill ? { type: ShadingType.CLEAR, fill } : undefined,
  margins: { top: 80, bottom: 80, left: 120, right: 120 },
  children: [new Paragraph({
    alignment: align,
    spacing: { after: 0, line: 280 },
    children: [new TextRun({ text, font: JP, size: 20, bold, color })],
  })],
});

const table = (widths, rows) => new Table({
  columnWidths: widths,
  width: { size: widths.reduce((a, b) => a + b, 0), type: WidthType.DXA },
  rows: rows.map((r, i) => new TableRow({
    tableHeader: i === 0,
    children: r.map((c, j) => cell(c, {
      width: widths[j],
      bold: i === 0,
      fill: i === 0 ? "17375E" : (i % 2 === 0 ? "F7F9FC" : undefined),
      color: i === 0 ? "FFFFFF" : undefined,
      align: i === 0 ? AlignmentType.CENTER : undefined,
    })),
  })),
});

const doc = new Document({
  styles: { default: { document: { run: { font: JP, size: 21 } } } },
  sections: [{
    properties: { page: { margin: { top: 1440, bottom: 1440, left: 1440, right: 1440 } } },
    children: [

      new Paragraph({
        alignment: AlignmentType.CENTER, spacing: { after: 60 },
        children: [new TextRun({ text: "作業評価のしくみについて", font: JP, size: 34,
                                 bold: true, color: "17375E" })] }),
      new Paragraph({
        alignment: AlignmentType.CENTER, spacing: { after: 240 },
        children: [new TextRun({ text: "― なぜ「1件あたり何分」での比較をやめたのか ―",
                                 font: JP, size: 22, color: "404040" })] }),
      new Paragraph({
        alignment: AlignmentType.RIGHT, spacing: { after: 240 },
        children: [new TextRun({ text: "【　部署名　】　2026年　月　日",
                                 font: JP, size: 20, color: "595959" })] }),

      P("この文書は、2026年4月から使っている作業評価のしくみを、評価を受ける皆さんご本人に向けて説明するものです。何を測っているのか、なぜそう測ることにしたのか、そして何は測れないのかを、隠さずに書きます。"),

      H1("1. きっかけ ― 従来の「1件あたり何分」を検証しました"),
      P("これまでは「実際にかかった時間 ÷ 件数」、つまり1件あたり何分かかったか、という数字で見ていました。単純で分かりやすい数字です。"),
      P("ところが2026年4月の実績（29名・45,716件・記録の揃った21日分）で検証したところ、この数字は、その人の速さではなく、担当したリストの中身で決まっていたことが分かりました。"),

      H1("2. 何が起きていたのか"),
      P("ピッキングには、1社ごとに必ず発生する時間があります。リストを見るのに約46秒、伝票を挟むのに約46秒。合わせて1社あたり約92秒です。これを「段取り」と呼びます。"),
      P("この段取りは、4月のピッキング総時間679.7時間のうち233.2時間、割合にして34.3％を占めていました。作業時間の3分の1が、件数ではなく社数で決まっていたことになります。"),
      P("ここで問題になるのがリストの中身です。1社から10個まとめて引くリストと、1社1個のリストを10枚引くのとでは、同じ10個でも背負う段取りが10倍違います。"),
      P("そこで「1件あたり何社ぶんの段取りを背負ったか」と「1件あたり何分かかったか」の関係を調べました。結果ははっきりと右上がりでした。"),
      BOX([{ t: "従来の「1件あたり何分」と、リスト構成との関係", size: 20, color: "404040" },
           { t: "相関 r ＝ 0.43　（p ＝ 0.019、29名）", size: 24, bold: true, color: "C00000" },
           { t: "この大きさの偏りは、偶然では説明できません", size: 20, color: "404040" }], "FDF2F2"),
      P("つまり、1社1個のリストを多く引いた人ほど、同じ速さで働いても数字が悪く出ていたということです。本人の努力や技能とは関係のない差が、評価に混ざっていました。", { before: 120 }),
      P("そこで段取りの分を差し引いた「手を動かす速さそのもの」で、同じ関係を調べ直しました。"),
      BOX([{ t: "段取りを除いたあとの速さと、リスト構成との関係", size: 20, color: "404040" },
           { t: "相関 r ＝ 0.09　（p ＝ 0.64、29名）", size: 24, bold: true, color: "1BAF7A" },
           { t: "偶然の範囲です。担当リストの偏りを取り除けました", size: 20, color: "404040" }], "F1FAF6"),
      P("この確認が取れたので、新しい方式に切り替えました。", { before: 120 }),

      H1("3. 新しいしくみ"),
      P("一人ひとりについて「その物量なら本来これくらいかかるはず」という時間（標準時間）を先に計算し、実際にかかった時間と比べます。"),
      BOX([{ t: "標準時間 ＝ 1社あたりの時間 × 企業数 ＋ 1件あたりの時間 × 件数", size: 22, bold: true },
           { t: "効率 ＝ 標準時間 ÷ 実際にかかった時間 × 100　（100 なら標準どおり）", size: 22, bold: true }]),
      new Paragraph({ spacing: { after: 120 }, children: [] }),
      table([2000, 3500, 3500], [
        ["工程", "1社あたり（段取り）", "1件あたり（作業）"],
        ["ピッキング", "92.1秒（リストを見る＋伝票を挟む）", "75.6秒（棚まで移動＋棚から取ってカゴへ）"],
        ["梱包", "92.1秒", "69.5秒"],
      ]),
      P("4月の全体平均は 99.98 でした。ほぼ100であることは、この標準時間の設定が実態と大きくずれていないことを示しています。", { before: 160 }),

      H1("4. 皆さんにとって何が良くなるか"),
      table([2600, 6400], [
        ["変わること", "内容"],
        ["引いたリストの中身で不利にならない",
         "1社1個ばかりのリストを引いた月でも、その分の段取りは最初から必要な時間として認められます。評価されるのは速さだけです。"],
        ["自分専用の目標が出る",
         "「公平目標（分/個）」は、その人が実際に担当したリストの構成に合わせて計算されます。全員一律の目標ではありません。"],
        ["少ない記録日数で決めつけられない",
         "記録日数が少ないと数字はブレます。そのため平均側へ寄せた値と95％の幅を出し、その幅が全体平均をまたぐ場合は「差があるとは言えない」と判定します。たまたま悪かった月が、そのまま評価になることはありません。"],
        ["どこを直せばよいかが分かる",
         "ピッキングと梱包を分けて出すので、自分がどちらの工程で時間を要しているかが分かります。漠然と「速くしてください」ではなく、直す場所が特定できます。"],
        ["物量の多さは成績にならない",
         "たくさん処理したかどうかは需要の問題であって、成績ではありません。逆に、物量が少ない月に不利になることもありません。"],
      ]),

      H1("5. この数字にできないこと"),
      P("信用していただくために、限界も書いておきます。"),
      BULLET("ピッキングの順位は月ごとにブレます。順位の再現性を示す数値は 0.61 です（1に近いほど安定）。1か月の順位だけで人を判断せず、数か月をならして見る前提で運用します。梱包は 0.89 で比較的安定しています。"),
      BULLET("梱包の段取り時間（92.1秒）は、統計的には0と区別できません。データから言えるのは「梱包の段取りが何秒かは特定できない」というところまでです。"),
      BULLET("時間の記録漏れがあると、その人の効率は実力以上に高く出ます。記録の正確さが、このしくみの前提です。"),
      BULLET("企業数が空欄の場合は、段取りの補正なしで計算されます（従来と同じ扱いになります）。"),

      H1("6. 誰が何を見るか"),
      P("全員の氏名と順位が並んだ一覧は、係長が見ます。改善の支援をどこから始めるかを決めるための資料です。"),
      BOX([{ t: "順位1位は「最も成績が悪い人」ではありません。", size: 22, bold: true },
           { t: "支援を最初に届ける人、という意味です。", size: 22, bold: true }], "FFF8E7"),

      H1("7. 処遇との関係"),
      P("現時点では、この数字は賞与・査定・時給・契約更新には使っていません。"),
      P("ただし、将来的には処遇に連動させることを検討しています。隠さずにお伝えします。その場合も、少なくとも次の点は満たしたうえで行います。", { bold: true }),
      BULLET("1か月の数字だけで判断せず、数か月をならして見ること（ピッキングの再現性は 0.61 です）"),
      BULLET("「差があるとは言えない」と判定された範囲を、差として扱わないこと"),
      BULLET("時間の記録の正確さが担保されていること"),
      BULLET("連動させる時期と方法を、事前に皆さんにお知らせすること"),

      H1("おわりに"),
      P("計算に使っている係数（1社あたり92.1秒など）は、実測値が取れ次第あらためて差し替えていきます。数字の出方に疑問があれば、【　問い合わせ先　】までお知らせください。"),
      P("このしくみは、皆さんを順位づけするためではなく、担当した仕事の中身によって評価が変わってしまう状態をなくすために導入しました。", { bold: true }),
    ],
  }],
});

Packer.toBuffer(doc).then((b) => {
  fs.writeFileSync("作業評価のしくみについて.docx", b);
  console.log("wrote 作業評価のしくみについて.docx");
});
