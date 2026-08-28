#!/usr/bin/env python3
"""
12/08 - esporta candele+trade_list per OGNI strategia del nucleo (16, incl.
THREE_BAR_DELIVERY_BREAK anche se non tradabile in MQL5 - vedi vault "Demo
Multi-Timeframe Pronta"), sulla configurazione LIVE attuale (non quella
ottimizzata trovata oggi - lo scopo qui e' vedere cosa succede ORA per capire
cosa migliorare, non celebrare un fix gia' trovato). Riusa live_config()/
parse_mql5_profiles() da exit_optimizer_all_strategies.py.

Include anche una serie M15 condivisa (stesso XAUUSD per tutte, quindi una
sola volta) limitata agli ultimi ~12 mesi della finestra OOS, per permettere
lo zoom di dettaglio richiesto esplicitamente dall'utente - M15 e' la
risoluzione piu' fine disponibile nella cache Dukascopy locale (non esiste
M5 vero scaricato).
"""
import sys
import os
import json

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import backtest as bt
from exit_optimizer_all_strategies import parse_mql5_profiles, live_config, TF_MAP

OOS_RANGE = (0.6, 1.0)
BARS = 110000

NUCLEO = [
    "BREAKOUT_ACC", "TURTLE_SOUP", "MACD", "LONDON_BO", "FVG_MIT", "LIQ_SWEEP",
    "AMD_CONT", "FVG_CONT", "TSI", "ADX_RSI", "SAR", "EMA_PULLBACK",
    "THREE_BAR_DELIVERY_BREAK", "LDN_REVERSAL", "AMD_REVERSAL", "CRT",
]


def slice_candles(symbol, tf, bar_range):
    candles, _src = bt._fetch_real(symbol, tf, BARS)
    n = len(candles)
    i0 = max(0, int(n * bar_range[0]))
    i1 = min(n, int(n * bar_range[1]))
    return candles[i0:i1]


def main():
    profiles, tfs, trailks = parse_mql5_profiles()
    out = {"symbol": "XAUUSD", "strategies": {}}

    for strat in NUCLEO:
        cfg = live_config(strat, profiles, tfs, trailks)
        tf = cfg["tf"]
        r = bt.run_backtest(symbol="XAUUSD", timeframe=tf, strategy=strat, strategies=[strat],
                             risk_pct=1.0, bars=BARS, bar_range=OOS_RANGE,
                             atr_sl=cfg["sl"], atr_tp=cfg["tp"], breakeven_r=cfg["be"],
                             htf_filter=cfg["htf"], trailing_atr=cfg["overlay_width"],
                             trailing_activate_atr=1.0)
        candles = slice_candles("XAUUSD", tf, OOS_RANGE)
        out["strategies"][strat] = {
            "tf": tf, "live_config": {k: cfg[k] for k in ("sl", "tp", "htf", "be", "overlay_width")},
            "pf": r.get("profit_factor"), "trades": r.get("trades"),
            "dd": r.get("max_dd_pct"), "win_rate": r.get("win_rate"),
            "candles": candles, "trade_list": r.get("trade_list", []),
        }
        print(f"{strat} ({tf}): pf={r.get('profit_factor')} n={r.get('trades')} "
              f"dd={r.get('max_dd_pct')}% candele={len(candles)}", flush=True)

    # M15 condivisa, ultimi ~12 mesi della finestra OOS (stessa per tutte le
    # strategie - risparmia spazio, e' lo stesso XAUUSD)
    m15_full = bt._load_dukascopy_m15("XAUUSD")
    if m15_full:
        cutoff_n = min(len(m15_full), 12 * 30 * 24 * 4)  # ~12 mesi di M15
        out["m15_recent"] = m15_full[-cutoff_n:]
        print(f"M15 condivisa: {len(out['m15_recent'])} candele (ultimi ~12 mesi)", flush=True)
    else:
        out["m15_recent"] = []
        print("M15 non disponibile (fonte dati non Dukascopy)", flush=True)

    out_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..",
                             "chart_export_nucleo_entries.json")
    out_path = os.path.abspath(out_path)
    with open(out_path, "w") as f:
        json.dump(out, f)
    print("wrote", out_path, os.path.getsize(out_path), "bytes")


if __name__ == "__main__":
    main()
