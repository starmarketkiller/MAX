#!/usr/bin/env python3
"""
10/08 - Fase 4: diagnosi "perche' non scattano" per le strategie rimaste
magre nella Fase 3c (bias-pipeline, fissata a TF=4h per allinearsi al
master BREAKOUT_ACC).

Cross-check col matrix a 5 TF di ieri (full_strategy_tf_scan.py) mostra che
il pool magro si divide in due gruppi ben distinti:

- GRUPPO A (mismatch di timeframe, non di logica): su 15m/30m/1h hanno
  decine di trade, il problema e' solo che il test di ieri le forzava a
  4h. Testate qui, singolarmente, sul loro TF migliore (dal matrix),
  parametri default, split IS/OOS onesto (mai fatto finora - il matrix
  era a periodo intero).
- GRUPPO B (rare per costruzione, verificato nel codice): pattern
  composite fedeli al MQL5 reale (es. JUDAS_SWING: solo dentro 3h di kill
  zone LONDON/NY + sweep confermato; SMS_BMS_RTO: 4 condizioni ANDed sulla
  stessa barra) - restano magre su OGNI TF, non e' un problema di timeframe
  ne' un bug. Non testate qui: nessun bar_range le rende meno rare, serve
  piu' storico (Dukascopy e' ancora a ~1.25 anni) o si accetta che sono
  strategie a bassa frequenza per design.
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import backtest as bt
import bt_verdict

SYMBOL = "XAUUSD"
MIN_TRADES = 8

# TF scelto per strategia = quello col piu' alto conteggio trade nel
# full_strategy_tf_scan.py di ieri, tra 15m/30m/1h (4h/1d gia' noti magri
# per queste specifiche strategie).
GROUP_A = {
    "LDN_REVERSAL": "1h",
    "WEEKLY_EXP": "1h",
    "OB_MIT": "30m",
    "ORDER_BLOCK": "30m",
    "SILVER_BULLET": "1h",
    "OTE_CONT": "15m",
    "RSI_DIV": "30m",
    "SH_BMS_RTO": "1h",
    "THREE_BAR_DELIVERY_BREAK": "1h",
}


def _eval(strat, tf, bar_range):
    try:
        r = bt.run_backtest(
            symbol=SYMBOL, timeframe=tf, strategy=strat, strategies=[strat],
            risk_pct=1.0, atr_sl=1.5, atr_tp=3.0, start_equity=10000.0,
            bar_range=bar_range)
    except Exception as e:
        return {"error": str(e)}
    n = r.get("trades", 0)
    pf = r.get("profit_factor") or 0.0
    exp = r.get("expectancy_r", 0.0)
    v, why = bt_verdict._verdict(
        {"executed": n, "profit_factor": pf, "expectancy_R": exp,
         "winrate_pct": r.get("win_rate", 0), "setup": n}, MIN_TRADES)
    return {"trades": n, "pf": round(pf, 2), "wr": r.get("win_rate", 0),
            "dd": round(r.get("max_dd_pct", 0.0), 2), "verdict": v}


def main():
    results = []
    for strat, tf in GROUP_A.items():
        is_r = _eval(strat, tf, (0.0, 0.6))
        oos_r = _eval(strat, tf, (0.6, 1.0))
        results.append({"strategy": strat, "tf": tf, "in_sample": is_r, "out_of_sample": oos_r})

    print(f"{'Strategia':<26}{'TF':>5}   {'IS PF':>7}{'IS n':>6}{'IS V':>8}   "
          f"{'OOS PF':>7}{'OOS n':>6}{'OOS V':>8}")
    for r in results:
        i, o = r["in_sample"], r["out_of_sample"]
        print(f"{r['strategy']:<26}{r['tf']:>5}   "
              f"{i.get('pf','-'):>7}{i.get('trades','-'):>6}{i.get('verdict','-'):>8}   "
              f"{o.get('pf','-'):>7}{o.get('trades','-'):>6}{o.get('verdict','-'):>8}")

    import json
    out_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "phase4_natural_tf_results.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    print(f"\nSalvato: {out_path}")


if __name__ == "__main__":
    main()
