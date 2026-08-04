#!/usr/bin/env python3
"""
04/08 (11) - "abbiamo bisogno di una finestra piu' ampia": scarica storico
tick XAUUSD via Dukascopy (gratuito, senza API key, anni di storico) e lo
aggrega a candele M15 - la risoluzione piu' fine che serve al motore, da
cui si ricampiona H1/H4/M30 (stesso schema di _resample_4h in backtest.py).
Yahoo limita H1/H4 a ~1.74 anni osservati; qui puntiamo a partire da
2023-01-01 (verificato raggiungibile, 2022 fallisce sistematicamente con
timeout SSL sull'handshake - possibile limite lato CDN Dukascopy per
archivi piu' vecchi, non approfondito oltre) fino a oggi.

Ogni giorno scaricato resta in cache locale su disco
(server/data_cache/dukascopy/XAUUSD/*.json) - uno script interrotto e
rilanciato riprende da dove era arrivato, non ri-scarica nulla.

Esegui dalla root del repo (puo' richiedere ore, pensato per background):
python3 server/research_scripts/fetch_dukascopy_history.py
"""
import json
import os
import sys
import time
from datetime import datetime, timezone

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import dukascopy_fetch as dk

SYMBOL = "XAUUSD"
START = datetime(2023, 1, 1, tzinfo=timezone.utc)
END = datetime.now(timezone.utc)
TF_MINUTES = 15
OUT_PATH = os.path.join(os.path.dirname(__file__), "..", "data_cache", "dukascopy_xauusd_m15.json")


def main():
    t0 = time.time()
    print(f"[fetch] {SYMBOL} {START.date()} -> {END.date()}, TF={TF_MINUTES}m", flush=True)
    ohlc = dk.fetch_range_ohlc(SYMBOL, START, END, TF_MINUTES, max_workers=8, progress_every=10)
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(ohlc, f)
    print(f"[fetch] fatto: {len(ohlc)} candele M15 scritte in {OUT_PATH} "
          f"({time.time()-t0:.0f}s totali)", flush=True)


if __name__ == "__main__":
    main()
