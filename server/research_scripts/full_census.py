#!/usr/bin/env python3
"""
11/08 (8) - richiesta esplicita dell'utente: sintesi completa di TUTTE le
50 strategie del motore (16 nucleo + 34 escluse), stesso metodo per
tutte (flat baseline SL1.5x/TP3.0x, no HTF/BE), stesso storico ampliato
(2019-2026), IS(60%)/OOS(40%) - un solo censimento coerente invece di
numeri raccolti da script diversi in momenti diversi con parametri
diversi.

TF per strategia: NXS_Profile_TF() (MQL5) dove esiste, altrimenti il
miglior TF gia' trovato in sessioni precedenti (phase4_natural_tf_check,
test diretti su MALAYSIAN_SNR_V2_*), altrimenti un default ragionevole
per famiglia (scalp->15m, sessione/kill-zone->1h).
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import backtest as bt

SYMBOL, BARS = "XAUUSD", 110000

NUCLEUS = {
    "BREAKOUT_ACC": "1d", "TURTLE_SOUP": "1h", "MACD": "4h", "LONDON_BO": "4h",
    "FVG_MIT": "4h", "LIQ_SWEEP": "1d", "AMD_CONT": "30m", "FVG_CONT": "4h",
    "TSI": "1d", "ADX_RSI": "1d", "SAR": "4h", "EMA_PULLBACK": "1h",
    "THREE_BAR_DELIVERY_BREAK": "4h", "LDN_REVERSAL": "15m", "AMD_REVERSAL": "15m",
    "CRT": "30m",
}

EXCLUDED = {
    "BB_SQUEEZE": "1d", "BJORGUM": "4h", "BOLLINGER": "1d", "DISP_REBAL": "4h",
    "ICHIMOKU": "4h", "IFVG": "4h", "LIQ_VOID": "4h", "MALAYSIAN_SNR": "1d",
    "OB_MIT": "30m", "ORDER_BLOCK": "30m", "OTE_CONT": "15m", "RANGE_FADE": "1d",
    "RSI_DIV": "1h", "SH_BMS_RTO": "1h", "SMS_BMS_RTO": "1d", "STRUCT_REACT": "1h",
    "WEEKLY_EXP": "1h",
    # senza profilo MQL5 - TF scelto per famiglia/analogia (vedi nota di modulo)
    "FVG_CONT_V2": "4h", "ORDER_BLOCK_V2": "30m", "OTE_CONT_V2": "15m",
    "SH_BMS_RTO_V2": "1h", "SILVER_BULLET_V2": "1h", "SILVER_BULLET": "1h",
    "MALAYSIAN_SNR_BREAKOUT": "4h", "MALAYSIAN_SNR_V2_RETEST": "1h",
    "MALAYSIAN_SNR_V2_STAGE1": "1h", "MALAYSIAN_SNR_V2_STAGE3": "1h",
    "JUDAS_SWING": "1h", "NY_REVERSAL": "1h", "PO3": "1h",
    "SCALP_BB_FADE": "15m", "SCALP_EMA": "15m", "SCALP_RANGE_BRK": "15m",
    "SCALP_RSI_SNAP": "15m",
}


def run(strat, tf, br):
    try:
        r = bt.run_backtest(symbol=SYMBOL, timeframe=tf, strategy=strat, strategies=[strat],
                             risk_pct=1.0, bars=BARS, bar_range=br, atr_sl=1.5, atr_tp=3.0)
        return {"trades": r.get("trades", 0), "pf": r.get("profit_factor"),
                "dd": r.get("max_dd_pct")}
    except Exception as e:
        return {"trades": 0, "pf": None, "dd": None, "err": str(e)[:60]}


def main():
    for label, group in [("NUCLEO (16)", NUCLEUS), ("ESCLUSE (34)", EXCLUDED)]:
        print(f"\n=== {label} ===", flush=True)
        for strat, tf in sorted(group.items()):
            is_r = run(strat, tf, (0.0, 0.6))
            oos_r = run(strat, tf, (0.6, 1.0))
            err = is_r.get("err") or oos_r.get("err") or ""
            print(f"{strat:<28}{tf:<5} IS pf={str(is_r['pf']):<6}n={is_r['trades']:<6}dd={is_r['dd']}  "
                  f"OOS pf={str(oos_r['pf']):<6}n={oos_r['trades']:<6}dd={oos_r['dd']}  {err}", flush=True)


if __name__ == "__main__":
    main()
