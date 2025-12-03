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
# 滾動回測的參數網格 (Grid Search Range)
PROB_GRID = [0.55, 0.60, 0.65]
EV_GRID = [0.0, 0.05, 0.10]
MIN_TRAIN_GAMES = 50  # 至少累積多少場比賽才開始跑優化 (冷啟動期)

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

def load_data(hist_pred, hist_odds):
    """讀取並整理歷史數據"""
    if not os.path.exists(hist_pred) or not os.path.exists(hist_odds):
        return None

    df_p = pd.read_csv(hist_pred)
    df_o = pd.read_csv(hist_odds)
    
    # 統一日期格式
    df_p['Date'] = pd.to_datetime(df_p['date']).dt.strftime('%Y-%m-%d')
    df_o['Date'] = pd.to_datetime(df_o['Date']).dt.strftime('%Y-%m-%d')

    # 建立賠率表
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
            merged.append({'Date': d, 'Team': team, 'Opp': opp, 'Prob': prob, 'Odds': odds, 'EV': ev, 'Win': win})
            
    return pd.DataFrame(merged).sort_values('Date')

def find_best_params_on_history(df_train):
    """
    給定一段歷史數據，找出當時表現最好的參數 (Min_Prob, Min_EV)
    """
    if len(df_train) < MIN_TRAIN_GAMES:
        return (0.55, 0.0) # 樣本不足時的預設值

    best_roi = -999
    best_params = (0.55, 0.0)

    # 簡單網格搜索
    for p in PROB_GRID:
        for e in EV_GRID:
            # 篩選符合條件的場次
            candidates = df_train[(df_train['Prob'] >= p) & (df_train['EV'] >= e)]
            if len(candidates) < 10: continue # 樣本太少不採信

            # 模擬投注 (簡化版：只看單場表現，因為串關組合太多算太久)
            # 註：這裡我們用單場 EV 總和來近似串關潛力，因為高 EV 單場通常組成高 EV 串關
            # 若要精確模擬串關，運算量會是指數級，這裡採用啟發式優化
            
            # 計算該參數下的平均 ROI
            # 實際獲利 = (賠率 - 1) if Win else -1
            profit = (candidates['Odds'] - 1) * candidates['Win'] - (1 - candidates['Win'])
            roi = profit.mean() * 100

            if roi > best_roi:
                best_roi = roi
                best_params = (p, e)
    
    return best_params

def rolling_backtest_simulation(df_full):
    """
    滾動回測：模擬每天都用「過去」的數據來優化，然後下注「今天」
    """
    print("\n⏳ 正在執行滾動式回測 (Rolling Backtest)...")
    dates = sorted(df_full['Date'].unique())
    
    history_log = []
    cumulative_profit = 0
    total_bets = 0
    
    # 從第 10 個比賽日開始 (讓前面累積一點數據)
    start_idx = 10 
    
    for i in range(start_idx, len(dates)):
        today = dates[i]
        
        # 1. 切割數據：只準看今天以前的 (Strict Look-ahead Bias Prevention)
        train_data = df_full[df_full['Date'] < today]
        today_data = df_full[df_full['Date'] == today]
        
        # 2. 學習：找出截至昨天的最佳參數
        best_p, best_e = find_best_params_on_history(train_data)
        
        # 3. 考試：應用在今天
        candidates = today_data[(today_data['Prob'] >= best_p) & (today_data['EV'] >= best_e)]
        
        daily_profit = 0
        daily_bets = 0
        
        if len(candidates) >= 2:
            # 模擬下注今日最佳串關 (Top 2 by EV)
            combs = list(combinations(candidates.iterrows(), 2))
            parlays = []
            for _, (idx1, r1), (idx2, r2) in [(0, *c) for c in combs]:
                if r1['Opp'] == r2['Team']: continue
                cp = r1['Prob'] * r2['Prob']
                co = r1['Odds'] * r2['Odds']
                cev = (cp * co) - 1
                is_win = 1 if (r1['Win']==1 and r2['Win']==1) else 0
                parlays.append({'EV': cev, 'Odds': co, 'Win': is_win})
            
            # 依 EV 排序下前 1 注
            parlays.sort(key=lambda x: x['EV'], reverse=True)
            if parlays:
                pick = parlays[0]
                daily_bets = 1
                if pick['Win']: daily_profit = pick['Odds'] - 1
                else: daily_profit = -1
        
        cumulative_profit += daily_profit
        total_bets += daily_bets
        
        history_log.append({
            'Date': today,
            'Params': f"P>{best_p}, E>{best_e}",
            'Bets': daily_bets,
            'Profit': daily_profit,
            'CumProfit': cumulative_profit
        })
    
    # 輸出結果
    df_res = pd.DataFrame(history_log)
    print("-" * 60)
    print(f"📊 滾動回測結果 (共 {len(dates)-start_idx} 天):")
    print(f"   總下注數: {total_bets}")
    print(f"   總獲利 (Units): {cumulative_profit:.2f} u")
    roi = (cumulative_profit / total_bets * 100) if total_bets > 0 else 0
    print(f"   真實 ROI: {roi:.2f}% (這是沒有未來函數的真實數據)")
    print("-" * 60)
    return df_res

def generate_today_ranking(target_date, pred_file, odds_file, df_history):
    """
    為 run_all 準備的：生成今日排名
    """
    print(f"\n🚀 正在生成今日 ({target_date}) 的動態優化排名...")
    
    # 1. 動態優化：只用今天以前的數據
    # 確保 df_history 真的不包含今天 (雖然後面邏輯會擋，但這裡再濾一次更保險)
    valid_history = df_history[df_history['Date'] < target_date]
    
    print(f"   學習樣本: {valid_history['Date'].min()} 到 {valid_history['Date'].max()} (共 {len(valid_history)} 筆)")
    opt_prob, opt_ev = find_best_params_on_history(valid_history)
    print(f"   🎯 演算法建議今日參數: 勝率 > {opt_prob:.2f}, EV > {opt_ev:.2f}")

    # 2. 應用於今日預測
    df_p = pd.read_csv(pred_file)
    df_o = pd.read_csv(odds_file)
    
    candidates = []
    for _, row in df_p.iterrows():
        h = normalize_team(row['Home'])
        a = normalize_team(row['Away'])
        # 找賠率
        match = df_o[((df_o['Home_Abbr']==h) & (df_o['Away_Abbr']==a)) | ((df_o['Home_Abbr']==a) & (df_o['Away_Abbr']==h))]
        if match.empty: continue
        oh = float(match.iloc[0]['Odds_Home'])
        oa = float(match.iloc[0]['Odds_Away'])
        
        ph = float(row['Home_Win_Prob'])
        pa = 1.0 - ph
        
        # 放入候選 (只要 EV > 0 就放入，但在評級時會看參數)
        if (ph * oh) - 1 > 0: candidates.append({'Team': h, 'Opp': a, 'Prob': ph, 'Odds': oh, 'EV': (ph*oh)-1})
        if (pa * oa) - 1 > 0: candidates.append({'Team': a, 'Opp': h, 'Prob': pa, 'Odds': oa, 'EV': (pa*oa)-1})

    if len(candidates) < 2:
        print("⚠️ 今日有效場次不足。")
        return

    # 3. 排列與評分
    combs = list(combinations(pd.DataFrame(candidates).iterrows(), 2))
    ranked = []
    
    for _, (i, r1), (j, r2) in [(0, *c) for c in combs]:
        if r1['Team'] == r2['Opp']: continue
        
        cev = ((r1['Prob']*r2['Prob']) * (r1['Odds']*r2['Odds'])) - 1
        
        # 評級邏輯
        grade = "普通"
        is_opt = False
        
        # 是否符合動態優化參數
        if (r1['Prob'] >= opt_prob and r1['EV'] >= opt_ev and 
            r2['Prob'] >= opt_prob and r2['EV'] >= opt_ev):
            grade = "👑 動態黃金 (AI優化)"
            is_opt = True
        elif cev > 0.15:
            grade = "💎 高價值"
        elif r1['Prob']*r2['Prob'] > 0.5:
            grade = "✅ 穩健"
            
        ranked.append({
            'Type': grade,
            'Team_1': r1['Team'], 
            'Team_2': r2['Team'],
            'Combined_Odds': round(r1['Odds']*r2['Odds'], 2),
            'Combined_EV': round(cev, 2),
            'Score': cev # 預設依 EV 排序
        })

    df_rank = pd.DataFrame(ranked).sort_values('Score', ascending=False).head(10)
    
    # 顯示前 3
    print("\n📋 AI 推薦前 3 名:")
    print("-" * 60)
    for _, r in df_rank.head(3).iterrows():
        print(f"{r['Type']:<15} | {r['Team_1']}+{r['Team_2']:<10} | EV: {r['Combined_EV']:+.2f}")
        
    # 存檔
    df_rank.head(5).to_csv("Daily_Parlay_Recommendations.csv", index=False, encoding='utf-8-sig')
    print("✅ 結果已儲存 (供 Dashboard 使用)")

def main():
    # 1. 準備數據
    hist_pred = "predictions_2026_full_report.csv"
    hist_odds = "odds_2026_full_season.csv"
    
    if os.path.exists(hist_pred) and os.path.exists(hist_odds):
        df_full = load_data(hist_pred, hist_odds)
        if df_full is not None and not df_full.empty:
            
            # --- 功能 A: 滾動回測 (可選，這裡預設跑一次給你看真實數據) ---
            # rolling_backtest_simulation(df_full) 
            # (註：為了節省每日執行時間，您可以把上面這行註解掉，偶爾手動開起來跑)

            # --- 功能 B: 今日預測 ---
            # 尋找今日檔案
            files = glob.glob("predictions_*.csv")
            files = [f for f in files if "full_" not in f]
            files.sort(key=lambda x: os.path.getctime(x), reverse=True) # 找最新的
            
            if files:
                today_pred = files[0]
                match = re.search(r"predictions_(\d{4}-\d{2}-\d{2})\.csv", today_pred)
                if match:
                    date_str = match.group(1)
                    today_odds = f"odds_for_{date_str}.csv"
                    
                    if os.path.exists(today_odds):
                        generate_today_ranking(date_str, today_pred, today_odds, df_full)
                    else:
                        print("❌ 找不到今日賠率檔")
    else:
        print("⚠️ 缺少歷史數據檔，無法進行動態優化。")

if __name__ == "__main__":
    main()