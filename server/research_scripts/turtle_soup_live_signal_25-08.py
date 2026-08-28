#!/usr/bin/env python3
"""
25/08 - prima ricerca da zero (non porting) sul vero segnale LIVE di
TURTLE_SOUP (NXS_Strat_TurtleSoup in NXS_Strategies_SMC.mqh) - scoperto
oggi che e' un pattern COMPLETAMENTE DIVERSO da bt.STRATEGIES['TURTLE_SOUP']
(quello e' un altro pattern che condivide solo il nome). Il vero live:
sweep di PDH/PDL o EQH/EQL (livelli uguali, swing wing=3, tolleranza
0.2xATR) + candela di rientro con corpo forte (>=0.4xATR) + chiusura
oltre il livello sweepato, stop nativo = livello +/- 0.5xATR, target
RR fisso 2.0. TF live = H1.

Fedele a NXS_MarketAnalysis.mqh: NXS_DetectSweepExt() (PDH/PDL da D1
shift1, EQH/EQL da swing-point clustering) + NXS_Strat_TurtleSoup().
Semplificazione dichiarata: ignora Asia/weekly/monthly (TURTLE_SOUP
controlla solo sweptPDH/sweptEQH e sweptPDL/sweptEQL, gli altri
livelli hanno priorita' piu' alta nel refHigh/refLow SOLO se sweepano
sulla STESSA barra - caso raro, non modellato).
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import backtest as bt

MAX_HOLD = 400
SWING_WING = 3


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


def net_series(trades, preset="retail_standard"):
    out = []
    for t in trades:
        cost = bt.scaled_cost_for_price(preset, t["entry"])
        cost_r = min((cost["spread_price"] + cost["slippage_price"]) / t["risk_dist"], bt.MAX_COST_R_PER_TRADE)
        out.append(t["raw_r"] - cost_r)
    return out


def fmt(label, trades):
    net = net_series(trades)
    wf = walk_forward(net)
    mid = len(net) // 2
    n_pos = sum(1 for _, p in (wf or []) if p >= 1.0)
    return (f"{label:30s} n={len(trades):4d} PF={pf(net):.2f} "
            f"(m1={pf(net[:mid]):.2f}/m2={pf(net[mid:]):.2f}) win={n_pos}/{len(wf) if wf else 0}")


def is_swing_high(highs, i, wing):
    h = highs[i]
    if h <= 0:
        return False
    for k in range(1, wing + 1):
        if i + k < len(highs) and highs[i + k] >= h:
            return False
        if i - k >= 0 and highs[i - k] >= h:
            return False
    return True


def is_swing_low(lows, i, wing):
    l = lows[i]
    if l <= 0:
        return False
    for k in range(1, wing + 1):
        if i + k < len(lows) and lows[i + k] <= l:
            return False
        if i - k >= 0 and lows[i - k] <= l:
            return False
    return True


def find_equal_high(highs, i, wing, tol):
    """i = indice della barra 'ora' (shift1 equivalente, i.e. l'ultima barra
    chiusa) - scansiona all'indietro (shift wing+1..60 rispetto a i)."""
    swings = []
    for s in range(wing + 1, 60):
        idx = i - s
        if idx < 0 or len(swings) >= 8:
            break
        if is_swing_high(highs, idx, wing):
            swings.append(highs[idx])
    for a in range(len(swings)):
        for b in range(a + 1, len(swings)):
            if abs(swings[a] - swings[b]) <= tol:
                return max(swings[a], swings[b])
    return 0


def find_equal_low(lows, i, wing, tol):
    swings = []
    for s in range(wing + 1, 60):
        idx = i - s
        if idx < 0 or len(swings) >= 8:
            break
        if is_swing_low(lows, idx, wing):
            swings.append(lows[idx])
    for a in range(len(swings)):
        for b in range(a + 1, len(swings)):
            if abs(swings[a] - swings[b]) <= tol:
                return min(swings[a], swings[b])
    return 0


def main():
    candles, src = bt._fetch_real("XAUUSD", "1h", 110000)
    ind = bt._prep(candles)
    atr, closes = ind["atr"], ind["close"]
    highs = [c["high"] for c in candles]
    lows = [c["low"] for c in candles]
    opens = [c["open"] for c in candles]
    n = len(candles)

    candlesD1, _ = bt._fetch_real("XAUUSD", "1d", 4000)
    d1_times = [c["time"] for c in candlesD1]
    d1_high = [c["high"] for c in candlesD1]
    d1_low = [c["low"] for c in candlesD1]
    import bisect

    def pdh_pdl(t):
        j = bisect.bisect_right(d1_times, t) - 1
        if j < 1:
            return None, None
        return d1_high[j - 1], d1_low[j - 1]   # shift1 rispetto al giorno corrente = ieri

    out = []
    for i in range(120, n - 2):
        a = atr[i]
        if not a:
            continue
        h1, l1, c1, o1 = highs[i], lows[i], closes[i], opens[i]
        body = abs(c1 - o1)
        if body < a * 0.4:
            continue
        t = candles[i]["time"]
        pdh, pdl = pdh_pdl(t)
        if pdh is None:
            continue
        tol = a * 0.2
        eqH = find_equal_high(highs, i, SWING_WING, tol)
        eqL = find_equal_low(lows, i, SWING_WING, tol)

        sweptPDH = h1 > pdh and c1 < pdh
        sweptEQH = eqH > 0 and h1 > eqH and c1 < eqH
        sweptPDL = l1 < pdl and c1 > pdl
        sweptEQL = eqL > 0 and l1 < eqL and c1 > eqL

        sig, entry_sl, entry_tp = 0, None, None
        if (sweptPDH or sweptEQH) and c1 < o1:
            refHigh = pdh if sweptPDH else eqH
            if c1 < refHigh:
                sig = -1
                entry_sl = refHigh + 0.5 * a
        if sig == 0 and (sweptPDL or sweptEQL) and c1 > o1:
            refLow = pdl if sweptPDL else eqL
            if c1 > refLow:
                sig = 1
                entry_sl = refLow - 0.5 * a
        if sig == 0:
            continue

        entry = candles[i + 1]["open"]
        sl = entry_sl
        rd = abs(entry - sl)
        if rd <= 0:
            continue
        tp = entry + sig * 2.0 * rd
        exit_r = None
        for j in range(i + 2, min(i + 2 + MAX_HOLD, n)):
            hi, lo = candles[j]["high"], candles[j]["low"]
            if sig == 1:
                if lo <= sl: exit_r = (sl - entry) / rd; break
                if hi >= tp: exit_r = (tp - entry) / rd; break
            else:
                if hi >= sl: exit_r = (entry - sl) / rd; break
                if lo <= tp: exit_r = (entry - tp) / rd; break
        if exit_r is None:
            continue
        out.append({"entry": entry, "risk_dist": rd, "raw_r": exit_r, "dir": sig, "time": t})

    print(fmt("TURTLE_SOUP live (simmetrica)", out), flush=True)
    buys = [t for t in out if t["dir"] == 1]
    sells = [t for t in out if t["dir"] == -1]
    print(fmt("  BUY-only", buys), flush=True)
    print(fmt("  SELL-only", sells), flush=True)


if __name__ == "__main__":
    main()
