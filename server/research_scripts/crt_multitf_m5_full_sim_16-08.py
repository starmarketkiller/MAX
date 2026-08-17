#!/usr/bin/env python3
"""
16/08 (2) - completa crt_multitf_m5_trigger_16-08.py: non solo la
struttura risk/reward, ma la SIMULAZIONE VERA candela-per-candela su M5
dal punto di entry fino a SL/TP, con costi reali applicati in R. Confronta
3 varianti (A baseline HTF, B entry M5 precisa senza floor, C entry M5 con
floor 0.15xATR) sullo stesso campione di segnali, stesso periodo
(2021-11-29 -> 2026-08-14, unico intervallo con M5 disponibile).
"""
import sys
import os
import json
import bisect
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import backtest as bt

SYMBOL = "XAUUSD"
HTF = "4h"
BARS = 110000
MAX_HOLD_M5 = 12 * 24 * 5  # 5 giorni di barre M5 (288/giorno), tetto di sicurezza

with open(os.path.join(os.path.dirname(__file__), "..", "data_cache_m5",
                        "dukascopy_xauusd_m5.json"), encoding="utf-8") as f:
    M5 = json.load(f)
M5_TIMES = [c["time"] for c in M5]


def _m5_idx_from(t_str):
    return bisect.bisect_left(M5_TIMES, t_str)


def simulate(label, candles, atr, sig, sl_a, tp_a, start_idx, n, cost_spread, cost_slip, floor_atr_mult=None):
    trades = []
    for i in range(start_idx, n):
        if sig[i] == 0:
            continue
        direction = sig[i]
        a = atr[i]
        if not a:
            continue
        t0 = candles[i]["time"]
        t1 = candles[i + 1]["time"] if i + 1 < n else None
        if t1 is None:
            continue
        j0, j1 = _m5_idx_from(t0), _m5_idx_from(t1)
        m5_win = M5[j0:j1]
        if not m5_win:
            continue

        if label == "A_baseline":
            entry = candles[i]["close"]
            sl = sl_a[i]
            if sl is None:
                continue
            risk_dist = abs(entry - sl)
            entry_m5_idx = j0  # entra all'inizio della barra HTF (close della precedente)
        else:
            if direction == 1:
                extreme = min(c["low"] for c in m5_win)
                extreme_pos = min(range(len(m5_win)), key=lambda k: m5_win[k]["low"])
            else:
                extreme = max(c["high"] for c in m5_win)
                extreme_pos = max(range(len(m5_win)), key=lambda k: m5_win[k]["high"])
            entry = extreme
            buf = 0.05 * a
            sl = extreme - buf if direction == 1 else extreme + buf
            risk_dist = abs(entry - sl)
            if floor_atr_mult:
                floor_dist = floor_atr_mult * a
                if risk_dist < floor_dist:
                    sl = entry - floor_dist if direction == 1 else entry + floor_dist
                    risk_dist = floor_dist
            entry_m5_idx = j0 + extreme_pos  # entra nel momento in cui M5 tocca l'estremo

        tp = tp_a[i]
        if tp is None or risk_dist <= 0:
            continue

        # cammina avanti su M5 da entry_m5_idx finche' non tocca SL o TP
        exit_r = None
        k_end = min(entry_m5_idx + MAX_HOLD_M5, len(M5) - 1)
        for k in range(entry_m5_idx + 1, k_end + 1):
            hi, lo = M5[k]["high"], M5[k]["low"]
            if direction == 1:
                if lo <= sl:
                    exit_r = -1.0
                    break
                elif hi >= tp:
                    exit_r = (tp - entry) / risk_dist
                    break
            else:
                if hi >= sl:
                    exit_r = -1.0
                    break
                elif lo <= tp:
                    exit_r = (entry - tp) / risk_dist
                    break
        if exit_r is None:
            continue  # non chiuso entro il tetto, scarta (raro, cauto)

        cost_r = min((cost_spread + cost_slip) / risk_dist, bt.MAX_COST_R_PER_TRADE)
        net_r = exit_r - cost_r
        trades.append(net_r)
    return trades


def pf_stats(trades):
    if not trades:
        return None, 0, None
    wins = sum(t for t in trades if t > 0)
    losses = -sum(t for t in trades if t < 0)
    pf = (wins / losses) if losses > 0 else None
    # DD semplice sulla curva cumulata in R
    eq, peak, dd = 0.0, 0.0, 0.0
    for t in trades:
        eq += t
        peak = max(peak, eq)
        dd = max(dd, peak - eq)
    return pf, len(trades), dd


def main():
    candles, src = bt._fetch_real(SYMBOL, HTF, BARS)
    atr = bt.atr_series(candles, 14)
    n = len(candles)
    start_idx = next((i for i, c in enumerate(candles) if c["time"] >= "2021-11-30"), 0)
    sig, sl_a, tp_a = bt._crt_series(candles, atr, min_stop_atr=0.3, mode="widen")

    for preset in ["retail_standard", "ecn"]:
        c = bt.COST_PRESETS[preset]
        print(f"\n=== costi {preset} (spread {c['spread_price']} + slip {c['slippage_price']}) ===", flush=True)
        for label, floor in (("A_baseline", None), ("B_m5_precise", None), ("C_m5_floor", 0.15)):
            trades = simulate(label, candles, atr, sig, sl_a, tp_a, start_idx, n,
                               c["spread_price"], c["slippage_price"], floor_atr_mult=floor)
            pf, cnt, dd = pf_stats(trades)
            print(f"  {label:16s} n={cnt:5d}  PF={pf}  DD(R cumulato)={dd}", flush=True)


if __name__ == "__main__":
    main()
