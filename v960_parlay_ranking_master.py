import pandas as pd
import numpy as np
import os
import glob
from itertools import combinations
import re

# ==========================================
# 設定區
# ==========================================
HIST_PRED_FILE = "predictions_2026_full_report.csv"
HIST_ODDS_FILE = "odds_2026_full_season.csv"

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

# ==========================================
# 核心邏輯：策略定義
# ==========================================
def get_active_strategies(row):
    """
    判斷單一注單符合哪些策略
    """
    prob = row['Prob']
    odds = row['Odds']
    ev = row['EV']
    is_home = row['Is_Home']
    
    strategies = []
    
    # 1. 🎯 精準打擊
    if prob > 0.65 and ev > 0.05: strategies.append('精準打擊')
    
    # 2. ⚖️ 平衡型
    if prob > 0.55 and odds > 1.6: strategies.append('平衡型')
    
    # 3. 🛡️ 穩健過濾
    if prob > 0.60 and odds > 1.3: strategies.append('穩健過濾')
    
    # 4. 🛣️ 客場殺手
    if not is_home and ev > 0.05: strategies.append('客場殺手')
    
    # 5. 💎 極高價值
    if ev > 0.15: strategies.append('極高價值')
    
    # 6. 🏹 狙擊冷門
    if odds > 1.75 and ev > 0.05: strategies.append('狙擊冷門')
    
    # 7. 🟢 基礎
    if ev > 0: strategies.append('基礎')
    
    # 8. 🛡️ 穩健保本
    if prob > 0.65: strategies.append('穩健保本')
    
    # 9. 🏠 主場優勢
    if is_home and prob > 0.60: strategies.append('主場優勢')
    
    # 10. 🏰 鐵桶防禦
    if prob > 0.75: strategies.append('鐵桶防禦')
    
    return strategies

# ==========================================
# 第一部分：歷史回測與模型訓練
# ==========================================
def load_and_process_history():
    """讀取並處理歷史資料"""
    print(f"📚 讀取歷史數據 ({HIST_PRED_FILE})...")
    if not os.path.exists(HIST_PRED_FILE) or not os.path.exists(HIST_ODDS_FILE):
        print("⚠️ 找不到歷史資料，將跳過模型訓練。")
        return pd.DataFrame()

    try:
        pred_df = pd.read_csv(HIST_PRED_FILE)
        odds_df = pd.read_csv(HIST_ODDS_FILE)
        
        pred_df['date'] = pd.to_datetime(pred_df['date'])
        odds_df['Date'] = pd.to_datetime(odds_df['Date'])
        
        # 展開賠率
        odds_home = odds_df[['Date', 'Home_Abbr', 'Odds_Home']].rename(columns={'Home_Abbr': 'Team', 'Odds_Home': 'Odds'})
        odds_home['Is_Home'] = True
        odds_away = odds_df[['Date', 'Away_Abbr', 'Odds_Away']].rename(columns={'Away_Abbr': 'Team', 'Odds_Away': 'Odds'})
        odds_away['Is_Home'] = False
        odds_long = pd.concat([odds_home, odds_away])
        
        # 展開預測
        df_home = pred_df.copy()
        df_home['Team'] = df_home['Team_Abbr']
        df_home['Is_Home'] = True
        df_home['Prob'] = df_home['Win_Prob']
        
        df_away = pred_df.copy()
        df_away['Team'] = df_away['Opp_Abbr']
        df_away['Is_Home'] = False
        df_away['Prob'] = 1.0 - df_away['Win_Prob']
        df_away['Win'] = 1 - df_away['Win']
        
        full_df = pd.concat([df_home, df_away], ignore_index=True)
        
        # 合併
        merged = pd.merge(full_df, odds_long, left_on=['date', 'Team', 'Is_Home'], right_on=['Date', 'Team', 'Is_Home'], how='inner')
        merged['EV'] = (merged['Prob'] * merged['Odds']) - 1
        merged['Game_ID'] = merged.apply(lambda x: f"{x['date'].strftime('%Y%m%d')}_{''.join(sorted([x['Team'], x['Opp_Abbr']]))}", axis=1)
        
        return merged
    except Exception as e:
        print(f"❌ 讀取歷史資料失敗: {e}")
        return pd.DataFrame()

def train_and_export_model(df):
    """
    1. 計算歷史 ROI, 勝率, 場次
    2. 匯出 Best_Strategy_Combos_Unique.csv
    3. 回傳 roi_map 供今日預測使用
    """
    if df.empty: return {}
    
    print("🧠 正在訓練策略組合模型 (計算歷史數據)...")
    
    # 標記策略
    records = df.to_dict('records')
    for r in records:
        r['Strategies'] = get_active_strategies(r)
        
    df_tagged = pd.DataFrame(records)
    daily_groups = df_tagged.groupby('date')
    
    # 統計 (S1, S2) -> {profit, wins, count}
    combo_stats = {} 
    
    for date, group in daily_groups:
        bets = group.to_dict('records')
        if len(bets) < 2: continue
        
        # 該日所有兩兩組合
        bet_pairs = list(combinations(bets, 2))
        
        for b1, b2 in bet_pairs:
            if b1['Game_ID'] == b2['Game_ID']: continue
            
            is_win = (b1['Win'] == 1 and b2['Win'] == 1)
            profit = (b1['Odds'] * b2['Odds'] - 1) if is_win else -1
            
            strats1 = b1['Strategies']
            strats2 = b2['Strategies']
            
            # 將結果歸因於所有策略組合
            for s1 in strats1:
                for s2 in strats2:
                    # 排序 key 確保 A+B = B+A
                    key = tuple(sorted([s1, s2]))
                    
                    if key not in combo_stats:
                        combo_stats[key] = {'profit': 0.0, 'wins': 0, 'count': 0}
                    
                    combo_stats[key]['profit'] += profit
                    combo_stats[key]['count'] += 1
                    if is_win:
                        combo_stats[key]['wins'] += 1
                        
    # --- 整理數據並匯出 CSV ---
    export_data = []
    roi_map = {} # 用於今日預測的快速查找表
    
    for (s1, s2), stats in combo_stats.items():
        if stats['count'] >= 10: # 門檻：至少 10 場
            roi = (stats['profit'] / stats['count']) * 100
            win_rate = (stats['wins'] / stats['count']) * 100
            
            roi_map[(s1, s2)] = roi
            
            export_data.append({
                '策略_A': s1,
                '策略_B': s2,
                'ROI': round(roi, 2),
                '勝率': round(win_rate, 2),
                '場次': stats['count']
            })
            
    df_export = pd.DataFrame(export_data)
    if not df_export.empty:
        # 去重邏輯：雖然 key 已經 sorted，但為了保險起見再次過濾
        df_export = df_export[df_export['策略_A'] <= df_export['策略_B']]
        df_export = df_export.sort_values('ROI', ascending=False)
        
        csv_name = "Best_Strategy_Combos_Unique.csv"
        df_export.to_csv(csv_name, index=False, encoding='utf-8-sig')
        print(f"✅ 策略回測報告已匯出: {csv_name}")
        
        # 顯示前 3 名
        print(f"🏆 歷史最強組合前 3 名:")
        for i, row in df_export.head(3).iterrows():
            print(f"   {row['策略_A']} + {row['策略_B']} | ROI: {row['ROI']}%")
            
    return roi_map

# ==========================================
# 第二部分：今日預測與排名
# ==========================================
def find_latest_prediction():
    """尋找最新的預測檔與賠率檔"""
    pred_files = glob.glob(os.path.join("predictions", "predictions_*.csv"))
    pred_files = [f for f in pred_files if "full_" not in f]
    
    pairs = []
    for pf in pred_files:
        match = re.search(r"predictions_(\d{4}-\d{2}-\d{2})\.csv", pf)
        if match:
            date_str = match.group(1)
            odds_file = os.path.join("odds", f"odds_for_{date_str}.csv")
            if os.path.exists(odds_file):
                pairs.append((date_str, pf, odds_file))
    
    if not pairs: return None, None, None
    pairs.sort(key=lambda x: x[0], reverse=True)
    return pairs[0]

def get_todays_bets(pred_file, odds_file):
    """讀取今日注單並標記策略"""
    df_p = pd.read_csv(pred_file)
    df_o = pd.read_csv(odds_file)
    
    candidates = []
    
    for _, row in df_p.iterrows():
        h = normalize_team(row['Home'])
        a = normalize_team(row['Away'])
        prob_h = float(row['Home_Win_Prob'])
        prob_a = 1.0 - prob_h
        
        match = df_o[((df_o['Home_Abbr']==h) & (df_o['Away_Abbr']==a)) | ((df_o['Home_Abbr']==a) & (df_o['Away_Abbr']==h))]
        if match.empty: continue
        
        odd_h = float(match.iloc[0]['Odds_Home'])
        odd_a = float(match.iloc[0]['Odds_Away'])
        
        # 主隊
        bet_h = {'Team': h, 'Opp': a, 'Is_Home': True, 'Prob': prob_h, 'Odds': odd_h, 'EV': (prob_h * odd_h) - 1}
        bet_h['Strategies'] = get_active_strategies(bet_h)
        if bet_h['Strategies']: candidates.append(bet_h)
            
        # 客隊
        bet_a = {'Team': a, 'Opp': h, 'Is_Home': False, 'Prob': prob_a, 'Odds': odd_a, 'EV': (prob_a * odd_a) - 1}
        bet_a['Strategies'] = get_active_strategies(bet_a)
        if bet_a['Strategies']: candidates.append(bet_a)
            
    return candidates

def generate_parlay_ranking(bets, roi_map):
    """基於歷史 ROI 生成今日排名"""
    print(f"\n🚀 正在生成今日串關排名...")
    
    combs = list(combinations(bets, 2))
    ranked_parlays = []
    
    for b1, b2 in combs:
        if b1['Team'] == b2['Opp']: continue
        
        # 找出這組串關的所有策略組合，取最高 ROI 者
        best_roi = -999
        best_combo_name = "一般組合"
        
        for s1 in b1['Strategies']:
            for s2 in b2['Strategies']:
                key = tuple(sorted([s1, s2]))
                roi = roi_map.get(key, -999)
                if roi > best_roi:
                    best_roi = roi
                    best_combo_name = f"{key[0]} + {key[1]}"
        
        # 若完全沒對應到歷史策略，或 ROI < 0，則不推薦 (或給低分)
        if best_roi > 0:
            comb_odds = b1['Odds'] * b2['Odds']
            comb_ev = ((b1['Prob'] * b2['Prob']) * comb_odds) - 1
            
            grade = "普通"
            if best_roi > 25: grade = "👑 鑽石級"
            elif best_roi > 15: grade = "🌟 黃金級"
            elif best_roi > 5: grade = "✅ 推薦級"
            
            ranked_parlays.append({
                'Grade': grade,
                'Strategy_Combo': best_combo_name,
                'Max_ROI': best_roi,
                'Team_1': b1['Team'],
                'Team_2': b2['Team'],
                'Combined_Odds': comb_odds,
                'Combined_EV': comb_ev
            })
            
    df_rank = pd.DataFrame(ranked_parlays)
    if not df_rank.empty:
        return df_rank.sort_values('Max_ROI', ascending=False)
    return pd.DataFrame()

def main():
    # 1. 訓練與匯出策略報表
    df_hist = load_and_process_history()
    roi_map = train_and_export_model(df_hist)
    
    if not roi_map:
        print("⚠️ 無法建立模型，請檢查歷史資料。")
        return

    # 2. 處理今日比賽
    date_str, pred_f, odds_f = find_latest_prediction()
    if not date_str:
        print("❌ 找不到今日預測檔。")
        return
        
    print(f"\n📅 分析日期: {date_str}")
    todays_bets = get_todays_bets(pred_f, odds_f)
    
    if len(todays_bets) < 2:
        print("⚠️ 今日有效注單不足 2 筆，無法串關。")
        return
        
    # 3. 生成今日排名並匯出
    df_rank = generate_parlay_ranking(todays_bets, roi_map)
    
    if df_rank.empty:
        print("⚠️ 今日沒有正 ROI 的串關組合。")
    else:
        print(f"\n📋 今日串關排行榜 (Top 10):")
        print("=" * 110)
        print(f"{'評級':<10} | {'策略組合':<25} | {'歷史ROI':<8} | {'隊伍組合':<20} | {'賠率':<6} | {'EV':<6}")
        print("-" * 110)
        
        for i, row in df_rank.head(10).iterrows():
            combo_team = f"{row['Team_1']} + {row['Team_2']}"
            print(f"{row['Grade']:<10} | {row['Strategy_Combo']:<25} | {row['Max_ROI']:>6.1f}%  | {combo_team:<20} | {row['Combined_Odds']:.2f}   | {row['Combined_EV']:+.2f}")
            
        output_file = "Daily_Parlay_Recommendations.csv"
        df_save = df_rank.head(10).copy()
        df_save = df_save.rename(columns={'Grade': 'Type'})
        df_save[['Type', 'Team_1', 'Team_2', 'Combined_Odds', 'Combined_EV', 'Strategy_Combo', 'Max_ROI']].to_csv(output_file, index=False, encoding='utf-8-sig')
        print(f"\n✅ 今日推薦已寫入 {output_file}")

if __name__ == "__main__":
    main()
