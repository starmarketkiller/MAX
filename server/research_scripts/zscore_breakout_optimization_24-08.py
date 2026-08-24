#!/usr/bin/env python3
"""
24/08 (28) - ottimizzazione individuale Z_SCORE_BREAKOUT, una delle
sole 2 strategie gia' portate in MQL5 (vedi NXS_Strat_ZScoreBreakout in
NXS_Strategies.mqh) - un miglioramento qui ha valore diretto, non solo
di ricerca. Config attuale: H1, stop strutturale M5 (12 candele),
target 4.0xATR fisso, ER+floor0.3. Tre ingredienti mai provati: trailing
al posto del target fisso, soglia z-score diversa (2.0 e' il default
del backtest originale, mai riottimizzata), BUY/SELL split.
"""
import sys, os, json, bisect
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import backtest as bt

THR_ER = 0.045
FLOOR_PCTL = 0.3
LOOKBACK_ER = 4000
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


_CACHE = {}


def get_data():
    if "h1" not in _CACHE:
        candles, src = bt._fetch_real("XAUUSD", "1h", 110000)
        ind = bt._prep(candles)
        with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..",
                                "data_cache_m5", "dukascopy_xauusd_m5.json"), encoding="utf-8") as f:
            m5_data = json.load(f)
        m5_times = [c["time"] for c in m5_data]
        _CACHE["h1"] = (candles, ind, m5_data, m5_times)
    return _CACHE["h1"]


def z_signal(candles, closes, i, n=20, z_thr=2.0, htf_period=200):
    if i < max(n, htf_period) + 1:
        return 0
    seg = closes[i - n + 1:i + 1]
    mean = sum(seg) / n
    var = sum((x - mean) ** 2 for x in seg) / n
    std = var ** 0.5
    if std <= 0:
        return 0
    z = (closes[i] - mean) / std
    htf_seg = closes[i - htf_period + 1:i + 1]
    htf_sma = sum(htf_seg) / htf_period
    bull = closes[i] > htf_sma
    bear = closes[i] < htf_sma
    if bull and z > z_thr:
        return 1
    if bear and z < -z_thr:
        return -1
    return 0


def m5_stop(m5_data, m5_times, sig, entry_time):
    j_entry = bisect.bisect_left(m5_times, entry_time)
    window = m5_data[max(0, j_entry - 12):j_entry]
    if len(window) < 3:
        return None
    return min(w["low"] for w in window) if sig == 1 else max(w["high"] for w in window)


def collect(z_thr, trail_mult=None, tp_mult=4.0, buy_only=False):
    candles, ind, m5_data, m5_times = get_data()
    atr, closes = ind["atr"], ind["close"]
    n = len(candles)
    atr_hist, out = [], []
    for i in range(max(300, LOOKBACK_ER + 50), n - 2):
        a = atr[i]
        if a:
            atr_hist.append(a)
        sig = z_signal(candles, closes, i, z_thr=z_thr)
        if sig == 0 or not a:
            continue
        if buy_only and sig != 1:
            continue
        e = efficiency_ratio(closes, i, LOOKBACK_ER)
        if e is None or e < THR_ER or len(atr_hist) < 500:
            continue
        w = sorted(atr_hist[-2000:])
        floor = w[min(int(FLOOR_PCTL * len(w)), len(w) - 1)]
        if a < floor:
            continue
        entry_time = candles[i + 1]["time"]
        entry = candles[i + 1]["open"]
        stop = m5_stop(m5_data, m5_times, sig, entry_time)
        if stop is None:
            continue
        rd = abs(entry - stop)
        floor_dist = 0.3 * a
        if rd < floor_dist:
            rd = floor_dist
        if rd <= 0:
            continue
        if trail_mult is None:
            tp = entry + sig * tp_mult * a
            exit_r = None
            for j in range(i + 2, min(i + 2 + MAX_HOLD, n)):
                hi, lo = candles[j]["high"], candles[j]["low"]
                if sig == 1:
                    if lo <= entry - rd: exit_r = -1.0; break
                    elif hi >= tp: exit_r = (tp - entry) / rd; break
                else:
                    if hi >= entry + rd: exit_r = -1.0; break
                    elif lo <= tp: exit_r = (entry - tp) / rd; break
            if exit_r is None:
                continue
        else:
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
        out.append({"entry": entry, "risk_dist": rd, "raw_r": exit_r, "dir": sig})
    return out


def main():
    print("=== Baseline nota (z_thr=2.0, target 4.0xATR fisso) ===", flush=True)
    base = collect(2.0)
    print(fmt("Z_SCORE_BREAKOUT baseline", "1h", len(base), summarize(base)), flush=True)

    print("\n=== Soglia z-score diversa ===", flush=True)
    for z_thr in (1.5, 1.75, 2.25, 2.5):
        trades = collect(z_thr)
        print(fmt(f"z_thr={z_thr}", "1h", len(trades), summarize(trades)), flush=True)

    print("\n=== Trailing invece di target fisso ===", flush=True)
    for trail_mult in (2.0, 2.5, 3.0):
        trades = collect(2.0, trail_mult=trail_mult)
        print(fmt(f"trailing {trail_mult}xATR", "1h", len(trades), summarize(trades)), flush=True)

    print("\n=== Split BUY/SELL ===", flush=True)
    buys = [t for t in base if t["dir"] == 1]
    sells = [t for t in base if t["dir"] == -1]
    for label, group in (("BUY", buys), ("SELL", sells)):
        if len(group) < 25:
            print(f"  {label}: n={len(group)} troppo pochi", flush=True)
            continue
        print(fmt(f"Z_SCORE_BREAKOUT [{label}]", "1h", len(group), summarize(group)), flush=True)


if __name__ == "__main__":
    main()
