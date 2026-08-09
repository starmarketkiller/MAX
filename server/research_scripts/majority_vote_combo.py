#!/usr/bin/env python3
"""
09/08 - motore di combinazione ALTERNATIVO a TREND_GATE: voto a maggioranza
puro, NESSUN gate ADX/breakout/conviction-istituzionale. Costruito dopo che
il test TREND_GATE su un pool di 10 strategie ha mostrato che il gate e'
troppo severo per far votare la maggior parte del pool (8 su 10 non
contribuivano NESSUN segnale - combo_scan.py). Qui invece ogni strategia del
pool vota (+1/0/-1) sulla stessa barra; si entra quando almeno `min_votes`
strategie sono d'accordo sulla stessa direzione. SL/TP fisso ad ATR (stesso
1.5/3.0 usato nello scan a parametri fissi, per confronto omogeneo).

NON e' fedele a nessun meccanismo MQL5 reale (dichiarato, sperimentale) -
serve a rispondere alla domanda "il motore combina qualcosa di buono?" con
un meccanismo che lascia effettivamente votare l'intero pool, a differenza
di TREND_GATE.
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import backtest as bt

COSTS = bt.COST_PRESETS["retail_standard"]
SYMBOL = "XAUUSD"
START_EQUITY = 10000.0
RISK_PCT = 1.0
MAX_HOLD = 40


def run_majority_vote(strats, tf, min_votes=2, atr_sl_mult=1.5, atr_tp_mult=3.0,
                      buy_only_execution=False, bars_min=60):
    candles, src = bt._fetch_real(SYMBOL, tf)
    ind = bt._prep(candles, intraday_ref=(bt._load_dukascopy_m15(SYMBOL) if src == "dukascopy" else None))
    atr = ind["atr"]

    equity = START_EQUITY
    trades = []
    position = None
    n = len(candles)
    for i in range(bars_min, n):
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
            if not hit and (i - position["open_i"]) >= MAX_HOLD:
                hit = ("TIME", px)
            if hit:
                reason, exitpx = hit
                rd = position["risk_dist"] if position["risk_dist"] > 0 else 1e-9
                r_mult = ((exitpx - position["entry"]) / rd) if position["dir"] == 1 \
                    else ((position["entry"] - exitpx) / rd)
                spread_r = COSTS["spread_price"] / rd if COSTS["spread_price"] > 0 else 0.0
                slip_r = 0.0
                if COSTS["slippage_price"] > 0:
                    slip_r = COSTS["slippage_price"] / rd
                    if reason in ("SL", "TIME"):
                        slip_r += COSTS["slippage_price"] / rd
                r_net = r_mult - spread_r - COSTS["commission_r"] - slip_r
                pnl = round(r_net * position["risk_money"], 2)
                equity += pnl
                trades.append({"side": "BUY" if position["dir"] == 1 else "SELL", "pnl": pnl, "reason": reason})
                position = None
            continue

        a = atr[i]
        if not a:
            continue
        votes = 0
        for s in strats:
            v = bt.STRATEGIES[s](candles, ind, i)
            votes += v
        if votes >= min_votes:
            dir_ = 1
        elif votes <= -min_votes:
            dir_ = -1
        else:
            continue
        if buy_only_execution and dir_ == -1:
            continue
        entry = px
        sl_dist = a * atr_sl_mult
        tp_dist = a * atr_tp_mult
        sl = entry - sl_dist if dir_ == 1 else entry + sl_dist
        tp = entry + tp_dist if dir_ == 1 else entry - tp_dist
        position = {"dir": dir_, "entry": entry, "sl": sl, "tp": tp, "open_i": i,
                    "risk_dist": sl_dist, "risk_money": equity * (RISK_PCT / 100.0)}

    gross_win = sum(t["pnl"] for t in trades if t["pnl"] > 0)
    gross_loss = -sum(t["pnl"] for t in trades if t["pnl"] < 0)
    pf = round(gross_win / gross_loss, 2) if gross_loss > 0 else (None if gross_win == 0 else float("inf"))
    wr = round(100 * sum(1 for t in trades if t["pnl"] >= 0) / len(trades), 1) if trades else None
    buys = [t for t in trades if t["side"] == "BUY"]
    sells = [t for t in trades if t["side"] == "SELL"]
    def _pf(lst):
        g = sum(t["pnl"] for t in lst if t["pnl"] > 0); l = -sum(t["pnl"] for t in lst if t["pnl"] < 0)
        return round(g / l, 2) if l > 0 else (None if g == 0 else float("inf"))
    return {
        "src": src, "trades": len(trades), "pf": pf, "wr": wr,
        "net_pnl": round(equity - START_EQUITY, 2),
        "n_buy": len(buys), "pf_buy": _pf(buys), "n_sell": len(sells), "pf_sell": _pf(sells),
    }
