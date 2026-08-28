#!/usr/bin/env python3
"""
24/08 (8) - richiesta esplicita dell'utente: uscire dallo schema "una
strategia = una sola logica", provare CONFLUENZE tra strategie/indicatori
diversi (i suoi esempi: MACD come conferma per ADX_RSI, zone di
Fibonacci per i pullback, Elliott per una lettura a onde) - con
l'avvertenza esplicita che un test puo' aiutare 10 strategie e
danneggiarne 20 altre, va verificato caso per caso, non assunto.

Due test qui (Elliott escluso per ora - richiede una logica di conteggio
onde molto piu' soggettiva/complessa da codificare bene in poco tempo,
lasciato come idea aperta, non abbandonata):

1. ADX_RSI + conferma MACD (l'esempio esplicito dell'utente): il segnale
   passa solo se l'istogramma MACD (linea - segnale) e' nella stessa
   direzione del trade al momento del segnale - un filtro di momentum
   aggiuntivo, non un secondo trigger.
2. EMA_PULLBACK + zona di ritracciamento Fibonacci (l'altro esempio
   esplicito): il pullback e' valido solo se il prezzo, al momento del
   segnale, e' rientrato nella "golden zone" (38.2%-61.8%) dello swing
   recente (max/min a N barre) - non un ritracciamento qualsiasi, uno
   strutturalmente significativo secondo la teoria della fonte.

Base line: stessa ricetta oggi validata (ER>=0.045 + floor ATR 30°
percentile mobile), stop ATR 1.5/4.0, walk-forward 5 finestre + verifica
due meta', costi retail/ECN - per poter confrontare onestamente "con
confluenza" vs "senza", stessa base per entrambi.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import backtest as bt

LOOKBACK_ER = {"4h": 1000, "1h": 4000}
THR_ER = 0.045
FLOOR_PCTL = 0.3
MAX_HOLD = 200
SL_MULT, TP_MULT = 1.5, 4.0


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
            net.append(t["raw_r"] - cost_r)
        wf = walk_forward(net)
        wf_str = " | ".join(f"{p:.2f}" for _, p in wf) if wf else "n/a"
        n_pos = sum(1 for _, p in (wf or []) if p >= 1.0)
        mid = len(net) // 2
        h1, h2 = net[:mid], net[mid:]
        print(f"  {preset:16s} aggPF={pf(net):.2f} sumR={sum(net):+7.1f} win>=1:{n_pos}/{len(wf) if wf else 0}"
              f"  meta1={pf(h1):.2f}/meta2={pf(h2):.2f}  [{wf_str}]", flush=True)


def collect(tf, strat_name, entry_gate=None):
    """entry_gate(candles, ind, i, sig) -> bool. None = nessun filtro extra
    (baseline pura, per confronto)."""
    candles, src = bt._fetch_real("XAUUSD", tf, 110000)
    ind = bt._prep(candles)
    atr, closes = ind["atr"], ind["close"]
    n = len(candles)
    lb_er = LOOKBACK_ER[tf]
    sig_fn = bt.STRATEGIES[strat_name]

    atr_hist, trades = [], []
    for i in range(max(1500, lb_er + 50), n - 2):
        a = atr[i]
        if a:
            atr_hist.append(a)
        sig = sig_fn(candles, ind, i)
        if sig == 0 or not a:
            continue
        e = efficiency_ratio(closes, i, lb_er)
        if e is None or e < THR_ER:
            continue
        if len(atr_hist) < 500:
            continue
        w = sorted(atr_hist[-2000:])
        floor = w[min(int(FLOOR_PCTL * len(w)), len(w) - 1)]
        if a < floor:
            continue
        if entry_gate is not None and not entry_gate(candles, ind, i, sig):
            continue
        entry = candles[i + 1]["open"]
        sl = entry - sig * SL_MULT * a
        tp = entry + sig * TP_MULT * a
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
        trades.append({"entry": entry, "risk_dist": rd, "raw_r": exit_r})
    return trades


# ---------- Test A: ADX_RSI + conferma MACD ----------
def gate_macd_aligned(candles, ind, i, sig):
    macd_line = ind["macd_line"][i]
    macd_sig = ind["macd_signal"][i]
    if macd_line is None or macd_sig is None:
        return False
    hist = macd_line - macd_sig
    return (hist > 0) if sig == 1 else (hist < 0)


def gate_macd_aligned_strict(candles, ind, i, sig):
    """Variante piu' severa: istogramma allineato E sopra/sotto zero (non
    solo istogramma>0, anche macd_line stessa dalla parte giusta dello zero)."""
    macd_line = ind["macd_line"][i]
    macd_sig = ind["macd_signal"][i]
    if macd_line is None or macd_sig is None:
        return False
    hist = macd_line - macd_sig
    aligned = (hist > 0) if sig == 1 else (hist < 0)
    zero_side = (macd_line > 0) if sig == 1 else (macd_line < 0)
    return aligned and zero_side


# ---------- Test B: EMA_PULLBACK + zona Fibonacci ----------
FIB_SWING_BARS = 50


def gate_fib_zone(candles, ind, i, sig):
    window = candles[max(0, i - FIB_SWING_BARS):i + 1]
    if len(window) < 10:
        return False
    swing_hi = max(c["high"] for c in window)
    swing_lo = min(c["low"] for c in window)
    rng = swing_hi - swing_lo
    if rng <= 0:
        return False
    price = candles[i]["close"]
    # ritracciamento misurato dall'estremo piu' recente in direzione del trade:
    # per un BUY (pullback in un uptrend) ci si aspetta un rientro da swing_hi
    # verso il basso; per un SELL, da swing_lo verso l'alto.
    if sig == 1:
        retrace = (swing_hi - price) / rng
    else:
        retrace = (price - swing_lo) / rng
    return 0.382 <= retrace <= 0.618


def main():
    print("=== TEST A: ADX_RSI + conferma MACD (4h) ===", flush=True)
    report("ADX_RSI baseline (nessuna conferma)", collect("4h", "ADX_RSI", None))
    report("ADX_RSI + MACD istogramma allineato", collect("4h", "ADX_RSI", gate_macd_aligned))
    report("ADX_RSI + MACD allineato E stesso lato dello zero", collect("4h", "ADX_RSI", gate_macd_aligned_strict))

    print("\n=== TEST A bis: stessa conferma MACD su SAR_FLIP e DONCHIAN_TURTLE (per vedere se generalizza) ===", flush=True)
    for name in ("SAR_FLIP", "DONCHIAN_TURTLE"):
        report(f"{name} baseline", collect("4h", name, None))
        report(f"{name} + MACD istogramma allineato", collect("4h", name, gate_macd_aligned))

    print("\n=== TEST B: EMA_PULLBACK + zona Fibonacci 38.2-61.8% (4h) ===", flush=True)
    report("EMA_PULLBACK baseline (nessuna zona)", collect("4h", "EMA_PULLBACK", None))
    report("EMA_PULLBACK + zona Fib golden", collect("4h", "EMA_PULLBACK", gate_fib_zone))

    print("\n=== TEST B bis: stessa zona Fib su DONCHIAN_TURTLE e SAR_FLIP (per vedere se generalizza) ===", flush=True)
    for name in ("DONCHIAN_TURTLE", "SAR_FLIP"):
        report(f"{name} + zona Fib golden", collect("4h", name, gate_fib_zone))


if __name__ == "__main__":
    main()
