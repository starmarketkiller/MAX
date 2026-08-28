#!/usr/bin/env python3
"""
25/08 - prima implementazione concreta dell'idea Elliott Wave del
25/08 (mai attaccata prima, l'utente l'aveva chiesta all'inizio della
sessione: "i pattern di elliot sono meccanici in se, la soggettivita'
sta solo nell'interpretazione al momento senza sapere cos'e' successo
prima"). Costruita come FILTRO di contesto su strategie esistenti, non
come sistema standalone (coerente con come sono stati trattati ER
regime/ATR floor/D1-align finora).

Meccanica: ZigZag su prezzo (soglia = dev_mult*ATR), poi le 3 regole
Elliott classiche su un impulso a 5 onde (bull: basso-alto-basso-alto-
basso-alto = P0..P5):
  1. onda 2 non ritraccia sotto l'inizio dell'onda 1 (P2 > P0)
  2. onda 3 non e' la piu' corta tra onda1/onda3/onda5
  3. onda 4 non sovrappone il territorio dell'onda 1 (P4 > P1)
(mirror per impulso ribassista). Se un impulso a 5 onde valido si
conclude (P5 confermato), la barra successiva entra in stato
"ESAURITO" nella direzione dell'impulso finche' non si forma un nuovo
pivot - usato per SOPPRIMERE segnali nella stessa direzione
dell'impulso appena esaurito (aspettarsi una correzione).
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import backtest as bt

THR_ER = 0.045
FLOOR_PCTL = 0.3
MAX_HOLD = 200
LOOKBACK_ER = 1000


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


def net_series(trades, preset="retail_standard"):
    out = []
    for t in trades:
        cost = bt.scaled_cost_for_price(preset, t["entry"])
        cost_r = min((cost["spread_price"] + cost["slippage_price"]) / t["risk_dist"], bt.MAX_COST_R_PER_TRADE)
        out.append(t["raw_r"] - cost_r)
    return out


def build_zigzag_full(candles, atr, dev_mult=2.0):
    """Versione che ricostruisce l'array di esaurimento correttamente
    segmento-per-segmento (tra un pivot e il successivo), non solo il
    primo bar dopo P5 - necessaria per un filtro usabile su ogni barra."""
    n = len(candles)
    highs = [c["high"] for c in candles]
    lows = [c["low"] for c in candles]
    pivots = []
    dir_up = None
    ext_idx = 0
    ext_price = highs[0]

    pivot_events = []  # (index_confermato, ) ogni volta che un pivot si chiude

    for i in range(1, n):
        a = atr[i]
        if not a:
            continue
        dev = dev_mult * a
        if dir_up is None:
            if highs[i] - min(lows[0:i + 1]) >= dev:
                dir_up = True
                low_idx = lows.index(min(lows[0:i + 1]))
                pivots.append((low_idx, lows[low_idx], "L"))
                ext_price = highs[i]; ext_idx = i
            elif max(highs[0:i + 1]) - lows[i] >= dev:
                dir_up = False
                hi_idx = highs.index(max(highs[0:i + 1]))
                pivots.append((hi_idx, highs[hi_idx], "H"))
                ext_price = lows[i]; ext_idx = i
            continue
        if dir_up:
            if highs[i] > ext_price:
                ext_price = highs[i]; ext_idx = i
            elif ext_price - lows[i] >= dev:
                pivots.append((ext_idx, ext_price, "H"))
                pivot_events.append(len(pivots) - 1)
                dir_up = False
                ext_price = lows[i]; ext_idx = i
        else:
            if lows[i] < ext_price:
                ext_price = lows[i]; ext_idx = i
            elif highs[i] - ext_price >= dev:
                pivots.append((ext_idx, ext_price, "L"))
                pivot_events.append(len(pivots) - 1)
                dir_up = True
                ext_price = highs[i]; ext_idx = i

    # ora cammina sui pivot in ordine e costruisci i segmenti di esaurimento
    exhaustion = [0] * n
    for k in pivot_events:
        if k < 5:
            continue
        P = pivots[k - 5:k + 1]
        types = [p[2] for p in P]
        prices = [p[1] for p in P]
        idxs = [p[0] for p in P]
        valid_bull = types == ["L", "H", "L", "H", "L", "H"]
        valid_bear = types == ["H", "L", "H", "L", "H", "L"]
        direction = 0
        if valid_bull:
            P0, P1, P2, P3, P4, P5 = prices
            w1, w3, w5 = P1 - P0, P3 - P2, P5 - P4
            if P2 > P0 and P4 > P1 and w3 >= w1 and w3 >= w5 and w1 > 0 and w3 > 0 and w5 > 0:
                direction = 1
        elif valid_bear:
            P0, P1, P2, P3, P4, P5 = prices
            w1, w3, w5 = P0 - P1, P2 - P3, P4 - P5
            if P2 < P0 and P4 < P1 and w3 >= w1 and w3 >= w5 and w1 > 0 and w3 > 0 and w5 > 0:
                direction = -1
        if direction != 0:
            start = idxs[-1]
            end = pivots[k + 1][0] if (k + 1) < len(pivots) else n
            for j in range(start, min(end, n)):
                exhaustion[j] = direction
    return exhaustion, pivots


def collect(name, sl_mult, tp_mult, dev_mult=2.0, use_elliott=False, buy_only=False):
    candles, src = bt._fetch_real("XAUUSD", "4h", 110000)
    ind = bt._prep(candles)
    atr, closes = ind["atr"], ind["close"]
    n = len(candles)
    sig_fn = bt.STRATEGIES[name]
    exhaustion = None
    if use_elliott:
        exhaustion, _ = build_zigzag_full(candles, atr, dev_mult)
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
        e = efficiency_ratio(closes, i, LOOKBACK_ER)
        if e is None or e < THR_ER or len(atr_hist) < 500:
            continue
        w = sorted(atr_hist[-2000:])
        floor = w[min(int(FLOOR_PCTL * len(w)), len(w) - 1)]
        if a < floor:
            continue
        if use_elliott and exhaustion[i] == sig:
            continue  # sopprimi: impulso nella stessa direzione appena esaurito
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


def fmt(label, trades):
    net = net_series(trades)
    wf = walk_forward(net)
    mid = len(net) // 2
    n_pos = sum(1 for _, p in (wf or []) if p >= 1.0)
    return (f"{label:40s} n={len(trades):4d} PF={pf(net):.2f} "
            f"(m1={pf(net[:mid]):.2f}/m2={pf(net[mid:]):.2f}) win={n_pos}/{len(wf) if wf else 0}")


CANDIDATES = [
    ("ADX_RSI", 1.5, 4.0, True),
    ("STRUCT_REACT", 2.0, 6.0, True),
    ("EMA_PULLBACK", 1.5, 4.0, False),
    ("SAR", 1.5, 4.0, True),
    ("MACD", 1.5, 4.0, False),
]


def main():
    for name, sl_m, tp_m, buy_only in CANDIDATES:
        print(f"=== {name} (buy_only={buy_only}) ===", flush=True)
        base = collect(name, sl_m, tp_m, use_elliott=False, buy_only=buy_only)
        print(fmt("  baseline (senza Elliott)", base), flush=True)
        for dev in (1.5, 2.0, 2.5):
            filt = collect(name, sl_m, tp_m, dev_mult=dev, use_elliott=True, buy_only=buy_only)
            print(fmt(f"  + Elliott exhaustion filter dev={dev}", filt), flush=True)
        print(flush=True)


if __name__ == "__main__":
    main()
