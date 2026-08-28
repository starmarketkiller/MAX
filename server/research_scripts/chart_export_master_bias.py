#!/usr/bin/env python3
"""
12/08 - esporta candele+trade_list+equity_curve per FVG_CONT e SAR
(baseline vs +master_bias=BREAKOUT_ACC) sulla finestra OOS (0.6-1.0),
stessa identica configurazione di master_bias_real_engine.py, per
costruire un grafico delle operazioni (richiesta esplicita dell'utente).
"""
import sys
import os
import json

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import backtest as bt

SYMBOL, BARS, TF = "XAUUSD", 110000, "4h"
MASTER = "BREAKOUT_ACC"
SLAVES = ["FVG_CONT", "SAR"]
BAR_RANGE = (0.6, 1.0)


def slice_candles():
    candles, _src = bt._fetch_real(SYMBOL, TF, BARS)
    n = len(candles)
    i0 = max(0, int(n * BAR_RANGE[0]))
    i1 = min(n, int(n * BAR_RANGE[1]))
    return candles[i0:i1]


def run(strat, biased):
    kwargs = dict(symbol=SYMBOL, timeframe=TF, strategy=strat, strategies=[strat],
                  risk_pct=1.0, bars=BARS, bar_range=BAR_RANGE)
    if biased:
        kwargs["master_bias"] = MASTER
    r = bt.run_backtest(**kwargs)
    return r


def main():
    out = {"symbol": SYMBOL, "timeframe": TF, "bar_range": BAR_RANGE,
           "master": MASTER, "candles": slice_candles(), "strategies": {}}
    for slave in SLAVES:
        out["strategies"][slave] = {}
        for label, biased in (("baseline", False), ("bias", True)):
            r = run(slave, biased)
            out["strategies"][slave][label] = {
                "trades": r.get("trades", 0),
                "pf": r.get("profit_factor"),
                "dd": r.get("max_dd_pct"),
                "win_rate": r.get("win_rate"),
                "net_pnl": r.get("net_pnl"),
                "trade_list": r.get("trade_list", []),
                "equity_curve": r.get("equity_curve", []),
            }
            print(f"{slave} [{label}]: pf={r.get('profit_factor')} n={r.get('trades')}", flush=True)
    out_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "..", "..", "chart_export_master_bias.json"
    )
    out_path = os.path.abspath(out_path)
    with open(out_path, "w") as f:
        json.dump(out, f)
    print("wrote", out_path, os.path.getsize(out_path), "bytes")


if __name__ == "__main__":
    main()
