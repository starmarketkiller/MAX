#!/usr/bin/env python3
"""
24/08 (29) - ottimizzazione individuale MALAYSIAN_SNR_BREAKOUT (la piu'
forte del blocco "altre solide", BUY-only PF1.93). Verifica laterale
gia' fatta (n=6, PF0.45 - stessa direzione delle altre, campione troppo
sottile per confermare, stesso caveat generale). Due ingredienti mai
provati: trailing, allineamento D1.
"""
import sys, os, bisect
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import backtest as bt

THR_ER = 0.045
FLOOR_PCTL = 0.3
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


def collect(sl_mult, tp_mult, buy_only=False, trail_mult=None):
    candles, src = bt._fetch_real("XAUUSD", "4h", 110000)
    ind = bt._prep(candles)
    atr, closes = ind["atr"], ind["close"]
    n = len(candles)
    sig_fn = bt.STRATEGIES["MALAYSIAN_SNR_BREAKOUT"]
    atr_hist, out = [], []
    for i in range(max(1500, 1050), n - 2):
        a = atr[i]
        if a:
            atr_hist.append(a)
        sig = sig_fn(candles, ind, i)
        if sig == 0 or not a:
            continue
        if buy_only and sig != 1:
            continue
        e = efficiency_ratio(closes, i, 1000)
        if e is None or e < THR_ER or len(atr_hist) < 500:
            continue
        w = sorted(atr_hist[-2000:])
        floor = w[min(int(FLOOR_PCTL * len(w)), len(w) - 1)]
        if a < floor:
            continue
        entry = candles[i + 1]["open"]
        if trail_mult is None:
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
        else:
            rd = sl_mult * a
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


def collect_d1_aligned(sl_mult, tp_mult):
    candles, src = bt._fetch_real("XAUUSD", "4h", 110000)
    ind = bt._prep(candles)
    atr = ind["atr"]
    n = len(candles)
    sig_fn = bt.STRATEGIES["MALAYSIAN_SNR_BREAKOUT"]
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
        sl = entry - sig * sl_mult * a
        tp = entry + sig * tp_mult * a
        rd = abs(entry - sl)
        if rd <= 0:
            continue
        exit_r = None
        for k in range(i + 2, min(i + 2 + MAX_HOLD, n)):
            hi, lo = candles[k]["high"], candles[k]["low"]
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


def main():
    print("=== BUY-only baseline (nota) ===", flush=True)
    base = collect(1.5, 4.0, buy_only=True)
    print(fmt("MALAYSIAN_SNR_BREAKOUT BUY", "4h", len(base), summarize(base)), flush=True)

    print("\n=== BUY-only + trailing ===", flush=True)
    for trail_mult in (2.0, 2.5, 3.0):
        trades = collect(1.5, None, buy_only=True, trail_mult=trail_mult)
        print(fmt(f"BUY trailing {trail_mult}xATR", "4h", len(trades), summarize(trades)), flush=True)

    print("\n=== D1-align (simmetrica, sostituisce ER) ===", flush=True)
    trades = collect_d1_aligned(1.5, 4.0)
    print(fmt("D1-align simmetrica", "4h", len(trades), summarize(trades)), flush=True)


if __name__ == "__main__":
    main()
