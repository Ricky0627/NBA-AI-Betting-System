import pandas as pd
import numpy as np
import os
import glob
from itertools import combinations
import re
import datetime

# ==========================================
# 設定區
# ==========================================
PROB_GRID = [0.55, 0.60, 0.65]
EV_GRID = [0.0, 0.05, 0.10]
MIN_TRAIN_GAMES = 50 

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

def load_data(hist_pred, hist_odds):
    if not os.path.exists(hist_pred) or not os.path.exists(hist_odds):
        print("❌ 找不到歷史檔案")
        return None

    print(f"📚 讀取歷史檔案: {hist_pred} + {hist_odds}")
    df_p = pd.read_csv(hist_pred)
    df_o = pd.read_csv(hist_odds)
    
    df_p['Date'] = pd.to_datetime(df_p['date']).dt.strftime('%Y-%m-%d')
    df_o['Date'] = pd.to_datetime(df_o['Date']).dt.strftime('%Y-%m-%d')

    odds_map = {}
    for _, row in df_o.iterrows():
        d = row['Date']
        h = normalize_team(row['Home_Abbr'])
        a = normalize_team(row['Away_Abbr'])
        odds_map[f"{d}_{h}"] = row['Odds_Home']
        odds_map[f"{d}_{a}"] = row['Odds_Away']

    merged = []
    for _, row in df_p.iterrows():
        d = row['Date']
        team = normalize_team(row['Team_Abbr']) if 'Team_Abbr' in row else normalize_team(row['Home'])
        opp = normalize_team(row['Opp_Abbr']) if 'Opp_Abbr' in row else normalize_team(row['Away'])
        
        is_home = False
        if 'Home' in row and team == normalize_team(row['Home']): is_home = True
        
        prob = row['Win_Prob'] if 'Win_Prob' in row else row['Home_Win_Prob']
        if not is_home and 'Home_Win_Prob' in row: prob = 1.0 - row['Home_Win_Prob']
        
        odds = odds_map.get(f"{d}_{team}", 0.0)
        
        if odds > 1.0:
            ev = (prob * odds) - 1
            win = row['Win'] if 'Win' in row else 0
            merged.append({
                'Date': d, 'Team': team, 'Opp': opp, 'Prob': prob, 'Odds': odds, 'EV': ev, 'Win': win, 'Is_Home': is_home
            })
            
    print(f"✅ 歷史數據配對成功: {len(merged)} 場")
    return pd.DataFrame(merged).sort_values('Date')

def find_best_params_on_history(df_train):
    if len(df_train) < MIN_TRAIN_GAMES: return (0.55, 0.0) 

    best_roi = -999
    best_params = (0.55, 0.0)

    for p in PROB_GRID:
        for e in EV_GRID:
            candidates = df_train[(df_train['Prob'] >= p) & (df_train['EV'] >= e)]
            if len(candidates) < 10: continue

            profit = (candidates['Odds'] - 1) * candidates['Win'] - (1 - candidates['Win'])
            roi = profit.mean() * 100

            if roi > best_roi:
                best_roi = roi
                best_params = (p, e)
    return best_params

def get_parlay_combinations(candidates, strategy_name, top_n=1):
    if len(candidates) < 2: return []
    
    combs = list(combinations(pd.DataFrame(candidates).iterrows(), 2))
    parlays = []
    
    for _, (i, r1), (j, r2) in [(0, *c) for c in combs]:
        if r1['Team'] == r2['Opp']: continue 
        
        comb_odds = r1['Odds'] * r2['Odds']
        comb_prob = r1['Prob'] * r2['Prob']
        comb_ev = (comb_prob * comb_odds) - 1
        
        parlays.append({
            'Type': strategy_name,
            'Team_1': r1['Team'], 
            'Team_2': r2['Team'],
            'Combined_Odds': round(comb_odds, 2),
            'Combined_EV': round(comb_ev, 2),
            'Score': comb_ev 
        })
        
    parlays.sort(key=lambda x: x['Score'], reverse=True)
    return parlays[:top_n]

def save_empty_result():
    """當無推薦時，儲存一個帶有標題的空檔，避免 Dashboard 報錯"""
    pd.DataFrame(columns=['Type', 'Team_1', 'Team_2', 'Combined_Odds', 'Combined_EV']).to_csv("Daily_Parlay_Recommendations.csv", index=False, encoding='utf-8-sig')
    print("⚠️ 已生成空的推薦檔 (今日無符合條件的比賽)")

def generate_today_ranking(target_date, pred_file, master_odds_file, df_history):
    print(f"\n🚀 正在生成今日 ({target_date}) 的全策略推薦...")
    
    df_p = pd.read_csv(pred_file)
    df_o = pd.read_csv(master_odds_file)
    
    # 篩選今日賠率
    df_today_odds = df_o[df_o['Date'] == target_date]
    if df_today_odds.empty:
        print(f"⚠️ 在主賠率檔中找不到今日 ({target_date}) 的賠率。")
        save_empty_result()
        return

    today_games = []
    for _, row in df_p.iterrows():
        h = normalize_team(row['Home'])
        a = normalize_team(row['Away'])
        
        match = df_today_odds[
            ((df_today_odds['Home_Abbr']==h) & (df_today_odds['Away_Abbr']==a)) | 
            ((df_today_odds['Home_Abbr']==a) & (df_today_odds['Away_Abbr']==h))
        ]
        if match.empty: continue
        
        oh = float(match.iloc[0]['Odds_Home'])
        oa = float(match.iloc[0]['Odds_Away'])
        ph = float(row['Home_Win_Prob'])
        pa = 1.0 - ph
        
        today_games.append({'Team': h, 'Opp': a, 'Prob': ph, 'Odds': oh, 'EV': (ph*oh)-1, 'Is_Home': True})
        today_games.append({'Team': a, 'Opp': h, 'Prob': pa, 'Odds': oa, 'EV': (pa*oa)-1, 'Is_Home': False})
    
    if len(today_games) < 2:
        print("⚠️ 今日有效場次不足，無法串關。")
        save_empty_result()
        return

    # === 10大策略執行區 ===
    valid_history = df_history[df_history['Date'] < target_date]
    opt_prob, opt_ev = find_best_params_on_history(valid_history)
    print(f"   🎯 AI 建議參數: 勝率 > {opt_prob:.2f}, EV > {opt_ev:.2f}")
    
    # 1. 👑 AI 動態黃金
    cand_ai = [g for g in today_games if g['Prob'] >= opt_prob and g['EV'] >= opt_ev]
    
    # 2. 🟢 基礎
    cand_base = [g for g in today_games if g['EV'] > 0]
    
    # 3. 🛡️ 穩健保本
    cand_safe = [g for g in today_games if g['Prob'] > 0.65]
    
    # 4. 🛡️ 穩健過濾
    cand_smart = [g for g in today_games if g['Prob'] > 0.60 and g['Odds'] > 1.3]
    
    # 5. 🏹 狙擊冷門
    cand_underdog = [g for g in today_games if g['Odds'] >= 1.75 and g['EV'] >= 0.05]
    
    # 6. ⚖️ 平衡型
    cand_balance = [g for g in today_games if g['Prob'] > 0.55 and g['Odds'] > 1.6]
    
    # 7. 🏠 主場優勢
    cand_home = [g for g in today_games if g['Is_Home'] and g['Prob'] > 0.60]
    
    # 8. 🛣️ 客場殺手
    cand_road = [g for g in today_games if not g['Is_Home'] and g['EV'] > 0.05]
    
    # 9. 💎 極高價值
    cand_value = [g for g in today_games if g['EV'] > 0.15]
    
    # 10. 🎯 精準打擊
    cand_precise = [g for g in today_games if g['Prob'] > 0.65 and g['EV'] > 0.05]

    # 組合所有策略的結果 (每個策略取 Top 1-2)
    all_recs = []
    all_recs.extend(get_parlay_combinations(cand_ai, "👑 AI動態黃金", 2))
    all_recs.extend(get_parlay_combinations(cand_balance, "⚖️ 平衡型", 2)) # 冠軍多取一點
    all_recs.extend(get_parlay_combinations(cand_smart, "🛡️ 穩健過濾", 1))
    all_recs.extend(get_parlay_combinations(cand_precise, "🎯 精準打擊", 1))
    all_recs.extend(get_parlay_combinations(cand_home, "🏠 主場優勢", 1))
    all_recs.extend(get_parlay_combinations(cand_underdog, "🏹 狙擊冷門", 1))
    all_recs.extend(get_parlay_combinations(cand_road, "🛣️ 客場殺手", 1))
    # 其他策略 (基礎、極高價值、保本) 通常會被上面涵蓋，如果不夠再加

    if not all_recs:
        print("⚠️ 經過策略篩選後，今日無推薦組合。")
        save_empty_result()
        return

    # 去重：如果重複，保留優先級最高的標籤
    # 優先級：AI > 平衡 > 穩健 > 精準 > 其他
    priority = {
        "👑 AI動態黃金": 10,
        "⚖️ 平衡型": 9,
        "🛡️ 穩健過濾": 8,
        "🎯 精準打擊": 7
    }
    
    unique_recs = {}
    for rec in all_recs:
        teams = tuple(sorted([rec['Team_1'], rec['Team_2']]))
        current_prio = priority.get(rec['Type'], 0)
        
        if teams not in unique_recs:
            unique_recs[teams] = rec
        else:
            existing_prio = priority.get(unique_recs[teams]['Type'], 0)
            if current_prio > existing_prio:
                unique_recs[teams] = rec # 覆蓋為更高優先級的標籤
    
    final_list = list(unique_recs.values())
    final_list.sort(key=lambda x: x['Combined_EV'], reverse=True)
    
    df_rank = pd.DataFrame(final_list)
    
    print("\n📋 今日全策略推薦:")
    print("-" * 75)
    print(f"{'策略類型':<15} | {'組合':<20} | {'賠率':<6} | {'EV':<6}")
    print("-" * 75)
    
    for _, r in df_rank.iterrows():
        print(f"{r['Type']:<15} | {r['Team_1']}+{r['Team_2']:<10} | {r['Combined_Odds']:.2f}   | {r['Combined_EV']:+.2f}")
        
    df_rank.to_csv("Daily_Parlay_Recommendations.csv", index=False, encoding='utf-8-sig')
    print("\n✅ 結果已儲存: Daily_Parlay_Recommendations.csv")

def main():
    hist_pred = "predictions_2026_full_report.csv"
    hist_odds = "odds_2026_full_season.csv"
    
    if os.path.exists(hist_pred) and os.path.exists(hist_odds):
        df_full = load_data(hist_pred, hist_odds)
        if df_full is not None and not df_full.empty:
            
            pred_path_pattern = os.path.join("predictions", "predictions_*.csv")
            files = glob.glob(pred_path_pattern)
            files = [f for f in files if "full_" not in f]
            files.sort(key=lambda x: os.path.getctime(x), reverse=True) 
            
            if files:
                today_pred = files[0]
                match = re.search(r"predictions_(\d{4}-\d{2}-\d{2})\.csv", today_pred)
                if match:
                    date_str = match.group(1)
                    generate_today_ranking(date_str, today_pred, hist_odds, df_full)
                else:
                    print(f"❌ 無法從檔名解析日期: {today_pred}")
            else:
                print("❌ 找不到今日預測檔")
    else:
        print("⚠️ 缺少歷史數據檔")

if __name__ == "__main__":
    main()