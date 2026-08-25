#!/usr/bin/env python3
"""
25/08 - completa l'idea Elliott Wave dell'utente dal lato mancante.
Finora usata solo come FILTRO di esclusione (sopprimi un segnale se un
impulso si e' appena esaurito - vedi elliott_wave_filter_25-08.py, 21/25
strategie migliorano). L'idea originale dell'utente pero' era piu'
ampia: "possiamo trovare dove siamo nell'onda, dove puo' essere la
possibile continuazione dell'onda" - un uso POSITIVO, non solo negativo.

Nuova strategia standalone ELLIOTT_WAVE3_CONT: usa lo stesso ZigZag di
oggi per riconoscere l'assetto "onda 1 (impulso) + onda 2 (correzione)"
e comprare la ripartenza attesa (onda 3), la fase di solito piu' forte
di un impulso Elliott:

1. Ultimi 3 pivot ZigZag: P0(low)->P1(high)->P2(low) per un setup
   rialzista (mirror per ribassista).
2. Regola 1: onda 2 non ritraccia sotto l'inizio di onda 1 (P2 > P0) -
   altrimenti il conteggio non e' valido.
3. Regola 2: la profondita' della correzione (P1-P2)/(P1-P0) deve
   stare in una zona Fibonacci plausibile per un'onda 2 (38.2%-78.6%,
   la regola pratica standard) - non troppo debole, non troppo forte.
4. Segnale: nel momento stesso in cui il pivot P2 si conferma (lo
   ZigZag rileva l'inversione), se le regole 1-2 sono soddisfatte,
   entra BUY - si scommette sulla ripartenza in onda 3.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import backtest as bt

THR_ER = 0.045
FLOOR_PCTL = 0.3
MAX_HOLD = 200
LOOKBACK_ER = 1000
DEV_MULT = 2.0
RETRACE_MIN, RETRACE_MAX = 0.382, 0.786


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


def fmt(label, trades):
    net = net_series(trades)
    wf = walk_forward(net)
    mid = len(net) // 2
    n_pos = sum(1 for _, p in (wf or []) if p >= 1.0)
    return (f"{label:40s} n={len(trades):4d} PF={pf(net):.2f} "
            f"(m1={pf(net[:mid]):.2f}/m2={pf(net[mid:]):.2f}) win={n_pos}/{len(wf) if wf else 0}")


def build_zigzag_pivots(candles, atr, dev_mult=DEV_MULT):
    n = len(candles)
    highs = [c["high"] for c in candles]
    lows = [c["low"] for c in candles]
    pivots = []
    dir_up = None
    ext_idx = 0
    ext_price = highs[0]
    pivot_at = [None] * n  # pivot_at[i] = index nella lista pivots del pivot appena confermato a i, o None

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
                pivot_at[i] = len(pivots) - 1
                dir_up = False
                ext_price = lows[i]; ext_idx = i
        else:
            if lows[i] < ext_price:
                ext_price = lows[i]; ext_idx = i
            elif highs[i] - ext_price >= dev:
                pivots.append((ext_idx, ext_price, "L"))
                pivot_at[i] = len(pivots) - 1
                dir_up = True
                ext_price = highs[i]; ext_idx = i
    return pivots, pivot_at


def wave3_signal_series(candles, atr, dev_mult=DEV_MULT):
    """Ritorna, per ogni barra i, +1/-1/0: segnale di continuazione
    onda3 confermato esattamente alla barra in cui il pivot 'onda 2'
    si chiude, 0 altrove."""
    n = len(candles)
    pivots, pivot_at = build_zigzag_pivots(candles, atr, dev_mult)
    sig = [0] * n
    for i in range(n):
        k = pivot_at[i]
        if k is None or k < 2:
            continue
        P0 = pivots[k - 2]
        P1 = pivots[k - 1]
        P2 = pivots[k]
        if P0[2] == "L" and P1[2] == "H" and P2[2] == "L":
            wave1 = P1[1] - P0[1]
            wave2 = P1[1] - P2[1]
            if wave1 <= 0 or wave2 <= 0:
                continue
            if P2[1] <= P0[1]:
                continue  # onda2 ritraccia sotto l'inizio di onda1, non valido
            retrace = wave2 / wave1
            if RETRACE_MIN <= retrace <= RETRACE_MAX:
                sig[i] = 1
        elif P0[2] == "H" and P1[2] == "L" and P2[2] == "H":
            wave1 = P0[1] - P1[1]
            wave2 = P2[1] - P1[1]
            if wave1 <= 0 or wave2 <= 0:
                continue
            if P2[1] >= P0[1]:
                continue
            retrace = wave2 / wave1
            if RETRACE_MIN <= retrace <= RETRACE_MAX:
                sig[i] = -1
    return sig


def collect(candles, ind, atr, closes, wave_sig, sl_mult, tp_mult, buy_only=False):
    n = len(candles)
    atr_hist, out = [], []
    for i in range(max(1500, 1050), n - 2):
        a = atr[i]
        if a:
            atr_hist.append(a)
        sig = wave_sig[i]
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
        out.append({"entry": entry, "risk_dist": rd, "raw_r": exit_r, "dir": sig, "time": candles[i + 1]["time"]})
    return out


def main():
    candles, src = bt._fetch_real("XAUUSD", "4h", 110000)
    ind = bt._prep(candles)
    atr, closes = ind["atr"], ind["close"]
    wave_sig = wave3_signal_series(candles, atr)
    n_sig = sum(1 for s in wave_sig if s != 0)
    print(f"Segnali onda3 grezzi (prima di ER/floor): {n_sig}", flush=True)

    for sl_m, tp_m in ((1.5, 4.0), (1.5, 6.0), (2.0, 6.0)):
        trades = collect(candles, ind, atr, closes, wave_sig, sl_m, tp_m, buy_only=False)
        print(fmt(f"simmetrica SL{sl_m}/TP{tp_m}", trades), flush=True)
        buys = [t for t in trades if t["dir"] == 1]
        sells = [t for t in trades if t["dir"] == -1]
        print(fmt(f"  BUY-only SL{sl_m}/TP{tp_m}", buys), flush=True)
        print(fmt(f"  SELL-only SL{sl_m}/TP{tp_m}", sells), flush=True)


if __name__ == "__main__":
    main()
