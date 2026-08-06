"""Fetcher storico tick Dukascopy per XAUUSD (e altri strumenti), con cache
locale su disco. Sostituisce Yahoo per i timeframe intraday (H4/H1/M15),
dove Yahoo limita a ~2 anni/60 giorni - Dukascopy pubblica tick gratuiti
per anni, senza API key.

Formato file: https://datafeed.dukascopy.com/datafeed/{SYM}/{anno}/{mese 0-indicizzato}/{giorno}/{ora}h_ticks.bi5
Compressione LZMA "alone" (non xz standard). Record da 20 byte big-endian:
  uint32 offset_ms_da_inizio_ora, uint32 ask_raw, uint32 bid_raw,
  float32 ask_vol, float32 bid_vol.
Divisore prezzo verificato empiricamente il 31/07/2026 per XAUUSD: /1000
(raw 2059815 -> 2059.815, coerente col prezzo oro reale di inizio gennaio 2024).
File orari senza tick (mercato chiuso) sono vuoti (0 byte) - normali, non errori.
"""
from __future__ import annotations
import lzma
import os
import struct
import time
import urllib.request
import urllib.error
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta, timezone

DUKASCOPY_POINT_DIVISOR = {"XAUUSD": 1000.0}


def data_cache_root() -> str:
    """Radice della cache dati (snapshot M15 + cache grezza per-giorno).
    Su Render il filesystem dell'immagine e' effimero (perso ad ogni deploy/
    riavvio) tranne il disco persistente montato su /data (vedi render.yaml,
    oggi usato solo dal database) - NEXUS_DUKASCOPY_DIR permette di puntare
    li' (es. /data/dukascopy) in produzione, restando sul path relativo di
    sempre in locale/dev quando la variabile non e' impostata."""
    override = os.environ.get("NEXUS_DUKASCOPY_DIR")
    if override:
        return override
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), "data_cache")


CACHE_DIR = os.path.join(data_cache_root(), "dukascopy")


def _hour_url(symbol: str, dt: datetime) -> str:
    return (f"https://datafeed.dukascopy.com/datafeed/{symbol}/"
            f"{dt.year}/{dt.month - 1:02d}/{dt.day:02d}/{dt.hour:02d}h_ticks.bi5")


def _fetch_hour_ticks(symbol: str, dt: datetime, timeout: int = 20, retries: int = 3) -> list:
    """Ritorna [(epoch_ms, mid_price), ...] per quell'ora, [] se vuota/assente.
    Retry con backoff: il proxy/rete di questo ambiente droppa qualche
    connessione sotto concorrenza, non e' un errore del server Dukascopy."""
    url = _hour_url(symbol, dt)
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 NEXUS-research"})
    raw_compressed = None
    last_err = None
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                raw_compressed = r.read()
            break
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return []
            last_err = e
        except Exception as e:
            last_err = e
        time.sleep(0.5 * (attempt + 1))
    if raw_compressed is None:
        raise RuntimeError(f"dukascopy fetch fallita dopo {retries} tentativi: {url} ({last_err})")
    if not raw_compressed:
        return []
    try:
        raw = lzma.decompress(raw_compressed, format=lzma.FORMAT_ALONE)
    except lzma.LZMAError:
        return []   # file vuoto/corrotto lato Dukascopy (raro ma capita per ore senza scambi)
    divisor = DUKASCOPY_POINT_DIVISOR.get(symbol, 100000.0)
    hour_epoch_ms = int(dt.replace(minute=0, second=0, microsecond=0).timestamp() * 1000)
    n = len(raw) // 20
    out = []
    for i in range(n):
        off = i * 20
        t_ms, ask_raw, bid_raw, _av, _bv = struct.unpack(">IIIff", raw[off:off + 20])
        mid = (ask_raw + bid_raw) / 2.0 / divisor
        out.append((hour_epoch_ms + t_ms, mid))
    return out


def _cache_path(symbol: str, day: datetime) -> str:
    d = os.path.join(CACHE_DIR, symbol)
    os.makedirs(d, exist_ok=True)
    return os.path.join(d, f"{day.year}-{day.month:02d}-{day.day:02d}.json")


def fetch_day_ticks(symbol: str, day: datetime, max_workers: int = 12) -> list:
    """Tick di un intero giorno (24 file orari), con cache locale su disco -
    un giorno gia' scaricato non viene mai ri-scaricato.
    Resiliente per-ora: un'ora che fallisce anche dopo i retry di
    _fetch_hour_ticks (es. 503 transitorio, host irraggiungibile per
    quell'archivio) viene loggata e trattata come vuota, non fa fallire
    l'intero giorno/anno - un fetch multi-anno non deve morire per un
    singolo file 404/503 in mezzo a migliaia."""
    cp = _cache_path(symbol, day)
    if os.path.exists(cp):
        with open(cp, encoding="utf-8") as f:
            return json.load(f)
    hours = [day.replace(hour=h, minute=0, second=0, microsecond=0) for h in range(24)]
    all_ticks = []
    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        futs = {ex.submit(_fetch_hour_ticks, symbol, h): h for h in hours}
        for fut in as_completed(futs):
            h = futs[fut]
            try:
                all_ticks.extend(fut.result())
            except Exception as e:
                print(f"[dukascopy] ora persa {symbol} {h.isoformat()}: {str(e)[:100]}", flush=True)
    all_ticks.sort(key=lambda x: x[0])
    with open(cp, "w", encoding="utf-8") as f:
        json.dump(all_ticks, f)
    return all_ticks


def ticks_to_ohlc(ticks: list, tf_minutes: int) -> list:
    """[(epoch_ms, mid)] -> candele OHLC a tf_minutes, formato compatibile
    con backtest.py: {time, open, high, low, close}."""
    if not ticks:
        return []
    bucket_ms = tf_minutes * 60 * 1000
    buckets = {}
    for t_ms, px in ticks:
        b = (t_ms // bucket_ms) * bucket_ms
        if b not in buckets:
            buckets[b] = [px, px, px, px]   # o h l c
        else:
            c = buckets[b]
            c[1] = max(c[1], px)
            c[2] = min(c[2], px)
            c[3] = px
    out = []
    for b in sorted(buckets):
        o, h, l, c = buckets[b]
        out.append({
            "time": datetime.fromtimestamp(b / 1000, tz=timezone.utc).strftime("%Y-%m-%d %H:%M"),
            "open": round(o, 5), "high": round(h, 5), "low": round(l, 5), "close": round(c, 5),
        })
    return out


def fetch_range_ohlc(symbol: str, start: datetime, end: datetime, tf_minutes: int,
                      max_workers: int = 12, progress_every: int = 30) -> list:
    """Scarica (con cache) tutti i giorni fra start ed end (inclusi) e li
    aggrega a candele tf_minutes. Salta i weekend (mercato XAUUSD chiuso,
    nessun tick - non e' un errore, e' il file vuoto atteso)."""
    all_ticks = []
    day = start
    n_days = (end - start).days + 1
    i = 0
    while day <= end:
        if day.weekday() < 5 or True:   # anche sab/dom: file vuoti, costo trascurabile con cache
            all_ticks.extend(fetch_day_ticks(symbol, day, max_workers=max_workers))
        i += 1
        if progress_every and i % progress_every == 0:
            print(f"[dukascopy] {symbol} {day.date()} - {i}/{n_days} giorni, "
                  f"{len(all_ticks)} tick finora", flush=True)
        day += timedelta(days=1)
    return ticks_to_ohlc(all_ticks, tf_minutes)
