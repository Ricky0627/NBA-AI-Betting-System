import pandas as pd
import os
import glob
import datetime
import numpy as np

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

def get_prob_bar(prob_val):
    try:
        prob_pct = float(prob_val) * 100
    except:
        prob_pct = 50
    
    color = "bg-success" if prob_pct >= 65 else "bg-warning" if prob_pct >= 50 else "bg-danger"
    return f'''
    <div class="d-flex align-items-center" style="min-width:100px;">
        <span class="me-2 fw-bold small">{int(prob_pct)}%</span>
        <div class="progress flex-grow-1" style="height: 6px;">
            <div class="progress-bar {color}" role="progressbar" style="width: {prob_pct}%"></div>
        </div>
    </div>
    '''

def main():
    print("\n" + "="*60)
    print(" 🌐 戰情室網頁生成器 v3.1 (修正版)")
    print(" 🎯 修復 KeyError: Team_1 問題")
    print("="*60)

    # --- 1. 讀取檔案 ---
    plan_file = find_latest_file("Betting_Plan_*.csv")
    parlay_file = find_latest_file("Daily_Parlay_Recommendations.csv")
    history_file = "predictions_2026_full_report.csv"
    raw_pred_file = find_latest_file("predictions_*.csv", exclude="full_report")

    # --- 2. 處理歷史戰績 (History Stats) ---
    stats_html = ""
    overall_acc = 0
    total_games_hist = 0
    
    if os.path.exists(history_file):
        print(f" 📜 讀取歷史戰績: {history_file}")
        df_hist = pd.read_csv(history_file)
        
        if 'Is_Correct' in df_hist.columns:
            total_games_hist = len(df_hist)
            overall_acc = df_hist['Is_Correct'].mean() * 100
            
            df_hist['date'] = pd.to_datetime(df_hist['date'])
            df_recent = df_hist.sort_values('date', ascending=False).head(10)
            recent_acc = df_recent['Is_Correct'].mean() * 100
            
            high_conf = df_hist[df_hist['Confidence'].str.contains("High", na=False)]
            high_acc = high_conf['Is_Correct'].mean() * 100 if not high_conf.empty else 0
            
            stats_html = f"""
            <div class="row g-3 mb-4">
                <div class="col-md-3"><div class="stat-card border-primary">
                    <div class="stat-title">歷史總預測</div>
                    <div class="stat-value">{total_games_hist} <span class="stat-unit">場</span></div>
                </div></div>
                <div class="col-md-3"><div class="stat-card border-success">
                    <div class="stat-title">總體勝率</div>
                    <div class="stat-value">{overall_acc:.1f}%</div>
                    <div class="progress mt-2" style="height:4px;"><div class="progress-bar bg-success" style="width:{overall_acc}%"></div></div>
                </div></div>
                <div class="col-md-3"><div class="stat-card border-info">
                    <div class="stat-title">近 10 場勝率</div>
                    <div class="stat-value">{recent_acc:.1f}%</div>
                    <div class="progress mt-2" style="height:4px;"><div class="progress-bar bg-info" style="width:{recent_acc}%"></div></div>
                </div></div>
                <div class="col-md-3"><div class="stat-card border-warning">
                    <div class="stat-title">高信心準確率</div>
                    <div class="stat-value">{high_acc:.1f}%</div>
                    <div class="progress mt-2" style="height:4px;"><div class="progress-bar bg-warning" style="width:{high_acc}%"></div></div>
                </div></div>
            </div>
            """
        else:
            stats_html = '<div class="alert alert-warning">歷史檔案缺少 Is_Correct 欄位。</div>'
    else:
        stats_html = '<div class="alert alert-secondary">尚無歷史戰績檔案。</div>'

    # --- 3. 處理策略單 (Strategy Table) ---
    strategy_table_html = '<div class="text-center py-4 text-muted">今日無策略推薦</div>'
    if plan_file and os.path.exists(plan_file):
        print(f" 🎯 策略單: {plan_file}")
        df_plan = pd.read_csv(plan_file)
        if not df_plan.empty:
            df_plan['Logo'] = df_plan['Team'].apply(get_logo_html)
            df_plan['注碼'] = df_plan['Signal'].apply(calculate_units)
            df_plan['勝率圖'] = df_plan['Win%'].apply(get_prob_bar)
            df_plan['EV'] = df_plan['EV'].apply(lambda x: f'<span class="fw-bold {"text-success" if x>0 else "text-muted"}">{x:+.2f}</span>')
            
            cols_show = ['Logo', 'Team', 'Loc', 'Opp', '勝率圖', 'Odds', 'EV', 'Signal', '注碼']
            rename = {'Team':'球隊', 'Loc':'主客', 'Opp':'對手', 'Odds':'賠率', 'Signal':'訊號'}
            
            strategy_table_html = df_plan[cols_show].rename(columns=rename).to_html(
                classes='table table-hover align-middle mb-0', index=False, escape=False, border=0
            )

    # --- 4. 處理今日所有預測 (All Predictions) ---
    raw_table_html = ""
    if raw_pred_file and os.path.exists(raw_pred_file):
        print(f" 🔮 原始預測: {raw_pred_file}")
        df_raw = pd.read_csv(raw_pred_file)
        if not df_raw.empty:
            df_raw['主隊'] = df_raw['Home'].apply(get_logo_html) + " " + df_raw['Home']
            df_raw['客隊'] = df_raw['Away'].apply(get_logo_html) + " " + df_raw['Away']
            df_raw['主勝率'] = df_raw['Home_Win_Prob'].apply(get_prob_bar)
            
            cols_raw = ['Date', '主隊', '客隊', '主勝率', 'Confidence']
            df_raw_show = df_raw[cols_raw].rename(columns={'Date':'日期', 'Confidence':'信心等級'})
            
            raw_table_html = df_raw_show.to_html(
                classes='table table-sm table-striped align-middle text-center', index=False, escape=False, border=0
            )

    # --- 5. 處理串關 (Parlay) - [修正點] ---
    parlay_html = '<div class="text-muted p-3">今日無串關推薦</div>'
    if parlay_file and os.path.exists(parlay_file):
        df_parlay = pd.read_csv(parlay_file)
        if not df_parlay.empty:
            print(f" 🔗 讀取串關檔: {parlay_file}")
            
            # --- 相容性處理 ---
            # 檢查是否存在 P1/P2 或是 Team_1/Team_2
            if 'P1' in df_parlay.columns:
                df_parlay['Team_1'] = df_parlay['P1']
                df_parlay['Team_2'] = df_parlay['P2']
            if 'Odds' in df_parlay.columns and 'Combined_Odds' not in df_parlay.columns:
                df_parlay['Combined_Odds'] = df_parlay['Odds']
            # ------------------

            df_parlay['組合'] = df_parlay['Team_1'] + ' ✚ ' + df_parlay['Team_2']
            df_parlay['類型'] = df_parlay['Type'].apply(lambda x: f'<span class="badge bg-dark">{x}</span>')
            
            p_cols = ['類型', '組合', 'Combined_Odds']
            parlay_html = df_parlay[p_cols].rename(columns={'Combined_Odds':'賠率'}).to_html(
                classes='table table-bordered align-middle', index=False, escape=False, border=0
            )

    # --- 6. 組合 HTML ---
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
            .stat-unit {{ font-size: 1rem; color: #95a5a6; font-weight: normal; }}
            
            .section-title {{ font-family: 'Teko', sans-serif; font-size: 1.5rem; border-left: 5px solid var(--accent); padding-left: 10px; margin-bottom: 20px; color: var(--primary); }}
            
            .card-box {{ background: #fff; border-radius: 12px; box-shadow: 0 4px 15px rgba(0,0,0,0.05); padding: 0; overflow: hidden; margin-bottom: 30px; }}
            .card-header-custom {{ background: #f8f9fa; padding: 15px 20px; border-bottom: 1px solid #eee; font-weight: 600; display: flex; justify-content: space-between; align-items: center; }}
            
            .team-logo {{ width: 30px; height: 30px; object-fit: contain; }}
            
            /* Table Styles */
            table {{ margin-bottom: 0 !important; }}
            thead th {{ background: #fdfdfd !important; font-size: 0.85rem; color: #999; text-transform: uppercase; }}
            
            .badge-roi {{ background: #8e44ad; color: #fff; }}
            .badge-val {{ background: #27ae60; color: #fff; }}
            .badge-high {{ background: #c0392b; color: #fff; }}
            
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
                    <div class="card-header-custom text-primary">
                        <span><i class="fas fa-link me-2"></i>精選串關</span>
                        <span class="badge bg-secondary">Parlay</span>
                    </div>
                    {parlay_html}
                </div>

                <div class="card-box">
                    <div class="card-header-custom text-success">
                        <span><i class="fas fa-crosshairs me-2"></i>最佳單場推薦</span>
                        <span class="badge bg-success">Best Singles</span>
                    </div>
                    <div class="table-responsive">
                        {strategy_table_html}
                    </div>
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
            NBA AI System v3.0 • Powered by Random Forest & Grid Search Strategy
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