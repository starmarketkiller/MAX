#!/usr/bin/env python3
"""
09/08 - scan combinazioni sotto TREND_GATE, dopo il fix Asian-range in
backtest.py. Pool di partenza: le strategie con miglior PF su 4h dallo scan
completo del 09/08 (full_strategy_tf_scan.py) + i 6 candidati "FORTE"
dell'ottimizzatore live + AMD_CONT/AMD_REVERSAL ora che il fix li sblocca.

Non tutte le 2^N combinazioni (impraticabile) - due domande mirate:
  1. Il pool INTERO combinato sotto TREND_GATE batte le singole componenti?
  2. Leave-one-out: rimuovere UNA strategia alla volta dal pool migliora o
     peggiora il PF combinato? (contributo marginale di ciascuna)
Poi le triple/coppie piu' promettenti indicate dal leave-one-out, testate
esplicitamente.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import trend_gate_core as tg

TF = "4h"
POOL = ["BREAKOUT_ACC", "FVG_MIT", "EMA_PULLBACK", "MACD", "LIQ_VOID",
        "AMD_CONT", "FVG_CONT", "ICHIMOKU", "SAR", "LIQ_SWEEP"]

SCORES = {
    "BREAKOUT_ACC": 68.0, "FVG_MIT": 70.0, "EMA_PULLBACK": 64.0, "MACD": 65.0,
    "LIQ_VOID": 73.0, "AMD_CONT": 72.0, "FVG_CONT": 70.0, "ICHIMOKU": 65.0,
    "SAR": 60.0, "LIQ_SWEEP": 72.0,
}


def run(strats, buy_only_execution=False):
    return tg.run_trend_gate(strats, TF, buy_only=set(), scores=SCORES,
                             buy_only_execution=buy_only_execution)


def fmt(label, r):
    print(f"{label:<45}trades={r['trades']:>4}  pf={str(r['pf']):>6}  wr={r['wr']}%  "
          f"net={r['net_pnl']:>9}  buy={r['n_buy']}/{r['pf_buy']}  sell={r['n_sell']}/{r['pf_sell']}  src={r['src']}")


def main():
    print("=== 1. Pool intero (bidirezionale) ===")
    full = run(POOL)
    fmt("TUTTE E 10", full)

    print("\n=== 2. Pool intero (buy-only execution) ===")
    full_bo = run(POOL, buy_only_execution=True)
    fmt("TUTTE E 10 (buy-only)", full_bo)

    print("\n=== 3. Leave-one-out (bidirezionale) - PF combinato rimuovendo 1 strategia ===")
    baseline_pf = full["pf"] or 0
    loo_results = []
    for s in POOL:
        rest = [x for x in POOL if x != s]
        r = run(rest)
        delta = (r["pf"] or 0) - baseline_pf
        loo_results.append((s, r, delta))
        fmt(f"SENZA {s} (delta PF={delta:+.2f})", r)

    print("\n=== 4. Singole componenti (per confronto) ===")
    for s in POOL:
        r = run([s])
        fmt(s, r)

    print("\n=== interpretazione leave-one-out ===")
    loo_results.sort(key=lambda x: -x[2])
    for s, r, delta in loo_results:
        verdict = "PESA (rimuoverla migliora)" if delta > 0.05 else \
                  ("CONTRIBUISCE (rimuoverla peggiora)" if delta < -0.05 else "NEUTRA")
        print(f"{s:<16} delta PF senza di lei: {delta:+.2f}  ->  {verdict}")


if __name__ == "__main__":
    main()
