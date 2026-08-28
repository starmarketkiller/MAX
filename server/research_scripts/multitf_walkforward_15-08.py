#!/usr/bin/env python3
"""
15/08 - le 5 strategie "sopravvissute ai costi" (batch 14/08) mostrano lo
stesso pattern: PF cresce dalla finestra 0 (piu' vecchia) alla finestra 4
(piu' recente, il rally storico dell'oro 2023-2026) - il regime_filter
esistente (ADX-based) non lo risolve. L'utente osserva (TradingView) che
molte strategie tipo MACD "prendono il trend e chiudono quasi in pari":
possibile problema di TF/uscita, non solo di entry. Qui: stesso walk-forward
a 5 finestre, ma su 4 TF (15m/30m/1h/4h) per ciascuna delle 5, stessa
ricetta (SL/TP/HTF/BE) delle rispettive strategie, per vedere se il pattern
regime-dipendente e' universale o cambia con TF piu' basso/veloce.
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import backtest as bt

SYMBOL, BARS = "XAUUSD", 110000
TFS = ["15m", "30m", "1h", "4h"]
N_WINDOWS = 5

RECIPES = {
    "SAR":          dict(atr_sl=1.5, atr_tp=4.0, htf_filter=True),
    "LONDON_BO":    dict(atr_sl=1.0, atr_tp=4.5, htf_filter=True),
    "MACD":         dict(atr_sl=2.0, atr_tp=8.0, htf_filter=True, breakeven_r=1.0),
    "EMA_PULLBACK": dict(atr_sl=1.5, atr_tp=4.0, htf_filter=True),
    "FVG_CONT":     dict(atr_sl=1.5, atr_tp=6.0, htf_filter=True, breakeven_r=1.5),
}


def run(strat, tf, br, rc):
    c = bt.COST_PRESETS["retail_standard"]
    try:
        r = bt.run_backtest(symbol=SYMBOL, timeframe=tf, strategy=strat, strategies=[strat],
                             risk_pct=1.0, bars=BARS, bar_range=br,
                             spread_price=c["spread_price"], commission_r=c["commission_r"],
                             slippage_price=c["slippage_price"], **rc)
    except Exception as e:
        return {"error": str(e)[:150]}
    return {"pf": r.get("profit_factor"), "n": r.get("trades"), "dd": r.get("max_dd_pct")}


def main():
    for strat, rc in RECIPES.items():
        print(f"\n=== {strat} ===", flush=True)
        for tf in TFS:
            row = []
            for w in range(N_WINDOWS):
                br = (w / N_WINDOWS, (w + 1) / N_WINDOWS)
                r = run(strat, tf, br, rc)
                if "error" in r:
                    row.append(f"ERR")
                else:
                    row.append(f"{r['pf']}/{r['n']}")
            n_pos = sum(1 for r in row if r != "ERR" and "/" in r and float(r.split("/")[0]) >= 1.0)
            print(f"  {tf:5s} {' | '.join(row)}   [{n_pos}/{N_WINDOWS} finestre PF>=1]", flush=True)


if __name__ == "__main__":
    main()
