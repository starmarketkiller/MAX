#!/usr/bin/env python3
"""
24/08 (19) - terza ottimizzazione individuale. OTE_CONT (diversificatrice
genuina, correlazione media 0.028 - vedi [[NEXUS EA - Correlazione tra le
20 Strategie (24-08)]]), gia' solida (SL1.0/TP6.0, retail PF1.61,
m1=1.69/m2=1.52) ma respinta su D1 (morta pre-2024, vedi diagnosi di
ieri sera). Tre ingredienti mai provati: split BUY/SELL con date,
allineamento D1 (sostituisce ER), trailing stop.
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


def gen_generic(sl_mult, tp_mult, trail_mult=None):
    candles, src = bt._fetch_real("XAUUSD", "4h", 110000)
    ind = bt._prep(candles)
    atr, closes = ind["atr"], ind["close"]
    n = len(candles)
    lb_er = 1000
    sig_fn = bt.STRATEGIES["OTE_CONT"]
    atr_hist, out = [], []
    for i in range(max(1500, lb_er + 50), n - 2):
        a = atr[i]
        if a:
            atr_hist.append(a)
        sig = sig_fn(candles, ind, i)
        if sig == 0 or not a:
            continue
        e = efficiency_ratio(closes, i, lb_er)
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
        out.append({"entry": entry, "risk_dist": rd, "raw_r": exit_r, "dir": sig,
                     "time": candles[i + 1]["time"]})
    return out


def gen_d1_aligned():
    candles, src = bt._fetch_real("XAUUSD", "4h", 110000)
    ind = bt._prep(candles)
    atr = ind["atr"]
    n = len(candles)
    sig_fn = bt.STRATEGIES["OTE_CONT"]
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
        sl = entry - sig * 1.0 * a
        tp = entry + sig * 6.0 * a
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
    print("=== 1. Baseline nota (SL1.0/TP6.0) ===", flush=True)
    base = gen_generic(1.0, 6.0)
    report("OTE_CONT baseline", base)

    print("\n=== 2. Split BUY/SELL con date ===", flush=True)
    buys = [t for t in base if t["dir"] == 1]
    sells = [t for t in base if t["dir"] == -1]
    for label, group in (("BUY", buys), ("SELL", sells)):
        print(f"  {label} n={len(group)}", flush=True)
        if len(group) < 15:
            continue
        report(f"  OTE_CONT {label}-only", group)
        nw = 5
        size = len(group) // nw
        for w in range(nw):
            seg = group[w * size:(w + 1) * size] if w < nw - 1 else group[w * size:]
            net = []
            for t in seg:
                cost = bt.scaled_cost_for_price("retail_standard", t["entry"])
                cost_r = min((cost["spread_price"] + cost["slippage_price"]) / t["risk_dist"], bt.MAX_COST_R_PER_TRADE)
                net.append(t["raw_r"] - cost_r)
            print(f"    F{w}: {seg[0]['time']} -> {seg[-1]['time']}  n={len(seg):4d}  PF={pf(net):.2f}", flush=True)

    print("\n=== 3. Allineamento D1 (sostituisce ER) ===", flush=True)
    report("OTE_CONT D1-aligned", gen_d1_aligned())

    print("\n=== 4. Trailing (invece di target fisso) ===", flush=True)
    for tm in (2.0, 2.5, 3.0):
        report(f"OTE_CONT trailing {tm}xATR", gen_generic(1.0, None, trail_mult=tm))


if __name__ == "__main__":
    main()
