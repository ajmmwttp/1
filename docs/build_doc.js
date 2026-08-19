const fs = require("fs");
const {
  Document, Packer, Paragraph, TextRun, HeadingLevel, AlignmentType,
  Table, TableRow, TableCell, WidthType, ShadingType, BorderStyle,
} = require("docx");

const JP = "游ゴシック";
const W = 9000;

const P = (text, opt = {}) => new Paragraph({
  alignment: opt.align,
  spacing: { before: opt.before ?? 0, after: opt.after ?? 120, line: 300 },
  children: [new TextRun({ text, font: JP, size: opt.size ?? 21, bold: opt.bold, color: opt.color })],
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
  children: [new TextRun({ text: "・", font: JP, size: 21 }),
             new TextRun({ text, font: JP, size: 21, bold })],
});

const BOX = (lines, fill) => new Table({
  columnWidths: [W], width: { size: W, type: WidthType.DXA },
  rows: [new TableRow({ children: [new TableCell({
    width: { size: W, type: WidthType.DXA },
    shading: { type: ShadingType.CLEAR, fill: fill ?? "F2F6FA" },
    margins: { top: 130, bottom: 130, left: 180, right: 180 },
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
  children: [new Paragraph({ alignment: align, spacing: { after: 0, line: 280 },
    children: [new TextRun({ text, font: JP, size: 20, bold, color })] })],
});

const table = (widths, rows) => new Table({
  columnWidths: widths,
  width: { size: widths.reduce((a, b) => a + b, 0), type: WidthType.DXA },
  rows: rows.map((r, i) => new TableRow({
    tableHeader: i === 0,
    children: r.map((c, j) => cell(c, {
      width: widths[j], bold: i === 0,
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

      new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 60 },
        children: [new TextRun({ text: "作業評価のしくみについて", font: JP, size: 34, bold: true, color: "17375E" })] }),
      new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 240 },
        children: [new TextRun({ text: "― 会社目標「1件あたり1.6分」に、どう向き合うか ―", font: JP, size: 22, color: "404040" })] }),
      new Paragraph({ alignment: AlignmentType.RIGHT, spacing: { after: 240 },
        children: [new TextRun({ text: "【　部署名　】　2026年　月　日", font: JP, size: 20, color: "595959" })] }),

      P("この文書は、2026年4月から使っている作業評価のしくみを、評価を受ける皆さんご本人に向けて説明するものです。何を測っているのか、なぜそう測ることにしたのか、そして何は測れないのかを、隠さずに書きます。"),

      H1("1. 会社の目標（変わらない数字）"),
      BOX([{ t: "ピッキング 1.6 分/件　＋　梱包 1.6 分/件　＝　合計 3.2 分", size: 24, bold: true },
           { t: "工程ごとにそれぞれ 1.6 分。誰に対しても同じ目標です。", size: 20, color: "404040" }]),
      P("この数字は会社が定めたもので、変更しない前提です。この文書の目的は、この目標に対して「いま何秒足りないのか」「その不足は誰が何をすれば埋まるのか」を、はっきりさせることです。", { before: 140 }),

      H1("2. これまでの評価には、速さ以外のものが混ざっていました"),
      P("従来は「実際にかかった時間 ÷ 件数」、つまり1件あたり何分かかったか、という数字で見ていました。単純で分かりやすい数字です。"),
      P("ところが2026年4月の実績（29名・45,716件・記録の揃った21日分）で検証したところ、この数字は、その人の速さではなく、担当したリストの中身で決まっていたことが分かりました。"),
      P("ピッキングには1社ごとに必ず発生する時間（段取り）があります。1社から10個まとめて引くリストと、1社1個のリストを10枚引くのとでは、同じ10個でも背負う段取りが10倍違います。"),
      P("そこで「1件あたり何社ぶんの段取りを背負ったか」と「1件あたり何分かかったか」の関係を調べると、はっきり右上がりでした。"),
      BOX([{ t: "従来の「1件あたり何分」と、リスト構成との関係", size: 20, color: "404040" },
           { t: "相関 r ＝ 0.43　（p ＝ 0.019、29名）", size: 24, bold: true, color: "C00000" },
           { t: "この大きさの偏りは、偶然では説明できません", size: 20, color: "404040" }], "FDF2F2"),
      P("1社1個のリストを多く引いた人ほど、同じ速さで働いても数字が悪く出ていた、ということです。本人の努力や技能とは関係のない差が、評価に混ざっていました。", { before: 120 }),

      H1("3. 段取り時間を見直しました"),
      P("段取りは当初「リストを見る 46.05秒 ＋ 伝票を挟む 46.05秒 ＝ 1社あたり 92.1秒」としていました。しかし現場から「リストを見るのに46秒もかからない、10秒だ」との指摘があり、次のとおり改めました。"),
      table([2800, 3100, 3100], [
        ["1社あたりの段取り", "見直し前", "見直し後"],
        ["① リストを見る", "46.05 秒", "10.00 秒"],
        ["④ 伝票を挟む", "46.05 秒", "46.05 秒（据え置き）"],
        ["合計 a", "92.10 秒/社", "56.05 秒/社"],
      ]),
      P("この見直しには大きな意味があります。1.6分（96秒）のうち、件数に比例する作業（棚まで移動＋棚から取ってカゴへ）が 75.6秒 を占めるため、段取りに使える枠は 20.4秒 しかありません。つまり「1社あたり何件のリストか」で、目標に届くかどうかが決まります。", { before: 160 }),
      table([3000, 3000, 3000], [
        ["段取りの設定", "1.6分に必要な1社あたり件数", "実績 2.33 件との関係"],
        ["見直し前 92.1 秒/社", "4.51 件", "1.94 倍が必要 — 事実上不可能"],
        ["見直し後 56.05 秒/社", "2.75 件", "あと +18％ — 手が届く"],
      ]),
      P("段取りを正しい値に直したことで、会社目標が「届かない数字」から「届きうる数字」に変わりました。", { before: 160, bold: true }),

      H1("4. 新しいしくみ"),
      P("一人ひとりについて「その物量なら本来これくらいかかるはず」という時間（標準時間）を計算し、実際にかかった時間と比べます。"),
      BOX([{ t: "標準時間 ＝ 1社あたりの時間 × 企業数 ＋ 1件あたりの時間 × 件数", size: 22, bold: true },
           { t: "効率 ＝ 標準時間 ÷ 実際にかかった時間 × 100　（100 なら標準どおり）", size: 22, bold: true }]),
      new Paragraph({ spacing: { after: 120 }, children: [] }),
      table([2000, 3500, 3500], [
        ["工程", "1社あたり（段取り）", "1件あたり（作業）"],
        ["ピッキング", "56.05 秒（リストを見る＋伝票を挟む）", "75.6 秒（棚まで移動＋棚から取ってカゴへ）"],
        ["梱包", "92.1 秒", "69.5 秒"],
      ]),

      H1("5. いま、目標にどれだけ届いているか"),
      P("2026年4月の実績を、会社目標 1.6分/件 と比べた結果です。"),
      table([2600, 2100, 4300], [
        ["工程", "目標達成率", "内容"],
        ["梱包", "99.9 ％", "実測 1.602 分/件。ほぼ目標どおりです。"],
        ["ピッキング", "83.4 ％", "実測 1.919 分/件。1件あたり 19.2 秒 足りていません。"],
      ]),
      P("この「足りない 19.2 秒」の中身が重要です。", { before: 160, bold: true }),
      BOX([{ t: "ピッキングの未達 19.2 秒/件 の内訳", size: 20, color: "404040" },
           { t: "速さ由来 15.5 秒（81％）　／　リスト構成由来 3.6 秒（19％）", size: 23, bold: true },
           { t: "8割は日々の作業で埋まる分。2割はリストの組み方で決まる分です。", size: 20, color: "404040" }], "FFF8E7"),
      P("速さ由来の 15.5 秒は、実測時間と標準時間の差です。ここは作業のしかたを見直せば縮みます。リスト構成由来の 3.6 秒は、1社あたりが 2.33 件しかないために生じる分で、担当者の努力では動かせません。1.6分に収めるには 1社あたり 2.75 件が必要で、この 18％ はリストの組み方の課題です。", { before: 120 }),
      P("この内訳は印刷ページの下部に毎月表示されます。数字が変われば自動で計算し直されます。"),

      H1("6. 皆さんにとって何が良くなるか"),
      table([2600, 6400], [
        ["変わること", "内容"],
        ["引いたリストの中身で不利にならない",
         "1社1個ばかりのリストを引いた月でも、その分の段取りは必要な時間として認められます。評価されるのは速さだけです。"],
        ["自分専用の目標が出る",
         "「公平目標（分/個）」は、その人が実際に担当したリストの構成に合わせて計算されます。会社目標 1.6分 は全員共通ですが、そこに届かない分の理由が分けて示されます。"],
        ["少ない記録日数で決めつけられない",
         "記録日数が少ないと数字はブレます。そのため平均側へ寄せた値と95％の幅を出し、その幅が全体平均をまたぐ場合は「差があるとは言えない」と判定します。たまたま悪かった月が、そのまま評価になることはありません。"],
        ["どこを直せばよいかが分かる",
         "ピッキングと梱包を分けて出すので、自分がどちらの工程で時間を要しているかが分かります。漠然と「速くしてください」ではなく、直す場所が特定できます。"],
        ["物量の多さは成績にならない",
         "たくさん処理したかどうかは需要の問題であって、成績ではありません。逆に、物量が少ない月に不利になることもありません。"],
      ]),

      H1("7. この数字にできないこと"),
      P("信用していただくために、限界も書いておきます。"),
      BULLET("段取りの見直しで、全員の数字がいったん下がりました。全体の平均は 98.4％ から 90.4％ になっています。これは皆さんの働きが落ちたのではなく、基準を厳しい側に直したためです。", true),
      BULLET("実績データから統計的に段取り時間を推定すると 113.6 秒/社 という値が出ます。今回採用した 56.05 秒/社 はその約半分です。この開きが何によるものかは、まだ分かっていません。「リストを見る・伝票を挟む」以外にも1社ごとに時間を要する作業がある可能性があります。"),
      BULLET("段取りを除いたあとも、リスト構成との相関は完全には消えません（相関 r ＝ 0.24、p ＝ 0.22）。統計的には「傾きは無いと言ってよい」範囲ですが、補正しきれていない分が残っている可能性があります。"),
      BULLET("ピッキングの順位は月ごとにブレます。順位の再現性を示す数値は 0.61 でした（1に近いほど安定）。1か月の順位だけで人を判断せず、数か月をならして見る前提で運用します。梱包は 0.89 で比較的安定しています。なお、この数値は段取りの見直し前に算出したものなので、あらためて計算し直す必要があります。"),
      BULLET("時間の記録漏れがあると、その人の効率は実力以上に高く出ます。記録の正確さが、このしくみの前提です。"),

      H1("8. 誰が何を見るか"),
      P("全員の氏名と順位が並んだ一覧は、係長が見ます。改善の支援をどこから始めるかを決めるための資料です。"),
      BOX([{ t: "順位1位は「最も成績が悪い人」ではありません。", size: 22, bold: true },
           { t: "支援を最初に届ける人、という意味です。", size: 22, bold: true }], "FFF8E7"),

      H1("9. 処遇との関係"),
      P("現時点では、この数字は賞与・査定・時給・契約更新には使っていません。"),
      P("ただし、将来的には処遇に連動させることを検討しています。隠さずにお伝えします。その場合も、少なくとも次の点は満たしたうえで行います。", { bold: true }),
      BULLET("1か月の数字だけで判断せず、数か月をならして見ること"),
      BULLET("「差があるとは言えない」と判定された範囲を、差として扱わないこと"),
      BULLET("リスト構成由来の不足を、本人の評価に含めないこと", true),
      BULLET("時間の記録の正確さが担保されていること"),
      BULLET("連動させる時期と方法を、事前に皆さんにお知らせすること"),

      H1("おわりに"),
      P("計算に使っている係数は、実測値が取れ次第あらためて差し替えていきます。今回の「リストを見る 10秒」も、現場からの指摘を反映したものです。数字の出方に疑問があれば、【　問い合わせ先　】までお知らせください。"),
      P("このしくみは、皆さんを順位づけするためではなく、目標に届かない理由を「作業のしかた」と「リストの組み方」に分けて、それぞれに正しく手を打つために導入しました。", { bold: true }),
    ],
  }],
});

Packer.toBuffer(doc).then((b) => {
  fs.writeFileSync("作業評価のしくみについて.docx", b);
  console.log("wrote 作業評価のしくみについて.docx");
});
