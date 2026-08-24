#!/usr/bin/env python3
"""
24/08 (2) - seguito a hull_suite_24-08.py (bocciata al config di default
dell'autore, length=55/Hma). L'utente chiede di provare altre varianti
prima di chiudere il caso, invece di fermarsi al primo parametro.

Sweep su DUE assi separati (non incrociati, per non esplodere in
combinazioni e restare leggibili — la regola "un plateau, non un picco"
si giudica meglio un asse alla volta):

1. LENGTH (asse principale, quello che l'autore stesso dice di
   modificare: 55 per "swing entry", 180-200 per "floating S/R" - due usi
   diversi, non uno solo) - mode Hma fissa, filtro regime ER trend
   invariato (gia' la scelta corretta per un sistema trend-following).
2. MODE (Hma/Ehma/Thma, i 3 algoritmi offerti dallo script) - alla
   length di default (55) e a quella "floating S/R" (200), per vedere se
   il tipo di media conta piu' della sua lunghezza.

Ablation aggiuntiva: miglior config trovato, SENZA filtro di regime, per
capire se il filtro (non il segnale) e' il collo di bottiglia.

Stessa pipeline delle altre verifiche di oggi: walk-forward 5 finestre,
costi retail/ECN, conversione a evento (cambio di direzione HULL[0] vs
HULL[2], stesso motivo gia' spiegato in hull_suite_24-08.py).
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import backtest as bt

LOOKBACK_ER = {"4h": 1000, "1h": 4000}
THR_ER = 0.045
MAX_HOLD = 200


def wma_series(values, length):
    n = len(values)
    out = [None] * n
    denom = length * (length + 1) / 2.0
    numer = 0.0
    S = 0.0
    for i in range(n):
        v = values[i]
        numer = numer + length * v - S
        S = S + v - (values[i - length] if i - length >= 0 else 0.0)
        out[i] = numer / denom if i >= length - 1 else None
    return out


def ema_series(values, length):
    n = len(values)
    out = [None] * n
    if n == 0:
        return out
    a = 2.0 / (length + 1)
    e = values[0]
    out[0] = e
    for i in range(1, n):
        e = values[i] * a + e * (1 - a)
        out[i] = e
    return out


def _filled(vals):
    return [v if v is not None else 0.0 for v in vals]


def hma_series(values, length, mode="Hma"):
    n = len(values)
    if mode == "Hma":
        half = max(1, length // 2)
        sq = max(1, round(length ** 0.5))
        wh = wma_series(values, half)
        wf = wma_series(values, length)
        diff = [(2 * wh[i] - wf[i]) if (wh[i] is not None and wf[i] is not None) else None for i in range(n)]
        hull = wma_series(_filled(diff), sq)
        warmup = (length - 1) + (sq - 1)
    elif mode == "Ehma":
        half = max(1, length // 2)
        sq = max(1, round(length ** 0.5))
        eh = ema_series(values, half)
        ef = ema_series(values, length)
        diff = [(2 * eh[i] - ef[i]) for i in range(n)]
        hull = ema_series(diff, sq)
        warmup = length  # ema ha warm-up "morbido", margine prudente
    elif mode == "Thma":
        L = max(2, length // 2)   # THMA(src, len/2) come nello script Pine
        l3 = max(1, L // 3)
        l2 = max(1, L // 2)
        w3 = wma_series(values, l3)
        w2 = wma_series(values, l2)
        wL = wma_series(values, L)
        inner = [(3 * w3[i] - w2[i] - wL[i]) if (w3[i] is not None and w2[i] is not None and wL[i] is not None) else None for i in range(n)]
        hull = wma_series(_filled(inner), L)
        warmup = L + max(l3, l2, L) + 5
    else:
        raise ValueError(mode)
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


_CANDLE_CACHE = {}


def get_candles(tf):
    if tf not in _CANDLE_CACHE:
        candles, src = bt._fetch_real("XAUUSD", tf, 110000)
        atr = bt.atr_series(candles, 14)
        closes = [c["close"] for c in candles]
        _CANDLE_CACHE[tf] = (candles, atr, closes)
    return _CANDLE_CACHE[tf]


def run_config(tf, length, mode, use_filter=True, label=""):
    candles, atr, closes = get_candles(tf)
    n = len(candles)
    hull = hma_series(closes, length, mode)
    lb_er = LOOKBACK_ER[tf]

    trades = []
    up_prev = None
    start = max(length + 10, (lb_er + 50) if use_filter else 30)
    for i in range(start, n - 2):
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
        if use_filter:
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
                    exit_r = (sl - entry) / rd; break
                elif hi >= tp:
                    exit_r = (tp - entry) / rd; break
            else:
                if hi >= sl:
                    exit_r = (entry - sl) / rd; break
                elif lo <= tp:
                    exit_r = (entry - tp) / rd; break
        if exit_r is None:
            continue
        trades.append({"entry": entry, "risk_dist": rd, "raw_r": exit_r})

    print(f"--- {label} TF={tf} len={length} mode={mode} filter={'ON' if use_filter else 'OFF'}: {len(trades)} trade ---", flush=True)
    for preset in ("retail_standard", "ecn"):
        net = []
        for t in trades:
            cost = bt.scaled_cost_for_price(preset, t["entry"])
            cost_r = min((cost["spread_price"] + cost["slippage_price"]) / t["risk_dist"], bt.MAX_COST_R_PER_TRADE)
            net.append(t["raw_r"] - cost_r)
        wf = walk_forward(net)
        wf_str = " | ".join(f"{p:.2f}" for _, p in wf) if wf else "n/a"
        n_pos = sum(1 for _, p in (wf or []) if p >= 1.0)
        print(f"  {preset:16s} aggPF={pf(net):.2f} sumR={sum(net):+7.1f} win>=1:{n_pos}/{len(wf) if wf else 0}  [{wf_str}]", flush=True)


def main():
    print("=== ASSE 1: LENGTH (mode=Hma, filtro ON) ===", flush=True)
    for tf in ("4h", "1h"):
        for length in (21, 34, 55, 89, 144, 200):
            run_config(tf, length, "Hma", True, "LEN")

    print("\n=== ASSE 2: MODE (length=55 e 200, filtro ON) ===", flush=True)
    for tf in ("4h", "1h"):
        for length in (55, 200):
            for mode in ("Ehma", "Thma"):
                run_config(tf, length, mode, True, "MODE")

    print("\n=== ABLATION: senza filtro di regime (length=55/Hma) ===", flush=True)
    for tf in ("4h", "1h"):
        run_config(tf, 55, "Hma", False, "NOFILTER")


if __name__ == "__main__":
    main()
