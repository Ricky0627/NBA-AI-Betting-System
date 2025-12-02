import pandas as pd
import os
import glob
import datetime

def find_latest_betting_plan():
    """尋找最新的 Betting_Plan_YYYY-MM-DD.csv"""
    # 這裡的邏輯是找 Betting_Plan 開頭的檔案
    files = glob.glob("Betting_Plan_*.csv")
    if not files: return None
    # 依檔案修改時間排序，找最新的
    return max(files, key=os.path.getctime)

def main():
    print("\n" + "="*60)
    print(" 🌐 獨立網頁報表生成器 (Dashboard Generator)")
    print("="*60)

    # 1. 自動尋找最新的出單計畫表
    target_file = find_latest_betting_plan()

    if not target_file:
        print(f" [!] 找不到任何 Betting_Plan 檔案，無法生成網頁。")
        return

    print(f" 📄 讀取最新戰報數據源: {target_file}")

    try:
        df = pd.read_csv(target_file)
        
        # --- 數據預處理 ---
        total_games = len(df)
        
        # 計算推薦場次 (有 BET 字眼的)
        bet_count = df[df['Signal'].astype(str).str.contains("BET", case=False, na=False)].shape[0]
        
        # 找出最大 EV
        max_ev = df['EV'].max() if 'EV' in df.columns else 0

        # 格式化顯示: 勝率
        if 'Win%' in df.columns:
            df['勝率'] = (df['Win%'] * 100).fillna(0).astype(int).astype(str) + '%'
        
        # 重命名欄位以符合閱讀習慣 (與 Betting_Plan 的欄位對應)
        rename_map = {
            'Date': '日期', 'Team': '球隊', 'Opp': '對手', 'Loc': '主客', 
            'Odds': '賠率', 'EV': '期望值', 'Signal': '策略訊號', 'Rank': '評級'
        }
        display_df = df.rename(columns=rename_map)
        
        # 選取要在網頁顯示的欄位
        show_cols = ['球隊', '主客', '對手', '勝率', '賠率', '期望值', '策略訊號']
        # 防呆：只選存在的欄位
        display_df = display_df[[c for c in show_cols if c in display_df.columns]]

        # 轉 HTML 表格字串 (不帶樣式，樣式由下方的 DataTables 控制)
        table_html = display_df.to_html(classes='table table-hover align-middle', index=False, table_id='predictionTable', border=0)

        # 取得當前時間
        update_time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M')

        # --- HTML 模板 (包含 CSS/JS) ---
        html_content = f"""
        <!DOCTYPE html>
        <html lang="zh-Hant">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>NBA AI 每日戰報</title>
            <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
            <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
            <link href="https://cdn.datatables.net/1.13.4/css/dataTables.bootstrap5.min.css" rel="stylesheet">
            
            <style>
                :root {{ --primary: #2c3e50; --accent: #3498db; --success: #27ae60; --danger: #e74c3c; --bg: #f8f9fa; }}
                body {{ background-color: var(--bg); font-family: 'Segoe UI', sans-serif; color: #333; }}
                .navbar {{ background: linear-gradient(to right, #141E30, #243B55); }}
                .stat-card {{ background: white; border-radius: 10px; padding: 20px; box-shadow: 0 4px 6px rgba(0,0,0,0.05); border-left: 5px solid var(--accent); margin-bottom: 20px; }}
                .table-container {{ background: white; border-radius: 15px; padding: 25px; box-shadow: 0 5px 15px rgba(0,0,0,0.05); }}
                
                /* 策略標籤樣式 */
                .badge-roi {{ background-color: #8e44ad; color: white; padding: 8px 12px; border-radius: 20px; font-weight: 600; font-size: 0.9em; }}
                .badge-val {{ background-color: var(--success); color: white; padding: 8px 12px; border-radius: 20px; font-weight: 600; font-size: 0.9em; }}
                .badge-high {{ background-color: var(--danger); color: white; padding: 8px 12px; border-radius: 20px; font-weight: 600; font-size: 0.9em; }}
                .badge-anchor {{ background-color: #2980b9; color: white; padding: 8px 12px; border-radius: 20px; font-weight: 600; font-size: 0.9em; }}
                
                .fw-bold {{ font-weight: 700 !important; }}
                .text-win {{ color: var(--success); font-weight: bold; }}
                
                /* 表格優化 */
                table.dataTable thead th {{ background-color: #f1f2f6; border-bottom: 2px solid #ddd; }}
            </style>
        </head>
        <body>

        <nav class="navbar navbar-dark mb-4">
            <div class="container">
                <a class="navbar-brand" href="#"><i class="fas fa-robot me-2"></i>NBA AI 投資戰情室</a>
                <span class="text-white-50" style="font-size:0.9em">更新時間: {update_time}</span>
            </div>
        </nav>

        <div class="container">
            <div class="row g-3 mb-4">
                <div class="col-md-4"><div class="stat-card" style="border-color: #3498db;">
                    <div class="text-muted text-uppercase small">監控賽事</div>
                    <div class="fs-2 fw-bold text-dark">{total_games} <span class="fs-6 text-muted">場</span></div>
                </div></div>
                <div class="col-md-4"><div class="stat-card" style="border-color: #2ecc71;">
                    <div class="text-muted text-uppercase small">推薦下注</div>
                    <div class="fs-2 fw-bold text-success">{bet_count} <span class="fs-6 text-muted">單</span></div>
                </div></div>
                <div class="col-md-4"><div class="stat-card" style="border-color: #f1c40f;">
                    <div class="text-muted text-uppercase small">最高期望值</div>
                    <div class="fs-2 fw-bold text-warning">+{max_ev:.2f}</div>
                </div></div>
            </div>

            <div class="table-container">
                <div class="d-flex justify-content-between align-items-center mb-4">
                    <h5 class="fw-bold m-0"><i class="fas fa-list-ul me-2"></i>明日賽事策略清單</h5>
                    <span class="badge bg-secondary">{target_file}</span>
                </div>
                <div class="table-responsive">
                    {table_html}
                </div>
            </div>
            
            <footer class="text-center mt-5 text-muted small">
                Generated by Master Controller v3
            </footer>
        </div>

        <script src="https://code.jquery.com/jquery-3.6.0.min.js"></script>
        <script src="https://cdn.datatables.net/1.13.4/js/jquery.dataTables.min.js"></script>
        <script src="https://cdn.datatables.net/1.13.4/js/dataTables.bootstrap5.min.js"></script>
        <script>
            $(document).ready(function() {{
                $('#predictionTable').DataTable({{
                    "paging": false,
                    "info": false,
                    "searching": false,
                    "order": [[ 5, "desc" ]], // 預設依期望值 (第6欄, index 5) 排序
                    "language": {{ "url": "//cdn.datatables.net/plug-ins/1.13.4/i18n/zh-Hant.json" }},
                    "createdRow": function( row, data, dataIndex ) {{
                        // 注意：DataTables 的欄位索引是從 0 開始
                        // 假設欄位順序: 球隊(0), 主客(1), 對手(2), 勝率(3), 賠率(4), 期望值(5), 策略訊號(6)
                        
                        var signal = data[6]; 
                        var cell = $('td', row).eq(6);
                        
                        if (signal.includes('ROI King')) cell.html('<span class="badge-roi"><i class="fas fa-crown me-1"></i>ROI King</span>');
                        else if (signal.includes('Value')) cell.html('<span class="badge-val"><i class="fas fa-check me-1"></i>Value</span>');
                        else if (signal.includes('High EV')) cell.html('<span class="badge-high"><i class="fas fa-fire me-1"></i>High EV</span>');
                        else if (signal.includes('Anchor')) cell.html('<span class="badge-anchor"><i class="fas fa-anchor me-1"></i>Anchor</span>');
                        
                        // 勝率加強顯示 (Win%)
                        var winRateStr = data[3];
                        var winRate = parseInt(winRateStr.replace('%',''));
                        if (winRate >= 60) $('td', row).eq(3).addClass('text-win');
                    }}
                }});
            }});
        </script>
        </body>
        </html>
        """

        with open('index.html', 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        print(" [V] index.html 生成成功！請直接打開網頁查看戰報。")

    except Exception as e:
        print(f" [X] 生成網頁時發生錯誤: {e}")

if __name__ == "__main__":
    main()  