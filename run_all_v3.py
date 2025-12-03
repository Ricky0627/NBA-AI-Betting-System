import subprocess
import time
import os
import sys

def run_script(script_name):
    print(f"\n" + "="*60)
    print(f" ▶ 正在執行: {script_name}")
    print("="*60 + "\n")
    
    start_time = time.time()
    try:
        # 使用當前 Python 解譯器執行
        result = subprocess.run([sys.executable, script_name], check=True)
        end_time = time.time()
        print(f"\n [V] {script_name} 執行成功！ (耗時: {end_time - start_time:.1f} 秒)")
        return True
    except subprocess.CalledProcessError as e:
        print(f"\n [X] {script_name} 執行失敗 (錯誤碼: {e.returncode})")
        return False
    except Exception as e:
        print(f"\n [X] {script_name} 發生未預期錯誤: {e}")
        return False

def main():
    print("Starting NBA AI Pipeline (v4.0 - Parlay Optimized)...")
    
    # 定義執行順序
    # 注意: v960 必須在 v900 之後 (需要賠率檔)，在 dashboard 之前
    scripts = [
        "v300_get_links.py",
        "v300_parse_data_incremental.py",
        "v400_get_current_injuries.py", 
        "v200_gmsc_cumulative.py",
        "v1_update_v53.py", 
        "v200data_process9.py",
        "v200_merge_final.py",
        "PlaySport歷史賠率批次爬蟲 (增量更新版).py",
        "predictions_2026_full_report.py",
        # "v300_update_master_dataset.py",  # (可選) 更新數據
        "fix_columns.py",                 # (可選) 修正欄位
        "v500_export_predictions.py",       # 1. 預測
        "v900_daily_strategy_output.py",    # 2. 爬賠率 + 單場策略 + 存賠率檔
        "v970_rolling_parlay_optimizer.py",    # 3. 生成最優串關 (讀取 v900 的賠率)
        "generate_dashboard.py"             # 4. 生成網頁
    ]

    for i, script in enumerate(scripts, 1):
        if not os.path.exists(script):
            print(f" [!] 跳過: 找不到檔案 {script}")
            continue
            
        print(f"\n [進度] 步驟 {i}/{len(scripts)}...")
        success = run_script(script)
        
        if not success:
            # 如果是關鍵步驟失敗，詢問是否繼續
            if script in ["v500_export_predictions.py", "v900_daily_strategy_output.py"]:
                user_input = input("關鍵步驟失敗，是否繼續執行後續步驟？ (y/n): ")
                if user_input.lower() != 'y':
                    print("已終止流程。")
                    break
        
        # 休息一下，避免爬蟲太快被擋
        if "v900" in script: 
            print("休息 2 秒...")
            time.sleep(2)

    print("\n" + "#"*60)
    print(" 🎉 所有分析步驟完成！")
    print(" 📂 請直接打開 'index.html' 查看今日戰報")
    print("#"*60)

if __name__ == "__main__":
    main()