#!/usr/bin/env python3
"""
10/08 - Fase 3b: dopo che il grid-search multi-parametro (SL/TP/HTF/BE/trail)
ha PEGGIORATO l'OOS di MACD/TURTLE_SOUP/BREAKOUT_ACC rispetto al semplice
default (fase3_param_refine.py) - overfit su troppi assi insieme su ~1 anno
di dati - qui si provano due assi a BASSA dimensionalita', molto meno
inclini a overfittare perche' ciascuno ha solo 2-3 varianti da confrontare
(contro le 5x4x2x2x2=160 combinazioni del grid completo):

1. direction_lock ("BUY"/"SHORT"/nessuno): se la strategia ha un'asimmetria
   buy/sell forte, isolare il lato buono puo' reggere l'OOS meglio di un
   tuning SL/TP - stesso approccio gia' pagante su OTE_CONT questa sessione.
2. timeframe alternativo, a parita' di parametri default (1.5/3.0, nessun
   gate) - mai verificato con uno split IS/OOS vero, solo a periodo intero
   nel full_strategy_tf_scan.py di ieri.

Sempre selezione su in-sample (60%), verifica su out-of-sample (40%) mai
visto durante la scelta.
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import backtest as bt
import bt_verdict

SYMBOL = "XAUUSD"
STRATS = ["MACD", "TURTLE_SOUP", "BREAKOUT_ACC"]
TFS = ["15m", "30m", "1h", "4h", "1d"]
MIN_TRADES = 8


def _eval(strat, tf, bar_range, direction_lock=None):
    try:
        r = bt.run_backtest(
            symbol=SYMBOL, timeframe=tf, strategy=strat, strategies=[strat],
            risk_pct=1.0, atr_sl=1.5, atr_tp=3.0, start_equity=10000.0,
            bar_range=bar_range, direction_lock=direction_lock)
    except Exception:
        return None
    n = r.get("trades", 0)
    pf = r.get("profit_factor") or 0.0
    exp = r.get("expectancy_r", 0.0)
    v, why = bt_verdict._verdict(
        {"executed": n, "profit_factor": pf, "expectancy_R": exp,
         "winrate_pct": r.get("win_rate", 0), "setup": n}, MIN_TRADES)
    return {"tf": tf, "direction_lock": direction_lock, "trades": n,
            "pf": round(pf, 2), "exp": round(exp, 3), "wr": r.get("win_rate", 0),
            "dd": round(r.get("max_dd_pct", 0.0), 2), "verdict": v}


def direction_lock_test(strat):
    """Sceglie BUY/SHORT/nessuno guardando solo l'IS, poi riporta l'OOS di
    quella scelta - stesso schema disciplinato del resto della sessione.

    NOTA: "nessun lock" (direction_lock=None) e' una variante candidata
    valida quanto le altre, non l'assenza di risultato - usa un sentinel
    di stringa per non confonderla col "nessuna variante trovata" di max().
    """
    variants = {"nessun lock": None, "BUY": "BUY", "SHORT": "SHORT"}
    is_results = {label: _eval(strat, "4h", (0.0, 0.6), v) for label, v in variants.items()}
    candidates = [label for label, r in is_results.items() if r and r["trades"] >= MIN_TRADES]
    if not candidates:
        return {"strategy": strat, "chosen": None, "reason": "nessuna variante con >=8 trade IS"}
    best_label = max(candidates, key=lambda label: is_results[label]["pf"])
    oos = _eval(strat, "4h", (0.6, 1.0), variants[best_label])
    baseline_oos = _eval(strat, "4h", (0.6, 1.0), None)
    return {"strategy": strat, "chosen": best_label,
            "is": is_results[best_label], "oos": oos, "baseline_oos_no_lock": baseline_oos}


def timeframe_test(strat):
    """Sceglie il TF migliore guardando solo l'IS, poi riporta l'OOS di
    quella scelta, sempre a parametri default (nessun tuning aggiuntivo)."""
    is_results = {tf: _eval(strat, tf, (0.0, 0.6)) for tf in TFS}
    best_tf = max(
        (tf for tf in TFS if is_results[tf] and is_results[tf]["trades"] >= MIN_TRADES),
        key=lambda tf: is_results[tf]["pf"], default=None)
    if best_tf is None:
        return {"strategy": strat, "chosen": None, "reason": "nessun TF con >=8 trade IS"}
    oos = _eval(strat, best_tf, (0.6, 1.0))
    return {"strategy": strat, "chosen": best_tf, "is": is_results[best_tf], "oos": oos,
            "all_is": is_results}


def main():
    dlock_results = [direction_lock_test(s) for s in STRATS]
    tf_results = [timeframe_test(s) for s in STRATS]

    print("=== Direction lock (TF fisso 4h, parametri default) ===")
    print(f"{'Strategia':<14}{'Scelto':>10}{'IS PF':>7}{'IS n':>6}   "
          f"{'OOS PF':>7}{'OOS n':>6}{'OOS V':>8}   {'Baseline OOS PF (no lock)':>26}")
    for r in dlock_results:
        if r.get("chosen") is None:
            print(f"{r['strategy']:<14}{'--':>10}  {r.get('reason','')}")
            continue
        i, o, b = r["is"], r["oos"], r["baseline_oos_no_lock"]
        print(f"{r['strategy']:<14}{r['chosen']:>10}{i['pf']:>7}{i['trades']:>6}   "
              f"{(o['pf'] if o else '-'):>7}{(o['trades'] if o else '-'):>6}{(o['verdict'] if o else '-'):>8}"
              f"   {(b['pf'] if b else '-'):>26}")

    print("\n=== Timeframe alternativo (parametri default, nessun altro tuning) ===")
    print(f"{'Strategia':<14}{'TF scelto':>10}{'IS PF':>7}{'IS n':>6}   "
          f"{'OOS PF':>7}{'OOS n':>6}{'OOS V':>8}")
    for r in tf_results:
        if r.get("chosen") is None:
            print(f"{r['strategy']:<14}{'--':>10}  {r.get('reason','')}")
            continue
        i, o = r["is"], r["oos"]
        print(f"{r['strategy']:<14}{r['chosen']:>10}{i['pf']:>7}{i['trades']:>6}   "
              f"{(o['pf'] if o else '-'):>7}{(o['trades'] if o else '-'):>6}{(o['verdict'] if o else '-'):>8}")

    import json
    out_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "phase3b_lowdim_results.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump({"direction_lock": dlock_results, "timeframe": tf_results}, f, indent=2)
    print(f"\nSalvato: {out_path}")


if __name__ == "__main__":
    main()
