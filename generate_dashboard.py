import pandas as pd
import os
import glob
import datetime
import numpy as np
import re
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from pandas.plotting import register_matplotlib_converters

# 註冊 Matplotlib 日期轉換器
register_matplotlib_converters()

# 設定 Matplotlib 不使用視窗介面 (避免在伺服器端報錯)
plt.switch_backend('Agg')

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
    return LOGO_MAP.get(abbr, "https://a.espncdn.com/i/teamlogos/nba/500/nba.png")

def format_ev_color(ev_val):
    try:
        val = float(ev_val)
        if val >= 0.10: return "text-success fw-bold"
        if val > 0: return "text-primary"
        return "text-muted"
    except:
        return "text-muted"

def format_grade_badge(grade):
    if "👑" in grade: return "bg-warning text-dark"
    if "💎" in grade: return "bg-info text-dark"
    if "🛡️" in grade: return "bg-success"
    if "⚖️" in grade: return "bg-primary"
    if "🏹" in grade: return "bg-danger"
    return "bg-secondary"

# --- 修正版 merge_odds_data 函數 ---
def merge_odds_data(df_pred, odds_file, pred_filename=None):
    if df_pred.empty or not os.path.exists(odds_file):
        return df_pred

    try:
        df_o = pd.read_csv(odds_file)
        
        fixed_date = None
        date_match = re.search(r'odds_for_(\d{4}-\d{2}-\d{2})\.csv', odds_file)
        if date_match:
            fixed_date = date_match.group(1)

        if 'date' in df_o.columns and 'Date' not in df_o.columns:
            df_o = df_o.rename(columns={'date': 'Date'})
        
        if 'Date' not in df_o.columns and fixed_date:
            df_o['Date'] = fixed_date
            print(f"✅ 修正：賠率檔缺少日期欄位，已強制加上 'Date' = {fixed_date}")
        
        odds_map = {}
        for _, row in df_o.iterrows():
            d = str(row['Date'])
            h = normalize_team(row['Home_Abbr'])
            a = normalize_team(row['Away_Abbr'])
            odds_map[f"{d}_{h}"] = row['Odds_Home']
            odds_map[f"{d}_{a}"] = row['Odds_Away']
        
        home_odds_list = []
        away_odds_list = []
        home_ev_list = []
        away_ev_list = []

        default_date = None
        if pred_filename:
            match = re.search(r"predictions_(\d{4}-\d{2}-\d{2})\.csv", pred_filename)
            if match:
                default_date = match.group(1)

        for _, row in df_pred.iterrows():
            d = default_date
            if not d:
                if 'date' in row: d = pd.to_datetime(row['date']).strftime('%Y-%m-%d')
                elif 'Date' in row: d = pd.to_datetime(row['Date']).strftime('%Y-%m-%d')
            
            if not d:
                home_odds_list.append("-")
                away_odds_list.append("-")
                home_ev_list.append(None)
                away_ev_list.append(None)
                continue

            h = normalize_team(row['Home'])
            a = normalize_team(row['Away'])
            
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
        return df_pred

# --- 數據計算功能 ---
def calculate_advanced_stats():
    """從 predictions_2026_full_report.csv 計算進階統計數據"""
    csv_file = "predictions_2026_full_report.csv"
    if not os.path.exists(csv_file):
        return 0, 0.0, 0.0, "N/A"

    try:
        df = pd.read_csv(csv_file)
        if df.empty: return 0, 0.0, 0.0, "N/A"
        
        # 確保依日期排序
        df['date'] = pd.to_datetime(df['date'])
        df = df.sort_values('date')
        
        # 1. 總場次 & 總勝率
        total_games = len(df)
        total_wins = df['Is_Correct'].sum()
        win_rate = (total_wins / total_games) * 100 if total_games > 0 else 0.0
        
        # 2. 近十場勝率 (Last 10)
        last_10 = df.tail(10)
        l10_wins = last_10['Is_Correct'].sum()
        l10_games = len(last_10)
        l10_rate = (l10_wins / l10_games) * 100 if l10_games > 0 else 0.0
        
        # 3. 昨日戰績 (Last Day Record)
        last_date = df['date'].iloc[-1]
        last_day_df = df[df['date'] == last_date]
        day_wins = last_day_df['Is_Correct'].sum()
        day_losses = len(last_day_df) - day_wins
        day_record_str = f"{day_wins}-{day_losses}"
        
        return int(total_games), win_rate, l10_rate, day_record_str
        
    except Exception as e:
        print(f"⚠️ 計算進階數據時出錯: {e}")
        return 0, 0.0, 0.0, "N/A"

def generate_strategy_table_html():
    csv_file = "Strategy_Performance_Report.csv"
    if not os.path.exists(csv_file):
        return '<p class="text-muted text-center my-3">尚未執行 v980，無策略數據</p>'
    
    try:
        df = pd.read_csv(csv_file)
        
        def format_roi(val):
            try:
                roi_num = float(val.replace('%', ''))
                if roi_num > 0: return f'<span class="text-success fw-bold">{val}</span>'
                if roi_num < 0: return f'<span class="text-danger fw-bold">{val}</span>'
                return val
            except: return val

        def format_profit(val):
            try:
                profit_num = float(val.replace('u', ''))
                if profit_num > 0: return f'<span class="text-success">{val}</span>'
                if profit_num < 0: return f'<span class="text-danger">{val}</span>'
                return val
            except: return val

        rows_html = ""
        for _, row in df.iterrows():
            roi_html = format_roi(str(row['ROI']))
            profit_html = format_profit(str(row['總獲利 (單位)']))
            rows_html += f"""
            <tr>
                <td class="fw-bold">{row['策略名稱']}</td>
                <td class="text-center">{row['場次']}</td>
                <td class="text-center">{row['勝率']}</td>
                <td class="text-center">{profit_html}</td>
                <td class="text-center">{roi_html}</td>
            </tr>
            """
        return f"""
        <table class="table table-hover table-sm mb-0 align-middle">
            <thead class="table-light small">
                <tr>
                    <th>策略名稱</th>
                    <th class="text-center">場次</th>
                    <th class="text-center">勝率</th>
                    <th class="text-center">總獲利</th>
                    <th class="text-center">ROI</th>
                </tr>
            </thead>
            <tbody>{rows_html}</tbody>
        </table>
        """
    except Exception as e:
        return f'<p class="text-danger text-center">讀取策略報告失敗: {e}</p>'

def generate_best_combos_table_html():
    csv_file = "Best_Strategy_Combos_Unique.csv"
    if not os.path.exists(csv_file):
        return ""
    
    try:
        df = pd.read_csv(csv_file)
        if df.empty: return ""
        
        rows_html = ""
        for _, row in df.iterrows():
            if 'ROI' not in row or '勝率' not in row or '場次' not in row:
                continue

            roi_val = float(row['ROI'])
            roi_class = "text-success fw-bold" if roi_val > 0 else "text-danger"
            
            rows_html += f"""
            <tr class="combo-row">
                <td class="small fw-bold">{row['策略_A']} + {row['策略_B']}</td>
                <td class="text-center {roi_class}">{row['ROI']:.1f}%</td>
                <td class="text-center text-primary">{row['勝率']:.1f}%</td>
                <td class="text-center text-muted">{row['場次']}</td>
            </tr>
            """
            
        return f"""
        <div class="card-box mt-4 mb-4">
            <div class="card-header-custom text-warning" style="background: linear-gradient(to right, #fff, #fff3cd);">
                <span><i class="fas fa-crown me-2 text-warning"></i>歷史最強策略組合 (Top Combos)</span>
            </div>
            <div class="table-responsive">
                <table class="table table-hover table-sm mb-0 align-middle" id="bestCombosTable">
                    <thead class="table-light small">
                        <tr>
                            <th>策略組合</th>
                            <th class="text-center">ROI</th>
                            <th class="text-center">勝率</th>
                            <th class="text-center">場次</th>
                        </tr>
                    </thead>
                    <tbody>{rows_html}</tbody>
                </table>
            </div>
            <div class="d-flex justify-content-between align-items-center p-2 bg-light border-top">
                <button class="btn btn-sm btn-outline-secondary" id="comboPrev"><i class="fas fa-chevron-left"></i></button>
                <span class="small text-muted" id="comboPageNum">1 / 1</span>
                <button class="btn btn-sm btn-outline-secondary" id="comboNext"><i class="fas fa-chevron-right"></i></button>
            </div>
        </div>

        <script>
        document.addEventListener('DOMContentLoaded', function() {{
            const table = document.getElementById('bestCombosTable');
            if (!table) return;
            const tbody = table.querySelector('tbody');
            const rows = Array.from(tbody.querySelectorAll('tr.combo-row'));
            const pageSize = 10;
            let currentPage = 1;
            const totalPages = Math.ceil(rows.length / pageSize);
            
            const btnPrev = document.getElementById('comboPrev');
            const btnNext = document.getElementById('comboNext');
            const pageInd = document.getElementById('comboPageNum');

            function renderTable(page) {{
                rows.forEach((row, index) => {{
                    if (index >= (page - 1) * pageSize && index < page * pageSize) {{
                        row.style.display = '';
                    }} else {{
                        row.style.display = 'none';
                    }}
                }});
                pageInd.textContent = page + ' / ' + totalPages;
                btnPrev.disabled = (page === 1);
                btnNext.disabled = (page === totalPages);
            }}
            
            btnPrev.addEventListener('click', () => {{
                if (currentPage > 1) {{ currentPage--; renderTable(currentPage); }}
            }});
            
            btnNext.addEventListener('click', () => {{
                if (currentPage < totalPages) {{ currentPage++; renderTable(currentPage); }}
            }});
            
            renderTable(1);
        }});
        </script>
        """
    except Exception as e:
        print(f"⚠️ 讀取最佳組合失敗: {e}")
        return ""

# --- 主功能：生成 HTML 報告 (v4.7 Final) ---
def generate_html_report(df_parlay, df_raw, last_updated_time, raw_pred_file):
    
    total_games, avg_win_rate, l10_rate, day_record = calculate_advanced_stats()
    
    l10_color = "text-success" if l10_rate >= 50 else "text-danger"
    if l10_rate >= 70: l10_color = "text-success fw-bold"
    
    stats_cards_html = f"""
    <div class="row mb-3">
        <div class="col-6 col-lg-3 mb-2">
            <div class="card-box p-3 border-start border-4 border-primary h-100">
                <div class="d-flex justify-content-between align-items-center">
                    <div>
                        <div class="text-muted small text-uppercase fw-bold">總場次 (Total)</div>
                        <div class="h3 mb-0 fw-bold text-dark">{total_games}</div>
                    </div>
                    <div class="text-primary fs-1 opacity-25"><i class="fas fa-basketball-ball"></i></div>
                </div>
            </div>
        </div>
        <div class="col-6 col-lg-3 mb-2">
            <div class="card-box p-3 border-start border-4 border-success h-100">
                <div class="d-flex justify-content-between align-items-center">
                    <div>
                        <div class="text-muted small text-uppercase fw-bold">平均勝率 (Avg)</div>
                        <div class="h3 mb-0 fw-bold text-success">{avg_win_rate:.1f}%</div>
                    </div>
                    <div class="text-success fs-1 opacity-25"><i class="fas fa-chart-pie"></i></div>
                </div>
            </div>
        </div>
        <div class="col-6 col-lg-3 mb-2">
            <div class="card-box p-3 border-start border-4 border-info h-100">
                <div class="d-flex justify-content-between align-items-center">
                    <div>
                        <div class="text-muted small text-uppercase fw-bold">近十場 (L10)</div>
                        <div class="h3 mb-0 {l10_color}">{l10_rate:.0f}%</div>
                    </div>
                    <div class="text-info fs-1 opacity-25"><i class="fas fa-fire-alt"></i></div>
                </div>
            </div>
        </div>
        <div class="col-6 col-lg-3 mb-2">
            <div class="card-box p-3 border-start border-4 border-warning h-100">
                <div class="d-flex justify-content-between align-items-center">
                    <div>
                        <div class="text-muted small text-uppercase fw-bold">昨日戰績 (Last Day)</div>
                        <div class="h3 mb-0 fw-bold text-dark">{day_record}</div>
                    </div>
                    <div class="text-warning fs-1 opacity-25"><i class="fas fa-history"></i></div>
                </div>
            </div>
        </div>
    </div>
    """

    parlay_html = ""
    if df_parlay.empty:
        parlay_html = """<div class="alert alert-warning text-center" role="alert"><i class="fas fa-exclamation-triangle me-2"></i>今日無符合高價值策略的串關組合</div>"""
    else:
        parlay_rows = ""
        for _, row in df_parlay.iterrows():
            t1, t2 = row['Team_1'], row['Team_2']
            # 取出新欄位資料
            strategy = row.get('Strategy_Combo', '-')
            max_roi = row.get('Max_ROI', 0)
            
            # 格式化 ROI
            try:
                roi_val = float(max_roi)
                roi_str = f"{roi_val:.1f}%"
            except:
                roi_str = str(max_roi)
            
            logo1 = f'<img src="{get_team_logo(t1)}" class="team-logo-sm">'
            logo2 = f'<img src="{get_team_logo(t2)}" class="team-logo-sm">'
            ev_class = format_ev_color(row['Combined_EV'])
            
            parlay_rows += f"""
            <tr class="align-middle">
                <td><div class="d-flex align-items-center">{logo1} <span class="fw-bold mx-1">{t1}</span> <span class="text-muted mx-2">+</span> {logo2} <span class="fw-bold mx-1">{t2}</span></div></td>
                <td class="text-center fw-bold">{row['Combined_Odds']:.2f}</td>
                <td class="text-center {ev_class}">{row['Combined_EV']:+.2f}</td>
                <td class="text-center small text-muted">{strategy}</td>
                <td class="text-center fw-bold text-success">{roi_str}</td>
            </tr>
            """
        
        parlay_html = f"""
        <table class="table table-hover mb-0">
            <thead class="table-light">
                <tr>
                    <th width="30%">組合 (Combo)</th>
                    <th width="15%" class="text-center">總賠率</th>
                    <th width="15%" class="text-center">總期望值</th>
                    <th width="25%" class="text-center">策略組合</th>
                    <th width="15%" class="text-center">Max ROI</th>
                </tr>
            </thead>
            <tbody>{parlay_rows}</tbody>
        </table>
        """

    if not df_raw.empty:
        raw_rows = ""
        for _, row in df_raw.iterrows():
            h, a = row['Home'], row['Away']
            prob = float(row['Home_Win_Prob'])
            odds_h, odds_a = row.get('Odds_Home', '-'), row.get('Odds_Away', '-')
            ev_h_val, ev_a_val = row.get('EV_Home'), row.get('EV_Away')
            
            def fmt_ev(val):
                if val is None or val == "-": return "-"
                try: return f'<span class="{"text-success fw-bold" if float(val)>0 else "text-muted"}">{float(val):+.2f}</span>'
                except: return "-"

            prob_pct = prob * 100
            bar_color = "bg-success" if prob > 0.5 else "bg-danger"
            win_text = f"{h} ({prob:.1%})" if prob > 0.5 else f"{a} ({1-prob:.1%})"
            raw_rows += f"""<tr><td class="text-center"><img src="{get_team_logo(h)}" class="team-logo-xs"> {h}</td><td class="text-center"><img src="{get_team_logo(a)}" class="team-logo-xs"> {a}</td><td style="width: 30%;"><div class="d-flex justify-content-between small mb-1"><span>{win_text}</span></div><div class="progress" style="height: 6px;"><div class="progress-bar {bar_color}" role="progressbar" style="width: {prob_pct if prob>0.5 else 100-prob_pct}%"></div></div></td><td class="text-center small">{odds_h}</td><td class="text-center small">{odds_a}</td><td class="text-center small">{fmt_ev(ev_h_val)}</td><td class="text-center small">{fmt_ev(ev_a_val)}</td></tr>"""
        raw_table_html = f"""<table class="table table-sm table-striped align-middle"><thead class="table-dark small"><tr><th class="text-center">主隊</th><th class="text-center">客隊</th><th>預測勝率</th><th class="text-center">主賠</th><th class="text-center">客賠</th><th class="text-center">主EV</th><th class="text-center">客EV</th></tr></thead><tbody>{raw_rows}</tbody></table>"""
    else:
        raw_table_html = "<p class='text-center text-muted my-3'>今日無賽事或尚未預測</p>"

    strategy_perf_html = generate_strategy_table_html()
    best_combos_html = generate_best_combos_table_html()
    
    # 串關策略儀表板區塊 (取代 Performance Trend)
    parlay_dashboard_html = ""
    if os.path.exists('chart_parlay_dashboard.png'):
        parlay_dashboard_html = f"""
        <div class="card-box mt-3">
            <div class="card-header-custom text-dark"><span><i class="fas fa-chart-area me-2"></i>串關策略儀表板 (Parlay Performance)</span></div>
            <div class="card-body p-2">
                <img src="chart_parlay_dashboard.png" class="img-fluid rounded" alt="串關策略儀表板" style="width:100%">
            </div>
        </div>
        """
    
    chart_profit_html = ""
    if os.path.exists('chart_strategy_dashboard.png'):
        chart_profit_html = f"""
        <div class="card-box mt-4">
            <div class="card-header-custom text-info"><span><i class="fas fa-chart-line me-2"></i>策略與勝率綜合儀表板 (Strategy & Win Rate Dashboard)</span></div>
            <div class="card-body p-2"><img src="chart_strategy_dashboard.png" class="img-fluid rounded" alt="策略儀表板" style="width: 100%;"></div>
        </div>
        """

    html_content = f"""
    <!DOCTYPE html>
    <html lang="zh-TW">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>NBA AI 戰情室 v4.7</title>
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
        <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
        <style>
            body {{ background-color: #f4f6f9; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; }}
            .header-bar {{ background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%); color: white; padding: 20px 0; margin-bottom: 25px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }}
            .card-box {{ background: white; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.05); margin-bottom: 20px; overflow: hidden; }}
            .card-header-custom {{ padding: 15px 20px; font-weight: bold; border-bottom: 1px solid #eee; display: flex; justify-content: space-between; align-items: center; }}
            .team-logo-sm {{ width: 30px; height: 30px; object-fit: contain; }}
            .team-logo-xs {{ width: 24px; height: 24px; object-fit: contain; margin-right: 5px; }}
            .section-title {{ font-size: 1.1rem; color: #555; margin-bottom: 15px; font-weight: 600; border-left: 4px solid #1e3c72; padding-left: 10px; }}
            footer {{ text-align: center; color: #888; padding: 20px; font-size: 0.9rem; }}
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
        {stats_cards_html}

        <div class="row">
            <div class="col-lg-6">
                <div class="section-title">今日核心推薦 (Core Recommendations)</div>
                <div class="card-box">
                    <div class="card-header-custom text-primary"><span><i class="fas fa-link me-2"></i>最佳串關組合 (Best Parlays)</span><span class="badge bg-warning text-dark">AI Optimized</span></div>
                    <div class="p-0">{parlay_html}</div>
                </div>
                
                <div class="section-title">策略績效回測 (Backtest Performance)</div>
                <div class="card-box">
                    <div class="card-header-custom text-success"><span><i class="fas fa-list-ol me-2"></i>各策略歷史數據 (Stats)</span></div>
                    <div class="table-responsive" style="max-height: 400px; overflow-y: auto;">
                        {strategy_perf_html}
                    </div>
                </div>
                
                {chart_profit_html}
            </div>

            <div class="col-lg-6">
                <div class="section-title">全賽事預測 & 賠率 (All Games & Odds)</div>
                <div class="card-box">
                    <div class="card-header-custom text-secondary"><span><i class="fas fa-list me-2"></i>今日總覽</span><span class="badge bg-light text-dark">{os.path.basename(raw_pred_file) if raw_pred_file else "No Data"}</span></div>
                    <div class="table-responsive" style="max-height: 800px; overflow-y: auto;">{raw_table_html}</div>
                </div>

                {best_combos_html}
                {parlay_dashboard_html}
            </div>
        </div>

        <footer>NBA AI System v4.7 • Powered by Random Forest & Parlay Optimizer</footer>
    </div>

    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
    </body>
    </html>
    """

    with open('index.html', 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    print(f"✅ Dashboard 已生成: index.html")

def main():
    print("\n🌐 啟動戰情室網頁生成器 v4.7 (Updated for Parlay Dashboard)...")
    
    parlay_file = "Daily_Parlay_Recommendations.csv"
    if os.path.exists(parlay_file):
        try: df_parlay = pd.read_csv(parlay_file)
        except pd.errors.EmptyDataError: df_parlay = pd.DataFrame()
    else: df_parlay = pd.DataFrame()

    files = glob.glob(os.path.join("predictions", "predictions_*.csv"))
    files = [f for f in files if "full_" not in f]
    files.sort(key=lambda x: os.path.getctime(x), reverse=True)
    raw_pred_file = files[0] if files else None
    df_raw = pd.read_csv(raw_pred_file) if raw_pred_file else pd.DataFrame()
    
    target_odds_file = "odds_2026_full_season.csv" 
    if raw_pred_file:
        match = re.search(r"predictions_(\d{4}-\d{2}-\d{2})\.csv", raw_pred_file)
        if match:
            pred_date = match.group(1)
            daily_odds_path = os.path.join("odds", f"odds_for_{pred_date}.csv")
            if os.path.exists(daily_odds_path):
                target_odds_file = daily_odds_path
                print(f"✅ 優先使用當日賠率檔: {target_odds_file}")
            else:
                print(f"⚠️ 無當日賠率檔，使用賽季總表: {target_odds_file}")

    if not df_raw.empty and os.path.exists(target_odds_file):
        print(f"🔗 正在合併賠率資訊...")
        df_raw = merge_odds_data(df_raw, target_odds_file, raw_pred_file)
    
    now_str = datetime.datetime.now().strftime('%Y-%m-%d %H:%M')
    generate_html_report(df_parlay, df_raw, now_str, raw_pred_file)

if __name__ == "__main__":
    main()
