# 文献調査メモ（TurnLine 検証用）

調査日 2026-10-29。WebSearch の要約をもとにまとめた。論文サイト（arXiv・RePEc など）はこの環境から直接開けないため、原文で数字を確かめられていないものがある。そのため各項目に「確からしさ」を付けた。

| # | 内容 | 確からしさ | 出典 |
|---|---|---|---|
| 1 | テクニカル分析の利益性を調べた研究のサーベイ（Park & Irwin）。2004年版では現代の研究92本のうち58本が肯定的、24本が否定的。ただし多くの研究に検証手順の問題（データスヌーピング＝同じデータで何度も試して偶然の当たりを拾う）がある | 確立（サーベイ） | [AgMAS04-04](https://ageconsearch.umn.edu/record/37487/files/AgMAS04_04.pdf), [J. Econ. Surveys 21(4) 2007](https://ideas.repec.org/a/bla/jecsur/v21y2007i4p786-826.html) |
| 2 | Sullivan, Timmermann & White (1999, J. Finance 54(5))。ダウ平均100年分で7,846個のルールを White の Reality Check で検定した。データスヌーピングを補正すると、Brock ら(1992)の「最良ルール」は後の期間（1987–1996）で有意でなくなった | 確立 | [LSE FMG DP303](https://www.fmg.ac.uk/sites/default/files/2020-11/dp303.pdf), [LSE Research Online](https://researchonline.lse.ac.uk/id/eprint/119144), [ageconsearch cp05pa01](https://ageconsearch.umn.edu/record/19039/files/cp05pa01.pdf) |
| 3 | DeMark（TD Sequential 等）の統計検定（Lissandrin, Daly & Sornette）。商品先物21銘柄・2004–2014で、ランダム化検定に対して有意な予測力があった。ただし効くのは限られた保有日数だけで、シグナルは年1〜5回と少ない。株式での厳密な査読研究は見つからなかった | 示唆 | [risk.net (J. Investment Strategies)](https://www.risk.net/journal-of-investment-strategies/5293521/statistical-testing-of-demark-technical-indicators-on-commodity-futures), [IDEAS rp1556](https://ideas.repec.org/p/chf/rpseri/rp1556.html) |
| 4 | 指数の RSI「買われすぎ」は下落の予兆になりにくい（強い上昇トレンドでは買われすぎが長く続く）。「売られすぎ」の方が情報量がある、とする実務家の検証が多い | 逸話〜示唆 | [Schaeffer's 2019](https://www.schaeffersresearch.com/content/analysis/2019/02/06/dont-fear-an-overbought-stock-market-yet), [SeeItMarket](https://seeitmarket.com/?p=52148), [Traders.com](https://technical.traders.com/tradersonline/display.asp?art=8652), [CXO Advisory](https://cxoadvisory.com/technical-trading/simple-test-of-rsi-as-an-abnormal-returns-indicator) |
| 5 | 天井（ピーク）より底（トラフ）の方が予測しやすい、とする研究がある。2016年の学位論文の要旨や、底（投げ売り）に絞った2025年の機械学習研究 | 示唆 | [airiti 2016](https://www.airitilibrary.com/Publication/Index/U0002-0407201614525300), [arXiv 2509.05922](https://arxiv.org/abs/2509.05922) |
| 6 | 変動率の非対称性: 同じ大きさなら、下落ショックの方が上昇ショックより変動率を大きく押し上げる（Ederington & Guan 2010 など）。暴落時は変動率とリターンが裾で連動する（Aboura & Wagner 2016）。下落局面ほど非対称性が強い。→ 売られすぎ・投げ売りは極端な値になりやすく、底の方が検出しやすい理由の一つと考えられる（価格の形との関係は推論） | 確立（変動率）／推論（形） | [HAL: Extreme Asymmetric Volatility](https://hal.archives-ouvertes.fr/hal-01526366), [ASEAN-5 研究](https://so05.tci-thaijo.org/index.php/saje/article/view/241862) |
| 7 | レバレッジETFは毎日リバランスするため値動きの経路に依存し、長く持つと変動率による目減りが出る（Cheng & Madhavan 2009, JOIM）。→ TQQQ では、空振りの売買による往復ビンタのコストが大きい | 確立 | [JOIM](https://joim.com/dynamics-leveraged-inverse-exchange-traded-funds) |
| 8 | ZigZag や高値/安値の転換点は、リアルタイムでは一定の反転を待たないと確定できない（遅れ）。描き直しをする（リペイント）版は最後の脚を後から引き直すので、過去チャートでは完璧に見える | 確立（実務） | [futures.io](https://futures.io/trading_member/56339-morganj71.html), [TradingView ZigZag](https://vn.tradingview.com/script/Bc8UqCv8-ZigZag) |
| 9 | ニューラルネットによる転換点予測を追試すると、元の論文の成績は楽観的すぎた（テスト期間60日と短い） | 示唆 | [arXiv 1209.0127](https://ar5iv.arxiv.org/html/1209.0127) |

## TurnLine への示唆（仮説。実データ検証で確かめる）
- 「底が近い」は「天井が近い」より作りやすい。天井側は買われすぎが続くので、早すぎる点灯や空振りが増えやすい。
- 過去チャートに確定ラベルを転換点ちょうどに描くと、実際より良く見える。リアルタイムでは確定は数本遅れる（今回のデータでは、確定までの遅れの中央値が天井7本・底4本）。
- 多数の設定を試して一番良いものを選ぶと、未使用期間で崩れやすい。学習用と検証用の期間を分け、帰無検定と比べることが必須。
