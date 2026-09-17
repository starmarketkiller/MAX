#!/usr/bin/env python3
"""Phase 5.B - costruisce barre H4 OHLC causali da tick Dukascopy XAUUSD
gia' validati in Phase 4 (DUKASCOPY_TICK_DATA_VALID, 148.097.525 tick,
2019-02-03 -> 2022-02-03). Fonte unica e coerente (nessun mix con lo
storico del broker live, per evitare esattamente il tipo di mismatch di
feed gia' catalogato in Failure Memory).

Convenzione di prezzo: OHLC costruito sul BID (convenzione standard di
molte piattaforme per il grafico principale) - ask/spread mantenuti
separatamente come feature di stato, non nel prezzo OHLC.

Convenzione di confine barra: allineamento UTC fisso (00,04,08,12,16,20)
- NON e' l'allineamento del broker MT5 live (che dipende dal suo GMT
offset), e' una scelta deliberata per un dataset di ricerca Python
indipendente, causale e riproducibile. Documentato qui come provenance.
"""
import gzip
import csv
import json
import os
from datetime import datetime, timedelta, timezone

ROOT = r"C:\Users\User\ClaudeWork\MAX"
DECODED_DIR = os.path.join(ROOT, "server", "data_cache", "dukascopy_phaseH", "decoded")
OUT_DIR = os.path.join(ROOT, "server", "research_scripts", "phase5", "data")
os.makedirs(OUT_DIR, exist_ok=True)

START = datetime(2019, 2, 3, tzinfo=timezone.utc)
END = datetime(2022, 2, 3, tzinfo=timezone.utc)
BAR_HOURS = 4


def h4_bucket(ts_ms: int) -> int:
    dt = datetime.fromtimestamp(ts_ms / 1000, tz=timezone.utc)
    bucket_hour = (dt.hour // BAR_HOURS) * BAR_HOURS
    bucket_dt = dt.replace(hour=bucket_hour, minute=0, second=0, microsecond=0)
    return int(bucket_dt.timestamp())


def main():
    bars = {}  # bucket_epoch -> dict
    day = START
    n_days = 0
    n_ticks = 0
    while day <= END:
        path = os.path.join(DECODED_DIR, f"{day.year:04d}", f"{day.strftime('%Y-%m-%d')}.csv.gz")
        if os.path.exists(path):
            with gzip.open(path, "rt", newline="", encoding="utf-8") as f:
                r = csv.reader(f)
                next(r, None)
                for row in r:
                    if not row:
                        continue
                    ts = int(row[0]); bid = float(row[1]); ask = float(row[2])
                    b = h4_bucket(ts)
                    rec = bars.get(b)
                    if rec is None:
                        bars[b] = {
                            "open": bid, "high": bid, "low": bid, "close": bid,
                            "open_ts": ts, "close_ts": ts,
                            "spread_sum": ask - bid, "n_ticks": 1,
                            "ask_close": ask,
                        }
                    else:
                        if ts < rec["open_ts"]:
                            rec["open"] = bid; rec["open_ts"] = ts
                        if ts >= rec["close_ts"]:
                            rec["close"] = bid; rec["close_ts"] = ts; rec["ask_close"] = ask
                        if bid > rec["high"]:
                            rec["high"] = bid
                        if bid < rec["low"]:
                            rec["low"] = bid
                        rec["spread_sum"] += (ask - bid)
                        rec["n_ticks"] += 1
                    n_ticks += 1
            n_days += 1
        day += timedelta(days=1)

    buckets = sorted(bars.keys())
    out_path = os.path.join(OUT_DIR, "xauusd_h4_bars.csv")
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["bar_time_utc", "bar_epoch", "open", "high", "low", "close",
                    "avg_spread", "n_ticks"])
        for b in buckets:
            rec = bars[b]
            avg_spread = rec["spread_sum"] / rec["n_ticks"]
            w.writerow([
                datetime.fromtimestamp(b, tz=timezone.utc).isoformat(),
                b, rec["open"], rec["high"], rec["low"], rec["close"],
                round(avg_spread, 5), rec["n_ticks"],
            ])

    meta = {
        "source": "server/data_cache/dukascopy_phaseH/decoded (Phase 4, DUKASCOPY_TICK_DATA_VALID)",
        "symbol": "XAUUSD",
        "price_convention": "OHLC built from BID; ask/spread tracked separately (avg_spread column)",
        "bar_boundary_convention": "fixed UTC alignment (00,04,08,12,16,20) - NOT broker/MT5 server-time aligned, deliberate independent research convention",
        "window_start_utc": START.isoformat(),
        "window_end_utc": END.isoformat(),
        "n_days_source_files_found": n_days,
        "n_ticks_aggregated": n_ticks,
        "n_h4_bars": len(buckets),
        "built_at": datetime.now(timezone.utc).isoformat(),
        "script": "server/research_scripts/phase5/build_h4_bars.py",
        "script_version": 1,
    }
    json.dump(meta, open(os.path.join(OUT_DIR, "xauusd_h4_bars.meta.json"), "w", encoding="utf-8"), indent=2)
    print(json.dumps(meta, indent=2))


if __name__ == "__main__":
    main()
