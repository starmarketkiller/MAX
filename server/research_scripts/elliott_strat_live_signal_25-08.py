#!/usr/bin/env python3
"""
25/08 - prima ricerca da zero sul vero segnale live NXS_Strat_Elliott()
(NXS_Strategies_Elliott.mqh) - strategia nuova, mai backtestata
(InpUseStrat_Elliott=false, commento "nuova strategia, backtesta prima").
Diversa sia dal filtro di esaurimento Elliott per-strategia (NXS_Elliott
Filter.mqh, gia' costruito e applicato ad altre 16 strategie stasera) sia
dalla ricerca Python ELLIOTT_WAVE3_CONT di ieri - questa e' una terza
implementazione indipendente, mai portata prima.

Meccanica (fedele a NXS_Strat_Elliott, righe 1-152):
1. Pivot alternati (swing high/low, wing=InpEllSwingWing=3) scansionati
   all'indietro dalla barra shift1, fino a 8 pivot, saltando pivot dello
   stesso tipo consecutivi.
2. W2->W3 (continuazione): 3 pivot L2/H1/L0 (BUY) o H2/L1/H0 (SELL),
   validita' onda1 (H1>L0 etc.), retracement onda2 in [0.382,0.786]
   (InpEllRetraceMin/Max), conferma candela shift1 nella direzione,
   target proiezione 1.618x onda1 dal pivot L2/H2.
3. W4->W5 (continuazione): 5 pivot, no-overlap onda4/onda1, retracement
   onda4 in [0.236,0.618] (fisso nel codice, non da input), target
   1.0x l'ampiezza onda1..3 dal pivot onda4.
4. W5 reversal: 6 pivot, impulso completo (5 onde crescenti/calanti),
   target ritracciamento 50% dell'intero impulso.
Stop nativo = oltre l'estremo di invalidazione +/- 0.4-0.5xATR (varia
per pattern, replicato esattamente per ciascuno). TF live: nessuna voce
per "ELLIOTT" in NXS_Profile_TF -> ricade su PERIOD_CURRENT ->
NXS_EffTF() ricade su InpTFEntry = M15.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import backtest as bt

MAX_HOLD = 300
WING = 3
RETRACE_MIN, RETRACE_MAX = 0.382, 0.786


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
    return (f"{label:14s} n={len(trades):4d} PF={pf(net):.2f} "
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


def pivots(highs, lows, i, wing, max_scan=100, max_n=8):
    """Da shift1 (=indice i, ultima barra chiusa) all'indietro: fino a
    max_n pivot alternati, shift wing+1..max_scan. Ritorna liste
    price[]/type[] (+1 high, -1 low), piu' recenti prima."""
    price, typ = [], []
    last_type = 0
    for sh in range(wing + 1, max_scan + 1):
        idx = i - sh + 1
        if idx < 0 or len(price) >= max_n:
            break
        sh_ = is_swing_high(highs, idx, wing)
        sl_ = is_swing_low(lows, idx, wing)
        t = 1 if sh_ else (-1 if sl_ else 0)
        if t == 0 or t == last_type:
            continue
        price.append(highs[idx] if t == 1 else lows[idx])
        typ.append(t)
        last_type = t
    return price, typ


def retrace(a, b, cur):
    rng = abs(b - a)
    if rng <= 0:
        return -1
    return abs(b - cur) / rng


def elliott_signal(highs, lows, closes, opens, atrv, i):
    a = atrv[i]
    if not a:
        return 0, None, None
    p, t = pivots(highs, lows, i, WING)
    np_ = len(p)
    if np_ < 3:
        return 0, None, None
    c1, o1 = closes[i], opens[i]
    bull1, bear1 = c1 > o1, c1 < o1

    # W2->W3 BUY: L2(-1),H1(+1),L0(-1)
    if t[0] == -1 and t[1] == 1 and t[2] == -1:
        L2, H1, L0 = p[0], p[1], p[2]
        if H1 > L0 and L2 > L0:
            r = retrace(L0, H1, L2)
            if RETRACE_MIN <= r <= RETRACE_MAX and bull1 and c1 <= H1:
                sl = min(L2, L0) - 0.4 * a
                tp = L2 + 1.618 * (H1 - L0)
                return 1, sl, tp
    # W2->W3 SELL
    if t[0] == 1 and t[1] == -1 and t[2] == 1:
        H2, L1, H0 = p[0], p[1], p[2]
        if L1 < H0 and H2 < H0:
            r = retrace(H0, L1, H2)
            if RETRACE_MIN <= r <= RETRACE_MAX and bear1 and c1 >= L1:
                sl = max(H2, H0) + 0.4 * a
                tp = H2 - 1.618 * (H0 - L1)
                return -1, sl, tp
    # W4->W5 BUY
    if np_ >= 5 and t[0] == -1 and t[1] == 1 and t[2] == -1 and t[3] == 1 and t[4] == -1:
        L4, H3, L2, H1, L0 = p[0], p[1], p[2], p[3], p[4]
        if H3 > H1 and H1 > L0 and L2 > L0 and L4 > H1:
            r = retrace(L2, H3, L4)
            if 0.236 <= r <= 0.618 and bull1 and c1 <= H3:
                sl = L4 - 0.4 * a
                tp = L4 + 1.0 * (H3 - L2)
                return 1, sl, tp
    # W4->W5 SELL
    if np_ >= 5 and t[0] == 1 and t[1] == -1 and t[2] == 1 and t[3] == -1 and t[4] == 1:
        H4, L3, H2, L1, H0 = p[0], p[1], p[2], p[3], p[4]
        if L3 < L1 and L1 < H0 and H2 < H0 and H4 < L1:
            r = retrace(H2, L3, H4)
            if 0.236 <= r <= 0.618 and bear1 and c1 >= L3:
                sl = H4 + 0.4 * a
                tp = H4 - 1.0 * (H2 - L3)
                return -1, sl, tp
    # W5 reversal SELL
    if np_ >= 6 and t[0] == 1 and t[1] == -1 and t[2] == 1 and t[3] == -1 and t[4] == 1 and t[5] == -1:
        H5, L4, H3, L2, H1, L0 = p[0], p[1], p[2], p[3], p[4], p[5]
        if H5 > H3 and H3 > H1 and L4 > L2 and L2 > L0 and bear1 and c1 < H5:
            sl = H5 + 0.5 * a
            tp = H5 - 0.5 * (H5 - L0)
            return -1, sl, tp
    # W5 reversal BUY
    if np_ >= 6 and t[0] == -1 and t[1] == 1 and t[2] == -1 and t[3] == 1 and t[4] == -1 and t[5] == 1:
        L5, H4, L3, H2, L1, H0 = p[0], p[1], p[2], p[3], p[4], p[5]
        if L5 < L3 and L3 < L1 and H4 < H2 and H2 < H0 and bull1 and c1 > L5:
            sl = L5 - 0.5 * a
            tp = L5 + 0.5 * (H0 - L5)
            return 1, sl, tp
    return 0, None, None


def test_tf(label, interval, bars):
    candles, _ = bt._fetch_real("XAUUSD", interval, bars)
    ind = bt._prep(candles)
    atrv = ind["atr"]
    highs = [c["high"] for c in candles]
    lows = [c["low"] for c in candles]
    closes = [c["close"] for c in candles]
    opens = [c["open"] for c in candles]
    n = len(candles)

    out = []
    for i in range(120, n - 2):
        sig, sl, tp = elliott_signal(highs, lows, closes, opens, atrv, i)
        if sig == 0:
            continue
        entry_i = i + 1
        entry = candles[entry_i]["open"]
        rd = abs(entry - sl)
        if rd <= 0:
            continue
        exit_r = None
        for j in range(entry_i + 1, min(entry_i + 1 + MAX_HOLD, n)):
            hi, lo = candles[j]["high"], candles[j]["low"]
            if sig == 1:
                if lo <= sl: exit_r = (sl - entry) / rd; break
                if hi >= tp: exit_r = (tp - entry) / rd; break
            else:
                if hi >= sl: exit_r = (entry - sl) / rd; break
                if lo <= tp: exit_r = (entry - tp) / rd; break
        if exit_r is None:
            continue
        out.append({"entry": entry, "risk_dist": rd, "raw_r": exit_r, "dir": sig})

    print(f"=== ELLIOTT su {label} ===", flush=True)
    print(fmt("simmetrica", out), flush=True)
    print(fmt("BUY-only", [t for t in out if t["dir"] == 1]), flush=True)
    print(fmt("SELL-only", [t for t in out if t["dir"] == -1]), flush=True)


def main():
    test_tf("M15 (live)", "15m", 130000)
    test_tf("M5 (scalp)", "5m", 200000)
    test_tf("H1 (wide)", "1h", 110000)
    test_tf("H4 (wide)", "4h", 30000)


if __name__ == "__main__":
    main()
