#!/usr/bin/env python3
"""Phase 7.9C - ricostruzione dello stream di eventi Python COMPLETO
(non solo i trade eseguiti) per BREAKOUT_ACC, simmetrico allo stream MT5
(NXS_BreakoutAccSignalDiagnostic.mq5): per ogni barra classifica
RAW_SIGNAL / BLOCKED_COOLDOWN / BLOCKED_HTF / SIGNAL_FIRE.

IMPORTANTE: NON modifica server/backtest.py. Importa ed esegue le
funzioni gia' esistenti e gia' verificate identiche a MQL5
(sig_breakout_acc, _breakout_acc_cooldown_series, _fetch_real, _prep) -
nessuna nuova logica di strategia, nessun nuovo Serious backtest (nessun
trade simulato, nessun P&L), solo lettura dello stream di segnali grezzo
sugli stessi identici dati/gate gia' usati da run_backtest(breakout_acc_
cooldown=True, htf_native_ema=True).
"""
import json
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "server"))
sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase6_6"))
import backtest as bt  # noqa: E402
from canonical_utils import save_json  # noqa: E402

WINDOW_START = "2019-02-03"
WINDOW_END = "2026-08-14"
COOLDOWN_BARS = 8
N_RANGE = 20


def build():
    candles, src = bt._fetch_real("XAUUSD", "1d", bars=3000)
    ind = bt._prep(candles)
    cooldown_series = bt._breakout_acc_cooldown_series(candles, ind, n=N_RANGE, cooldown_bars=COOLDOWN_BARS)

    events = []
    n_raw = n_blocked_cooldown = n_blocked_htf = n_fire = 0
    for i in range(len(candles)):
        raw_dir = bt.sig_breakout_acc(candles, ind, i, n=N_RANGE)
        if raw_dir == 0:
            continue
        n_raw += 1
        bar_time = candles[i]["time"]
        c1, c2 = candles[i]["close"], candles[i - 1]["close"]
        hh = max(x["high"] for x in candles[i - N_RANGE - 1:i - 1])
        ll = min(x["low"] for x in candles[i - N_RANGE - 1:i - 1])

        cooldown_ok = cooldown_series[i] == raw_dir
        if not cooldown_ok:
            events.append({
                "bar_time": bar_time, "raw_dir": raw_dir, "c1": c1, "c2": c2,
                "range_hi": hh, "range_lo": ll, "cooldown_state": "BLOCKED",
                "htf_state": None, "event": "BLOCKED_COOLDOWN",
            })
            n_blocked_cooldown += 1
            continue

        htf_ok = True
        e200_closed = ind["ema200"][i - 1] if i - 1 >= 0 else None
        if e200_closed and e200_closed > 0:
            if (raw_dir == 1 and c1 < e200_closed) or (raw_dir == -1 and c1 > e200_closed):
                htf_ok = False
        if not htf_ok:
            events.append({
                "bar_time": bar_time, "raw_dir": raw_dir, "c1": c1, "c2": c2,
                "range_hi": hh, "range_lo": ll, "cooldown_state": "OK",
                "htf_state": "BLOCKED", "event": "BLOCKED_HTF",
            })
            n_blocked_htf += 1
            continue

        events.append({
            "bar_time": bar_time, "raw_dir": raw_dir, "c1": c1, "c2": c2,
            "range_hi": hh, "range_lo": ll, "cooldown_state": "OK",
            "htf_state": "OK", "event": "SIGNAL_FIRE",
        })
        n_fire += 1

    summary = {
        "symbol": "XAUUSD", "data_source": src, "n_bars_loaded": len(candles),
        "window_requested": f"{WINDOW_START} to {WINDOW_END}",
        "window_actual": f"{candles[0]['time']} to {candles[-1]['time']}" if candles else None,
        "n_signals_raw_generated": n_raw, "n_blocked_cooldown": n_blocked_cooldown,
        "n_blocked_htf": n_blocked_htf, "n_final_fire": n_fire,
        "cooldown_bars": COOLDOWN_BARS, "range_n": N_RANGE,
        "engine": "server/backtest.py: sig_breakout_acc + _breakout_acc_cooldown_series + "
                 "htf_native_ema gate (righe ~4983-4988), importate SENZA modifiche.",
    }
    return events, summary


def main():
    out_dir = os.path.dirname(os.path.abspath(__file__))
    events, summary = build()
    save_json(os.path.join(out_dir, "raw_data", "python_breakoutacc_full_signal_stream.json"),
              {"summary": summary, "events": events})
    csv_path = os.path.join(out_dir, "raw_data", "python_breakoutacc_full_signal_stream.csv")
    with open(csv_path, "w", encoding="utf-8") as f:
        f.write("bar_time,raw_dir,c1,c2,range_hi,range_lo,cooldown_state,htf_state,event\n")
        for e in events:
            f.write(f"{e['bar_time']},{e['raw_dir']},{e['c1']},{e['c2']},{e['range_hi']},{e['range_lo']},"
                    f"{e['cooldown_state']},{e['htf_state'] or ''},{e['event']}\n")
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return events, summary


if __name__ == "__main__":
    main()
