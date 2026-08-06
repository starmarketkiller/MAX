#!/usr/bin/env python3
"""
06/08 - "dove migliorare l'esecuzione e con cosa": per le strategie con edge
gia' confermato (LONDON_BO, MACD+grid, FVG_CONT+grid, LIQ_VOID), testa le
leve di esecuzione non ancora esplorate oggi:

1. confirm_bars (0,1,2): il segnale deve restare valido N barre consecutive
   prima di essere preso - filtra cross/condizioni che durano un solo tick.
2. cooldown_bars (0,2,5): barre minime fra un trade e il successivo.
3. allow_flip (True/False): un segnale opposto fresco chiude ed apre subito,
   invece di aspettare SL/TP/TIME.
4. costi "stress" (spread/slippage raddoppiati rispetto a retail_standard,
   vedi COST_PRESETS in backtest.py) - la domanda e' se l'edge sopravvive a
   un'esecuzione peggiore di quella assunta finora, non solo se il numero
   e' bello con costi ottimistici.

Ogni leva testata isolatamente sul profilo migliore gia' trovato (non un
prodotto cartesiano completo - troppi run per il beneficio marginale).

Esegui dalla root del repo: python3 server/research_scripts/execution_tuning.py
"""
import sys
sys.path.insert(0, "server")
import backtest as bt

RETAIL = bt.COST_PRESETS["retail_standard"]
STRESS = bt.COST_PRESETS["stress"]

CONFIGS = {
    "LONDON_BO": dict(tf="1h", atr_sl=2.0, atr_tp=4.0, breakeven_r=0.0, trailing_atr=0.0),
    "MACD":      dict(tf="4h", atr_sl=1.0, atr_tp=4.0, breakeven_r=0.0, trailing_atr=0.0,
                      grid_max_legs=3, grid_step_atr=1.2, grid_regime_filter=True),
    "FVG_CONT":  dict(tf="4h", atr_sl=1.0, atr_tp=4.0, breakeven_r=0.0, trailing_atr=0.0,
                      grid_max_legs=3, grid_step_atr=1.2, grid_regime_filter=True),
    "LIQ_VOID":  dict(tf="4h", atr_sl=1.5, atr_tp=3.0, breakeven_r=0.0, trailing_atr=0.0),
}


def run(strat, params, **overrides):
    kw = dict(params)
    tf = kw.pop("tf")
    kw.update(overrides)
    r = bt.run_backtest(symbol="XAUUSD", strategy=strat, timeframe=tf, **kw)
    return r["trades"], r["profit_factor"], r["max_dd_pct"], r["net_pnl"]


def fmt(label, res):
    tr, pf, dd, pnl = res
    pf_s = f"{pf:.2f}" if pf is not None else " n/a"
    return f"    {label:<28} trades={tr:>4}  PF={pf_s}  MaxDD={dd:>5.1f}%  NetPnL={pnl:>9.1f}"


def main():
    for strat, params in CONFIGS.items():
        print(f"\n=== {strat} ===")
        base = run(strat, params, **RETAIL)
        print(fmt("baseline (retail_standard)", base))

        for cb in (1, 2):
            r = run(strat, params, confirm_bars=cb, **RETAIL)
            print(fmt(f"confirm_bars={cb}", r))

        for cd in (2, 5):
            r = run(strat, params, cooldown_bars=cd, **RETAIL)
            print(fmt(f"cooldown_bars={cd}", r))

        r = run(strat, params, allow_flip=True, **RETAIL)
        print(fmt("allow_flip=True", r))

        stress = run(strat, params, **STRESS)
        print(fmt("costi STRESS (spread/slip 2x)", stress))
        if base[1] and stress[1] is not None:
            drop = 100 * (1 - stress[1] / base[1])
            print(f"    -> PF sotto stress: {'-' if drop>=0 else '+'}{abs(drop):.0f}% "
                  f"rispetto a retail_standard")
        print(flush=True)


if __name__ == "__main__":
    main()
