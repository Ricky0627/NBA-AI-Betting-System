import pandas as pd
import numpy as np
import os

def generate_parlays():
    print("--- 🔗 串關生成器 ---")
    input_file = "Final_Betting_Signals.csv"
    if not os.path.exists(input_file): print("找不到訊號表"); return

    df = pd.read_csv(input_file)
    date_col = 'date' if 'date' in df.columns else 'Date'
    df[date_col] = pd.to_datetime(df[date_col])
    
    df = df[df['Signal'].str.contains("BET") | (df['Prob'] > 0.75)]
    unique_dates = sorted(df[date_col].unique(), reverse=True)
    all_parlays = []

    for d in unique_dates:
        games = df[df[date_col] == d].copy()
        if len(games) < 2: continue
        
        games['Rank'] = 0
        for i, row in games.iterrows():
            if "ROI King" in str(row['Signal']): games.at[i, 'Rank'] = 3
            elif "BET" in str(row['Signal']): games.at[i, 'Rank'] = 2
            elif row['Prob'] > 0.75: games.at[i, 'Rank'] = 1
            
        games = games.sort_values(by=['Rank', 'Prob'], ascending=[False, False])
        top2 = games.head(2)
        
        if len(top2) == 2:
            p1, p2 = top2.iloc[0], top2.iloc[1]
            comb_odd = p1['Odds_Team'] * p2['Odds_Team']
            all_parlays.append({
                'Date': d.strftime('%Y-%m-%d'),
                'Type': '🛡️ 穩健二串一',
                'P1': f"{p1['Team_Abbr']}", 'P2': f"{p2['Team_Abbr']}",
                'Odds': round(comb_odd, 2)
            })

    pd.DataFrame(all_parlays).to_csv("Daily_Parlay_Recommendations.csv", index=False, encoding='utf-8-sig')
    print("✅ 生成串關表: Daily_Parlay_Recommendations.csv")

if __name__ == "__main__":
    generate_parlays()