#!/usr/bin/env python3
"""
16/08 (5) - risposta a "magari le altre hanno bisogno di un altro tipo di
stop": lo stop strutturale M5 (min/max ultime 12 candele M5) usato in
m5_structural_stop_broad_16-08.py e' generico, adatto a strategie di
trend/breakout (SAR/MACD/ICHIMOKU l'hanno confermato). Ma le strategie
"sweep" (LIQ_SWEEP, TURTLE_SOUP_CHOCH, SH_BMS_RTO_V2) e "rejection"
(STRUCT_REACT) hanno gia' un livello di invalidazione NATURALE nel loro
stesso codice (il wick dello sweep via _sweep_ext_at, la candela di
rejection stessa) - diverso, e piu' specifico alla tesi del trade, di un
generico "minimo/massimo dell'ultima ora". Anche RSI_DIV/BOLLINGER
(mean-reversion) hanno un riferimento naturale: l'estremo della barra che
ha generato il segnale, non uno swing a 12 barre.

Questo script ritesta le 6 bocciate di prima con lo stop NATIVO di
ciascuna (gia' scritto nel motore, riusato non reinventato) invece del
generico M5, stessa disciplina (entry a mercato all'apertura della barra
successiva, filtro di regime ER, walk-forward a 5 finestre, entrambi i
preset di costo).
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import backtest as bt

LOOKBACK_ER = 4000
THR_ER = 0.045
MAX_HOLD_BARS = 200
SWEEP_BUFFER_ATR = 0.5     # stessa convenzione di _turtle_soup_sl_tp
REJECT_BUFFER_ATR = 0.3
DIVERG_BUFFER_ATR = 0.3


def efficiency_ratio(closes, i, lookback):
    if i < lookback:
        return None
    net = abs(closes[i] - closes[i - lookback])
    total = sum(abs(closes[k] - closes[k - 1]) for k in range(i - lookback + 1, i + 1))
    return net / total if total > 0 else None


def stop_liq_sweep(c, ind, i, sig, entry, atr):
    sw = bt._sweep_ext_at(c, ind, i)
    if not sw:
        return None
    if sig == 1:
        if sw["refLow"] is None:
            return None
        return sw["refLow"] - SWEEP_BUFFER_ATR * atr
    if sw["refHigh"] is None:
        return None
    return sw["refHigh"] + SWEEP_BUFFER_ATR * atr


def stop_turtle_soup_choch(c, ind, i, sig, entry, atr):
    r = bt._turtle_soup_sl_tp(c, ind, i, sig, entry, atr)
    if r is None:
        return None
    return r[0]


def stop_shbms_v2(c, ind, i, sig, entry, atr):
    sl = ind["shbms_v2_sl"][i]
    return sl


def stop_struct_react(c, ind, i, sig, entry, atr):
    cur = c[i]
    if sig == 1:
        return cur["low"] - REJECT_BUFFER_ATR * atr
    return cur["high"] + REJECT_BUFFER_ATR * atr


def stop_rsi_div(c, ind, i, sig, entry, atr):
    l1, l8 = c[i]["low"], c[i - 7]["low"]
    h1, h8 = c[i]["high"], c[i - 7]["high"]
    if sig == 1:
        return min(l1, l8) - DIVERG_BUFFER_ATR * atr
    return max(h1, h8) + DIVERG_BUFFER_ATR * atr


def stop_bollinger(c, ind, i, sig, entry, atr):
    # riferimento naturale: la barra di touch (i-1), non uno swing a 12 barre
    prev = c[i - 1]
    if sig == 1:
        return min(prev["low"], c[i]["low"]) - DIVERG_BUFFER_ATR * atr
    return max(prev["high"], c[i]["high"]) + DIVERG_BUFFER_ATR * atr


# nome -> (tp_mult, funzione stop nativo)
STRAT_LIST = [
    ("LIQ_SWEEP", 4.0, stop_liq_sweep),
    ("TURTLE_SOUP_CHOCH", 4.0, stop_turtle_soup_choch),
    ("SH_BMS_RTO_V2", 4.0, stop_shbms_v2),
    ("STRUCT_REACT", 4.0, stop_struct_react),
    ("RSI_DIV", 4.0, stop_rsi_div),
    ("BOLLINGER", 4.0, stop_bollinger),
]


def collect_trades(name, tp_mult, stop_fn, candles, ind, atr, closes, n):
    sig_fn = bt.STRATEGIES[name]
    out = []
    for i in range(max(1500, LOOKBACK_ER + 50), n - 2):
        sig = sig_fn(candles, ind, i)
        if sig == 0:
            continue
        er = efficiency_ratio(closes, i, LOOKBACK_ER)
        if er is None or er < THR_ER:
            continue
        a = atr[i]
        if not a:
            continue
        entry_time = candles[i + 1]["time"]
        entry = candles[i + 1]["open"]
        stop = stop_fn(candles, ind, i, sig, entry, a)
        if stop is None:
            continue
        risk_dist = abs(entry - stop)
        floor = 0.3 * a
        if risk_dist < floor:
            risk_dist = floor
        if risk_dist <= 0:
            continue
        tp = entry + sig * tp_mult * a
        exit_r = None
        exit_j = None
        for j in range(i + 2, min(i + 2 + MAX_HOLD_BARS, n)):
            hi, lo = candles[j]["high"], candles[j]["low"]
            if sig == 1:
                sl_level = entry - risk_dist
                if lo <= sl_level:
                    exit_r = -1.0
                    exit_j = j
                    break
                elif hi >= tp:
                    exit_r = (tp - entry) / risk_dist
                    exit_j = j
                    break
            else:
                sl_level = entry + risk_dist
                if hi >= sl_level:
                    exit_r = -1.0
                    exit_j = j
                    break
                elif lo <= tp:
                    exit_r = (entry - tp) / risk_dist
                    exit_j = j
                    break
        if exit_r is None:
            continue
        out.append({"entry": entry, "risk_dist": risk_dist, "raw_r": exit_r})
    return out


def pf(trades):
    g = sum(t for t in trades if t > 0)
    l = -sum(t for t in trades if t < 0)
    if l == 0:
        return float("inf") if g > 0 else 0.0
    return g / l


def walk_forward(trades_net, n_windows=5):
    n = len(trades_net)
    if n < n_windows * 5:
        return None
    size = n // n_windows
    out = []
    for w in range(n_windows):
        seg = trades_net[w * size: (w + 1) * size] if w < n_windows - 1 else trades_net[w * size:]
        out.append((len(seg), pf(seg), sum(seg)))
    return out


def main():
    candles, src = bt._fetch_real("XAUUSD", "1h", 110000)
    print(f"H1 candles: {len(candles)} (fonte={src}) {candles[0]['time']} -> {candles[-1]['time']}", flush=True)
    ind = bt._prep(candles)
    atr = ind["atr"]
    closes = ind["close"]
    n = len(candles)

    for name, tp_mult, stop_fn in STRAT_LIST:
        raw_trades = collect_trades(name, tp_mult, stop_fn, candles, ind, atr, closes, n)
        if len(raw_trades) < 20:
            print(f"{name:18s} n={len(raw_trades):4d} -> troppo pochi trade, salto", flush=True)
            continue
        print(f"\n== {name} (stop nativo, tp_mult={tp_mult}) == n_raw_trades={len(raw_trades)}", flush=True)
        for preset in ("retail_standard", "ecn"):
            net_trades = []
            for t in raw_trades:
                cost = bt.scaled_cost_for_price(preset, t["entry"])
                cost_r = min((cost["spread_price"] + cost["slippage_price"]) / t["risk_dist"],
                             bt.MAX_COST_R_PER_TRADE)
                net_trades.append(t["raw_r"] - cost_r)
            agg_pf = pf(net_trades)
            wf = walk_forward(net_trades)
            wf_str = "n/a" if wf is None else " | ".join(f"n={c} PF={p:.2f} R={r:+.1f}" for c, p, r in wf)
            n_pos = sum(1 for _, p, _ in (wf or []) if p >= 1.0)
            print(f"  {preset:16s} aggPF={agg_pf:5.2f}  sumR={sum(net_trades):+7.1f}  "
                  f"finestre_PF>=1: {n_pos}/{len(wf) if wf else 0}   [{wf_str}]", flush=True)


if __name__ == "__main__":
    main()
