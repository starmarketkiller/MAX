#!/usr/bin/env python3
"""
24/08 (27) - ottimizzazione individuale FVG_MIT (diversificatrice quasi
indipendente, correlazione media 0.015 - vedi [[NEXUS EA - Correlazione
tra le 20 Strategie (24-08)]]). Config nota: 4h, SL2.0/TP6.0,
allineamento D1 (EMA50), PF1.48 (m1=1.33/m2=1.64, 5/5 finestre, n=79).
Tre ingredienti mai provati: trailing (ha aiutato OTE_CONT/EMA_PULLBACK),
EMA D1 piu' lunga (100/200 invece di 50 - segnale di trend piu' lento,
forse piu' adatto a un ingresso di mitigation che aspetta gia' un
ritorno), floor ATR (mai provato insieme a D1-align per questa
strategia specifica).
"""
import sys, os, bisect
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import backtest as bt

MAX_HOLD = 200


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


def get_4h():
    if "4h" not in _CACHE:
        candles, src = bt._fetch_real("XAUUSD", "4h", 110000)
        ind = bt._prep(candles)
        _CACHE["4h"] = (candles, ind)
    return _CACHE["4h"]


def get_d1(ema_period):
    key = f"d1_{ema_period}"
    if key not in _CACHE:
        d1, src = bt._fetch_real("XAUUSD", "1d", 4000)
        d1_times = [c["time"] for c in d1]
        d1_close = [c["close"] for c in d1]
        d1_ema = bt.ema_series(d1_close, ema_period)
        _CACHE[key] = (d1_times, d1_close, d1_ema)
    return _CACHE[key]


def collect(sl_mult, tp_mult, ema_period, floor_pctl, trail_mult=None):
    candles, ind = get_4h()
    atr = ind["atr"]
    n = len(candles)
    sig_fn = bt.STRATEGIES["FVG_MIT"]
    d1_times, d1_close, d1_ema = get_d1(ema_period)
    atr_hist, out = [], []
    for i in range(max(1500, 250), n - 2):
        a = atr[i]
        if a:
            atr_hist.append(a)
        sig = sig_fn(candles, ind, i)
        if sig == 0 or not a:
            continue
        t = candles[i]["time"]
        j_d1 = bisect.bisect_right(d1_times, t) - 1
        if j_d1 < ema_period + 5 or not d1_ema[j_d1]:
            continue
        d1_up = d1_close[j_d1] > d1_ema[j_d1]
        if sig == 1 and not d1_up:
            continue
        if sig == -1 and d1_up:
            continue
        if floor_pctl is not None:
            if len(atr_hist) < 500:
                continue
            w = sorted(atr_hist[-2000:])
            floor = w[min(int(floor_pctl * len(w)), len(w) - 1)]
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


def main():
    print("=== Baseline nota (EMA50 D1, SL2.0/TP6.0, no floor) ===", flush=True)
    base = collect(2.0, 6.0, 50, None)
    print(fmt("FVG_MIT baseline", "4h", len(base), summarize(base)), flush=True)

    print("\n=== EMA D1 piu' lenta (100/200) ===", flush=True)
    for ema_p in (100, 200):
        trades = collect(2.0, 6.0, ema_p, None)
        print(fmt(f"FVG_MIT EMA{ema_p} D1", "4h", len(trades), summarize(trades)), flush=True)

    print("\n=== + floor ATR (mai provato insieme a D1-align qui) ===", flush=True)
    for floor_pctl in (0.2, 0.3):
        trades = collect(2.0, 6.0, 50, floor_pctl)
        print(fmt(f"FVG_MIT EMA50 D1 + floor{floor_pctl}", "4h", len(trades), summarize(trades)), flush=True)

    print("\n=== Trailing invece di target fisso ===", flush=True)
    for trail_mult in (2.0, 2.5, 3.0):
        trades = collect(2.0, None, 50, None, trail_mult=trail_mult)
        print(fmt(f"FVG_MIT trailing {trail_mult}xATR", "4h", len(trades), summarize(trades)), flush=True)


if __name__ == "__main__":
    main()
