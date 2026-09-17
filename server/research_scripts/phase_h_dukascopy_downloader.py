#!/usr/bin/env python3
"""Phase H - downloader tick BID/ASK reali Dukascopy XAUUSD, finestra
congelata 2019-02-03 -> 2022-02-03 (NON modificata da questo fix di
performance, come da istruzione esplicita).

STORIA DEL FIX DI PERFORMANCE (16-17/09): la v1 usava urllib.request con
una connessione TCP+TLS NUOVA per ogni singola richiesta oraria - misurato
empiricamente ~16s di solo handshake per richiesta. A 12+ connessioni
nuove in parallelo il server (o un WAF/CDN davanti) rispondeva con 503 di
massa entro <0.3s (bloccando il BURST di connessioni nuove simultanee, non
il volume totale - confermato: una singola richiesta sequenziale subito
dopo un burst-503 tornava 200 pulito). La v2 qui:
  - riusa UNA sessione requests.Session() con pool di connessioni HTTPS
    PERSISTENTI (stessa TLS, keep-alive) per l'intera durata dello script,
    non ricreata per giorno/ora - misurato ~30ms/richiesta dopo il primo
    handshake per connessione, contro i 16s iniziali (>500x).
  - limita la CONCORRENZA reale (non il pool) a max_workers=5, tarato
    empiricamente: 96 richieste su 4 giorni a concorrenza 5 -> 94/96 200 OK
    (97.9%), ~13.6s/giorno, contro il 503-flood sistematico visto a
    concorrenza 12+ con connessioni nuove per richiesta.
  - retry con backoff esponenziale+jitter su OGNI tipo di fallimento
    (503, timeout, connection reset - non solo HTTPError), non solo sulle
    eccezioni originariamente gestite.
  - verifica di integrita' esplicita: ogni file (nuovo O gia' presente su
    disco da run precedenti) viene decompresso con LZMA prima di essere
    considerato valido; un file 0-byte "vuoto" viene accettato solo se la
    decompressione NON e' richiesta (0 byte = giorno/ora senza tick, atteso
    per weekend/festivi - un file non-zero che fallisce la decompressione
    e' invece considerato corrotto e ri-scaricato, non solo "assente").
"""
from __future__ import annotations
import lzma, os, struct, time, sys, json, csv, gzip, random
import requests
from requests.adapters import HTTPAdapter
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
MAX_WORKERS = 5   # tarato empiricamente il 17/09 - vedi docstring modulo

_SESSION = None


def get_session() -> requests.Session:
    global _SESSION
    if _SESSION is None:
        s = requests.Session()
        # pool_connections=1 (un solo host), pool_maxsize>=MAX_WORKERS cosi'
        # ogni worker thread ottiene la propria connessione persistente dal
        # pool invece di aprirne una nuova ad ogni richiesta.
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
    """0 byte = valido (ora senza tick, atteso). Non-zero deve decomprimere
    con LZMA FORMAT_ALONE senza errori, altrimenti e' corrotto."""
    if not raw:
        return True
    try:
        lzma.decompress(raw, format=lzma.FORMAT_ALONE)
        return True
    except lzma.LZMAError:
        return False


def fetch_hour_raw(dt: datetime, timeout: int = 20, retries: int = 5) -> tuple[str, bytes | None]:
    """Ritorna (status, raw_bytes). status in {'empty','ok','failed'}.
    Riusa il file su disco SOLO se passa la verifica di integrita' -
    altrimenti lo ri-scarica (corrotto da un run precedente)."""
    path = _raw_path(dt)
    if os.path.exists(path):
        with open(path, "rb") as f:
            data = f.read()
        if _is_valid_bi5(data):
            return ("empty" if not data else "ok"), data
        # corrotto: cade nel ramo di ri-download sotto

    session = get_session()
    url = _hour_url(dt)
    last_err = None
    for attempt in range(retries):
        try:
            r = session.get(url, headers={"User-Agent": "Mozilla/5.0 NEXUS-research-phaseH"}, timeout=timeout)
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
        # backoff esponenziale con jitter, cap 20s - piu' breve della v1
        # perche' la causa dominante non e' piu' rate-limit sostenuto ma
        # occasionali connection reset transitori.
        time.sleep(min(1.0 * (2 ** attempt), 20.0) + random.uniform(0, 0.5))
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
            print(f"[phaseH] {i}/{n_days} {day.date()} ticks={entry['n_ticks']} "
                  f"ok={entry['n_hours_ok']} empty={entry['n_hours_empty']} "
                  f"failed={entry['n_hours_failed']} complete={entry['complete']} "
                  f"elapsed={elapsed:.0f}s rate={rate:.1f}s/day ETA={eta_s/3600:.1f}h", flush=True)
        day += timedelta(days=1)
    save_manifest(manifest)
    print(f"[phaseH] COMPLETATO {n_days} giorni in {time.time()-t0:.0f}s", flush=True)


if __name__ == "__main__":
    main()
