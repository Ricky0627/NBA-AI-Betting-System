import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns 
import os
import matplotlib.cm as cm
import matplotlib.dates as mdates
from pandas.plotting import register_matplotlib_converters

# ==========================================
# 0. 環境設定
# ==========================================
# 設定 Matplotlib 不使用視窗介面 (避免在伺服器端報錯)
plt.switch_backend('Agg')

# 註冊 Matplotlib 日期轉換器
register_matplotlib_converters()

# ==========================================
# 1. 字體與繪圖風格設定
# ==========================================
plt.style.use('ggplot')
sns.set_theme(style="whitegrid")
# 設定中文字體優先順序
plt.rcParams['font.sans-serif'] = ['WenQuanYi Zen Hei', 'SimHei', 'Microsoft JhengHei', 'Arial Unicode MS', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False 
plt.rcParams['font.size'] = 12

# ==========================================
# 2. 核心邏輯：載入數據、模擬策略、匯出報告
# ==========================================
def load_and_simulate():
    """
    讀取預測與賠率檔案，模擬各策略損益，並匯出 CSV 報告。
    """
    print("⏳ 正在讀取數據並進行模擬...")
    
    try:
        # --- A. 讀取檔案 ---
        pred_file = "predictions_2026_full_report.csv"
        odds_file = "odds_2026_full_season.csv"
        
        if not os.path.exists(pred_file) or not os.path.exists(odds_file):
            print(f"❌ 錯誤：找不到 {pred_file} 或 {odds_file}")
            return {}

        df_pred = pd.read_csv(pred_file)
        df_o = pd.read_csv(odds_file)

        df_pred['date'] = pd.to_datetime(df_pred['date'])
        
        if 'date' in df_o.columns and 'Date' not in df_o.columns:
             df_o = df_o.rename(columns={'date': 'Date'})
        df_o['Date'] = pd.to_datetime(df_o['Date'])

        # --- B. 數據整併 ---
        odds_home = df_o[['Date', 'Home_Abbr', 'Odds_Home']].rename(columns={'Home_Abbr': 'Team', 'Odds_Home': 'Odds'})
        odds_home['Is_Home'] = True
        odds_away = df_o[['Date', 'Away_Abbr', 'Odds_Away']].rename(columns={'Away_Abbr': 'Team', 'Odds_Away': 'Odds'})
        odds_away['Is_Home'] = False
        odds_long = pd.concat([odds_home, odds_away])
        
        df_home = df_pred.copy()
        df_home['Team'] = df_home['Team_Abbr']
        df_home['Is_Home'] = True
        df_home['Prob'] = df_home['Win_Prob']
        
        df_away = df_pred.copy()
        df_away['Team'] = df_away['Opp_Abbr']
        df_away['Is_Home'] = False
        df_away['Prob'] = 1.0 - df_away['Win_Prob']
        df_away['Win'] = 1 - df_away['Win']
        
        full_df = pd.concat([df_home, df_away], ignore_index=True)
        merged = pd.merge(full_df, odds_long, left_on=['date', 'Team', 'Is_Home'], right_on=['Date', 'Team', 'Is_Home'], how='inner')
        merged['EV'] = (merged['Prob'] * merged['Odds']) - 1
        
        # --- C. 定義策略 ---
        strategies = {
            '🛡️ 穩健過濾 (Prob>60%, Odds>1.3)': merged[(merged['Prob'] > 0.60) & (merged['Odds'] > 1.3)].copy(),
            '🏰 鐵桶防禦 (Prob>75%)': merged[merged['Prob'] > 0.75].copy(),
            '🛡️ 穩健保本 (Prob>65%)': merged[merged['Prob'] > 0.65].copy(),
            '🎯 精準打擊 (Prob>65%, EV>5%)': merged[(merged['Prob'] > 0.65) & (merged['EV'] > 0.05)].copy(),
            '💎 極高價值 (EV>15%)': merged[merged['EV'] > 0.15].copy(),
            '⚖️ 平衡型 (Prob>55%, Odds>1.6)': merged[(merged['Prob'] > 0.55) & (merged['Odds'] > 1.6)].copy(),
            '🏠 主場優勢 (Home, Prob>60%)': merged[(merged['Is_Home'] == True) & (merged['Prob'] > 0.60)].copy(),
            '🛣️ 客場殺手 (Away, EV>5%)': merged[(merged['Is_Home'] == False) & (merged['EV'] > 0.05)].copy(),
            '🟢 基礎 (EV>0)': merged[merged['EV'] > 0].copy(),
            '🏹 狙擊冷門 (Odds>1.75, EV>5%)': merged[(merged['Odds'] >= 1.75) & (merged['EV'] > 0.05)].copy(),
        }

        results = {}
        report_data = []

        # --- D. 模擬迴圈 ---
        for name, strat_df in strategies.items():
            if strat_df.empty:
                results[name] = {'df': pd.DataFrame(), 'stats': (0, 0.0, 0.0, 0.0)}
                continue
            
            strat_df = strat_df.sort_values('date')
            strat_df['Profit'] = np.where(strat_df['Win'] == 1, strat_df['Odds'] - 1, -1)
            strat_df['Cumulative_Profit'] = strat_df['Profit'].cumsum()
            
            # 計算滾動勝率 (Win Rate Trend)
            strat_df['Cumulative_Wins'] = strat_df['Win'].cumsum()
            strat_df['Bet_Count'] = np.arange(1, len(strat_df) + 1)
            strat_df['Running_WR'] = strat_df['Cumulative_Wins'] / strat_df['Bet_Count']
            
            total_bets = len(strat_df)
            wins = strat_df['Win'].sum()
            win_rate = wins / total_bets
            profit_sum = strat_df['Profit'].sum()
            roi = (profit_sum / total_bets) * 100
            
            results[name] = {'df': strat_df, 'stats': (total_bets, win_rate, profit_sum, roi)}
            
            report_data.append({
                '策略名稱': name,
                '場次': total_bets,
                '勝率': f"{win_rate:.1%}",
                '總獲利 (單位)': f"{profit_sum:+.2f}u",
                'ROI': f"{roi:+.1f}%",
                'ROI_Raw': roi
            })
            
        # --- E. 匯出 CSV 與 顯示結果 ---
        df_report = pd.DataFrame(report_data)
        if not df_report.empty:
            df_report = df_report.sort_values('ROI_Raw', ascending=False)
            df_report_export = df_report.drop(columns=['ROI_Raw'])
            df_report_export.to_csv("Strategy_Performance_Report.csv", index=False, encoding='utf-8-sig')
            
            print("\n" + "="*60)
            print("🚀 策略績效排行榜 (Top 5)")
            print("="*60)
            # 👇 修改這裡：改用 .to_string() 避免需要 tabulate 套件
            print(df_report_export.head(5).to_string(index=False))
            print("="*60 + "\n")
        
        return results

    except Exception as e:
        print(f"❌ 致命錯誤：數據模擬失敗: {e}")
        import traceback
        traceback.print_exc()
        return {}


# ==========================================
# 3. 視覺化邏輯：繪製二合一儀表板
# ==========================================
def plot_strategy_dashboard(results):
    """
    繪製包含「累積獲利」與「勝率走勢」的雙子圖儀表板
    """
    try:
        df_report = pd.read_csv("Strategy_Performance_Report.csv")
        df_report['ROI_Val'] = df_report['ROI'].astype(str).str.replace('%', '').str.replace('+', '').astype(float)
        sorted_names = df_report.sort_values('ROI_Val', ascending=False)['策略名稱'].tolist()
        best_strategy_name = sorted_names[0] if sorted_names else None
    except:
        sorted_names = list(results.keys())
        best_strategy_name = sorted_names[0] if sorted_names else None
    
    plottable_results = {name: data for name, data in results.items() if not data['df'].empty}
    
    if not plottable_results:
        print("⚠️ 沒有數據可繪圖")
        return

    # 設定畫布：2 個子圖 (Rows=2, Cols=1)，高度比例 3:2
    fig, axes = plt.subplots(2, 1, figsize=(18, 14), sharex=True, gridspec_kw={'height_ratios': [3, 2]})
    colors = cm.tab10(np.linspace(0, 1, len(results)))
    
    # --- 圖表 1: 累積獲利趨勢 ---
    ax1 = axes[0]
    i = 0
    for name in sorted_names:
        if name in plottable_results:
            data = plottable_results[name]
            df = data['df']
            
            is_best = (name == best_strategy_name)
            linewidth = 4.5 if is_best else 2.0 
            color = '#FFD700' if is_best else colors[i % 10]
            zorder = 10 if is_best else 2
            alpha = 1.0 if is_best else 0.7
            linestyle = ['-', '--', '-.', ':'][i % 4]
            
            ax1.plot(df['date'], df['Cumulative_Profit'], 
                     label=name, 
                     linewidth=linewidth, color=color, linestyle=linestyle, alpha=alpha, zorder=zorder)
            i += 1
            
    ax1.set_title('各策略累積獲利趨勢 (Cumulative Profit)', fontsize=18, fontweight='bold')
    ax1.set_ylabel('獲利 (單位)', fontsize=14)
    ax1.legend(bbox_to_anchor=(1.01, 1), loc='upper left', fontsize=10)
    ax1.grid(True, alpha=0.3)

    # --- 圖表 2: 勝率走勢 ---
    ax2 = axes[1]
    i = 0
    for name in sorted_names:
        if name in plottable_results:
            data = plottable_results[name]
            df = data['df']
            
            is_best = (name == best_strategy_name)
            linewidth = 3.5 if is_best else 1.0
            color = '#FFD700' if is_best else colors[i % 10]
            alpha = 1.0 if is_best else 0.3 
            
            if len(df) > 5:
                ax2.plot(df['date'].iloc[5:], df['Running_WR'].iloc[5:], 
                         linewidth=linewidth, color=color, alpha=alpha)
            i += 1
            
    ax2.axhline(y=0.5, color='gray', linestyle='--', linewidth=1, alpha=0.5)
    ax2.set_title(f'勝率穩定度 (Win Rate Trend) - 金色線為最佳策略: {best_strategy_name}', fontsize=16)
    ax2.set_ylabel('累積勝率', fontsize=14)
    ax2.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: '{:.0%}'.format(x)))

    # X 軸日期格式化
    plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%m/%d'))
    plt.gca().xaxis.set_major_locator(mdates.DayLocator(interval=5))

    plt.tight_layout()
    plt.savefig('chart_strategy_dashboard.png', dpi=100)
    print("✅ 圖表已建立：chart_strategy_dashboard.png (含累積獲利與勝率走勢)")


def main_visualizer():
    try:
        import matplotlib.font_manager as fm
        fm._get_fontconfig_pattern.cache_clear() 
    except:
        pass
    
    results = load_and_simulate()
    
    if results:
        print("📊 正在繪製圖表...")
        plot_strategy_dashboard(results)
    
    print("✅ v980_strategy_visualizer.py 執行完畢。")


if __name__ == "__main__":
    main_visualizer()
