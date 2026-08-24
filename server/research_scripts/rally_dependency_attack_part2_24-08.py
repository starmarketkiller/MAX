#!/usr/bin/env python3
"""
24/08 (6) - seguito diretto di rally_dependency_attack_24-08.py: il
floor di volatilita' assoluta (percentile ATR mobile, ortogonale al
filtro ER di forma) ha corretto sostanzialmente la dipendenza dal rally
su SAR/MACD/FVG_CONT ma NON su LONDON_BO (verificato, non assunto).
Qui: stessa verifica sui 4 candidati trovati oggi PRIMA di questo
attacco, che mostravano tutti la stessa firma "prima meta' debole,
seconda forte" - Hull Suite, ML Adaptive SuperTrend, Z_SCORE_BREAKOUT,
SWING_FALSEBREAK. Ognuno riusa la propria logica di segnale/uscita gia'
validata oggi (nessuna riscrittura), solo il gate di ingresso guadagna
il floor ATR in piu', stesso principio - "verificare non assumere" per
ciascuna.
"""
import sys, os, json, bisect
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import backtest as bt
import importlib.util

HERE = os.path.dirname(os.path.abspath(__file__))


def _load(modname, filename):
    spec = importlib.util.spec_from_file_location(modname, os.path.join(HERE, filename))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


hs = _load("hs24", "hull_suite_sweep_24-08.py")
mst = _load("mst24", "ml_adaptive_supertrend_sweep_24-08.py")

LOOKBACK_ER = {"4h": 1000, "1h": 4000}
THR_ER = 0.045


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


def atr_pctl_floor(atr_hist, pctl):
    if len(atr_hist) < 500:
        return None
    w = sorted(atr_hist[-2000:])
    return w[min(int(pctl * len(w)), len(w) - 1)]


# ---------- 1. Hull Suite (length=25, Hma, 4h) ----------
def run_hull(floor_pctl):
    candles, atr, closes = hs.get_candles("4h")
    hull = hs.hma_series(closes, 25, "Hma")
    n = len(candles)
    lb_er = LOOKBACK_ER["4h"]
    atr_hist, trades = [], []
    up_prev = None
    for i in range(max(25 + 10, lb_er + 50), n - 2):
        a = atr[i]
        if a:
            atr_hist.append(a)
        if hull[i] is None or hull[i - 2] is None:
            continue
        up = hull[i] > hull[i - 2]
        if up_prev is None:
            up_prev = up
            continue
        if up == up_prev:
            continue
        sig = 1 if up else -1
        up_prev = up
        e = hs.efficiency_ratio(closes, i, lb_er)
        if e is None or e < THR_ER or not a:
            continue
        if floor_pctl is not None:
            floor = atr_pctl_floor(atr_hist, floor_pctl)
            if floor is None or a < floor:
                continue
        entry = candles[i + 1]["open"]
        sl = entry - sig * 1.5 * a
        tp = entry + sig * 4.0 * a
        rd = abs(entry - sl)
        if rd <= 0:
            continue
        exit_r = None
        for j in range(i + 2, min(i + 2 + hs.MAX_HOLD, n)):
            hi, lo = candles[j]["high"], candles[j]["low"]
            if sig == 1:
                if lo <= sl: exit_r = (sl - entry) / rd; break
                elif hi >= tp: exit_r = (tp - entry) / rd; break
            else:
                if hi >= sl: exit_r = (entry - sl) / rd; break
                elif lo <= tp: exit_r = (entry - tp) / rd; break
        if exit_r is None:
            continue
        trades.append({"entry": entry, "risk_dist": rd, "raw_r": exit_r})
    return trades


# ---------- 2. ML Adaptive SuperTrend (factor=1.5, 4h) ----------
def run_mlst(floor_pctl):
    candles, atr, closes, assigned = mst.get_dir_series("4h")
    dir_series = mst.supertrend_dir(candles, closes, assigned, 1.5)
    n = len(candles)
    lb_er = LOOKBACK_ER["4h"]
    atr_hist, trades = [], []
    dir_prev = None
    for i in range(max(mst.TRAIN_PERIOD + 5, lb_er + 50), n - 2):
        a = atr[i]
        if a:
            atr_hist.append(a)
        d = dir_series[i]
        if d is None:
            continue
        if dir_prev is None:
            dir_prev = d
            continue
        if d == dir_prev:
            continue
        sig = 1 if (dir_prev == 1 and d == -1) else (-1 if (dir_prev == -1 and d == 1) else 0)
        dir_prev = d
        if sig == 0:
            continue
        e = mst.efficiency_ratio(closes, i, lb_er)
        if e is None or e < THR_ER or not a:
            continue
        if floor_pctl is not None:
            floor = atr_pctl_floor(atr_hist, floor_pctl)
            if floor is None or a < floor:
                continue
        entry = candles[i + 1]["open"]
        sl = entry - sig * 1.5 * a
        tp = entry + sig * 4.0 * a
        rd = abs(entry - sl)
        if rd <= 0:
            continue
        exit_r = None
        for j in range(i + 2, min(i + 2 + mst.MAX_HOLD, n)):
            hi, lo = candles[j]["high"], candles[j]["low"]
            if sig == 1:
                if lo <= sl: exit_r = (sl - entry) / rd; break
                elif hi >= tp: exit_r = (tp - entry) / rd; break
            else:
                if hi >= sl: exit_r = (entry - sl) / rd; break
                elif lo <= tp: exit_r = (entry - tp) / rd; break
        if exit_r is None:
            continue
        trades.append({"entry": entry, "risk_dist": rd, "raw_r": exit_r})
    return trades


# ---------- 3. Z_SCORE_BREAKOUT (H1, stop strutturale M5 - stessa logica del 17/08) ----------
def run_zsb(floor_pctl):
    candles, src = bt._fetch_real("XAUUSD", "1h", 110000)
    ind = bt._prep(candles)
    atr, closes = ind["atr"], ind["close"]
    n = len(candles)
    lb_er = LOOKBACK_ER["1h"]
    sig_fn = bt.STRATEGIES["Z_SCORE_BREAKOUT"]

    with open(os.path.join(HERE, "..", "data_cache_m5", "dukascopy_xauusd_m5.json"), encoding="utf-8") as f:
        m5_data = json.load(f)
    m5_times = [c["time"] for c in m5_data]

    def m5_stop(sig, entry_time):
        j_entry = bisect.bisect_left(m5_times, entry_time)
        window = m5_data[max(0, j_entry - 12):j_entry]
        if len(window) < 3:
            return None
        return min(w["low"] for w in window) if sig == 1 else max(w["high"] for w in window)

    atr_hist, trades = [], []
    for i in range(max(1500, lb_er + 50), n - 2):
        a = atr[i]
        if a:
            atr_hist.append(a)
        sig = sig_fn(candles, ind, i)
        if sig == 0 or not a:
            continue
        # efficiency_ratio locale (stessa formula di tutti gli script di oggi)
        if i < lb_er:
            continue
        net = abs(closes[i] - closes[i - lb_er])
        tot = sum(abs(closes[k] - closes[k - 1]) for k in range(i - lb_er + 1, i + 1))
        e = net / tot if tot > 0 else None
        if e is None or e < THR_ER:
            continue
        if floor_pctl is not None:
            floor = atr_pctl_floor(atr_hist, floor_pctl)
            if floor is None or a < floor:
                continue
        entry_time = candles[i + 1]["time"]
        entry = candles[i + 1]["open"]
        stop = m5_stop(sig, entry_time)
        if stop is None:
            continue
        rd = abs(entry - stop)
        floor_dist = 0.3 * a
        if rd < floor_dist:
            rd = floor_dist
        if rd <= 0:
            continue
        tp = entry + sig * 4.0 * a
        exit_r = None
        for j in range(i + 2, min(i + 2 + 200, n)):
            hi, lo = candles[j]["high"], candles[j]["low"]
            if sig == 1:
                if lo <= entry - rd: exit_r = -1.0; break
                elif hi >= tp: exit_r = (tp - entry) / rd; break
            else:
                if hi >= entry + rd: exit_r = -1.0; break
                elif lo <= tp: exit_r = (entry - tp) / rd; break
        if exit_r is None:
            continue
        trades.append({"entry": entry, "risk_dist": rd, "raw_r": exit_r})
    return trades


# ---------- 4. SWING_FALSEBREAK (1h, pivot swing maggiore) ----------
LEFT, RIGHT = 20, 15


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


def run_sfb(floor_pctl):
    candles, src = bt._fetch_real("XAUUSD", "1h", 110000)
    atr = bt.atr_series(candles, 14)
    closes = [c["close"] for c in candles]
    n = len(candles)
    piv_high, piv_low = find_pivots(candles)
    lb_er = LOOKBACK_ER["1h"]

    atr_hist, trades = [], []
    for i in range(max(LEFT + RIGHT + 5, lb_er + 50), n - 2):
        a = atr[i]
        if a:
            atr_hist.append(a)
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
        net = abs(closes[i] - closes[i - lb_er]) if i >= lb_er else None
        if net is None:
            continue
        tot = sum(abs(closes[k] - closes[k - 1]) for k in range(i - lb_er + 1, i + 1))
        e = net / tot if tot > 0 else None
        if e is None or e < THR_ER:
            continue
        if floor_pctl is not None:
            floor = atr_pctl_floor(atr_hist, floor_pctl)
            if floor is None or a < floor:
                continue
        entry = candles[i + 1]["open"]
        sl = entry - sig * 1.5 * a
        tp = entry + sig * 4.0 * a
        rd = abs(entry - sl)
        if rd <= 0:
            continue
        exit_r = None
        for j in range(i + 2, min(i + 2 + 200, n)):
            hi, lo = candles[j]["high"], candles[j]["low"]
            if sig == 1:
                if lo <= sl: exit_r = (sl - entry) / rd; break
                elif hi >= tp: exit_r = (tp - entry) / rd; break
            else:
                if hi >= sl: exit_r = (entry - sl) / rd; break
                elif lo <= tp: exit_r = (entry - tp) / rd; break
        if exit_r is None:
            continue
        trades.append({"entry": entry, "risk_dist": rd, "raw_r": exit_r})
    return trades


def main():
    print("=== Hull Suite length=25/Hma/4h ===", flush=True)
    report("Hull Suite senza floor", run_hull(None))
    for fp in (0.3, 0.4):
        report(f"Hull Suite floor={fp}", run_hull(fp))

    print("\n=== ML Adaptive SuperTrend factor=1.5/4h ===", flush=True)
    report("ML SuperTrend senza floor", run_mlst(None))
    for fp in (0.3, 0.4):
        report(f"ML SuperTrend floor={fp}", run_mlst(fp))

    print("\n=== Z_SCORE_BREAKOUT 1h (stop M5 strutturale) ===", flush=True)
    report("Z_SCORE_BREAKOUT senza floor", run_zsb(None))
    for fp in (0.3, 0.4):
        report(f"Z_SCORE_BREAKOUT floor={fp}", run_zsb(fp))

    print("\n=== SWING_FALSEBREAK 1h ===", flush=True)
    report("SWING_FALSEBREAK senza floor", run_sfb(None))
    for fp in (0.3, 0.4):
        report(f"SWING_FALSEBREAK floor={fp}", run_sfb(fp))


if __name__ == "__main__":
    main()
