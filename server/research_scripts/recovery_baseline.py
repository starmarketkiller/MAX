#!/usr/bin/env python3
"""
11/08 (6) - Fase C, primo passo: il motore ha gia' un meccanismo di
recovery (grid_max_legs/grid_step_atr/grid_risk_mult, porting di
NXS_ManageGrid) ma e' UNIFORME - ogni gamba aggiunta condivide lo stesso
sl/tp della posizione originale, cambia solo size ed entry. Prima di
disegnare una versione con gestione per-gamba differenziata (come chiesto
esplicitamente), verifico se il meccanismo uniforme gia' esistente aiuta
o peggiora sui migliori candidati del nucleo - baseline per capire se
vale la pena costruire la versione piu' sofisticata.

Confronto: nessun recovery vs recovery uniforme (1-2-3 gambe), walk-forward
a 5 finestre, riporto PF E max drawdown (non solo PF - il recovery aumenta
l'esposizione media, il rischio di rovina non si vede nel PF da solo).
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import backtest as bt

SYMBOL, BARS = "XAUUSD", 110000
N_WINDOWS = 5

# (strategia, TF, sl, tp, htf, be) - le piu' solide trovate finora in sessione
CANDIDATES = [
    ("CRT", "30m", 1.5, 3.0, False, 0.0),
    ("FVG_CONT", "4h", 1.0, 4.5, True, 0.0),
    ("TURTLE_SOUP", "1h", 1.0, 4.5, True, 0.0),
    ("EMA_PULLBACK", "1h", 1.5, 4.0, True, 0.0),
    ("SAR", "4h", 1.5, 4.0, True, 0.0),
]

RECOVERY_CONFIGS = [
    ("no_recovery", dict(grid_max_legs=0)),
    ("recovery_1leg", dict(grid_max_legs=1, grid_step_atr=1.2, grid_risk_mult=1.0, grid_regime_filter=True)),
    ("recovery_2leg", dict(grid_max_legs=2, grid_step_atr=1.2, grid_risk_mult=1.0, grid_regime_filter=True)),
]


def run(strat, tf, br, sl, tp, htf, be, **extra):
    r = bt.run_backtest(symbol=SYMBOL, timeframe=tf, strategy=strat, strategies=[strat],
                         risk_pct=1.0, bars=BARS, bar_range=br,
                         atr_sl=sl, atr_tp=tp, htf_filter=htf, breakeven_r=be, **extra)
    return {"trades": r.get("trades", 0), "pf": r.get("profit_factor"),
            "dd": r.get("max_dd_pct"), "ret": r.get("return_pct")}


def main():
    for strat, tf, sl, tp, htf, be in CANDIDATES:
        print(f"\n=== {strat} @ {tf} ===", flush=True)
        for label, cfg in RECOVERY_CONFIGS:
            wins = 0
            row = []
            for w in range(N_WINDOWS):
                br = (w / N_WINDOWS, (w + 1) / N_WINDOWS)
                r = run(strat, tf, br, sl, tp, htf, be, **cfg)
                row.append(f"pf={r['pf']} dd={r['dd']}% n={r['trades']}")
            print(f"  {label:<16}" + "  |  ".join(row), flush=True)


if __name__ == "__main__":
    main()
