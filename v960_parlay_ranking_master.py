import pandas as pd
import numpy as np
import os
import glob
from itertools import combinations
import re

# ==========================================
# 設定區
# ==========================================
# 這是我們從歷史回測中發現的「黃金標準」，用來標記強烈推薦的單
# 但程式會列出所有 EV > 0 的組合供您參考
GOLDEN_THRESHOLD_PROB = 0.60
GOLDEN_THRESHOLD_EV = 0.05

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

def find_latest_pair():
    """尋找日期匹配的預測檔與賠率檔"""
    pred_path_pattern = os.path.join("predictions", "predictions_*.csv")
    pred_files = glob.glob(pred_path_pattern)
    # 排除 full_season / full_report
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
    # 依日期最新排序
    pairs.sort(key=lambda x: x[0], reverse=True)
    return pairs[0]

def load_history_data(hist_pred, hist_odds):
    """讀取歷史數據用於驗證策略"""
    print(f"📚 讀取歷史數據: {hist_pred} + {hist_odds}")
    df_p = pd.read_csv(hist_pred)
    df_o = pd.read_csv(hist_odds)
    
    # 建立賠率表
    odds_map = {}
    for _, row in df_o.iterrows():
        d = pd.to_datetime(row['Date']).strftime('%Y-%m-%d')
        h = normalize_team(row['Home_Abbr'])
        a = normalize_team(row['Away_Abbr'])
        odds_map[f"{d}_{h}"] = row['Odds_Home']
        odds_map[f"{d}_{a}"] = row['Odds_Away']

    merged = []
    for _, row in df_p.iterrows():
        d = pd.to_datetime(row['date']).strftime('%Y-%m-%d')
        # 欄位相容性處理
        team = normalize_team(row['Team_Abbr']) if 'Team_Abbr' in row else normalize_team(row['Home'])
        opp = normalize_team(row['Opp_Abbr']) if 'Opp_Abbr' in row else normalize_team(row['Away'])
        
        # 判斷是否為主場
        is_home = False
        if 'Home' in row and team == normalize_team(row['Home']): is_home = True
        
        # 獲取勝率
        prob = row['Win_Prob'] if 'Win_Prob' in row else row['Home_Win_Prob']
        if not is_home and 'Home_Win_Prob' in row: prob = 1.0 - row['Home_Win_Prob']
        
        # 獲取賠率
        odds = odds_map.get(f"{d}_{team}", 0.0)
        
        if odds > 1.0:
            ev = (prob * odds) - 1
            win = row['Win'] if 'Win' in row else 0
            merged.append({'Date': d, 'Team': team, 'Opp': opp, 'Prob': prob, 'Odds': odds, 'EV': ev, 'Win': win})
            
    return pd.DataFrame(merged)

def optimize_and_get_params(df_hist):
    """
    簡單回測：確認當前最佳參數 (主要用於確認趨勢)
    """
    print("\n🔍 分析歷史最佳策略 (基於 ROI)...")
    best_roi = -100
    best_params = (0.55, 0.0) # 預設
    
    # 網格搜索
    for min_p in [0.55, 0.60, 0.65]:
        for min_e in [0.0, 0.05, 0.10]:
            # 篩選
            candidates = df_hist[(df_hist['Prob'] >= min_p) & (df_hist['EV'] >= min_e)]
            dates = candidates['Date'].unique()
            
            balance = 0
            bets = 0
            
            # 模擬每日下注前 2 名
            for d in dates:
                daily = candidates[candidates['Date'] == d]
                if len(daily) < 2: continue
                
                combs = list(combinations(daily.iterrows(), 2))
                parlays = []
                for _, (i, r1), (j, r2) in [(0, *c) for c in combs]:
                    if r1['Opp'] == r2['Team']: continue
                    cp = r1['Prob'] * r2['Prob']
                    co = r1['Odds'] * r2['Odds']
                    cev = (cp * co) - 1
                    is_win = 1 if (r1['Win']==1 and r2['Win']==1) else 0
                    parlays.append({'EV': cev, 'Odds': co, 'Win': is_win})
                
                # 排序取前 2
                parlays.sort(key=lambda x: x['EV'], reverse=True)
                for p in parlays[:2]:
                    bets += 1
                    if p['Win']: balance += (p['Odds'] - 1)
                    else: balance -= 1
            
            if bets > 10:
                roi = (balance / bets) * 100
                if roi > best_roi:
                    best_roi = roi
                    best_params = (min_p, min_e)

    print(f"🏆 歷史回測最佳參數: 勝率 > {best_params[0]:.2f}, EV > {best_params[1]:.2f} (ROI: {best_roi:.1f}%)")
    return best_params

def generate_todays_ranking(date_str, pred_file, odds_file, opt_params):
    """生成並排名今日所有串關"""
    print(f"\n🚀 正在生成今日 ({date_str}) 串關排名...")
    
    df_p = pd.read_csv(pred_file)
    df_o = pd.read_csv(odds_file)
    
    # 1. 建立候選池 (只要 EV > 0 都有資格進入排名，不強制過濾，但會標記)
    candidates = []
    
    for _, row in df_p.iterrows():
        h = normalize_team(row['Home'])
        a = normalize_team(row['Away'])
        prob_h = float(row['Home_Win_Prob'])
        prob_a = 1.0 - prob_h
        
        # 找賠率
        match = df_o[((df_o['Home_Abbr']==h) & (df_o['Away_Abbr']==a)) | ((df_o['Home_Abbr']==a) & (df_o['Away_Abbr']==h))]
        if match.empty: continue
        
        odd_h = float(match.iloc[0]['Odds_Home'])
        odd_a = float(match.iloc[0]['Odds_Away'])
        
        # 主隊
        ev_h = (prob_h * odd_h) - 1
        if ev_h > 0: # 基礎門檻
            candidates.append({'Team': h, 'Opp': a, 'Prob': prob_h, 'Odds': odd_h, 'EV': ev_h})
        
        # 客隊
        ev_a = (prob_a * odd_a) - 1
        if ev_a > 0: # 基礎門檻
            candidates.append({'Team': a, 'Opp': h, 'Prob': prob_a, 'Odds': odd_a, 'EV': ev_a})
            
    if len(candidates) < 2:
        print("⚠️ 今日正期望值 (EV>0) 場次不足 2 場，無法串關。")
        return

    # 2. 排列組合 & 評分
    df_cand = pd.DataFrame(candidates)
    combs = list(combinations(df_cand.iterrows(), 2))
    
    ranked_parlays = []
    
    opt_prob_th, opt_ev_th = opt_params
    
    for (i, r1), (j, r2) in combs:
        if r1['Team'] == r2['Opp']: continue # 同場避開
        
        comb_prob = r1['Prob'] * r2['Prob']
        comb_odds = r1['Odds'] * r2['Odds']
        comb_ev = (comb_prob * comb_odds) - 1
        
        # 評級邏輯
        # 黃金級: 符合歷史最優參數
        # 白銀級: 符合基礎 EV > 0
        
        grade = "普通"
        is_golden = False
        
        # 檢查單場是否都符合最優參數
        c1_ok = (r1['Prob'] >= opt_prob_th and r1['EV'] >= opt_ev_th)
        c2_ok = (r2['Prob'] >= opt_prob_th and r2['EV'] >= opt_ev_th)
        
        if c1_ok and c2_ok:
            grade = "🌟 黃金組合 (強烈推薦)"
            is_golden = True
        elif comb_ev > 0.15:
            grade = "💎 高價值 (High EV)"
        elif comb_prob > 0.5:
            grade = "✅ 穩健 (Solid)"
            
        ranked_parlays.append({
            'Grade': grade,
            'Team_1': r1['Team'],
            'Team_2': r2['Team'],
            'Comb_Odds': comb_odds,
            'Comb_Prob': comb_prob,
            'Comb_EV': comb_ev,
            'Is_Golden': is_golden
        })
        
    # 3. 排序 (EV 優先，這是歷史回測告訴我們的真理)
    df_rank = pd.DataFrame(ranked_parlays)
    df_rank = df_rank.sort_values('Comb_EV', ascending=False)
    
    # 4. 輸出顯示
    print(f"\n📋 今日串關排行榜 (共 {len(df_rank)} 組，依 EV 排序):")
    print("=" * 90)
    print(f"{'評級':<15} | {'組合':<20} | {'總賠率':<8} | {'總勝率':<8} | {'總EV':<8}")
    print("-" * 90)
    
    for i, row in df_rank.head(10).iterrows(): # 顯示前 10 名
        combo_str = f"{row['Team_1']} + {row['Team_2']}"
        print(f"{row['Grade']:<15} | {combo_str:<20} | {row['Comb_Odds']:.2f}     | {row['Comb_Prob']:.1%}     | {row['Comb_EV']:+.2f}")
        
    # 儲存
    # 轉換欄位以配合 Dashboard
    df_save = df_rank.head(5).copy()
    df_save = df_save.rename(columns={
        'Grade': 'Type', 
        'Comb_Odds': 'Combined_Odds', 
        'Comb_EV': 'Combined_EV'
    })
    # 移除 Dashboard 不用的欄位
    output_file = "Daily_Parlay_Recommendations.csv"
    df_save[['Type', 'Team_1', 'Team_2', 'Combined_Odds', 'Combined_EV']].to_csv(output_file, index=False, encoding='utf-8-sig')
    print(f"\n✅ 已將前 5 名寫入 {output_file} (供 Dashboard 使用)")

def main():
    # 1. 讀取歷史並優化
    hist_pred = "predictions_2026_full_report.csv"
    hist_odds = "odds_2026_full_season.csv"
    
    opt_params = (0.55, 0.0) # 預設安全值
    
    if os.path.exists(hist_pred) and os.path.exists(hist_odds):
        df_hist = load_history_data(hist_pred, hist_odds)
        if not df_hist.empty:
            opt_params = optimize_and_get_params(df_hist)
    else:
        print("⚠️ 找不到歷史檔案，使用預設參數。")
        
    # 2. 針對今日比賽生成排名
    date_str, pred_f, odds_f = find_latest_pair()
    if date_str:
        generate_todays_ranking(date_str, pred_f, odds_f, opt_params)
    else:
        print("❌ 找不到今日完整的預測與賠率檔，無法生成排名。")

if __name__ == "__main__":
    main()