import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import os
import matplotlib.cm as cm

# ==========================================
# 設定區
# ==========================================
# 圖表風格設定
plt.style.use('ggplot')
sns.set_theme(style="whitegrid")
plt.rcParams['font.sans-serif'] = ['Microsoft JhengHei', 'SimHei', 'Arial'] 
plt.rcParams['axes.unicode_minus'] = False

# 隊名標準化
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

def load_and_merge_data(pred_file, odds_file):
    """讀取並合併數據"""
    print(f"📚 讀取檔案: {pred_file} & {odds_file}...")
    
    try:
        df_p = pd.read_csv(pred_file)
        df_o = pd.read_csv(odds_file)
        
        # 統一日期格式
        df_p['Date'] = pd.to_datetime(df_p['date']).dt.strftime('%Y-%m-%d')
        df_o['Date'] = pd.to_datetime(df_o['Date']).dt.strftime('%Y-%m-%d')
        
        # 建立賠率查找表
        odds_map = {}
        for _, row in df_o.iterrows():
            d = row['Date']
            h = normalize_team(row['Home_Abbr'])
            a = normalize_team(row['Away_Abbr'])
            odds_map[f"{d}_{h}"] = row['Odds_Home']
            odds_map[f"{d}_{a}"] = row['Odds_Away']
            
        merged_data = []
        matches_count = 0
        
        for _, row in df_p.iterrows():
            d = row['Date']
            team = normalize_team(row['Team_Abbr']) if 'Team_Abbr' in row else normalize_team(row['Home'])
            
            is_home = False
            if 'Home' in row and team == normalize_team(row['Home']):
                is_home = True
            
            odds = odds_map.get(f"{d}_{team}")
            
            if odds:
                matches_count += 1
                prob = row['Win_Prob'] if 'Win_Prob' in row else row['Home_Win_Prob']
                if not is_home and 'Home_Win_Prob' in row: prob = 1.0 - row['Home_Win_Prob']
                
                ev = (prob * odds) - 1
                win = row['Win'] if 'Win' in row else 0
                
                merged_data.append({
                    'Date': pd.to_datetime(d),
                    'Team': team,
                    'Prob': prob,
                    'Odds': odds,
                    'EV': ev,
                    'Win': win,
                    'Is_Home': is_home
                })
        
        print(f"✅ 合併完成: 預測 {len(df_p)} 筆 -> 配對成功 {matches_count} 筆")
        return pd.DataFrame(merged_data).sort_values('Date')

    except Exception as e:
        print(f"❌ 資料讀取錯誤: {e}")
        return pd.DataFrame()

def simulate_strategies(df):
    """
    模擬 10 大策略的損益
    """
    
    strategies = {
        # --- 基準線 ---
        '🟢 基礎 (EV>0)': df[df['EV'] > 0].copy(),
        
        # --- 保守派 ---
        '🛡️ 穩健保本 (Prob>65%)': df[df['Prob'] > 0.65].copy(),
        '🛡️ 穩健過濾 (Prob>60%, Odds>1.3)': df[(df['Prob'] > 0.60) & (df['Odds'] > 1.3)].copy(),
        '🏰 鐵桶防禦 (Prob>75%)': df[df['Prob'] > 0.75].copy(),
        
        # --- 激進派 ---
        '🏹 狙擊冷門 (Odds>1.75, EV>5%)': df[(df['Odds'] >= 1.75) & (df['EV'] > 0.05)].copy(),
        '💎 極高價值 (EV>15%)': df[df['EV'] > 0.15].copy(),
        
        # --- 均衡派 ---
        '⚖️ 平衡型 (Prob>55%, Odds>1.6)': df[(df['Prob'] > 0.55) & (df['Odds'] > 1.6)].copy(),
        '🎯 精準打擊 (Prob>65%, EV>5%)': df[(df['Prob'] > 0.65) & (df['EV'] > 0.05)].copy(),
        
        # --- 情境派 ---
        '🏠 主場優勢 (Home, Prob>60%)': df[(df['Is_Home'] == True) & (df['Prob'] > 0.60)].copy(),
        '🛣️ 客場殺手 (Away, EV>5%)': df[(df['Is_Home'] == False) & (df['EV'] > 0.05)].copy(),
    }
    
    results = {}
    
    for name, strat_df in strategies.items():
        if strat_df.empty:
            continue
            
        # 計算單場損益 (單位: 1 unit)
        strat_df['Profit'] = np.where(strat_df['Win'] == 1, strat_df['Odds'] - 1, -1)
        strat_df['Cumulative_Profit'] = strat_df['Profit'].cumsum()
        
        total_bets = len(strat_df)
        wins = strat_df['Win'].sum()
        win_rate = wins / total_bets
        total_profit = strat_df['Profit'].sum()
        roi = (total_profit / total_bets) * 100
        
        results[name] = {
            'df': strat_df,
            'stats': (total_bets, win_rate, total_profit, roi)
        }
        
    return results

def plot_cumulative_profit(results):
    """圖表 1: 累計獲利曲線"""
    plt.figure(figsize=(14, 8))
    
    # 自動產生 10 種顏色
    colors = cm.tab10(np.linspace(0, 1, len(results)))
    
    # 依 ROI 排序
    sorted_results = sorted(results.items(), key=lambda x: x[1]['stats'][3], reverse=True)
    
    for i, (name, data) in enumerate(sorted_results):
        df = data['df']
        # 樣式循環：實線、虛線、點線、點劃線
        linestyle = ['-', '--', '-.', ':'][i % 4] 
        # 第一名加粗
        linewidth = 3.0 if i == 0 else 1.5
        # 第一名顏色特別顯眼 (例如金色/黃色)，如果不是第一名就用循環色
        color = 'gold' if i == 0 else colors[i]
        # 第一名永遠在最上層
        zorder = 10 if i == 0 else 2
        
        plt.plot(df['Date'], df['Cumulative_Profit'], 
                 label=f"{name} (ROI: {data['stats'][3]:.1f}%)", 
                 linewidth=linewidth, 
                 color=color,
                 linestyle=linestyle,
                 alpha=0.9,
                 zorder=zorder)
        
    plt.title('10大策略全明星大亂鬥 (Cumulative Profit)', fontsize=18)
    plt.xlabel('日期', fontsize=12)
    plt.ylabel('獲利 (單位: 注)', fontsize=12)
    plt.legend(bbox_to_anchor=(1.02, 1), loc='upper left', borderaxespad=0)
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    
    output_path = 'chart_cumulative_profit.png'
    plt.savefig(output_path)
    print(f"📊 圖表已儲存: {output_path}")

def plot_roi_summary(results):
    """圖表 2: ROI 橫條圖"""
    names = []
    rois = []
    colors = []
    
    # 從低到高排
    sorted_items = sorted(results.items(), key=lambda x: x[1]['stats'][3], reverse=False)
    
    for name, data in sorted_items:
        # 簡化名稱，只取前面幾個字
        short_name = name.split(' (')[0]
        names.append(short_name)
        roi = data['stats'][3]
        rois.append(roi)
        
        if roi > 5: colors.append('darkgreen')
        elif roi > 0: colors.append('lightgreen')
        elif roi > -5: colors.append('salmon')
        else: colors.append('darkred')
        
    plt.figure(figsize=(12, 8))
    bars = plt.barh(names, rois, color=colors, alpha=0.8)
    
    plt.axvline(0, color='black', linewidth=1.0)
    plt.xlabel('ROI (%)', fontsize=12)
    plt.title('各策略投資報酬率 (ROI) 排行榜', fontsize=16)
    
    for bar in bars:
        width = bar.get_width()
        label_x_pos = width + 0.5 if width >= 0 else width - 2.5
        plt.text(label_x_pos, bar.get_y() + bar.get_height()/2, 
                 f'{width:.1f}%', va='center', fontweight='bold')
    
    plt.tight_layout()
    plt.savefig('chart_roi_summary.png')
    print(f"📊 圖表已儲存: chart_roi_summary.png")

def main():
    pred_file = "predictions_2026_full_report.csv"
    odds_file = "odds_2026_full_season.csv"
    
    if not os.path.exists(pred_file) or not os.path.exists(odds_file):
        print("❌ 找不到輸入檔案。")
        return
        
    df = load_and_merge_data(pred_file, odds_file)
    if df.empty:
        print("⚠️ 無有效數據。")
        return

    # 模擬
    results = simulate_strategies(df)
    
    # 文字報告
    print("\n" + "="*80)
    print(f"{'策略名稱':<35} | {'場次':<6} | {'勝率':<6} | {'總獲利':<8} | {'ROI':<6}")
    print("-" * 80)
    
    # 依 ROI 排序
    sorted_results = sorted(results.items(), key=lambda x: x[1]['stats'][3], reverse=True)
    
    for name, data in sorted_results:
        count, win_rate, profit, roi = data['stats']
        print(f"{name:<35} | {count:<6} | {win_rate:.1%} | {profit:+.2f}u  | {roi:+.1f}%")
    print("="*80 + "\n")

    # 繪圖
    plot_cumulative_profit(results)
    plot_roi_summary(results)
    
    print("\n✅ 全明星分析完成！請查看 chart_cumulative_profit.png。")

if __name__ == "__main__":
    main()