import pandas as pd
import numpy as np
import os

def generate_signals():
    print("--- 🎯 啟動訊號生成器 (v800.4 Strategy) ---")
    pred_file = "predictions_2026_full_report.csv"
    odds_file = "odds_2026_full_season.csv"
    output_file = "Final_Betting_Signals.csv"

    if not os.path.exists(pred_file) or not os.path.exists(odds_file):
        print("❌ 缺少 predictions_2026_full_report.csv 或 odds_2026_full_season.csv")
        return

    df_pred = pd.read_csv(pred_file)
    df_odds = pd.read_csv(odds_file)

    date_col = 'date' if 'date' in df_pred.columns else 'Date'
    df_pred[date_col] = pd.to_datetime(df_pred[date_col])
    df_odds['Date'] = pd.to_datetime(df_odds['Date'])

    # 雙向合併
    m1 = pd.merge(df_pred, df_odds, left_on=[date_col, 'Team_Abbr', 'Opp_Abbr'], right_on=['Date', 'Home_Abbr', 'Away_Abbr'], how='left')
    m2 = pd.merge(df_pred, df_odds, left_on=[date_col, 'Team_Abbr', 'Opp_Abbr'], right_on=['Date', 'Away_Abbr', 'Home_Abbr'], how='left')

    df = df_pred.copy()
    df['Odds_Team'] = np.nan
    df['Is_Home'] = False

    mask_h = m1['Odds_Home'].notna()
    df.loc[mask_h, 'Odds_Team'] = m1.loc[mask_h, 'Odds_Home']
    df.loc[mask_h, 'Is_Home'] = True

    mask_a = m2['Odds_Away'].notna()
    df.loc[mask_a, 'Odds_Team'] = m2.loc[mask_a, 'Odds_Away']
    df.loc[mask_a, 'Is_Home'] = False
    
    df = df.dropna(subset=['Odds_Team'])
    
    prob_col = 'Win_Prob' if 'Win_Prob' in df.columns else 'Predicted_Win_Prob'
    df['Prob'] = pd.to_numeric(df[prob_col], errors='coerce')
    df['EV'] = (df['Prob'] * df['Odds_Team']) - 1
    
    def get_signal(row):
        prob, ev, is_home = row['Prob'], row['EV'], row['Is_Home']
        signals = []
        
        # 策略邏輯
        if is_home and 0.60 <= prob < 0.70 and ev > 0:
            signals.append(f"💎 BET HOME (ROI King) EV={ev:.2f}")
        elif is_home and 0.50 <= prob < 0.60 and ev > 0:
            signals.append(f"🟡 BET HOME (Value) EV={ev:.2f}")
        
        if not signals and ev > 0.20:
             signals.append(f"🚀 BET {'HOME' if is_home else 'AWAY'} (High EV) EV={ev:.2f}")

        if prob > 0.80 and ev < 0.15: return "PASS (Odds Too Low)"

        return " | ".join(signals) if signals else "PASS"

    df['Signal'] = df.apply(get_signal, axis=1)
    
    cols = [date_col, 'Team_Abbr', 'Opp_Abbr', 'Is_Home', 'Prob', 'Odds_Team', 'EV', 'Signal', 'Win']
    df_final = df[[c for c in cols if c in df.columns]].sort_values(by=[date_col, 'Team_Abbr'], ascending=[False, True])
    
    df_final.to_csv(output_file, index=False, encoding='utf-8-sig')
    print(f"✅ 生成訊號表: {output_file} (共 {len(df_final)} 筆)")

if __name__ == "__main__":
    generate_signals()