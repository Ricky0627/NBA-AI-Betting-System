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
    'SAS': 'https://a.espncdn.com/i/teamlogos/nba/500/sas.png', 'TOR': 'https://a.espncdn.com/i/teamlogos/nba/500/tor.png',
    'UTA': 'https://a.espncdn.com/i/teamlogos/nba/500/utah.png', 'WAS': 'https://a.espncdn.com/i/teamlogos/nba/500/was.png',
    'UNK': 'https://a.espncdn.com/i/teamlogos/nba/500/nba.png'
}

def get_logo_html(abbr):
    url = LOGO_MAP.get(abbr, LOGO_MAP['UNK'])
    return f'<img src="{url}" class="team-logo" alt="{abbr}">'

def find_latest_file(pattern, exclude=None):
    files = glob.glob(pattern)
    if exclude:
        files = [f for f in files if exclude not in f]
    if not files: return None
    return max(files, key=os.path.getctime)

def calculate_units(signal):
    if "ROI King" in signal: return "⭐⭐ 2u"
    if "Value" in signal: return "⭐ 1u"
    if "High EV" in signal: return "✨ 0.5u"
    if "Anchor" in signal: return "⚓ 配腳"
    return "-"

def get_prob_text(prob_val):
    try:
        prob_pct = float(prob_val) * 100
    except:
        prob_pct = 50
    color_class = "text-success" if prob_pct >= 60 else "text-danger" if prob_pct <= 40 else "text-dark"
    return f'<span class="fw-bold {color_class}" style="font-size: 1.1rem;">{int(prob_pct)}%</span>'

def main():
    print("\n" + "="*60)
    print(" 🌐 戰情室網頁生成器 v3.7 (讀取優化串關版)")
    print("="*60)

    # 檔案路徑
    plan_file = find_latest_file("betting_plan/Betting_Plan_*.csv")
    history_file = "predictions_2026_full_report.csv"
    raw_pred_file = find_latest_file("predictions/predictions_*.csv", exclude="full_report")
    parlay_file = "Daily_Parlay_Recommendations.csv" # 這是 v960 的產出

    # --- 1. 歷史戰績 ---
    stats_html = ""
    if os.path.exists(history_file):
        df_hist = pd.read_csv(history_file)
        if 'Is_Correct' in df_hist.columns:
            total = len(df_hist)
            acc = df_hist['Is_Correct'].mean() * 100
            
            df_hist['date'] = pd.to_datetime(df_hist['date'])
            recent_acc = df_hist.sort_values('date', ascending=False).head(10)['Is_Correct'].mean() * 100
            high_acc = df_hist[df_hist['Confidence'].str.contains("High", na=False)]['Is_Correct'].mean() * 100
            
            stats_html = f"""
            <div class="row g-3 mb-4">
                <div class="col-md-3"><div class="stat-card border-primary">
                    <div class="stat-title">歷史總預測</div>
                    <div class="stat-value">{total}</div>
                </div></div>
                <div class="col-md-3"><div class="stat-card border-success">
                    <div class="stat-title">總體勝率</div>
                    <div class="stat-value">{acc:.1f}%</div>
                </div></div>
                <div class="col-md-3"><div class="stat-card border-info">
                    <div class="stat-title">近 10 場勝率</div>
                    <div class="stat-value">{recent_acc:.1f}%</div>
                </div></div>
                <div class="col-md-3"><div class="stat-card border-warning">
                    <div class="stat-title">高信心準確率</div>
                    <div class="stat-value">{high_acc:.1f}%</div>
                </div></div>
            </div>
            """

    # --- 2. 策略單 (Strategy) ---
    strategy_table_html = '<div class="text-center py-4 text-muted">今日無策略推薦</div>'
    if plan_file and os.path.exists(plan_file):
        df_plan = pd.read_csv(plan_file)
        if not df_plan.empty:
            df_plan['Logo'] = df_plan['Team'].apply(get_logo_html)
            df_plan['注碼'] = df_plan['Signal'].apply(calculate_units)
            df_plan['勝率'] = df_plan['Win%'].apply(get_prob_text)
            df_plan['EV'] = df_plan['EV'].apply(lambda x: f'<span class="fw-bold {"text-success" if x>0 else "text-muted"}">{x:+.2f}</span>')
            
            cols_show = ['Logo', 'Team', 'Loc', 'Opp', '勝率', 'Odds', 'EV', 'Signal', '注碼']
            rename = {'Team':'球隊', 'Loc':'主客', 'Opp':'對手', 'Odds':'賠率', 'Signal':'訊號'}
            
            strategy_table_html = df_plan[cols_show].rename(columns=rename).to_html(
                classes='table table-hover align-middle mb-0', index=False, escape=False, border=0
            )

    # --- 3. 全賽事預測 (All Games) ---
    raw_table_html = ""
    if raw_pred_file and os.path.exists(raw_pred_file):
        df_raw = pd.read_csv(raw_pred_file)
        if not df_raw.empty:
            # 嘗試填入賠率
            odds_map = {}
            match = re.search(r"predictions_(\d{4}-\d{2}-\d{2})\.csv", raw_pred_file)
            if match:
                odds_file = f"odds/odds_for_{match.group(1)}.csv"
                if os.path.exists(odds_file):
                    df_o = pd.read_csv(odds_file)
                    for _, r in df_o.iterrows():
                        odds_map[f"{r['Home_Abbr']}_{r['Away_Abbr']}"] = (r['Odds_Home'], r['Odds_Away'])
            
            def get_odds(row):
                k = f"{row['Home']}_{row['Away']}"
                kr = f"{row['Away']}_{row['Home']}"
                if k in odds_map: return odds_map[k]
                if kr in odds_map: return (odds_map[kr][1], odds_map[kr][0])
                return ("-", "-")
                
            od = df_raw.apply(get_odds, axis=1)
            df_raw['主賠率'] = [x[0] for x in od]
            df_raw['客賠率'] = [x[1] for x in od]

            df_raw['主隊'] = df_raw['Home'].apply(get_logo_html) + " " + df_raw['Home']
            df_raw['客隊'] = df_raw['Away'].apply(get_logo_html) + " " + df_raw['Away']
            df_raw['主勝率'] = df_raw['Home_Win_Prob'].apply(get_prob_text)
            
            cols = ['Date', '主隊', '主賠率', '客賠率', '客隊', '主勝率', 'Confidence']
            raw_table_html = df_raw[cols].rename(columns={'Date':'日期', 'Confidence':'信心'}).to_html(
                classes='table table-sm table-striped align-middle text-center', index=False, escape=False, border=0
            )

    # --- 4. 串關 (Parlay) - [v3.7 核心修正] ---
    parlay_html = '<div class="text-muted p-3">今日無串關推薦</div>'
    
    if os.path.exists(parlay_file):
        print(f" 🔗 讀取優化串關: {parlay_file}")
        df_parlay = pd.read_csv(parlay_file)
        
        if not df_parlay.empty:
            # 樣式優化
            def get_parlay_badge(ptype):
                if "黃金" in ptype: return f'<span class="badge bg-warning text-dark"><i class="fas fa-crown"></i> {ptype}</span>'
                if "高價值" in ptype: return f'<span class="badge bg-primary"><i class="fas fa-gem"></i> {ptype}</span>'
                if "穩健" in ptype: return f'<span class="badge bg-success"><i class="fas fa-check-circle"></i> {ptype}</span>'
                return f'<span class="badge bg-secondary">{ptype}</span>'

            df_parlay['類型'] = df_parlay['Type'].apply(get_parlay_badge)
            df_parlay['組合'] = df_parlay['Team_1'] + " + " + df_parlay['Team_2']
            df_parlay['期望值'] = df_parlay['Combined_EV'].apply(lambda x: f'<span class="fw-bold {"text-success" if x>0 else "text-muted"}">{x:+.2f}</span>')
            
            # 欄位對應 v960 的輸出
            p_cols = ['類型', '組合', 'Combined_Odds', '期望值']
            parlay_html = df_parlay[p_cols].rename(columns={'Combined_Odds':'賠率'}).to_html(
                classes='table table-bordered align-middle', index=False, escape=False, border=0
            )
        else:
            print(" ⚠️ 串關檔案為空")
    else:
        print(f" ⚠️ 找不到串關檔案 ({parlay_file})，請確認 v960 是否執行成功。")

    # --- 輸出 HTML ---
    update_time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M')
    
    html = f"""
    <!DOCTYPE html>
    <html lang="zh-Hant">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>NBA AI 戰情室</title>
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
        <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
        <link href="https://fonts.googleapis.com/css2?family=Teko:wght@400;600&family=Roboto:wght@400;500;700&display=swap" rel="stylesheet">
        <style>
            :root {{ --primary: #1a252f; --accent: #3498db; --bg: #f0f2f5; }}
            body {{ background-color: var(--bg); font-family: 'Roboto', sans-serif; color: #2c3e50; }}
            .navbar {{ background: #2c3e50; padding: 1rem; }}
            .navbar-brand {{ font-family: 'Teko', sans-serif; font-size: 1.8rem; letter-spacing: 1px; color: #fff !important; }}
            
            .stat-card {{ background: #fff; border-radius: 12px; padding: 20px; box-shadow: 0 4px 15px rgba(0,0,0,0.05); border-left: 5px solid #ddd; }}
            .stat-card.border-primary {{ border-left-color: #3498db; }}
            .stat-card.border-success {{ border-left-color: #2ecc71; }}
            .stat-card.border-info {{ border-left-color: #17a2b8; }}
            .stat-card.border-warning {{ border-left-color: #f1c40f; }}
            
            .stat-title {{ font-size: 0.85rem; text-transform: uppercase; color: #7f8c8d; font-weight: 600; }}
            .stat-value {{ font-size: 1.8rem; font-weight: 700; color: #2c3e50; }}
            
            .section-title {{ font-family: 'Teko', sans-serif; font-size: 1.5rem; border-left: 5px solid var(--accent); padding-left: 10px; margin-bottom: 20px; color: var(--primary); }}
            
            .card-box {{ background: #fff; border-radius: 12px; box-shadow: 0 4px 15px rgba(0,0,0,0.05); padding: 0; overflow: hidden; margin-bottom: 30px; }}
            .card-header-custom {{ background: #f8f9fa; padding: 15px 20px; border-bottom: 1px solid #eee; font-weight: 600; display: flex; justify-content: space-between; align-items: center; }}
            
            .team-logo {{ width: 30px; height: 30px; object-fit: contain; }}
            
            table {{ margin-bottom: 0 !important; }}
            thead th {{ background: #fdfdfd !important; font-size: 0.85rem; color: #999; text-transform: uppercase; }}
            
            footer {{ margin-top: 50px; padding: 20px; text-align: center; color: #aaa; font-size: 0.9rem; }}
        </style>
    </head>
    <body>

    <nav class="navbar navbar-dark mb-4">
        <div class="container">
            <a class="navbar-brand" href="#"><i class="fas fa-basketball-ball me-2 text-warning"></i> NBA AI 戰情室</a>
            <span class="text-white-50 small">Updated: {update_time}</span>
        </div>
    </nav>

    <div class="container">
        {stats_html}

        <div class="row">
            <div class="col-lg-8">
                <div class="section-title">今日核心策略 (Strategy)</div>
                
                <div class="card-box">
                    <div class="card-header-custom text-success">
                        <span><i class="fas fa-crosshairs me-2"></i>最佳單場推薦</span>
                        <span class="badge bg-success">Top Picks</span>
                    </div>
                    <div class="table-responsive">
                        {strategy_table_html}
                    </div>
                </div>
                
                <div class="card-box">
                    <div class="card-header-custom text-primary">
                        <span><i class="fas fa-link me-2"></i>最佳串關推薦 (Best Parlays)</span>
                        <span class="badge bg-warning text-dark">Optimization: 60% ROI Strategy</span>
                    </div>
                    {parlay_html}
                </div>
            </div>

            <div class="col-lg-4">
                <div class="section-title">全賽事預測 (All Games)</div>
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
            NBA AI System v3.7 • Powered by Random Forest & Parlay Optimizer
        </footer>
    </div>

    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
    </body>
    </html>
    """

    with open('index.html', 'w', encoding='utf-8') as f:
        f.write(html)
    
    print(" [V] 戰情室 index.html 生成完畢！")

if __name__ == "__main__":
    main()