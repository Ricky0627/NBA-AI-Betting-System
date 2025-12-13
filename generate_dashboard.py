import pandas as pd
import os
import glob
import datetime
import numpy as np
import re

# --- 設定：Logo 對照 ---
LOGO_MAP = {
    'ATL': 'https://a.espncdn.com/i/teamlogos/nba/500/atl.png', 'BOS': 'https://a.espncdn.com/i/teamlogos/nba/500/bos.png',
    'BRK': 'https://a.espncdn.com/i/teamlogos/nba/500/bkn.png', 'CHO': 'https://a.espncdn.com/i/teamlogos/nba/500/cha.png',
    'CHI': 'https://a.espncdn.com/i/teamlogos/nba/500/chi.png', 'CLE': 'https://a.espncdn.com/i/teamlogos/nba/500/cle.png',
    'DAL': 'https://a.espncdn.com/i/teamlogos/nba/500/dal.png', 'DEN': 'https://a.espncdn.com/i/teamlogos/nba/500/den.png',
    'DET': 'https://a.espncdn.com/i/teamlogos/nba/500/det.png', 'GSW': 'https://a.espncdn.com/i/teamlogos/nba/500/gs.png',
    'HOU': 'https://a.espncdn.com/i/teamlogos/nba/500/hou.png', 'IND': 'https://a.espncdn.com/i/teamlogos/nba/500/ind.png',
    'LAC': 'https://a.espncdn.com/i/teamlogos/nba/500/lac.png', 'LAL': 'https://a.espncdn.com/i/teamlogos/nba/500/lal.png',
    'MEM': 'https://a.espncdn.com/i/teamlogos/nba/500/mem.png', 'MIA': 'https://a.espncdn.com/i/teamlogos/nba/500/mia.png',
    'MIL': 'https://a.espncdn.com/i/teamlogos/nba/500/mil.png', 'MIN': 'https://a.espncdn.com/i/teamlogos/nba/500/min.png',
    'NOP': 'https://a.espncdn.com/i/teamlogos/nba/500/no.png', 'NYK': 'https://a.espncdn.com/i/teamlogos/nba/500/ny.png',
    'OKC': 'https://a.espncdn.com/i/teamlogos/nba/500/okc.png', 'ORL': 'https://a.espncdn.com/i/teamlogos/nba/500/orl.png',
    'PHI': 'https://a.espncdn.com/i/teamlogos/nba/500/phi.png', 'PHO': 'https://a.espncdn.com/i/teamlogos/nba/500/phx.png',
    'POR': 'https://a.espncdn.com/i/teamlogos/nba/500/por.png', 'SAC': 'https://a.espncdn.com/i/teamlogos/nba/500/sac.png',
    'SAS': 'https://a.espncdn.com/i/teamlogos/nba/500/sa.png', 'TOR': 'https://a.espncdn.com/i/teamlogos/nba/500/tor.png',
    'UTA': 'https://a.espncdn.com/i/teamlogos/nba/500/utah.png', 'WAS': 'https://a.espncdn.com/i/teamlogos/nba/500/wsh.png'
}

# --- 設定：隊名標準化 ---
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

def get_team_logo(abbr):
    """取得球隊 Logo URL"""
    return LOGO_MAP.get(abbr, "https://a.espncdn.com/i/teamlogos/nba/500/nba.png")

def format_ev_color(ev_val):
    """根據 EV 值回傳顏色 Class"""
    try:
        val = float(ev_val)
        if val >= 0.10: return "text-success fw-bold"
        if val > 0: return "text-primary"
        return "text-muted"
    except:
        return "text-muted"

def format_grade_badge(grade):
    """根據評級回傳 Badge 樣式"""
    if "👑" in grade: return "bg-warning text-dark"
    if "💎" in grade: return "bg-info text-dark"
    if "🛡️" in grade: return "bg-success"
    if "⚖️" in grade: return "bg-primary"
    if "🏹" in grade: return "bg-danger"
    return "bg-secondary"

def merge_odds_data(df_pred, odds_file, pred_filename=None):
    """將賠率資料合併到預測資料中 (修正版：支援從檔名抓日期)"""
    if df_pred.empty or not os.path.exists(odds_file):
        return df_pred

    try:
        df_o = pd.read_csv(odds_file)
        # 建立賠率查找表 Key: "YYYY-MM-DD_Team"
        odds_map = {}
        for _, row in df_o.iterrows():
            d = str(row['Date'])
            h = normalize_team(row['Home_Abbr'])
            a = normalize_team(row['Away_Abbr'])
            odds_map[f"{d}_{h}"] = row['Odds_Home']
            odds_map[f"{d}_{a}"] = row['Odds_Away']
        
        # 準備新欄位
        home_odds_list = []
        away_odds_list = []
        home_ev_list = []
        away_ev_list = []

        # --- 關鍵修正：決定日期來源 ---
        default_date = None
        if pred_filename:
            match = re.search(r"predictions_(\d{4}-\d{2}-\d{2})\.csv", pred_filename)
            if match:
                default_date = match.group(1)
                # print(f" 📅 從檔名偵測到日期: {default_date}")

        for _, row in df_pred.iterrows():
            # 優先使用檔名日期，否則找 date/Date 欄位
            d = default_date
            if not d:
                if 'date' in row: d = pd.to_datetime(row['date']).strftime('%Y-%m-%d')
                elif 'Date' in row: d = pd.to_datetime(row['Date']).strftime('%Y-%m-%d')
            
            # 如果還是沒日期，跳過
            if not d:
                home_odds_list.append("-")
                away_odds_list.append("-")
                home_ev_list.append(None)
                away_ev_list.append(None)
                continue

            h = normalize_team(row['Home'])
            a = normalize_team(row['Away'])
            
            # 查找賠率
            odd_h = odds_map.get(f"{d}_{h}")
            odd_a = odds_map.get(f"{d}_{a}")
            
            prob_h = float(row['Home_Win_Prob'])
            prob_a = 1.0 - prob_h
            
            ev_h = (prob_h * float(odd_h)) - 1 if odd_h else None
            ev_a = (prob_a * float(odd_a)) - 1 if odd_a else None
            
            home_odds_list.append(odd_h if odd_h else "-")
            away_odds_list.append(odd_a if odd_a else "-")
            home_ev_list.append(ev_h)
            away_ev_list.append(ev_a)
            
        df_pred['Odds_Home'] = home_odds_list
        df_pred['Odds_Away'] = away_odds_list
        df_pred['EV_Home'] = home_ev_list
        df_pred['EV_Away'] = away_ev_list
        
        return df_pred
    except Exception as e:
        print(f"❌ 合併賠率時發生錯誤: {e}")
        # 發生錯誤時回傳原始資料，避免程式崩潰
        return df_pred

def generate_html_report(df_parlay, df_raw, last_updated_time, raw_pred_file):
    """生成 HTML 報告"""
    
    # --- 1. 串關區塊 HTML ---
    parlay_html = ""
    if df_parlay.empty:
        parlay_html = """
        <div class="alert alert-warning text-center" role="alert">
            <i class="fas fa-exclamation-triangle me-2"></i>
            今日無符合高價值策略的串關組合 (No Recommendation Today)
        </div>
        """
    else:
        parlay_rows = ""
        for _, row in df_parlay.iterrows():
            t1 = row['Team_1']
            t2 = row['Team_2']
            grade = row['Type']
            
            logo1 = f'<img src="{get_team_logo(t1)}" class="team-logo-sm">'
            logo2 = f'<img src="{get_team_logo(t2)}" class="team-logo-sm">'
            
            ev_class = format_ev_color(row['Combined_EV'])
            badge_class = format_grade_badge(grade)
            
            parlay_rows += f"""
            <tr class="align-middle">
                <td><span class="badge {badge_class}">{grade}</span></td>
                <td>
                    <div class="d-flex align-items-center">
                        {logo1} <span class="fw-bold mx-1">{t1}</span> 
                        <span class="text-muted mx-2">+</span> 
                        {logo2} <span class="fw-bold mx-1">{t2}</span>
                    </div>
                </td>
                <td class="text-center fw-bold">{row['Combined_Odds']:.2f}</td>
                <td class="text-center {ev_class}">{row['Combined_EV']:+.2f}</td>
            </tr>
            """
            
        parlay_html = f"""
        <table class="table table-hover mb-0">
            <thead class="table-light">
                <tr>
                    <th width="20%">策略類型</th>
                    <th width="40%">組合 (Combo)</th>
                    <th width="20%" class="text-center">總賠率</th>
                    <th width="20%" class="text-center">總期望值</th>
                </tr>
            </thead>
            <tbody>
                {parlay_rows}
            </tbody>
        </table>
        """

    # --- 2. 原始預測表 HTML (含賠率與 EV) ---
    if not df_raw.empty:
        raw_rows = ""
        for _, row in df_raw.iterrows():
            h = row['Home']
            a = row['Away']
            prob = float(row['Home_Win_Prob'])
            
            # 賠率與 EV 顯示處理
            odds_h = row.get('Odds_Home', '-')
            odds_a = row.get('Odds_Away', '-')
            ev_h_val = row.get('EV_Home')
            ev_a_val = row.get('EV_Away')
            
            # 格式化 EV 顯示
            def fmt_ev(val):
                if val is None or val == "-": return "-"
                try:
                    v = float(val)
                    color = "text-success fw-bold" if v > 0 else "text-muted"
                    return f'<span class="{color}">{v:+.2f}</span>'
                except:
                    return "-"

            ev_h_str = fmt_ev(ev_h_val)
            ev_a_str = fmt_ev(ev_a_val)
            
            # 進度條
            prob_pct = prob * 100
            if prob > 0.5:
                bar_color = "bg-success"
                win_text = f"{h} ({prob:.1%})"
            else:
                bar_color = "bg-danger"
                win_text = f"{a} ({1-prob:.1%})"
                
            raw_rows += f"""
            <tr>
                <td class="text-center"><img src="{get_team_logo(h)}" class="team-logo-xs"> {h}</td>
                <td class="text-center"><img src="{get_team_logo(a)}" class="team-logo-xs"> {a}</td>
                <td style="width: 30%;">
                    <div class="d-flex justify-content-between small mb-1">
                        <span>{win_text}</span>
                    </div>
                    <div class="progress" style="height: 6px;">
                        <div class="progress-bar {bar_color}" role="progressbar" style="width: {prob_pct if prob>0.5 else 100-prob_pct}%"></div>
                    </div>
                </td>
                <td class="text-center small">{odds_h}</td>
                <td class="text-center small">{odds_a}</td>
                <td class="text-center small">{ev_h_str}</td>
                <td class="text-center small">{ev_a_str}</td>
            </tr>
            """
            
        raw_table_html = f"""
        <table class="table table-sm table-striped align-middle">
            <thead class="table-dark small">
                <tr>
                    <th class="text-center">主隊</th>
                    <th class="text-center">客隊</th>
                    <th>預測勝率</th>
                    <th class="text-center">主賠</th>
                    <th class="text-center">客賠</th>
                    <th class="text-center">主EV</th>
                    <th class="text-center">客EV</th>
                </tr>
            </thead>
            <tbody>
                {raw_rows}
            </tbody>
        </table>
        """
    else:
        raw_table_html = "<p class='text-center text-muted my-3'>今日無賽事或尚未預測</p>"

    # --- 3. 策略圖表區塊 ---
    chart_html = ""
    chart1_exists = os.path.exists('chart_cumulative_profit.png')
    chart2_exists = os.path.exists('chart_roi_summary.png')
    
    if chart1_exists or chart2_exists:
        chart_imgs = ""
        if chart1_exists:
            chart_imgs += '<div class="col-md-6 mb-3"><img src="chart_cumulative_profit.png" class="img-fluid rounded border shadow-sm" alt="獲利曲線"></div>'
        if chart2_exists:
            chart_imgs += '<div class="col-md-6 mb-3"><img src="chart_roi_summary.png" class="img-fluid rounded border shadow-sm" alt="ROI排行"></div>'
            
        chart_html = f"""
        <div class="card-box mt-4">
            <div class="card-header-custom text-info">
                <span><i class="fas fa-chart-line me-2"></i>策略回測分析 (Strategy Backtest)</span>
            </div>
            <div class="card-body">
                <div class="row">
                    {chart_imgs}
                </div>
                <p class="text-muted small text-center mt-2">
                    <i class="fas fa-info-circle"></i> 此圖表由 v980 自動生成，展示各策略在歷史數據上的真實表現。
                </p>
            </div>
        </div>
        """

    # --- 4. 組合最終 HTML ---
    html_content = f"""
    <!DOCTYPE html>
    <html lang="zh-TW">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>NBA AI 戰情室 v3.9</title>
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
        <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
        <style>
            body {{ background-color: #f4f6f9; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; }}
            .header-bar {{ background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%); color: white; padding: 20px 0; margin-bottom: 30px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }}
            .card-box {{ background: white; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.05); margin-bottom: 20px; overflow: hidden; }}
            .card-header-custom {{ padding: 15px 20px; font-weight: bold; border-bottom: 1px solid #eee; display: flex; justify-content: space-between; align-items: center; }}
            .team-logo-sm {{ width: 30px; height: 30px; object-fit: contain; }}
            .team-logo-xs {{ width: 24px; height: 24px; object-fit: contain; margin-right: 5px; }}
            .section-title {{ font-size: 1.1rem; color: #555; margin-bottom: 15px; font-weight: 600; border-left: 4px solid #1e3c72; padding-left: 10px; }}
            footer {{ text-align: center; color: #888; padding: 20px; font-size: 0.9rem; }}
            /* 表格文字微調 */
            .table-sm td, .table-sm th {{ font-size: 0.9rem; }}
        </style>
    </head>
    <body>

    <div class="header-bar">
        <div class="container">
            <div class="d-flex justify-content-between align-items-center">
                <div>
                    <h2 class="mb-0"><i class="fas fa-basketball-ball me-2"></i>NBA AI 運彩戰情室</h2>
                    <small class="opacity-75">Daily Sports Betting Analysis Dashboard</small>
                </div>
                <div class="text-end">
                    <div class="badge bg-light text-primary fs-6">
                        <i class="far fa-clock me-1"></i> Update: {last_updated_time}
                    </div>
                </div>
            </div>
        </div>
    </div>

    <div class="container">
        
        <div class="row">
            <div class="col-lg-7">
                <div class="section-title">今日核心推薦 (Core Recommendations)</div>
                <div class="card-box">
                    <div class="card-header-custom text-primary">
                        <span><i class="fas fa-link me-2"></i>最佳串關組合 (Best Parlays)</span>
                        <span class="badge bg-warning text-dark">AI Optimized</span>
                    </div>
                    <div class="p-0">
                        {parlay_html}
                    </div>
                </div>
                
                {chart_html}
            </div>

            <div class="col-lg-5">
                <div class="section-title">全賽事預測 & 賠率 (All Games & Odds)</div>
                <div class="card-box">
                    <div class="card-header-custom text-secondary">
                        <span><i class="fas fa-list me-2"></i>今日總覽</span>
                        <span class="badge bg-light text-dark">{os.path.basename(raw_pred_file) if raw_pred_file else "No Data"}</span>
                    </div>
                    <div class="table-responsive" style="max-height: 800px; overflow-y: auto;">
                        {raw_table_html}
                    </div>
                </div>
            </div>
        </div>

        <footer>
            NBA AI System v3.9 • Powered by Random Forest & Parlay Optimizer
        </footer>
    </div>

    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
    </body>
    </html>
    """

    with open('index.html', 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    print(f"✅ Dashboard 已生成: index.html (包含 {len(df_parlay)} 筆推薦)")

def main():
    print("\n🌐 啟動戰情室網頁生成器 v3.9...")
    
    # 1. 讀取推薦結果
    parlay_file = "Daily_Parlay_Recommendations.csv"
    if os.path.exists(parlay_file):
        try:
            df_parlay = pd.read_csv(parlay_file)
        except pd.errors.EmptyDataError:
            df_parlay = pd.DataFrame()
    else:
        df_parlay = pd.DataFrame()

    # 2. 讀取最新預測檔
    files = glob.glob(os.path.join("predictions", "predictions_*.csv"))
    files = [f for f in files if "full_" not in f]
    files.sort(key=lambda x: os.path.getctime(x), reverse=True)
    
    raw_pred_file = files[0] if files else None
    df_raw = pd.read_csv(raw_pred_file) if raw_pred_file else pd.DataFrame()
    
    # 3. 讀取並合併賠率 (新增)
    odds_file = "odds_2026_full_season.csv"
    if not df_raw.empty and os.path.exists(odds_file):
        print("🔗 正在合併最新賠率資訊...")
        # 這裡會傳入檔名，讓 merge_odds_data 知道該用哪一天
        df_raw = merge_odds_data(df_raw, odds_file, raw_pred_file)
    
    # 4. 生成網頁
    now_str = datetime.datetime.now().strftime('%Y-%m-%d %H:%M')
    generate_html_report(df_parlay, df_raw, now_str, raw_pred_file)

if __name__ == "__main__":
    main()