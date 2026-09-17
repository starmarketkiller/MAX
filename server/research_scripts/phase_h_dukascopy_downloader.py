#!/usr/bin/env python3
"""Phase H - downloader dedicato per tick BID/ASK reali Dukascopy XAUUSD,
finestra congelata 2019-02-03 -> 2022-02-03. A differenza del
server/dukascopy_fetch.py esistente (che scarta bid/ask separati e tiene
solo il mid per costruire OHLC M15), questo:
  1. Salva i file .bi5 RAW originali su disco (provenienza, punto 3 task).
  2. Decodifica preservando bid, ask, bid_vol, ask_vol separati (non solo mid).
  3. Distingue esplicitamente EMPTY (404/0 byte, mercato chiuso - normale) da
     FAILED (errore di rete dopo i retry - da ritentare in un secondo passo),
     invece di trattarli come equivalenti (limite del fetcher esistente).
  4. Tiene un manifest per-giorno per rendere il download ripristinabile e
     per rispondere direttamente a "giorni mancanti" nell'integrity audit.

Formato .bi5: LZMA "ALONE", record da 20 byte big-endian:
  uint32 offset_ms_da_inizio_ora, uint32 ask_raw, uint32 bid_raw,
  float32 ask_vol, float32 bid_vol.
Divisore prezzo XAUUSD verificato in dukascopy_fetch.py: /1000.
"""
from __future__ import annotations
import lzma, os, struct, time, sys, json, csv, gzip
import urllib.request, urllib.error
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta, timezone

SYMBOL = "XAUUSD"
DIVISOR = 1000.0
START = datetime(2019, 2, 3, tzinfo=timezone.utc)
END = datetime(2022, 2, 3, tzinfo=timezone.utc)

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data_cache", "dukascopy_phaseH")
RAW_DIR = os.path.join(ROOT, "raw")
DECODED_DIR = os.path.join(ROOT, "decoded")
MANIFEST_PATH = os.path.join(ROOT, "manifest.json")
MAX_WORKERS = 4   # ridotto da 12: 503 diffusi osservati a 12, il server rallenta/blocca sotto carico
                  # sostenuto (non solo istantaneo) - piu' lento ma affidabile.


def _hour_url(dt: datetime) -> str:
    return (f"https://datafeed.dukascopy.com/datafeed/{SYMBOL}/"
            f"{dt.year}/{dt.month - 1:02d}/{dt.day:02d}/{dt.hour:02d}h_ticks.bi5")


def _raw_path(dt: datetime) -> str:
    d = os.path.join(RAW_DIR, f"{dt.year:04d}", f"{dt.month:02d}", f"{dt.day:02d}")
    os.makedirs(d, exist_ok=True)
    return os.path.join(d, f"{dt.hour:02d}h_ticks.bi5")


def fetch_hour_raw(dt: datetime, timeout: int = 25, retries: int = 6) -> tuple[str, bytes | None]:
    """Ritorna (status, raw_bytes). status in {'empty','ok','failed'}."""
    path = _raw_path(dt)
    if os.path.exists(path):
        size = os.path.getsize(path)
        with open(path, "rb") as f:
            data = f.read()
        return ("empty" if size == 0 else "ok"), data
    url = _hour_url(dt)
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 NEXUS-research-phaseH"})
    last_err = None
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                raw = r.read()
            with open(path, "wb") as f:
                f.write(raw)
            return ("empty" if not raw else "ok"), raw
        except urllib.error.HTTPError as e:
            if e.code == 404:
                with open(path, "wb") as f:
                    pass
                return "empty", b""
            last_err = e
        except Exception as e:
            last_err = e
        time.sleep(min(2.0 * (2 ** attempt), 30.0))   # backoff esponenziale, cap 30s
    print(f"[phaseH] FAILED {dt.isoformat()}: {str(last_err)[:120]}", flush=True)
    return "failed", None


def decode_hour(raw: bytes, hour_dt: datetime) -> list[tuple[int, float, float, float, float]]:
    """[(epoch_ms, bid, ask, bid_vol, ask_vol)]"""
    if not raw:
        return []
    try:
        data = lzma.decompress(raw, format=lzma.FORMAT_ALONE)
    except lzma.LZMAError:
        return []
    hour_ms = int(hour_dt.timestamp() * 1000)
    n = len(data) // 20
    out = []
    for i in range(n):
        off = i * 20
        t_ms, ask_raw, bid_raw, av, bv = struct.unpack(">IIIff", data[off:off + 20])
        out.append((hour_ms + t_ms, bid_raw / DIVISOR, ask_raw / DIVISOR, bv, av))
    return out


def _day_decoded_path(day: datetime) -> str:
    d = os.path.join(DECODED_DIR, f"{day.year:04d}")
    os.makedirs(d, exist_ok=True)
    return os.path.join(d, f"{day.strftime('%Y-%m-%d')}.csv.gz")


def load_manifest() -> dict:
    if os.path.exists(MANIFEST_PATH):
        with open(MANIFEST_PATH, encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_manifest(m: dict):
    tmp = MANIFEST_PATH + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(m, f, indent=1)
    os.replace(tmp, MANIFEST_PATH)


def process_day(day: datetime, manifest: dict, max_workers: int = MAX_WORKERS) -> dict:
    key = day.strftime("%Y-%m-%d")
    existing = manifest.get(key)
    if existing and existing.get("complete"):
        return existing
    hours = [day.replace(hour=h, minute=0, second=0, microsecond=0) for h in range(24)]
    results = {}
    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        futs = {ex.submit(fetch_hour_raw, h): h for h in hours}
        for fut in as_completed(futs):
            h = futs[fut]
            status, raw = fut.result()
            results[h.hour] = (status, raw)

    all_ticks = []
    n_empty = n_ok = n_failed = 0
    for h in hours:
        status, raw = results[h.hour]
        if status == "ok":
            n_ok += 1
            all_ticks.extend(decode_hour(raw, h))
        elif status == "empty":
            n_empty += 1
        else:
            n_failed += 1

    all_ticks.sort(key=lambda x: x[0])
    out_path = _day_decoded_path(day)
    with gzip.open(out_path, "wt", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["epoch_ms", "bid", "ask", "bid_vol", "ask_vol"])
        for row in all_ticks:
            w.writerow(row)

    entry = {
        "n_ticks": len(all_ticks), "n_hours_ok": n_ok, "n_hours_empty": n_empty,
        "n_hours_failed": n_failed, "complete": n_failed == 0,
        "weekday": day.weekday(),  # 5=sat, 6=sun
    }
    manifest[key] = entry
    return entry


def main():
    manifest = load_manifest()
    t0 = time.time()
    day = START.replace(hour=0, minute=0, second=0, microsecond=0)
    end = END.replace(hour=0, minute=0, second=0, microsecond=0)
    n_days = (end - day).days + 1
    i = 0
    while day <= end:
        i += 1
        entry = process_day(day, manifest)
        if i % 10 == 0 or not entry["complete"]:
            save_manifest(manifest)
            elapsed = time.time() - t0
            print(f"[phaseH] {i}/{n_days} {day.date()} ticks={entry['n_ticks']} "
                  f"ok={entry['n_hours_ok']} empty={entry['n_hours_empty']} "
                  f"failed={entry['n_hours_failed']} complete={entry['complete']} "
                  f"elapsed={elapsed:.0f}s", flush=True)
        day += timedelta(days=1)
    save_manifest(manifest)
    print(f"[phaseH] COMPLETATO {n_days} giorni in {time.time()-t0:.0f}s", flush=True)


if __name__ == "__main__":
    main()
