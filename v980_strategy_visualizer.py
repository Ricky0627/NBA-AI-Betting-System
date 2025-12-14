import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import os
import matplotlib.cm as cm
from matplotlib import font_manager  # 新增

# ==========================================
# 設定區
# ==========================================
plt.style.use('ggplot')
sns.set_theme(style="whitegrid")

# 嘗試載入中文字型檔案 (需放在 repo/fonts 目錄或指定路徑)
font_path = os.path.join("fonts", "NotoSansCJK-Regular.ttc")
if os.path.exists(font_path):
    font_prop = font_manager.FontProperties(fname=font_path)
    plt.rcParams['font.family'] = font_prop.get_name()
else:
    # fallback: 使用常見字型名稱，避免 CI 環境找不到
    plt.rcParams['font.sans-serif'] = ['Microsoft JhengHei', 'SimHei', 'Arial']

plt.rcParams['axes.unicode_minus'] = False
plt.rcParams['font.size'] = 14

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
    """
    讀取並合併數據 (邏輯修正版)
    """
    print(f"📚 讀取檔案: {pred_file} & {odds_file}...")
    try:
        df_p = pd.read_csv(pred_file)
        df_o = pd.read_csv(odds_file)
        
        # 日期標準化
        if 'date' in df_p.columns:
            df_p['Date'] = pd.to_datetime(df_p['date']).dt.strftime('%Y-%m-%d')
        elif 'Date' in df_p.columns:
            df_p['Date'] = pd.to_datetime(df_p['Date']).dt.strftime('%Y-%m-%d')
            
        df_o['Date'] = pd.to_datetime(df_o['Date']).dt.strftime('%Y-%m-%d')
        
        # 建立賠率查找表 (只存主隊當 Key，確保唯一性)
        odds_map = {}
        for _, row in df_o.iterrows():
            d = row['Date']
            h = normalize_team(row['Home_Abbr'])
            # 格式：(主賠, 客賠)
            odds_map[f"{d}_{h}"] = (float(row['Odds_Home']), float(row['Odds_Away']))
            
        merged_data = []
        matches_count = 0
        
        for _, row in df_p.iterrows():
            d = row['Date']
            
            # 解析隊名
            if 'Home' in row:
                h = normalize_team(row['Home'])
                a = normalize_team(row['Away'])
                # 如果有 Home_Win_Prob 欄位，直接使用
                prob_h = float(row['Home_Win_Prob']) if 'Home_Win_Prob' in row else 0.5
            elif 'Team_Abbr' in row:
                # 處理另一種格式
                t = normalize_team(row['Team_Abbr'])
                o = normalize_team(row['Opp_Abbr'])
                is_home = row.get('Is_Home', True)
                if str(is_home).lower() in ['true', '1']:
                    h, a = t, o
                    prob_h = float(row['Win_Prob'])
                else:
                    h, a = o, t
                    prob_h = 1.0 - float(row['Win_Prob'])
            else:
                continue

            # 查找賠率 (用日期+主隊)
            odds_tuple = odds_map.get(f"{d}_{h}")
            
            if odds_tuple:
                matches_count += 1
                odds_home, odds_away = odds_tuple
                prob_a = 1.0 - prob_h
                
                # --- 嚴格勝負判定 (優先使用分數) ---
                real_win_h = 0
                if 'Home_Score' in row and 'Away_Score' in row:
                    try:
                        s_h = float(row['Home_Score'])
                        s_a = float(row['Away_Score'])
                        if s_h > s_a: real_win_h = 1
                    except:
                        pass
                elif 'Win' in row:
                    # 如果只有 Win 欄位，需確認它是指誰贏
                    # 假設 predictions_full_report.csv 都是主隊視角
                    if 'Home' in row:
                        real_win_h = int(row['Win'])
                    # 如果是 Team_Abbr 視角，且當前行是客隊，Win=1 可能代表客勝
                    elif 'Team_Abbr' in row and not is_home:
                        real_win_h = 1 - int(row['Win'])
                    else:
                        real_win_h = int(row['Win'])

                real_win_a = 1 - real_win_h

                # --- 產生數據 ---
                # 主隊下注
                ev_h = (prob_h * odds_home) - 1
                merged_data.append({
                    'Date': pd.to_datetime(d),
                    'Team': h, 'Prob': prob_h, 'Odds': odds_home, 'EV': ev_h, 'Win': real_win_h, 'Is_Home': True
                })
                
                # 客隊下注
                ev_a = (prob_a * odds_away) - 1
                merged_data.append({
                    'Date': pd.to_datetime(d),
                    'Team': a, 'Prob': prob_a, 'Odds': odds_away, 'EV': ev_a, 'Win': real_win_a, 'Is_Home': False
                })
        
        print(f"✅ 合併完成: 配對成功 {matches_count} 場 -> 展開為 {len(merged_data)} 筆數據")
        return pd.DataFrame(merged_data).sort_values('Date')

    except Exception as e:
        print(f"❌ 資料讀取錯誤: {e}")
        return pd.DataFrame()

def simulate_strategies(df):
    """
    模擬 10 大策略的損益
    """
    strategies = {
        '🟢 基礎 (EV>0)': df[df['EV'] > 0].copy(),
        '🛡️ 穩健保本 (Prob>65%)': df[df['Prob'] > 0.65].copy(),
        '🛡️ 穩健過濾 (Prob>60%, Odds>1.3)': df[(df['Prob'] > 0.60) & (df['Odds'] > 1.3)].copy(),
        '🏰 鐵桶防禦 (Prob>75%)': df[df['Prob'] > 0.75].copy(),
        '🏹 狙擊冷門 (Odds>1.75, EV>5%)': df[(df['Odds'] >= 1.75) & (df['EV'] > 0.05)].copy(),
        '💎 極高價值 (EV>15%)': df[df['EV'] > 0.15].copy(),
        '⚖️ 平衡型 (Prob>55%, Odds>1.6)': df[(df['Prob'] > 0.55) & (df['Odds'] > 1.6)].copy(),
        '🎯 精準打擊 (Prob>65%, EV>5%)': df[(df['Prob'] > 0.65) & (df['EV'] > 0.05)].copy(),
        '🏠 主場優勢 (Home, Prob>60%)': df[(df['Is_Home'] == True) & (df['Prob'] > 0.60)].copy(),
        '🛣️ 客場殺手 (Away, EV>5%)': df[(df['Is_Home'] == False) & (df['EV'] > 0.05)].copy(),
    }
    
    results = {}
    for name, strat_df in strategies.items():
        if strat_df.empty:
            results[name] = {'df': pd.DataFrame({'Date':[], 'Cumulative_Profit':[]}), 'stats': (0, 0.0, 0.0, 0.0)}
            continue
            
        # 計算獲利 (扣除本金)
        # 贏: 賠率 - 1 (例如賠率1.8，贏了拿回1.8，扣掉本金1，淨利0.8)
        # 輸: -1
        strat_df['Profit'] = np.where(strat_df['Win'] == 1, strat_df['Odds'] - 1, -1)
        
        # 異常值過濾 (如果單場獲利超過 10u，可能是賠率資料錯誤，強制修正為 0)
        strat_df.loc[strat_df['Profit'] > 10, 'Profit'] = 0
        
        strat_df['Cumulative_Profit'] = strat_df['Profit'].cumsum()
        
        total_bets = len(strat_df)
        wins = strat_df['Win'].sum()
        roi = (strat_df['Profit'].sum() / total_bets) * 100
        results[name] = {'df': strat_df, 'stats': (total_bets, wins/total_bets, strat_df['Profit'].sum(), roi)}
        
    return results

def plot_cumulative_profit(results):
    plt.figure(figsize=(20, 12))
    colors = cm.tab10(np.linspace(0, 1, len(results)))
    sorted_results = sorted(results.items(), key=lambda x: x[1]['stats'][3], reverse=True)
    
    has_data = False
    for i, (name, data) in enumerate(sorted_results):
        df = data['df']
        if df.empty: continue
        has_data = True
        linestyle = ['-', '--', '-.', ':'][i % 4] 
        linewidth = 4.0 if i == 0 else 2.0 
        color = 'gold' if i == 0 else colors[i]
        zorder = 10 if i == 0 else 2
        
        plt.plot(df['Date'], df['Cumulative_Profit'], 
                 label=f"{name} (ROI: {data['stats'][3]:.1f}%)", 
                 linewidth=linewidth, color=color, linestyle=linestyle, alpha=0.9, zorder=zorder)
    
    if not has_data:
        plt.text(0.5, 0.5, '無足夠數據繪製圖表', ha='center', va='center', fontsize=20)

    plt.title('10大策略全明星大亂鬥 (Cumulative Profit)', fontsize=24, fontweight='bold')
    plt.xlabel('日期', fontsize=18)
    plt.ylabel('獲利 (單位: 注)', fontsize=18)
    plt.xticks(fontsize=14)
    plt.yticks(fontsize=14)
    plt.legend(bbox_to_anchor=(1.01, 1), loc='upper left', borderaxespad=0, fontsize=14)
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig('chart_cumulative_profit.png', dpi=100)
    print(f"📊 圖表已儲存: chart_cumulative_profit.png")

def export_strategy_report(results):
    report_data = []
    sorted_results = sorted(results.items(), key=lambda x: x[1]['stats'][3], reverse=True)
    
    for name, data in sorted_results:
        count, win_rate, profit, roi = data['stats']
        report_data.append({
            '策略名稱': name,
            '場次': count,
            '勝率': f"{win_rate:.1%}",
            '總獲利 (單位)': f"{profit:+.2f}u",
            'ROI': f"{roi:+.1f}%"
        })
        
    df_report = pd.DataFrame(report_data)
    df_report.to_csv("Strategy_Performance_Report.csv", index=False, encoding='utf-8-sig')
    print(f"✅ 策略績效報告已匯出: Strategy_Performance_Report.csv")
    
    print("\n" + "="*80)
    print(f"{'策略名稱':<35} | {'場次':<6} | {'勝率':<6} | {'總獲利':<10} | {'ROI':<6}")
    print("-" * 80)
    for item in report_data:
        print(f"{item['策略名稱']:<35} | {item['場次']:<6} | {item['勝率']:<6} | {item['總獲利 (單位)']:<10} | {item['ROI']:<6}")
    print("="*80 + "\n")

def main():
    pred_file = "predictions_2026_full_report.csv"
    odds_file = "odds_2026_full_season.csv"
    
    if not os.path.exists(pred_file) or not os.path.exists(odds_file):
        print("❌ 找不到輸入檔案。")
        return
        
    df = load_and_merge_data(pred_file, odds_file)
    if df.empty: return

    results = simulate_strategies(df)
    plot_cumulative_profit(results)
    export_strategy_report(results)

if __name__ == "__main__":
    main()
