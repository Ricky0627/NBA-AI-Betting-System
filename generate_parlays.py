import pandas as pd
import numpy as np
import os
from itertools import product

# --- 基於 12/2 報告的參數設定 ---
# ✅ 模範生：預測準確率極高，優先作為配腳
TRUSTED_TEAMS = ['OKC', 'BRK', 'PHI', 'NOP', 'LAC'] 

# ⚠️ 搗亂者：預測失準，絕對避開 (扣分)
RISKY_TEAMS = ['CHO', 'MIL', 'ATL']

def generate_parlays():
    print("--- 🔗 串關生成器 (v4.0 - 策略+穩膽版) ---")
    print("--- 邏輯：以高 EV 策略單為主，搭配高信心穩膽 ---")
    
    input_file = "Final_Betting_Signals.csv"
    if not os.path.exists(input_file):
        print(f"❌ 找不到 {input_file}。")
        return

    df = pd.read_csv(input_file)
    
    # 日期處理
    col_date = 'date' if 'date' in df.columns else 'Date'
    df[col_date] = pd.to_datetime(df[col_date]).dt.date
    
    # ---------------------------------------------------------
    # 1. 定義評分函數 (尋找最佳配腳)
    # ---------------------------------------------------------
    def get_anchor_score(row):
        # 基礎分數 = 勝率
        score = float(row.get('Prob', 0)) * 100
        team = row['Team_Abbr']
        is_home = row['Is_Home']
        prob = float(row.get('Prob', 0))
        
        # A. 信心水準加權 (根據報告)
        # High (Away) 準確率 86.1% -> 大幅加分
        if not is_home and prob >= 0.60:
            score += 25 
        # High (Home) 準確率 73.9% -> 中幅加分
        elif is_home and prob >= 0.65:
            score += 10
            
        # B. 球隊特性加權 (根據報告)
        if team in TRUSTED_TEAMS:
            score += 15  # 模範生加分
        elif team in RISKY_TEAMS:
            score -= 100 # 搗亂者直接淘汰 (扣到負分)
            
        return score

    df['Anchor_Score'] = df.apply(get_anchor_score, axis=1)

    # ---------------------------------------------------------
    # 2. 分類：主角 (Strategy) 與 配角 (Anchor)
    # ---------------------------------------------------------
    # 主角：符合我們原本的高 EV 策略
    def is_main_leg(row):
        sig = str(row.get('Signal', ''))
        return "ROI King" in sig or "Value" in sig or "High EV" in sig

    df['Is_Main'] = df.apply(is_main_leg, axis=1)
    
    # 配角：勝率高，且不是搗亂者 (Anchor Score 高)
    # 這裡設定 Score > 75 分才有資格當穩膽
    df['Is_Anchor'] = df['Anchor_Score'] > 75

    unique_dates = sorted(df[col_date].unique(), reverse=True)
    all_parlays = []

    print(f"正在掃描 {len(unique_dates)} 個比賽日...")

    for d in unique_dates:
        daily_games = df[df[col_date] == d].copy()
        
        if len(daily_games) < 2: continue
        
        # 分別取出當天的主角群與配角群
        main_legs = daily_games[daily_games['Is_Main']].copy()
        anchor_legs = daily_games[daily_games['Is_Anchor']].copy()
        
        # 依分數排序，最好的配角排前面
        anchor_legs = anchor_legs.sort_values(by='Anchor_Score', ascending=False)
        
        # 產生組合
        # 邏輯：拿每一個「主角」，去配一個最好的「配角」
        # 如果當天沒有主角，則退而求其次，找兩個最好的配角互串
        
        daily_parlays = []
        used_pairs = set()

        # --- 情況 A: 有策略單 (主角 + 配角) ---
        if not main_legs.empty:
            for idx1, row1 in main_legs.iterrows():
                # 找一個不是自己的最佳配角
                for idx2, row2 in anchor_legs.iterrows():
                    # 避免同場比賽互串
                    if row1['Team_Abbr'] == row2['Opp_Abbr']: continue
                    # 避免自己串自己
                    if row1['Team_Abbr'] == row2['Team_Abbr']: continue
                    
                    # 建立組合 ID 防止重複
                    pair_id = tuple(sorted([row1['Team_Abbr'], row2['Team_Abbr']]))
                    if pair_id in used_pairs: continue
                    
                    # 計算數據
                    comb_odd = row1['Odds_Team'] * row2['Odds_Team']
                    comb_prob = row1['Prob'] * row2['Prob']
                    comb_ev = (comb_prob * comb_odd) - 1
                    
                    p_type = "🏆 策略+穩膽"
                    if row2['Team_Abbr'] in TRUSTED_TEAMS:
                        p_type += " (模範生)"
                    
                    # 這是我們最想要的組合，分數給高一點
                    sort_score = 1000 + comb_ev 
                    
                    daily_parlays.append({
                        'Date': d.strftime('%Y-%m-%d'),
                        'Type': p_type,
                        'Score': sort_score,
                        'Team_1': f"{row1['Team_Abbr']} ({row1['Odds_Team']})", # 主角
                        'Team_2': f"{row2['Team_Abbr']} ({row2['Odds_Team']})", # 配角
                        'P1': row1['Team_Abbr'], 
                        'P2': row2['Team_Abbr'],
                        'Combined_Odds': round(comb_odd, 2),
                        'Combined_Prob': round(comb_prob * 100, 1),
                        'Combined_EV': round(comb_ev, 2)
                    })
                    used_pairs.add(pair_id)
                    break # 每個主角只配一個最好的配角，避免重複太多

        # --- 情況 B: 沒策略單 (雙配角互串) ---
        # 如果上面產生的組合太少(例如0個)，我們就拿最好的兩個 Anchor 互串
        if len(daily_parlays) == 0 and len(anchor_legs) >= 2:
            row1 = anchor_legs.iloc[0]
            row2 = anchor_legs.iloc[1]
            
            if row1['Team_Abbr'] != row2['Opp_Abbr']:
                comb_odd = row1['Odds_Team'] * row2['Odds_Team']
                comb_prob = row1['Prob'] * row2['Prob']
                comb_ev = (comb_prob * comb_odd) - 1
                
                daily_parlays.append({
                    'Date': d.strftime('%Y-%m-%d'),
                    'Type': "🛡️ 雙穩膽 (無策略單)",
                    'Score': 500, # 分數比策略單低
                    'Team_1': f"{row1['Team_Abbr']} ({row1['Odds_Team']})",
                    'Team_2': f"{row2['Team_Abbr']} ({row2['Odds_Team']})",
                    'P1': row1['Team_Abbr'], 
                    'P2': row2['Team_Abbr'],
                    'Combined_Odds': round(comb_odd, 2),
                    'Combined_Prob': round(comb_prob * 100, 1),
                    'Combined_EV': round(comb_ev, 2)
                })

        # 加入總表 (每天只取前 3 名)
        daily_parlays.sort(key=lambda x: x['Score'], reverse=True)
        for p in daily_parlays[:3]:
            del p['Score']
            all_parlays.append(p)

    # 輸出
    if all_parlays:
        df_out = pd.DataFrame(all_parlays)
        df_out.to_csv("Daily_Parlay_Recommendations.csv", index=False, encoding='utf-8-sig')
        print(f"✅ 生成串關表: Daily_Parlay_Recommendations.csv (共 {len(df_out)} 筆)")
        
        # 預覽
        print(f"\n📢 最新推薦 [{df_out.iloc[0]['Date']}]:")
        top = df_out.iloc[0]
        print(f"   [{top['Type']}]")
        print(f"   {top['P1']} + {top['P2']} | 賠率: {top['Combined_Odds']} | EV: {top['Combined_EV']}")
    else:
        print("⚠️ 無法生成串關建議。")
        cols = ['Date','Type','Team_1','Team_2','P1','P2','Combined_Odds','Combined_Prob','Combined_EV']
        pd.DataFrame(columns=cols).to_csv("Daily_Parlay_Recommendations.csv", index=False)

if __name__ == "__main__":
    generate_parlays()