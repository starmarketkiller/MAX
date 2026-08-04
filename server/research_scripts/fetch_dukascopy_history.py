#!/usr/bin/env python3
"""
04/08 (11-12) - "abbiamo bisogno di una finestra piu' ampia" / "scarica
piu' storico possibile": scarica storico tick XAUUSD via Dukascopy
(gratuito, senza API key) e lo aggrega a candele M15 - la risoluzione
piu' fine che serve al motore, da cui si ricampiona H1/H4/M30 (stesso
schema di _resample_4h in backtest.py). Yahoo limita H1/H4 a ~1.74 anni
osservati.

Punta a 10 anni (2016-01-01 -> oggi, stessa profondita' di Yahoo su
D1/W1) per coprire piu' regimi di mercato reali (COVID, ciclo rialzi
tassi 2022, ecc.) - non solo "piu' dati", dati che attraversano regimi
diversi, l'unico modo per sapere se un edge e' reale o un artefatto del
singolo periodo (vedi lezioni #10/#18 sul confondimento di regime).

Verificato (04/08): non esiste un muro netto per anno - 2010/2015/2020
hanno risposto, 2018/2021/2023 hanno avuto errori 503/timeout
transitori sulla stessa ora testata. Non e' un limite dei dati, e' rete
instabile via il proxy di questo ambiente - per questo il fetch procede
giorno per giorno con cache persistente e tollera ore/giorni persi
(dukascopy_fetch.fetch_day_ticks logga e continua, non solleva piu').

A differenza della versione precedente (chiamava fetch_range_ohlc in un
colpo solo, senza risultati fino alla fine), qui il loop e' manuale e
scrive uno snapshot incrementale ogni SNAPSHOT_EVERY giorni - un fetch
di questa durata (stimate 15-20+ ore per 10 anni) puo' essere letto o
interrotto in qualunque momento senza perdere il lavoro fatto finora.

Ogni giorno scaricato resta anche in cache locale separata su disco
(server/data_cache/dukascopy/XAUUSD/*.json) - un rilancio riprende da
dove era arrivato, non ri-scarica nulla.

Esegui dalla root del repo (pensato per girare in background per ore):
python3 server/research_scripts/fetch_dukascopy_history.py
"""
import json
import os
import sys
import time
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import dukascopy_fetch as dk

SYMBOL = "XAUUSD"
START = datetime(2016, 1, 1, tzinfo=timezone.utc)
END = datetime.now(timezone.utc)
TF_MINUTES = 15
SNAPSHOT_EVERY = 20   # giorni fra uno snapshot incrementale e il successivo
OUT_PATH = os.path.join(os.path.dirname(__file__), "..", "data_cache", "dukascopy_xauusd_m15.json")
PROGRESS_PATH = os.path.join(os.path.dirname(__file__), "..", "data_cache", "dukascopy_fetch_progress.json")


def main():
    t0 = time.time()
    n_days = (END - START).days + 1
    print(f"[fetch] {SYMBOL} {START.date()} -> {END.date()} ({n_days} giorni), "
          f"TF={TF_MINUTES}m, snapshot ogni {SNAPSHOT_EVERY} giorni", flush=True)

    all_ticks = []
    day = START
    i = 0
    days_with_data = 0
    while day <= END:
        i += 1
        try:
            ticks = dk.fetch_day_ticks(SYMBOL, day, max_workers=10)
            if ticks:
                days_with_data += 1
            all_ticks.extend(ticks)
        except Exception as e:
            print(f"[fetch] giorno perso {day.date()}: {str(e)[:100]}", flush=True)
        if i % SNAPSHOT_EVERY == 0 or day >= END:
            ohlc = dk.ticks_to_ohlc(all_ticks, TF_MINUTES)
            with open(OUT_PATH, "w", encoding="utf-8") as f:
                json.dump(ohlc, f)
            with open(PROGRESS_PATH, "w", encoding="utf-8") as f:
                json.dump({
                    "last_day_done": day.strftime("%Y-%m-%d"),
                    "days_done": i, "days_total": n_days,
                    "days_with_data": days_with_data,
                    "m15_candles_so_far": len(ohlc),
                    "elapsed_s": round(time.time() - t0),
                }, f, indent=2)
            print(f"[fetch] {i}/{n_days} giorni ({day.date()}), {days_with_data} con dati, "
                  f"{len(ohlc)} candele M15 finora, {time.time()-t0:.0f}s trascorsi", flush=True)
        day += timedelta(days=1)

    print(f"[fetch] completato: {len(all_ticks)} tick totali su {days_with_data} giorni con dati "
          f"({time.time()-t0:.0f}s totali)", flush=True)


if __name__ == "__main__":
    main()
