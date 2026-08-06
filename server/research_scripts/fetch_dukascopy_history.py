#!/usr/bin/env python3
"""
06/08 - scarica storico tick XAUUSD via Dukascopy (gratuito, senza API key)
e lo aggrega a candele M15 - la risoluzione piu' fine che serve al motore,
da cui si ricampiona H1/H4/D1/W1 (stesso schema di _resample_4h in
backtest.py). Yahoo limita H1/H4 a ~1.74 anni osservati; TradingView piano
base ha uno storico intraday ancora piu' corto; MT5 Strategy Tester scarica
un simbolo/timeframe alla volta ed e' lento.

Punta a 10 anni (2016-01-01 -> oggi) per coprire piu' regimi di mercato
reali (COVID, ciclo rialzi tassi 2022, ecc.) - non solo "piu' dati", dati
che attraversano regimi diversi, l'unico modo per sapere se un edge e'
reale o un artefatto del singolo periodo.

DIFFERENZA dalla prima versione di questo script (fetch in avanti da
2016): qui si scarica **a ritroso da oggi**. Un fetch di questa portata
richiede ore (stimate 15-20+ per 10 anni pieni) e questo ambiente e' un
container effimero che puo' essere riciclato per inattivita' - se il
fetch si interrompe a meta', un ordine forward lascia lo storico PIU'
recente (2022-2026, il piu' rilevante per le strategie attive oggi) per
ultimo, cioe' proprio quello che rischia di non arrivare mai. L'ordine a
ritroso garantisce che qualunque snapshot parziale copra sempre la
finestra piu' recente e utile per prima, e si estenda all'indietro (verso
regimi piu' vecchi) man mano che il budget di tempo lo consente.

Parallelismo a due livelli: dentro un giorno (24 file orari, gestito da
dukascopy_fetch.fetch_day_ticks, default 12 thread) e fra giorni diversi
(DAY_WORKERS qui sotto). Misurato empiricamente il 06/08: DAY_WORKERS=3
(36 richieste concorrenti totali) faceva fallire il 25% delle ore dopo
tutti i retry - non rallentamento, PERDITA di dati (ore mancanti nella
candela risultante, silenziosa se non si guarda il log). DAY_WORKERS=1
(solo i 12 thread interni al giorno, la stessa configurazione del test
a giorno singolo che non ha mai avuto un errore) e' piu' lento ma
completo - qui la correttezza dei dati vale piu' della velocita', dato
che serviranno a decidere il rischio reale.

Ogni giorno scaricato resta in cache locale su disco
(server/data_cache/dukascopy/XAUUSD/*.json) - un rilancio non ri-scarica
mai un giorno gia' presente, quindi lo script e' idempotente e riprendibile
in qualunque momento, in qualunque ordine.

Esegui dalla root del repo (pensato per girare in background per ore):
python3 server/research_scripts/fetch_dukascopy_history.py
"""
import json
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import dukascopy_fetch as dk

SYMBOL = "XAUUSD"
END = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
START = END - timedelta(days=365 * 10)
TF_MINUTES = 15
DAY_WORKERS = 1           # giorni scaricati in parallelo (ognuno con 12 thread interni sulle 24 ore) - vedi nota sopra
SNAPSHOT_EVERY = 10       # giorni fra uno snapshot incrementale e il successivo
_DATA_ROOT = dk.data_cache_root()
OUT_PATH = os.path.join(_DATA_ROOT, "dukascopy_xauusd_m15.json")
PROGRESS_PATH = os.path.join(_DATA_ROOT, "dukascopy_fetch_progress.json")
# 06/08 - il disco persistente su Render e' 1GB (render.yaml, condiviso col
# database), la cache grezza per-giorno (~3.4MB/giorno) su 10 anni
# supererebbe da sola quel budget (~9GB). Lo snapshot M15 aggregato (questo
# OUT_PATH, solo OHLC, non i tick) e' la fonte durevole - i file grezzi per-
# giorno servono solo a rendere ripetibile un fetch interrotto, non oltre.
# Tenerne solo gli ultimi RAW_KEEP_DAYS (i giorni non ancora coperti da uno
# snapshot scritto) mantiene l'uso disco costante invece di crescere per
# sempre con lo storico.
RAW_KEEP_DAYS = SNAPSHOT_EVERY * 2


def _day_range_desc(start: datetime, end: datetime):
    d = end
    while d >= start:
        yield d
        d -= timedelta(days=1)


def _prune_raw_cache(oldest_frontier: datetime):
    """Elimina la cache grezza per-giorno piu' vecchia della finestra di
    sicurezza RAW_KEEP_DAYS oltre il fronte di avanzamento corrente - quei
    giorni sono gia' scritti nello snapshot durevole (OUT_PATH), tenerli
    anche come file grezzi individuali servirebbe solo a riprendere un
    fetch interrotto, non a ricostruire lo storico (quello lo fa lo
    snapshot). Vedi nota RAW_KEEP_DAYS sopra sul budget disco."""
    cutoff = oldest_frontier + timedelta(days=RAW_KEEP_DAYS)
    day_dir = os.path.join(dk.CACHE_DIR, SYMBOL)
    if not os.path.isdir(day_dir):
        return
    for fname in os.listdir(day_dir):
        if not fname.endswith(".json"):
            continue
        try:
            fday = datetime.strptime(fname[:-5], "%Y-%m-%d").replace(tzinfo=timezone.utc)
        except ValueError:
            continue
        if fday > cutoff:
            try:
                os.remove(os.path.join(day_dir, fname))
            except OSError:
                pass


def main():
    t0 = time.time()
    days = list(_day_range_desc(START, END))
    n_days = len(days)
    print(f"[fetch] {SYMBOL} {END.date()} -> {START.date()} (a ritroso, {n_days} giorni), "
          f"TF={TF_MINUTES}m, {DAY_WORKERS} giorni in parallelo, "
          f"snapshot ogni {SNAPSHOT_EVERY} giorni", flush=True)

    ohlc_by_day = {}   # day.date() -> list[candle], cosi' il riordino finale e' deterministico
    days_with_data = 0
    oldest_done = END

    def _fetch_one(day):
        ticks = dk.fetch_day_ticks(SYMBOL, day, max_workers=12)
        return day, dk.ticks_to_ohlc(ticks, TF_MINUTES)

    i = 0
    with ThreadPoolExecutor(max_workers=DAY_WORKERS) as pool:
        futures = {pool.submit(_fetch_one, day): day for day in days}
        for fut in as_completed(futures):
            day = futures[fut]
            i += 1
            try:
                _, candles = fut.result()
            except Exception as e:
                print(f"[fetch] giorno perso {day.date()}: {str(e)[:120]}", flush=True)
                candles = []
            if candles:
                days_with_data += 1
                ohlc_by_day[day.date()] = candles
            if day < oldest_done:
                oldest_done = day

            if i % SNAPSHOT_EVERY == 0 or i == n_days:
                merged = []
                for d in sorted(ohlc_by_day):
                    merged.extend(ohlc_by_day[d])
                with open(OUT_PATH, "w", encoding="utf-8") as f:
                    json.dump(merged, f)
                with open(PROGRESS_PATH, "w", encoding="utf-8") as f:
                    json.dump({
                        "order": "recent_first",
                        "days_done": i, "days_total": n_days,
                        "days_with_data": days_with_data,
                        "oldest_day_covered": oldest_done.strftime("%Y-%m-%d"),
                        "newest_day_covered": END.strftime("%Y-%m-%d"),
                        "m15_candles_so_far": len(merged),
                        "elapsed_s": round(time.time() - t0),
                    }, f, indent=2)
                _prune_raw_cache(oldest_done)
                print(f"[fetch] {i}/{n_days} giorni, {days_with_data} con dati, "
                      f"copertura fino a {oldest_done.date()}, {len(merged)} candele M15, "
                      f"{time.time()-t0:.0f}s trascorsi", flush=True)

    print(f"[fetch] completato: {days_with_data} giorni con dati su {n_days} "
          f"({time.time()-t0:.0f}s totali)", flush=True)


if __name__ == "__main__":
    main()
