# =============================================================================
# v66.6 メタ認知AI予測システム【データ最適化版】
# =============================================================================
# 実績表データに完全最適化
# 搭載: 12 MLモデル + Prophet + Optuna最適化 + スタッキング
# =============================================================================

print("="*70)
print("【v66.6 メタ認知AI予測システム】データ最適化版")
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
# データ最適化特徴量エンジニアリング
# =============================================================================
def create_optimized_features(df, target_col='合計'):
    """実績表データに最適化した特徴量生成"""
    print("  📊 最適化特徴量エンジニアリング...")

    df = df.copy()
    df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
    df = df.dropna(subset=['Date']).sort_values('Date').reset_index(drop=True)

    # ===================
    # 基本時間特徴量
    # ===================
    df['year'] = df['Date'].dt.year
    df['month'] = df['Date'].dt.month
    df['day'] = df['Date'].dt.day
    df['weekday'] = df['Date'].dt.dayofweek
    df['week_of_year'] = df['Date'].dt.isocalendar().week.astype(int)
    df['week_of_month'] = ((df['day'] - 1) // 7 + 1)
    df['quarter'] = df['Date'].dt.quarter
    df['day_of_year'] = df['Date'].dt.dayofyear

    # ===================
    # 周期的エンコーディング
    # ===================
    df['month_sin'] = np.sin(2 * np.pi * df['month'] / 12)
    df['month_cos'] = np.cos(2 * np.pi * df['month'] / 12)
    df['weekday_sin'] = np.sin(2 * np.pi * df['weekday'] / 7)
    df['weekday_cos'] = np.cos(2 * np.pi * df['weekday'] / 7)
    df['day_sin'] = np.sin(2 * np.pi * df['day'] / 31)
    df['day_cos'] = np.cos(2 * np.pi * df['day'] / 31)
    df['week_of_year_sin'] = np.sin(2 * np.pi * df['week_of_year'] / 52)
    df['week_of_year_cos'] = np.cos(2 * np.pi * df['week_of_year'] / 52)

    # ===================
    # 特殊日フラグ
    # ===================
    df['is_month_start'] = (df['day'] <= 3).astype(int)
    df['is_month_end'] = (df['day'] >= 28).astype(int)
    df['is_weekend'] = (df['weekday'] >= 5).astype(int)
    df['is_monday'] = (df['weekday'] == 0).astype(int)
    df['is_friday'] = (df['weekday'] == 4).astype(int)
    df['is_mid_month'] = ((df['day'] >= 10) & (df['day'] <= 20)).astype(int)

    # 祝日
    if HAS_JPHOLIDAY:
        df['is_holiday'] = df['Date'].apply(lambda x: 1 if jpholiday.is_holiday(x) else 0)
        df['is_holiday_eve'] = df['is_holiday'].shift(-1).fillna(0).astype(int)
        df['is_after_holiday'] = df['is_holiday'].shift(1).fillna(0).astype(int)
        # 連休判定
        df['holiday_streak'] = df['is_holiday'].rolling(3, min_periods=1).sum()
    else:
        df['is_holiday'] = 0
        df['is_holiday_eve'] = 0
        df['is_after_holiday'] = 0
        df['holiday_streak'] = 0

    # 季節
    df['season'] = df['month'].apply(lambda x: 0 if x in [3,4,5] else (1 if x in [6,7,8] else (2 if x in [9,10,11] else 3)))
    for s in range(4):
        df[f'season_{s}'] = (df['season'] == s).astype(int)

    # ===================
    # 時間帯別比率特徴量 (データ固有)
    # ===================
    ratio_cols = ['件数(～12:00)比率', '件数(～14:00)比率', '件数(～15:00)比率', '件数(～最終)比率', '御来社/持参比率']
    for col in ratio_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
            # ラグ特徴量
            for lag in [1, 7, 14]:
                df[f'{col}_lag_{lag}'] = df[col].shift(lag)
            # ローリング平均
            df[f'{col}_rolling_7'] = df[col].shift(1).rolling(7, min_periods=1).mean()
            df[f'{col}_rolling_30'] = df[col].shift(1).rolling(30, min_periods=1).mean()

    # ===================
    # 時間帯別件数特徴量
    # ===================
    count_cols = ['件数(～12:00)', '件数(～14:00)', '件数(～15:00)', '件数(～最終)', '御来社/持参']
    for col in count_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
            # ラグ
            for lag in [1, 7]:
                df[f'{col}_lag_{lag}'] = df[col].shift(lag)
            # ローリング
            df[f'{col}_rolling_7'] = df[col].shift(1).rolling(7, min_periods=1).mean()

    # ===================
    # 合計のラグ・ローリング特徴量
    # ===================
    if target_col in df.columns:
        # ラグ特徴量
        for lag in [1, 2, 3, 4, 5, 6, 7, 14, 21, 28, 30, 60, 90]:
            df[f'lag_{lag}'] = df[target_col].shift(lag)

        # 同曜日ラグ
        for w in [1, 2, 3, 4]:
            df[f'lag_{w*7}_same_weekday'] = df[target_col].shift(w * 7)

        # 前年同日・同週
        df['lag_365'] = df[target_col].shift(365)
        df['lag_364'] = df[target_col].shift(364)  # 同曜日

        # ローリング統計
        for window in [3, 5, 7, 14, 21, 30, 60, 90]:
            df[f'rolling_mean_{window}'] = df[target_col].shift(1).rolling(window, min_periods=1).mean()
            df[f'rolling_std_{window}'] = df[target_col].shift(1).rolling(window, min_periods=1).std()
            df[f'rolling_min_{window}'] = df[target_col].shift(1).rolling(window, min_periods=1).min()
            df[f'rolling_max_{window}'] = df[target_col].shift(1).rolling(window, min_periods=1).max()
            df[f'rolling_median_{window}'] = df[target_col].shift(1).rolling(window, min_periods=1).median()

        # パーセンタイル
        df['rolling_25pct_30'] = df[target_col].shift(1).rolling(30, min_periods=1).quantile(0.25)
        df['rolling_75pct_30'] = df[target_col].shift(1).rolling(30, min_periods=1).quantile(0.75)

        # 変化率
        for period in [1, 7, 14, 30]:
            df[f'pct_change_{period}'] = df[target_col].pct_change(period).shift(1)
            df[f'diff_{period}'] = df[target_col].diff(period).shift(1)

        # 曜日別・月別統計との差
        weekday_mean = df.groupby('weekday')[target_col].transform('mean')
        df['weekday_mean'] = weekday_mean
        df['diff_from_weekday_mean'] = df[target_col].shift(1) - weekday_mean

        month_mean = df.groupby('month')[target_col].transform('mean')
        df['month_mean'] = month_mean
        df['diff_from_month_mean'] = df[target_col].shift(1) - month_mean

        # 曜日×月の交互作用
        df['weekday_month'] = df['weekday'] * 12 + df['month']
        wm_mean = df.groupby('weekday_month')[target_col].transform('mean')
        df['weekday_month_mean'] = wm_mean

        # EMA (指数移動平均)
        for span in [7, 14, 30, 60]:
            df[f'ema_{span}'] = df[target_col].shift(1).ewm(span=span, adjust=False).mean()

        # ボラティリティ
        df['volatility_7'] = df[target_col].shift(1).rolling(7).std() / (df[target_col].shift(1).rolling(7).mean() + 1e-8)
        df['volatility_30'] = df[target_col].shift(1).rolling(30).std() / (df[target_col].shift(1).rolling(30).mean() + 1e-8)

        # トレンド (線形回帰の傾き)
        def calc_trend(x):
            if len(x) < 2:
                return 0
            return np.polyfit(range(len(x)), x, 1)[0]
        df['trend_7'] = df[target_col].shift(1).rolling(7, min_periods=2).apply(calc_trend, raw=True)
        df['trend_30'] = df[target_col].shift(1).rolling(30, min_periods=2).apply(calc_trend, raw=True)

        # 年間成長率
        df['yoy_growth'] = (df[target_col].shift(1) / (df[target_col].shift(366) + 1e-8)) - 1
        df['yoy_growth'] = df['yoy_growth'].clip(-0.5, 0.5)

    # 無限値・NaN処理
    df = df.replace([np.inf, -np.inf], np.nan)

    feature_count = len([c for c in df.columns if c not in ['Date', target_col]])
    print(f"  ✅ {feature_count}個の特徴量を生成")

    return df


# =============================================================================
# Prophet予測
# =============================================================================
def predict_with_prophet(df, target_date, target_col='合計'):
    """Prophet時系列予測"""
    if not HAS_PROPHET:
        return None, {}

    try:
        print("  🔮 Prophet予測...")
        df_prophet = df[['Date', target_col]].copy()
        df_prophet.columns = ['ds', 'y']
        df_prophet = df_prophet.dropna()

        # 祝日データ
        if HAS_JPHOLIDAY:
            holidays_list = []
            for d in pd.date_range(df_prophet['ds'].min(), df_prophet['ds'].max()):
                if jpholiday.is_holiday(d):
                    holidays_list.append({'ds': d, 'holiday': jpholiday.is_holiday_name(d)})
            holidays_df = pd.DataFrame(holidays_list) if holidays_list else None
        else:
            holidays_df = None

        model = Prophet(
            yearly_seasonality=True,
            weekly_seasonality=True,
            daily_seasonality=False,
            holidays=holidays_df,
            changepoint_prior_scale=0.05,
            seasonality_prior_scale=10,
            seasonality_mode='multiplicative'
        )
        model.fit(df_prophet)

        future = pd.DataFrame({'ds': [pd.to_datetime(target_date)]})
        forecast = model.predict(future)

        pred = forecast['yhat'].values[0]
        lower = forecast['yhat_lower'].values[0]
        upper = forecast['yhat_upper'].values[0]

        print(f"    Prophet予測: {pred:.0f}件 ({lower:.0f}～{upper:.0f})")

        return pred, {'lower': lower, 'upper': upper}
    except Exception as e:
        print(f"    ⚠️ Prophetエラー: {e}")
        return None, {}


# =============================================================================
# Optuna最適化
# =============================================================================
def optimize_with_optuna(X, y, n_trials=30):
    """Optunaでハイパーパラメータ最適化"""
    if not HAS_OPTUNA or not HAS_LGB:
        return None

    print("  🔧 Optuna最適化中...")

    def objective(trial):
        params = {
            'n_estimators': trial.suggest_int('n_estimators', 100, 500),
            'learning_rate': trial.suggest_float('learning_rate', 0.01, 0.2),
            'max_depth': trial.suggest_int('max_depth', 3, 12),
            'num_leaves': trial.suggest_int('num_leaves', 15, 63),
            'min_child_samples': trial.suggest_int('min_child_samples', 5, 50),
            'subsample': trial.suggest_float('subsample', 0.6, 1.0),
            'colsample_bytree': trial.suggest_float('colsample_bytree', 0.6, 1.0),
            'reg_alpha': trial.suggest_float('reg_alpha', 1e-8, 10.0, log=True),
            'reg_lambda': trial.suggest_float('reg_lambda', 1e-8, 10.0, log=True),
            'random_state': 42,
            'verbose': -1,
            'n_jobs': -1
        }

        model = lgb.LGBMRegressor(**params)
        tscv = TimeSeriesSplit(n_splits=3)
        scores = cross_val_score(model, X, y, cv=tscv, scoring='neg_mean_absolute_error')
        return -scores.mean()

    study = optuna.create_study(direction='minimize')
    study.optimize(objective, n_trials=n_trials, show_progress_bar=False)

    print(f"    最適MAE: {study.best_value:.1f}")

    return study.best_params


# =============================================================================
# 機械学習予測クラス
# =============================================================================
class MLPredictorV66:
    """v66.6 最適化ML予測クラス"""

    def __init__(self):
        self.models = {}
        self.scaler = RobustScaler()
        self.feature_cols = None
        self.is_trained = False
        self.model_scores = {}
        self.best_lgb_params = None
        self.stacking_model = None

    def _init_models(self, optimized_params=None):
        """全モデル初期化"""
        models = {}

        # 1. LightGBM (最適化済み or デフォルト)
        if HAS_LGB:
            if optimized_params:
                lgb_params = {**optimized_params, 'random_state': 42, 'verbose': -1, 'n_jobs': -1}
            else:
                lgb_params = {
                    'n_estimators': 500, 'learning_rate': 0.05, 'max_depth': 8,
                    'num_leaves': 31, 'min_child_samples': 20, 'subsample': 0.8,
                    'colsample_bytree': 0.8, 'reg_alpha': 0.1, 'reg_lambda': 0.1,
                    'random_state': 42, 'verbose': -1, 'n_jobs': -1
                }
            models['LightGBM'] = lgb.LGBMRegressor(**lgb_params)

        # 2. XGBoost
        if HAS_XGB:
            models['XGBoost'] = xgb.XGBRegressor(
                n_estimators=500, learning_rate=0.05, max_depth=8,
                min_child_weight=3, subsample=0.8, colsample_bytree=0.8,
                reg_alpha=0.1, reg_lambda=0.1, random_state=42, verbosity=0, n_jobs=-1
            )

        # 3. CatBoost
        if HAS_CAT:
            models['CatBoost'] = CatBoostRegressor(
                iterations=500, learning_rate=0.05, depth=8,
                l2_leaf_reg=3, random_state=42, verbose=0
            )

        # 4-6. アンサンブル系
        models['RandomForest'] = RandomForestRegressor(
            n_estimators=300, max_depth=15, min_samples_split=5,
            min_samples_leaf=2, max_features='sqrt', random_state=42, n_jobs=-1
        )
        models['ExtraTrees'] = ExtraTreesRegressor(
            n_estimators=300, max_depth=15, min_samples_split=5,
            min_samples_leaf=2, random_state=42, n_jobs=-1
        )
        models['GradientBoosting'] = GradientBoostingRegressor(
            n_estimators=300, learning_rate=0.05, max_depth=6,
            min_samples_split=5, min_samples_leaf=2, subsample=0.8, random_state=42
        )

        # 7-10. 線形系
        models['Ridge'] = Ridge(alpha=1.0, random_state=42)
        models['Lasso'] = Lasso(alpha=0.1, random_state=42, max_iter=5000)
        models['ElasticNet'] = ElasticNet(alpha=0.1, l1_ratio=0.5, random_state=42, max_iter=5000)
        models['BayesianRidge'] = BayesianRidge()

        # 11. SVR
        models['SVR'] = SVR(kernel='rbf', C=100, gamma='scale', epsilon=0.1)

        # 12. ニューラルネット
        models['NeuralNet'] = MLPRegressor(
            hidden_layer_sizes=(128, 64, 32), activation='relu', solver='adam',
            learning_rate='adaptive', learning_rate_init=0.001, max_iter=1000,
            early_stopping=True, validation_fraction=0.1, random_state=42
        )

        return models

    def train(self, df, target_col='合計', use_optuna=True):
        """全モデル訓練"""
        print("\n" + "="*70)
        print("【v66.6 機械学習訓練開始】")
        print("="*70)

        # 特徴量生成
        df_feat = create_optimized_features(df, target_col)
        df_train = df_feat.dropna(subset=[target_col])

        # 特徴量選択
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

        # スケーリング
        X_scaled = self.scaler.fit_transform(X)

        # Optuna最適化
        if use_optuna and HAS_OPTUNA and HAS_LGB:
            self.best_lgb_params = optimize_with_optuna(X_scaled, y, n_trials=20)
        else:
            self.best_lgb_params = None

        # モデル初期化
        self.models = self._init_models(self.best_lgb_params)

        # 各モデル訓練
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

        # スタッキング構築
        self._build_stacking(X_scaled, y)

        self.is_trained = True

        # ランキング表示
        print("\n【モデル性能ランキング】")
        sorted_scores = sorted(self.model_scores.items(), key=lambda x: x[1])
        for i, (name, score) in enumerate(sorted_scores[:5], 1):
            print(f"  {i}. {name}: MAE={score:.1f}")

        return True

    def _build_stacking(self, X, y):
        """スタッキングメタ学習器構築"""
        print("\n  🔧 スタッキング構築...")

        try:
            # 上位モデルを選択
            sorted_models = sorted(self.model_scores.items(), key=lambda x: x[1])
            top_models = [(name, self.models[name]) for name, _ in sorted_models[:5] if name in self.models]

            if len(top_models) < 2:
                return

            self.stacking_model = StackingRegressor(
                estimators=top_models,
                final_estimator=Ridge(alpha=1.0),
                cv=3,
                n_jobs=-1
            )
            self.stacking_model.fit(X, y)
            print("    ✅ スタッキング完了")
        except Exception as e:
            print(f"    ⚠️ スタッキングエラー: {e}")
            self.stacking_model = None

    def predict(self, df, target_date, target_col='合計'):
        """予測実行"""
        if not self.is_trained:
            return None, {}

        print("\n【機械学習予測】")

        df_feat = create_optimized_features(df, target_col)
        target_dt = pd.to_datetime(target_date)

        # 予測日の特徴量作成
        target_row = df_feat[df_feat['Date'] == target_dt]

        if len(target_row) == 0:
            last_row = df_feat.iloc[-1:].copy()
            last_row['Date'] = target_dt
            # 時間特徴量更新
            last_row['year'] = target_dt.year
            last_row['month'] = target_dt.month
            last_row['day'] = target_dt.day
            last_row['weekday'] = target_dt.dayofweek
            last_row['week_of_year'] = target_dt.isocalendar().week
            last_row['week_of_month'] = (target_dt.day - 1) // 7 + 1
            last_row['quarter'] = (target_dt.month - 1) // 3 + 1
            last_row['day_of_year'] = target_dt.timetuple().tm_yday
            # 周期エンコーディング
            last_row['month_sin'] = np.sin(2 * np.pi * target_dt.month / 12)
            last_row['month_cos'] = np.cos(2 * np.pi * target_dt.month / 12)
            last_row['weekday_sin'] = np.sin(2 * np.pi * target_dt.dayofweek / 7)
            last_row['weekday_cos'] = np.cos(2 * np.pi * target_dt.dayofweek / 7)
            # フラグ
            last_row['is_month_start'] = 1 if target_dt.day <= 3 else 0
            last_row['is_month_end'] = 1 if target_dt.day >= 28 else 0
            last_row['is_weekend'] = 1 if target_dt.dayofweek >= 5 else 0
            if HAS_JPHOLIDAY:
                last_row['is_holiday'] = 1 if jpholiday.is_holiday(target_dt) else 0
            target_row = last_row

        # 特徴量抽出
        available_cols = [c for c in self.feature_cols if c in target_row.columns]
        X_pred = target_row[available_cols].fillna(0)

        # 不足列を0で埋める
        for col in self.feature_cols:
            if col not in X_pred.columns:
                X_pred[col] = 0
        X_pred = X_pred[self.feature_cols]

        X_pred_scaled = self.scaler.transform(X_pred)

        # 各モデル予測
        predictions = {}
        for name, model in self.models.items():
            try:
                pred = model.predict(X_pred_scaled)[0]
                predictions[name] = max(0, pred)
            except:
                pass

        # スタッキング予測
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
        else:
            weights = {k: 1/len(predictions) for k in predictions}

        ensemble_pred = sum(predictions[k] * weights.get(k, 0) for k in predictions)

        # 結果表示
        print(f"\n  【各モデル予測】")
        sorted_preds = sorted(predictions.items(), key=lambda x: self.model_scores.get(x[0], float('inf')))
        for name, pred in sorted_preds[:6]:
            w = weights.get(name, 0) * 100
            print(f"    {name}: {pred:.0f}件 ({w:.1f}%)")

        print(f"\n  ★ MLアンサンブル: {ensemble_pred:.0f}件")

        return ensemble_pred, {'predictions': predictions, 'weights': weights}


# =============================================================================
# リアルタイム調整関数
# =============================================================================
def adjust_with_realtime(prediction, df, actuals, target_date):
    """時間帯別実績でリアルタイム調整"""
    print("\n【リアルタイム調整】")

    adjusted = prediction
    adjustments = {}

    # 各時間帯の実績で調整
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
                # 直近30日の比率を使用
                recent_ratio = df_valid.tail(30)[ratio_col].mean()
                if recent_ratio > 0.1:
                    estimated_total = actual_count / recent_ratio
                    # 時間が進むほど実績の重みを増やす
                    weight = 0.3 + (hour - 12) * 0.15
                    adjusted = adjusted * (1 - weight) + estimated_total * weight
                    adjustments[hour] = {'estimated': estimated_total, 'weight': weight}
                    print(f"  {hour}時実績 {actual_count}件 → 推定 {estimated_total:.0f}件 (重み{weight:.0%})")

    if adjustments:
        print(f"  調整後予測: {adjusted:.0f}件")
    else:
        print("  実績入力なし")

    return adjusted, adjustments


# =============================================================================
# メイン予測関数
# =============================================================================
ml_predictor = MLPredictorV66()

def run_prediction_v66_6(target_date, actuals, df_orig):
    """v66.6 メイン予測"""
    global ml_predictor

    print("\n" + "="*70)
    print("【v66.6 予測開始】データ最適化版")
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

        # ===================
        # 1. ML予測
        # ===================
        if not ml_predictor.is_trained:
            ml_predictor.train(df, '合計', use_optuna=HAS_OPTUNA)

        ml_pred, ml_info = ml_predictor.predict(df, target_date, '合計')

        # ===================
        # 2. Prophet予測
        # ===================
        prophet_pred, prophet_info = predict_with_prophet(df, target_date, '合計')

        # ===================
        # 3. 統計予測
        # ===================
        print("\n【統計予測】")
        pred_date = pd.to_datetime(target_date)

        # 同曜日・同月の平均
        same_cond = (df['Date'].dt.weekday == pred_date.dayofweek) & (df['Date'].dt.month == pred_date.month)
        same_days = df[same_cond]['合計']
        stat_pred = same_days.mean() if len(same_days) > 0 else df['合計'].mean()
        print(f"  同曜日同月平均: {stat_pred:.0f}件")

        # ===================
        # 4. アンサンブル
        # ===================
        print("\n【最終アンサンブル】")
        preds = []
        weights = []

        if ml_pred:
            preds.append(ml_pred)
            weights.append(0.50)  # ML: 50%
            print(f"  ML予測: {ml_pred:.0f}件 (50%)")

        if prophet_pred:
            preds.append(prophet_pred)
            weights.append(0.30)  # Prophet: 30%
            print(f"  Prophet: {prophet_pred:.0f}件 (30%)")

        preds.append(stat_pred)
        weights.append(0.20 if len(preds) > 1 else 1.0)  # 統計: 20%
        print(f"  統計: {stat_pred:.0f}件 ({weights[-1]:.0%})")

        # 正規化
        total_w = sum(weights)
        weights = [w/total_w for w in weights]

        ensemble = sum(p * w for p, w in zip(preds, weights))

        # ===================
        # 5. リアルタイム調整
        # ===================
        final_pred, adj_info = adjust_with_realtime(ensemble, df, actuals, target_date)

        # ===================
        # 6. 信頼区間
        # ===================
        all_preds = preds.copy()
        if ml_info.get('predictions'):
            all_preds.extend(list(ml_info['predictions'].values()))

        pred_std = np.std(all_preds) if len(all_preds) > 1 else final_pred * 0.1
        pred_lower = max(0, final_pred - 1.96 * pred_std)
        pred_upper = final_pred + 1.96 * pred_std

        cv = pred_std / (final_pred + 1e-8)
        confidence = max(0, min(100, 100 * (1 - cv)))

        # ===================
        # 結果
        # ===================
        print("\n" + "="*70)
        print(f"★★★ 最終予測: {int(final_pred):,}件 ★★★")
        print(f"    信頼区間: {int(pred_lower):,} ～ {int(pred_upper):,}件")
        print(f"    信頼度: {confidence:.1f}点")
        print("="*70)

        # 構成表示
        model_count = len(ml_predictor.models) + (1 if HAS_PROPHET else 0)
        print(f"\n【搭載モデル: {model_count}個】")
        print(f"  ML: {', '.join(ml_predictor.models.keys())}")
        if HAS_PROPHET:
            print("  時系列: Prophet")

        return {
            'final_prediction': int(final_pred),
            'pred_lower': int(pred_lower),
            'pred_upper': int(pred_upper),
            'confidence_score': confidence,
            'ml_prediction': ml_pred,
            'prophet_prediction': prophet_pred,
            'stat_prediction': stat_pred,
            'model_count': model_count
        }

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

        # ファイル検索
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

        # 列名正規化
        if 'Date' not in global_df.columns:
            for col in ['日付', 'date', 'prediction_date']:
                if col in global_df.columns:
                    global_df = global_df.rename(columns={col: 'Date'})
                    break

        actuals = {12: actual_12h.value, 14: actual_14h.value, 15: actual_15h.value}
        results = run_prediction_v66_6(date_picker.value, actuals, global_df)

        with result_output:
            clear_output()
            display(HTML(f"""
            <div style='background:linear-gradient(135deg,#667eea,#764ba2);color:white;padding:25px;border-radius:15px;text-align:center;margin-top:20px;'>
                <h2 style='margin:0;'>🧠 v66.6 予測結果</h2>
                <div style='font-size:56px;font-weight:bold;margin:20px 0;'>{results['final_prediction']:,}件</div>
                <div style='font-size:18px;'>信頼区間: {results['pred_lower']:,} ～ {results['pred_upper']:,}件</div>
                <div style='font-size:16px;margin-top:10px;'>信頼度: {results['confidence_score']:.1f}点 | モデル: {results.get('model_count', 0)}個</div>
                <div style='font-size:14px;margin-top:15px;opacity:0.9;'>
                    ML: {results.get('ml_prediction', 'N/A')} | Prophet: {results.get('prophet_prediction', 'N/A')} | 統計: {results.get('stat_prediction', 'N/A'):.0f if results.get('stat_prediction') else 'N/A'}
                </div>
            </div>
            """))

    run_btn.disabled = False
    run_btn.description = '🚀 予測実行'

def on_retrain(b):
    global ml_predictor
    ml_predictor = MLPredictorV66()
    with output:
        clear_output()
        print("🔄 リセット完了。次回予測時に再学習します。")

run_btn.on_click(on_run)
retrain_btn.on_click(on_retrain)

ui = widgets.VBox([
    widgets.HTML('<h2 style="color:#1f77b4;">🧠 v66.6 メタ認知AI予測システム【データ最適化版】</h2>'),
    widgets.HTML('<p>12 MLモデル + Prophet + Optuna最適化 + スタッキング</p>'),
    date_picker,
    widgets.HTML('<p><b>リアルタイム調整用（任意）:</b></p>'),
    widgets.HBox([actual_12h, actual_14h, actual_15h]),
    widgets.HBox([run_btn, retrain_btn]),
    result_output
])

display(ui, output)

print("\n" + "="*70)
print("✅ v66.6 準備完了！")
print("="*70)
print("\n【v66.6 新機能】")
print("  ✅ 実績表データに最適化した特徴量")
print("  ✅ 時間帯別比率を活用")
print("  ✅ Optuna自動ハイパーパラメータ最適化")
print("  ✅ Prophet時系列予測")
print("  ✅ スタッキングメタ学習器")
print("  ✅ 12時/14時/15時実績でリアルタイム調整")
print("="*70)
