#!/usr/bin/env python3
"""
06/08 - grid recovery (porting di NXS_GridRecovery.mqh, vedi commento su
grid_max_legs in backtest.py) applicato alle strategie con edge positivo
gia' confermato (find_best_profiles.py + portfolio_test.py del 06/08),
ognuna col proprio profilo SL/TP/BE/trailing. Confronta baseline (senza
grid) contro grid ON, stessi dati/costi, per vedere quali strategie ne
traggono beneficio reale e quali no - non un'ipotesi, un confronto diretto.

Esegui dalla root del repo: python3 server/research_scripts/grid_recovery_test.py
"""
import sys
sys.path.insert(0, "server")
import backtest as bt

COSTS = bt.COST_PRESETS["retail_standard"]

# strat_id -> (tf, atr_sl, atr_tp, breakeven_r, trailing_atr) dal giro
# find_best_profiles.py del 06/08 post-fix (PF>1.0, >=15 trade, no flag
# campione piccolo - stessa lista di portfolio_test.py).
CANDIDATES = {
    "OTE_CONT":                 ("1d", 1.0, 4.0, 1.0, 2.5),
    "BREAKOUT_ACC":             ("1d", 2.0, 4.0, 1.5, 2.5),
    "SH_BMS_RTO":               ("1d", 1.0, 2.0, 1.0, 2.5),
    "TSI":                      ("1d", 1.0, 4.0, 0.0, 2.5),
    "ADX_RSI":                  ("1d", 2.0, 4.0, 0.0, 2.5),
    "LIQ_SWEEP":                ("1d", 1.5, 2.0, 0.0, 0.0),
    "FVG_MIT":                  ("1d", 1.0, 2.0, 0.0, 0.0),
    "THREE_BAR_DELIVERY_BREAK": ("4h", 1.5, 3.0, 0.0, 0.0),
    "EMA_PULLBACK":             ("4h", 1.0, 4.0, 0.0, 0.0),
    "MACD":                     ("4h", 1.0, 4.0, 0.0, 0.0),
    "SAR":                      ("4h", 2.0, 4.0, 0.0, 0.0),
    "FVG_CONT":                 ("4h", 1.0, 4.0, 0.0, 0.0),
    "LIQ_VOID":                 ("4h", 1.5, 3.0, 0.0, 0.0),
}


def main():
    rows = []
    for strat, (tf, sl, tp, be, trail) in CANDIDATES.items():
        kw = dict(symbol="XAUUSD", strategy=strat, timeframe=tf,
                  atr_sl=sl, atr_tp=tp, breakeven_r=be, trailing_atr=trail, **COSTS)
        base = bt.run_backtest(**kw)
        grid = bt.run_backtest(grid_max_legs=3, grid_step_atr=1.2,
                               grid_risk_mult=1.0, grid_regime_filter=True, **kw)
        n_multi = sum(1 for t in grid["trade_list"] if t["legs"] > 1)
        rows.append({
            "strat": strat, "tf": tf,
            "base_pf": base["profit_factor"], "base_dd": base["max_dd_pct"],
            "base_pnl": base["net_pnl"], "base_trades": base["trades"],
            "grid_pf": grid["profit_factor"], "grid_dd": grid["max_dd_pct"],
            "grid_pnl": grid["net_pnl"], "grid_trades": grid["trades"],
            "n_multi_leg": n_multi,
        })
        print(f"[{strat}] fatto", flush=True)

    print("\n" + "=" * 130)
    print(f"{'Strategia':<26}{'TF':>4}{'BasePF':>8}{'BaseDD%':>9}{'BasePnL':>10}"
          f"{'GridPF':>8}{'GridDD%':>9}{'GridPnL':>10}{'#multi':>8}  Delta")
    for r in rows:
        d_pf = r["grid_pf"] - r["base_pf"]
        tag = "MEGLIO" if d_pf > 0.02 else ("PEGGIO" if d_pf < -0.02 else "invariato")
        print(f"{r['strat']:<26}{r['tf']:>4}{r['base_pf']:>8.2f}{r['base_dd']:>9.2f}"
              f"{r['base_pnl']:>10.1f}{r['grid_pf']:>8.2f}{r['grid_dd']:>9.2f}"
              f"{r['grid_pnl']:>10.1f}{r['n_multi_leg']:>8}  {tag} (dPF={d_pf:+.2f})")
    print("=" * 130)


if __name__ == "__main__":
    main()
