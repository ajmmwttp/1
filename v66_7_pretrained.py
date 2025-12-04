# =============================================================================
# v66.7 メタ認知AI予測システム【2年分学習済み版】
# =============================================================================
# バックテストで2年分の予測履歴を学習済み
# =============================================================================

print("="*70)
print("【v66.7 メタ認知AI予測システム】2年分学習済み版")
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

# パス設定
AI_MEMORY_PATH = '/content/ai_memory_note_v66.csv'

# ライブラリインポート
try:
    import lightgbm as lgb
    HAS_LGB = True
    print("✅ LightGBM")
except:
    HAS_LGB = False

try:
    import xgboost as xgb
    HAS_XGB = True
    print("✅ XGBoost")
except:
    HAS_XGB = False

try:
    from catboost import CatBoostRegressor
    HAS_CAT = True
    print("✅ CatBoost")
except:
    HAS_CAT = False

try:
    from prophet import Prophet
    HAS_PROPHET = True
    print("✅ Prophet")
except:
    HAS_PROPHET = False

try:
    import jpholiday
    HAS_JPHOLIDAY = True
    print("✅ jpholiday")
except:
    HAS_JPHOLIDAY = False

print("\n✅ ライブラリ読み込み完了\n")


# =============================================================================
# AI記憶ノートクラス
# =============================================================================
class AIMemoryNote:
    """AI記憶ノート - 2年分学習対応版"""

    def __init__(self, memory_path=AI_MEMORY_PATH):
        self.memory_path = memory_path
        self.df_memory = self._load_memory()
        self.bias_info = {}

    def _load_memory(self):
        if os.path.exists(self.memory_path):
            try:
                df = pd.read_csv(self.memory_path)
                df['prediction_date'] = pd.to_datetime(df['prediction_date'], errors='coerce')
                print(f"  📚 AI記憶ノート: {len(df)}件の記録を読み込み")
                return df
            except:
                return pd.DataFrame()
        return pd.DataFrame()

    def save_prediction(self, prediction_date, prediction_data):
        """予測を保存"""
        try:
            new_record = {
                'prediction_date': pd.Timestamp(prediction_date).isoformat(),
                'prediction_timestamp': datetime.now().isoformat(),
                'final_prediction': prediction_data.get('final_prediction'),
                'pred_lower': prediction_data.get('pred_lower'),
                'pred_upper': prediction_data.get('pred_upper'),
                'confidence_score': prediction_data.get('confidence_score'),
                'ml_prediction': prediction_data.get('ml_prediction'),
                'stat_prediction': prediction_data.get('stat_prediction'),
                'actual_value': prediction_data.get('actual_value'),
                'error': prediction_data.get('error'),
                'error_pct': prediction_data.get('error_pct'),
                'bias_correction_applied': prediction_data.get('bias_correction_applied', False),
                'bias_correction_amount': prediction_data.get('bias_correction_amount', 0),
            }

            df_new = pd.DataFrame([new_record])
            self.df_memory = pd.concat([self.df_memory, df_new], ignore_index=True)
            return True
        except:
            return False

    def save_to_file(self):
        """ファイルに保存"""
        self.df_memory.to_csv(self.memory_path, index=False)

    def detect_bias(self, recent_n=10):
        """バイアス検出"""
        df_completed = self.df_memory[self.df_memory['actual_value'].notna()].copy()

        if len(df_completed) < 3:
            self.bias_info = {'detected': False, 'bias': 0, 'std': 0}
            return self.bias_info

        recent_errors = df_completed.tail(recent_n)['error'].dropna()

        if len(recent_errors) < 3:
            self.bias_info = {'detected': False, 'bias': 0, 'std': 0}
            return self.bias_info

        bias = recent_errors.mean()
        std = recent_errors.std()

        is_biased = abs(bias) > max(10, 0.5 * std)

        self.bias_info = {
            'detected': is_biased,
            'bias': bias,
            'std': std,
            'sample_count': len(recent_errors),
            'direction': '過大予測' if bias > 0 else '過小予測'
        }

        return self.bias_info

    def apply_correction(self, prediction, special_day_score=0):
        """自己補正を適用"""
        if not self.bias_info.get('detected', False):
            return prediction, 0

        bias = self.bias_info['bias']

        if special_day_score > 0.5:
            correction_rate = 0.3
        elif special_day_score > 0.2:
            correction_rate = 0.5
        else:
            correction_rate = 0.7

        correction = -bias * correction_rate
        corrected_prediction = prediction + correction

        return corrected_prediction, correction

    def get_accuracy_stats(self):
        """精度統計を取得"""
        df_completed = self.df_memory[self.df_memory['actual_value'].notna()].copy()

        if len(df_completed) == 0:
            return None

        return {
            'total': len(df_completed),
            'mae': df_completed['error'].abs().mean(),
            'mae_pct': df_completed['error_pct'].abs().mean(),
            'median_error': df_completed['error_pct'].median(),
            'within_5pct': (df_completed['error_pct'].abs() <= 5).sum(),
            'within_10pct': (df_completed['error_pct'].abs() <= 10).sum(),
        }


# =============================================================================
# 簡易予測関数（バックテスト用）
# =============================================================================
def simple_predict(df_history, target_date):
    """シンプルな予測（類似日+前年+トレンド）"""
    pred_date = pd.to_datetime(target_date)

    # 同曜日同月の平均
    same_cond = (df_history['Date'].dt.weekday == pred_date.dayofweek) & \
                (df_history['Date'].dt.month == pred_date.month)
    same_days = df_history[same_cond]['合計']
    pred1 = same_days.mean() if len(same_days) > 0 else df_history['合計'].mean()

    # 前年同月の平均
    prev_year = df_history[(df_history['Date'].dt.year == pred_date.year - 1) &
                          (df_history['Date'].dt.month == pred_date.month)]['合計']
    pred2 = prev_year.mean() if len(prev_year) > 0 else pred1

    # 直近30日の平均
    recent = df_history[df_history['Date'] >= pred_date - timedelta(days=30)]['合計']
    pred3 = recent.mean() if len(recent) > 0 else pred1

    # アンサンブル
    ensemble = pred1 * 0.4 + pred2 * 0.4 + pred3 * 0.2

    return ensemble, pred1, pred2, pred3


# =============================================================================
# バックテスト実行（2年分学習）
# =============================================================================
def run_backtest_learning(df_orig, years=2):
    """2年分のバックテストでAI記憶ノートを学習"""
    print("\n" + "="*70)
    print("【AI記憶ノート】2年分バックテスト学習")
    print("="*70)

    memory_note = AIMemoryNote()

    df = df_orig.copy()
    df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
    df = df.dropna(subset=['Date']).sort_values('Date').reset_index(drop=True)

    if '合計' not in df.columns:
        print("⚠️ '合計'列が見つかりません")
        return memory_note

    df['合計'] = pd.to_numeric(df['合計'], errors='coerce').fillna(0)
    df = df[df['合計'] > 0]

    # 学習期間を設定（最新から2年分）
    end_date = df['Date'].max()
    start_date = end_date - timedelta(days=365 * years)

    # 少なくとも90日のヒストリカルデータが必要
    min_history_date = df['Date'].min() + timedelta(days=90)
    if start_date < min_history_date:
        start_date = min_history_date

    print(f"  学習期間: {start_date.date()} ～ {end_date.date()}")

    # バックテスト対象日
    backtest_dates = df[(df['Date'] >= start_date) & (df['Date'] <= end_date)]['Date'].tolist()

    print(f"  バックテスト日数: {len(backtest_dates)}日")
    print("\n  🔄 バックテスト実行中...")

    success_count = 0
    total_error = 0

    for i, target_date in enumerate(backtest_dates):
        try:
            # その日より前のデータのみを使用
            df_history = df[df['Date'] < target_date].copy()

            if len(df_history) < 30:
                continue

            # 予測
            ensemble, pred1, pred2, pred3 = simple_predict(df_history, target_date)

            # 実績値を取得
            actual = df[df['Date'] == target_date]['合計'].values[0]

            # 誤差計算
            error = ensemble - actual
            error_pct = (ensemble - actual) / actual * 100

            # バイアス検出と補正（過去10件の誤差から）
            memory_note.detect_bias(recent_n=10)
            corrected_pred, correction = memory_note.apply_correction(ensemble)

            # 補正後の誤差
            corrected_error = corrected_pred - actual
            corrected_error_pct = (corrected_pred - actual) / actual * 100

            # 記録（補正後の値を使用）
            prediction_data = {
                'final_prediction': corrected_pred,
                'pred_lower': corrected_pred * 0.85,
                'pred_upper': corrected_pred * 1.15,
                'confidence_score': 70,
                'ml_prediction': ensemble,
                'stat_prediction': pred1,
                'actual_value': actual,
                'error': corrected_error,
                'error_pct': corrected_error_pct,
                'bias_correction_applied': correction != 0,
                'bias_correction_amount': correction,
            }

            memory_note.save_prediction(target_date, prediction_data)

            total_error += abs(corrected_error_pct)
            success_count += 1

            # 進捗表示（100日ごと）
            if (i + 1) % 100 == 0:
                avg_error = total_error / success_count
                print(f"    {i+1}/{len(backtest_dates)} 完了 (平均誤差率: {avg_error:.2f}%)")

        except Exception as e:
            continue

    # 保存
    memory_note.save_to_file()

    # 結果表示
    print("\n" + "="*70)
    print("【バックテスト完了】")
    print("="*70)

    stats = memory_note.get_accuracy_stats()
    if stats:
        print(f"  ✅ 学習データ: {stats['total']}件")
        print(f"  📊 平均絶対誤差: {stats['mae']:.1f}件")
        print(f"  📊 平均絶対誤差率: {stats['mae_pct']:.2f}%")
        print(f"  📊 中央値誤差率: {stats['median_error']:+.2f}%")
        print(f"  📊 ±5%以内: {stats['within_5pct']}/{stats['total']} ({stats['within_5pct']/stats['total']*100:.1f}%)")
        print(f"  📊 ±10%以内: {stats['within_10pct']}/{stats['total']} ({stats['within_10pct']/stats['total']*100:.1f}%)")

    # 最終バイアス検出
    memory_note.detect_bias(recent_n=30)
    if memory_note.bias_info['detected']:
        print(f"\n  ⚠️ バイアス検出: {memory_note.bias_info['direction']}")
        print(f"     平均誤差: {memory_note.bias_info['bias']:+.1f}件")

    print("="*70 + "\n")

    return memory_note


# =============================================================================
# 特徴量エンジニアリング
# =============================================================================
def create_features(df, target_col='合計'):
    """特徴量生成"""
    df = df.copy()
    df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
    df = df.dropna(subset=['Date']).sort_values('Date').reset_index(drop=True)

    df['year'] = df['Date'].dt.year
    df['month'] = df['Date'].dt.month
    df['day'] = df['Date'].dt.day
    df['weekday'] = df['Date'].dt.dayofweek
    df['week_of_year'] = df['Date'].dt.isocalendar().week.astype(int)
    df['week_of_month'] = ((df['day'] - 1) // 7 + 1)

    df['month_sin'] = np.sin(2 * np.pi * df['month'] / 12)
    df['month_cos'] = np.cos(2 * np.pi * df['month'] / 12)
    df['weekday_sin'] = np.sin(2 * np.pi * df['weekday'] / 7)
    df['weekday_cos'] = np.cos(2 * np.pi * df['weekday'] / 7)

    df['is_month_start'] = (df['day'] <= 3).astype(int)
    df['is_month_end'] = (df['day'] >= 28).astype(int)
    df['is_weekend'] = (df['weekday'] >= 5).astype(int)
    df['is_monday'] = (df['weekday'] == 0).astype(int)
    df['is_friday'] = (df['weekday'] == 4).astype(int)

    if HAS_JPHOLIDAY:
        df['is_holiday'] = df['Date'].apply(lambda x: 1 if jpholiday.is_holiday(x) else 0)
    else:
        df['is_holiday'] = 0

    if target_col in df.columns:
        for lag in [1, 2, 3, 5, 7, 14, 21, 28, 30]:
            df[f'lag_{lag}'] = df[target_col].shift(lag)

        for w in [1, 2, 3, 4]:
            df[f'lag_{w*7}_weekday'] = df[target_col].shift(w * 7)

        df['lag_365'] = df[target_col].shift(365)

        for window in [7, 14, 30]:
            df[f'rolling_mean_{window}'] = df[target_col].shift(1).rolling(window, min_periods=1).mean()
            df[f'rolling_std_{window}'] = df[target_col].shift(1).rolling(window, min_periods=1).std()

        for span in [7, 14, 30]:
            df[f'ema_{span}'] = df[target_col].shift(1).ewm(span=span, adjust=False).mean()

        df['weekday_mean'] = df.groupby('weekday')[target_col].transform('mean')
        df['month_mean'] = df.groupby('month')[target_col].transform('mean')

    df = df.replace([np.inf, -np.inf], np.nan)
    return df


# =============================================================================
# 機械学習予測クラス
# =============================================================================
class MLPredictor:
    """ML予測クラス"""

    def __init__(self):
        self.models = {}
        self.scaler = RobustScaler()
        self.feature_cols = None
        self.is_trained = False
        self.model_scores = {}

    def train(self, df, target_col='合計'):
        """モデル訓練"""
        print("\n【機械学習訓練】")

        df_feat = create_features(df, target_col)
        df_train = df_feat.dropna(subset=[target_col])

        exclude_cols = ['Date', target_col, 'year']
        self.feature_cols = [c for c in df_train.columns
                            if c not in exclude_cols
                            and df_train[c].dtype in ['int64', 'float64', 'int32', 'float32']]

        X = df_train[self.feature_cols].fillna(0)
        y = df_train[target_col]

        if len(X) < 50:
            return False

        print(f"  訓練データ: {len(X)}件, 特徴量: {len(self.feature_cols)}個")

        X_scaled = self.scaler.fit_transform(X)

        # モデル初期化
        self.models = {}
        if HAS_LGB:
            self.models['LightGBM'] = lgb.LGBMRegressor(n_estimators=300, random_state=42, verbose=-1)
        if HAS_XGB:
            self.models['XGBoost'] = xgb.XGBRegressor(n_estimators=300, random_state=42, verbosity=0)
        if HAS_CAT:
            self.models['CatBoost'] = CatBoostRegressor(iterations=300, random_state=42, verbose=0)
        self.models['RandomForest'] = RandomForestRegressor(n_estimators=200, random_state=42, n_jobs=-1)
        self.models['Ridge'] = Ridge(alpha=1.0)

        # 訓練
        tscv = TimeSeriesSplit(n_splits=3)
        for name, model in self.models.items():
            try:
                print(f"  🔄 {name}...", end=" ")
                cv_scores = cross_val_score(model, X_scaled, y, cv=tscv, scoring='neg_mean_absolute_error')
                cv_mae = -cv_scores.mean()
                model.fit(X_scaled, y)
                self.model_scores[name] = cv_mae
                print(f"✅ MAE: {cv_mae:.1f}")
            except Exception as e:
                print(f"❌")

        self.is_trained = True
        return True

    def predict(self, df, target_date, target_col='合計'):
        """予測"""
        if not self.is_trained:
            return None, {}

        df_feat = create_features(df, target_col)
        target_dt = pd.to_datetime(target_date)
        target_row = df_feat[df_feat['Date'] == target_dt]

        if len(target_row) == 0:
            last_row = df_feat.iloc[-1:].copy()
            last_row['Date'] = target_dt
            target_row = last_row

        X_pred = target_row[self.feature_cols].fillna(0)
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

        if len(predictions) == 0:
            return None, {}

        # 加重平均
        weights = {k: 1/(self.model_scores.get(k, 100)+1) for k in predictions}
        total_w = sum(weights.values())
        weights = {k: v/total_w for k, v in weights.items()}

        ensemble = sum(predictions[k] * weights[k] for k in predictions)

        return ensemble, predictions


# =============================================================================
# メイン予測関数
# =============================================================================
memory_note = None
ml_predictor = MLPredictor()
global_df = None
is_initialized = False

def initialize_system(df_orig):
    """システム初期化（2年分学習）"""
    global memory_note, ml_predictor, is_initialized

    print("\n" + "="*70)
    print("【v66.7 システム初期化】2年分学習")
    print("="*70)

    # 2年分バックテスト学習
    memory_note = run_backtest_learning(df_orig, years=2)

    # MLモデル訓練
    ml_predictor.train(df_orig, '合計')

    is_initialized = True
    print("\n✅ 初期化完了！AI記憶ノートに2年分の学習データを蓄積しました。")


def run_prediction(target_date, actuals, df_orig):
    """予測実行"""
    global memory_note, ml_predictor, is_initialized

    if not is_initialized:
        initialize_system(df_orig)

    print("\n" + "="*70)
    print("【v66.7 予測実行】2年分学習済み")
    print("="*70)
    print(f"予測日: {target_date}\n")

    df = df_orig.copy()
    df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
    df = df.dropna(subset=['Date'])
    df['合計'] = pd.to_numeric(df['合計'], errors='coerce').fillna(0)
    df = df[df['合計'] > 0]

    # ML予測
    ml_pred, ml_preds = ml_predictor.predict(df, target_date, '合計')

    # 統計予測
    pred_date = pd.to_datetime(target_date)
    same_cond = (df['Date'].dt.weekday == pred_date.dayofweek) & (df['Date'].dt.month == pred_date.month)
    stat_pred = df[same_cond]['合計'].mean() if len(df[same_cond]) > 0 else df['合計'].mean()

    # アンサンブル
    if ml_pred:
        ensemble = ml_pred * 0.7 + stat_pred * 0.3
    else:
        ensemble = stat_pred

    # バイアス検出と補正
    print("\n【AI記憶ノート分析】")
    stats = memory_note.get_accuracy_stats()
    if stats:
        print(f"  学習データ: {stats['total']}件")
        print(f"  過去MAE: {stats['mae_pct']:.2f}%")

    memory_note.detect_bias(recent_n=30)
    if memory_note.bias_info['detected']:
        print(f"  ⚠️ バイアス検出: {memory_note.bias_info['direction']} ({memory_note.bias_info['bias']:+.1f}件)")

    corrected_pred, correction = memory_note.apply_correction(ensemble)

    if correction != 0:
        print(f"\n【メタ認知的自己補正】")
        print(f"  補正前: {ensemble:.0f}件")
        print(f"  補正量: {correction:+.0f}件")
        print(f"  補正後: {corrected_pred:.0f}件")

    # リアルタイム調整
    final_pred = corrected_pred
    if actuals.get(12, 0) > 0:
        ratio_col = '件数(～12:00)比率'
        if ratio_col in df.columns:
            recent_ratio = df[df[ratio_col] > 0].tail(30)[ratio_col].mean()
            if recent_ratio > 0.1:
                est_12h = actuals[12] / recent_ratio
                final_pred = final_pred * 0.4 + est_12h * 0.6
                print(f"\n  ⏰ 12時実績調整: {actuals[12]}件 → 推定{est_12h:.0f}件")

    # 信頼区間
    pred_std = final_pred * 0.08
    pred_lower = max(0, final_pred - 1.96 * pred_std)
    pred_upper = final_pred + 1.96 * pred_std

    # 信頼度（学習データに基づく）
    if stats and stats['mae_pct'] < 5:
        confidence = 85
    elif stats and stats['mae_pct'] < 10:
        confidence = 75
    else:
        confidence = 65

    print("\n" + "="*70)
    print(f"★★★ 最終予測: {int(final_pred):,}件 ★★★")
    print(f"    信頼区間: {int(pred_lower):,} ～ {int(pred_upper):,}件")
    print(f"    信頼度: {confidence}点")
    if correction != 0:
        print(f"    AI補正: {correction:+.0f}件")
    print("="*70)

    return {
        'final_prediction': int(final_pred),
        'pred_lower': int(pred_lower),
        'pred_upper': int(pred_upper),
        'confidence_score': confidence,
        'ml_prediction': ml_pred,
        'stat_prediction': stat_pred,
        'bias_correction': correction
    }


# =============================================================================
# UI
# =============================================================================
date_picker = widgets.DatePicker(description='予測日:', value=date.today())
actual_12h = widgets.IntText(value=0, description='12時実績:', layout=widgets.Layout(width='150px'))

run_btn = widgets.Button(description='🚀 予測実行', button_style='success',
                        layout=widgets.Layout(width='200px', height='50px'))
init_btn = widgets.Button(description='🎓 2年分学習', button_style='warning',
                         layout=widgets.Layout(width='150px', height='50px'))
output = widgets.Output()
result_output = widgets.Output()

def on_init(b):
    global global_df, is_initialized
    init_btn.disabled = True
    init_btn.description = '学習中...'

    with output:
        clear_output()

        import glob
        files = glob.glob('/content/*.xlsx')
        if not files:
            files = glob.glob('/content/*.csv')

        if not files:
            print("⚠️ データファイルをアップロードしてください")
            init_btn.disabled = False
            init_btn.description = '🎓 2年分学習'
            return

        try:
            if files[0].endswith('.xlsx'):
                global_df = pd.read_excel(files[0], engine='openpyxl')
            else:
                global_df = pd.read_csv(files[0])

            if 'Date' not in global_df.columns:
                for col in ['日付', 'date']:
                    if col in global_df.columns:
                        global_df = global_df.rename(columns={col: 'Date'})
                        break

            initialize_system(global_df)

        except Exception as e:
            print(f"⚠️ エラー: {e}")
            traceback.print_exc()

    init_btn.disabled = False
    init_btn.description = '🎓 2年分学習'

def on_run(b):
    global global_df, is_initialized
    run_btn.disabled = True
    run_btn.description = '処理中...'

    with output:
        clear_output()

        if global_df is None:
            import glob
            files = glob.glob('/content/*.xlsx')
            if not files:
                files = glob.glob('/content/*.csv')

            if not files:
                print("⚠️ データファイルをアップロードしてください")
                run_btn.disabled = False
                run_btn.description = '🚀 予測実行'
                return

            try:
                if files[0].endswith('.xlsx'):
                    global_df = pd.read_excel(files[0], engine='openpyxl')
                else:
                    global_df = pd.read_csv(files[0])

                if 'Date' not in global_df.columns:
                    for col in ['日付', 'date']:
                        if col in global_df.columns:
                            global_df = global_df.rename(columns={col: 'Date'})
                            break
            except Exception as e:
                print(f"⚠️ エラー: {e}")
                run_btn.disabled = False
                run_btn.description = '🚀 予測実行'
                return

        actuals = {12: actual_12h.value}
        results = run_prediction(date_picker.value, actuals, global_df)

        with result_output:
            clear_output()

            correction_info = ""
            if results.get('bias_correction', 0) != 0:
                correction_info = f"<div style='margin-top:10px;'>🧠 AI補正: {results['bias_correction']:+.0f}件</div>"

            display(HTML(f"""
            <div style='background:linear-gradient(135deg,#667eea,#764ba2);color:white;padding:25px;border-radius:15px;text-align:center;margin-top:20px;'>
                <h2 style='margin:0;'>🧠 v66.7【2年分学習済み】</h2>
                <div style='font-size:56px;font-weight:bold;margin:20px 0;'>{results['final_prediction']:,}件</div>
                <div style='font-size:18px;'>信頼区間: {results['pred_lower']:,} ～ {results['pred_upper']:,}件</div>
                <div style='font-size:16px;margin-top:10px;'>信頼度: {results['confidence_score']}点</div>
                {correction_info}
            </div>
            """))

    run_btn.disabled = False
    run_btn.description = '🚀 予測実行'

init_btn.on_click(on_init)
run_btn.on_click(on_run)

ui = widgets.VBox([
    widgets.HTML('<h2 style="color:#1f77b4;">🧠 v66.7 メタ認知AI予測【2年分学習済み版】</h2>'),
    widgets.HTML('<p>初回実行時に2年分のバックテストでAI記憶ノートを学習します</p>'),
    date_picker,
    widgets.HBox([actual_12h]),
    widgets.HBox([run_btn, init_btn]),
    result_output
])

display(ui, output)

print("\n" + "="*70)
print("✅ v66.7【2年分学習版】準備完了！")
print("="*70)
print("\n【使い方】")
print("1. 実績表Excelをアップロード")
print("2. 「🎓 2年分学習」または「🚀 予測実行」をクリック")
print("3. 初回は2年分のバックテスト学習を実行（3-5分）")
print("4. 学習完了後、AIが過去の誤差パターンから自己補正")
print("="*70)
