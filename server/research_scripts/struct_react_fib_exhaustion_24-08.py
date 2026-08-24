#!/usr/bin/env python3
"""
24/08 (17) - prima ottimizzazione individuale su una baseline gia'
trovata, come richiesto dall'utente. STRUCT_REACT (BUY-only, la
diversificatrice piu' solida di oggi - vedi [[NEXUS EA - Correlazione
tra le 20 Strategie (24-08)]]) + Fibonacci come GESTIONE DI USCITA/
REVERSE, non filtro d'ingresso (idea esplicita dell'utente, mai provata
oggi in questa forma - il tentativo precedente su EMA_PULLBACK era una
zona di ritracciamento come filtro d'INGRESSO, un meccanismo diverso).

Meccanismo:
1. All'apertura del trade BUY, ancora l'estensione Fibonacci allo swing
   (range max-min) delle 20 barre precedenti l'ingresso.
2. Livello di "esaurimento" = entry + 1.618 x swing_range (estensione
   Fibonacci classica).
3. Durante il trade, controllati nell'ordine: SL originale (protezione),
   poi TP originale, POI il livello di esaurimento - se il prezzo lo
   raggiunge PRIMA di SL/TP, il trade primario si chiude li' (di norma
   in profitto, essendo oltre l'entry nella direzione favorevole) e si
   apre un trade di REVERSE (SELL, opposto) dallo stesso prezzo, con lo
   stesso profilo SL/TP ma direzione invertita - stesso principio "lato
   SELL possibile hedge naturale" gia' trovato nella diagnosi per-data di
   STRUCT_REACT (il SELL era forte nella finestra vecchia/laterale).
4. Il reverse e' valutato sia a size piena (limite superiore) sia a size
   dimezzata ("lotto ridotto", la richiesta esplicita dell'utente) - il
   PF non cambia con la size (e' un rapporto), ma il contributo in R
   sommato si', quindi riportati entrambi.

Confronto a tre bracci: (a) baseline invariata (nessun Fibonacci), (b)
solo l'uscita anticipata a esaurimento (nessun reverse), (c) uscita +
reverse completo - per isolare quale pezzo del meccanismo aggiunge
valore, non solo il risultato finale.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import backtest as bt

THR_ER = 0.045
FLOOR_PCTL = 0.3
MAX_HOLD = 200
SL_MULT, TP_MULT = 2.0, 6.0
SWING_N = 20
FIB_EXT = 1.618
REVERSE_SIZE_MULT = 0.5


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
            net.append((t["raw_r"] - cost_r) * t.get("weight", 1.0))
        wf = walk_forward(net)
        wf_str = " | ".join(f"{p:.2f}" for _, p in wf) if wf else "n/a"
        n_pos = sum(1 for _, p in (wf or []) if p >= 1.0)
        mid = len(net) // 2
        h1, h2 = net[:mid], net[mid:]
        print(f"  {preset:16s} aggPF={pf(net):.2f} sumR={sum(net):+7.1f} win>=1:{n_pos}/{len(wf) if wf else 0}"
              f"  meta1={pf(h1):.2f}/meta2={pf(h2):.2f}  [{wf_str}]", flush=True)


def get_data():
    candles, src = bt._fetch_real("XAUUSD", "4h", 110000)
    ind = bt._prep(candles)
    atr, closes = ind["atr"], ind["close"]
    return candles, ind, atr, closes


def find_signals():
    """Segnali BUY validi (ER+floor), stessa base di sempre - restituisce
    lista di indici i con tutto il necessario gia' filtrato."""
    candles, ind, atr, closes = get_data()
    n = len(candles)
    lb_er = 1000
    sig_fn = bt.STRATEGIES["STRUCT_REACT"]
    atr_hist, sigs = [], []
    for i in range(max(1500, lb_er + 50), n - 2):
        a = atr[i]
        if a:
            atr_hist.append(a)
        sig = sig_fn(candles, ind, i)
        if sig != 1 or not a:  # BUY-only
            continue
        e = efficiency_ratio(closes, i, lb_er)
        if e is None or e < THR_ER or len(atr_hist) < 500:
            continue
        w = sorted(atr_hist[-2000:])
        floor = w[min(int(FLOOR_PCTL * len(w)), len(w) - 1)]
        if a < floor:
            continue
        sigs.append(i)
    return candles, sigs


def baseline_trades(candles, sigs):
    out = []
    n = len(candles)
    for i in sigs:
        entry = candles[i + 1]["open"]
        sl = entry - SL_MULT * _atr_at(candles, i)
        tp = entry + TP_MULT * _atr_at(candles, i)
        rd = abs(entry - sl)
        if rd <= 0:
            continue
        exit_r = None
        for j in range(i + 2, min(i + 2 + MAX_HOLD, n)):
            hi, lo = candles[j]["high"], candles[j]["low"]
            if lo <= sl: exit_r = (sl - entry) / rd; break
            elif hi >= tp: exit_r = (tp - entry) / rd; break
        if exit_r is None:
            continue
        out.append({"entry": entry, "risk_dist": rd, "raw_r": exit_r, "weight": 1.0})
    return out


_ATR_CACHE = {}


def _atr_at(candles, i):
    if id(candles) not in _ATR_CACHE:
        _ATR_CACHE[id(candles)] = bt.atr_series(candles, 14)
    return _ATR_CACHE[id(candles)][i]


def fib_exit_trades(candles, sigs, with_reverse, reverse_weight):
    out = []
    n = len(candles)
    for i in sigs:
        a = _atr_at(candles, i)
        entry = candles[i + 1]["open"]
        sl = entry - SL_MULT * a
        tp = entry + TP_MULT * a
        rd = abs(entry - sl)
        if rd <= 0:
            continue
        window = candles[max(0, i - SWING_N + 1):i + 1]
        swing_range = max(c["high"] for c in window) - min(c["low"] for c in window)
        exhaustion = entry + FIB_EXT * swing_range if swing_range > 0 else None

        exit_r, exit_j, exit_price, hit_exhaustion = None, None, None, False
        for j in range(i + 2, min(i + 2 + MAX_HOLD, n)):
            hi, lo = candles[j]["high"], candles[j]["low"]
            if lo <= sl:
                exit_r, exit_j = (sl - entry) / rd, j
                break
            if exhaustion is not None and hi >= exhaustion:
                exit_r, exit_j, exit_price = (exhaustion - entry) / rd, j, exhaustion
                hit_exhaustion = True
                break
            if hi >= tp:
                exit_r, exit_j = (tp - entry) / rd, j
                break
        if exit_r is None:
            continue
        out.append({"entry": entry, "risk_dist": rd, "raw_r": exit_r, "weight": 1.0})

        if with_reverse and hit_exhaustion:
            r_entry = exit_price
            r_sl = r_entry + SL_MULT * a
            r_tp = r_entry - TP_MULT * a
            r_rd = abs(r_entry - r_sl)
            if r_rd <= 0:
                continue
            r_exit = None
            for k in range(exit_j + 1, min(exit_j + 1 + MAX_HOLD, n)):
                hi, lo = candles[k]["high"], candles[k]["low"]
                if hi >= r_sl:
                    r_exit = (r_entry - r_sl) / r_rd
                    break
                elif lo <= r_tp:
                    r_exit = (r_entry - r_tp) / r_rd
                    break
            if r_exit is not None:
                out.append({"entry": r_entry, "risk_dist": r_rd, "raw_r": r_exit, "weight": reverse_weight})
    return out


def main():
    candles, sigs = find_signals()
    print(f"Segnali BUY totali: {len(sigs)}", flush=True)

    report("(a) baseline invariata (nessun Fibonacci)", baseline_trades(candles, sigs))
    report("(b) uscita anticipata a esaurimento 1.618, NESSUN reverse",
           fib_exit_trades(candles, sigs, with_reverse=False, reverse_weight=0.0))
    report("(c) uscita + reverse a size PIENA (limite superiore)",
           fib_exit_trades(candles, sigs, with_reverse=True, reverse_weight=1.0))
    report("(c bis) uscita + reverse a LOTTO RIDOTTO (0.5x, la richiesta dell'utente)",
           fib_exit_trades(candles, sigs, with_reverse=True, reverse_weight=REVERSE_SIZE_MULT))


if __name__ == "__main__":
    main()
