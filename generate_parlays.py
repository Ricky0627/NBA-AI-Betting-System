import pandas as pd
import numpy as np
import os
from itertools import combinations

def generate_parlays():
    print("--- 🔗 串關生成器 (v4.0 - 嚴格同日修正版) ---")
    
    input_file = "Final_Betting_Signals.csv"
    if not os.path.exists(input_file):
        print(f"❌ 找不到 {input_file}，無法生成串關建議。")
        return

    df = pd.read_csv(input_file)
    
    # 日期處理 (確保只有日期部分，去除時間)
    col_date = 'date' if 'date' in df.columns else 'Date'
    df[col_date] = pd.to_datetime(df[col_date]).dt.date
    
    # 1. 篩選候選名單
    # 條件：EV > 0 (正期望值) 或 勝率 > 65% (高勝率)
    def is_candidate(row):
        ev = float(row.get('EV', 0))
        prob = float(row.get('Prob', 0))
        if ev > 0: return True
        if prob > 0.65: return True
        return False

    df['Is_Candidate'] = df.apply(is_candidate, axis=1)
    candidates = df[df['Is_Candidate']].copy()
    
    # 取得所有唯一的日期，並由新到舊排序
    unique_dates = sorted(candidates[col_date].unique(), reverse=True)
    all_parlays = []

    print(f"正在分析 {len(unique_dates)} 個比賽日的最佳組合...")

    # --- 關鍵修正：針對「每一天」獨立進行配對 ---
    for d in unique_dates:
        # 鎖定這一天的比賽
        daily_games = candidates[candidates[col_date] == d].copy()
        
        # 至少要 2 場才能串
        if len(daily_games) < 2: 
            # print(f"  日期 {d}: 符合條件場次不足 ({len(daily_games)} 場)，跳過。")
            continue
            
        # 產生所有 2 串 1 組合 (C取2)
        combs = list(combinations(daily_games.iterrows(), 2))
        
        # 暫存當日的組合，稍後排序
        daily_parlays = []
        
        for (idx1, row1), (idx2, row2) in combs:
            # 防呆：同一場比賽的主客隊不能串 (Team_Abbr vs Opp_Abbr)
            if row1['Team_Abbr'] == row2['Opp_Abbr']: continue

            # 計算串關數據
            comb_odd = row1['Odds_Team'] * row2['Odds_Team']
            comb_prob = row1['Prob'] * row2['Prob']
            comb_ev = (comb_prob * comb_odd) - 1
            
            # 評分機制 (Score)
            score = (comb_ev * 0.7) + (comb_prob * 0.3)
            
            # 定義類型
            p_type = "普通串關"
            if row1['Prob'] > 0.7 and row2['Prob'] > 0.7: p_type = "🛡️ 雙穩膽"
            elif comb_ev > 0.3: p_type = "💰 高價值"
            elif "ROI King" in str(row1['Signal']) and "ROI King" in str(row2['Signal']): p_type = "💎 黃金串"
            elif "ROI King" in str(row1['Signal']) or "ROI King" in str(row2['Signal']): p_type = "✨ 強力串"
            
            daily_parlays.append({
                'Date': d,
                'Type': p_type,
                'Score': round(score, 4),
                'Team_1': f"{row1['Team_Abbr']} ({row1['Odds_Team']})",
                'Team_2': f"{row2['Team_Abbr']} ({row2['Odds_Team']})",
                'P1': row1['Team_Abbr'], 
                'P2': row2['Team_Abbr'],
                'Combined_Odds': round(comb_odd, 2),
                'Combined_Prob': round(comb_prob * 100, 1),
                'Combined_EV': round(comb_ev, 2)
            })
            
        # 對當日的組合進行排序 (分數高 -> 低)
        daily_parlays.sort(key=lambda x: x['Score'], reverse=True)
        
        # 只取當日前 5 名加入總表
        all_parlays.extend(daily_parlays[:5])

    # 4. 輸出結果
    if all_parlays:
        df_out = pd.DataFrame(all_parlays)
        output_file = "Daily_Parlay_Recommendations.csv"
        df_out.to_csv(output_file, index=False, encoding='utf-8-sig')
        
        print(f"✅ 已生成串關排行榜: {output_file}")
        print(f"   共列出 {len(df_out)} 組建議 (嚴格同日配對)")
        
        # 預覽最新一天的第一名
        if not df_out.empty:
            latest = df_out.iloc[0]
            print(f"\n📢 [{latest['Date']}] 最佳推薦:")
            print(f"   {latest['P1']} + {latest['P2']} (賠率 {latest['Combined_Odds']})")
            
    else:
        print("⚠️ 無法生成串關建議 (可能因為每天符合條件的比賽都不足 2 場)。")
        # 產生空檔防止報錯
        cols = ['Date','Type','Team_1','Team_2','P1','P2','Combined_Odds','Combined_Prob','Combined_EV']
        pd.DataFrame(columns=cols).to_csv("Daily_Parlay_Recommendations.csv", index=False)

if __name__ == "__main__":
    generate_parlays()