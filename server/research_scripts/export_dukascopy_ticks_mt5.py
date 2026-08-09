#!/usr/bin/env python3
"""
09/08 - esporta tick Dukascopy grezzi (bid/ask separati, non solo il mid
usato da dukascopy_fetch.fetch_day_ticks) in CSV per l'import "Simbolo
Personalizzato" di MT5 - cosi' Python e MT5 possono girare sullo STESSO
identico storico invece di due feed diversi (broker vs Dukascopy), che oggi
garantiscono divergenze anche a parita' di logica.

NON modifica dukascopy_fetch.py (usato in produzione dal sito/fetch
automatico) - fetch separata, stessa fonte/formato .bi5, per non introdurre
rischio sulla pipeline che alimenta il motore Python live.

Formato CSV: <DATE>,<TIME>,<BID>,<ASK>,<LAST>,<VOLUME> - il formato
documentato per "Importa tick" nella finestra Simboli Personalizzati di MT5
(Ctrl+U -> Crea simbolo personalizzato -> scheda Tick -> Importa tick).
NON verificato contro un'istanza MT5 reale in questa sessione (nessun
accesso qui) - prima di un fetch multi-anno, fare UN giorno di prova e
verificare che l'import vada a buon fine, poi procedere sul resto.

Uso (da eseguire dove c'e' spazio disco e/o MT5 - NON sul container Render,
1GB di disco condiviso col database):
  python3 server/research_scripts/export_dukascopy_ticks_mt5.py \
      --start 2021-01-01 --end 2026-08-09 --out xauusd_ticks_mt5.csv

Riprendibile: salta i giorni gia' presenti nel CSV di output (stesso
principio del resume-fix di fetch_dukascopy_history.py, PR #18) - un
fetch di anni di tick puo' richiedere ore, non deve ripartire da zero se
si interrompe.
"""
import argparse
import csv
import lzma
import os
import struct
import sys
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from dukascopy_fetch import DUKASCOPY_POINT_DIVISOR, _hour_url

SYMBOL = "XAUUSD"


def _fetch_hour_bidask(symbol: str, dt: datetime, timeout: int = 20, retries: int = 3) -> list:
    """Come dukascopy_fetch._fetch_hour_ticks, ma ritorna
    [(epoch_ms, bid, ask), ...] invece di collassare subito sul mid -
    l'import MT5 vuole bid/ask separati per calcolare lo spread reale."""
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
        raise RuntimeError(f"fetch fallita dopo {retries} tentativi: {url} ({last_err})")
    if not raw_compressed:
        return []
    try:
        raw = lzma.decompress(raw_compressed, format=lzma.FORMAT_ALONE)
    except lzma.LZMAError:
        return []
    divisor = DUKASCOPY_POINT_DIVISOR.get(symbol, 100000.0)
    hour_epoch_ms = int(dt.replace(minute=0, second=0, microsecond=0).timestamp() * 1000)
    n = len(raw) // 20
    out = []
    for i in range(n):
        off = i * 20
        t_ms, ask_raw, bid_raw, _av, _bv = struct.unpack(">IIIff", raw[off:off + 20])
        out.append((hour_epoch_ms + t_ms, bid_raw / divisor, ask_raw / divisor))
    return out


def _fetch_day_bidask(symbol: str, day: datetime, max_workers: int = 12) -> list:
    hours = [day.replace(hour=h, minute=0, second=0, microsecond=0) for h in range(24)]
    all_ticks = []
    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        futs = {ex.submit(_fetch_hour_bidask, symbol, h): h for h in hours}
        for fut in as_completed(futs):
            h = futs[fut]
            try:
                all_ticks.extend(fut.result())
            except Exception as e:
                print(f"[export] ora persa {symbol} {h.isoformat()}: {str(e)[:100]}", flush=True)
    all_ticks.sort(key=lambda x: x[0])
    return all_ticks


def _existing_days(out_path: str) -> set:
    """Giorni gia' scritti nel CSV di output (per la ripresa) - legge solo
    la colonna DATE, non l'intero file in memoria."""
    if not os.path.exists(out_path):
        return set()
    days = set()
    with open(out_path, encoding="utf-8") as f:
        next(f, None)  # header
        for line in f:
            d = line.split(",", 1)[0]
            if d:
                days.add(d)
    return days


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", required=True, help="YYYY-MM-DD")
    ap.add_argument("--end", required=True, help="YYYY-MM-DD")
    ap.add_argument("--out", default="xauusd_ticks_mt5.csv")
    ap.add_argument("--symbol", default=SYMBOL)
    args = ap.parse_args()

    start = datetime.strptime(args.start, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    end = datetime.strptime(args.end, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    all_days = []
    d = start
    while d <= end:
        all_days.append(d)
        d += timedelta(days=1)

    done_days = _existing_days(args.out)
    todo = [d for d in all_days if d.strftime("%Y.%m.%d") not in done_days]
    print(f"[export] {len(all_days)} giorni totali, {len(done_days)} gia' presenti, "
          f"{len(todo)} da scaricare", flush=True)

    write_header = not os.path.exists(args.out)
    t0 = time.time()
    with open(args.out, "a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if write_header:
            w.writerow(["<DATE>", "<TIME>", "<BID>", "<ASK>", "<LAST>", "<VOLUME>"])
        for i, day in enumerate(todo, 1):
            ticks = _fetch_day_bidask(args.symbol, day)
            date_str = day.strftime("%Y.%m.%d")
            for epoch_ms, bid, ask in ticks:
                t = datetime.fromtimestamp(epoch_ms / 1000.0, tz=timezone.utc)
                time_str = t.strftime("%H:%M:%S.") + f"{t.microsecond // 1000:03d}"
                w.writerow([date_str, time_str, f"{bid:.3f}", f"{ask:.3f}", 0, 0])
            f.flush()
            if i % 10 == 0 or i == len(todo):
                print(f"[export] {i}/{len(todo)} giorni, {time.time()-t0:.0f}s trascorsi", flush=True)

    print(f"[export] completato: {args.out}", flush=True)


if __name__ == "__main__":
    main()
