#!/usr/bin/env python3
"""Phase 6 sec.3 - downloader tick BID/ASK reali Dukascopy XAUUSD per il
periodo di TRUE HOLDOUT: 2022-02-04 -> 2023-02-03 (giorno immediatamente
successivo alla fine della finestra usata in Phase 5, un anno esatto,
MAI scaricato prima - vedi true_holdout_declaration.json, dichiarato
PRIMA di questo fetch).

Stessa identica logica del downloader v2 di Phase 4
(server/research_scripts/phase_h_dukascopy_downloader.py) - copiata qui
SENZA modifiche funzionali, solo con START/END/ROOT diversi, per non
toccare/mischiare la cache/manifest originale di Phase 4/5.
"""
from __future__ import annotations
import lzma, os, struct, time, sys, json, csv, gzip, random
import requests
from requests.adapters import HTTPAdapter
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta, timezone

SYMBOL = "XAUUSD"
DIVISOR = 1000.0
START = datetime(2022, 2, 4, tzinfo=timezone.utc)
END = datetime(2023, 2, 3, tzinfo=timezone.utc)

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data_cache_holdout")
RAW_DIR = os.path.join(ROOT, "raw")
DECODED_DIR = os.path.join(ROOT, "decoded")
MANIFEST_PATH = os.path.join(ROOT, "manifest.json")
MAX_WORKERS = 5

_SESSION = None


def get_session() -> requests.Session:
    global _SESSION
    if _SESSION is None:
        s = requests.Session()
        adapter = HTTPAdapter(pool_connections=1, pool_maxsize=MAX_WORKERS + 2, max_retries=0)
        s.mount("https://", adapter)
        _SESSION = s
    return _SESSION


def _hour_url(dt: datetime) -> str:
    return (f"https://datafeed.dukascopy.com/datafeed/{SYMBOL}/"
            f"{dt.year}/{dt.month - 1:02d}/{dt.day:02d}/{dt.hour:02d}h_ticks.bi5")


def _raw_path(dt: datetime) -> str:
    d = os.path.join(RAW_DIR, f"{dt.year:04d}", f"{dt.month:02d}", f"{dt.day:02d}")
    os.makedirs(d, exist_ok=True)
    return os.path.join(d, f"{dt.hour:02d}h_ticks.bi5")


def _is_valid_bi5(raw: bytes) -> bool:
    if not raw:
        return True
    try:
        lzma.decompress(raw, format=lzma.FORMAT_ALONE)
        return True
    except lzma.LZMAError:
        return False


def fetch_hour_raw(dt: datetime, timeout: int = 20, retries: int = 5) -> tuple[str, bytes | None]:
    path = _raw_path(dt)
    if os.path.exists(path):
        with open(path, "rb") as f:
            data = f.read()
        if _is_valid_bi5(data):
            return ("empty" if not data else "ok"), data

    session = get_session()
    url = _hour_url(dt)
    last_err = None
    for attempt in range(retries):
        try:
            r = session.get(url, headers={"User-Agent": "Mozilla/5.0 NEXUS-research-phase6"}, timeout=timeout)
            if r.status_code == 404:
                with open(path, "wb") as f:
                    pass
                return "empty", b""
            if r.status_code != 200:
                last_err = f"HTTP {r.status_code}"
                raise RuntimeError(last_err)
            raw = r.content
            if not _is_valid_bi5(raw):
                last_err = "decompressione fallita (file corrotto ricevuto)"
                raise RuntimeError(last_err)
            with open(path, "wb") as f:
                f.write(raw)
            return ("empty" if not raw else "ok"), raw
        except Exception as e:
            last_err = str(e)
        time.sleep(min(1.0 * (2 ** attempt), 20.0) + random.uniform(0, 0.5))
    print(f"[phase6] FAILED {dt.isoformat()}: {str(last_err)[:120]}", flush=True)
    return "failed", None


def decode_hour(raw: bytes, hour_dt: datetime) -> list[tuple[int, float, float, float, float]]:
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
        "weekday": day.weekday(),
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
    day_times = []
    while day <= end:
        i += 1
        td0 = time.time()
        entry = process_day(day, manifest)
        day_times.append(time.time() - td0)
        if i % 10 == 0 or not entry["complete"]:
            save_manifest(manifest)
            elapsed = time.time() - t0
            recent = day_times[-20:]
            rate = sum(recent) / len(recent)
            remaining = n_days - i
            eta_s = remaining * rate
            print(f"[phase6] {i}/{n_days} {day.date()} ticks={entry['n_ticks']} "
                  f"ok={entry['n_hours_ok']} empty={entry['n_hours_empty']} "
                  f"failed={entry['n_hours_failed']} complete={entry['complete']} "
                  f"elapsed={elapsed:.0f}s rate={rate:.1f}s/day ETA={eta_s/3600:.1f}h", flush=True)
        day += timedelta(days=1)
    save_manifest(manifest)
    print(f"[phase6] COMPLETATO {n_days} giorni in {time.time()-t0:.0f}s", flush=True)


if __name__ == "__main__":
    main()
