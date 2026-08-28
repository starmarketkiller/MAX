#!/usr/bin/env python3
"""
17/08 - spunto da uno script TradingView (Bjorgum Key Levels) inviato
dall'utente: falso breakout su zona, stesso concetto di "Spring"/sweep
gia' chiuso 3 volte (LIQ_SWEEP/TURTLE_SOUP/CISD_TRUE, ancorati a
PDH/PDL/Asia session), MA con un ancoraggio diverso e mai provato: un
pivot di swing MAGGIORE (left=20/right=15 barre, quindi confermato solo
15 barre dopo essersi formato - nessun lookahead, stesso principio del
nostro choch_int/choch_ext ma con finestra piu' larga), zona larga
min(prezzo*2%, 0.5xATR) intorno al pivot, invece dei livelli
intraday/sessione (PDH/PDL/Asia) usati finora.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import backtest as bt

LEFT, RIGHT = 20, 15
LOOKBACK_ER, THR_ER = 4000, 0.045
MAX_HOLD = 200


def find_pivots(candles, atr):
    n = len(candles)
    piv_high = [None] * n   # prezzo del pivot high CONFERMATO fino a i (gia' noto, right barre fa)
    piv_low = [None] * n
    last_ph, last_pl = None, None
    for i in range(LEFT, n):
        # un pivot confermato a i-RIGHT richiede guardare avanti fino a i
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


def walk_forward(rs, nw=5):
    n = len(rs)
    if n < nw * 5:
        return None
    size = n // nw
    out = []
    for w in range(nw):
        seg = rs[w * size:(w + 1) * size] if w < nw - 1 else rs[w * size:]
        out.append((len(seg), pf(seg)))
    return out


def main():
    for tf in ("4h", "1h"):
        candles, src = bt._fetch_real("XAUUSD", tf, 110000)
        atr = bt.atr_series(candles, 14)
        closes = [c["close"] for c in candles]
        n = len(candles)
        piv_high, piv_low = find_pivots(candles, atr)

        trades = []
        for i in range(max(LEFT + RIGHT + 5, LOOKBACK_ER + 50), n - 2):
            a = atr[i]
            if not a:
                continue
            ph, pl = piv_high[i], piv_low[i]
            cur = candles[i]
            band = min(cur["close"] * 0.02, 0.5 * a)
            sig = 0
            # false break ribassista risolto: la barra CORRENTE (o le due precedenti)
            # ha rotto sotto la zona del pivot low e la barra corrente chiude sopra
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
            exit_r, exit_j = None, None
            for j in range(i + 2, min(i + 2 + MAX_HOLD, n)):
                hi, lo = candles[j]["high"], candles[j]["low"]
                if sig == 1:
                    if lo <= sl:
                        exit_r, exit_j = (sl - entry) / rd, j
                        break
                    elif hi >= tp:
                        exit_r, exit_j = (tp - entry) / rd, j
                        break
                else:
                    if hi >= sl:
                        exit_r, exit_j = (entry - sl) / rd, j
                        break
                    elif lo <= tp:
                        exit_r, exit_j = (entry - tp) / rd, j
                        break
            if exit_r is None:
                continue
            trades.append({"entry": entry, "risk_dist": rd, "raw_r": exit_r})

        print(f"--- Bjorgum-style false-break su swing maggiore, TF={tf}: {len(trades)} trade grezzi ---", flush=True)
        for preset in ("retail_standard", "ecn"):
            net = []
            for t in trades:
                cost = bt.scaled_cost_for_price(preset, t["entry"])
                cost_r = min((cost["spread_price"] + cost["slippage_price"]) / t["risk_dist"], bt.MAX_COST_R_PER_TRADE)
                net.append(t["raw_r"] - cost_r)
            wf = walk_forward(net)
            wf_str = " | ".join(f"PF={p:.2f}" for _, p in wf) if wf else "n/a"
            n_pos = sum(1 for _, p in (wf or []) if p >= 1.0)
            print(f"  {preset:16s} aggPF={pf(net):.2f} sumR={sum(net):+.1f} "
                  f"finestre_PF>=1:{n_pos}/{len(wf) if wf else 0}  [{wf_str}]", flush=True)


if __name__ == "__main__":
    main()
