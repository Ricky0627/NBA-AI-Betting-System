import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
import datetime
import random
import os  # 新增：用於檢查檔案

# --- 1. 隊名對照表 ---
TEAM_MAP = {
    '老鷹': 'ATL', '塞爾提克': 'BOS', '塞爾提': 'BOS',
    '籃網': 'BRK', '黃蜂': 'CHO',
    '公牛': 'CHI', '騎士': 'CLE', '獨行俠': 'DAL', '金塊': 'DEN',
    '活塞': 'DET', '勇士': 'GSW', '火箭': 'HOU', '溜馬': 'IND',
    '快艇': 'LAC', '湖人': 'LAL', '灰熊': 'MEM', '熱火': 'MIA',
    '公鹿': 'MIL', '灰狼': 'MIN', '鵜鶘': 'NOP', '尼克': 'NYK',
    '雷霆': 'OKC', '魔術': 'ORL', '76人': 'PHI', '七六人': 'PHI',
    '太陽': 'PHO', '拓荒者': 'POR', '拓荒': 'POR',
    '國王': 'SAC', '馬刺': 'SAS', '暴龍': 'TOR',
    '爵士': 'UTA', '巫師': 'WAS'
}

def get_playsport_odds_robust(target_date_str):
    """
    抓取單日賠率 (邏輯不變)
    target_date_str: YYYYMMDD
    """
    url = f"https://www.playsport.cc/gamesData/result?allianceid=3&gametime={target_date_str}"
    # print(f"  正在抓取: {target_date_str} ...")
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.content, 'lxml')
        
        game_rows = soup.find_all('tr', attrs={'gameid': True})
        if not game_rows:
            main_table = soup.find('table', class_='predictgame-table')
            if main_table:
                game_rows = main_table.find_all('tr', attrs={'gameid': True})
        
        if not game_rows:
            return []
            
        games_dict = {}
        for row in game_rows:
            gid = row['gameid']
            if gid not in games_dict: games_dict[gid] = []
            games_dict[gid].append(row)
            
        daily_data = []
        
        for gid, rows in games_dict.items():
            if len(rows) < 2: continue 
            
            r_away = rows[0]
            r_home = rows[1]
            
            # --- 解析隊名 ---
            def extract_team_name(row):
                td = row.find('td', class_='td-teaminfo')
                if not td: return None
                links = td.find_all('a')
                for link in links:
                    txt = link.text.strip()
                    if txt in TEAM_MAP: return txt
                return None

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

            # --- 解析賠率 ---
            def extract_odd(row):
                if not row: return None
                td = row.find('td', class_='td-bank-bet03')
                if not td: return None
                txt = td.get_text().strip()
                import re
                nums = re.findall(r"[-+]?\d*\.\d+|\d+", txt)
                if nums: return float(nums[-1])
                return None

            odd_away = extract_odd(r_away)
            odd_home = extract_odd(r_home)
            
            if odd_away is None or odd_home is None:
                continue

            away_abbr = TEAM_MAP.get(away_name_ch, "UNKNOWN")
            home_abbr = TEAM_MAP.get(home_name_ch, "UNKNOWN")
            
            daily_data.append({
                'Away_Abbr': away_abbr,
                'Home_Abbr': home_abbr,
                'Odds_Away': odd_away,
                'Odds_Home': odd_home
            })
        
        return daily_data

    except Exception as e:
        print(f"  ❌ 抓取失敗 ({target_date_str}): {e}")
        return []

def scrape_playsport_history(start_date, end_date):
    """
    批次抓取指定範圍的賠率
    """
    all_history = []
    current_date = start_date
    
    total_days = (end_date - start_date).days + 1
    processed_count = 0

    while current_date <= end_date:
        date_str = current_date.strftime("%Y%m%d")
        display_date = current_date.strftime("%Y-%m-%d")
        
        processed_count += 1
        print(f"[{processed_count}/{total_days}] 正在處理: {display_date} ... ", end="", flush=True)
        
        day_data = get_playsport_odds_robust(date_str)
        
        if day_data:
            print(f"✅ 抓到 {len(day_data)} 場")
            for d in day_data:
                d['Date'] = display_date # 加入日期欄位
                all_history.append(d)
        else:
            print("⚠️ 無數據")
        
        current_date += datetime.timedelta(days=1)
        
        # 隨機延遲，避免被鎖 IP
        time.sleep(random.uniform(0.5, 1.5))
        
    return all_history

def main():
    # 設定檔案名稱
    filename = "odds_2026_full_season.csv"
    
    # 預設：如果沒有檔案，從賽季第一天開始
    season_start = datetime.date(2024, 10, 22)
    
    # 設定結束日 (昨天，因為今天的比賽可能還沒打完或賠率還在變)
    end_date = datetime.date.today() - datetime.timedelta(days=1)
    
    existing_df = pd.DataFrame()
    start_date = season_start

    # 1. 檢查檔案是否存在，決定 start_date
    if os.path.exists(filename):
        print(f"📂 發現現有檔案: {filename}")
        try:
            existing_df = pd.read_csv(filename)
            if not existing_df.empty and 'Date' in existing_df.columns:
                # 確保日期格式正確
                existing_df['Date'] = pd.to_datetime(existing_df['Date']).dt.date
                
                # 找出最後一天
                last_date = existing_df['Date'].max()
                print(f"   目前數據更新至: {last_date}")
                
                # 設定新的開始日期 = 最後一天 + 1
                start_date = last_date + datetime.timedelta(days=1)
            else:
                print("   ⚠️ 檔案似乎為空或格式不符，將重新完整抓取。")
        except Exception as e:
            print(f"   ⚠️ 讀取舊檔失敗 ({e})，將重新完整抓取。")
    else:
        print(f"📂 找不到現有檔案，將建立新檔案 (從 {season_start} 開始)...")

    # 2. 判斷是否需要執行
    if start_date > end_date:
        print(f"✅ 數據已是最新 (至 {end_date})，無需更新！休息一下吧。")
        return

    print(f"\n🚀 開始增量更新，範圍: {start_date} ~ {end_date}")
    print("=" * 60)

    # 3. 執行爬蟲
    new_data = scrape_playsport_history(start_date, end_date)

    # 4. 合併與存檔
    if new_data:
        new_df = pd.DataFrame(new_data)
        
        # 轉換日期格式以便合併
        new_df['Date'] = pd.to_datetime(new_df['Date']).dt.date
        
        if not existing_df.empty:
            print(f"\n🔄 正在合併新舊數據... (舊: {len(existing_df)} + 新: {len(new_df)})")
            final_df = pd.concat([existing_df, new_df], ignore_index=True)
        else:
            final_df = new_df

        # 排序與去重 (非常重要：避免重複寫入)
        # 依日期排序
        final_df = final_df.sort_values(by=['Date', 'Home_Abbr'])
        # 移除完全重複的行
        final_df.drop_duplicates(subset=['Date', 'Home_Abbr', 'Away_Abbr'], keep='last', inplace=True)
        
        # 存檔
        final_df.to_csv(filename, index=False, encoding='utf-8-sig')
        print(f"💾 存檔完成！總筆數: {len(final_df)}")
        print(f"   檔案位置: {filename}")
    else:
        print("\n⚠️ 本次執行沒有抓到任何新數據 (可能是網站結構變更或當日無比賽)。")

if __name__ == "__main__":
    main()