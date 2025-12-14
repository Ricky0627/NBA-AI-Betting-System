import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns 
import os
import matplotlib.cm as cm
import re
import matplotlib.font_manager as fm # 導入字體管理器
from itertools import combinations # 確保該模組已被導入

# ==========================================
# 修正區：Matplotlib 字體設定 (使用 CJK 字體)
# ==========================================
plt.style.use('ggplot')
sns.set_theme(style="whitegrid")
# 設置字體列表，嘗試使用常見的 CJK 字體
plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft JhengHei', 'Arial Unicode MS', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False # 確保負號正常顯示
plt.rcParams['font.size'] = 14

# --- 隊名標準化 (保留以便函數能運行) ---
TEAM_MAP = {
    'PHO': 'PHO', 'PHX': 'PHO', 'BOS': 'BOS', 'MIL': 'MIL', 'DEN': 'DEN',
    'LAL': 'LAL', 'LAC': 'LAC', 'GSW': 'GSW', 'NYK': 'NYK', 'BKN': 'BRK', 'BRK': 'BRK',
    'MIA': 'MIA', 'PHI': 'PHI', 'CHI': 'CHI', 'CLE': 'CLE', 'ATL': 'ATL',
    'TOR': 'TOR', 'WAS': 'WAS', 'CHA': 'CHO', 'CHO': 'CHO', 'ORL': 'ORL',
    'IND': 'IND', 'DET': 'DET', 'MIN': 'MIN', 'OKC': 'OKC', 'POR': 'POR',
    'UTA': 'UTA', 'SAC': 'SAC', 'DAL': 'DAL', 'SAS': 'SAS', 'HOU': 'HOU',
    'MEM': 'MEM', 'NOP': 'NOP', 'NO': 'NOP'
}

def normalize_team(name):
    return TEAM_MAP.get(name, name)

# --- 載入與模擬邏輯 ---
def load_and_simulate():
    """載入數據並模擬策略損益，產生 Strategy_Performance_Report.csv"""
    
    try:
        # 1. 載入數據 (這裡假設數據文件存在)
        pred_file = "predictions_2026_full_report.csv"
        odds_file = "odds_2026_full_season.csv"
        
        df_p = pd.read_csv(pred_file)
        df_o = pd.read_csv(odds_file)

        df_p['date'] = pd.to_datetime(df_p['date'])
        
        # 處理賠率檔日期欄位 (防止大小寫不一)
        if 'date' in df_o.columns and 'Date' not in df_o.columns:
             df_o = df_o.rename(columns={'date': 'Date'})
        df_o['Date'] = pd.to_datetime(df_o['Date'])

        # 展開主客隊資料 (Long Format)
        odds_home = df_o[['Date', 'Home_Abbr', 'Odds_Home']].rename(columns={'Home_Abbr': 'Team', 'Odds_Home': 'Odds'})
        odds_home['Is_Home'] = True
        odds_away = df_o[['Date', 'Away_Abbr', 'Odds_Away']].rename(columns={'Away_Abbr': 'Team', 'Odds_Away': 'Odds'})
        odds_away['Is_Home'] = False
        odds_long = pd.concat([odds_home, odds_away])
        
        df_home = df_p.copy()
        df_home['Team'] = df_home['Team_Abbr']
        df_home['Is_Home'] = True
        df_home['Prob'] = df_home['Win_Prob']
        
        df_away = df_p.copy()
        df_away['Team'] = df_away['Opp_Abbr']
        df_away['Is_Home'] = False
        df_away['Prob'] = 1.0 - df_away['Win_Prob']
        df_away['Win'] = 1 - df_away['Win'] # 客隊贏等於主隊輸
        
        full_df = pd.concat([df_home, df_away], ignore_index=True)
        
        merged = pd.merge(full_df, odds_long, left_on=['date', 'Team', 'Is_Home'], right_on=['Date', 'Team', 'Is_Home'], how='inner')
        merged['EV'] = (merged['Prob'] * merged['Odds']) - 1
        
        # 2. 定義策略並模擬
        # 這裡的策略名稱必須使用長名稱，以匹配 CSV 報表
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

        for name, strat_df in strategies.items():
            if strat_df.empty:
                results[name] = {'df': pd.DataFrame({'date':[], 'Cumulative_Profit':[]}), 'stats': (0, 0.0, 0.0, 0.0)}
                continue
            
            strat_df['Profit'] = np.where(strat_df['Win'] == 1, strat_df['Odds'] - 1, -1)
            strat_df['Cumulative_Profit'] = strat_df['Profit'].cumsum()
            
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
                'ROI': f"{roi:+.1f}%"
            })
            
        # 3. 匯出策略報告 (供 Dashboard 使用)
        df_report = pd.DataFrame(report_data)
        # 必須轉換 ROI 為數字才能排序
        df_report['ROI_Val'] = df_report['ROI'].astype(str).str.replace('%', '').str.replace('+', '').astype(float)
        df_report = df_report.sort_values('ROI_Val', ascending=False)
        df_report[['策略名稱', '場次', '勝率', '總獲利 (單位)', 'ROI']].to_csv("Strategy_Performance_Report.csv", index=False, encoding='utf-8-sig')
        
        return results

    except Exception as e:
        print(f"致命錯誤：v980 數據處理失敗: {e}")
        return {}


# --- 核心圖表生成函數 (已修正所有中文標籤) ---
def plot_cumulative_profit(results):
    plt.figure(figsize=(20, 12))
    colors = cm.tab10(np.linspace(0, 1, len(results)))
    
    # 讀取剛剛生成的 CSV 進行排序
    try:
        df_report = pd.read_csv("Strategy_Performance_Report.csv")
        df_report['ROI_Val'] = df_report['ROI'].astype(str).str.replace('%', '').str.replace('+', '').astype(float)
        sorted_names = df_report.sort_values('ROI_Val', ascending=False)['策略名稱'].tolist()
    except Exception as e:
        sorted_names = list(results.keys())
    
    plottable_results = {name: data for name, data in results.items() if not data['df'].empty}
    
    i = 0
    for name in sorted_names:
        if name in plottable_results:
            data = plottable_results[name]
            df = data['df']
            
            # 標籤使用原始中文，依靠 Matplotlib 內建 CJK 字體顯示
            label_name = name
            
            linestyle = ['-', '--', '-.', ':'][i % 4] 
            linewidth = 4.0 if i == 0 else 2.0 
            color = 'gold' if i == 0 else colors[i]
            zorder = 10 if i == 0 else 2
            
            plt.plot(df['date'], df['Cumulative_Profit'], 
                     label=label_name, 
                     linewidth=linewidth, color=color, linestyle=linestyle, alpha=0.9, zorder=zorder)
            i += 1
            
    if not plottable_results:
        plt.text(0.5, 0.5, '無足夠數據繪製圖表', ha='center', va='center', fontsize=20)

    # 關鍵修正：圖表標題和軸標籤使用中文，依靠 Matplotlib CJK 字體顯示
    plt.title('10大策略累積獲利趨勢', fontsize=20, fontweight='bold')
    plt.xlabel('日期', fontsize=16)
    plt.ylabel('累積獲利 (注單位)', fontsize=16)
    
    plt.xticks(fontsize=14)
    plt.yticks(fontsize=14)
    # 將圖例放在圖外右上方，避免遮擋
    plt.legend(bbox_to_anchor=(1.01, 1), loc='upper left', borderaxespad=0, fontsize=12)
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig('chart_cumulative_profit.png', dpi=100)
    print(f"📊 圖表已儲存: chart_cumulative_profit.png")


def main_visualizer():
    # 嘗試清除 Matplotlib 緩存，以解決雲端環境字體查找問題
    try:
        import matplotlib.font_manager as fm
        fm._get_fontconfig_pattern.cache_clear() 
    except:
        pass
    
    results = load_and_simulate()
    if results:
        plot_cumulative_profit(results)
    
    print("✅ v980_strategy_visualizer.py 執行完畢 (已修正字體配置)")


if __name__ == "__main__":
    main_visualizer()
