#!/usr/bin/env python3
"""
14/08 - variante M5 di fetch_dukascopy_history.py, per testare strategie a
timeframe piu' basso di M15 (es. famiglia SCALP_*, gia' pensate per 15m ma
utile avere un M5 nativo invece di derivarlo). Stessa logica, stessa
disciplina (a ritroso da oggi, snapshot incrementale, resume idempotente) -
vedi quel file per i dettagli commentati per esteso.

Cache SEPARATA (NEXUS_DUKASCOPY_DIR) dalla M15 in corso, per non litigare
sugli stessi file grezzi per-giorno mentre entrambe girano in parallelo.

Esegui dalla root del repo:
python3 server/research_scripts/fetch_dukascopy_history_m5.py
"""
import json
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta, timezone

# cache separata dalla fetch M15 in corso - evita contesa sugli stessi file
# grezzi per-giorno se le due girano insieme.
os.environ.setdefault(
    "NEXUS_DUKASCOPY_DIR",
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data_cache_m5"))

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import dukascopy_fetch as dk

SYMBOL = "XAUUSD"
END = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
START = END - timedelta(days=365 * 10)
TF_MINUTES = 5
DAY_WORKERS = 1
SNAPSHOT_EVERY = 10
_DATA_ROOT = dk.data_cache_root()
OUT_PATH = os.path.join(_DATA_ROOT, "dukascopy_xauusd_m5.json")
PROGRESS_PATH = os.path.join(_DATA_ROOT, "dukascopy_fetch_progress_m5.json")
RAW_KEEP_DAYS = SNAPSHOT_EVERY * 2


def _day_range_desc(start, end):
    d = end
    while d >= start:
        yield d
        d -= timedelta(days=1)


def _prune_raw_cache(oldest_frontier):
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


def _load_existing_snapshot():
    if not os.path.exists(OUT_PATH):
        return {}
    try:
        with open(OUT_PATH, encoding="utf-8") as f:
            candles = json.load(f)
    except (OSError, json.JSONDecodeError):
        return {}
    by_day = {}
    for c in candles:
        try:
            d = datetime.strptime(c["time"][:10], "%Y-%m-%d").replace(tzinfo=timezone.utc)
        except (KeyError, ValueError):
            continue
        by_day.setdefault(d, []).append(c)
    return by_day


def main():
    t0 = time.time()
    all_days = list(_day_range_desc(START, END))
    n_days = len(all_days)

    ohlc_by_day = _load_existing_snapshot()
    already_done = len(ohlc_by_day)
    days = [d for d in all_days if d not in ohlc_by_day]

    print(f"[fetch-m5] {SYMBOL} {END.date()} -> {START.date()} (a ritroso, {n_days} giorni totali, "
          f"{already_done} gia' presenti dallo snapshot, {len(days)} da scaricare), "
          f"TF={TF_MINUTES}m, {DAY_WORKERS} giorni in parallelo, "
          f"snapshot ogni {SNAPSHOT_EVERY} giorni, cache={_DATA_ROOT}", flush=True)

    days_with_data = sum(1 for lst in ohlc_by_day.values() if lst)
    oldest_done = min(ohlc_by_day) if ohlc_by_day else END

    def _fetch_one(day):
        ticks = dk.fetch_day_ticks(SYMBOL, day, max_workers=12)
        return day, dk.ticks_to_ohlc(ticks, TF_MINUTES)

    i = already_done
    with ThreadPoolExecutor(max_workers=DAY_WORKERS) as pool:
        futures = {pool.submit(_fetch_one, day): day for day in days}
        for fut in as_completed(futures):
            day = futures[fut]
            i += 1
            try:
                _, candles = fut.result()
            except Exception as e:
                print(f"[fetch-m5] giorno perso {day.date()}: {str(e)[:120]}", flush=True)
                candles = []
            if candles:
                days_with_data += 1
                ohlc_by_day[day] = candles
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
                        "order": "recent_first", "tf_minutes": TF_MINUTES,
                        "days_done": i, "days_total": n_days,
                        "days_with_data": days_with_data,
                        "oldest_day_covered": oldest_done.strftime("%Y-%m-%d"),
                        "newest_day_covered": END.strftime("%Y-%m-%d"),
                        "m5_candles_so_far": len(merged),
                        "elapsed_s": round(time.time() - t0),
                    }, f, indent=2)
                _prune_raw_cache(oldest_done)
                print(f"[fetch-m5] {i}/{n_days} giorni, {days_with_data} con dati, "
                      f"copertura fino a {oldest_done.date()}, {len(merged)} candele M5, "
                      f"{time.time()-t0:.0f}s trascorsi", flush=True)

    print(f"[fetch-m5] completato: {days_with_data} giorni con dati su {n_days} "
          f"({time.time()-t0:.0f}s totali)", flush=True)


if __name__ == "__main__":
    main()
