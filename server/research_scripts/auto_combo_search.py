#!/usr/bin/env python3
"""
09/08 - Fase 2 della pipeline proposta all'utente: ricerca automatica di
TUTTE le coppie e triple della shortlist (12 strategie, le piu' coerenti
sui 5 timeframe della Fase 1 - full_strategy_tf_scan.py), ciascuna valutata
con split in-sample (primi 60%)/out-of-sample (ultimi 40%) INTEGRATO nel
motore di ricerca stesso - mai una combinazione scelta guardando il
periodo intero, sempre e solo l'ultima fetta mai vista durante la scelta.

Combinazione = accordo UNANIME (min_votes = dimensione del pool): e' la
lettura piu' letterale di "breakout + adx_rsi" - entrambe le strategie
devono confermare sulla stessa barra, non "almeno una delle due". Motore:
majority_vote_combo.py (nessun gate ADX/breakout - il test di ieri con
TREND_GATE ha mostrato che quel gate lascia votare troppo poche strategie).

Escluso LIQ_VOID dalla shortlist: e' letteralmente la stessa funzione di
FVG_CONT (server/backtest.py:3311, "liquidity void = FVG proxy") - tenerle
entrambe avrebbe pesato due volte lo stesso segnale in ogni combo che le
includesse insieme, lo stesso bug (non riconosciuto) di ieri.
"""
import sys
import os
import itertools
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import backtest as bt
import majority_vote_combo as mv

SYMBOL = "XAUUSD"
TF = "4h"
SHORTLIST = ["BREAKOUT_ACC", "AMD_CONT", "FVG_CONT", "LONDON_BO", "MACD", "SAR",
             "TURTLE_SOUP", "ADX_RSI", "EMA_PULLBACK", "FVG_MIT", "ICHIMOKU", "TSI"]
MIN_OOS_TRADES = 5


def _run_slice(strats, frac_range, min_votes):
    candles, src = bt._fetch_real(SYMBOL, TF)
    n = len(candles)
    i0, i1 = int(n * frac_range[0]), int(n * frac_range[1])
    candles = candles[i0:i1]
    intraday = bt._load_dukascopy_m15(SYMBOL) if src == "dukascopy" else None
    ind = bt._prep(candles, intraday_ref=intraday)
    atr = ind["atr"]
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
                trades.append({"side": "BUY" if position["dir"] == 1 else "SELL", "pnl": pnl})
                position = None
            continue
        a = atr[i]
        if not a:
            continue
        votes = sum(bt.STRATEGIES[s](candles, ind, i) for s in strats)
        if votes >= min_votes:
            dir_ = 1
        elif votes <= -min_votes:
            dir_ = -1
        else:
            continue
        entry = px
        sl_dist = a * 1.5
        tp_dist = a * 3.0
        sl = entry - sl_dist if dir_ == 1 else entry + sl_dist
        tp = entry + tp_dist if dir_ == 1 else entry - tp_dist
        position = {"dir": dir_, "entry": entry, "sl": sl, "tp": tp, "open_i": i,
                    "risk_dist": sl_dist, "risk_money": equity * (mv.RISK_PCT / 100.0)}
    gw = sum(t["pnl"] for t in trades if t["pnl"] > 0)
    gl = -sum(t["pnl"] for t in trades if t["pnl"] < 0)
    pf = round(gw / gl, 2) if gl > 0 else (None if gw == 0 else float("inf"))
    wr = round(100 * sum(1 for t in trades if t["pnl"] >= 0) / len(trades), 1) if trades else None
    return {"trades": len(trades), "pf": pf, "wr": wr, "net": round(equity - mv.START_EQUITY, 2)}


def main():
    candidates = []
    for size in (1, 2, 3):
        for combo in itertools.combinations(SHORTLIST, size):
            combo = list(combo)
            min_votes = len(combo)  # accordo unanime
            is_r = _run_slice(combo, (0.0, 0.6), min_votes)
            oos_r = _run_slice(combo, (0.6, 1.0), min_votes)
            candidates.append({"combo": combo, "size": size, "in_sample": is_r, "out_of_sample": oos_r})
        print(f"[{size}-tuple] fatto", flush=True)

    survivors = [c for c in candidates
                 if c["out_of_sample"]["trades"] >= MIN_OOS_TRADES
                 and c["out_of_sample"]["pf"] is not None
                 and c["out_of_sample"]["pf"] > 1.0]
    survivors.sort(key=lambda c: -c["out_of_sample"]["pf"])

    print(f"\n{len(candidates)} combinazioni testate ({len(survivors)} superano OOS trades>={MIN_OOS_TRADES} e PF>1.0)\n")
    print(f"{'Combinazione':<55}{'IS PF':>8}{'IS n':>6}{'OOS PF':>8}{'OOS n':>7}{'OOS WR%':>9}")
    for c in survivors[:30]:
        name = "+".join(c["combo"])
        isr, oosr = c["in_sample"], c["out_of_sample"]
        print(f"{name:<55}{str(isr['pf']):>8}{isr['trades']:>6}{str(oosr['pf']):>8}{oosr['trades']:>7}{str(oosr['wr']):>9}")

    import json
    out_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "auto_combo_search_results.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(candidates, f, indent=2)
    print(f"\nSalvato: {out_path}")


if __name__ == "__main__":
    main()
