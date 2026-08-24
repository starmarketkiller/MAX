#!/usr/bin/env python3
"""
24/08 - test di "Hull Suite Strategy" (script TradingView condiviso
dall'utente, tinkered by InSilico / DashTrader), uno dei 4 nuovi script
di oggi (vedi vault "NEXUS EA - Idee da Script TradingView Esterni
17-08", addendum 24/08). Modalita' default "Hma", length=55 (il valore
che l'autore raccomanda per "swing entry" - l'altro default, 180-200,
e' descritto come "floating S/R", un uso diverso, non testato qui: una
sola ipotesi per esperimento).

Conversione dal sistema Pine (sempre in mercato, si ribalta long<->short
a ogni cambio di trend HULL[0] vs HULL[2]) al nostro formato ad EVENTO,
stessa scelta gia' fatta per MACD+SMA200 il 17/08: il segnale scatta
SOLO al bar del cambio di direzione, non ad ogni barra dove la
condizione resta vera - altrimenti il nostro motore (stop ATR fisso,
non "resta in posizione finche' il trend non gira") non replicherebbe
il sistema originale.

Filtro di regime ER (trend, soglia 0.045) applicato: e' un sistema
trend-following (media che segue il prezzo), stessa logica della scelta
16-17/08 (trend-following -> filtro trend).
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import backtest as bt

HULL_LEN = 55
LOOKBACK_ER = {"4h": 1000, "1h": 4000}
THR_ER = 0.045
MAX_HOLD = 200


def wma_series(values, length):
    n = len(values)
    out = [None] * n
    denom = length * (length + 1) / 2.0
    numer = 0.0
    S = 0.0  # rolling sum of last `length` values ending at i-1
    for i in range(n):
        v = values[i]
        numer = numer + length * v - S
        S = S + v - (values[i - length] if i - length >= 0 else 0.0)
        if i >= length - 1:
            out[i] = numer / denom
        else:
            # invalid until window full; reset accumulators is unnecessary,
            # the recurrence is still correct once i>=length-1
            out[i] = None
    return out


def hma_series(values, length):
    half = max(1, length // 2)
    sq = max(1, round(length ** 0.5))
    wma_half = wma_series(values, half)
    wma_full = wma_series(values, length)
    n = len(values)
    diff = [None] * n
    for i in range(n):
        if wma_half[i] is not None and wma_full[i] is not None:
            diff[i] = 2 * wma_half[i] - wma_full[i]
    # wma_series needs a plain list without None gaps for the sqrt-length pass;
    # feed 0.0 where undefined (only affects the warm-up region, discarded anyway)
    diff_filled = [d if d is not None else 0.0 for d in diff]
    hull = wma_series(diff_filled, sq)
    warmup = (length - 1) + (sq - 1)
    for i in range(min(warmup, n)):
        hull[i] = None
    return hull


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
    out = []
    for w in range(nw):
        seg = rs[w * size:(w + 1) * size] if w < nw - 1 else rs[w * size:]
        out.append((len(seg), pf(seg)))
    return out


def main():
    for tf in ("4h", "1h"):
        candles, src = bt._fetch_real("XAUUSD", tf, 110000)
        closes = [c["close"] for c in candles]
        atr = bt.atr_series(candles, 14)
        hull = hma_series(closes, HULL_LEN)
        n = len(candles)
        lb_er = LOOKBACK_ER[tf]

        trades = []
        up_prev = None
        for i in range(max(HULL_LEN + 10, lb_er + 50), n - 2):
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
            e = efficiency_ratio(closes, i, lb_er)
            if e is None or e < THR_ER:
                continue
            a = atr[i]
            if not a:
                continue
            entry = candles[i + 1]["open"]
            sl = entry - sig * 1.5 * a
            tp = entry + sig * 4.0 * a
            rd = abs(entry - sl)
            if rd <= 0:
                continue
            exit_r = None
            for j in range(i + 2, min(i + 2 + MAX_HOLD, n)):
                hi, lo = candles[j]["high"], candles[j]["low"]
                if sig == 1:
                    if lo <= sl:
                        exit_r = (sl - entry) / rd
                        break
                    elif hi >= tp:
                        exit_r = (tp - entry) / rd
                        break
                else:
                    if hi >= sl:
                        exit_r = (entry - sl) / rd
                        break
                    elif lo <= tp:
                        exit_r = (entry - tp) / rd
                        break
            if exit_r is None:
                continue
            trades.append({"entry": entry, "risk_dist": rd, "raw_r": exit_r})

        print(f"--- Hull Suite (Hma len={HULL_LEN}), TF={tf}: {len(trades)} trade grezzi ---", flush=True)
        for preset in ("retail_standard", "ecn"):
            net = []
            for t in trades:
                cost = bt.scaled_cost_for_price(preset, t["entry"])
                cost_r = min((cost["spread_price"] + cost["slippage_price"]) / t["risk_dist"], bt.MAX_COST_R_PER_TRADE)
                net.append(t["raw_r"] - cost_r)
            wf = walk_forward(net)
            wf_str = " | ".join(f"PF={p:.2f}" for _, p in wf) if wf else "n/a"
            n_pos = sum(1 for _, p in (wf or []) if p >= 1.0)
            print(f"  {preset:16s} aggPF={pf(net):.2f} sumR={sum(net):+.1f} "
                  f"finestre_PF>=1:{n_pos}/{len(wf) if wf else 0}  [{wf_str}]", flush=True)


if __name__ == "__main__":
    main()
