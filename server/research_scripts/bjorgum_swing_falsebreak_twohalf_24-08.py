#!/usr/bin/env python3
"""
24/08 - validazione due-meta'-storia del candidato piu' interessante
lasciato aperto il 17/08 (falso breakout su swing maggiore, ispirato da
Bjorgum Key Levels): vedi
vault/01-Trading/NEXUS EA - Idee da Script TradingView Esterni (17-08).md
("Prossimo passo"). Stessa disciplina usata per il tetto-euro sul
portafoglio (m5_stop_portfolio_euro_16-08.py): split del campione a meta',
nessuna meta' negativa = non e' un risultato trascinato da un solo periodo.

Solo 1h (il campione migliore, 234 trade grezzi, ECN PF1.57 5/5 finestre
il 17/08). Logica di segnale IDENTICA a bjorgum_swing_falsebreak_17-08.py,
nessuna riottimizzazione qui - questo e' uno script di verifica, non di
tuning (regola vault: un'ipotesi per esperimento).
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import backtest as bt

LEFT, RIGHT = 20, 15
LOOKBACK_ER, THR_ER = 4000, 0.045
MAX_HOLD = 200
TF = "1h"


def find_pivots(candles):
    n = len(candles)
    piv_high = [None] * n
    piv_low = [None] * n
    last_ph, last_pl = None, None
    for i in range(LEFT, n):
        k = i - RIGHT
        if k < LEFT:
            piv_high[i] = last_ph
            piv_low[i] = last_pl
            continue
        window_hi = [candles[j]["high"] for j in range(k - LEFT, k + RIGHT + 1)]
        window_lo = [candles[j]["low"] for j in range(k - LEFT, k + RIGHT + 1)]
        if candles[k]["high"] == max(window_hi):
            last_ph = candles[k]["high"]
        if candles[k]["low"] == min(window_lo):
            last_pl = candles[k]["low"]
        piv_high[i] = last_ph
        piv_low[i] = last_pl
    return piv_high, piv_low


def efficiency_ratio(closes, i, lookback):
    if i < lookback:
        return None
    net = abs(closes[i] - closes[i - lookback])
    total = sum(abs(closes[k] - closes[k - 1]) for k in range(i - lookback + 1, i + 1))
    return net / total if total > 0 else None


def pf(rs):
    g = sum(r for r in rs if r > 0)
    l = -sum(r for r in rs if r < 0)
    return g / l if l > 0 else (float("inf") if g > 0 else 0.0)


def main():
    candles, src = bt._fetch_real("XAUUSD", TF, 110000)
    atr = bt.atr_series(candles, 14)
    closes = [c["close"] for c in candles]
    n = len(candles)
    piv_high, piv_low = find_pivots(candles)

    trades = []
    for i in range(max(LEFT + RIGHT + 5, LOOKBACK_ER + 50), n - 2):
        a = atr[i]
        if not a:
            continue
        ph, pl = piv_high[i], piv_low[i]
        cur = candles[i]
        band = min(cur["close"] * 0.02, 0.5 * a)
        sig = 0
        if pl is not None:
            zone_bottom = pl - band
            swept = any(candles[i - k]["low"] < zone_bottom for k in range(0, 3))
            if swept and cur["close"] > zone_bottom and cur["close"] > cur["open"]:
                sig = 1
        if sig == 0 and ph is not None:
            zone_top = ph + band
            swept = any(candles[i - k]["high"] > zone_top for k in range(0, 3))
            if swept and cur["close"] < zone_top and cur["close"] < cur["open"]:
                sig = -1
        if sig == 0:
            continue
        e = efficiency_ratio(closes, i, LOOKBACK_ER)
        if e is None or e < THR_ER:
            continue
        entry = candles[i + 1]["open"]
        sl = entry - sig * 1.5 * a
        tp = entry + sig * 4.0 * a
        rd = abs(entry - sl)
        if rd <= 0:
            continue
        exit_r = None
        for j in range(i + 2, min(i + 2 + MAX_HOLD, n)):
            hi, lo = candles[j]["high"], candles[j]["low"]
            if sig == 1:
                if lo <= sl:
                    exit_r = (sl - entry) / rd
                    break
                elif hi >= tp:
                    exit_r = (tp - entry) / rd
                    break
            else:
                if hi >= sl:
                    exit_r = (entry - sl) / rd
                    break
                elif lo <= tp:
                    exit_r = (entry - tp) / rd
                    break
        if exit_r is None:
            continue
        trades.append({"entry": entry, "risk_dist": rd, "raw_r": exit_r})

    print(f"--- Bjorgum-style false-break su swing maggiore, TF={TF}: {len(trades)} trade grezzi, verifica due meta' ---", flush=True)
    for preset in ("retail_standard", "ecn"):
        net = []
        for t in trades:
            cost = bt.scaled_cost_for_price(preset, t["entry"])
            cost_r = min((cost["spread_price"] + cost["slippage_price"]) / t["risk_dist"], bt.MAX_COST_R_PER_TRADE)
            net.append(t["raw_r"] - cost_r)
        mid = len(net) // 2
        first_half, second_half = net[:mid], net[mid:]
        print(f"  {preset}: aggregato PF={pf(net):.2f} sumR={sum(net):+.1f} n={len(net)}", flush=True)
        for label, seg in (("prima meta'", first_half), ("seconda meta'", second_half)):
            print(f"    {label:12s} n={len(seg):4d} PF={pf(seg):.2f} sumR={sum(seg):+.1f}", flush=True)


if __name__ == "__main__":
    main()
