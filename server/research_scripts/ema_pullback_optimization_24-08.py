#!/usr/bin/env python3
"""
24/08 (26) - ottimizzazione individuale EMA_PULLBACK. Tensione da
risolvere: versione D1 (SL1.5/TP6.0, ER+floor0.2) PF2.53 ma n=32 -
troppo pochi per fidarsene fino in fondo; versione 4h+D1-align PF1.42
ma n=241, piu' solida numericamente. Tre tentativi per allargare il
campione D1 senza perdere troppa qualita', poi trailing sulla versione
4h (mai provato).
"""
import sys, os, bisect
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import backtest as bt

THR_ER = 0.045
MAX_HOLD = 200


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
    return [(len(rs[w * size:(w + 1) * size] if w < nw - 1 else rs[w * size:]),
              pf(rs[w * size:(w + 1) * size] if w < nw - 1 else rs[w * size:]))
            for w in range(nw)]


def summarize(trades):
    out = {}
    for preset in ("retail_standard", "ecn"):
        net = []
        for t in trades:
            cost = bt.scaled_cost_for_price(preset, t["entry"])
            cost_r = min((cost["spread_price"] + cost["slippage_price"]) / t["risk_dist"], bt.MAX_COST_R_PER_TRADE)
            net.append(t["raw_r"] - cost_r)
        wf = walk_forward(net)
        n_pos = sum(1 for _, p in (wf or []) if p >= 1.0)
        mid = len(net) // 2
        h1, h2 = net[:mid], net[mid:]
        out[preset] = {"pf": pf(net), "sumR": sum(net), "win": n_pos, "nw": len(wf) if wf else 0,
                        "m1": pf(h1), "m2": pf(h2)}
    return out


def fmt(name, tag, n, s):
    r, e = s["retail_standard"], s["ecn"]
    return (f"{name:34s} [{tag}] n={n:4d}  "
            f"retail PF={r['pf']:.2f}(m1={r['m1']:.2f}/m2={r['m2']:.2f}) win{r['win']}/{r['nw']}  "
            f"ECN PF={e['pf']:.2f}(m1={e['m1']:.2f}/m2={e['m2']:.2f}) win{e['win']}/{e['nw']}")


def collect_d1(sl_mult, tp_mult, floor_pctl):
    candles, src = bt._fetch_real("XAUUSD", "1d", 4000)
    ind = bt._prep(candles)
    atr, closes = ind["atr"], ind["close"]
    n = len(candles)
    sig_fn = bt.STRATEGIES["EMA_PULLBACK"]
    atr_hist, out = [], []
    for i in range(max(300, 170), n - 2):
        a = atr[i]
        if a:
            atr_hist.append(a)
        sig = sig_fn(candles, ind, i)
        if sig == 0 or not a:
            continue
        e = efficiency_ratio(closes, i, 120)
        if e is None or e < THR_ER or len(atr_hist) < 100:
            continue
        if floor_pctl is not None:
            w = sorted(atr_hist[-500:])
            floor = w[min(int(floor_pctl * len(w)), len(w) - 1)]
            if a < floor:
                continue
        entry = candles[i + 1]["open"]
        sl = entry - sig * sl_mult * a
        tp = entry + sig * tp_mult * a
        rd = abs(entry - sl)
        if rd <= 0:
            continue
        exit_r = None
        for j in range(i + 2, min(i + 2 + MAX_HOLD, n)):
            hi, lo = candles[j]["high"], candles[j]["low"]
            if sig == 1:
                if lo <= sl: exit_r = (sl - entry) / rd; break
                elif hi >= tp: exit_r = (tp - entry) / rd; break
            else:
                if hi >= sl: exit_r = (entry - sl) / rd; break
                elif lo <= tp: exit_r = (entry - tp) / rd; break
        if exit_r is None:
            continue
        out.append({"entry": entry, "risk_dist": rd, "raw_r": exit_r})
    return out


def collect_4h_trailing(trail_mult, init_sl_mult):
    candles, src = bt._fetch_real("XAUUSD", "4h", 110000)
    ind = bt._prep(candles)
    atr = ind["atr"]
    n = len(candles)
    sig_fn = bt.STRATEGIES["EMA_PULLBACK"]
    d1, _ = bt._fetch_real("XAUUSD", "1d", 4000)
    d1_times = [c["time"] for c in d1]
    d1_close = [c["close"] for c in d1]
    d1_ema50 = bt.ema_series(d1_close, 50)
    out = []
    for i in range(max(1500, 250), n - 2):
        a = atr[i]
        if not a:
            continue
        sig = sig_fn(candles, ind, i)
        if sig == 0:
            continue
        t = candles[i]["time"]
        j_d1 = bisect.bisect_right(d1_times, t) - 1
        if j_d1 < 60 or not d1_ema50[j_d1]:
            continue
        d1_up = d1_close[j_d1] > d1_ema50[j_d1]
        if sig == 1 and not d1_up:
            continue
        if sig == -1 and d1_up:
            continue
        entry = candles[i + 1]["open"]
        rd = init_sl_mult * a
        sl = entry - sig * rd
        extreme = entry
        exit_r = None
        for j in range(i + 2, min(i + 2 + MAX_HOLD, n)):
            hi, lo = candles[j]["high"], candles[j]["low"]
            if sig == 1:
                if lo <= sl: exit_r = (sl - entry) / rd; break
                extreme = max(extreme, hi)
                ns = extreme - trail_mult * a
                if ns > sl: sl = ns
            else:
                if hi >= sl: exit_r = (entry - sl) / rd; break
                extreme = min(extreme, lo)
                ns = extreme + trail_mult * a
                if ns < sl: sl = ns
        if exit_r is None:
            j_last = min(i + 1 + MAX_HOLD, n - 1)
            lc = candles[j_last]["close"]
            exit_r = (lc - entry) / rd if sig == 1 else (entry - lc) / rd
        out.append({"entry": entry, "risk_dist": rd, "raw_r": exit_r})
    return out


def main():
    print("=== D1: allargare il campione (floor piu' basso / assente) ===", flush=True)
    for floor_pctl, label in [(0.2, "floor0.2 (nota)"), (0.1, "floor0.1"), (0.0, "floor0.0"), (None, "no floor")]:
        trades = collect_d1(1.5, 6.0, floor_pctl)
        if len(trades) < 15:
            print(f"  {label}: n={len(trades)} troppo pochi", flush=True)
            continue
        s = summarize(trades)
        print(fmt(f"EMA_PULLBACK D1 {label}", "1d", len(trades), s), flush=True)

    print("\n=== 4h+D1-align: trailing invece di target fisso ===", flush=True)
    for trail_mult in (2.0, 2.5, 3.0):
        trades = collect_4h_trailing(trail_mult, 1.5)
        s = summarize(trades)
        print(fmt(f"EMA_PULLBACK 4h trailing {trail_mult}xATR", "4h", len(trades), s), flush=True)


if __name__ == "__main__":
    main()
