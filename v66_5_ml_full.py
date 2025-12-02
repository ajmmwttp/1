# =============================================================================
# v66.5 メタ認知AI予測システム【完全機械学習統合版】
# =============================================================================
# 搭載ML: LightGBM, XGBoost, CatBoost, RandomForest, GradientBoosting,
#         Ridge, Lasso, ElasticNet, SVR, MLPRegressor(ニューラルネット)
# =============================================================================

print("="*70)
print("【v66.5 メタ認知AI予測システム】完全機械学習統合版")
print("="*70)

import os
import pandas as pd
import numpy as np
from sklearn.preprocessing import StandardScaler, RobustScaler
from sklearn.model_selection import TimeSeriesSplit, cross_val_score
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor, ExtraTreesRegressor
from sklearn.ensemble import StackingRegressor, VotingRegressor
from sklearn.linear_model import Ridge, Lasso, ElasticNet, BayesianRidge
from sklearn.svm import SVR
from sklearn.neural_network import MLPRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error
from datetime import date, timedelta, datetime
import ipywidgets as widgets
from IPython.display import display, clear_output, HTML
import warnings
import traceback
warnings.filterwarnings("ignore")

# オプショナルライブラリ
try:
    import lightgbm as lgb
    HAS_LGB = True
    print("✅ LightGBM")
except:
    HAS_LGB = False
    print("⚠️ LightGBM未インストール")

try:
    import xgboost as xgb
    HAS_XGB = True
    print("✅ XGBoost")
except:
    HAS_XGB = False
    print("⚠️ XGBoost未インストール")

try:
    from catboost import CatBoostRegressor
    HAS_CAT = True
    print("✅ CatBoost")
except:
    HAS_CAT = False
    print("⚠️ CatBoost未インストール")

try:
    import jpholiday
    HAS_JPHOLIDAY = True
    print("✅ jpholiday")
except:
    HAS_JPHOLIDAY = False

print("\n✅ 基本ライブラリ読み込み完了")


# =============================================================================
# 特徴量エンジニアリング (100+特徴量)
# =============================================================================
def create_advanced_features(df, target_col='合計'):
    """100以上の高度な特徴量を生成"""
    print("  📊 特徴量エンジニアリング実行中...")

    df = df.copy()
    df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
    df = df.dropna(subset=['Date']).sort_values('Date').reset_index(drop=True)

    # 基本時間特徴量
    df['year'] = df['Date'].dt.year
    df['month'] = df['Date'].dt.month
    df['day'] = df['Date'].dt.day
    df['weekday'] = df['Date'].dt.dayofweek
    df['week_of_year'] = df['Date'].dt.isocalendar().week.astype(int)
    df['week_of_month'] = ((df['day'] - 1) // 7 + 1)
    df['quarter'] = df['Date'].dt.quarter
    df['day_of_year'] = df['Date'].dt.dayofyear

    # 周期的エンコーディング
    df['month_sin'] = np.sin(2 * np.pi * df['month'] / 12)
    df['month_cos'] = np.cos(2 * np.pi * df['month'] / 12)
    df['weekday_sin'] = np.sin(2 * np.pi * df['weekday'] / 7)
    df['weekday_cos'] = np.cos(2 * np.pi * df['weekday'] / 7)
    df['day_sin'] = np.sin(2 * np.pi * df['day'] / 31)
    df['day_cos'] = np.cos(2 * np.pi * df['day'] / 31)
    df['week_of_year_sin'] = np.sin(2 * np.pi * df['week_of_year'] / 52)
    df['week_of_year_cos'] = np.cos(2 * np.pi * df['week_of_year'] / 52)
    df['quarter_sin'] = np.sin(2 * np.pi * df['quarter'] / 4)
    df['quarter_cos'] = np.cos(2 * np.pi * df['quarter'] / 4)

    # 月初・月末・週末フラグ
    df['is_month_start'] = (df['day'] <= 3).astype(int)
    df['is_month_end'] = (df['day'] >= 28).astype(int)
    df['is_weekend'] = (df['weekday'] >= 5).astype(int)
    df['is_monday'] = (df['weekday'] == 0).astype(int)
    df['is_friday'] = (df['weekday'] == 4).astype(int)

    # 祝日
    if HAS_JPHOLIDAY:
        df['is_holiday'] = df['Date'].apply(lambda x: 1 if jpholiday.is_holiday(x) else 0)
        df['is_holiday_eve'] = df['is_holiday'].shift(-1).fillna(0).astype(int)
        df['is_after_holiday'] = df['is_holiday'].shift(1).fillna(0).astype(int)
    else:
        df['is_holiday'] = 0
        df['is_holiday_eve'] = 0
        df['is_after_holiday'] = 0

    # 季節
    df['season'] = df['month'].apply(lambda x: 0 if x in [3,4,5] else (1 if x in [6,7,8] else (2 if x in [9,10,11] else 3)))
    for s in range(4):
        df[f'season_{s}'] = (df['season'] == s).astype(int)

    # ラグ特徴量 (1日〜30日)
    if target_col in df.columns:
        for lag in [1, 2, 3, 4, 5, 6, 7, 14, 21, 28, 30]:
            df[f'lag_{lag}'] = df[target_col].shift(lag)

        # 同曜日ラグ
        df['lag_7_same_weekday'] = df[target_col].shift(7)
        df['lag_14_same_weekday'] = df[target_col].shift(14)
        df['lag_21_same_weekday'] = df[target_col].shift(21)
        df['lag_28_same_weekday'] = df[target_col].shift(28)

        # ローリング統計 (7日, 14日, 30日窓)
        for window in [3, 7, 14, 21, 30]:
            df[f'rolling_mean_{window}'] = df[target_col].shift(1).rolling(window=window, min_periods=1).mean()
            df[f'rolling_std_{window}'] = df[target_col].shift(1).rolling(window=window, min_periods=1).std()
            df[f'rolling_min_{window}'] = df[target_col].shift(1).rolling(window=window, min_periods=1).min()
            df[f'rolling_max_{window}'] = df[target_col].shift(1).rolling(window=window, min_periods=1).max()
            df[f'rolling_median_{window}'] = df[target_col].shift(1).rolling(window=window, min_periods=1).median()

        # 変化率
        df['pct_change_1'] = df[target_col].pct_change(1).shift(1)
        df['pct_change_7'] = df[target_col].pct_change(7).shift(1)
        df['pct_change_14'] = df[target_col].pct_change(14).shift(1)
        df['pct_change_30'] = df[target_col].pct_change(30).shift(1)

        # 差分
        df['diff_1'] = df[target_col].diff(1).shift(1)
        df['diff_7'] = df[target_col].diff(7).shift(1)

        # 曜日別平均との差
        weekday_mean = df.groupby('weekday')[target_col].transform('mean')
        df['weekday_mean'] = weekday_mean
        df['diff_from_weekday_mean'] = df[target_col].shift(1) - weekday_mean

        # 月別平均との差
        month_mean = df.groupby('month')[target_col].transform('mean')
        df['month_mean'] = month_mean
        df['diff_from_month_mean'] = df[target_col].shift(1) - month_mean

        # 指数移動平均 (EMA)
        for span in [7, 14, 30]:
            df[f'ema_{span}'] = df[target_col].shift(1).ewm(span=span, adjust=False).mean()

        # 前年同日
        df['prev_year_same_day'] = df[target_col].shift(365)
        df['prev_year_same_week'] = df[target_col].shift(364)  # 同曜日

        # 年間成長率
        df['yoy_growth'] = (df[target_col].shift(1) / df[target_col].shift(366)).fillna(1) - 1

        # ボラティリティ
        df['volatility_7'] = df[target_col].shift(1).rolling(7).std() / df[target_col].shift(1).rolling(7).mean()
        df['volatility_30'] = df[target_col].shift(1).rolling(30).std() / df[target_col].shift(1).rolling(30).mean()

    # 無限値・NaN処理
    df = df.replace([np.inf, -np.inf], np.nan)

    feature_count = len([c for c in df.columns if c not in ['Date', target_col]])
    print(f"  ✅ {feature_count}個の特徴量を生成")

    return df


# =============================================================================
# 機械学習モデルクラス
# =============================================================================
class MLPredictor:
    """複数の機械学習モデルを統合した予測クラス"""

    def __init__(self):
        self.models = {}
        self.scaler = RobustScaler()
        self.feature_cols = None
        self.is_trained = False
        self.model_scores = {}

    def _init_models(self):
        """全モデルを初期化"""
        models = {}

        # 1. LightGBM
        if HAS_LGB:
            models['LightGBM'] = lgb.LGBMRegressor(
                n_estimators=500,
                learning_rate=0.05,
                max_depth=8,
                num_leaves=31,
                min_child_samples=20,
                subsample=0.8,
                colsample_bytree=0.8,
                reg_alpha=0.1,
                reg_lambda=0.1,
                random_state=42,
                verbose=-1,
                n_jobs=-1
            )

        # 2. XGBoost
        if HAS_XGB:
            models['XGBoost'] = xgb.XGBRegressor(
                n_estimators=500,
                learning_rate=0.05,
                max_depth=8,
                min_child_weight=3,
                subsample=0.8,
                colsample_bytree=0.8,
                reg_alpha=0.1,
                reg_lambda=0.1,
                random_state=42,
                verbosity=0,
                n_jobs=-1
            )

        # 3. CatBoost
        if HAS_CAT:
            models['CatBoost'] = CatBoostRegressor(
                iterations=500,
                learning_rate=0.05,
                depth=8,
                l2_leaf_reg=3,
                random_state=42,
                verbose=0
            )

        # 4. RandomForest
        models['RandomForest'] = RandomForestRegressor(
            n_estimators=300,
            max_depth=15,
            min_samples_split=5,
            min_samples_leaf=2,
            max_features='sqrt',
            random_state=42,
            n_jobs=-1
        )

        # 5. ExtraTrees
        models['ExtraTrees'] = ExtraTreesRegressor(
            n_estimators=300,
            max_depth=15,
            min_samples_split=5,
            min_samples_leaf=2,
            random_state=42,
            n_jobs=-1
        )

        # 6. GradientBoosting
        models['GradientBoosting'] = GradientBoostingRegressor(
            n_estimators=300,
            learning_rate=0.05,
            max_depth=6,
            min_samples_split=5,
            min_samples_leaf=2,
            subsample=0.8,
            random_state=42
        )

        # 7. Ridge回帰
        models['Ridge'] = Ridge(alpha=1.0, random_state=42)

        # 8. Lasso回帰
        models['Lasso'] = Lasso(alpha=0.1, random_state=42, max_iter=5000)

        # 9. ElasticNet
        models['ElasticNet'] = ElasticNet(alpha=0.1, l1_ratio=0.5, random_state=42, max_iter=5000)

        # 10. BayesianRidge
        models['BayesianRidge'] = BayesianRidge()

        # 11. SVR (Support Vector Regression)
        models['SVR'] = SVR(kernel='rbf', C=100, gamma='scale', epsilon=0.1)

        # 12. MLPRegressor (ニューラルネットワーク)
        models['NeuralNet'] = MLPRegressor(
            hidden_layer_sizes=(128, 64, 32),
            activation='relu',
            solver='adam',
            learning_rate='adaptive',
            learning_rate_init=0.001,
            max_iter=1000,
            early_stopping=True,
            validation_fraction=0.1,
            random_state=42
        )

        return models

    def train(self, df, target_col='合計'):
        """全モデルを訓練"""
        print("\n" + "="*70)
        print("【機械学習モデル訓練開始】")
        print("="*70)

        # 特徴量生成
        df_feat = create_advanced_features(df, target_col)

        # 学習対象データ抽出
        df_train = df_feat.dropna(subset=[target_col])

        # 特徴量選択
        exclude_cols = ['Date', target_col, 'year']
        self.feature_cols = [c for c in df_train.columns if c not in exclude_cols and df_train[c].dtype in ['int64', 'float64']]

        # NaN処理
        X = df_train[self.feature_cols].fillna(0)
        y = df_train[target_col]

        # データ不足チェック
        if len(X) < 30:
            print("⚠️ データ不足（30日以上必要）")
            return False

        print(f"  訓練データ: {len(X)}件, 特徴量: {len(self.feature_cols)}個")

        # スケーリング
        X_scaled = self.scaler.fit_transform(X)

        # モデル初期化
        self.models = self._init_models()

        # 各モデル訓練
        print("\n【各モデル訓練】")
        tscv = TimeSeriesSplit(n_splits=3)

        for name, model in self.models.items():
            try:
                print(f"  🔄 {name}...", end=" ")

                # 時系列CV
                cv_scores = cross_val_score(model, X_scaled, y, cv=tscv, scoring='neg_mean_absolute_error')
                cv_mae = -cv_scores.mean()

                # 全データで再訓練
                model.fit(X_scaled, y)

                self.model_scores[name] = cv_mae
                print(f"✅ CV-MAE: {cv_mae:.1f}")

            except Exception as e:
                print(f"❌ エラー: {e}")
                self.model_scores[name] = float('inf')

        self.is_trained = True

        # スコアサマリー
        print("\n【モデル性能ランキング】")
        sorted_scores = sorted(self.model_scores.items(), key=lambda x: x[1])
        for i, (name, score) in enumerate(sorted_scores[:5], 1):
            print(f"  {i}. {name}: MAE={score:.1f}")

        return True

    def predict(self, df, target_date, target_col='合計'):
        """全モデルで予測"""
        if not self.is_trained:
            print("⚠️ モデル未訓練")
            return None, {}

        print("\n【機械学習予測】")

        # 特徴量生成
        df_feat = create_advanced_features(df, target_col)

        # 予測日の行を作成
        target_dt = pd.to_datetime(target_date)

        # 予測日のデータがあるか確認
        target_row = df_feat[df_feat['Date'] == target_dt]

        if len(target_row) == 0:
            # 予測日のデータがない場合、直近データから作成
            last_row = df_feat.iloc[-1:].copy()
            last_row['Date'] = target_dt

            # 時間特徴量を更新
            last_row['year'] = target_dt.year
            last_row['month'] = target_dt.month
            last_row['day'] = target_dt.day
            last_row['weekday'] = target_dt.dayofweek
            last_row['week_of_year'] = target_dt.isocalendar().week
            last_row['week_of_month'] = (target_dt.day - 1) // 7 + 1
            last_row['quarter'] = (target_dt.month - 1) // 3 + 1
            last_row['day_of_year'] = target_dt.timetuple().tm_yday

            # 周期エンコーディング更新
            last_row['month_sin'] = np.sin(2 * np.pi * target_dt.month / 12)
            last_row['month_cos'] = np.cos(2 * np.pi * target_dt.month / 12)
            last_row['weekday_sin'] = np.sin(2 * np.pi * target_dt.dayofweek / 7)
            last_row['weekday_cos'] = np.cos(2 * np.pi * target_dt.dayofweek / 7)

            # フラグ更新
            last_row['is_month_start'] = 1 if target_dt.day <= 3 else 0
            last_row['is_month_end'] = 1 if target_dt.day >= 28 else 0
            last_row['is_weekend'] = 1 if target_dt.dayofweek >= 5 else 0
            last_row['is_monday'] = 1 if target_dt.dayofweek == 0 else 0
            last_row['is_friday'] = 1 if target_dt.dayofweek == 4 else 0

            if HAS_JPHOLIDAY:
                last_row['is_holiday'] = 1 if jpholiday.is_holiday(target_dt) else 0

            target_row = last_row

        # 特徴量抽出
        X_pred = target_row[self.feature_cols].fillna(0)
        X_pred_scaled = self.scaler.transform(X_pred)

        # 各モデルで予測
        predictions = {}
        for name, model in self.models.items():
            try:
                pred = model.predict(X_pred_scaled)[0]
                predictions[name] = max(0, pred)  # 負の値は0に
            except Exception as e:
                print(f"  ⚠️ {name}予測エラー: {e}")

        if len(predictions) == 0:
            return None, {}

        # 加重平均アンサンブル (MAEの逆数で重み付け)
        weights = {}
        total_inv_score = 0
        for name in predictions:
            if self.model_scores.get(name, float('inf')) < float('inf'):
                inv_score = 1 / (self.model_scores[name] + 1)
                weights[name] = inv_score
                total_inv_score += inv_score

        if total_inv_score > 0:
            weights = {k: v/total_inv_score for k, v in weights.items()}
        else:
            weights = {k: 1/len(predictions) for k in predictions}

        # 加重平均
        ensemble_pred = sum(predictions[k] * weights.get(k, 0) for k in predictions)

        # 結果表示
        print(f"\n  【各モデル予測】")
        sorted_preds = sorted(predictions.items(), key=lambda x: self.model_scores.get(x[0], float('inf')))
        for name, pred in sorted_preds[:6]:
            weight = weights.get(name, 0) * 100
            print(f"    {name}: {pred:.0f}件 (重み: {weight:.1f}%)")

        print(f"\n  ★ MLアンサンブル予測: {ensemble_pred:.0f}件")

        return ensemble_pred, {
            'predictions': predictions,
            'weights': weights,
            'model_scores': self.model_scores
        }


# =============================================================================
# 統計予測関数（従来手法）
# =============================================================================
def predict_by_similar_days(df_orig, prediction_date, recent_years=3, top_n=15):
    """多次元類似日検索"""
    try:
        if df_orig is None or len(df_orig) == 0 or '合計' not in df_orig.columns:
            return 1000, {}

        pred_date = pd.to_datetime(prediction_date)
        df = df_orig.copy()
        df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
        df = df.dropna(subset=['Date'])
        df = df[df['合計'] > 0].copy()

        if len(df) == 0:
            return 1000, {}

        # 特徴量計算
        df['weekday'] = df['Date'].dt.dayofweek
        df['month'] = df['Date'].dt.month
        df['day'] = df['Date'].dt.day
        df['week_of_month'] = ((df['day'] - 1) // 7 + 1)
        df['month_sin'] = np.sin(2 * np.pi * df['month'] / 12)
        df['month_cos'] = np.cos(2 * np.pi * df['month'] / 12)
        df['weekday_sin'] = np.sin(2 * np.pi * df['weekday'] / 7)
        df['weekday_cos'] = np.cos(2 * np.pi * df['weekday'] / 7)

        target_features = {
            'weekday': pred_date.dayofweek, 'month': pred_date.month,
            'week_of_month': (pred_date.day - 1) // 7 + 1,
            'month_sin': np.sin(2 * np.pi * pred_date.month / 12),
            'month_cos': np.cos(2 * np.pi * pred_date.month / 12),
            'weekday_sin': np.sin(2 * np.pi * pred_date.dayofweek / 7),
            'weekday_cos': np.cos(2 * np.pi * pred_date.dayofweek / 7),
        }

        feature_weights = {'weekday': 5.0, 'month': 3.0, 'week_of_month': 2.0,
            'month_sin': 2.0, 'month_cos': 2.0, 'weekday_sin': 3.0, 'weekday_cos': 3.0}

        feature_cols = list(feature_weights.keys())
        weights_array = np.array([feature_weights[col] for col in feature_cols])

        cutoff_date = pred_date - pd.DateOffset(years=recent_years)
        df_recent = df[(df['Date'] >= cutoff_date) & (df['Date'] < pred_date)].copy()
        if len(df_recent) < 10:
            df_recent = df[df['Date'] < pred_date].copy()
        if len(df_recent) == 0:
            return df['合計'].mean(), {}

        X_history = df_recent[feature_cols].values
        X_target = np.array([[target_features[col] for col in feature_cols]])

        scaler = StandardScaler()
        X_history_scaled = scaler.fit_transform(X_history)
        X_target_scaled = scaler.transform(X_target)

        weighted_diff = (X_history_scaled - X_target_scaled) * weights_array
        distances = np.sqrt((weighted_diff ** 2).sum(axis=1))
        df_recent['distance'] = distances

        similar_days = df_recent.nsmallest(min(top_n, len(df_recent)), 'distance').copy()

        inv_distances = 1 / (similar_days['distance'].values + 0.01)
        similarity_weights = inv_distances / inv_distances.sum()
        prediction = (similar_days['合計'].values * similarity_weights).sum()

        return prediction, {'method': 'similar_days', 'count': len(similar_days)}
    except:
        return 1000, {}


def predict_by_previous_year(df_orig, prediction_date):
    """前年同日ベース予測"""
    try:
        if df_orig is None or len(df_orig) == 0:
            return 1000, {}

        pred_date = pd.to_datetime(prediction_date)
        df = df_orig.copy()
        df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
        df = df.dropna(subset=['Date'])
        df['year'], df['month'] = df['Date'].dt.year, df['Date'].dt.month

        prev_year_data = df[(df['year'] == pred_date.year - 1) & (df['month'] == pred_date.month) & (df['合計'] > 0)]
        if len(prev_year_data) == 0:
            return df['合計'].mean() if len(df) > 0 else 1000, {}

        prev_year_avg = prev_year_data['合計'].mean()
        current_year_data = df[(df['year'] == pred_date.year) & (df['合計'] > 0)]
        prev_year_all = df[(df['year'] == pred_date.year - 1) & (df['合計'] > 0)]

        growth = np.clip(current_year_data['合計'].mean() / prev_year_all['合計'].mean(), 0.8, 1.3) if len(current_year_data) > 0 and len(prev_year_all) > 0 else 1.0

        return prev_year_avg * growth, {'method': 'previous_year', 'growth': growth}
    except:
        return 1000, {}


# =============================================================================
# メイン予測関数
# =============================================================================
ml_predictor = MLPredictor()

def run_prediction_v66_5(target_date, actuals, df_orig):
    """v66.5 メイン予測（ML統合版）"""
    global ml_predictor

    print("\n" + "="*70)
    print("【v66.5 予測開始】完全機械学習統合版")
    print("="*70)
    print(f"予測日: {target_date}\n")

    try:
        df = df_orig.copy()
        if 'Date' in df.columns:
            df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
            df = df.dropna(subset=['Date'])

        # 列名正規化
        if '合計' not in df.columns:
            for col in ['actual_value', 'total', '件数']:
                if col in df.columns:
                    df = df.rename(columns={col: '合計'})
                    break

        df['合計'] = pd.to_numeric(df['合計'], errors='coerce').fillna(0)
        df = df[df['合計'] > 0]

        print(f"データ: {len(df)}日分\n")

        # ===============================
        # 1. 機械学習予測
        # ===============================
        if not ml_predictor.is_trained:
            ml_predictor.train(df, '合計')

        ml_pred, ml_info = ml_predictor.predict(df, target_date, '合計')

        # ===============================
        # 2. 統計予測（類似日・前年）
        # ===============================
        print("\n【統計手法予測】")
        stat_pred1, _ = predict_by_similar_days(df, target_date)
        stat_pred2, _ = predict_by_previous_year(df, target_date)
        stat_avg = (stat_pred1 + stat_pred2) / 2
        print(f"  類似日: {stat_pred1:.0f}件")
        print(f"  前年同日: {stat_pred2:.0f}件")
        print(f"  統計平均: {stat_avg:.0f}件")

        # ===============================
        # 3. 最終アンサンブル (ML 70% + 統計 30%)
        # ===============================
        if ml_pred is not None:
            final_pred = ml_pred * 0.7 + stat_avg * 0.3
        else:
            final_pred = stat_avg

        # ===============================
        # 4. 12時実績調整
        # ===============================
        if actuals.get(12, 0) > 0 and '件数(～12:00)' in df.columns:
            df_12h = df[(df['件数(～12:00)'] > 0) & (df['合計'] > 0)].copy()
            if len(df_12h) > 0:
                df_12h['件数(～12:00)'] = pd.to_numeric(df_12h['件数(～12:00)'], errors='coerce')
                ratio = (df_12h['件数(～12:00)'] / df_12h['合計']).mean()
                if ratio > 0:
                    est_12h = actuals[12] / ratio
                    final_pred = final_pred * 0.3 + est_12h * 0.7
                    print(f"\n⏰ 12時実績反映: 推定{est_12h:.0f}件")

        # ===============================
        # 5. 信頼区間計算
        # ===============================
        all_preds = [stat_pred1, stat_pred2]
        if ml_pred:
            all_preds.append(ml_pred)
            if ml_info.get('predictions'):
                all_preds.extend(list(ml_info['predictions'].values()))

        pred_std = np.std(all_preds) if len(all_preds) > 1 else final_pred * 0.1
        pred_lower = max(0, final_pred - 1.96 * pred_std)
        pred_upper = final_pred + 1.96 * pred_std

        # 信頼度 (モデル間のばらつきが小さいほど高い)
        cv = pred_std / (final_pred + 1e-8)
        confidence = max(0, min(100, 100 * (1 - cv)))

        # ===============================
        # 結果表示
        # ===============================
        print("\n" + "="*70)
        print(f"★★★ 最終予測: {int(final_pred):,}件 ★★★")
        print(f"    信頼区間: {int(pred_lower):,} ～ {int(pred_upper):,}件")
        print(f"    信頼度: {confidence:.1f}点")
        print("="*70)

        # ML構成表示
        print("\n【搭載機械学習モデル】")
        ml_names = list(ml_predictor.models.keys()) if ml_predictor.is_trained else []
        print(f"  {', '.join(ml_names)}")
        print(f"  計 {len(ml_names)} モデル")

        return {
            'final_prediction': int(final_pred),
            'pred_lower': int(pred_lower),
            'pred_upper': int(pred_upper),
            'confidence_score': confidence,
            'ml_prediction': ml_pred,
            'stat_prediction': stat_avg,
            'model_count': len(ml_names)
        }

    except Exception as e:
        print(f"\n⚠️ エラー: {e}")
        traceback.print_exc()
        return {'final_prediction': 1000, 'pred_lower': 800, 'pred_upper': 1200, 'confidence_score': 0}


# =============================================================================
# UIウィジェット
# =============================================================================
date_picker = widgets.DatePicker(description='予測日:', value=date.today())
actual_12h = widgets.IntText(value=0, description='実績12時:')
run_btn = widgets.Button(description='🚀 予測実行', button_style='success',
                        layout=widgets.Layout(width='200px', height='50px'))
retrain_btn = widgets.Button(description='🔄 再学習', button_style='info',
                            layout=widgets.Layout(width='100px', height='50px'))
output = widgets.Output()
result_output = widgets.Output()

global_df = None

def on_run(b):
    global global_df
    run_btn.disabled = True
    run_btn.description = '処理中...'

    with output:
        clear_output()

        # データ読み込み
        data_file = None
        for f in os.listdir('/content/'):
            if '実績' in f and f.endswith('.xlsx'):
                data_file = f'/content/{f}'
                break
        if data_file is None:
            for f in os.listdir('/content/'):
                if f.endswith('.csv') or f.endswith('.xlsx'):
                    data_file = f'/content/{f}'
                    break

        if data_file is None:
            print("⚠️ データファイルが見つかりません")
            print("実績表Excelをアップロードしてください")
            run_btn.disabled = False
            run_btn.description = '🚀 予測実行'
            return

        print(f"📂 {os.path.basename(data_file)}")

        try:
            if data_file.endswith('.xlsx'):
                global_df = pd.read_excel(data_file, engine='openpyxl')
            else:
                global_df = pd.read_csv(data_file)
        except Exception as e:
            print(f"⚠️ ファイル読み込みエラー: {e}")
            run_btn.disabled = False
            run_btn.description = '🚀 予測実行'
            return

        # 列名正規化
        if 'Date' not in global_df.columns:
            for col in ['日付', 'date', 'prediction_date']:
                if col in global_df.columns:
                    global_df = global_df.rename(columns={col: 'Date'})
                    break

        results = run_prediction_v66_5(date_picker.value, {12: actual_12h.value}, global_df)

        with result_output:
            clear_output()
            display(HTML(f"""
            <div style='background:linear-gradient(135deg,#667eea,#764ba2);color:white;padding:20px;border-radius:10px;text-align:center;margin-top:20px;'>
                <h2 style='margin:0;'>🧠 v66.5 ML統合予測結果</h2>
                <div style='font-size:48px;font-weight:bold;margin:20px 0;'>{results['final_prediction']:,}件</div>
                <div style='font-size:16px;'>信頼区間: {results['pred_lower']:,} ～ {results['pred_upper']:,}件</div>
                <div style='font-size:16px;margin-top:10px;'>信頼度: {results['confidence_score']:.1f}点 | MLモデル: {results.get('model_count', 0)}個</div>
            </div>
            """))

    run_btn.disabled = False
    run_btn.description = '🚀 予測実行'

def on_retrain(b):
    global ml_predictor
    ml_predictor = MLPredictor()
    with output:
        clear_output()
        print("🔄 モデルをリセットしました。次回予測時に再学習します。")

run_btn.on_click(on_run)
retrain_btn.on_click(on_retrain)

ui = widgets.VBox([
    widgets.HTML('<h2 style="color:#1f77b4;">🧠 v66.5 メタ認知AI予測システム【完全ML統合版】</h2>'),
    widgets.HTML('''<p>搭載ML: LightGBM, XGBoost, CatBoost, RandomForest, ExtraTrees,<br>
                    GradientBoosting, Ridge, Lasso, ElasticNet, BayesianRidge, SVR, NeuralNet</p>'''),
    widgets.HBox([date_picker, actual_12h]),
    widgets.HBox([run_btn, retrain_btn]),
    result_output
])

display(ui, output)

print("\n" + "="*70)
print("✅ v66.5 準備完了！")
print("="*70)
print("【搭載機械学習モデル: 12種】")
print("  1. LightGBM (勾配ブースティング)")
print("  2. XGBoost (勾配ブースティング)")
print("  3. CatBoost (勾配ブースティング)")
print("  4. RandomForest (ランダムフォレスト)")
print("  5. ExtraTrees (極度ランダム化木)")
print("  6. GradientBoosting (勾配ブースティング)")
print("  7. Ridge (リッジ回帰)")
print("  8. Lasso (ラッソ回帰)")
print("  9. ElasticNet (弾性ネット)")
print(" 10. BayesianRidge (ベイズリッジ)")
print(" 11. SVR (サポートベクター回帰)")
print(" 12. NeuralNet (ニューラルネットワーク)")
print("="*70)
print("\n使い方:")
print("1. 左側📁から実績表Excelをアップロード")
print("2. 日付選択 → 「🚀 予測実行」クリック")
print("="*70)
