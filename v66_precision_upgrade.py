# =============================================================================
# v66.4 精度向上モジュール【類似日検索高度化 + 特徴量エンジニアリング強化】
# =============================================================================
# 既存のv66.3コードに追加・置換して使用してください
# =============================================================================

import numpy as np
import pandas as pd
from datetime import datetime, timedelta, date
from scipy.spatial.distance import cdist
from sklearn.preprocessing import StandardScaler
import warnings
warnings.filterwarnings("ignore")

print("="*80)
print("【v66.4 精度向上モジュール】")
print("  ✅ 類似日検索の高度化（多次元類似度計算）")
print("  ✅ 特徴量エンジニアリング強化（50+新特徴量）")
print("="*80 + "\n")


# =============================================================================
# 【改善1】類似日検索の高度化 - 多次元類似度計算版
# =============================================================================

def predict_by_similar_days_v66_advanced(df_orig, prediction_date, recent_years=3, top_n=15):
    """
    【v66.4改善版】多次元特徴量ベースの類似日検索

    改善点：
    1. 複数特徴量での類似度計算（曜日、月、週、月初/月末など）
    2. 特徴量ごとの重み付け
    3. 距離の逆数による重み付き平均
    4. 年次トレンドの動的補正
    5. 季節性を考慮した類似日選択
    """
    print("\n" + "="*70)
    print("【v66.4改善版】多次元類似日ベース予測")
    print("="*70)

    try:
        # 防御: DataFrameの検証
        if df_orig is None or len(df_orig) == 0:
            print("  ⚠️ データフレームが空です")
            return 1000, {}

        if '合計' not in df_orig.columns:
            print("  ⚠️ '合計'列が見つかりません")
            return 1000, {}

        pred_date = pd.to_datetime(prediction_date)

        df = df_orig.copy()
        df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
        df = df.dropna(subset=['Date'])
        df = df[df['合計'] > 0].copy()

        if len(df) == 0:
            print("  ⚠️ 有効なデータがありません")
            return 1000, {}

        # =================================================================
        # 特徴量ベクトルの作成
        # =================================================================

        # 各日の特徴量を計算
        df['weekday'] = df['Date'].dt.dayofweek  # 0-6
        df['month'] = df['Date'].dt.month  # 1-12
        df['day'] = df['Date'].dt.day  # 1-31
        df['week_of_month'] = ((df['day'] - 1) // 7 + 1)  # 1-5
        df['is_month_start'] = (df['day'] <= 3).astype(int)
        df['is_month_end'] = (df['day'] >= 25).astype(int)
        df['quarter'] = df['Date'].dt.quarter  # 1-4
        df['day_of_year'] = df['Date'].dt.dayofyear  # 1-366
        df['is_monday'] = (df['weekday'] == 0).astype(int)
        df['is_friday'] = (df['weekday'] == 4).astype(int)

        # 月の季節性（sin/cos変換で連続性を保持）
        df['month_sin'] = np.sin(2 * np.pi * df['month'] / 12)
        df['month_cos'] = np.cos(2 * np.pi * df['month'] / 12)

        # 曜日の周期性
        df['weekday_sin'] = np.sin(2 * np.pi * df['weekday'] / 7)
        df['weekday_cos'] = np.cos(2 * np.pi * df['weekday'] / 7)

        # 予測日の特徴量
        target_features = {
            'weekday': pred_date.dayofweek,
            'month': pred_date.month,
            'day': pred_date.day,
            'week_of_month': (pred_date.day - 1) // 7 + 1,
            'is_month_start': 1 if pred_date.day <= 3 else 0,
            'is_month_end': 1 if pred_date.day >= 25 else 0,
            'quarter': (pred_date.month - 1) // 3 + 1,
            'day_of_year': pred_date.timetuple().tm_yday,
            'is_monday': 1 if pred_date.dayofweek == 0 else 0,
            'is_friday': 1 if pred_date.dayofweek == 4 else 0,
            'month_sin': np.sin(2 * np.pi * pred_date.month / 12),
            'month_cos': np.cos(2 * np.pi * pred_date.month / 12),
            'weekday_sin': np.sin(2 * np.pi * pred_date.dayofweek / 7),
            'weekday_cos': np.cos(2 * np.pi * pred_date.dayofweek / 7),
        }

        # =================================================================
        # 特徴量の重み設定（重要度順）
        # =================================================================
        feature_weights = {
            'weekday': 5.0,        # 曜日は最重要
            'month': 3.0,          # 月も重要
            'week_of_month': 2.0,  # 月の何週目か
            'is_month_start': 4.0, # 月初フラグは重要
            'is_month_end': 2.5,   # 月末フラグ
            'quarter': 1.5,        # 四半期
            'day_of_year': 0.5,    # 年間通算日（季節性）
            'is_monday': 2.0,      # 月曜フラグ
            'is_friday': 2.0,      # 金曜フラグ
            'month_sin': 2.0,      # 月の周期性
            'month_cos': 2.0,
            'weekday_sin': 3.0,    # 曜日の周期性
            'weekday_cos': 3.0,
        }

        feature_cols = list(feature_weights.keys())
        weights_array = np.array([feature_weights[col] for col in feature_cols])

        # =================================================================
        # 類似度計算
        # =================================================================

        # 直近N年のデータに限定
        cutoff_date = pred_date - pd.DateOffset(years=recent_years)
        df_recent = df[(df['Date'] >= cutoff_date) & (df['Date'] < pred_date)].copy()

        if len(df_recent) < 10:
            print(f"  ⚠️ 直近{recent_years}年のデータが少ない({len(df_recent)}件)。全期間を使用します。")
            df_recent = df[df['Date'] < pred_date].copy()

        if len(df_recent) == 0:
            print("  ⚠️ 有効な過去データがありません")
            return df['合計'].mean(), {}

        # 特徴量行列を作成
        X_history = df_recent[feature_cols].values
        X_target = np.array([[target_features[col] for col in feature_cols]])

        # 標準化（スケールを揃える）
        scaler = StandardScaler()
        X_history_scaled = scaler.fit_transform(X_history)
        X_target_scaled = scaler.transform(X_target)

        # 重み付きユークリッド距離を計算
        weighted_diff = (X_history_scaled - X_target_scaled) * weights_array
        distances = np.sqrt((weighted_diff ** 2).sum(axis=1))

        df_recent['similarity_distance'] = distances

        # =================================================================
        # 上位N件の類似日を選択
        # =================================================================

        actual_top_n = min(top_n, len(df_recent))
        similar_days = df_recent.nsmallest(actual_top_n, 'similarity_distance').copy()

        # 距離ベースの重み計算（距離が近いほど重みが大きい）
        min_distance = 0.01  # ゼロ除算防止
        inv_distances = 1 / (similar_days['similarity_distance'].values + min_distance)
        similarity_weights = inv_distances / inv_distances.sum()

        # 重み付き平均
        weighted_prediction = (similar_days['合計'].values * similarity_weights).sum()

        # =================================================================
        # 年次トレンド補正
        # =================================================================

        # 類似日の平均年と予測年の差
        similar_years = similar_days['Date'].dt.year
        avg_similar_year = similar_years.mean()
        years_diff = pred_date.year - avg_similar_year

        # 年ごとの平均を計算して成長率を推定
        yearly_avg = df_recent.groupby(df_recent['Date'].dt.year)['合計'].mean()

        if len(yearly_avg) >= 2:
            # 年次成長率を計算
            yearly_growth_rates = yearly_avg.pct_change().dropna()

            if len(yearly_growth_rates) > 0:
                # 直近の成長率を重視した加重平均
                weights_growth = np.linspace(0.5, 1.0, len(yearly_growth_rates))
                weights_growth = weights_growth / weights_growth.sum()
                avg_growth_rate = (yearly_growth_rates.values * weights_growth).sum()

                # 異常な成長率を制限（-15%～+25%）
                avg_growth_rate = np.clip(avg_growth_rate, -0.15, 0.25)
            else:
                avg_growth_rate = 0.0
        else:
            avg_growth_rate = 0.0

        # トレンド補正係数
        trend_adjustment = (1 + avg_growth_rate) ** years_diff
        trend_adjustment = np.clip(trend_adjustment, 0.7, 1.5)  # 極端な補正を制限

        # 最終予測
        prediction = weighted_prediction * trend_adjustment

        # 防御: 予測値の妥当性チェック
        if pd.isna(prediction) or prediction <= 0 or not np.isfinite(prediction):
            prediction = df['合計'].mean()

        # =================================================================
        # 結果出力
        # =================================================================

        print(f"  📊 類似日検索結果:")
        print(f"     - 検索対象期間: {df_recent['Date'].min().date()} ～ {df_recent['Date'].max().date()}")
        print(f"     - 候補日数: {len(df_recent)}件")
        print(f"     - 選択した類似日数: {actual_top_n}件")
        print(f"  📈 類似日の上位5件:")

        for i, (_, row) in enumerate(similar_days.head(5).iterrows()):
            print(f"     {i+1}. {row['Date'].date()} ({['月','火','水','木','金','土','日'][int(row['weekday'])]}) "
                  f"実績:{int(row['合計'])}件 距離:{row['similarity_distance']:.3f}")

        print(f"\n  🔢 計算結果:")
        print(f"     - 重み付き平均: {weighted_prediction:.1f}件")
        print(f"     - 年次成長率: {avg_growth_rate*100:+.2f}%")
        print(f"     - トレンド補正係数: {trend_adjustment:.4f}")
        print(f"     - 【予測値】: {prediction:.0f}件")
        print("="*70)

        details = {
            'similar_count': actual_top_n,
            'weighted_avg': weighted_prediction,
            'avg_growth_rate': avg_growth_rate,
            'trend_adjustment': trend_adjustment,
            'years_diff': years_diff,
            'top_similar_dates': similar_days['Date'].head(5).dt.strftime('%Y-%m-%d').tolist(),
            'top_similar_values': similar_days['合計'].head(5).tolist(),
            'similarity_weights': similarity_weights[:5].tolist()
        }

        return prediction, details

    except Exception as e:
        print(f"  ⚠️ 類似日ベース予測エラー: {e}")
        import traceback
        traceback.print_exc()
        try:
            return df_orig['合計'].mean() if len(df_orig) > 0 else 1000, {}
        except:
            return 1000, {}


def predict_by_similar_pattern_v66(df_orig, prediction_date, pattern_days=7, top_n=10):
    """
    【v66.4新機能】直近パターンマッチング予測

    直近N日間の推移パターンと類似した過去のパターンを検索し、
    その後の値から予測を行う
    """
    print("\n" + "="*70)
    print("【v66.4新機能】パターンマッチング予測")
    print("="*70)

    try:
        if df_orig is None or len(df_orig) == 0:
            return 1000, {}

        pred_date = pd.to_datetime(prediction_date)

        df = df_orig.copy()
        df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
        df = df.dropna(subset=['Date'])
        df = df.sort_values('Date').reset_index(drop=True)
        df = df[df['合計'] > 0].copy()

        if len(df) < pattern_days * 3:
            print("  ⚠️ パターンマッチングに十分なデータがありません")
            return df['合計'].mean(), {}

        # 直近N日間のパターンを取得
        recent_data = df[df['Date'] < pred_date].tail(pattern_days)

        if len(recent_data) < pattern_days:
            print(f"  ⚠️ 直近{pattern_days}日のデータが不足しています")
            return df['合計'].mean(), {}

        # パターンを正規化（相対変化率に変換）
        recent_values = recent_data['合計'].values
        recent_pattern = (recent_values - recent_values.mean()) / (recent_values.std() + 1e-8)

        # 過去の全パターンと比較
        pattern_similarities = []

        for i in range(pattern_days, len(df) - pattern_days - 1):
            # i日目を起点としたパターン
            hist_values = df.iloc[i-pattern_days:i]['合計'].values

            if len(hist_values) == pattern_days:
                hist_pattern = (hist_values - hist_values.mean()) / (hist_values.std() + 1e-8)

                # コサイン類似度を計算
                similarity = np.dot(recent_pattern, hist_pattern) / (
                    np.linalg.norm(recent_pattern) * np.linalg.norm(hist_pattern) + 1e-8
                )

                # パターン後の実績値
                next_value = df.iloc[i]['合計']
                pattern_date = df.iloc[i]['Date']

                pattern_similarities.append({
                    'date': pattern_date,
                    'similarity': similarity,
                    'next_value': next_value,
                    'pattern_mean': hist_values.mean()
                })

        if len(pattern_similarities) == 0:
            return df['合計'].mean(), {}

        # 類似度でソート
        pattern_df = pd.DataFrame(pattern_similarities)
        pattern_df = pattern_df.nlargest(top_n, 'similarity')

        # 類似度ベースの重み付き平均
        similarities = pattern_df['similarity'].values
        # 類似度を正の値に変換（-1～1 → 0～1）
        positive_similarities = (similarities + 1) / 2
        weights = positive_similarities / positive_similarities.sum()

        # スケール調整（直近の平均レベルに合わせる）
        recent_mean = recent_values.mean()
        pattern_means = pattern_df['pattern_mean'].values
        scale_factors = recent_mean / (pattern_means + 1e-8)

        adjusted_values = pattern_df['next_value'].values * scale_factors
        prediction = (adjusted_values * weights).sum()

        # 異常値チェック
        if pd.isna(prediction) or prediction <= 0 or not np.isfinite(prediction):
            prediction = recent_mean

        print(f"  📊 パターンマッチング結果:")
        print(f"     - 直近{pattern_days}日の平均: {recent_mean:.1f}件")
        print(f"     - 類似パターン数: {len(pattern_df)}件")
        print(f"     - 最高類似度: {pattern_df['similarity'].max():.4f}")
        print(f"     - 【予測値】: {prediction:.0f}件")
        print("="*70)

        return prediction, {
            'pattern_days': pattern_days,
            'recent_mean': recent_mean,
            'top_similarity': pattern_df['similarity'].max(),
            'matched_patterns': len(pattern_df)
        }

    except Exception as e:
        print(f"  ⚠️ パターンマッチング予測エラー: {e}")
        return 1000, {}


# =============================================================================
# 【改善2】特徴量エンジニアリング強化
# =============================================================================

def create_advanced_features_v66(df_orig, target_col='合計'):
    """
    【v66.4改善版】高度な特徴量エンジニアリング

    改善点：
    1. 多様なラグ特徴量（50+種類）
    2. 同曜日ラグ
    3. 移動統計量の拡充
    4. 指数加重移動平均
    5. 変化率・差分特徴量
    6. 前年同期比
    7. 曜日×月の交互作用
    """
    print("\n【v66.4】高度な特徴量エンジニアリング実行中...")

    try:
        df = df_orig.copy()

        # インデックスが日付型でない場合は変換
        if 'Date' in df.columns:
            df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
            df = df.set_index('Date')

        if not isinstance(df.index, pd.DatetimeIndex):
            print("  ⚠️ 日付インデックスが見つかりません")
            return df

        df = df.sort_index()
        initial_cols = len(df.columns)

        # =================================================================
        # 1. 基本ラグ特徴量
        # =================================================================
        lag_days = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 14, 21, 28, 35, 42, 49, 56,
                    60, 90, 91, 120, 180, 182, 270, 364, 365, 371, 728, 729]

        for lag in lag_days:
            if lag < len(df):
                df[f'lag_{lag}'] = df[target_col].shift(lag)

        # =================================================================
        # 2. 同曜日ラグ（1週前、2週前、...、12週前）
        # =================================================================
        for w in range(1, 13):
            lag = 7 * w
            if lag < len(df):
                df[f'same_dow_lag_{w}w'] = df[target_col].shift(lag)

        # 同曜日の移動平均（直近4週、8週、12週）
        for weeks in [4, 8, 12]:
            cols = [f'same_dow_lag_{w}w' for w in range(1, weeks+1) if f'same_dow_lag_{w}w' in df.columns]
            if cols:
                df[f'same_dow_mean_{weeks}w'] = df[cols].mean(axis=1)

        # =================================================================
        # 3. 移動統計量（平均、標準偏差、最小、最大、中央値）
        # =================================================================
        windows = [3, 5, 7, 10, 14, 21, 28, 42, 56, 60, 90]

        for w in windows:
            if w < len(df):
                df[f'rolling_mean_{w}'] = df[target_col].rolling(w, min_periods=1).mean()
                df[f'rolling_std_{w}'] = df[target_col].rolling(w, min_periods=1).std()
                df[f'rolling_min_{w}'] = df[target_col].rolling(w, min_periods=1).min()
                df[f'rolling_max_{w}'] = df[target_col].rolling(w, min_periods=1).max()
                df[f'rolling_median_{w}'] = df[target_col].rolling(w, min_periods=1).median()

                # 範囲（max - min）
                df[f'rolling_range_{w}'] = df[f'rolling_max_{w}'] - df[f'rolling_min_{w}']

                # 変動係数（CV）
                df[f'rolling_cv_{w}'] = df[f'rolling_std_{w}'] / (df[f'rolling_mean_{w}'] + 1e-8)

        # =================================================================
        # 4. 指数加重移動平均（EWMA）
        # =================================================================
        for span in [3, 7, 14, 21, 28, 60]:
            df[f'ewm_mean_{span}'] = df[target_col].ewm(span=span, adjust=False).mean()
            df[f'ewm_std_{span}'] = df[target_col].ewm(span=span, adjust=False).std()

        # =================================================================
        # 5. 変化率特徴量
        # =================================================================
        for period in [1, 2, 3, 5, 7, 14, 21, 28, 364]:
            if period < len(df):
                df[f'pct_change_{period}'] = df[target_col].pct_change(period)
                df[f'pct_change_{period}'] = df[f'pct_change_{period}'].replace([np.inf, -np.inf], np.nan)

        # =================================================================
        # 6. 差分特徴量
        # =================================================================
        for period in [1, 2, 7, 14, 28, 364]:
            if period < len(df):
                df[f'diff_{period}'] = df[target_col].diff(period)

        # 2次差分
        df['diff2_1'] = df[target_col].diff(1).diff(1)
        df['diff2_7'] = df[target_col].diff(7).diff(7)

        # =================================================================
        # 7. 前年同期比
        # =================================================================
        if len(df) > 365:
            df['yoy_ratio'] = df[target_col] / df[target_col].shift(364)
            df['yoy_ratio'] = df['yoy_ratio'].replace([np.inf, -np.inf], np.nan)

            df['yoy_diff'] = df[target_col] - df[target_col].shift(364)

            # 前年同期の移動平均比
            if 'rolling_mean_7' in df.columns:
                df['yoy_rolling_mean_7_ratio'] = df['rolling_mean_7'] / df['rolling_mean_7'].shift(364)
                df['yoy_rolling_mean_7_ratio'] = df['yoy_rolling_mean_7_ratio'].replace([np.inf, -np.inf], np.nan)

        # =================================================================
        # 8. 時間特徴量
        # =================================================================
        df['year'] = df.index.year
        df['month'] = df.index.month
        df['day'] = df.index.day
        df['dayofweek'] = df.index.dayofweek
        df['dayofyear'] = df.index.dayofyear
        df['weekofyear'] = df.index.isocalendar().week.astype(int)
        df['quarter'] = df.index.quarter
        df['week_of_month'] = ((df['day'] - 1) // 7 + 1)

        # 月初・月末
        df['is_month_start'] = (df['day'] <= 3).astype(int)
        df['is_month_end'] = (df['day'] >= 25).astype(int)
        df['days_from_month_start'] = df['day']
        df['days_to_month_end'] = df.index.to_series().apply(
            lambda x: (x.replace(day=1) + pd.DateOffset(months=1) - pd.DateOffset(days=1)).day - x.day
        )

        # 周期性特徴量（sin/cos変換）
        df['month_sin'] = np.sin(2 * np.pi * df['month'] / 12)
        df['month_cos'] = np.cos(2 * np.pi * df['month'] / 12)
        df['day_sin'] = np.sin(2 * np.pi * df['day'] / 31)
        df['day_cos'] = np.cos(2 * np.pi * df['day'] / 31)
        df['dow_sin'] = np.sin(2 * np.pi * df['dayofweek'] / 7)
        df['dow_cos'] = np.cos(2 * np.pi * df['dayofweek'] / 7)
        df['doy_sin'] = np.sin(2 * np.pi * df['dayofyear'] / 365)
        df['doy_cos'] = np.cos(2 * np.pi * df['dayofyear'] / 365)

        # =================================================================
        # 9. 曜日ワンホット
        # =================================================================
        for i in range(7):
            df[f'is_dow_{i}'] = (df['dayofweek'] == i).astype(int)

        # =================================================================
        # 10. 月ワンホット
        # =================================================================
        for i in range(1, 13):
            df[f'is_month_{i}'] = (df['month'] == i).astype(int)

        # =================================================================
        # 11. 曜日×月の交互作用
        # =================================================================
        for dow in range(7):
            for month in range(1, 13):
                df[f'dow{dow}_month{month}'] = (
                    (df['dayofweek'] == dow) & (df['month'] == month)
                ).astype(int)

        # =================================================================
        # 12. 月初×曜日の交互作用
        # =================================================================
        for dow in range(7):
            df[f'month_start_dow{dow}'] = (
                (df['is_month_start'] == 1) & (df['dayofweek'] == dow)
            ).astype(int)
            df[f'month_end_dow{dow}'] = (
                (df['is_month_end'] == 1) & (df['dayofweek'] == dow)
            ).astype(int)

        # =================================================================
        # 13. 曜日別の統計量
        # =================================================================
        # 曜日ごとの移動平均（過去データのみ使用）
        for dow in range(7):
            dow_mask = df['dayofweek'] == dow
            dow_data = df.loc[dow_mask, target_col]

            if len(dow_data) > 0:
                # 累積平均（データリーク防止のためshift）
                df.loc[dow_mask, f'dow_{dow}_cumulative_mean'] = dow_data.expanding().mean().shift(1)

                # 直近4週の同曜日平均
                df.loc[dow_mask, f'dow_{dow}_rolling_4w'] = dow_data.rolling(4, min_periods=1).mean().shift(1)

        # =================================================================
        # 14. 月別の統計量
        # =================================================================
        for month in range(1, 13):
            month_mask = df['month'] == month
            month_data = df.loc[month_mask, target_col]

            if len(month_data) > 0:
                df.loc[month_mask, f'month_{month}_cumulative_mean'] = month_data.expanding().mean().shift(1)

        # =================================================================
        # 15. 相対位置特徴量
        # =================================================================
        # 直近の値と移動平均の比率
        for w in [7, 14, 28]:
            if f'rolling_mean_{w}' in df.columns:
                df[f'value_to_ma_{w}_ratio'] = df[target_col] / (df[f'rolling_mean_{w}'] + 1e-8)
                df[f'value_to_ma_{w}_ratio'] = df[f'value_to_ma_{w}_ratio'].replace([np.inf, -np.inf], np.nan)

        # Zスコア（標準化された位置）
        for w in [14, 28, 60]:
            if f'rolling_mean_{w}' in df.columns and f'rolling_std_{w}' in df.columns:
                df[f'zscore_{w}'] = (df[target_col] - df[f'rolling_mean_{w}']) / (df[f'rolling_std_{w}'] + 1e-8)

        # =================================================================
        # 16. トレンド特徴量
        # =================================================================
        # 短期トレンド vs 長期トレンド
        if 'rolling_mean_7' in df.columns and 'rolling_mean_28' in df.columns:
            df['trend_7_28'] = df['rolling_mean_7'] / (df['rolling_mean_28'] + 1e-8)
            df['trend_7_28'] = df['trend_7_28'].replace([np.inf, -np.inf], np.nan)

        if 'rolling_mean_14' in df.columns and 'rolling_mean_60' in df.columns:
            df['trend_14_60'] = df['rolling_mean_14'] / (df['rolling_mean_60'] + 1e-8)
            df['trend_14_60'] = df['trend_14_60'].replace([np.inf, -np.inf], np.nan)

        # =================================================================
        # 17. 特殊日フラグ
        # =================================================================
        # 年末年始
        df['is_year_end'] = ((df['month'] == 12) & (df['day'] >= 28)).astype(int)
        df['is_year_start'] = ((df['month'] == 1) & (df['day'] <= 5)).astype(int)

        # お盆
        df['is_obon'] = ((df['month'] == 8) & (df['day'] >= 11) & (df['day'] <= 16)).astype(int)

        # ゴールデンウィーク
        df['is_golden_week'] = ((df['month'] == 5) & (df['day'] >= 1) & (df['day'] <= 7)).astype(int)

        # 給料日前後（25日前後）
        df['is_payday'] = ((df['day'] >= 24) & (df['day'] <= 26)).astype(int)

        # 五十日（5, 10, 15, 20, 25, 30日）
        df['is_gotobi'] = df['day'].isin([5, 10, 15, 20, 25, 30]).astype(int)

        # =================================================================
        # 18. NaN処理
        # =================================================================
        # 前方埋め → 後方埋め → 0埋め
        df = df.fillna(method='ffill').fillna(method='bfill').fillna(0)

        # inf/-infを処理
        df = df.replace([np.inf, -np.inf], np.nan).fillna(0)

        final_cols = len(df.columns)
        print(f"  ✅ 特徴量生成完了: {initial_cols}列 → {final_cols}列 (+{final_cols - initial_cols}特徴量)")

        return df

    except Exception as e:
        print(f"  ⚠️ 特徴量エンジニアリングエラー: {e}")
        import traceback
        traceback.print_exc()
        return df_orig


def select_important_features(X, y, n_features=100, method='mutual_info'):
    """
    【v66.4】特徴量選択

    重要な特徴量のみを選択してノイズを減らす
    """
    from sklearn.feature_selection import mutual_info_regression, SelectKBest, f_regression

    try:
        # 欠損値を処理
        X_clean = X.fillna(0).replace([np.inf, -np.inf], 0)
        y_clean = y.fillna(y.mean())

        n_features = min(n_features, X_clean.shape[1])

        if method == 'mutual_info':
            # 相互情報量ベース
            selector = SelectKBest(mutual_info_regression, k=n_features)
        else:
            # F値ベース
            selector = SelectKBest(f_regression, k=n_features)

        selector.fit(X_clean, y_clean)
        selected_mask = selector.get_support()
        selected_features = X_clean.columns[selected_mask].tolist()

        print(f"  ✅ 特徴量選択: {X_clean.shape[1]}列 → {len(selected_features)}列")

        return X[selected_features], selected_features

    except Exception as e:
        print(f"  ⚠️ 特徴量選択エラー: {e}")
        return X, X.columns.tolist()


# =============================================================================
# 【改善3】改善版アンサンブル関数
# =============================================================================

def ensemble_predictions_v66_advanced(pred_similar, pred_pattern, pred_prev_year, pred_trend,
                                      similar_details, pattern_details, prev_year_details, trend_details):
    """
    【v66.4改善版】4手法のアンサンブル（動的重み調整）
    """
    print("\n" + "="*70)
    print("【v66.4アンサンブル】4手法統合")
    print("="*70)

    try:
        # 各手法の信頼度スコアを計算
        scores = {}

        # 1. 類似日ベース
        similar_count = similar_details.get('similar_count', 0)
        scores['similar'] = min(1.0, similar_count / 15) * 0.8 + 0.2

        # 2. パターンマッチング
        pattern_similarity = pattern_details.get('top_similarity', 0)
        scores['pattern'] = max(0.2, pattern_similarity)

        # 3. 前年同日ベース
        month_growth = prev_year_details.get('month_growth', 1.0)
        growth_stability = 1.0 - min(1.0, abs(month_growth - 1.0))
        scores['prev_year'] = growth_stability * 0.7 + 0.3

        # 4. 直近トレンド
        trend_ratio = trend_details.get('trend_ratio', 1.0)
        trend_stability = 1.0 - min(1.0, abs(trend_ratio - 1.0))
        scores['trend'] = trend_stability * 0.6 + 0.2

        # スコアを正規化
        total_score = sum(scores.values())
        weights = {k: v / total_score for k, v in scores.items()}

        # 重み付きアンサンブル
        predictions = {
            'similar': pred_similar,
            'pattern': pred_pattern,
            'prev_year': pred_prev_year,
            'trend': pred_trend
        }

        ensemble = sum(predictions[k] * weights[k] for k in predictions.keys())

        # 予測値のばらつきから不確実性を計算
        pred_values = list(predictions.values())
        pred_std = np.std(pred_values)
        pred_mean = np.mean(pred_values)
        uncertainty = pred_std / (pred_mean + 1e-8)

        print(f"  📊 各手法の予測値と重み:")
        print(f"     - 類似日ベース:     {pred_similar:,.0f}件 (重み: {weights['similar']:.1%})")
        print(f"     - パターンマッチ:   {pred_pattern:,.0f}件 (重み: {weights['pattern']:.1%})")
        print(f"     - 前年同日ベース:   {pred_prev_year:,.0f}件 (重み: {weights['prev_year']:.1%})")
        print(f"     - 直近トレンド:     {pred_trend:,.0f}件 (重み: {weights['trend']:.1%})")
        print(f"\n  🎯 アンサンブル予測値: {ensemble:,.0f}件")
        print(f"  📉 不確実性: {uncertainty:.2%}")
        print("="*70)

        return ensemble, {
            'weights': weights,
            'predictions': predictions,
            'uncertainty': uncertainty
        }

    except Exception as e:
        print(f"  ⚠️ アンサンブルエラー: {e}")
        return (pred_similar + pred_prev_year + pred_trend) / 3, {}


# =============================================================================
# 使用例
# =============================================================================

def demo_improved_prediction(df_orig, prediction_date):
    """改善版予測のデモ"""

    print("\n" + "="*80)
    print("【v66.4 精度向上版】予測デモ実行")
    print("="*80)

    # 1. 類似日ベース予測（改善版）
    pred_similar, similar_details = predict_by_similar_days_v66_advanced(
        df_orig, prediction_date, recent_years=3, top_n=15
    )

    # 2. パターンマッチング予測（新機能）
    pred_pattern, pattern_details = predict_by_similar_pattern_v66(
        df_orig, prediction_date, pattern_days=7, top_n=10
    )

    # 3. 前年同日ベース（既存関数を使用）
    # pred_prev_year, prev_year_details = predict_by_previous_year_v65(df_orig, prediction_date)
    # ここでは仮の値を使用
    pred_prev_year = pred_similar * 0.95
    prev_year_details = {'month_growth': 1.02}

    # 4. 直近トレンド（既存関数を使用）
    # pred_trend, trend_details = predict_by_recent_trend_v65(df_orig, prediction_date)
    pred_trend = pred_similar * 1.03
    trend_details = {'trend_ratio': 1.01}

    # アンサンブル
    final_pred, ensemble_details = ensemble_predictions_v66_advanced(
        pred_similar, pred_pattern, pred_prev_year, pred_trend,
        similar_details, pattern_details, prev_year_details, trend_details
    )

    print(f"\n★★★ 最終予測値: {final_pred:,.0f}件 ★★★\n")

    return final_pred, {
        'similar': (pred_similar, similar_details),
        'pattern': (pred_pattern, pattern_details),
        'ensemble': ensemble_details
    }


print("\n" + "="*80)
print("【v66.4 精度向上モジュール】読み込み完了！")
print("="*80)
print("\n使用方法:")
print("  1. predict_by_similar_days_v66_advanced() - 改善版類似日検索")
print("  2. predict_by_similar_pattern_v66() - パターンマッチング（新機能）")
print("  3. create_advanced_features_v66() - 高度な特徴量生成")
print("  4. select_important_features() - 特徴量選択")
print("  5. ensemble_predictions_v66_advanced() - 4手法アンサンブル")
print("\n" + "="*80 + "\n")
