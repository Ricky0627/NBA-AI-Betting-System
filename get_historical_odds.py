import proxy_patch
import requests
from bs4 import BeautifulSoup
import pandas as pd
import numpy as np
import time
import datetime
import os

TEAM_MAP = {
    '老鷹': 'ATL', '塞爾提克': 'BOS', '塞爾提': 'BOS', '籃網': 'BRK', '黃蜂': 'CHO',
    '公牛': 'CHI', '騎士': 'CLE', '獨行俠': 'DAL', '金塊': 'DEN', '活塞': 'DET',
    '勇士': 'GSW', '火箭': 'HOU', '溜馬': 'IND', '快艇': 'LAC', '湖人': 'LAL',
    '灰熊': 'MEM', '熱火': 'MIA', '公鹿': 'MIL', '灰狼': 'MIN', '鵜鶘': 'NOP',
    '尼克': 'NYK', '雷霆': 'OKC', '魔術': 'ORL', '76人': 'PHI', '七六人': 'PHI',
    '太陽': 'PHO', '拓荒者': 'POR', '拓荒': 'POR', '國王': 'SAC', '馬刺': 'SAS',
    '暴龍': 'TOR', '爵士': 'UTA', '巫師': 'WAS'
}

def get_playsport_odds_robust(target_date_str):
    url = f"https://www.playsport.cc/gamesData/result?allianceid=3&gametime={target_date_str}"
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    try:
        response = requests.get(url, headers=headers, timeout=15)
        soup = BeautifulSoup(response.content, 'lxml')
        game_rows = soup.find_all('tr', attrs={'gameid': True})
        if not game_rows:
            main_table = soup.find('table', class_='predictgame-table')
            if main_table: game_rows = main_table.find_all('tr', attrs={'gameid': True})
        if not game_rows: return []
        
        games_dict = {}
        for row in game_rows:
            gid = row['gameid']
            if gid not in games_dict: games_dict[gid] = []
            games_dict[gid].append(row)
            
        daily_data = []
        for gid, rows in games_dict.items():
            if len(rows) < 2: continue
            r_away, r_home = rows[0], rows[1]
            
            def extract_team(row):
                td = row.find('td', class_='td-teaminfo')
                if td:
                    for link in td.find_all('a'):
                        if link.text.strip() in TEAM_MAP: return link.text.strip()
                return None

            teams = []
            td_away = r_away.find('td', class_='td-teaminfo')
            if td_away:
                teams = [l.text.strip() for l in td_away.find_all('a') if l.text.strip() in TEAM_MAP]
            
            if len(teams) >= 2: away_ch, home_ch = teams[0], teams[1]
            else: away_ch, home_ch = extract_team(r_away), extract_team(r_home)
            
            if not away_ch or not home_ch: continue

            def extract_odd(row):
                td = row.find('td', class_='td-bank-bet03')
                if not td: return np.nan
                import re
                nums = re.findall(r"[-+]?\d*\.\d+|\d+", td.text.strip())
                return float(nums[-1]) if nums else np.nan

            daily_data.append({
                'Away_Abbr': TEAM_MAP.get(away_ch, "UNK"),
                'Home_Abbr': TEAM_MAP.get(home_ch, "UNK"),
                'Odds_Away': extract_odd(r_away),
                'Odds_Home': extract_odd(r_home)
            })
        return daily_data
    except Exception as e:
        print(f"  抓取失敗 {target_date_str}: {e}")
        return []

def main():
    print("--- 🕷️ 歷史賠率總表爬蟲 ---")
    report_file = "predictions_2026_full_report.csv"
    if not os.path.exists(report_file):
        print(f"找不到 {report_file}，請先放入資料夾。"); return

    df_pred = pd.read_csv(report_file)
    date_col = 'date' if 'date' in df_pred.columns else 'Date'
    df_pred[date_col] = pd.to_datetime(df_pred[date_col])
    unique_dates = sorted(df_pred[date_col].dt.date.unique())
    
    print(f"需要抓取 {len(unique_dates)} 天的賠率...")
    all_data = []
    
    for i, us_date in enumerate(unique_dates):
        tw_date = us_date + datetime.timedelta(days=1)
        tw_str = tw_date.strftime("%Y%m%d")
        us_str = us_date.strftime("%Y-%m-%d")
        
        print(f"[{i+1}/{len(unique_dates)}] 抓取: US {us_str} ...")
        odds = get_playsport_odds_robust(tw_str)
        if odds:
            for r in odds: r['Date'] = us_str
            all_data.extend(odds)
            time.sleep(1)
            
    if all_data:
        pd.DataFrame(all_data).to_csv("odds_2026_full_season.csv", index=False, encoding='utf-8-sig')
        print("✅ 成功生成 odds_2026_full_season.csv")
    else:
        print("❌ 無資料生成")

if __name__ == "__main__":
    main()