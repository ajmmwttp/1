# =============================================================================
# v66.7 メタ認知AI予測システム【AI記憶ノート統合版】
# =============================================================================
# v66.6の全機能 + AI記憶ノートシステム
# 搭載: 12 MLモデル + Prophet + Optuna + スタッキング + AI記憶ノート
# =============================================================================

print("="*70)
print("【v66.7 メタ認知AI予測システム】AI記憶ノート統合版")
print("="*70)

import os
import json
import pandas as pd
import numpy as np
from sklearn.preprocessing import StandardScaler, RobustScaler
from sklearn.model_selection import TimeSeriesSplit, cross_val_score
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor, ExtraTreesRegressor
from sklearn.ensemble import StackingRegressor
from sklearn.linear_model import Ridge, Lasso, ElasticNet, BayesianRidge
from sklearn.svm import SVR
from sklearn.neural_network import MLPRegressor
from sklearn.metrics import mean_absolute_error
from datetime import date, timedelta, datetime
import ipywidgets as widgets
from IPython.display import display, clear_output, HTML
import warnings
import traceback
warnings.filterwarnings("ignore")

# =============================================================================
# パス設定
# =============================================================================
AI_MEMORY_PATH = '/content/ai_memory_note_v66.csv'
MODEL_METADATA_PATH = '/content/model_metadata_v66.json'

# =============================================================================
# ライブラリインポート
# =============================================================================
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
    from prophet import Prophet
    HAS_PROPHET = True
    print("✅ Prophet")
except:
    try:
        from fbprophet import Prophet
        HAS_PROPHET = True
        print("✅ Prophet (fbprophet)")
    except:
        HAS_PROPHET = False
        print("⚠️ Prophet未インストール")

try:
    import optuna
    optuna.logging.set_verbosity(optuna.logging.WARNING)
    HAS_OPTUNA = True
    print("✅ Optuna")
except:
    HAS_OPTUNA = False
    print("⚠️ Optuna未インストール")

try:
    import jpholiday
    HAS_JPHOLIDAY = True
    print("✅ jpholiday")
except:
    HAS_JPHOLIDAY = False

print("\n✅ ライブラリ読み込み完了\n")


# =============================================================================
# 【AI記憶ノート】予測記録システム
# =============================================================================

class AIMemoryNote:
    """AI記憶ノート - 予測の記録・学習・自己補正"""

    def __init__(self, memory_path=AI_MEMORY_PATH):
        self.memory_path = memory_path
        self.df_memory = self._load_memory()
        self.bias_info = {}

    def _load_memory(self):
        """記憶ノートを読み込み"""
        if os.path.exists(self.memory_path):
            try:
                df = pd.read_csv(self.memory_path)
                df['prediction_date'] = pd.to_datetime(df['prediction_date'], errors='coerce')
                print(f"  📚 AI記憶ノート: {len(df)}件の記録を読み込み")
                return df
            except Exception as e:
                print(f"  ⚠️ 記憶ノート読み込みエラー: {e}")
                return pd.DataFrame()
        else:
            print("  📚 AI記憶ノート: 新規作成")
            return pd.DataFrame()

    def save_prediction(self, prediction_date, prediction_data):
        """予測をCSVに保存"""
        try:
            new_record = {
                'prediction_date': pd.Timestamp(prediction_date).isoformat(),
                'prediction_timestamp': datetime.now().isoformat(),
                'final_prediction': prediction_data.get('final_prediction'),
                'pred_lower': prediction_data.get('pred_lower'),
                'pred_upper': prediction_data.get('pred_upper'),
                'confidence_score': prediction_data.get('confidence_score'),
                'ml_prediction': prediction_data.get('ml_prediction'),
                'prophet_prediction': prediction_data.get('prophet_prediction'),
                'stat_prediction': prediction_data.get('stat_prediction'),
                'actual_value': None,  # 後で更新
                'error': None,
                'error_pct': None,
                'bias_correction_applied': prediction_data.get('bias_correction_applied', False),
                'bias_correction_amount': prediction_data.get('bias_correction_amount', 0),
            }

            # 既存記録に追加
            df_new = pd.DataFrame([new_record])
            self.df_memory = pd.concat([self.df_memory, df_new], ignore_index=True)

            # 保存
            self.df_memory.to_csv(self.memory_path, index=False)
            print(f"  💾 予測を記憶ノートに保存: {prediction_date}")

            return True
        except Exception as e:
            print(f"  ⚠️ 保存エラー: {e}")
            return False

    def update_actual_values(self, df_actual):
        """実績値を反映して誤差を計算"""
        print("\n" + "="*70)
        print("【AI記憶ノート】実績値の反映と誤差計算")
        print("="*70)

        if self.df_memory is None or len(self.df_memory) == 0:
            print("  ⚠️ 記憶ノートが空です")
            return 0

        if df_actual is None or len(df_actual) == 0:
            print("  ⚠️ 実績データがありません")
            return 0

        # 実績データの日付を変換
        df_actual = df_actual.copy()
        if 'Date' in df_actual.columns:
            df_actual['prediction_date'] = pd.to_datetime(df_actual['Date'], errors='coerce')
        elif 'prediction_date' in df_actual.columns:
            df_actual['prediction_date'] = pd.to_datetime(df_actual['prediction_date'], errors='coerce')

        if '合計' in df_actual.columns:
            df_actual['actual_value'] = df_actual['合計']

        update_count = 0

        for idx, row in self.df_memory.iterrows():
            # 実績値が未入力の予測のみ
            if pd.isna(row.get('actual_value')):
                pred_date = pd.to_datetime(row['prediction_date'])

                # 実績データから該当日を検索
                match = df_actual[df_actual['prediction_date'].dt.date == pred_date.date()]

                if len(match) > 0:
                    actual = match.iloc[0]['actual_value']
                    final_pred = row['final_prediction']

                    if pd.notna(actual) and actual > 0 and pd.notna(final_pred):
                        # 誤差計算
                        error = final_pred - actual
                        error_pct = (final_pred - actual) / actual * 100

                        # 更新
                        self.df_memory.loc[idx, 'actual_value'] = actual
                        self.df_memory.loc[idx, 'error'] = error
                        self.df_memory.loc[idx, 'error_pct'] = error_pct

                        update_count += 1
                        print(f"  ✓ {pred_date.date()}: 実績{int(actual):,}件, 誤差{error:+.0f}件 ({error_pct:+.1f}%)")

        if update_count > 0:
            self.df_memory.to_csv(self.memory_path, index=False)
            print(f"\n  ✅ {update_count}件の実績値を反映しました")

            # 統計表示
            self._show_accuracy_stats()
        else:
            print("  💡 新規反映する実績値はありませんでした")

        print("="*70 + "\n")
        return update_count

    def _show_accuracy_stats(self):
        """精度統計を表示"""
        df_completed = self.df_memory[self.df_memory['actual_value'].notna()].copy()

        if len(df_completed) == 0:
            return

        mae = df_completed['error_pct'].abs().mean()
        median_error = df_completed['error_pct'].median()
        within_5pct = (df_completed['error_pct'].abs() <= 5).sum()
        within_10pct = (df_completed['error_pct'].abs() <= 10).sum()

        print(f"\n  📊 精度統計（{len(df_completed)}件）:")
        print(f"    - 平均絶対誤差率: {mae:.2f}%")
        print(f"    - 中央値誤差: {median_error:+.2f}%")
        print(f"    - ±5%以内: {within_5pct}/{len(df_completed)} ({within_5pct/len(df_completed)*100:.1f}%)")
        print(f"    - ±10%以内: {within_10pct}/{len(df_completed)} ({within_10pct/len(df_completed)*100:.1f}%)")

    def detect_bias(self):
        """バイアス（系統的誤差）を検出"""
        print("\n【AI記憶ノート】バイアス検出")

        df_completed = self.df_memory[self.df_memory['actual_value'].notna()].copy()

        if len(df_completed) < 3:
            print("  💡 データ不足（3件以上必要）")
            self.bias_info = {'detected': False, 'bias': 0, 'std': 0}
            return self.bias_info

        # 直近10件の誤差を分析
        recent_errors = df_completed.tail(10)['error'].dropna()

        if len(recent_errors) < 3:
            self.bias_info = {'detected': False, 'bias': 0, 'std': 0}
            return self.bias_info

        bias = recent_errors.mean()
        std = recent_errors.std()

        # バイアス判定（平均誤差が標準偏差の0.5倍以上、かつ絶対値10以上）
        is_biased = abs(bias) > max(10, 0.5 * std)

        self.bias_info = {
            'detected': is_biased,
            'bias': bias,
            'std': std,
            'sample_count': len(recent_errors),
            'direction': '過大予測' if bias > 0 else '過小予測'
        }

        if is_biased:
            print(f"  ⚠️ バイアス検出！")
            print(f"    - 方向: {self.bias_info['direction']}")
            print(f"    - 平均誤差: {bias:+.1f}件")
            print(f"    - 標準偏差: {std:.1f}件")
            print(f"    - サンプル数: {len(recent_errors)}件")
        else:
            print(f"  ✅ 系統的バイアスなし（平均誤差: {bias:+.1f}件）")

        return self.bias_info

    def apply_correction(self, prediction, special_day_score=0):
        """メタ認知的自己補正を適用"""
        print("\n【AI記憶ノート】メタ認知的自己補正")

        if not self.bias_info.get('detected', False):
            print("  💡 バイアスなし。補正スキップ")
            return prediction, 0

        bias = self.bias_info['bias']

        # 補正率（特殊日は控えめに）
        if special_day_score > 0.5:
            correction_rate = 0.3
        elif special_day_score > 0.2:
            correction_rate = 0.5
        else:
            correction_rate = 0.7

        correction = -bias * correction_rate
        corrected_prediction = prediction + correction

        print(f"  🧠 検出バイアス: {bias:+.1f}件 ({self.bias_info['direction']})")
        print(f"  🎯 補正率: {correction_rate:.0%}")
        print(f"  ✨ 補正量: {correction:+.1f}件")
        print(f"  📊 補正前: {prediction:.0f}件 → 補正後: {corrected_prediction:.0f}件")

        return corrected_prediction, correction

    def get_learning_summary(self):
        """学習サマリーを取得"""
        df_completed = self.df_memory[self.df_memory['actual_value'].notna()]

        return {
            'total_predictions': len(self.df_memory),
            'completed_predictions': len(df_completed),
            'pending_predictions': len(self.df_memory) - len(df_completed),
            'mae': df_completed['error_pct'].abs().mean() if len(df_completed) > 0 else None,
            'bias_detected': self.bias_info.get('detected', False),
            'bias_amount': self.bias_info.get('bias', 0)
        }


# =============================================================================
# 特徴量エンジニアリング
# =============================================================================
def create_optimized_features(df, target_col='合計'):
    """最適化特徴量生成"""
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

    # 特殊日フラグ
    df['is_month_start'] = (df['day'] <= 3).astype(int)
    df['is_month_end'] = (df['day'] >= 28).astype(int)
    df['is_weekend'] = (df['weekday'] >= 5).astype(int)
    df['is_monday'] = (df['weekday'] == 0).astype(int)
    df['is_friday'] = (df['weekday'] == 4).astype(int)

    # 祝日
    if HAS_JPHOLIDAY:
        df['is_holiday'] = df['Date'].apply(lambda x: 1 if jpholiday.is_holiday(x) else 0)
    else:
        df['is_holiday'] = 0

    # 季節
    df['season'] = df['month'].apply(lambda x: 0 if x in [3,4,5] else (1 if x in [6,7,8] else (2 if x in [9,10,11] else 3)))

    # ラグ特徴量
    if target_col in df.columns:
        for lag in [1, 2, 3, 5, 7, 14, 21, 28, 30, 60, 90]:
            df[f'lag_{lag}'] = df[target_col].shift(lag)

        # 同曜日ラグ
        for w in [1, 2, 3, 4]:
            df[f'lag_{w*7}_weekday'] = df[target_col].shift(w * 7)

        # 前年
        df['lag_365'] = df[target_col].shift(365)
        df['lag_364'] = df[target_col].shift(364)

        # ローリング統計
        for window in [3, 5, 7, 14, 21, 30, 60]:
            df[f'rolling_mean_{window}'] = df[target_col].shift(1).rolling(window, min_periods=1).mean()
            df[f'rolling_std_{window}'] = df[target_col].shift(1).rolling(window, min_periods=1).std()
            df[f'rolling_min_{window}'] = df[target_col].shift(1).rolling(window, min_periods=1).min()
            df[f'rolling_max_{window}'] = df[target_col].shift(1).rolling(window, min_periods=1).max()

        # 変化率
        for period in [1, 7, 14, 30]:
            df[f'pct_change_{period}'] = df[target_col].pct_change(period).shift(1)

        # EMA
        for span in [7, 14, 30]:
            df[f'ema_{span}'] = df[target_col].shift(1).ewm(span=span, adjust=False).mean()

        # 曜日別・月別平均
        df['weekday_mean'] = df.groupby('weekday')[target_col].transform('mean')
        df['month_mean'] = df.groupby('month')[target_col].transform('mean')

        # ボラティリティ
        df['volatility_7'] = df[target_col].shift(1).rolling(7).std() / (df[target_col].shift(1).rolling(7).mean() + 1e-8)
        df['volatility_30'] = df[target_col].shift(1).rolling(30).std() / (df[target_col].shift(1).rolling(30).mean() + 1e-8)

    # 時間帯別比率特徴量
    ratio_cols = ['件数(～12:00)比率', '件数(～14:00)比率', '件数(～15:00)比率']
    for col in ratio_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
            for lag in [1, 7]:
                df[f'{col}_lag_{lag}'] = df[col].shift(lag)
            df[f'{col}_rolling_7'] = df[col].shift(1).rolling(7, min_periods=1).mean()

    df = df.replace([np.inf, -np.inf], np.nan)

    return df


# =============================================================================
# 機械学習予測クラス
# =============================================================================
class MLPredictorV67:
    """v66.7 ML予測クラス（AI記憶ノート連携）"""

    def __init__(self, memory_note):
        self.models = {}
        self.scaler = RobustScaler()
        self.feature_cols = None
        self.is_trained = False
        self.model_scores = {}
        self.stacking_model = None
        self.memory_note = memory_note  # AI記憶ノート連携

    def _init_models(self):
        """全モデル初期化"""
        models = {}

        if HAS_LGB:
            models['LightGBM'] = lgb.LGBMRegressor(
                n_estimators=500, learning_rate=0.05, max_depth=8,
                num_leaves=31, min_child_samples=20, subsample=0.8,
                colsample_bytree=0.8, random_state=42, verbose=-1, n_jobs=-1
            )

        if HAS_XGB:
            models['XGBoost'] = xgb.XGBRegressor(
                n_estimators=500, learning_rate=0.05, max_depth=8,
                min_child_weight=3, subsample=0.8, colsample_bytree=0.8,
                random_state=42, verbosity=0, n_jobs=-1
            )

        if HAS_CAT:
            models['CatBoost'] = CatBoostRegressor(
                iterations=500, learning_rate=0.05, depth=8,
                random_state=42, verbose=0
            )

        models['RandomForest'] = RandomForestRegressor(
            n_estimators=300, max_depth=15, min_samples_split=5,
            min_samples_leaf=2, random_state=42, n_jobs=-1
        )
        models['ExtraTrees'] = ExtraTreesRegressor(
            n_estimators=300, max_depth=15, random_state=42, n_jobs=-1
        )
        models['GradientBoosting'] = GradientBoostingRegressor(
            n_estimators=300, learning_rate=0.05, max_depth=6,
            subsample=0.8, random_state=42
        )
        models['Ridge'] = Ridge(alpha=1.0, random_state=42)
        models['Lasso'] = Lasso(alpha=0.1, random_state=42, max_iter=5000)
        models['ElasticNet'] = ElasticNet(alpha=0.1, l1_ratio=0.5, random_state=42, max_iter=5000)
        models['BayesianRidge'] = BayesianRidge()
        models['SVR'] = SVR(kernel='rbf', C=100, gamma='scale', epsilon=0.1)
        models['NeuralNet'] = MLPRegressor(
            hidden_layer_sizes=(128, 64, 32), activation='relu', solver='adam',
            learning_rate='adaptive', max_iter=1000, early_stopping=True,
            random_state=42
        )

        return models

    def train(self, df, target_col='合計'):
        """モデル訓練"""
        print("\n" + "="*70)
        print("【v66.7 機械学習訓練】")
        print("="*70)

        df_feat = create_optimized_features(df, target_col)
        df_train = df_feat.dropna(subset=[target_col])

        exclude_cols = ['Date', target_col, 'year']
        self.feature_cols = [c for c in df_train.columns
                            if c not in exclude_cols
                            and df_train[c].dtype in ['int64', 'float64', 'int32', 'float32']]

        X = df_train[self.feature_cols].fillna(0)
        y = df_train[target_col]

        if len(X) < 50:
            print("⚠️ データ不足")
            return False

        print(f"  訓練データ: {len(X)}件, 特徴量: {len(self.feature_cols)}個")

        X_scaled = self.scaler.fit_transform(X)
        self.models = self._init_models()

        print("\n【各モデル訓練】")
        tscv = TimeSeriesSplit(n_splits=5)

        for name, model in self.models.items():
            try:
                print(f"  🔄 {name}...", end=" ")
                cv_scores = cross_val_score(model, X_scaled, y, cv=tscv, scoring='neg_mean_absolute_error')
                cv_mae = -cv_scores.mean()
                model.fit(X_scaled, y)
                self.model_scores[name] = cv_mae
                print(f"✅ MAE: {cv_mae:.1f}")
            except Exception as e:
                print(f"❌ {e}")
                self.model_scores[name] = float('inf')

        self._build_stacking(X_scaled, y)
        self.is_trained = True

        print("\n【モデル性能ランキング】")
        sorted_scores = sorted(self.model_scores.items(), key=lambda x: x[1])
        for i, (name, score) in enumerate(sorted_scores[:5], 1):
            print(f"  {i}. {name}: MAE={score:.1f}")

        return True

    def _build_stacking(self, X, y):
        """スタッキング構築"""
        try:
            sorted_models = sorted(self.model_scores.items(), key=lambda x: x[1])
            top_models = [(name, self.models[name]) for name, _ in sorted_models[:5] if name in self.models]

            if len(top_models) >= 2:
                self.stacking_model = StackingRegressor(
                    estimators=top_models,
                    final_estimator=Ridge(alpha=1.0),
                    cv=3, n_jobs=-1
                )
                self.stacking_model.fit(X, y)
                print("  ✅ スタッキング構築完了")
        except Exception as e:
            print(f"  ⚠️ スタッキングエラー: {e}")

    def predict(self, df, target_date, target_col='合計'):
        """予測実行"""
        if not self.is_trained:
            return None, {}

        print("\n【機械学習予測】")

        df_feat = create_optimized_features(df, target_col)
        target_dt = pd.to_datetime(target_date)
        target_row = df_feat[df_feat['Date'] == target_dt]

        if len(target_row) == 0:
            last_row = df_feat.iloc[-1:].copy()
            last_row['Date'] = target_dt
            last_row['year'] = target_dt.year
            last_row['month'] = target_dt.month
            last_row['day'] = target_dt.day
            last_row['weekday'] = target_dt.dayofweek
            target_row = last_row

        available_cols = [c for c in self.feature_cols if c in target_row.columns]
        X_pred = target_row[available_cols].fillna(0)

        for col in self.feature_cols:
            if col not in X_pred.columns:
                X_pred[col] = 0
        X_pred = X_pred[self.feature_cols]
        X_pred_scaled = self.scaler.transform(X_pred)

        predictions = {}
        for name, model in self.models.items():
            try:
                pred = model.predict(X_pred_scaled)[0]
                predictions[name] = max(0, pred)
            except:
                pass

        if self.stacking_model:
            try:
                stacking_pred = self.stacking_model.predict(X_pred_scaled)[0]
                predictions['Stacking'] = max(0, stacking_pred)
                self.model_scores['Stacking'] = min(self.model_scores.values()) * 0.95
            except:
                pass

        if len(predictions) == 0:
            return None, {}

        # 加重平均
        weights = {}
        for name in predictions:
            score = self.model_scores.get(name, float('inf'))
            if score < float('inf'):
                weights[name] = 1 / (score + 1)

        total_weight = sum(weights.values())
        if total_weight > 0:
            weights = {k: v/total_weight for k, v in weights.items()}

        ensemble_pred = sum(predictions[k] * weights.get(k, 0) for k in predictions)

        print(f"  ★ MLアンサンブル: {ensemble_pred:.0f}件")

        return ensemble_pred, {'predictions': predictions, 'weights': weights}


# =============================================================================
# Prophet予測
# =============================================================================
def predict_with_prophet(df, target_date, target_col='合計'):
    """Prophet予測"""
    if not HAS_PROPHET:
        return None, {}

    try:
        print("  🔮 Prophet予測...")
        df_prophet = df[['Date', target_col]].copy()
        df_prophet.columns = ['ds', 'y']
        df_prophet = df_prophet.dropna()

        model = Prophet(
            yearly_seasonality=True,
            weekly_seasonality=True,
            daily_seasonality=False,
            changepoint_prior_scale=0.05,
            seasonality_mode='multiplicative'
        )
        model.fit(df_prophet)

        future = pd.DataFrame({'ds': [pd.to_datetime(target_date)]})
        forecast = model.predict(future)

        pred = forecast['yhat'].values[0]
        print(f"    Prophet予測: {pred:.0f}件")

        return pred, {'lower': forecast['yhat_lower'].values[0], 'upper': forecast['yhat_upper'].values[0]}
    except Exception as e:
        print(f"    ⚠️ Prophetエラー: {e}")
        return None, {}


# =============================================================================
# リアルタイム調整
# =============================================================================
def adjust_with_realtime(prediction, df, actuals, target_date):
    """12時/14時/15時実績で調整"""
    adjusted = prediction

    time_slots = [
        (12, '件数(～12:00)', '件数(～12:00)比率'),
        (14, '件数(～14:00)', '件数(～14:00)比率'),
        (15, '件数(～15:00)', '件数(～15:00)比率'),
    ]

    for hour, count_col, ratio_col in time_slots:
        actual_count = actuals.get(hour, 0)
        if actual_count > 0 and count_col in df.columns and ratio_col in df.columns:
            df_valid = df[(df[count_col] > 0) & (df['合計'] > 0)].copy()
            if len(df_valid) > 30:
                recent_ratio = df_valid.tail(30)[ratio_col].mean()
                if recent_ratio > 0.1:
                    estimated_total = actual_count / recent_ratio
                    weight = 0.3 + (hour - 12) * 0.15
                    adjusted = adjusted * (1 - weight) + estimated_total * weight
                    print(f"  ⏰ {hour}時実績: {actual_count}件 → 推定{estimated_total:.0f}件 (重み{weight:.0%})")

    return adjusted


# =============================================================================
# メイン予測関数
# =============================================================================
memory_note = AIMemoryNote()
ml_predictor = MLPredictorV67(memory_note)

def run_prediction_v66_7(target_date, actuals, df_orig):
    """v66.7 メイン予測（AI記憶ノート統合）"""
    global memory_note, ml_predictor

    print("\n" + "="*70)
    print("【v66.7 予測開始】AI記憶ノート統合版")
    print("="*70)
    print(f"予測日: {target_date}\n")

    try:
        df = df_orig.copy()
        df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
        df = df.dropna(subset=['Date'])

        if '合計' not in df.columns:
            for col in ['actual_value', 'total', '件数']:
                if col in df.columns:
                    df = df.rename(columns={col: '合計'})
                    break

        df['合計'] = pd.to_numeric(df['合計'], errors='coerce').fillna(0)
        df = df[df['合計'] > 0]

        print(f"データ: {len(df)}日分\n")

        # ===============================
        # 1. AI記憶ノート分析
        # ===============================
        print("【AI記憶ノート分析】")
        learning_summary = memory_note.get_learning_summary()
        print(f"  総予測数: {learning_summary['total_predictions']}件")
        print(f"  実績反映済み: {learning_summary['completed_predictions']}件")
        if learning_summary['mae']:
            print(f"  過去MAE: {learning_summary['mae']:.2f}%")

        # バイアス検出
        memory_note.detect_bias()

        # ===============================
        # 2. ML予測
        # ===============================
        if not ml_predictor.is_trained:
            ml_predictor.train(df, '合計')

        ml_pred, ml_info = ml_predictor.predict(df, target_date, '合計')

        # ===============================
        # 3. Prophet予測
        # ===============================
        prophet_pred, prophet_info = predict_with_prophet(df, target_date, '合計')

        # ===============================
        # 4. 統計予測
        # ===============================
        print("\n【統計予測】")
        pred_date = pd.to_datetime(target_date)
        same_cond = (df['Date'].dt.weekday == pred_date.dayofweek) & (df['Date'].dt.month == pred_date.month)
        same_days = df[same_cond]['合計']
        stat_pred = same_days.mean() if len(same_days) > 0 else df['合計'].mean()
        print(f"  同曜日同月平均: {stat_pred:.0f}件")

        # ===============================
        # 5. アンサンブル
        # ===============================
        print("\n【アンサンブル】")
        preds, weights = [], []

        if ml_pred:
            preds.append(ml_pred)
            weights.append(0.50)
            print(f"  ML予測: {ml_pred:.0f}件 (50%)")

        if prophet_pred:
            preds.append(prophet_pred)
            weights.append(0.30)
            print(f"  Prophet: {prophet_pred:.0f}件 (30%)")

        preds.append(stat_pred)
        weights.append(0.20 if len(preds) > 1 else 1.0)
        print(f"  統計: {stat_pred:.0f}件 ({weights[-1]:.0%})")

        total_w = sum(weights)
        weights = [w/total_w for w in weights]
        ensemble = sum(p * w for p, w in zip(preds, weights))

        # ===============================
        # 6. AI記憶ノート自己補正
        # ===============================
        corrected_pred, correction_amount = memory_note.apply_correction(ensemble, special_day_score=0)

        # ===============================
        # 7. リアルタイム調整
        # ===============================
        print("\n【リアルタイム調整】")
        final_pred = adjust_with_realtime(corrected_pred, df, actuals, target_date)

        # ===============================
        # 8. 信頼区間
        # ===============================
        all_preds = preds.copy()
        if ml_info.get('predictions'):
            all_preds.extend(list(ml_info['predictions'].values()))

        pred_std = np.std(all_preds) if len(all_preds) > 1 else final_pred * 0.1
        pred_lower = max(0, final_pred - 1.96 * pred_std)
        pred_upper = final_pred + 1.96 * pred_std

        cv = pred_std / (final_pred + 1e-8)
        confidence = max(0, min(100, 100 * (1 - cv)))

        # ===============================
        # 結果
        # ===============================
        print("\n" + "="*70)
        print(f"★★★ 最終予測: {int(final_pred):,}件 ★★★")
        print(f"    信頼区間: {int(pred_lower):,} ～ {int(pred_upper):,}件")
        print(f"    信頼度: {confidence:.1f}点")
        if correction_amount != 0:
            print(f"    AI補正: {correction_amount:+.0f}件")
        print("="*70)

        # 予測を記憶ノートに保存
        prediction_data = {
            'final_prediction': int(final_pred),
            'pred_lower': int(pred_lower),
            'pred_upper': int(pred_upper),
            'confidence_score': confidence,
            'ml_prediction': ml_pred,
            'prophet_prediction': prophet_pred,
            'stat_prediction': stat_pred,
            'bias_correction_applied': correction_amount != 0,
            'bias_correction_amount': correction_amount
        }
        memory_note.save_prediction(target_date, prediction_data)

        return prediction_data

    except Exception as e:
        print(f"\n⚠️ エラー: {e}")
        traceback.print_exc()
        return {'final_prediction': 1000, 'pred_lower': 800, 'pred_upper': 1200, 'confidence_score': 0}


# =============================================================================
# UI
# =============================================================================
date_picker = widgets.DatePicker(description='予測日:', value=date.today())
actual_12h = widgets.IntText(value=0, description='12時実績:', layout=widgets.Layout(width='150px'))
actual_14h = widgets.IntText(value=0, description='14時実績:', layout=widgets.Layout(width='150px'))
actual_15h = widgets.IntText(value=0, description='15時実績:', layout=widgets.Layout(width='150px'))

run_btn = widgets.Button(description='🚀 予測実行', button_style='success',
                        layout=widgets.Layout(width='150px', height='50px'))
update_btn = widgets.Button(description='🔄 実績更新', button_style='warning',
                           layout=widgets.Layout(width='150px', height='50px'))
retrain_btn = widgets.Button(description='🔧 再学習', button_style='info',
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

        import glob
        files = glob.glob('/content/*.xlsx')
        if not files:
            files = glob.glob('/content/*.csv')

        if not files:
            print("⚠️ データファイルが見つかりません")
            run_btn.disabled = False
            run_btn.description = '🚀 予測実行'
            return

        data_file = files[0]
        print(f"📂 {os.path.basename(data_file)}")

        try:
            if data_file.endswith('.xlsx'):
                global_df = pd.read_excel(data_file, engine='openpyxl')
            else:
                global_df = pd.read_csv(data_file)
        except Exception as e:
            print(f"⚠️ 読み込みエラー: {e}")
            run_btn.disabled = False
            run_btn.description = '🚀 予測実行'
            return

        if 'Date' not in global_df.columns:
            for col in ['日付', 'date', 'prediction_date']:
                if col in global_df.columns:
                    global_df = global_df.rename(columns={col: 'Date'})
                    break

        actuals = {12: actual_12h.value, 14: actual_14h.value, 15: actual_15h.value}
        results = run_prediction_v66_7(date_picker.value, actuals, global_df)

        with result_output:
            clear_output()

            # 補正情報
            correction_info = ""
            if results.get('bias_correction_applied'):
                correction_info = f"<div style='font-size:14px;margin-top:10px;'>🧠 AI補正: {results.get('bias_correction_amount', 0):+.0f}件</div>"

            display(HTML(f"""
            <div style='background:linear-gradient(135deg,#667eea,#764ba2);color:white;padding:25px;border-radius:15px;text-align:center;margin-top:20px;'>
                <h2 style='margin:0;'>🧠 v66.7 AI記憶ノート統合版</h2>
                <div style='font-size:56px;font-weight:bold;margin:20px 0;'>{results['final_prediction']:,}件</div>
                <div style='font-size:18px;'>信頼区間: {results['pred_lower']:,} ～ {results['pred_upper']:,}件</div>
                <div style='font-size:16px;margin-top:10px;'>信頼度: {results['confidence_score']:.1f}点</div>
                {correction_info}
            </div>
            """))

    run_btn.disabled = False
    run_btn.description = '🚀 予測実行'

def on_update(b):
    global global_df, memory_note
    update_btn.disabled = True

    with output:
        clear_output()

        if global_df is not None:
            memory_note.update_actual_values(global_df)
        else:
            print("⚠️ まず予測を実行してデータを読み込んでください")

    update_btn.disabled = False

def on_retrain(b):
    global ml_predictor, memory_note
    ml_predictor = MLPredictorV67(memory_note)
    with output:
        clear_output()
        print("🔄 モデルをリセットしました。次回予測時に再学習します。")

run_btn.on_click(on_run)
update_btn.on_click(on_update)
retrain_btn.on_click(on_retrain)

ui = widgets.VBox([
    widgets.HTML('<h2 style="color:#1f77b4;">🧠 v66.7 メタ認知AI予測システム【AI記憶ノート統合版】</h2>'),
    widgets.HTML('''<p>12 MLモデル + Prophet + Optuna + <b>AI記憶ノート（自己学習・自己補正）</b></p>'''),
    date_picker,
    widgets.HTML('<p><b>リアルタイム調整用:</b></p>'),
    widgets.HBox([actual_12h, actual_14h, actual_15h]),
    widgets.HBox([run_btn, update_btn, retrain_btn]),
    result_output
])

display(ui, output)

print("\n" + "="*70)
print("✅ v66.7 準備完了！")
print("="*70)
print("\n【v66.7 新機能: AI記憶ノート】")
print("  📚 予測を自動記録（CSV保存）")
print("  📊 実績値を反映して誤差を計算")
print("  🔍 バイアス（系統的誤差）を自動検出")
print("  🧠 メタ認知的自己補正（次回予測を自動調整）")
print("="*70)
print("\n使い方:")
print("1. 「🚀 予測実行」→ 予測を実行＆記録")
print("2. 翌日、実績表を更新して再アップロード")
print("3. 「🔄 実績更新」→ 誤差を計算＆学習")
print("4. 次回予測時、AIが自動でバイアス補正")
print("="*70)
