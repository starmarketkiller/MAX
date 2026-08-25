#!/usr/bin/env python3
"""
25/08 - riprova dell'idea Fibonacci esaurimento-reverse dell'utente
(prima versione: struct_react_fib_exhaustion_24-08.py, fallita su
STRUCT_REACT con uno swing a finestra fissa di 20 barre). Oggi
abbiamo un vero rilevatore di pivot (ZigZag di elliott_wave_filter_25-08.py)
- l'estensione Fibonacci ancorata all'ULTIMA GAMBA REALMENTE FORMATA
(non una finestra arbitraria) e' concettualmente piu' fedele all'idea
originale. Riprovata su STRUCT_REACT (per confronto diretto col
fallimento di ieri) + 3 strategie mai testate con questo meccanismo.

Meccanismo (identico a ieri, solo lo swing cambia):
1. All'ingresso, prendi l'ultima gamba ZigZag confermata (dal pivot
   precedente al pivot piu' recente prima del segnale).
2. Livello di esaurimento = entry + 1.618 x lunghezza_gamba (estensione
   Fibonacci classica) nella direzione del trade.
3. Se il prezzo raggiunge l'esaurimento prima di SL/TP, chiudi li' e
   apri un reverse dallo stesso prezzo, stesso profilo SL/TP,
   direzione opposta, a lotto pieno o ridotto (0.5x).
4. Confronto a 4 bracci: baseline, solo uscita anticipata (no reverse),
   reverse a size piena, reverse a lotto ridotto.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import backtest as bt
import importlib.util
spec = importlib.util.spec_from_file_location(
    "ew", os.path.join(os.path.dirname(os.path.abspath(__file__)), "elliott_wave_filter_25-08.py"))
ew = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ew)

THR_ER = 0.045
FLOOR_PCTL = 0.3
MAX_HOLD = 200
FIB_EXT = 1.618
REVERSE_SIZE_MULT = 0.5
DEV_MULT = 2.0


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
    for preset in ("retail_standard",):
        net = []
        for t in trades:
            cost = bt.scaled_cost_for_price(preset, t["entry"])
            cost_r = min((cost["spread_price"] + cost["slippage_price"]) / t["risk_dist"], bt.MAX_COST_R_PER_TRADE)
            net.append((t["raw_r"] - cost_r) * t.get("weight", 1.0))
        wf = walk_forward(net)
        n_pos = sum(1 for _, p in (wf or []) if p >= 1.0)
        mid = len(net) // 2
        h1, h2 = net[:mid], net[mid:]
        print(f"  {label:48s} n={len(trades):4d} PF={pf(net):.2f} "
              f"(m1={pf(h1):.2f}/m2={pf(h2):.2f}) win={n_pos}/{len(wf) if wf else 0}", flush=True)


_CACHE = {}


def get_data():
    if "4h" not in _CACHE:
        candles, src = bt._fetch_real("XAUUSD", "4h", 110000)
        ind = bt._prep(candles)
        atr = ind["atr"]
        _, pivots = ew.build_zigzag_full(candles, atr, DEV_MULT)
        _CACHE["4h"] = (candles, ind, atr, pivots)
    return _CACHE["4h"]


def last_leg_length(pivots, entry_idx):
    """Lunghezza (in prezzo) dell'ultima gamba ZigZag confermata prima
    di entry_idx - distanza tra gli ultimi due pivot."""
    prior = [p for p in pivots if p[0] < entry_idx]
    if len(prior) < 2:
        return None
    return abs(prior[-1][1] - prior[-2][1])


def find_signals(name, sl_mult, tp_mult, buy_only):
    candles, ind, atr, pivots = get_data()
    closes = ind["close"]
    n = len(candles)
    lb_er = 1000
    sig_fn = bt.STRATEGIES[name]
    atr_hist, sigs = [], []
    for i in range(max(1500, lb_er + 50), n - 2):
        a = atr[i]
        if a:
            atr_hist.append(a)
        sig = sig_fn(candles, ind, i)
        if sig == 0 or not a:
            continue
        if buy_only and sig != 1:
            continue
        e = ew.efficiency_ratio(closes, i, lb_er)
        if e is None or e < THR_ER or len(atr_hist) < 500:
            continue
        w = sorted(atr_hist[-2000:])
        floor = w[min(int(FLOOR_PCTL * len(w)), len(w) - 1)]
        if a < floor:
            continue
        sigs.append((i, sig))
    return candles, atr, pivots, sigs


def baseline_trades(candles, atr, sigs, sl_mult, tp_mult):
    out = []
    n = len(candles)
    for i, sig in sigs:
        a = atr[i]
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
        out.append({"entry": entry, "risk_dist": rd, "raw_r": exit_r, "weight": 1.0})
    return out


def fib_exit_trades(candles, atr, pivots, sigs, sl_mult, tp_mult, with_reverse, reverse_weight):
    out = []
    n = len(candles)
    for i, sig in sigs:
        a = atr[i]
        entry = candles[i + 1]["open"]
        sl = entry - sig * sl_mult * a
        tp = entry + sig * tp_mult * a
        rd = abs(entry - sl)
        if rd <= 0:
            continue
        leg = last_leg_length(pivots, i)
        exhaustion = entry + sig * FIB_EXT * leg if leg else None

        exit_r, exit_j, exit_price, hit_exhaustion = None, None, None, False
        for j in range(i + 2, min(i + 2 + MAX_HOLD, n)):
            hi, lo = candles[j]["high"], candles[j]["low"]
            if sig == 1:
                if lo <= sl:
                    exit_r, exit_j = (sl - entry) / rd, j; break
                if exhaustion is not None and hi >= exhaustion:
                    exit_r, exit_j, exit_price = (exhaustion - entry) / rd, j, exhaustion
                    hit_exhaustion = True; break
                if hi >= tp:
                    exit_r, exit_j = (tp - entry) / rd, j; break
            else:
                if hi >= sl:
                    exit_r, exit_j = (entry - sl) / rd, j; break
                if exhaustion is not None and lo <= exhaustion:
                    exit_r, exit_j, exit_price = (entry - exhaustion) / rd, j, exhaustion
                    hit_exhaustion = True; break
                if lo <= tp:
                    exit_r, exit_j = (entry - tp) / rd, j; break
        if exit_r is None:
            continue
        out.append({"entry": entry, "risk_dist": rd, "raw_r": exit_r, "weight": 1.0})

        if with_reverse and hit_exhaustion:
            r_sig = -sig
            r_entry = exit_price
            r_sl = r_entry - r_sig * sl_mult * a
            r_tp = r_entry + r_sig * tp_mult * a
            r_rd = abs(r_entry - r_sl)
            if r_rd <= 0:
                continue
            r_exit = None
            for k in range(exit_j + 1, min(exit_j + 1 + MAX_HOLD, n)):
                hi, lo = candles[k]["high"], candles[k]["low"]
                if r_sig == 1:
                    if lo <= r_sl: r_exit = (r_sl - r_entry) / r_rd; break
                    elif hi >= r_tp: r_exit = (r_tp - r_entry) / r_rd; break
                else:
                    if hi >= r_sl: r_exit = (r_entry - r_sl) / r_rd; break
                    elif lo <= r_tp: r_exit = (r_entry - r_tp) / r_rd; break
            if r_exit is not None:
                out.append({"entry": r_entry, "risk_dist": r_rd, "raw_r": r_exit, "weight": reverse_weight})
    return out


CANDIDATES = [
    ("STRUCT_REACT", 2.0, 6.0, True),
    ("SAR", 1.5, 4.0, True),
    ("ADX_RSI", 1.5, 4.0, True),
    ("MACD", 1.5, 4.0, False),
]


def main():
    for name, sl_m, tp_m, buy_only in CANDIDATES:
        print(f"=== {name} ===", flush=True)
        candles, atr, pivots, sigs = find_signals(name, sl_m, tp_m, buy_only)
        report("(a) baseline (nessun Fibonacci)", baseline_trades(candles, atr, sigs, sl_m, tp_m))
        report("(b) uscita anticipata a esaurimento, no reverse",
               fib_exit_trades(candles, atr, pivots, sigs, sl_m, tp_m, False, 0.0))
        report("(c) uscita + reverse size piena",
               fib_exit_trades(candles, atr, pivots, sigs, sl_m, tp_m, True, 1.0))
        report("(c bis) uscita + reverse lotto ridotto (0.5x)",
               fib_exit_trades(candles, atr, pivots, sigs, sl_m, tp_m, True, REVERSE_SIZE_MULT))
        print(flush=True)


if __name__ == "__main__":
    main()
