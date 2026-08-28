#!/usr/bin/env python3
"""
24/08 (18) - ottimizzazione individuale di LIQ_SWEEP (bassa correlazione
con tutto il resto - 0.084 media, vedi [[NEXUS EA - Correlazione tra le
20 Strategie (24-08)]] - ma la peggiore nel portafoglio a 20 per
crowding-out dei pochi slot). Oggi era gia' doppiamente confermata
(SL1.5/TP6.0 fisso E trailing 3.0xATR, entrambi PF1.07) ma mai provata
con: (1) lo stop nativo dello sweep (_sweep_ext_at, la stessa famiglia
usata per TURTLE_SOUP/CISD_TRUE - MAI applicata a LIQ_SWEEP oggi
nonostante sia anch'essa un segnale di sweep), (2) l'allineamento D1
(ha salvato FVG_MIT ieri sera), (3) lo split BUY/SELL con diagnosi
per-data (non per-conteggio, lezione di oggi).
"""
import sys, os, bisect
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import backtest as bt

THR_ER = 0.045
FLOOR_PCTL = 0.3
MAX_HOLD = 200
SWEEP_BUFFER_ATR = 0.5


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


# ---------- 1: stop nativo dello sweep ----------
def gen_native_sweep_stop(tf):
    candles, src = bt._fetch_real("XAUUSD", tf, 110000)
    ind = bt._prep(candles)
    atr, closes = ind["atr"], ind["close"]
    n = len(candles)
    lb_er = 1000 if tf == "4h" else 4000
    sig_fn = bt.STRATEGIES["LIQ_SWEEP"]
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
        sw = bt._sweep_ext_at(candles, ind, i)
        if not sw:
            continue
        entry = candles[i + 1]["open"]
        if sig == 1:
            if sw["refLow"] is None:
                continue
            sl = sw["refLow"] - SWEEP_BUFFER_ATR * a
        else:
            if sw["refHigh"] is None:
                continue
            sl = sw["refHigh"] + SWEEP_BUFFER_ATR * a
        rd = abs(entry - sl)
        floor_dist = 0.3 * a
        if rd < floor_dist:
            rd = floor_dist
        if rd <= 0:
            continue
        tp = entry + sig * 4.0 * a
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
        out.append({"entry": entry, "risk_dist": rd, "raw_r": exit_r})
    return out


# ---------- 2: allineamento D1 al posto di ER ----------
def gen_d1_aligned():
    candles, src = bt._fetch_real("XAUUSD", "4h", 110000)
    ind = bt._prep(candles)
    atr = ind["atr"]
    n = len(candles)
    sig_fn = bt.STRATEGIES["LIQ_SWEEP"]
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
        sl = entry - sig * 1.5 * a
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


# ---------- 3: split BUY/SELL con diagnosi per-data ----------
def gen_generic_with_dir(tf, sl_mult, tp_mult):
    candles, src = bt._fetch_real("XAUUSD", tf, 110000)
    ind = bt._prep(candles)
    atr, closes = ind["atr"], ind["close"]
    n = len(candles)
    lb_er = 1000 if tf == "4h" else 4000
    sig_fn = bt.STRATEGIES["LIQ_SWEEP"]
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
        out.append({"entry": entry, "risk_dist": rd, "raw_r": exit_r, "dir": sig,
                     "time": candles[i + 1]["time"]})
    return out


def main():
    print("=== 1. Stop nativo dello sweep (target 4.0xATR) ===", flush=True)
    for tf in ("4h", "1h"):
        report(f"LIQ_SWEEP native-sweep-stop {tf}", gen_native_sweep_stop(tf))

    print("\n=== 2. Allineamento D1 (sostituisce ER) ===", flush=True)
    report("LIQ_SWEEP D1-aligned, 4h", gen_d1_aligned())

    print("\n=== 3. Split BUY/SELL con date (SL1.5/TP6.0, 4h) ===", flush=True)
    trades = gen_generic_with_dir("4h", 1.5, 6.0)
    buys = [t for t in trades if t["dir"] == 1]
    sells = [t for t in trades if t["dir"] == -1]
    for label, group in (("BUY", buys), ("SELL", sells)):
        print(f"  {label} n={len(group)}", flush=True)
        if len(group) < 15:
            continue
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


if __name__ == "__main__":
    main()
