import subprocess
import sys
import time
import os

def run_step(script_name):
    """
    執行外部 Python 腳本的函式
    """
    print(f"\n" + "="*60)
    print(f" ▶ 正在執行: {script_name}")
    print("="*60)
    
    if not os.path.exists(script_name):
        # 容錯：fix_columns.py 有時可有可無
        if script_name == "fix_columns.py":
            print(f" [!] 提示：找不到 '{script_name}'，假設檔案已不需要修正，跳過。")
            return True
        print(f" [X] 錯誤：找不到檔案 '{script_name}'")
        return False

    start_time = time.time()
    try:
        result = subprocess.run([sys.executable, script_name], check=True)
        elapsed = time.time() - start_time
        print(f"\n [V] {script_name} 執行成功！ (耗時: {elapsed:.1f} 秒)")
        return True
    except subprocess.CalledProcessError as e:
        print(f"\n [X] {script_name} 執行失敗！ (錯誤碼: {e.returncode})")
        return False
    except Exception as e:
        print(f"\n [X] 發生未預期錯誤: {e}")
        return False

def main():
    print("\n" + "#"*60)
    print(" 🏀 NBA 全自動投資系統 (Master Controller v3 - 模組化版)")
    print(" 🎯 任務：更新數據 -> 預測明日 -> 抓取賠率 -> 產出策略 -> 生成網頁")
    print("#"*60)
    
    # ==========================================
    # 定義執行清單 (Daily Pipeline)
    # ==========================================
    pipeline = [
        # --- 階段 1: 數據更新 ---
        "v300_get_links.py",               # 1. 找連結
        "v300_parse_data_incremental.py",  # 2. 抓數據
        "v400_get_current_injuries.py",    # 3. 抓傷病
        
        # --- 階段 2: 特徵工程 ---
        "v200_gmsc_cumulative.py",         # 4. 累積數據
        "v1_update_v53.py",                # 5. 進階數據
        "v200data_process9.py",            # 6. 最終特徵
        "v200_merge_final.py",             # 7. 合併資料
        "fix_columns.py",                  # 8. 修正欄位 (如果有的話)
        
        # --- 階段 3: 預測與決策 (核心) ---
        "v500_export_predictions.py",      # 9. 預測明日
        "v900_daily_strategy_output.py",   # 10. 實戰出單 (產出 Betting_Plan)
        
        # --- 階段 4: 報表呈現 (獨立模組) ---
        "generate_dashboard.py"            # 11. 生成網頁戰報
    ]

    # ==========================================
    # 執行流程
    # ==========================================
    for i, script in enumerate(pipeline):
        print(f"\n [進度] 步驟 {i+1}/{len(pipeline)}...")
        success = run_step(script)
        if not success and script != "fix_columns.py": 
            print(f"\n [!] 系統在執行 '{script}' 時發生錯誤，流程停止。")
            break
    else:
        # 全部成功後
        print("\n" + "#"*60)
        print(" 🎉 所有分析步驟完成！")
        print(" 📂 請直接打開 'index.html' 查看今日戰報")
        print("#"*60)

if __name__ == "__main__":
    main()