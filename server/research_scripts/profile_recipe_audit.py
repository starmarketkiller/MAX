#!/usr/bin/env python3
"""
11/08 (4) - richiesta esplicita dell'utente: "magari avevamo gia' costruito
un profilo migliore senza accorgercene, come per CRT dove un errore ha
rivelato qualcosa di buono". I profili MQL5 esistenti (NXS_StrategyProfiles.mqh)
hanno SL/TP/HTF/breakeven storici (dal ciclo di ricerca "sito" di luglio,
quasi tutti con HTF filter ACCESO) - MAI testati con il motore corretto
di oggi (post-fix bars/W1/Asian-range) sul nuovo storico ampliato. Ogni
test di questa sessione ha sempre usato la baseline piatta (SL1.5x/TP3.0x,
niente HTF, niente BE).

Per ogni strategia con un profilo: confronto diretto flat-baseline vs
"ricetta ufficiale" (SL/TP/HTF/BE del profilo, sul TF del profilo),
IS(60%)/OOS(40%), stesso storico ampliato (2019-2026) per entrambe le
gambe - cosi' la differenza e' SOLO nei parametri, non nei dati.
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import backtest as bt

SYMBOL, BARS = "XAUUSD", 110000

# (strategia, TF profilo, slMult, tpMult, htf, beR)
PROFILES = [
    ("MACD", "4h", 2.0, 8.0, True, 1.0),
    ("TURTLE_SOUP", "1h", 1.0, 4.5, True, 0.0),
    ("BREAKOUT_ACC", "1d", 1.0, 4.5, True, 0.0),
    ("THREE_BAR_DELIVERY_BREAK", "4h", 1.5, 3.0, True, 0.0),
    ("EMA_PULLBACK", "1h", 1.5, 4.0, True, 0.0),
    ("FVG_CONT", "4h", 1.0, 4.5, True, 0.0),
    ("FVG_MIT", "4h", 1.5, 4.5, True, 0.0),
    ("LIQ_SWEEP", "1d", 1.5, 3.0, True, 0.0),
    ("LONDON_BO", "4h", 1.0, 4.5, True, 0.0),
    ("SAR", "4h", 1.5, 4.0, True, 0.0),
    ("TSI", "1d", 1.5, 4.5, True, 1.0),
    ("ADX_RSI", "1d", 1.0, 10.0, True, 1.5),
    ("RSI_DIV", "1h", 1.0, 4.5, False, 0.0),
    ("BOLLINGER", "1d", 1.0, 2.0, False, 0.0),
    ("BJORGUM", "4h", 1.5, 3.0, False, 0.0),
    ("ICHIMOKU", "4h", 1.0, 4.5, True, 0.0),
    ("STRUCT_REACT", "1h", 1.0, 4.5, True, 0.0),
    ("OB_MIT", "1d", 1.5, 4.0, False, 0.0),
    ("ORDER_BLOCK", "1d", 1.0, 3.0, True, 0.0),
    ("OTE_CONT", "1d", 2.0, 4.5, True, 0.0),
    ("SH_BMS_RTO", "1d", 1.0, 4.5, False, 0.0),
    ("WEEKLY_EXP", "1d", 1.0, 4.5, True, 0.0),
    ("IFVG", "4h", 1.5, 4.5, True, 0.0),
    ("MALAYSIAN_SNR", "1d", 2.0, 4.5, True, 0.0),
    ("BB_SQUEEZE", "1d", 1.0, 4.5, False, 0.0),
    ("SMS_BMS_RTO", "1d", 1.0, 4.5, False, 0.0),
]


def run(strat, tf, br, **kw):
    r = bt.run_backtest(symbol=SYMBOL, timeframe=tf, strategy=strat, strategies=[strat],
                         risk_pct=1.0, bars=BARS, bar_range=br, **kw)
    return {"trades": r.get("trades", 0), "pf": r.get("profit_factor")}


def main():
    for strat, tf, sl, tp, htf, be in PROFILES:
        flat_is = run(strat, tf, (0.0, 0.6), atr_sl=1.5, atr_tp=3.0)
        flat_oos = run(strat, tf, (0.6, 1.0), atr_sl=1.5, atr_tp=3.0)
        rec_is = run(strat, tf, (0.0, 0.6), atr_sl=sl, atr_tp=tp, htf_filter=htf, breakeven_r=be)
        rec_oos = run(strat, tf, (0.6, 1.0), atr_sl=sl, atr_tp=tp, htf_filter=htf, breakeven_r=be)
        better = (rec_oos["pf"] is not None and flat_oos["pf"] is not None
                  and rec_oos["pf"] > flat_oos["pf"] and rec_oos["trades"] >= 15)
        flag = "  <-- RICETTA MIGLIORE" if better else ""
        print(f"{strat:<26}{tf:<5} flat: IS={flat_is['pf']}/{flat_is['trades']:<5} OOS={flat_oos['pf']}/{flat_oos['trades']:<5}   "
              f"ricetta(sl{sl}/tp{tp}/htf{int(htf)}/be{be}): IS={rec_is['pf']}/{rec_is['trades']:<5} OOS={rec_oos['pf']}/{rec_oos['trades']}{flag}",
              flush=True)


if __name__ == "__main__":
    main()
