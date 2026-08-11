#!/usr/bin/env python3
"""
11/08 (13) - richiesta esplicita dell'utente: riprovare "TP sulla
prossima liquidita' reale" (il meccanismo dietro la forza di CRT) sulle
strategie del nucleo dove il concetto si applica. L'infrastruttura
esisteva gia' (STRATEGY_TARGETS_OPTIN/_liq_sweep_target, PDH/PDL/Asia/
swing esterno) - testata una volta sola su LIQ_SWEEP il 16/07 con esito
"misto/non decisivo" (storico vecchio). Qui: riverifica su LIQ_SWEEP +
estensione a FVG_CONT (unico altro candidato pulito nel nucleo - gli
altri hanno gia' un SL/TP strutturale con priorita' assoluta), storico
ampio, TF di profilo reale, IS/OOS + walk-forward a 5 finestre.
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import backtest as bt

SYMBOL, BARS = "XAUUSD", 110000
N_WINDOWS = 5

# (strategia, TF di profilo reale)
CANDIDATES = [
    ("LIQ_SWEEP", "1d"),
    ("FVG_CONT", "4h"),
]


def run(strat, tf, br, dyn=False):
    r = bt.run_backtest(symbol=SYMBOL, timeframe=tf, strategy=strat, strategies=[strat],
                         risk_pct=1.0, bars=BARS, bar_range=br, use_dynamic_tp=dyn)
    return {"trades": r.get("trades", 0), "pf": r.get("profit_factor"), "dd": r.get("max_dd_pct")}


def main():
    for strat, tf in CANDIDATES:
        print(f"\n=== {strat} @ {tf} ===", flush=True)
        flat_is, flat_oos = run(strat, tf, (0.0, 0.6)), run(strat, tf, (0.6, 1.0))
        dyn_is, dyn_oos = run(strat, tf, (0.0, 0.6), True), run(strat, tf, (0.6, 1.0), True)
        print(f"  flat TP:    IS pf={flat_is['pf']} n={flat_is['trades']} dd={flat_is['dd']}%   "
              f"OOS pf={flat_oos['pf']} n={flat_oos['trades']} dd={flat_oos['dd']}%")
        print(f"  liquidity TP: IS pf={dyn_is['pf']} n={dyn_is['trades']} dd={dyn_is['dd']}%   "
              f"OOS pf={dyn_oos['pf']} n={dyn_oos['trades']} dd={dyn_oos['dd']}%", flush=True)
        flat_row, dyn_row = [], []
        wins = 0
        for w in range(N_WINDOWS):
            br = (w / N_WINDOWS, (w + 1) / N_WINDOWS)
            rf, rd = run(strat, tf, br), run(strat, tf, br, True)
            flat_row.append(f"{rf['pf']}/{rf['trades']}")
            dyn_row.append(f"{rd['pf']}/{rd['trades']}")
            if rd["pf"] is not None and rf["pf"] is not None and rd["pf"] > rf["pf"]:
                wins += 1
        print("  flat wf:      " + "  |  ".join(flat_row))
        print("  liquidity wf: " + "  |  ".join(dyn_row))
        print(f"  TP dinamico batte flat in {wins}/{N_WINDOWS} finestre", flush=True)


if __name__ == "__main__":
    main()
