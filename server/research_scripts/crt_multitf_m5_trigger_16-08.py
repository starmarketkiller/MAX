#!/usr/bin/env python3
"""
16/08 - CRT multi-timeframe: range/sweep rilevato su 4h (come la versione
attuale in nucleo, ora disattivata), ma l'ENTRY rifinita sui dati M5 reali
dentro la barra 4h di entry, invece di entrare al close della 4h. Idea
dell'utente: "si trova l'ingresso in tf grande e si entra su un trigger
m1/m5 rimanendo coerente con l'analisi" - stop molto piu' preciso (M5),
target invariato (lato opposto del range 4h, largo).

Dati M5 disponibili solo da 2021-11-29 (fetch non completato, container
riavviato) - non copre la finestra 0 del walk-forward (2019-2020), ma
copre abbastanza delle finestre 2-4 per un primo test onesto.

Confronta 3 varianti sullo stesso campione di segnali 4h:
  A) baseline attuale: entry al close della barra 4h successiva al sweep,
     SL = wick della barra di sweep (floor MinStopATR 0.3 attivo)
  B) multi-TF: entry al minimo/massimo M5 reale raggiunto dentro la barra
     4h di entry (assume limit order riempito li'), SL = quel minimo/
     massimo M5 - piccolo buffer, TP invariato (lato opposto range 4h)
  C) come B ma SL con floor minimo (0.15xATR) per evitare stop M5 troppo
     microscopici
"""
import sys
import os
import json
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import backtest as bt
from datetime import datetime, timedelta

SYMBOL = "XAUUSD"
HTF = "4h"
BARS = 110000

with open(os.path.join(os.path.dirname(__file__), "..", "data_cache_m5",
                        "dukascopy_xauusd_m5.json"), encoding="utf-8") as f:
    M5 = json.load(f)
M5_BY_TIME = {c["time"]: c for c in M5}
M5_START = datetime.strptime(M5[0]["time"], "%Y-%m-%d %H:%M")


def _m5_window(t0_str, t1_str):
    """Candele M5 con time in [t0, t1) - ricerca lineare su indice ordinato
    via binary-ish range scan (M5 e' ordinato per costruzione)."""
    out = []
    for c in M5:
        if t0_str <= c["time"] < t1_str:
            out.append(c)
        elif c["time"] >= t1_str:
            break
    return out


def main():
    candles, src = bt._fetch_real(SYMBOL, HTF, BARS)
    atr = bt.atr_series(candles, 14)
    n = len(candles)

    # solo il sotto-periodo dove abbiamo M5 (2021-11-29 in poi)
    start_idx = next((i for i, c in enumerate(candles) if c["time"] >= "2021-11-30"), 0)
    print(f"[crt-m5] HTF={HTF} bars totali={n}, uso da idx={start_idx} "
          f"({candles[start_idx]['time']}) - copertura M5 disponibile", flush=True)

    sig, sl_a, tp_a = bt._crt_series(candles, atr, min_stop_atr=0.3, mode="widen")

    results = {"A_baseline": [], "B_m5_precise": [], "C_m5_floor": []}
    n_signals = 0
    n_no_m5 = 0

    for i in range(start_idx, n):
        if sig[i] == 0:
            continue
        n_signals += 1
        direction = sig[i]
        entry_htf = candles[i]["close"]
        a = atr[i]
        if not a:
            continue

        # --- A) baseline: gia' abbiamo sl_a/tp_a da _crt_series ---
        risk_a = abs(entry_htf - sl_a[i]) if sl_a[i] is not None else None

        # --- finestra M5 della barra HTF di entry (i) ---
        t0 = candles[i]["time"]
        t1 = candles[i + 1]["time"] if i + 1 < n else None
        if t1 is None:
            continue
        m5_win = _m5_window(t0, t1)
        if not m5_win:
            n_no_m5 += 1
            continue

        if direction == 1:
            m5_extreme = min(c["low"] for c in m5_win)
        else:
            m5_extreme = max(c["high"] for c in m5_win)

        # --- B) entry al retest M5 dell'estremo, SL = estremo M5 (no floor) ---
        entry_b = m5_extreme
        buf = 0.05 * a
        sl_b = m5_extreme - buf if direction == 1 else m5_extreme + buf
        risk_b = abs(entry_b - sl_b)

        # --- C) come B ma con floor 0.15xATR sul rischio ---
        floor_dist = 0.15 * a
        if risk_b < floor_dist:
            sl_c = entry_b - floor_dist if direction == 1 else entry_b + floor_dist
        else:
            sl_c = sl_b
        risk_c = abs(entry_b - sl_c)

        tp = tp_a[i]  # target invariato: lato opposto del range 4h
        if tp is None:
            continue

        for label, entry, sl, risk in (
            ("A_baseline", entry_htf, sl_a[i], risk_a),
            ("B_m5_precise", entry_b, sl_b, risk_b),
            ("C_m5_floor", entry_b, sl_c, risk_c),
        ):
            if risk is None or risk <= 0:
                continue
            tp_dist = abs(tp - entry)
            r_potential = tp_dist / risk
            results[label].append({
                "i": i, "dir": direction, "entry": entry, "sl": sl, "tp": tp,
                "risk_dist": risk, "r_potential": r_potential,
            })

    print(f"[crt-m5] segnali HTF nel periodo: {n_signals}, senza M5 disponibile: {n_no_m5}", flush=True)
    for label, rows in results.items():
        if not rows:
            print(f"  {label}: nessun trade valido")
            continue
        risks = [r["risk_dist"] for r in rows]
        rpots = [r["r_potential"] for r in rows]
        print(f"  {label}: n={len(rows)}  risk_dist medio=${sum(risks)/len(risks):.3f}  "
              f"mediana=${sorted(risks)[len(risks)//2]:.3f}  "
              f"R-potenziale medio(TP/risk)={sum(rpots)/len(rpots):.2f}")


if __name__ == "__main__":
    main()
