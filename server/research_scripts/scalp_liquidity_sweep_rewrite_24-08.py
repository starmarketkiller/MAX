#!/usr/bin/env python3
"""
24/08 (24) - riscrittura vera (non un altro filtro) delle SCALP_*, su
richiesta esplicita dell'utente, informata dalla ricerca online (vedi
scalp_session_rewrite_24-08.py per le fonti - contenuto per lo piu'
promozionale, ma il meccanismo strutturale "liquidity sweep reversal
nell'overlap London-NY" ricorre in fonti indipendenti tra loro).

Nuovo segnale, non una variante di RSI/EMA/Bollinger: sweep di uno swing
a 30 barre M15 (~7.5 ore, scala coerente con lo scalping - non i 20/15
usati per SWING_FALSEBREAK su H1, qui scalati alla granularita' M15) +
rientro (stessa logica sweep+rejection gia' validata a scala swing,
qui applicata per la prima volta a M15), ristretto alla finestra di
overlap London-NY (12-16 UTC, il vincolo di liquidita' emerso dalla
ricerca). R:R 1:2, stop oltre il wick dello sweep (strutturale, non
ATR-arbitrario - stessa lezione "stop troppo stretto = costi
dominanti" di oggi, qui risolta ancorando allo swing invece che a un
moltiplicatore fisso).
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import backtest as bt

OVERLAP_START_H, OVERLAP_END_H = 12, 16
RR = 2.0
MAX_HOLD_BARS = 200
BUFFER_ATR = 0.2


def pf(rs):
    g = sum(r for r in rs if r > 0)
    l = -sum(r for r in rs if r < 0)
    return g / l if l > 0 else (float("inf") if g > 0 else 0.0)


def walk_forward(rs, nw=5):
    n = len(rs)
    if n < nw * 5:
        return None
    size = n // nw
    return [(len(rs[w * size:(w + 1) * size] if w < nw - 1 else rs[w * size:]),
              pf(rs[w * size:(w + 1) * size] if w < nw - 1 else rs[w * size:]))
            for w in range(nw)]


def report(label, trades):
    print(f"--- {label}: {len(trades)} trade grezzi ---", flush=True)
    for preset in ("retail_standard", "ecn"):
        net = []
        for t in trades:
            cost = bt.scaled_cost_for_price(preset, t["entry"])
            cost_r = min((cost["spread_price"] + cost["slippage_price"]) / t["risk_dist"], bt.MAX_COST_R_PER_TRADE)
            net.append(t["raw_r"] - cost_r)
        wf = walk_forward(net)
        wf_str = " | ".join(f"{p:.2f}" for _, p in wf) if wf else "n/a"
        n_pos = sum(1 for _, p in (wf or []) if p >= 1.0)
        mid = len(net) // 2
        h1, h2 = net[:mid], net[mid:]
        print(f"  {preset:16s} aggPF={pf(net):.2f} sumR={sum(net):+7.1f} win>=1:{n_pos}/{len(wf) if wf else 0}"
              f"  meta1={pf(h1):.2f}/meta2={pf(h2):.2f}  [{wf_str}]", flush=True)


def find_pivots(candles, left, right):
    n = len(candles)
    piv_high = [None] * n
    piv_low = [None] * n
    last_ph, last_pl = None, None
    for i in range(left, n):
        k = i - right
        if k < left:
            piv_high[i] = last_ph
            piv_low[i] = last_pl
            continue
        window_hi = [candles[j]["high"] for j in range(k - left, k + right + 1)]
        window_lo = [candles[j]["low"] for j in range(k - left, k + right + 1)]
        if candles[k]["high"] == max(window_hi):
            last_ph = candles[k]["high"]
        if candles[k]["low"] == min(window_lo):
            last_pl = candles[k]["low"]
        piv_high[i] = last_ph
        piv_low[i] = last_pl
    return piv_high, piv_low


def collect(candles, atr, left, right, restrict_overlap):
    n = len(candles)
    piv_high, piv_low = find_pivots(candles, left, right)
    trades = []
    for i in range(max(left + right + 5, 300), n - 2):
        a = atr[i]
        if not a:
            continue
        if restrict_overlap:
            hh = int(candles[i + 1]["time"].split(" ")[1].split(":")[0])
            if not (OVERLAP_START_H <= hh < OVERLAP_END_H):
                continue
        ph, pl = piv_high[i], piv_low[i]
        cur = candles[i]
        sig, stop = 0, None
        if pl is not None:
            swept = any(candles[i - k]["low"] < pl for k in range(0, 2))
            if swept and cur["close"] > pl and cur["close"] > cur["open"]:
                sig, stop = 1, pl - BUFFER_ATR * a
        if sig == 0 and ph is not None:
            swept = any(candles[i - k]["high"] > ph for k in range(0, 2))
            if swept and cur["close"] < ph and cur["close"] < cur["open"]:
                sig, stop = -1, ph + BUFFER_ATR * a
        if sig == 0:
            continue
        entry = candles[i + 1]["open"]
        rd = abs(entry - stop)
        if rd <= 0:
            continue
        tp = entry + sig * RR * rd
        exit_r = None
        for j in range(i + 2, min(i + 2 + MAX_HOLD_BARS, n)):
            hi, lo = candles[j]["high"], candles[j]["low"]
            if sig == 1:
                if lo <= stop: exit_r = -1.0; break
                elif hi >= tp: exit_r = RR; break
            else:
                if hi >= stop: exit_r = -1.0; break
                elif lo <= tp: exit_r = RR; break
        if exit_r is None:
            continue
        trades.append({"entry": entry, "risk_dist": rd, "raw_r": exit_r})
    return trades


def main():
    candles, src = bt._fetch_real("XAUUSD", "15m", 110000)
    ind = bt._prep(candles)
    atr = ind["atr"]
    print(f"M15: {len(candles)} candele ({src})", flush=True)

    for left, right in [(30, 10), (20, 8), (15, 5)]:
        report(f"Sweep swing L{left}/R{right}, tutte le ore", collect(candles, atr, left, right, False))
        report(f"Sweep swing L{left}/R{right}, SOLO overlap 12-16 UTC", collect(candles, atr, left, right, True))


if __name__ == "__main__":
    main()
