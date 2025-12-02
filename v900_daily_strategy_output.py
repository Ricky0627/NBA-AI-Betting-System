import pandas as pd
import numpy as np
import os
import glob
import re
import requests
from bs4 import BeautifulSoup
import datetime
import time

# --- 1. 隊名對照表 (沿用 v501 的完整版) ---
TEAM_MAP = {
    '老鷹': 'ATL', '塞爾提克': 'BOS', '塞爾提': 'BOS', '籃網': 'BRK', '黃蜂': 'CHO',
    '公牛': 'CHI', '騎士': 'CLE', '獨行俠': 'DAL', '金塊': 'DEN', '活塞': 'DET',
    '勇士': 'GSW', '火箭': 'HOU', '溜馬': 'IND', '快艇': 'LAC', '湖人': 'LAL',
    '灰熊': 'MEM', '熱火': 'MIA', '公鹿': 'MIL', '灰狼': 'MIN', '鵜鶘': 'NOP',
    '尼克': 'NYK', '雷霆': 'OKC', '魔術': 'ORL', '76人': 'PHI', '七六人': 'PHI',
    '太陽': 'PHO', '拓荒者': 'POR', '拓荒': 'POR', '國王': 'SAC', '馬刺': 'SAS',
    '暴龍': 'TOR', '爵士': 'UTA', '巫師': 'WAS'
}

def find_latest_prediction_file():
    """尋找最新的 predictions_YYYY-MM-DD.csv"""
    files = glob.glob("predictions_*.csv")
    daily_files = [f for f in files if "full_report" not in f]
    
    if not daily_files: return None
    latest_file = max(daily_files, key=os.path.getctime)
    return latest_file

def get_playsport_odds_v501(target_date_str):
    """
    【移植自 v501】抓取 PlaySport 指定日期的賠率
    target_date_str: 'YYYYMMDD' (TW Time)
    """
    url = f"https://www.playsport.cc/gamesData/result?allianceid=3&gametime={target_date_str}"
    print(f"  🔄 [v501核心] 正在抓取: {target_date_str} (PlaySport)...")
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=15)
        soup = BeautifulSoup(response.content, 'lxml')
        
        # 1. 找到所有帶有 gameid 的行 (v501 邏輯)
        game_rows = soup.find_all('tr', attrs={'gameid': True})
        if not game_rows:
            main_table = soup.find('table', class_='predictgame-table')
            if main_table:
                game_rows = main_table.find_all('tr', attrs={'gameid': True})
        
        if not game_rows:
            print("  ⚠️  找不到比賽數據 (尚未開盤或當日無賽事)。")
            return []
            
        # 2. 根據 gameid 分組
        games_dict = {}
        for row in game_rows:
            gid = row['gameid']
            if gid not in games_dict: games_dict[gid] = []
            games_dict[gid].append(row)
            
        daily_data = []
        
        for gid, rows in games_dict.items():
            if len(rows) < 2: continue 
            
            # Row 0 = 客隊, Row 1 = 主隊
            r_away = rows[0]
            r_home = rows[1]
            
            # --- 解析隊名 ---
            def extract_team_name(row):
                td = row.find('td', class_='td-teaminfo')
                if not td: return None
                # 優先找連結
                links = td.find_all('a')
                for link in links:
                    txt = link.text.strip()
                    if txt in TEAM_MAP: return txt
                return None

            # 檢查是否兩隊都在第一行 (有時候 PlaySport 會這樣排)
            teams_in_away_row = []
            td_away = r_away.find('td', class_='td-teaminfo')
            if td_away:
                for link in td_away.find_all('a'):
                    txt = link.text.strip()
                    if txt in TEAM_MAP: teams_in_away_row.append(txt)
            
            if len(teams_in_away_row) >= 2:
                away_name_ch = teams_in_away_row[0]
                home_name_ch = teams_in_away_row[1]
            else:
                away_name_ch = extract_team_name(r_away)
                home_name_ch = extract_team_name(r_home)
            
            if not away_name_ch or not home_name_ch:
                continue

            # --- 解析賠率 (td-bank-bet03) ---
            def extract_odd(row):
                if not row: return np.nan
                td = row.find('td', class_='td-bank-bet03')
                if not td: return np.nan
                txt = td.get_text().strip()
                import re
                nums = re.findall(r"[-+]?\d*\.\d+|\d+", txt)
                if nums: return float(nums[-1])
                return np.nan

            odd_away = extract_odd(r_away)
            odd_home = extract_odd(r_home)
            
            # 轉換為代碼
            away_abbr = TEAM_MAP.get(away_name_ch, "UNKNOWN")
            home_abbr = TEAM_MAP.get(home_name_ch, "UNKNOWN")
            
            daily_data.append({
                'Away_Abbr': away_abbr,
                'Home_Abbr': home_abbr,
                'Odds_Away': odd_away,
                'Odds_Home': odd_home
            })
        
        print(f"  ✅ 成功抓取 {len(daily_data)} 場比賽賠率！")
        return daily_data

    except Exception as e:
        print(f"  抓取失敗: {e}")
        return []

def main():
    print("\n" + "="*60)
    print(" 🏀 NBA 每日實戰出單機 (v900 - v501核心版)")
    print(" 🎯 讀取預測 -> 爬取 PlaySport (隔日) -> 產出策略單")
    print("="*60)

    # 1. 讀取最新預測
    pred_file = find_latest_prediction_file()
    if not pred_file:
        print("❌ 找不到每日預測檔 (predictions_YYYY-MM-DD.csv)。請先執行 v500。")
        return

    # 解析日期 (US Time)
    match = re.search(r"predictions_(\d{4}-\d{2}-\d{2})\.csv", pred_file)
    if not match: print("日期解析失敗"); return
    
    us_date_str = match.group(1)
    us_date = datetime.datetime.strptime(us_date_str, "%Y-%m-%d")
    
    # 台灣時間 = US + 1天 (這是 v501 的核心邏輯)
    tw_date = us_date + datetime.timedelta(days=1)
    tw_date_str = tw_date.strftime("%Y%m%d")

    print(f"📅 預測日期 (US): {us_date_str}")
    print(f"🎯 目標賠率日期 (TW): {tw_date.strftime('%Y-%m-%d')} (+1 day)")
    print(f"📂 讀取檔案: {pred_file}")
    
    df_pred = pd.read_csv(pred_file)
    
    # 2. 使用 v501 邏輯抓取賠率
    odds_data = get_playsport_odds_v501(tw_date_str)
    
    if not odds_data:
        print("\n❌ 無法取得賠率 (可能是尚未開盤或日期錯誤)。")
        # 產生空檔防止報錯
        pd.DataFrame(columns=['Date','Team','Opp','Loc','Win%','Odds','EV','Signal','Rank']).to_csv(f"Betting_Plan_{us_date_str}.csv", index=False)
        return

    df_odds = pd.DataFrame(odds_data)
    
    # 3. 合併數據與計算 (v900 策略核心)
    final_rows = []
    
    for idx, row in df_pred.iterrows():
        # v500 產出的檔案欄位通常是 'Home', 'Away', 'Home_Win_Prob'
        home = row['Home']
        away = row['Away']
        prob_h = float(row['Home_Win_Prob'])
        prob_a = 1.0 - prob_h
        
        # 找賠率 (雙向匹配)
        match_odd = df_odds[
            ((df_odds['Home_Abbr'] == home) & (df_odds['Away_Abbr'] == away)) |
            ((df_odds['Home_Abbr'] == away) & (df_odds['Away_Abbr'] == home))
        ]
        
        if match_odd.empty:
            # print(f"  [跳過] 找不到賠率: {away} vs {home}")
            continue
            
        odd_h = float(match_odd.iloc[0]['Odds_Home'])
        odd_a = float(match_odd.iloc[0]['Odds_Away'])
        
        # --- 應用核心策略 ---
        
        # 1. 主隊分析
        ev_h = (prob_h * odd_h) - 1
        signal_h = ""
        rank_h = 0
        
        if 0.60 <= prob_h < 0.70 and ev_h > 0:
            signal_h = "💎 BET HOME (ROI King)"
            rank_h = 3
        elif 0.50 <= prob_h < 0.60 and ev_h > 0:
            signal_h = "🟡 BET HOME (Value)"
            rank_h = 2
        elif ev_h > 0.20:
            signal_h = "🚀 BET HOME (High EV)"
            rank_h = 2
            
        if signal_h:
            final_rows.append({
                'Date': us_date_str, 'Team': home, 'Opp': away, 'Loc': 'Home',
                'Win%': prob_h, 'Odds': odd_h, 'EV': ev_h, 
                'Signal': signal_h, 'Rank': rank_h
            })
            
        # 2. 客隊分析
        ev_a = (prob_a * odd_a) - 1
        signal_a = ""
        rank_a = 0
        
        if ev_a > 0.20:
            signal_a = "🚀 BET AWAY (High EV)"
            rank_a = 2
        elif prob_a > 0.75:
             signal_a = "⚓ AWAY (Anchor)"
             rank_a = 1
             
        if signal_a:
            final_rows.append({
                'Date': us_date_str, 'Team': away, 'Opp': home, 'Loc': 'Away',
                'Win%': prob_a, 'Odds': odd_a, 'EV': ev_a, 
                'Signal': signal_a, 'Rank': rank_a
            })

    # 4. 輸出結果與串關
    df_final = pd.DataFrame(final_rows)
    if not df_final.empty:
        df_final = df_final.sort_values(by=['Rank', 'Win%'], ascending=[False, False])
        
        print(f"\n📋 【明日最佳單場推薦】 (共 {len(df_final)} 場)")
        print("-" * 80)
        print(f"{'隊伍 (主/客)':<15} | {'勝率':<6} | {'賠率':<6} | {'EV':<6} | {'策略訊號'}")
        print("-" * 80)
        
        for _, row in df_final.iterrows():
            team_str = f"{row['Team']} ({row['Loc']})"
            print(f"{team_str:<15} | {row['Win%']:.0%}    | {row['Odds']:<6} | {row['EV']:+.2f}   | {row['Signal']}")

        # 串關計算
        candidates = df_final[df_final['Rank'] >= 1]
        if len(candidates) >= 2:
            print(f"\n🔗 【明日最佳串關組合】")
            print("-" * 80)
            p1 = candidates.iloc[0]
            p2 = candidates.iloc[1]
            comb_odd = round(p1['Odds'] * p2['Odds'], 2)
            comb_ev = round((p1['Win%'] * p2['Win%'] * comb_odd) - 1, 2)
            print(f"🛡️ [穩健二串一] 主推: {p1['Team']} + {p2['Team']}")
            print(f"   賠率: {comb_odd} | 預期獲利(EV): {comb_ev:+.2f}")
        else:
            print("\n⚠️ 有效場次不足 2 場，無法組成優質串關。")
            
    else:
        print("\n⚠️ 今日無符合策略 (EV>0 或高勝率) 的投注機會。")
        # 仍建立空 DataFrame 以免後續報錯
        df_final = pd.DataFrame(columns=['Date','Team','Opp','Loc','Win%','Odds','EV','Signal','Rank'])

    # 存檔
    output_csv = f"Betting_Plan_{us_date_str}.csv"
    df_final.to_csv(output_csv, index=False, encoding='utf-8-sig')
    print(f"\n✅ 詳細計畫已匯出: {output_csv}")

if __name__ == "__main__":
    main()