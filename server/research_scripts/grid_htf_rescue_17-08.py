#!/usr/bin/env python3
"""
17/08 - richiesta esplicita: magari altre configurazioni (griglia SL/TP +
filtro HTF, l'asse che l'agente parallelo sta usando su MT5/SAR) salvano
qualcuna delle strategie bocciate oggi col solo stop ATR di default
(1.5/4.0, nessun HTF). Usa run_backtest() - il motore canonico, non uno
script ad-hoc - su un set di bocciate/borderline di oggi, con una
piccola griglia SL/TP e htf_filter on/off, storico intero + split a due
meta' (bar_range, walk-forward-lite dato che trade_list e' troncato a
200 in run_backtest).
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import backtest as bt

TF = "1h"
BARS = 32000
GRID = [(1.0, 6.0), (1.5, 4.0), (2.0, 6.0), (1.0, 3.0)]
CANDIDATES = [
    "SAR_ADX20", "SAR_FLIP", "BREAKOUT_ACC", "DARVAS_BOX", "TSI",
    "LIQ_SWEEP", "TURTLE_SOUP", "STRUCT_REACT", "SH_BMS_RTO",
]
cost = bt.COST_PRESETS["retail_standard"]


def run_one(name, sl, tp, htf):
    r = bt.run_backtest(symbol="XAUUSD", timeframe=TF, strategy=name, strategies=[name],
                         risk_pct=1.0, atr_sl=sl, atr_tp=tp, bars=BARS,
                         htf_filter=htf, trend_period=50,
                         spread_price=cost["spread_price"], slippage_price=cost["slippage_price"])
    r1 = bt.run_backtest(symbol="XAUUSD", timeframe=TF, strategy=name, strategies=[name],
                          risk_pct=1.0, atr_sl=sl, atr_tp=tp, bars=BARS,
                          htf_filter=htf, trend_period=50, bar_range=(0.0, 0.5),
                          spread_price=cost["spread_price"], slippage_price=cost["slippage_price"])
    r2 = bt.run_backtest(symbol="XAUUSD", timeframe=TF, strategy=name, strategies=[name],
                          risk_pct=1.0, atr_sl=sl, atr_tp=tp, bars=BARS,
                          htf_filter=htf, trend_period=50, bar_range=(0.5, 1.0),
                          spread_price=cost["spread_price"], slippage_price=cost["slippage_price"])
    return r, r1, r2


def main():
    for name in CANDIDATES:
        print(f"\n=== {name} ===", flush=True)
        best = None
        for sl, tp in GRID:
            for htf in (False, True):
                try:
                    r, r1, r2 = run_one(name, sl, tp, htf)
                except Exception as e:
                    print(f"  SL{sl}/TP{tp} HTF={'on ' if htf else 'off'}  ERRORE: {str(e)[:100]}", flush=True)
                    continue
                pf = r.get("profit_factor")
                n = r.get("trades", 0)
                if n < 20:
                    continue
                pf1, pf2 = r1.get("profit_factor"), r2.get("profit_factor")
                n1, n2 = r1.get("trades", 0), r2.get("trades", 0)
                dd = r.get("max_dd_pct")
                print(f"  SL{sl}/TP{tp} HTF={'on ' if htf else 'off'}  n={n:4d} PF={pf}  DD={dd}%  "
                      f"[1a meta n={n1} PF={pf1} | 2a meta n={n2} PF={pf2}]", flush=True)
                score = (pf or 0)
                if pf1 and pf2 and pf1 >= 1.0 and pf2 >= 1.0:
                    if best is None or score > best[0]:
                        best = (score, sl, tp, htf, pf, n)
        if best:
            print(f"  --> MIGLIORE CON ENTRAMBE LE META POSITIVE: SL{best[1]}/TP{best[2]} "
                  f"HTF={'on' if best[3] else 'off'} PF={best[4]} n={best[5]}", flush=True)
        else:
            print("  --> nessuna combinazione con entrambe le meta positive", flush=True)


if __name__ == "__main__":
    main()
