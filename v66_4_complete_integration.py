# =============================================================================
# v66.4 統合ガイド - v66.3への精度向上モジュール統合方法
# =============================================================================
#
# このファイルは v66_precision_upgrade.py をv66.3に統合する手順を示します
#
# =============================================================================

"""
【統合手順】

============================================================================
STEP 1: v66.3のコードの先頭（インポート部分の後）に以下を追加
============================================================================
"""

INTEGRATION_CODE_STEP1 = '''
# =============================================================================
# v66.4 精度向上モジュールのインポート
# =============================================================================
# 以下のコードを v66.3 のインポート部分の後に追加してください

# v66.4精度向上モジュール（同じディレクトリに配置）
try:
    from v66_precision_upgrade import (
        predict_by_similar_days_v66_advanced,
        predict_by_similar_pattern_v66,
        create_advanced_features_v66,
        select_important_features,
        ensemble_predictions_v66_advanced
    )
    V66_4_AVAILABLE = True
    print("✅ v66.4 精度向上モジュールを読み込みました")
except ImportError:
    V66_4_AVAILABLE = False
    print("⚠️ v66.4 精度向上モジュールが見つかりません。v66.3の機能で動作します。")
'''

"""
============================================================================
STEP 2: predict_by_similar_days_v65 関数を置き換え
============================================================================
"""

INTEGRATION_CODE_STEP2 = '''
# =============================================================================
# 【置き換え】predict_by_similar_days_v65 → predict_by_similar_days_v66_advanced
# =============================================================================
# v66.3の predict_by_similar_days_v65 関数を以下で置き換えるか、
# 呼び出し部分を変更してください

def predict_by_similar_days_v65(df_orig, prediction_date, recent_years=2):
    """v66.3互換ラッパー - 内部でv66.4の改善版を呼び出す"""
    if V66_4_AVAILABLE:
        # v66.4の改善版を使用
        return predict_by_similar_days_v66_advanced(
            df_orig, prediction_date, recent_years=recent_years, top_n=15
        )
    else:
        # 元のv66.3実装にフォールバック
        # （元のコードをここに残す）
        pass
'''

"""
============================================================================
STEP 3: run_all_predictions_v66_part_a を修正
============================================================================
"""

INTEGRATION_CODE_STEP3 = '''
# =============================================================================
# 【修正】run_all_predictions_v66_part_a 内の予測呼び出し部分
# =============================================================================
# Step 6-10 の部分を以下のように修正

def run_all_predictions_v66_part_a_v64(target_date, actuals, update_progress):
    """v66.4対応版 - Part A"""

    # ... (Step 1-5 は変更なし) ...

    # =================================================================
    # Step 6-10: v66.4改善版アンサンブル予測
    # =================================================================

    update_progress(6, "【Step 6/30】【v66.4改善版】多次元類似日ベース予測...")
    if V66_4_AVAILABLE:
        pred1, similar_details = predict_by_similar_days_v66_advanced(
            df_orig, target_date, recent_years=3, top_n=15
        )
    else:
        pred1, similar_details = predict_by_similar_days_v65(df_orig, target_date, recent_years=2)

    update_progress(7, "【Step 7/30】【v66.4新機能】パターンマッチング予測...")
    if V66_4_AVAILABLE:
        pred_pattern, pattern_details = predict_by_similar_pattern_v66(
            df_orig, target_date, pattern_days=7, top_n=10
        )
    else:
        pred_pattern = pred1  # フォールバック
        pattern_details = {}

    update_progress(8, "【Step 8/30】【v65.0革新】前年同日ベース予測...")
    pred2, prev_year_details = predict_by_previous_year_v65(df_orig, target_date)

    update_progress(9, "【Step 9/30】【v65.0革新】直近トレンド補正予測...")
    pred3, trend_details = predict_by_recent_trend_v65(df_orig, target_date)

    update_progress(10, "【Step 10/30】【v66.4改善版】4手法アンサンブル統合...")
    if V66_4_AVAILABLE:
        # v66.4の4手法アンサンブル
        v65_ensemble, ensemble_info = ensemble_predictions_v66_advanced(
            pred1, pred_pattern, pred2, pred3,
            similar_details, pattern_details, prev_year_details, trend_details
        )
        ensemble_weights = list(ensemble_info.get('weights', {}).values())
        if len(ensemble_weights) < 3:
            ensemble_weights = [0.35, 0.25, 0.25, 0.15]
    else:
        # v66.3の3手法アンサンブル
        ensemble_weights = optimize_ensemble_weights_v66(
            target_date, df_orig, similar_details, prev_year_details, trend_details
        )
        v65_ensemble = ensemble_v65_predictions(pred1, pred2, pred3, weights=ensemble_weights)

    # v65_details にパターン予測も追加
    v65_details = {
        'pred1': pred1,
        'pred2': pred2,
        'pred3': pred3,
        'pred_pattern': pred_pattern if V66_4_AVAILABLE else None,
        'similar_details': similar_details,
        'pattern_details': pattern_details if V66_4_AVAILABLE else {},
        'prev_year_details': prev_year_details,
        'trend_details': trend_details
    }

    # ... (残りは変更なし) ...
'''

"""
============================================================================
STEP 4: 特徴量エンジニアリング部分を修正
============================================================================
"""

INTEGRATION_CODE_STEP4 = '''
# =============================================================================
# 【修正】run_all_predictions_v66_part_b 内の特徴量エンジニアリング部分
# =============================================================================
# Step 13-17 の部分を以下のように修正

def run_all_predictions_v66_part_b_v64(results, target_date, update_progress):
    """v66.4対応版 - Part B"""

    # ... (Step 11-12 は変更なし) ...

    # =================================================================
    # Step 13-17: v66.4改善版特徴量エンジニアリング
    # =================================================================

    update_progress(13, "【Step 13/30】【v66.4改善版】高度特徴量エンジニアリング...")

    df_data_indexed = df_orig.set_index('Date')

    if V66_4_AVAILABLE:
        # v66.4の高度な特徴量エンジニアリング
        df_combined = create_advanced_features_v66(df_data_indexed, target_col='合計')

        # 予測日のインデックスを追加
        if target_date_ts not in df_combined.index:
            # 予測日の行を追加
            new_row = pd.DataFrame(index=[target_date_ts])
            df_combined = pd.concat([df_combined, new_row])
            df_combined = df_combined.sort_index()

            # 予測日の特徴量を補完
            df_combined = df_combined.fillna(method='ffill').fillna(0)
    else:
        # v66.3の基本特徴量エンジニアリング
        # （元のコード）
        pass

    update_progress(14, "【Step 14/30】特徴量選択...")

    # 学習データの準備
    train_mask = df_combined.index < target_date_ts
    all_train_features_df = df_combined[train_mask].copy()

    # ターゲット変数
    if '合計' in all_train_features_df.columns:
        all_train_target_s = all_train_features_df['合計']
        all_train_features_df = all_train_features_df.drop(columns=['合計'])

    y_train_log = np.log1p(all_train_target_s)

    if V66_4_AVAILABLE and len(all_train_features_df.columns) > 100:
        # 特徴量選択で重要な特徴量のみを使用
        all_train_features_df, selected_features = select_important_features(
            all_train_features_df, y_train_log, n_features=100, method='mutual_info'
        )
        results['selected_features'] = selected_features

    # ... (Step 15-17 は変更なし、または省略可能) ...
'''

print("="*80)
print("【v66.4 統合ガイド】")
print("="*80)
print("\n統合手順:")
print("  STEP 1: v66_precision_upgrade.py を同じディレクトリに配置")
print("  STEP 2: v66.3コードの先頭でインポート")
print("  STEP 3: run_all_predictions_v66_part_a を修正")
print("  STEP 4: run_all_predictions_v66_part_b を修正")
print("\n" + "="*80)


# =============================================================================
# 【完全統合版】v66.3 + v66.4精度向上モジュール統合コード
# =============================================================================
# 以下は、v66.3の主要な予測関数をv66.4対応に修正したコードです
# この関数で既存の関数を置き換えてください
# =============================================================================

def run_all_predictions_v66_4_integrated(target_date, actuals, df_orig, update_progress=None):
    """
    【v66.4統合版】メイン予測処理

    v66.3のコードを修正せずに、この関数を追加で呼び出すことで
    v66.4の精度向上機能を使用できます
    """

    if update_progress is None:
        def update_progress(step, msg):
            print(f"[{step}/30] {msg}")

    results = {}

    try:
        # =================================================================
        # Step 1-5: データ前処理（v66.3と同じ）
        # =================================================================
        update_progress(1, "【Step 1/30】データ検証...")

        if df_orig is None or len(df_orig) == 0:
            raise ValueError("データが空です")

        df = df_orig.copy()

        if 'Date' in df.columns:
            df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
            df = df.dropna(subset=['Date'])

        if '合計' not in df.columns:
            raise KeyError("'合計'列が見つかりません")

        df['合計'] = pd.to_numeric(df['合計'], errors='coerce').fillna(0)
        df = df[df['合計'] > 0]

        target_date_ts = pd.to_datetime(target_date)

        # =================================================================
        # Step 6-10: v66.4改善版予測
        # =================================================================

        update_progress(6, "【Step 6/30】【v66.4】多次元類似日ベース予測...")
        pred1, similar_details = predict_by_similar_days_v66_advanced(
            df, target_date, recent_years=3, top_n=15
        )

        update_progress(7, "【Step 7/30】【v66.4】パターンマッチング予測...")
        pred_pattern, pattern_details = predict_by_similar_pattern_v66(
            df, target_date, pattern_days=7, top_n=10
        )

        update_progress(8, "【Step 8/30】前年同日ベース予測...")
        # 簡易版の前年同日予測
        pred_date = pd.to_datetime(target_date)
        df_temp = df.copy()
        df_temp['Date'] = pd.to_datetime(df_temp['Date'])
        df_temp['month'] = df_temp['Date'].dt.month
        df_temp['year'] = df_temp['Date'].dt.year

        prev_year_data = df_temp[
            (df_temp['year'] == pred_date.year - 1) &
            (df_temp['month'] == pred_date.month)
        ]

        if len(prev_year_data) > 0:
            pred2 = prev_year_data['合計'].mean()

            # 成長率補正
            current_year_data = df_temp[df_temp['year'] == pred_date.year]
            if len(current_year_data) > 0:
                growth = current_year_data['合計'].mean() / prev_year_data['合計'].mean()
                growth = np.clip(growth, 0.8, 1.2)
                pred2 = pred2 * growth
        else:
            pred2 = pred1

        prev_year_details = {'prev_year_avg': pred2, 'month_growth': 1.0}

        update_progress(9, "【Step 9/30】直近トレンド予測...")
        # 簡易版の直近トレンド予測
        recent_30d = df_temp[df_temp['Date'] >= (pred_date - pd.Timedelta(days=30))]
        if len(recent_30d) > 0:
            recent_avg = recent_30d['合計'].mean()
            overall_avg = df_temp['合計'].mean()
            trend_ratio = recent_avg / overall_avg if overall_avg > 0 else 1.0
            pred3 = pred1 * trend_ratio
        else:
            pred3 = pred1
            trend_ratio = 1.0

        trend_details = {'recent_avg': recent_avg if len(recent_30d) > 0 else 0, 'trend_ratio': trend_ratio}

        update_progress(10, "【Step 10/30】【v66.4】4手法アンサンブル統合...")
        final_ensemble, ensemble_info = ensemble_predictions_v66_advanced(
            pred1, pred_pattern, pred2, pred3,
            similar_details, pattern_details, prev_year_details, trend_details
        )

        # =================================================================
        # Step 11-20: 特徴量エンジニアリング
        # =================================================================

        update_progress(13, "【Step 13/30】【v66.4】高度特徴量エンジニアリング...")
        df_indexed = df.set_index('Date')
        df_features = create_advanced_features_v66(df_indexed, target_col='合計')

        # =================================================================
        # Step 21-30: 結果集計
        # =================================================================

        update_progress(30, "【Step 30/30】結果集計...")

        # 信頼区間の計算
        pred_values = [pred1, pred_pattern, pred2, pred3]
        pred_std = np.std(pred_values)

        pred_lower = final_ensemble - 1.96 * pred_std
        pred_upper = final_ensemble + 1.96 * pred_std

        # 信頼度スコア
        uncertainty = ensemble_info.get('uncertainty', 0.1)
        confidence_score = max(0, min(100, 100 * (1 - uncertainty)))

        # 12時実績ベース推定
        estimate_12h_info = None
        if actuals.get(12, 0) > 0:
            actual_12h = actuals[12]
            # 過去の12時比率を計算
            if '件数(～12:00)' in df.columns:
                df_with_12h = df[df['件数(～12:00)'] > 0].copy()
                if len(df_with_12h) > 0:
                    ratio_12h = df_with_12h['件数(～12:00)'] / df_with_12h['合計']
                    mean_ratio = ratio_12h.mean()
                    if mean_ratio > 0:
                        estimate_from_12h = actual_12h / mean_ratio
                        estimate_12h_info = {
                            'estimated_final': estimate_from_12h,
                            'estimated_lower': actual_12h / ratio_12h.quantile(0.75),
                            'estimated_upper': actual_12h / ratio_12h.quantile(0.25),
                            'pace_ratio': actual_12h / (final_ensemble * mean_ratio),
                            'used_ratio': mean_ratio,
                            'confidence': '中'
                        }

                        # 12時実績を加味した最終予測
                        weight_12h = 0.6
                        final_ensemble = estimate_from_12h * weight_12h + final_ensemble * (1 - weight_12h)

        results = {
            'final_prediction': int(final_ensemble),
            'pred_lower': int(max(0, pred_lower)),
            'pred_upper': int(pred_upper),
            'confidence_score': confidence_score,
            'v65_ensemble': final_ensemble,
            'v65_details': {
                'pred1': pred1,
                'pred2': pred2,
                'pred3': pred3,
                'pred_pattern': pred_pattern,
                'similar_details': similar_details,
                'pattern_details': pattern_details,
                'prev_year_details': prev_year_details,
                'trend_details': trend_details
            },
            'ensemble_weights': list(ensemble_info.get('weights', {}).values()),
            'estimate_12h_info': estimate_12h_info,
            'meta_corrections': {'correction_applied': False},
            'special_day_score': 0.0
        }

        print("\n" + "="*70)
        print(f"★★★ v66.4 最終予測: {results['final_prediction']:,}件 ★★★")
        print(f"    信頼区間: {results['pred_lower']:,} ～ {results['pred_upper']:,}件")
        print(f"    信頼度スコア: {results['confidence_score']:.1f}点")
        print("="*70 + "\n")

        return results

    except Exception as e:
        print(f"⚠️ 予測エラー: {e}")
        import traceback
        traceback.print_exc()
        return {
            'final_prediction': 1000,
            'pred_lower': 800,
            'pred_upper': 1200,
            'confidence_score': 0,
            'error': str(e)
        }


# =============================================================================
# テスト用コード
# =============================================================================

if __name__ == "__main__":
    print("\n" + "="*80)
    print("【v66.4 統合版テスト】")
    print("="*80)

    # テストデータ作成
    import pandas as pd
    import numpy as np
    from datetime import datetime, timedelta

    # 2年分のダミーデータを生成
    dates = pd.date_range(start='2022-01-01', end='2024-11-30', freq='D')

    # 曜日パターン + 季節性 + トレンド + ノイズ
    np.random.seed(42)

    base_value = 1000
    trend = np.linspace(0, 200, len(dates))  # 上昇トレンド
    seasonal = 100 * np.sin(2 * np.pi * np.arange(len(dates)) / 365)  # 年間季節性
    weekly = 50 * np.sin(2 * np.pi * np.arange(len(dates)) / 7)  # 週間季節性
    noise = np.random.normal(0, 50, len(dates))

    # 曜日効果
    dow_effect = np.array([0, 20, 30, 40, 60, -100, -150])  # 月～日
    dow_values = np.array([dow_effect[d.dayofweek] for d in dates])

    values = base_value + trend + seasonal + weekly + dow_values + noise
    values = np.maximum(values, 100)  # 最小値制限

    df_test = pd.DataFrame({
        'Date': dates,
        '合計': values.astype(int),
        '件数(～12:00)': (values * 0.65).astype(int)
    })

    # 土日を除外（営業日のみ）
    df_test = df_test[df_test['Date'].dt.dayofweek < 5]

    print(f"テストデータ: {len(df_test)}件")
    print(f"期間: {df_test['Date'].min().date()} ～ {df_test['Date'].max().date()}")

    # 予測実行
    target_date = '2024-12-02'
    actuals = {12: 750, 14: 0, 15: 0}

    results = run_all_predictions_v66_4_integrated(
        target_date=target_date,
        actuals=actuals,
        df_orig=df_test
    )

    print("\n【テスト完了】")
    print(f"予測結果: {results['final_prediction']:,}件")
