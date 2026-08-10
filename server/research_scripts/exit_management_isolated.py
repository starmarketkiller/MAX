#!/usr/bin/env python3
"""
10/08 (10) - richiesta esplicita dell'utente dopo la spiegazione delle leve
di exit-management disponibili nel motore ("Si esatto proviamo ora"):
test ISOLATO di breakeven_r / trailing_atr / use_dynamic_tp, UNA leva alla
volta, SENZA rimescolare SL/TP come faceva la griglia della Fase 3
(optimize(sweep_management=True) spazzola sl/tp/be/trail INSIEME - 81
combinazioni confuse, non isola l'effetto della sola gestione d'uscita).

Qui invece: SL/TP fissi al valore di riferimento della sessione
(ATR_SL=1.5, ATR_TP=3.0, quello usato per tutti i confronti singoli/
regime/ensemble di oggi), e si varia SOLO la leva in esame. Selezione
del valore migliore SOLO su in-sample (60%), verifica su out-of-sample
(40%) mai visto durante la scelta - stessa disciplina di
regime_filter_singles.py.

Tre leve, tre domande separate:
1. breakeven_r: sposta lo SL a pareggio dopo N x rischio a favore -
   "i trade brutti diventano almeno in pari?"
2. trailing_atr: insegue lo stop a N x ATR dal prezzo - "si estrae di
   piu' dai trade buoni lasciandoli correre?"
3. use_dynamic_tp: il target non e' un multiplo fisso ma il prossimo
   livello strutturale (swing/OB a seconda della strategia) - stessa
   domanda della leva 2 ma con un meccanismo diverso.

Strategie: le tre "buone confermate" della sessione (MACD, TURTLE_SOUP,
BREAKOUT_ACC), stesso mercato/TF/storico di tutti i confronti precedenti
(XAUUSD 4h, bars=60000).
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import backtest as bt
import bt_verdict

SYMBOL, TF, BARS = "XAUUSD", "4h", 60000
STRATS = sys.argv[1:] if len(sys.argv) > 1 else ["MACD", "TURTLE_SOUP", "BREAKOUT_ACC"]
ATR_SL, ATR_TP = 1.5, 3.0
RISK_PCT = 1.0
MIN_IS_TRADES = 15

BE_GRID = [0.0, 0.5, 1.0, 1.5]
TRAIL_GRID = [0.0, 1.0, 1.5, 2.0, 2.5]
DYNTP_GRID = [False, "nearest", "far"]


def run(strat, br, **kw):
    r = bt.run_backtest(symbol=SYMBOL, timeframe=TF, strategy=strat, strategies=[strat],
                         risk_pct=RISK_PCT, atr_sl=ATR_SL, atr_tp=ATR_TP,
                         bar_range=br, bars=BARS, **kw)
    n = r.get("trades", 0)
    pf = r.get("profit_factor") or 0.0
    exp = r.get("expectancy_r", 0.0)
    return {"trades": n, "pf": round(pf, 2), "exp_r": exp, "net": r.get("net_pnl")}


def score(res):
    if res["trades"] < MIN_IS_TRADES:
        return -999
    return res["exp_r"] * (res["trades"] ** 0.5)


def test_lever(strat, lever_name, grid, kw_fn):
    baseline_is = run(strat, (0.0, 0.6))
    baseline_oos = run(strat, (0.6, 1.0))
    best = None
    for val in grid:
        r_is = run(strat, (0.0, 0.6), **kw_fn(val))
        sc = score(r_is)
        if best is None or sc > best["score"]:
            best = {"val": val, "score": sc, "is": r_is}
    r_oos = run(strat, (0.6, 1.0), **kw_fn(best["val"]))
    helped = (r_oos["pf"] is not None and baseline_oos["pf"] is not None
              and r_oos["pf"] > baseline_oos["pf"])
    print(f"{strat:<14}{lever_name:<14}{str(best['val']):<10}"
          f"{best['is']['pf']:>7}{best['is']['trades']:>6}   "
          f"{r_oos['pf']:>7}{r_oos['trades']:>6}   "
          f"{baseline_oos['pf']:>10}{baseline_oos['trades']:>6}"
          f"{'  <- aiuta' if helped else ''}")
    return {"strategy": strat, "lever": lever_name, "chosen": best["val"],
            "is": best["is"], "oos": r_oos, "baseline_oos": baseline_oos, "helped": helped}


def main():
    print(f"{'Strategia':<14}{'Leva':<14}{'Valore':<10}{'IS PF':>7}{'IS n':>6}   "
          f"{'OOS PF':>7}{'OOS n':>6}   {'Base OOS PF':>10}{'n':>6}")
    results = []
    for strat in STRATS:
        results.append(test_lever(strat, "breakeven_r", BE_GRID, lambda v: {"breakeven_r": v}))
        results.append(test_lever(strat, "trailing_atr", TRAIL_GRID, lambda v: {"trailing_atr": v}))
        results.append(test_lever(strat, "dynamic_tp", DYNTP_GRID,
                                   lambda v: {"use_dynamic_tp": bool(v),
                                              "dynamic_tp_pick": v if v else "nearest"}))
        print()

    import json
    out_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "exit_management_isolated_results.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    print(f"Salvato: {out_path}")


if __name__ == "__main__":
    main()
