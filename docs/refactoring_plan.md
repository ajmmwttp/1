# コードリファクタリング計画

## 現状の問題点サマリー

### 🔴 重大（即座に対応すべき）
1. **モノリシック構造** - 6000行が1ファイル
2. **グローバル変数** - 状態管理が危険
3. **エラー隠蔽** - デバッグ不可能

### 🟠 深刻（早急に対応すべき）
4. **ハードコード** - チューニング不可
5. **型情報なし** - バグを誘発
6. **テストなし** - 品質保証不可
7. **パフォーマンス** - 5-10分かかる

### 🟡 中程度（計画的に対応）
8. **環境依存** - Colab専用
9. **設定埋め込み** - 柔軟性なし
10. **重複コード** - 保守性低下

---

## 段階的改善計画

### フェーズ1: 基盤整備（1-2週間）

#### Step 1: プロジェクト構造の作成
```
src/
├── __init__.py
├── config/
│   ├── __init__.py
│   ├── settings.py          # 設定管理
│   └── constants.py         # 定数定義
├── data/
│   ├── __init__.py
│   ├── loader.py            # データ読み込み
│   ├── validator.py         # データ検証
│   └── preprocessor.py      # 前処理
├── features/
│   ├── __init__.py
│   ├── basic.py             # 基本特徴量
│   ├── temporal.py          # 時系列特徴量
│   ├── calendar.py          # カレンダー特徴量
│   └── advanced.py          # 高度な特徴量
├── models/
│   ├── __init__.py
│   ├── base_models.py       # 15モデル定義
│   ├── trainer.py           # 学習ロジック
│   └── predictor.py         # 予測ロジック
├── ensemble/
│   ├── __init__.py
│   ├── v65_methods.py       # 3手法アンサンブル
│   ├── meta_model.py        # メタモデル
│   └── weight_optimizer.py  # 動的重み調整
├── analysis/
│   ├── __init__.py
│   ├── confidence.py        # 信頼度スコア
│   ├── shap_analysis.py     # SHAP分析
│   └── memory_notebook.py   # AI記憶ノート
├── utils/
│   ├── __init__.py
│   ├── logger.py            # ロギング
│   ├── holidays.py          # 祝日管理
│   └── reporting.py         # レポート生成
└── main.py                  # エントリーポイント
```

#### Step 2: 設定ファイルの分離
```python
# config/settings.py
from dataclasses import dataclass
from typing import Dict

@dataclass
class EnsembleWeights:
    similar: float = 0.40
    prev_year: float = 0.40
    trend: float = 0.20

@dataclass
class GrowthThresholds:
    high: float = 1.15
    medium: float = 1.05
    low: float = 0.95

@dataclass
class PredictionConfig:
    weights: EnsembleWeights = EnsembleWeights()
    thresholds: GrowthThresholds = GrowthThresholds()
    month_start_days: int = 3
    recent_years: int = 2

    def to_dict(self) -> Dict:
        return {
            'weights': {
                'similar': self.weights.similar,
                'prev_year': self.weights.prev_year,
                'trend': self.weights.trend
            },
            'thresholds': {
                'high': self.thresholds.high,
                'medium': self.thresholds.medium,
                'low': self.thresholds.low
            }
        }
```

#### Step 3: ロギングシステムの導入
```python
# utils/logger.py
import logging
from typing import Optional

def setup_logger(
    name: str,
    level: int = logging.INFO,
    log_file: Optional[str] = None
) -> logging.Logger:
    """統一されたロガーを設定"""
    logger = logging.getLogger(name)
    logger.setLevel(level)

    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # コンソールハンドラ
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # ファイルハンドラ（オプション）
    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger

# 使用例
logger = setup_logger(__name__)
logger.info("予測を開始します")
logger.error("エラーが発生しました", exc_info=True)
```

---

### フェーズ2: コア機能の分離（2-3週間）

#### Step 4: データ処理モジュール
```python
# data/loader.py
from pathlib import Path
import pandas as pd
from typing import Union
from ..utils.logger import setup_logger

logger = setup_logger(__name__)

class DataLoader:
    """実績データの読み込みと検証"""

    def __init__(self, data_path: Union[str, Path]):
        self.data_path = Path(data_path)

    def load(self, filename: Optional[str] = None) -> pd.DataFrame:
        """データを読み込む"""
        if filename is None:
            filename = self._find_data_file()

        file_path = self.data_path / filename

        logger.info(f"データを読み込み中: {file_path}")

        if file_path.suffix == '.xlsx':
            df = pd.read_excel(file_path)
        elif file_path.suffix == '.csv':
            df = pd.read_csv(file_path)
        else:
            raise ValueError(f"未対応のファイル形式: {file_path.suffix}")

        logger.info(f"読み込み完了: {len(df)}件")
        return df

    def _find_data_file(self) -> str:
        """実績表ファイルを自動検出"""
        patterns = ['実績表*.csv', '実績表*.xlsx']

        for pattern in patterns:
            files = list(self.data_path.glob(pattern))
            if files:
                return files[0].name

        raise FileNotFoundError(
            f"実績表ファイルが見つかりません: {self.data_path}"
        )
```

#### Step 5: v65.0アンサンブルの分離
```python
# ensemble/v65_methods.py
from typing import Tuple, Dict
import pandas as pd
from ..config.settings import PredictionConfig
from ..utils.logger import setup_logger

logger = setup_logger(__name__)

class V65Ensemble:
    """v65.0の3手法アンサンブル予測"""

    def __init__(self, config: PredictionConfig):
        self.config = config

    def predict(
        self,
        df: pd.DataFrame,
        prediction_date: str
    ) -> Tuple[float, Dict]:
        """3手法で予測してアンサンブル"""

        # 手法1: 類似日ベース
        pred1, details1 = self._predict_similar_days(df, prediction_date)

        # 手法2: 前年同日ベース
        pred2, details2 = self._predict_previous_year(df, prediction_date)

        # 手法3: 直近トレンド
        pred3, details3 = self._predict_recent_trend(df, prediction_date)

        # 重みを最適化
        weights = self._optimize_weights(
            prediction_date, df, details1, details2, details3
        )

        # アンサンブル
        ensemble = (
            pred1 * weights[0] +
            pred2 * weights[1] +
            pred3 * weights[2]
        )

        details = {
            'pred1': pred1,
            'pred2': pred2,
            'pred3': pred3,
            'weights': weights,
            'details1': details1,
            'details2': details2,
            'details3': details3
        }

        logger.info(f"v65.0アンサンブル結果: {ensemble:.0f}件")

        return ensemble, details

    def _predict_similar_days(
        self,
        df: pd.DataFrame,
        prediction_date: str
    ) -> Tuple[float, Dict]:
        """類似日ベース予測"""
        # 元のpredict_by_similar_days_v65の内容
        ...

    def _predict_previous_year(
        self,
        df: pd.DataFrame,
        prediction_date: str
    ) -> Tuple[float, Dict]:
        """前年同日ベース予測"""
        # 元のpredict_by_previous_year_v65の内容
        ...

    def _predict_recent_trend(
        self,
        df: pd.DataFrame,
        prediction_date: str
    ) -> Tuple[float, Dict]:
        """直近トレンド補正予測"""
        # 元のpredict_by_recent_trend_v65の内容
        ...

    def _optimize_weights(
        self,
        target_date: str,
        df: pd.DataFrame,
        details1: Dict,
        details2: Dict,
        details3: Dict
    ) -> Tuple[float, float, float]:
        """動的重み調整"""
        # 元のoptimize_ensemble_weights_v66の内容
        ...
```

---

### フェーズ3: テストとCI/CD（1-2週間）

#### Step 6: ユニットテストの作成
```python
# tests/test_v65_ensemble.py
import pytest
import pandas as pd
from src.ensemble.v65_methods import V65Ensemble
from src.config.settings import PredictionConfig

@pytest.fixture
def sample_data():
    """テスト用データ"""
    dates = pd.date_range('2023-01-01', '2024-12-31', freq='D')
    return pd.DataFrame({
        'Date': dates,
        '合計': [1000 + i for i in range(len(dates))]
    })

@pytest.fixture
def ensemble():
    """V65Ensembleインスタンス"""
    config = PredictionConfig()
    return V65Ensemble(config)

def test_predict_returns_positive_value(ensemble, sample_data):
    """予測値が正の数であることを確認"""
    pred, details = ensemble.predict(sample_data, '2025-01-15')

    assert pred > 0
    assert isinstance(pred, float)

def test_predict_returns_details(ensemble, sample_data):
    """詳細情報が返されることを確認"""
    pred, details = ensemble.predict(sample_data, '2025-01-15')

    assert 'pred1' in details
    assert 'pred2' in details
    assert 'pred3' in details
    assert 'weights' in details

def test_weights_sum_to_one(ensemble, sample_data):
    """重みの合計が1.0であることを確認"""
    pred, details = ensemble.predict(sample_data, '2025-01-15')

    weights = details['weights']
    assert abs(sum(weights) - 1.0) < 1e-6

def test_invalid_date_raises_error(ensemble, sample_data):
    """無効な日付でエラーが発生することを確認"""
    with pytest.raises(ValueError):
        ensemble.predict(sample_data, 'invalid-date')
```

#### Step 7: 統合テスト
```python
# tests/test_integration.py
import pytest
from pathlib import Path
from src.main import PredictionPipeline

def test_end_to_end_prediction(tmp_path):
    """エンドツーエンドの予測テスト"""
    # テストデータを作成
    test_data = tmp_path / "test_data.csv"
    # ... データ作成

    # パイプライン実行
    pipeline = PredictionPipeline(data_path=tmp_path)
    result = pipeline.predict('2025-01-15')

    # 検証
    assert result.final_prediction > 0
    assert 0 <= result.confidence_score <= 100
    assert result.pred_lower <= result.final_prediction <= result.pred_upper
```

---

### フェーズ4: パフォーマンス最適化（1週間）

#### Step 8: 並列処理の導入
```python
# models/trainer.py
from concurrent.futures import ProcessPoolExecutor, as_completed
from typing import Dict
import pandas as pd

class ParallelModelTrainer:
    """モデルを並列学習"""

    def __init__(self, max_workers: int = 4):
        self.max_workers = max_workers

    def train_all(
        self,
        models: Dict,
        X: pd.DataFrame,
        y: pd.Series,
        weights: pd.Series
    ) -> Dict:
        """全モデルを並列学習"""

        with ProcessPoolExecutor(max_workers=self.max_workers) as executor:
            # ジョブを投入
            futures = {
                executor.submit(
                    self._train_single,
                    name, model, X, y, weights
                ): name
                for name, model in models.items()
            }

            # 結果を収集
            results = {}
            for future in as_completed(futures):
                name = futures[future]
                try:
                    results[name] = future.result()
                    logger.info(f"✓ {name} 学習完了")
                except Exception as e:
                    logger.error(f"✗ {name} 学習失敗: {e}")

        return results

    @staticmethod
    def _train_single(name, model, X, y, weights):
        """単一モデルの学習"""
        # ... 学習ロジック
        return trained_model
```

---

### フェーズ5: ドキュメントとデプロイ（1週間）

#### Step 9: API化（オプション）
```python
# api/main.py
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from datetime import date
from src.main import PredictionPipeline

app = FastAPI(title="AI受注予測API v66.0")

class PredictionRequest(BaseModel):
    prediction_date: date
    actual_12h: int = 0
    actual_14h: int = 0
    actual_15h: int = 0

class PredictionResponse(BaseModel):
    final_prediction: int
    confidence_score: float
    pred_lower: int
    pred_upper: int
    v65_ensemble: float

@app.post("/predict", response_model=PredictionResponse)
async def predict(request: PredictionRequest):
    """受注予測を実行"""
    try:
        pipeline = PredictionPipeline()
        result = pipeline.predict(
            prediction_date=str(request.prediction_date),
            actuals={
                12: request.actual_12h,
                14: request.actual_14h,
                15: request.actual_15h
            }
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

---

## 実装優先順位

### 今すぐ実施すべき（Phase 1）
1. ✅ プロジェクト構造の作成
2. ✅ 設定ファイルの分離
3. ✅ ロギングシステムの導入

### 1週間以内（Phase 2）
4. データ処理モジュールの分離
5. v65.0アンサンブルの分離
6. エラーハンドリングの統一

### 2週間以内（Phase 3）
7. ユニットテストの作成
8. 統合テストの作成
9. CI/CDパイプラインの構築

### 1ヶ月以内（Phase 4-5）
10. 並列処理の導入
11. メモリ最適化
12. API化（必要に応じて）

---

## 期待される効果

### 品質向上
- ✅ バグの早期発見（テストカバレッジ80%以上）
- ✅ 保守性の向上（モジュール化）
- ✅ 可読性の向上（型ヒント、ドキュメント）

### パフォーマンス
- ✅ 実行時間: 5-10分 → 2-3分
- ✅ メモリ使用量: 30%削減

### 開発効率
- ✅ 新機能追加が容易
- ✅ チーム開発が可能
- ✅ 実験・チューニングが容易

---

## 移行戦略

### オプション1: 段階的移行（推奨）
1. 新しい構造で機能を再実装
2. 旧コードと並行運用
3. 徐々に新コードに切り替え

### オプション2: 一括移行
1. 全機能を一度に移行
2. リスクは高いが短期間で完了

### オプション3: ハイブリッド
1. コア機能のみ移行
2. 残りは旧コードを維持
3. 必要に応じて段階的に移行

---

## 結論

現在のコードは**機能的には完成**していますが、**ソフトウェアエンジニアリングの観点では大幅な改善が必要**です。

特に以下の3点は早急に対応すべきです:
1. **モジュール分割** - 保守性・テスト性の向上
2. **テストコード** - 品質保証
3. **設定の分離** - 柔軟性・実験性の向上

これらの改善により、長期的な保守コストを大幅に削減できます。
