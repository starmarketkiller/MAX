#!/usr/bin/env python3
"""
16/08 (4) - richiesta esplicita dell'utente: "prova anche tutte le altre
strategie con lo stop [strutturale M5] come ti ho detto". Estende il
meccanismo scoperto oggi su SAR/MACD/LONDON_BO/FVG_CONT (stop = minimo/
massimo delle ultime `swing_bars` candele M5 PRIMA dell'apertura della
barra H1 di entrata, invece di un multiplo ATR) a un set ampio di
strategie di famiglie diverse, riusando bt.STRATEGIES[...] (le funzioni
sig_* gia' auditate riga per riga oggi nel controllo di coerenza sul
catalogo completo), non reimplementazioni.

Convenzione entry (lezione CRT open-vs-close): segnale confermato alla
CHIUSURA della barra H1 i, entrata all'APERTURA della barra i+1 - lo stop
M5 usa solo candele M5 con time < tempo di apertura della barra i+1,
quindi nessun lookahead. Target = entry +/- tp_mult * ATR(H1)[i] (ATR
noto al momento del segnale, nessun lookahead); tp_mult ripreso da
CONFIGS_4 di portfolio_regime_sim_16-08.py per le 4 gia' calibrate,
default 4.0 per le nuove (non tarato, primo tentativo dichiarato).

swing_bars=12 (~1h di M5) e floor_atr=0.3 sono valori di primo tentativo,
MAI tarati con uno sweep di robustezza (a differenza del tetto-euro di
oggi pomeriggio, validato su un plateau) - i risultati qui sono un primo
screening, non una conferma definitiva.
"""
import sys
import os
import json
import bisect
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import backtest as bt

with open(os.path.join(os.path.dirname(__file__), "..", "data_cache_m5",
                        "dukascopy_xauusd_m5.json"), encoding="utf-8") as f:
    M5 = json.load(f)
M5_TIMES = [c["time"] for c in M5]

SWING_BARS = 12
FLOOR_ATR = 0.3
LOOKBACK_ER = 4000
THR_ER = 0.045
MAX_HOLD_BARS = 200

# nome -> tp_mult (ATR). Le prime 4 riprendono CONFIGS_4 (portfolio_regime_sim_16-08.py).
STRAT_LIST = [
    ("SAR", 4.0), ("MACD", 8.0), ("LONDON_BO", 4.5), ("FVG_CONT", 6.0),
    ("EMA_PULLBACK", 4.0), ("RSI_DIV", 4.0), ("BOLLINGER", 4.0),
    ("ICHIMOKU", 4.0), ("ADX_RSI", 4.0), ("DONCHIAN_TURTLE", 4.0),
    ("LIQ_SWEEP", 4.0), ("TURTLE_SOUP_CHOCH", 4.0), ("STRUCT_REACT", 4.0),
    ("SH_BMS_RTO_V2", 4.0), ("ORDER_BLOCK", 4.0), ("IFVG", 4.0),
]


def efficiency_ratio(closes, i, lookback):
    if i < lookback:
        return None
    net = abs(closes[i] - closes[i - lookback])
    total = sum(abs(closes[k] - closes[k - 1]) for k in range(i - lookback + 1, i + 1))
    return net / total if total > 0 else None


def m5_idx_from(t_str):
    return bisect.bisect_left(M5_TIMES, t_str)


def m5_structural_stop(entry_time_str, direction, atr_val):
    j_entry = m5_idx_from(entry_time_str)
    j_start = max(0, j_entry - SWING_BARS)
    window = M5[j_start:j_entry]
    if len(window) < 3:
        return None
    if direction == 1:
        stop = min(c["low"] for c in window)
    else:
        stop = max(c["high"] for c in window)
    return stop


def collect_trades(name, tp_mult, candles, ind, atr, closes, n):
    sig_fn = bt.STRATEGIES[name]
    out = []
    n_geo_err = 0
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
        stop = m5_structural_stop(entry_time, sig, a)
        if stop is None:
            continue
        risk_dist = abs(entry - stop)
        floor = FLOOR_ATR * a
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
        out.append({
            "open_time": entry_time, "close_time": candles[exit_j]["time"],
            "entry": entry, "risk_dist": risk_dist, "raw_r": exit_r,
        })
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

    for name, tp_mult in STRAT_LIST:
        if name not in bt.STRATEGIES:
            print(f"{name}: non in STRATEGIES, salto", flush=True)
            continue
        raw_trades = collect_trades(name, tp_mult, candles, ind, atr, closes, n)
        if len(raw_trades) < 20:
            print(f"{name:18s} n={len(raw_trades):4d} -> troppo pochi trade, salto", flush=True)
            continue

        # controllo geometrico: nessuna uscita SL puo' avere raw_r > -1 (tolleranza fp)
        # e nessuna TP puo' avere raw_r < 0 dato come sono costruiti sopra - qui il
        # controllo reale e' su risk_dist>0 e coerenza segno gia' garantita dal codice,
        # quindi passiamo al controllo prezzo-lato (drenaggio in eur/costi sotto).

        print(f"\n== {name} (tp_mult={tp_mult}) == n_raw_trades={len(raw_trades)}", flush=True)
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
