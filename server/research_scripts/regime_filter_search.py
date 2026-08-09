#!/usr/bin/env python3
"""
09/08 - approfondimento richiesto dall'utente su "cambio strategia per
regime", dopo aver ricordato che una versione precedente di oggi (rect_engine
+ range-fade in stato RANGING) era risultata dannosa. Qui non uno switch fra
due strategie diverse, ma un FILTRO di regime per ciascuna strategia della
shortlist (auto_combo_search.py) - verifica se ristringere una strategia al
suo regime migliore (scelto SOLO guardando l'in-sample) migliora l'out-of-
sample rispetto a lasciarla libera, stessa disciplina di auto_combo_search.py.

Usa _regime_series (ind["regime"], backtest.py) - il classificatore reale
gia' verificato contro NXS_Inputs.mqh/InpEnableGrid, NON rect_engine (quello
resta specifico per la conferma di breakout in TREND_GATE).
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import backtest as bt
import majority_vote_combo as mv

SYMBOL = "XAUUSD"
TF = "4h"
SHORTLIST = ["BREAKOUT_ACC", "AMD_CONT", "FVG_CONT", "LONDON_BO", "MACD", "SAR",
             "TURTLE_SOUP", "ADX_RSI", "EMA_PULLBACK", "FVG_MIT", "ICHIMOKU", "TSI"]
REGIME_NAMES = {0: "UNKNOWN", 1: "STRONG_TREND", 2: "WEAK_TREND", 3: "VOLATILE",
                4: "CHOPPY", 5: "RANGING"}
MIN_TRADES = 5


def _run_tagged(strat, frac_range):
    """Backtest della singola strategia sulla fetta [frac_range], ogni trade
    taggato col regime della barra di ingresso. SL/TP fisso 1.5/3.0 ATR,
    stesso standard usato in tutto il resto della sessione."""
    candles, src = bt._fetch_real(SYMBOL, TF)
    n = len(candles)
    i0, i1 = int(n * frac_range[0]), int(n * frac_range[1])
    candles = candles[i0:i1]
    intraday = bt._load_dukascopy_m15(SYMBOL) if src == "dukascopy" else None
    ind = bt._prep(candles, intraday_ref=intraday)
    atr = ind["atr"]
    regime = ind["regime"]
    equity = mv.START_EQUITY
    trades = []
    position = None
    for i in range(60, len(candles)):
        px = candles[i]["close"]
        if position is not None:
            hi, lo = candles[i]["high"], candles[i]["low"]
            hit = None
            if position["dir"] == 1:
                if lo <= position["sl"]:
                    hit = ("SL", position["sl"])
                elif hi >= position["tp"]:
                    hit = ("TP", position["tp"])
            else:
                if hi >= position["sl"]:
                    hit = ("SL", position["sl"])
                elif lo <= position["tp"]:
                    hit = ("TP", position["tp"])
            if not hit and (i - position["open_i"]) >= mv.MAX_HOLD:
                hit = ("TIME", px)
            if hit:
                reason, exitpx = hit
                rd = position["risk_dist"] if position["risk_dist"] > 0 else 1e-9
                r_mult = ((exitpx - position["entry"]) / rd) if position["dir"] == 1 \
                    else ((position["entry"] - exitpx) / rd)
                pnl = round(r_mult * position["risk_money"], 2)
                equity += pnl
                trades.append({"pnl": pnl, "regime": position["regime"]})
                position = None
            continue
        a = atr[i]
        if not a:
            continue
        v = bt.STRATEGIES[strat](candles, ind, i)
        if v == 0:
            continue
        dir_ = v
        entry = px
        sl_dist = a * 1.5
        tp_dist = a * 3.0
        sl = entry - sl_dist if dir_ == 1 else entry + sl_dist
        tp = entry + tp_dist if dir_ == 1 else entry - tp_dist
        position = {"dir": dir_, "entry": entry, "sl": sl, "tp": tp, "open_i": i,
                    "risk_dist": sl_dist, "risk_money": equity * (mv.RISK_PCT / 100.0),
                    "regime": regime[i]}
    return trades


def _pf(trades):
    if not trades:
        return None, 0
    gw = sum(t["pnl"] for t in trades if t["pnl"] > 0)
    gl = -sum(t["pnl"] for t in trades if t["pnl"] < 0)
    pf = round(gw / gl, 2) if gl > 0 else (None if gw == 0 else float("inf"))
    return pf, len(trades)


def main():
    print(f"{'Strategia':<16}{'Regime scelto (IS)':<18}{'OOS libero':>14}{'OOS filtrato':>15}{'Delta':>8}")
    rows = []
    for strat in SHORTLIST:
        is_trades = _run_tagged(strat, (0.0, 0.6))
        oos_trades = _run_tagged(strat, (0.6, 1.0))

        # scegli il regime migliore SOLO da IS (mai guardare OOS per scegliere)
        by_regime = {}
        for t in is_trades:
            by_regime.setdefault(t["regime"], []).append(t)
        best_regime, best_pf = None, -1
        for r, ts in by_regime.items():
            pf, n = _pf(ts)
            if pf is not None and n >= MIN_TRADES and pf > best_pf:
                best_pf, best_regime = pf, r

        oos_free_pf, oos_free_n = _pf(oos_trades)
        if best_regime is not None:
            oos_filtered = [t for t in oos_trades if t["regime"] == best_regime]
            oos_filt_pf, oos_filt_n = _pf(oos_filtered)
        else:
            oos_filt_pf, oos_filt_n = None, 0

        delta = (oos_filt_pf or 0) - (oos_free_pf or 0) if best_regime is not None else None
        rname = REGIME_NAMES.get(best_regime, "—") if best_regime is not None else "—"
        rows.append((strat, rname, oos_free_pf, oos_free_n, oos_filt_pf, oos_filt_n, delta))
        d_s = f"{delta:+.2f}" if delta is not None else "—"
        print(f"{strat:<16}{rname:<18}{str(oos_free_pf)+'/'+str(oos_free_n):>14}"
              f"{str(oos_filt_pf)+'/'+str(oos_filt_n):>15}{d_s:>8}")

    print("\nDelta = PF out-of-sample filtrato per regime meno PF out-of-sample libero.")
    print("Positivo = il filtro di regime aiuta davvero, non solo sull'in-sample.")


if __name__ == "__main__":
    main()
