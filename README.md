# Ledger — 庫内作業オペレーション・ダッシュボード

ピッキング（PK）と梱包の生産性を、**段取り時間を切り分けて**評価するオペレーション
・ダッシュボード。2026年4月の実績データで動きます。

## なぜ作るか

従来の「分/個」は、担当したリストの枚数（＝企業数）を無視します。段取りは
**1社ごとに必ず発生する**ため、1社1個のリストを多く引いた人ほど不利に出ます。

```
標準時間 ＝ a × 企業数 ＋ b × 件数
効率     ＝ 標準時間 ÷ 実測時間 × 100
```

| 工程 | a（段取り） | b（1件あたり） |
|---|---|---|
| ピッキング | 112.8 秒/社 | 65.7 秒/件 |
| 梱包 | 50.0 秒/社 ※暫定 | 81.8 秒/件 |

4月のピッキングでは、この段取りが総時間 504.6 時間のうち **212.8 時間（42.2%）**
を占めていました。

## 技術構成

- Next.js 15 (App Router) / TypeScript strict
- Tailwind CSS v4（CSS-first。`tailwind.config` は持たない）
- shadcn/ui 相当のプリミティブを Radix 上に自前で vendoring（`components/ui/`）
- Recharts 3 / Framer Motion 12 / lucide-react
- Geist Sans + Geist Mono（数値は全て tabular-nums）+ Noto Sans JP

## デザインシステム

トークンは `app/globals.css` の CSS 変数に集約。ゴールドのアクセントは
**操作と強調のみ**に使い、データ系列の色としては決して使いません。

系列色は目視ではなく検証スクリプトで確定しています。

| | dark | light |
|---|---|---|
| 全ペア CVD ΔE | 9.4 | 9.2 |
| 全ペア 通常視 ΔE | 20.9 | 24.0 |

カテゴリ色は 3 色まで。4 色目（黄）は橙との判別が CVD ΔE 4.8 / 通常視 10.6 で
下限 15 を割るため、部分‐全体の表示は 3 スライス ＋ 中立色の「その他」で固定です。

## 構成

```
app/            layout（シェル同梱）/ page / loading / error / not-found
components/ui/      Radix ベースのプリミティブ
components/shell/   サイドバー・ヘッダー・コマンドパレット
components/kpi/     KPI タイルとスパークライン
components/charts/  Recharts 実装
components/table/   担当者ランキング表
components/states/  ローディング / 空 / エラー
lib/                トークン・整形・データ
```

## 開発

```bash
pnpm install
pnpm dev      # http://localhost:3000
pnpm build
```

## データ

`lib/data/warehouse.ts` は生成物です。月次実績表を IE 標準時間モデルで評価した
結果を型付きで固めています。4/24 以降は PK 実働時間の記録が欠落しており、
チャート上では「記録なし」帯として明示しています（欠損を隠しません）。
