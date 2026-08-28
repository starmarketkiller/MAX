#!/usr/bin/env python3
"""
24/08 - test di "Machine Learning Adaptive SuperTrend" (AlgoAlpha, script
TradingView condiviso dall'utente), uno dei 4 nuovi script di oggi (vedi
vault "NEXUS EA - Idee da Script TradingView Esterni 17-08", addendum
24/08). Idea distinta dal nostro SAR/nucleo: SuperTrend classico (fattore
3, ATR 10), ma invece dell'ATR grezzo usa il CENTROIDE di un k-means a 3
cluster (alta/media/bassa volatilita') fittato sugli ultimi 100 valori di
ATR, con warm-start dal centroide del bar precedente (replica lo `var`
array Pine, che NON riparte da zero ogni bar). Segnale: cambio di
direzione del SuperTrend (crossover/crossunder di dir attorno a 0).

Conversione a evento (nessuna posizione persistente, stop ATR fisso in
uscita) stessa scelta di Hull Suite/MACD+SMA200 in questa stessa serie di
test. Filtro di regime ER (trend, soglia 0.045): e' un sistema
trend-following per costruzione (un supertrend), stessa logica gia'
applicata a Hull Suite oggi.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import backtest as bt

ATR_LEN = 10
FACTOR = 3.0
TRAIN_PERIOD = 100
LOOKBACK_ER = {"4h": 1000, "1h": 4000}
THR_ER = 0.045
MAX_HOLD = 200


def kmeans3(window, centroids, max_iter=30, tol=1e-9):
    a, b, c = centroids
    hv = mv = lv = None
    for _ in range(max_iter):
        hv, mv, lv = [], [], []
        for v in window:
            d1, d2, d3 = abs(v - a), abs(v - b), abs(v - c)
            m = min(d1, d2, d3)
            if d1 == m:
                hv.append(v)
            elif d2 == m:
                mv.append(v)
            else:
                lv.append(v)
        na = sum(hv) / len(hv) if hv else a
        nb = sum(mv) / len(mv) if mv else b
        nc = sum(lv) / len(lv) if lv else c
        conv = abs(na - a) < tol and abs(nb - b) < tol and abs(nc - c) < tol
        a, b, c = na, nb, nc
        if conv:
            break
    return (a, b, c)


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


def run_tf(tf):
    candles, src = bt._fetch_real("XAUUSD", tf, 110000)
    closes = [c["close"] for c in candles]
    atr = bt.atr_series(candles, ATR_LEN)
    n = len(candles)
    lb_er = LOOKBACK_ER[tf]

    centroids = None
    prevUpper = prevLower = prevST = None
    direction = 1
    dir_series = [None] * n
    for i in range(n):
        a = atr[i]
        if not a:
            continue
        if i < TRAIN_PERIOD - 1:
            continue
        window = [atr[k] for k in range(i - TRAIN_PERIOD + 1, i + 1) if atr[k]]
        if len(window) < TRAIN_PERIOD:
            continue
        if centroids is None:
            hi, lo = max(window), min(window)
            centroids = (lo + 0.75 * (hi - lo), lo + 0.5 * (hi - lo), lo + 0.25 * (hi - lo))
        centroids = kmeans3(window, centroids)
        dists = [abs(a - cv) for cv in centroids]
        assigned_atr = centroids[dists.index(min(dists))]

        hl2 = (candles[i]["high"] + candles[i]["low"]) / 2.0
        upperBand = hl2 + FACTOR * assigned_atr
        lowerBand = hl2 - FACTOR * assigned_atr
        c_prev = closes[i - 1] if i > 0 else closes[i]
        if prevLower is not None:
            lowerBand = lowerBand if (lowerBand > prevLower or c_prev < prevLower) else prevLower
        if prevUpper is not None:
            upperBand = upperBand if (upperBand < prevUpper or c_prev > prevUpper) else prevUpper

        if prevST is None:
            direction = 1
        elif prevST == prevUpper:
            direction = -1 if closes[i] > upperBand else 1
        else:
            direction = 1 if closes[i] < lowerBand else -1
        superTrend = lowerBand if direction == -1 else upperBand

        dir_series[i] = direction
        prevUpper, prevLower, prevST = upperBand, lowerBand, superTrend

    trades = []
    dir_prev = None
    for i in range(max(TRAIN_PERIOD + 5, lb_er + 50), n - 2):
        d = dir_series[i]
        if d is None:
            continue
        if dir_prev is None:
            dir_prev = d
            continue
        if d == dir_prev:
            continue
        # crossunder(dir,0): 1->-1 = bullish; crossover(dir,0): -1->1 = bearish
        sig = 1 if (dir_prev == 1 and d == -1) else (-1 if (dir_prev == -1 and d == 1) else 0)
        dir_prev = d
        if sig == 0:
            continue
        e = efficiency_ratio(closes, i, lb_er)
        if e is None or e < THR_ER:
            continue
        a = atr[i]
        if not a:
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

    print(f"--- ML Adaptive SuperTrend (f={FACTOR}, atr={ATR_LEN}, kmeans train={TRAIN_PERIOD}), TF={tf}: {len(trades)} trade grezzi ---", flush=True)
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


def main():
    for tf in ("4h", "1h"):
        run_tf(tf)


if __name__ == "__main__":
    main()
