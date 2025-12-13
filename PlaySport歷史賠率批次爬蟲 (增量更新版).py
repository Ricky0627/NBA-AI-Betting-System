import proxy_patch
import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
import datetime
import random
import os
import re

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

def parse_odds_from_td(td_tag):
    """從賠率格子中提取數字"""
    if not td_tag:
        return None
    try:
        # 移除 HTML 標籤，只留文字
        text = td_tag.get_text().strip()
        # 尋找浮點數 (如 1.75, 2.25)
        # 排除日期格式或百分比
        matches = re.findall(r"(\d+\.\d+)", text)
        for m in matches:
            val = float(m)
            # 運彩不讓分賠率通常在 1.01 到 15.0 之間
            if 1.01 <= val <= 15.0:
                return val
    except:
        pass
    return None

def get_playsport_odds_robust(target_date_str):
    """
    抓取單日賠率 (針對 gamesData/result 歷史賽果頁面優化版)
    target_date_str: YYYYMMDD (這是台灣時間)
    """
    url = f"https://www.playsport.cc/gamesData/result?allianceid=3&gametime={target_date_str}"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }

    try:
        resp = requests.get(url, headers=headers, timeout=10)
        resp.encoding = 'utf-8' # 強制 UTF-8
        
        if resp.status_code != 200:
            print(f"   ⚠️ 請求失敗 ({resp.status_code}) - URL: {url}")
            return []
            
        soup = BeautifulSoup(resp.text, 'html.parser')
        
        # --- 計算美國時間 (用於存檔) ---
        tw_date = datetime.datetime.strptime(target_date_str, "%Y%m%d").date()
        us_date = tw_date - datetime.timedelta(days=1)
        date_for_save = us_date.strftime("%Y-%m-%d")
        # ---------------------------

        games_data = []
        
        # 尋找所有比賽的第一行 (包含 td-teaminfo 的那一行)
        # 這些 tr 通常帶有 gameid 屬性
        rows = soup.find_all('tr', attrs={'gameid': True})
        
        # 使用 set 避免重複處理 (因為有些結構可能有嵌套)
        processed_gameids = set()

        for row in rows:
            game_id = row['gameid']
            if game_id in processed_gameids:
                continue
            
            # 檢查這一行是否包含球隊資訊 (td-teaminfo)
            # 只有包含球隊資訊的行，才是我們處理的起點 (客隊行)
            team_info_td = row.find('td', class_='td-teaminfo')
            if not team_info_td:
                continue # 如果這行沒有球隊資訊，跳過 (這可能是主隊行，稍後會被自動抓取)
            
            # --- 1. 解析隊名 ---
            # td-teaminfo 裡面包含兩個隊伍的連結或文字
            # 順序通常是：上為客隊，下為主隊
            # 我們直接抓取該格子內的所有文字，並依序比對
            all_text = team_info_td.get_text()
            
            found_teams = []
            # 這裡我們需要保留順序，所以不能用字典迭代，改用掃描文字的方式
            # 但最簡單的方法是：找出所有符合我們 TEAM_MAP 的關鍵字
            # 為了避免誤判 (例如 "公牛" 和 "小牛"?)，我們直接尋找 map 中的 key
            
            # 更好的方法：找裡面的 <a> 標籤，通常隊名都在 <a> 裡面
            links = team_info_td.find_all('a')
            for link in links:
                t_text = link.get_text().strip()
                for name, code in TEAM_MAP.items():
                    if name in t_text:
                        found_teams.append(code)
                        break # 找到對應代碼就換下一個 link
            
            # 如果用 <a> 找不到 (有時可能沒連結)，再試試純文字暴力搜尋
            if len(found_teams) < 2:
                found_teams = []
                for name, code in TEAM_MAP.items():
                    if name in all_text:
                        # 這裡有個小問題：如果文字是 "洛杉磯湖人"，"湖人" 會被對到。
                        # 我們假設 map 裡的 key 是足夠獨特的
                        # 為了確保順序，這有點難，暫時假設 <a> 標籤解析成功率較高
                        # 若真的失敗，使用備用方案：
                        pass

            # 若還是抓不到兩隊，跳過
            if len(found_teams) < 2:
                # Debug: print(f"   跳過: 抓不到兩個隊名 - {all_text.strip()[:20]}...")
                continue
            
            # 按照 PlaySport 賽果頁面慣例：第一個是客隊，第二個是主隊
            away_code = found_teams[0]
            home_code = found_teams[1]
            
            if away_code == home_code:
                continue

            # --- 2. 解析賠率 ---
            # 客隊賠率：在當前行 (row) 的 td-bank-bet03
            # 主隊賠率：在下一行 (next_sibling) 的 td-bank-bet03
            
            # 客隊賠率
            odds_away = parse_odds_from_td(row.find('td', class_='td-bank-bet03'))
            
            # 主隊賠率 (尋找下一個 tr)
            next_row = row.find_next_sibling('tr')
            odds_home = None
            if next_row and next_row.get('gameid') == game_id:
                odds_home = parse_odds_from_td(next_row.find('td', class_='td-bank-bet03'))
            
            # 若下一行找不到，有時候可能是結構問題，再試試 next_sibling 的 next_sibling
            # 但通常 PlaySport 結構很固定
            
            if odds_away and odds_home:
                games_data.append({
                    'Date': date_for_save,
                    'Away_Abbr': away_code,
                    'Home_Abbr': home_code,
                    'Odds_Away': odds_away,
                    'Odds_Home': odds_home
                })
                # 標記此 game_id 已處理
                processed_gameids.add(game_id)
        
        return games_data

    except Exception as e:
        print(f"   ⚠️ 解析錯誤: {e}")
        return []

def scrape_playsport_history(start_date, end_date):
    """批次抓取範圍內的賠率"""
    all_data = []
    current = start_date
    
    while current <= end_date:
        date_str = current.strftime("%Y%m%d")
        
        # 顯示正在抓取，並提示對應的美國日期
        us_date_display = current - datetime.timedelta(days=1)
        print(f"   正在抓取: {date_str} (對應美國時間 {us_date_display}) ...")
        
        daily_data = get_playsport_odds_robust(date_str)
        if daily_data:
            print(f"     -> 成功抓取 {len(daily_data)} 場")
            all_data.extend(daily_data)
        else:
            print("     -> 無資料或解析失敗")
            
        current += datetime.timedelta(days=1)
        # 隨機延遲，避免被鎖 IP
        time.sleep(random.uniform(1.0, 2.0)) 
        
    return all_data

# --- 主程式 ---
if __name__ == "__main__":
    filename = "odds_2026_full_season.csv"
    
    # 賽季開始日期 (2025-10-22 台灣時間)
    season_start = datetime.date(2025, 10, 22) 
    end_date = datetime.date.today() + datetime.timedelta(days=1) 

    existing_df = pd.DataFrame()
    start_date = season_start

    if os.path.exists(filename):
        try:
            existing_df = pd.read_csv(filename)
            if not existing_df.empty:
                last_us_date_str = existing_df['Date'].max()
                last_us_date = datetime.datetime.strptime(last_us_date_str, "%Y-%m-%d").date()
                
                # 增量更新邏輯
                start_date = last_us_date + datetime.timedelta(days=2) 
                
                print(f"📂 發現舊檔案，最後記錄日期 (US): {last_us_date_str}")
                print(f"   -> 上次爬取的台灣日期應為: {last_us_date + datetime.timedelta(days=1)}")
                print(f"   -> 本次將從台灣時間 {start_date} 開始更新")
            else:
                print("   ⚠️ 檔案似乎為空，重新抓取。")
        except:
            print("   ⚠️ 讀取失敗，重新抓取。")
            
    if start_date > end_date:
        print(f"✅ 數據已是最新 (已涵蓋至台灣時間 {end_date})，無需更新。")
    else:
        print(f"\n🚀 開始更新 2026 賽季數據，範圍: {start_date} ~ {end_date}")
        print("=" * 60)
        
        new_data = scrape_playsport_history(start_date, end_date)
        
        if new_data:
            new_df = pd.DataFrame(new_data)
            final_df = pd.concat([existing_df, new_df]).drop_duplicates(subset=['Date', 'Home_Abbr', 'Away_Abbr'], keep='last')
            final_df = final_df.sort_values('Date')
            
            final_df.to_csv(filename, index=False, encoding='utf-8-sig')
            print(f"🎉 更新完成！總筆數: {len(final_df)}")
            print(f"檔案已儲存至: {filename}")
        else:
            print("⚠️ 本次無新數據更新。")