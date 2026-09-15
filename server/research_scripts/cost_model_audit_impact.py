#!/usr/bin/env python3
"""
NEXUS Broker Cost Model Audit - Impact Test.

Ricalcola 3 strategie storiche rappresentative (positiva/borderline/negativa,
scelte da un run REALE di nucleus_cost_reverify_14-08.py, nessun segnale/
parametro modificato) sotto 4 cost model: OLD_COST_MODEL (retail_standard,
il preset gia' usato per il gate storico), BROKER_BASELINE (costi osservati
sul broker reale via campione live), CONSERVATIVE (~1.5x baseline), STRESS
(~2x baseline).

Nessuna modifica a strategie/segnali/parametri - SOLO il cost model cambia.
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import backtest as bt

SYMBOL, BARS = "XAUUSD", 110000
BAR_RANGE = (0.6, 1.0)  # OOS, stesso range di nucleus_cost_reverify_14-08.py

# 3 strategie rappresentative, scelte da un run REALE (non modificato) di
# nucleus_cost_reverify_14-08.py: positiva (robusta a tutti i livelli di
# costo), borderline (PF_none>1 ma PF_retail<1 - il cost model decide
# l'esito), negativa (gia' PF_none<1, i costi non cambiano la conclusione).
STRATEGIES = [
    ("BREAKOUT_ACC", "1d", "positiva"),
    ("EMA_PULLBACK", "1h", "borderline"),
    ("THREE_BAR_DELIVERY_BREAK", "4h", "negativa"),
]

# --- Cost profiles ---
# OLD_COST_MODEL: il preset "retail_standard" gia' esistente in COST_PRESETS,
# quello effettivamente usato per il gate SURVIVAL in nucleus_cost_reverify_14-08.py.
OLD_COST_MODEL = dict(bt.COST_PRESETS["retail_standard"])

# BROKER_BASELINE: costi osservati sul broker reale collegato (vedi report
# NEXUS - Broker Cost Model Audit.md §4 per campione live e deal history).
# spread_price: mediana di 900 campioni live reali (15 min, 2026.09.15
# 19:33-19:48), GOLD, $0.54 = 5.4 pip (convenzione NEXUS 1 pip=0.10).
# commission_r: CONFERMATA 0.0 da 79 deal reali della cronologia del conto
# (tutti con commission=0.0000) - non stimata, misurata.
# slippage_price: NON misurabile dalla sola deal history (il prezzo richiesto
# all'invio ordine non e' loggato, solo il prezzo di fill) - stima esplicita,
# NON una misura, per non lasciare il campo a 0 quando l'esecuzione reale
# quasi certamente ne ha un po' (dichiarato onestamente nel report, non
# nascosto come se fosse dato reale).
BROKER_BASELINE = {
    "spread_price": 0.54,
    "commission_r": 0.0,
    "slippage_price": 0.10,
}
CONSERVATIVE = {k: (v * 1.5 if k != "commission_r" else v) for k, v in BROKER_BASELINE.items()}
STRESS = {k: (v * 2.0 if k != "commission_r" else v) for k, v in BROKER_BASELINE.items()}

PROFILES = {
    "OLD_COST_MODEL": OLD_COST_MODEL,
    "BROKER_BASELINE": BROKER_BASELINE,
    "CONSERVATIVE": CONSERVATIVE,
    "STRESS": STRESS,
}


def run_one(strat, tf, cost):
    r = bt.run_backtest(symbol=SYMBOL, timeframe=tf, strategy=strat, strategies=[strat],
                         risk_pct=1.0, atr_sl=1.5, atr_tp=3.0, bars=BARS, bar_range=BAR_RANGE,
                         spread_price=cost["spread_price"], commission_r=cost["commission_r"],
                         slippage_price=cost["slippage_price"])
    return {
        "n": r.get("trades"), "pf": r.get("profit_factor"), "gross_pf": r.get("gross_profit_factor"),
        "net": r.get("net_pnl"), "gross": r.get("gross_pnl"), "total_cost": r.get("total_cost"),
        "avg_cost": r.get("avg_cost_per_trade"), "expectancy_r": r.get("expectancy_r"),
        "dd": r.get("max_dd_pct"),
    }


def main():
    import json
    print(f"{'strategy':<26}{'label':<12}{'cost_profile':<18}{'n':<5}{'PF':<7}{'PFgross':<9}"
          f"{'net':<10}{'gross':<10}{'cost_tot':<10}{'cost/trd':<9}{'DD%':<7}")
    results = {}
    for strat, tf, label in STRATEGIES:
        results[strat] = {"tf": tf, "label": label, "profiles": {}}
        n_ref = None
        for name, cost in PROFILES.items():
            r = run_one(strat, tf, cost)
            results[strat]["profiles"][name] = r
            print(f"{strat:<26}{label:<12}{name:<18}{str(r['n']):<5}{str(r['pf']):<7}{str(r['gross_pf']):<9}"
                  f"{str(r['net']):<10}{str(r['gross']):<10}{str(r['total_cost']):<10}{str(r['avg_cost']):<9}{str(r['dd']):<7}")
            if n_ref is None:
                n_ref = r["n"]
            elif r["n"] != n_ref:
                print(f"  *** ATTENZIONE: n trade diverso da OLD_COST_MODEL ({r['n']} vs {n_ref}) - "
                      f"il cost model NON e' puramente contabile per questa strategia! ***")
        gross_edge = results[strat]["profiles"]["OLD_COST_MODEL"]["gross"]
        for name in PROFILES:
            tc = results[strat]["profiles"][name]["total_cost"]
            drag = (tc / gross_edge) if gross_edge else None
            results[strat]["profiles"][name]["cost_drag_pct"] = round(drag * 100, 1) if drag is not None else None
        print()

    out_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "results", "cost_model_audit")
    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, "impact_test_results.json"), "w", encoding="utf-8") as f:
        json.dump({"profiles_definition": PROFILES, "results": results}, f, indent=2, default=str)
    print("\ncost_drag % (total_cost / gross_pnl a OLD_COST_MODEL, stesso denominatore per tutti i profili):")
    for strat in results:
        for name in PROFILES:
            print(f"  {strat:<26}{name:<18}{results[strat]['profiles'][name]['cost_drag_pct']}%")

    return results


if __name__ == "__main__":
    main()
