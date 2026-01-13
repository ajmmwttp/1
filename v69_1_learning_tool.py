# =============================================================================
# v69.1 予測学習ツール【予測 vs 実績 分析システム】
# =============================================================================
# 機能:
# 1. 予測値と実績値を記録・比較
# 2. 誤差パターンを分析
# 3. 曜日・月・時期別のバイアスを検出
# 4. 自動補正係数を学習
# 5. 精度レポート生成
# =============================================================================

print("="*70)
print("【v69.1 予測学習ツール】予測 vs 実績 分析システム")
print("="*70)

import subprocess
import sys

# 必要なライブラリをインストール
packages = ['openpyxl', 'jpholiday']
for pkg in packages:
    try:
        subprocess.check_call([sys.executable, '-m', 'pip', 'install', '-q', pkg])
    except:
        pass

import os
import pandas as pd
import numpy as np
from datetime import date, timedelta, datetime
from scipy import stats
import warnings
warnings.filterwarnings("ignore")

try:
    import jpholiday
    HAS_JPHOLIDAY = True
except:
    HAS_JPHOLIDAY = False

# =============================================================================
# 学習データ管理クラス
# =============================================================================
class PredictionLearningSystem:
    """予測学習システム - 予測と実績を比較して学習"""

    def __init__(self, save_path='./prediction_learning_data.csv'):
        self.save_path = save_path
        self.df_records = self._load_records()
        self.correction_factors = {}
        self.bias_analysis = {}

        if len(self.df_records) > 0:
            self._analyze_all()
            print(f"✅ {len(self.df_records)}件の学習データを読み込み")

    def _load_records(self):
        """記録を読み込み"""
        if os.path.exists(self.save_path):
            try:
                df = pd.read_csv(self.save_path)
                df['date'] = pd.to_datetime(df['date'], errors='coerce')
                return df
            except:
                pass
        return pd.DataFrame(columns=[
            'date', 'prediction', 'actual', 'error', 'error_pct',
            'weekday', 'month', 'week_of_month', 'is_holiday',
            'prediction_source', 'notes'
        ])

    def save_records(self):
        """記録を保存"""
        self.df_records.to_csv(self.save_path, index=False)
        print(f"💾 保存完了: {self.save_path}")

    def add_record(self, record_date, prediction, actual, source='v69.0', notes=''):
        """新しい記録を追加"""
        record_date = pd.to_datetime(record_date)

        # 誤差計算
        error = prediction - actual
        error_pct = (prediction - actual) / actual * 100 if actual > 0 else 0

        # 日付属性
        weekday = record_date.dayofweek
        month = record_date.month
        week_of_month = (record_date.day - 1) // 7 + 1
        is_holiday = 1 if HAS_JPHOLIDAY and jpholiday.is_holiday(record_date) else 0

        new_record = {
            'date': record_date,
            'prediction': prediction,
            'actual': actual,
            'error': error,
            'error_pct': error_pct,
            'weekday': weekday,
            'month': month,
            'week_of_month': week_of_month,
            'is_holiday': is_holiday,
            'prediction_source': source,
            'notes': notes
        }

        # 重複チェック
        existing = self.df_records[self.df_records['date'] == record_date]
        if len(existing) > 0:
            self.df_records = self.df_records[self.df_records['date'] != record_date]
            print(f"⚠️ {record_date.date()}の既存記録を更新")

        self.df_records = pd.concat([self.df_records, pd.DataFrame([new_record])], ignore_index=True)
        self.df_records = self.df_records.sort_values('date').reset_index(drop=True)

        # 分析更新
        self._analyze_all()
        self.save_records()

        print(f"\n📝 記録追加: {record_date.date()}")
        print(f"   予測: {prediction:,}件 | 実績: {actual:,}件")
        print(f"   誤差: {error:+.0f}件 ({error_pct:+.1f}%)")

        return error, error_pct

    def _analyze_all(self):
        """全分析を実行"""
        if len(self.df_records) < 3:
            return

        df = self.df_records.copy()

        # 曜日別バイアス
        self.bias_analysis['weekday'] = df.groupby('weekday').agg({
            'error': 'mean',
            'error_pct': 'mean',
            'actual': 'count'
        }).rename(columns={'actual': 'count'}).to_dict('index')

        # 月別バイアス
        self.bias_analysis['month'] = df.groupby('month').agg({
            'error': 'mean',
            'error_pct': 'mean',
            'actual': 'count'
        }).rename(columns={'actual': 'count'}).to_dict('index')

        # 週別バイアス
        self.bias_analysis['week_of_month'] = df.groupby('week_of_month').agg({
            'error': 'mean',
            'error_pct': 'mean',
            'actual': 'count'
        }).rename(columns={'actual': 'count'}).to_dict('index')

        # 補正係数を計算
        self._calculate_correction_factors()

    def _calculate_correction_factors(self):
        """補正係数を計算"""
        if len(self.df_records) < 10:
            return

        df = self.df_records.tail(30)  # 直近30件

        # 曜日別補正
        for wd in range(7):
            wd_data = df[df['weekday'] == wd]
            if len(wd_data) >= 3:
                bias = wd_data['error_pct'].mean()
                if abs(bias) > 2:  # 2%以上のバイアスがある場合
                    self.correction_factors[f'weekday_{wd}'] = -bias / 100

        # 月別補正
        for m in range(1, 13):
            m_data = df[df['month'] == m]
            if len(m_data) >= 3:
                bias = m_data['error_pct'].mean()
                if abs(bias) > 2:
                    self.correction_factors[f'month_{m}'] = -bias / 100

        # 全体バイアス
        overall_bias = df['error_pct'].mean()
        if abs(overall_bias) > 2:
            self.correction_factors['overall'] = -overall_bias / 100

    def get_correction(self, target_date):
        """指定日の補正係数を取得"""
        target_date = pd.to_datetime(target_date)
        weekday = target_date.dayofweek
        month = target_date.month

        correction = 0

        # 曜日補正
        wd_key = f'weekday_{weekday}'
        if wd_key in self.correction_factors:
            correction += self.correction_factors[wd_key] * 0.5

        # 月補正
        m_key = f'month_{month}'
        if m_key in self.correction_factors:
            correction += self.correction_factors[m_key] * 0.3

        # 全体補正
        if 'overall' in self.correction_factors:
            correction += self.correction_factors['overall'] * 0.2

        return correction

    def apply_correction(self, prediction, target_date):
        """予測に補正を適用"""
        correction = self.get_correction(target_date)
        corrected = prediction * (1 + correction)

        if correction != 0:
            print(f"🔧 学習補正: {prediction:.0f} → {corrected:.0f} ({correction*100:+.1f}%)")

        return corrected

    def get_accuracy_report(self):
        """精度レポートを生成"""
        if len(self.df_records) < 3:
            print("⚠️ データが不足しています（最低3件必要）")
            return None

        df = self.df_records.copy()

        print("\n" + "="*70)
        print("【予測精度レポート】")
        print("="*70)

        # 全体統計
        total = len(df)
        mae = df['error'].abs().mean()
        mae_pct = df['error_pct'].abs().mean()
        median_error = df['error_pct'].median()
        std_error = df['error_pct'].std()

        within_5 = (df['error_pct'].abs() <= 5).sum()
        within_10 = (df['error_pct'].abs() <= 10).sum()
        within_15 = (df['error_pct'].abs() <= 15).sum()

        print(f"\n【全体統計】({total}件)")
        print(f"  平均絶対誤差: {mae:.0f}件 ({mae_pct:.1f}%)")
        print(f"  中央値誤差: {median_error:+.1f}%")
        print(f"  誤差標準偏差: {std_error:.1f}%")
        print(f"\n  ±5%以内:  {within_5:3d}/{total} ({within_5/total*100:.1f}%)")
        print(f"  ±10%以内: {within_10:3d}/{total} ({within_10/total*100:.1f}%)")
        print(f"  ±15%以内: {within_15:3d}/{total} ({within_15/total*100:.1f}%)")

        # 曜日別分析
        weekday_names = ['月', '火', '水', '木', '金', '土', '日']
        print(f"\n【曜日別分析】")
        print(f"  {'曜日':4} {'件数':>5} {'平均誤差':>10} {'バイアス':>10}")
        print(f"  {'-'*35}")
        for wd in range(7):
            wd_data = df[df['weekday'] == wd]
            if len(wd_data) > 0:
                avg_err = wd_data['error_pct'].mean()
                bias = "過大" if avg_err > 2 else "過小" if avg_err < -2 else "適正"
                print(f"  {weekday_names[wd]:4} {len(wd_data):5d} {avg_err:+9.1f}%  {bias}")

        # 月別分析
        print(f"\n【月別分析】")
        print(f"  {'月':4} {'件数':>5} {'平均誤差':>10} {'バイアス':>10}")
        print(f"  {'-'*35}")
        for m in range(1, 13):
            m_data = df[df['month'] == m]
            if len(m_data) > 0:
                avg_err = m_data['error_pct'].mean()
                bias = "過大" if avg_err > 2 else "過小" if avg_err < -2 else "適正"
                print(f"  {m:2d}月 {len(m_data):5d} {avg_err:+9.1f}%  {bias}")

        # トレンド分析（直近の傾向）
        if len(df) >= 10:
            recent = df.tail(10)
            recent_mae = recent['error_pct'].abs().mean()
            older = df.head(len(df)-10)
            if len(older) > 0:
                older_mae = older['error_pct'].abs().mean()
                trend = "改善中" if recent_mae < older_mae else "悪化中" if recent_mae > older_mae * 1.1 else "安定"
                print(f"\n【トレンド】")
                print(f"  直近10件MAE: {recent_mae:.1f}%")
                print(f"  過去MAE:     {older_mae:.1f}%")
                print(f"  傾向: {trend}")

        # 補正係数
        if self.correction_factors:
            print(f"\n【学習済み補正係数】")
            for key, value in self.correction_factors.items():
                print(f"  {key}: {value*100:+.1f}%")

        print("="*70)

        return {
            'total': total,
            'mae': mae,
            'mae_pct': mae_pct,
            'median_error': median_error,
            'std_error': std_error,
            'within_5_pct': within_5/total*100,
            'within_10_pct': within_10/total*100,
            'within_15_pct': within_15/total*100,
        }

    def get_worst_predictions(self, n=10):
        """最も誤差が大きかった予測を表示"""
        if len(self.df_records) == 0:
            return None

        df = self.df_records.copy()
        df['abs_error_pct'] = df['error_pct'].abs()
        worst = df.nlargest(n, 'abs_error_pct')

        print(f"\n【誤差が大きかった予測 TOP {n}】")
        print(f"{'日付':12} {'予測':>8} {'実績':>8} {'誤差':>10}")
        print("-"*45)
        for _, row in worst.iterrows():
            print(f"{row['date'].strftime('%Y-%m-%d')} {row['prediction']:8,.0f} {row['actual']:8,.0f} {row['error_pct']:+9.1f}%")

        return worst

    def get_best_predictions(self, n=10):
        """最も精度が高かった予測を表示"""
        if len(self.df_records) == 0:
            return None

        df = self.df_records.copy()
        df['abs_error_pct'] = df['error_pct'].abs()
        best = df.nsmallest(n, 'abs_error_pct')

        print(f"\n【精度が高かった予測 TOP {n}】")
        print(f"{'日付':12} {'予測':>8} {'実績':>8} {'誤差':>10}")
        print("-"*45)
        for _, row in best.iterrows():
            print(f"{row['date'].strftime('%Y-%m-%d')} {row['prediction']:8,.0f} {row['actual']:8,.0f} {row['error_pct']:+9.1f}%")

        return best

    def bulk_import_from_history(self, df_history, prediction_col='prediction', actual_col='合計', date_col='Date'):
        """過去データを一括インポート"""
        df = df_history.copy()
        df[date_col] = pd.to_datetime(df[date_col], errors='coerce')
        df = df.dropna(subset=[date_col, prediction_col, actual_col])

        count = 0
        for _, row in df.iterrows():
            try:
                self.add_record(
                    record_date=row[date_col],
                    prediction=row[prediction_col],
                    actual=row[actual_col],
                    source='history_import'
                )
                count += 1
            except:
                pass

        print(f"\n✅ {count}件のデータをインポートしました")
        return count


# =============================================================================
# バックテスト機能
# =============================================================================
def run_backtest_learning(df_orig, learning_system, years=2):
    """バックテストを実行して学習データを生成"""
    print("\n" + "="*70)
    print("【バックテスト学習】")
    print("="*70)

    df = df_orig.copy()
    df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
    df = df.dropna(subset=['Date']).sort_values('Date').reset_index(drop=True)
    df['合計'] = pd.to_numeric(df['合計'], errors='coerce').fillna(0)
    df = df[df['合計'] > 0]

    end_date = df['Date'].max()
    start_date = end_date - timedelta(days=365 * years)
    min_history = df['Date'].min() + timedelta(days=90)
    if start_date < min_history:
        start_date = min_history

    backtest_dates = df[(df['Date'] >= start_date) & (df['Date'] <= end_date)]['Date'].tolist()

    print(f"  期間: {start_date.date()} ～ {end_date.date()}")
    print(f"  対象日数: {len(backtest_dates)}日")
    print("\n  🔄 バックテスト実行中...")

    for i, target_date in enumerate(backtest_dates):
        df_history = df[df['Date'] < target_date]
        if len(df_history) < 30:
            continue

        # シンプルな予測（同曜日同月平均）
        pred_date = pd.to_datetime(target_date)
        same_cond = (df_history['Date'].dt.weekday == pred_date.dayofweek) & \
                    (df_history['Date'].dt.month == pred_date.month)
        pred1 = df_history[same_cond]['合計'].mean() if len(df_history[same_cond]) > 0 else df_history['合計'].mean()

        # 直近30日平均
        recent = df_history.tail(30)['合計'].mean()

        # 前年同時期
        prev_year = df_history[(df_history['Date'].dt.year == pred_date.year - 1) &
                               (df_history['Date'].dt.month == pred_date.month)]['合計']
        pred2 = prev_year.mean() if len(prev_year) > 0 else pred1

        # アンサンブル
        prediction = pred1 * 0.4 + pred2 * 0.3 + recent * 0.3

        # 学習補正を適用
        prediction = learning_system.apply_correction(prediction, target_date)

        # 実績
        actual = df[df['Date'] == target_date]['合計'].values[0]

        # 記録（サイレント）
        learning_system.df_records = pd.concat([
            learning_system.df_records,
            pd.DataFrame([{
                'date': target_date,
                'prediction': prediction,
                'actual': actual,
                'error': prediction - actual,
                'error_pct': (prediction - actual) / actual * 100,
                'weekday': pred_date.dayofweek,
                'month': pred_date.month,
                'week_of_month': (pred_date.day - 1) // 7 + 1,
                'is_holiday': 1 if HAS_JPHOLIDAY and jpholiday.is_holiday(pred_date) else 0,
                'prediction_source': 'backtest',
                'notes': ''
            }])
        ], ignore_index=True)

        # 進捗
        if (i + 1) % 100 == 0:
            print(f"    {i+1}/{len(backtest_dates)} 完了")

    # 分析と保存
    learning_system._analyze_all()
    learning_system.save_records()

    print("\n✅ バックテスト完了！")
    learning_system.get_accuracy_report()

    return learning_system


# =============================================================================
# UI（Google Colab用）
# =============================================================================
try:
    import ipywidgets as widgets
    from IPython.display import display, clear_output, HTML
    HAS_WIDGETS = True
except:
    HAS_WIDGETS = False

if HAS_WIDGETS:
    learning_system = PredictionLearningSystem()

    date_input = widgets.DatePicker(description='日付:', value=date.today())
    pred_input = widgets.IntText(value=0, description='予測値:')
    actual_input = widgets.IntText(value=0, description='実績値:')

    add_btn = widgets.Button(description='📝 記録追加', button_style='success',
                            layout=widgets.Layout(width='150px', height='40px'))
    report_btn = widgets.Button(description='📊 精度レポート', button_style='info',
                               layout=widgets.Layout(width='150px', height='40px'))
    worst_btn = widgets.Button(description='❌ 最悪予測', button_style='warning',
                              layout=widgets.Layout(width='120px', height='40px'))
    best_btn = widgets.Button(description='✅ 最良予測', button_style='primary',
                             layout=widgets.Layout(width='120px', height='40px'))

    output = widgets.Output()

    def on_add(b):
        with output:
            clear_output()
            if pred_input.value > 0 and actual_input.value > 0:
                learning_system.add_record(date_input.value, pred_input.value, actual_input.value)
            else:
                print("⚠️ 予測値と実績値を入力してください")

    def on_report(b):
        with output:
            clear_output()
            learning_system.get_accuracy_report()

    def on_worst(b):
        with output:
            clear_output()
            learning_system.get_worst_predictions()

    def on_best(b):
        with output:
            clear_output()
            learning_system.get_best_predictions()

    add_btn.on_click(on_add)
    report_btn.on_click(on_report)
    worst_btn.on_click(on_worst)
    best_btn.on_click(on_best)

    display(widgets.VBox([
        widgets.HTML('''
        <div style="background:linear-gradient(135deg,#2d3436,#636e72);color:white;padding:20px;border-radius:15px;margin-bottom:15px;">
            <h2 style="margin:0;">📚 v69.1 予測学習ツール</h2>
            <p style="margin:5px 0 0 0;opacity:0.9;">予測 vs 実績を記録・分析して精度を向上</p>
        </div>
        '''),
        widgets.HBox([date_input, pred_input, actual_input]),
        widgets.HBox([add_btn, report_btn, worst_btn, best_btn]),
        output
    ]))

print("\n" + "="*70)
print("✅ 予測学習ツール準備完了！")
print("="*70)
print("\n【使い方】")
print("1. learning = PredictionLearningSystem()")
print("2. learning.add_record('2025-01-13', 1050, 1023)  # 記録追加")
print("3. learning.get_accuracy_report()  # 精度レポート")
print("4. learning.apply_correction(1000, '2025-01-14')  # 補正適用")
print("="*70)
