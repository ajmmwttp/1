# =============================================================================
# v66.4 メタ認知AI予測システム【精度向上統合版】- 修正版
# =============================================================================

print("="*70)
print("【v66.4 メタ認知AI予測システム】精度向上統合版")
print("="*70)

import os
import pandas as pd
import numpy as np
from sklearn.preprocessing import StandardScaler
from datetime import date, timedelta, datetime
import ipywidgets as widgets
from IPython.display import display, clear_output, HTML
import warnings
import traceback
warnings.filterwarnings("ignore")

try:
    import lightgbm as lgb
    HAS_LGB = True
except:
    HAS_LGB = False

try:
    import jpholiday
    HAS_JPHOLIDAY = True
except:
    HAS_JPHOLIDAY = False

print("✅ インポート完了\n")


# =============================================================================
# 類似日検索関数
# =============================================================================
def predict_by_similar_days_v66(df_orig, prediction_date, recent_years=3, top_n=15):
    """多次元類似日検索"""
    print("\n【類似日検索】")
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
        df['is_month_start'] = (df['day'] <= 3).astype(int)
        df['is_month_end'] = (df['day'] >= 25).astype(int)
        df['month_sin'] = np.sin(2 * np.pi * df['month'] / 12)
        df['month_cos'] = np.cos(2 * np.pi * df['month'] / 12)
        df['weekday_sin'] = np.sin(2 * np.pi * df['weekday'] / 7)
        df['weekday_cos'] = np.cos(2 * np.pi * df['weekday'] / 7)

        target_features = {
            'weekday': pred_date.dayofweek, 'month': pred_date.month,
            'week_of_month': (pred_date.day - 1) // 7 + 1,
            'is_month_start': 1 if pred_date.day <= 3 else 0,
            'is_month_end': 1 if pred_date.day >= 25 else 0,
            'month_sin': np.sin(2 * np.pi * pred_date.month / 12),
            'month_cos': np.cos(2 * np.pi * pred_date.month / 12),
            'weekday_sin': np.sin(2 * np.pi * pred_date.dayofweek / 7),
            'weekday_cos': np.cos(2 * np.pi * pred_date.dayofweek / 7),
        }

        feature_weights = {
            'weekday': 5.0, 'month': 3.0, 'week_of_month': 2.0,
            'is_month_start': 4.0, 'is_month_end': 2.5,
            'month_sin': 2.0, 'month_cos': 2.0,
            'weekday_sin': 3.0, 'weekday_cos': 3.0
        }

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

        actual_top_n = min(top_n, len(df_recent))
        similar_days = df_recent.nsmallest(actual_top_n, 'distance').copy()

        inv_distances = 1 / (similar_days['distance'].values + 0.01)
        similarity_weights = inv_distances / inv_distances.sum()
        weighted_prediction = (similar_days['合計'].values * similarity_weights).sum()

        # 年次トレンド補正
        yearly_avg = df_recent.groupby(df_recent['Date'].dt.year)['合計'].mean()
        if len(yearly_avg) >= 2:
            growth_rates = yearly_avg.pct_change().dropna()
            avg_growth = np.clip(growth_rates.mean(), -0.15, 0.25)
        else:
            avg_growth = 0.0

        years_diff = pred_date.year - similar_days['Date'].dt.year.mean()
        trend_adj = np.clip((1 + avg_growth) ** years_diff, 0.7, 1.5)
        prediction = weighted_prediction * trend_adj

        print(f"  類似日: {actual_top_n}件, 重み付き平均: {weighted_prediction:.0f}件")
        print(f"  年次成長率: {avg_growth*100:+.1f}%, 予測値: {prediction:.0f}件")

        return prediction, {'similar_count': actual_top_n, 'avg_growth_rate': avg_growth}
    except Exception as e:
        print(f"  ⚠️ エラー: {e}")
        return 1000, {}


# =============================================================================
# パターンマッチング関数
# =============================================================================
def predict_by_pattern_matching_v66(df_orig, prediction_date, pattern_days=7, top_n=10):
    """パターンマッチング予測"""
    print("\n【パターンマッチング】")
    try:
        if df_orig is None or len(df_orig) == 0:
            return 1000, {}

        pred_date = pd.to_datetime(prediction_date)
        df = df_orig.copy()
        df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
        df = df.dropna(subset=['Date']).sort_values('Date').reset_index(drop=True)
        df = df[df['合計'] > 0].copy()

        if len(df) < pattern_days * 3:
            return df['合計'].mean() if len(df) > 0 else 1000, {}

        recent_data = df[df['Date'] < pred_date].tail(pattern_days)
        if len(recent_data) < pattern_days:
            return df['合計'].mean(), {}

        recent_values = recent_data['合計'].values
        recent_std = max(recent_values.std(), 1e-8)
        recent_pattern = (recent_values - recent_values.mean()) / recent_std

        pattern_similarities = []
        for i in range(pattern_days, len(df) - pattern_days - 1):
            hist_values = df.iloc[i-pattern_days:i]['合計'].values
            if len(hist_values) == pattern_days:
                hist_std = max(hist_values.std(), 1e-8)
                hist_pattern = (hist_values - hist_values.mean()) / hist_std

                norm_r, norm_h = np.linalg.norm(recent_pattern), np.linalg.norm(hist_pattern)
                if norm_r > 1e-8 and norm_h > 1e-8:
                    similarity = np.dot(recent_pattern, hist_pattern) / (norm_r * norm_h)
                else:
                    similarity = 0

                pattern_similarities.append({
                    'similarity': similarity,
                    'next_value': df.iloc[i]['合計'],
                    'pattern_mean': hist_values.mean()
                })

        if len(pattern_similarities) == 0:
            return df['合計'].mean(), {}

        pattern_df = pd.DataFrame(pattern_similarities).nlargest(top_n, 'similarity')

        similarities = pattern_df['similarity'].values
        positive_sim = (similarities + 1) / 2
        weights = positive_sim / positive_sim.sum() if positive_sim.sum() > 0 else np.ones(len(positive_sim)) / len(positive_sim)

        recent_mean = recent_values.mean()
        scale_factors = np.clip(recent_mean / (pattern_df['pattern_mean'].values + 1e-8), 0.5, 2.0)
        adjusted_values = pattern_df['next_value'].values * scale_factors
        prediction = (adjusted_values * weights).sum()

        print(f"  パターン数: {len(pattern_df)}件, 最高類似度: {pattern_df['similarity'].max():.3f}")
        print(f"  予測値: {prediction:.0f}件")

        return prediction, {'top_similarity': pattern_df['similarity'].max()}
    except Exception as e:
        print(f"  ⚠️ エラー: {e}")
        return 1000, {}


# =============================================================================
# 前年同日・トレンド予測
# =============================================================================
def predict_by_previous_year_v66(df_orig, prediction_date):
    """前年同日ベース予測"""
    print("\n【前年同日ベース】")
    try:
        if df_orig is None or len(df_orig) == 0 or '合計' not in df_orig.columns:
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
        prediction = prev_year_avg * growth

        print(f"  前年同月平均: {prev_year_avg:.0f}件, 成長率: {(growth-1)*100:+.1f}%")
        print(f"  予測値: {prediction:.0f}件")

        return prediction, {'prev_year_avg': prev_year_avg, 'month_growth': growth}
    except Exception as e:
        print(f"  ⚠️ エラー: {e}")
        return 1000, {}


def predict_by_recent_trend_v66(df_orig, prediction_date):
    """直近トレンド予測"""
    print("\n【直近トレンド】")
    try:
        if df_orig is None or len(df_orig) == 0 or '合計' not in df_orig.columns:
            return 1000, {}

        pred_date = pd.to_datetime(prediction_date)
        df = df_orig.copy()
        df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
        df = df.dropna(subset=['Date'])
        df['month'], df['weekday'], df['year'] = df['Date'].dt.month, df['Date'].dt.dayofweek, df['Date'].dt.year

        recent_data = df[(df['Date'] >= pred_date - timedelta(days=30)) & (df['Date'] < pred_date) & (df['合計'] > 0)]
        if len(recent_data) < 5:
            recent_data = df[(df['Date'] < pred_date) & (df['合計'] > 0)].tail(20)
        if len(recent_data) == 0:
            return df['合計'].mean() if len(df) > 0 else 1000, {}

        recent_avg = recent_data['合計'].mean()

        historical_data = df[(df['month'] == pred_date.month) & (df['weekday'] == pred_date.dayofweek) & (df['year'] < pred_date.year) & (df['合計'] > 0)]
        if len(historical_data) == 0:
            historical_data = df[(df['weekday'] == pred_date.dayofweek) & (df['合計'] > 0)]
        if len(historical_data) == 0:
            return recent_avg, {}

        historical_avg = historical_data['合計'].mean()
        overall_avg = df[df['合計'] > 0]['合計'].mean()

        trend_ratio = np.clip(recent_avg / overall_avg, 0.7, 1.5) if overall_avg > 0 else 1.0
        prediction = historical_avg * trend_ratio

        print(f"  直近30日: {recent_avg:.0f}件, トレンド係数: {trend_ratio:.3f}")
        print(f"  予測値: {prediction:.0f}件")

        return prediction, {'recent_avg': recent_avg, 'trend_ratio': trend_ratio}
    except Exception as e:
        print(f"  ⚠️ エラー: {e}")
        return 1000, {}


# =============================================================================
# アンサンブル関数
# =============================================================================
def ensemble_predictions_v66(pred1, pred2, pred3, pred4, d1, d2, d3, d4):
    """4手法動的アンサンブル"""
    print("\n【アンサンブル統合】")
    try:
        scores = {}
        scores['similar'] = min(1.0, d1.get('similar_count', 0) / 15) * 0.8 + 0.2
        scores['pattern'] = max(0.2, (d2.get('top_similarity', 0) + 1) / 2)
        scores['prev_year'] = (1.0 - min(1.0, abs(d3.get('month_growth', 1.0) - 1.0))) * 0.7 + 0.3
        scores['trend'] = (1.0 - min(1.0, abs(d4.get('trend_ratio', 1.0) - 1.0))) * 0.6 + 0.2

        total_score = sum(scores.values())
        weights = {k: v / total_score for k, v in scores.items()}

        predictions = {'similar': pred1, 'pattern': pred2, 'prev_year': pred3, 'trend': pred4}
        ensemble = sum(predictions[k] * weights[k] for k in predictions.keys())

        pred_values = list(predictions.values())
        uncertainty = np.std(pred_values) / (np.mean(pred_values) + 1e-8)

        print(f"  重み: 類似日{weights['similar']:.0%}, パターン{weights['pattern']:.0%}, 前年{weights['prev_year']:.0%}, トレンド{weights['trend']:.0%}")
        print(f"  アンサンブル予測: {ensemble:.0f}件")

        return ensemble, {'weights': weights, 'uncertainty': uncertainty}
    except Exception as e:
        print(f"  ⚠️ エラー: {e}")
        return (pred1 + pred3 + pred4) / 3, {}


# =============================================================================
# メイン予測関数
# =============================================================================
def run_prediction_v66_4(target_date, actuals, df_orig):
    """v66.4 メイン予測"""
    print("\n" + "="*70)
    print("【v66.4 予測開始】")
    print("="*70)
    print(f"予測日: {target_date}\n")

    try:
        df = df_orig.copy()
        if 'Date' in df.columns:
            df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
            df = df.dropna(subset=['Date'])

        if '合計' not in df.columns:
            for col in ['actual_value', 'total', '件数']:
                if col in df.columns:
                    df = df.rename(columns={col: '合計'})
                    break

        df['合計'] = pd.to_numeric(df['合計'], errors='coerce').fillna(0)
        df = df[df['合計'] > 0]

        print(f"データ: {len(df)}日分")

        # 4手法予測
        pred1, d1 = predict_by_similar_days_v66(df, target_date)
        pred2, d2 = predict_by_pattern_matching_v66(df, target_date)
        pred3, d3 = predict_by_previous_year_v66(df, target_date)
        pred4, d4 = predict_by_recent_trend_v66(df, target_date)

        ensemble, ensemble_info = ensemble_predictions_v66(pred1, pred2, pred3, pred4, d1, d2, d3, d4)

        # 12時実績調整
        if actuals.get(12, 0) > 0 and '件数(～12:00)' in df.columns:
            df_12h = df[(df['件数(～12:00)'] > 0) & (df['合計'] > 0)].copy()
            if len(df_12h) > 0:
                df_12h['件数(～12:00)'] = pd.to_numeric(df_12h['件数(～12:00)'], errors='coerce')
                ratio = (df_12h['件数(～12:00)'] / df_12h['合計']).mean()
                if ratio > 0:
                    est_12h = actuals[12] / ratio
                    ensemble = ensemble * 0.4 + est_12h * 0.6
                    print(f"\n⏰ 12時実績反映: {est_12h:.0f}件")

        # 結果
        pred_values = [pred1, pred2, pred3, pred4]
        pred_std = np.std(pred_values)
        pred_lower = max(0, ensemble - 1.96 * pred_std)
        pred_upper = ensemble + 1.96 * pred_std
        confidence = max(0, min(100, 100 * (1 - ensemble_info.get('uncertainty', 0.1))))

        print("\n" + "="*70)
        print(f"★★★ 最終予測: {int(ensemble):,}件 ★★★")
        print(f"    信頼区間: {int(pred_lower):,} ～ {int(pred_upper):,}件")
        print(f"    信頼度: {confidence:.1f}点")
        print("="*70)

        return {
            'final_prediction': int(ensemble),
            'pred_lower': int(pred_lower),
            'pred_upper': int(pred_upper),
            'confidence_score': confidence
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
run_btn = widgets.Button(description='🚀 予測実行', button_style='success', layout=widgets.Layout(width='200px', height='50px'))
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

        results = run_prediction_v66_4(date_picker.value, {12: actual_12h.value}, global_df)

        with result_output:
            clear_output()
            display(HTML(f"""
            <div style='background:linear-gradient(135deg,#667eea,#764ba2);color:white;padding:20px;border-radius:10px;text-align:center;margin-top:20px;'>
                <h2 style='margin:0;'>🎯 v66.4 予測結果</h2>
                <div style='font-size:48px;font-weight:bold;margin:20px 0;'>{results['final_prediction']:,}件</div>
                <div style='font-size:16px;'>信頼区間: {results['pred_lower']:,} ～ {results['pred_upper']:,}件</div>
                <div style='font-size:16px;margin-top:10px;'>信頼度スコア: {results['confidence_score']:.1f}点</div>
            </div>
            """))

    run_btn.disabled = False
    run_btn.description = '🚀 予測実行'

run_btn.on_click(on_run)

ui = widgets.VBox([
    widgets.HTML('<h2 style="color:#1f77b4;">🧠 v66.4 メタ認知AI予測システム</h2>'),
    widgets.HTML('<p>実績表Excelをアップロードしてから予測を実行してください</p>'),
    widgets.HBox([date_picker, actual_12h]),
    run_btn,
    result_output
])

display(ui, output)

print("\n" + "="*70)
print("✅ 準備完了！")
print("="*70)
print("1. 左側の📁アイコンから実績表Excelをアップロード")
print("2. 日付を選択")
print("3. 「🚀 予測実行」ボタンをクリック")
print("="*70)
