import proxy_patch
import requests
from bs4 import BeautifulSoup
import pandas as pd
import numpy as np
import time
import os
import re

def get_scores(date_str):
    try:
        dt = pd.to_datetime(date_str)
        url = f"https://www.basketball-reference.com/boxscores/?month={dt.month}&day={dt.day}&year={dt.year}"
        headers = {'User-Agent': 'Mozilla/5.0'}
        res = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(res.content, 'lxml')
        scores = {}
        for sum_div in soup.find_all('div', class_='game_summary'):
            teams = sum_div.find_all('tr')
            if len(teams) < 2: continue
            try:
                t1 = teams[0].find('a')['href'].split('/')[2]
                t2 = teams[1].find('a')['href'].split('/')[2]
                s1 = int(teams[0].find('td', class_='right').text)
                s2 = int(teams[1].find('td', class_='right').text)
                scores[tuple(sorted((t1, t2)))] = {t1: s1, t2: s2}
            except: continue
        return scores
    except: return {}

def grade_report():
    print("--- 📝 結算機器人 v3 (適配 Signal 表) ---")
    target_file = "Final_Betting_Signals.csv"
    if not os.path.exists(target_file): print("找不到訊號表"); return

    df = pd.read_csv(target_file)
    date_col = 'date' if 'date' in df.columns else 'Date'
    
    if 'Outcome' not in df.columns: df['Outcome'] = "-"
    
    # BBR 隊名轉換 (BKN->BRK, PHX->PHO, CHA->CHO)
    map_bbr = {'BKN': 'BRK', 'PHX': 'PHO', 'CHA': 'CHO'}
    
    for d in df[date_col].unique():
        # 如果當天還有沒結算的比賽
        day_mask = (df[date_col] == d)
        if df[day_mask]['Outcome'].str.contains("WIN|LOSS").all(): continue
        
        print(f"查詢比分: {d} ...")
        scores = get_scores(d)
        if not scores: continue
        
        for i, row in df[day_mask].iterrows():
            if row['Outcome'] in ["WIN", "LOSS"]: continue
            
            # 轉換隊名以匹配 BBR
            team = map_bbr.get(row['Team_Abbr'], row['Team_Abbr'])
            opp = map_bbr.get(row['Opp_Abbr'], row['Opp_Abbr'])
            
            key = tuple(sorted((team, opp)))
            if key in scores:
                s_team = scores[key].get(team, 0)
                s_opp = scores[key].get(opp, 0)
                
                signal = str(row['Signal'])
                if "BET" not in signal: 
                    df.at[i, 'Outcome'] = "PASS"
                    continue
                
                is_win = False
                # 這裡 Signal 只有 BET HOME/AWAY，但這個表是以 Team_Abbr 為主視角
                # 我們的生成器有考慮 Is_Home，所以如果 Signal 是 BET HOME 且 Team 是主場 -> 買 Team 贏
                
                bet_on_team = False
                if "BET HOME" in signal and row['Is_Home']: bet_on_team = True
                if "BET AWAY" in signal and not row['Is_Home']: bet_on_team = True
                # 注意：如果 Signal 是 BET AWAY 但 Team 是主場，代表買對手，這裡簡化邏輯：
                # Final_Signals 裡的 Signal 是根據 Team_Abbr 的視角產生的嗎？
                # 回頭看 generate_best_signals.py -> Signal 是 "BET HOME" / "BET AWAY"
                # 是基於比賽的主客場。
                
                # 修正判定邏輯：
                target_winner = "HOME" if "BET HOME" in signal else "AWAY"
                actual_winner = "HOME" if (row['Is_Home'] and s_team > s_opp) or (not row['Is_Home'] and s_team < s_opp) else "AWAY"
                
                res = "WIN" if target_winner == actual_winner else "LOSS"
                df.at[i, 'Outcome'] = res
                print(f"  {row['Team_Abbr']} vs {row['Opp_Abbr']} ({s_team}-{s_opp}) -> {res}")
                
    df.to_csv("Final_Betting_Signals_Graded.csv", index=False, encoding='utf-8-sig')
    print("✅ 結算完成: Final_Betting_Signals_Graded.csv")

if __name__ == "__main__":
    grade_report()