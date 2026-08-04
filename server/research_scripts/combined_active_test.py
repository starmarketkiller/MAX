#!/usr/bin/env python3
"""
Passo 2 richiesto dall'utente ("poi provare con tutte le strategie
attive"): esegue tutte le strategie con profilo trovato da
find_best_profiles.py INSIEME, ognuna col proprio SL/TP/breakeven/trailing
(strategy_profiles, aggiunto a run_backtest il 04/08 apposta per questo -
prima il motore applicava un unico sl/tp/gestione globale a chiunque
scattasse).

Limite del motore (non aggirabile senza riscriverlo): un run lavora su UNA
sola serie di candele -> strategie con TF diversi non possono girare
"insieme" nello stesso run. Raggruppate per TF; dentro ogni gruppo, al bar i
la PRIMA strategia della lista che genera segnale apre la posizione (motore
single-position, priorita' d'ordine - non multi-ticket concorrente come fa
l'EA reale in MT5, dove strategie diverse possono avere posizioni aperte in
parallelo). I numeri qui sono quindi un limite inferiore di attivita' vera,
non un equivalente esatto del comportamento live.

BB_SQUEEZE e DISP_REBAL esclusi (5 e 9 trade nel batch di ottimizzazione -
campione troppo piccolo per fidarsi del profilo trovato).

Esegui dalla root del repo: python3 server/research_scripts/combined_active_test.py
"""
import sys
from collections import Counter
sys.path.insert(0, "server")
import backtest as bt

COSTS = bt.COST_PRESETS["retail_standard"]

BEST = {
    "IFVG": {"tf": "4h", "atr_sl": 1.5, "atr_tp": 4.0, "breakeven_r": 0.0, "trailing_atr": 0.0},
    "THREE_BAR_DELIVERY_BREAK": {"tf": "4h", "atr_sl": 1.5, "atr_tp": 3.0, "breakeven_r": 0.0, "trailing_atr": 0.0},
    "OB_MIT": {"tf": "1d", "atr_sl": 2.0, "atr_tp": 4.0, "breakeven_r": 0.0, "trailing_atr": 2.5},
    "OTE_CONT": {"tf": "1d", "atr_sl": 1.0, "atr_tp": 4.0, "breakeven_r": 1.0, "trailing_atr": 2.5},
    "SH_BMS_RTO": {"tf": "1d", "atr_sl": 2.0, "atr_tp": 4.0, "breakeven_r": 0.0, "trailing_atr": 2.5},
    "SMS_BMS_RTO": {"tf": "1d", "atr_sl": 2.0, "atr_tp": 4.0, "breakeven_r": 0.0, "trailing_atr": 2.5},
    "SAR": {"tf": "4h", "atr_sl": 2.0, "atr_tp": 3.0, "breakeven_r": 0.0, "trailing_atr": 0.0},
    "BREAKOUT_ACC": {"tf": "1d", "atr_sl": 2.0, "atr_tp": 4.0, "breakeven_r": 1.5, "trailing_atr": 2.5},
    "ICHIMOKU": {"tf": "4h", "atr_sl": 1.0, "atr_tp": 4.0, "breakeven_r": 0.0, "trailing_atr": 2.5},
    "MACD": {"tf": "4h", "atr_sl": 1.0, "atr_tp": 4.0, "breakeven_r": 0.0, "trailing_atr": 0.0},
    "LONDON_BO": {"tf": "1d", "atr_sl": 1.0, "atr_tp": 4.0, "breakeven_r": 0.0, "trailing_atr": 0.0},
    "WEEKLY_EXP": {"tf": "1d", "atr_sl": 1.0, "atr_tp": 4.0, "breakeven_r": 0.0, "trailing_atr": 0.0},
    "EMA_PULLBACK": {"tf": "4h", "atr_sl": 1.0, "atr_tp": 4.0, "breakeven_r": 0.0, "trailing_atr": 2.5},
    "ADX_RSI": {"tf": "1d", "atr_sl": 2.0, "atr_tp": 4.0, "breakeven_r": 0.0, "trailing_atr": 2.5},
    "RSI_DIV": {"tf": "1h", "atr_sl": 2.0, "atr_tp": 4.0, "breakeven_r": 0.0, "trailing_atr": 0.0},
    "TURTLE_SOUP": {"tf": "1h", "atr_sl": 1.0, "atr_tp": 3.0, "breakeven_r": 0.0, "trailing_atr": 0.0},
    "FVG_CONT": {"tf": "4h", "atr_sl": 1.0, "atr_tp": 4.0, "breakeven_r": 0.0, "trailing_atr": 0.0},
    "TSI": {"tf": "1d", "atr_sl": 1.5, "atr_tp": 4.0, "breakeven_r": 0.0, "trailing_atr": 0.0},
    "LIQ_VOID": {"tf": "4h", "atr_sl": 1.5, "atr_tp": 3.0, "breakeven_r": 0.0, "trailing_atr": 0.0},
    "FVG_MIT": {"tf": "1d", "atr_sl": 1.5, "atr_tp": 4.0, "breakeven_r": 1.5, "trailing_atr": 2.5},
    "BJORGUM": {"tf": "4h", "atr_sl": 2.0, "atr_tp": 3.0, "breakeven_r": 0.0, "trailing_atr": 0.0},
    "ORDER_BLOCK": {"tf": "1d", "atr_sl": 1.0, "atr_tp": 2.0, "breakeven_r": 0.0, "trailing_atr": 0.0},
    "BOLLINGER": {"tf": "1d", "atr_sl": 1.5, "atr_tp": 3.0, "breakeven_r": 1.0, "trailing_atr": 1.5},
    "RANGE_FADE": {"tf": "1d", "atr_sl": 1.5, "atr_tp": 3.0, "breakeven_r": 1.0, "trailing_atr": 1.5},
    "LIQ_SWEEP": {"tf": "1d", "atr_sl": 1.5, "atr_tp": 3.0, "breakeven_r": 0.0, "trailing_atr": 0.0},
    "STRUCT_REACT": {"tf": "1h", "atr_sl": 1.0, "atr_tp": 4.0, "breakeven_r": 0.0, "trailing_atr": 0.0},
    "MALAYSIAN_SNR": {"tf": "1d", "atr_sl": 1.0, "atr_tp": 4.0, "breakeven_r": 0.0, "trailing_atr": 0.0},
}


def main():
    groups = {}
    for s, p in BEST.items():
        groups.setdefault(p["tf"], []).append(s)

    print("=" * 100)
    for tf, strats in groups.items():
        profiles = {s: {k: v for k, v in BEST[s].items() if k != "tf"} for s in strats}
        r = bt.run_backtest(symbol="XAUUSD", timeframe=tf, strategies=strats,
                             strategy_profiles=profiles, **COSTS)
        print(f"\n--- Gruppo TF={tf} ({len(strats)} strategie: {', '.join(sorted(strats))}) ---")
        print(f"Trade: {r['trades']}  WinRate: {r['win_rate']}%  PF: {r['profit_factor']}  "
              f"ExpR: {r['expectancy_r']}  MaxDD: {r['max_dd_pct']}%  NetPnL: {r['net_pnl']}")
        cnt = Counter(t["strategy"] for t in r["trade_list"])
        print(f"  (mix strategie negli ultimi {len(r['trade_list'])} trade salvati: {dict(cnt)})")
    print("=" * 100)


if __name__ == "__main__":
    main()
