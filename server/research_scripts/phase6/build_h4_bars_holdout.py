#!/usr/bin/env python3
"""Phase 6 sec.3 - costruisce barre H4 per il periodo di TRUE HOLDOUT
(2022-02-04..2023-02-03) PIU' un buffer di lookback (2021-11-01..2022-02-03,
dati GIA' cache da Phase 4/5, riusati SOLO per il warmup delle feature
rolling) - stessa identica logica di aggregazione di
server/research_scripts/phase5/build_h4_bars.py (OHLC su BID, allineamento
UTC fisso 00/04/08/12/16/20), copiata qui senza modifiche funzionali.

Il buffer NON viene mai valutato come osservazione del test - serve solo
a dare a feature come atr_percentile (finestra 252 barre) una storia
sufficiente fin dalla primissima barra ufficiale di holdout
(2022-02-04 00:00 UTC).
"""
import gzip
import csv
import json
import os
from datetime import datetime, timedelta, timezone

ROOT = r"C:\Users\User\ClaudeWork\MAX"
PHASE4_DECODED_DIR = os.path.join(ROOT, "server", "data_cache", "dukascopy_phaseH", "decoded")
PHASE6_DECODED_DIR = os.path.join(ROOT, "server", "research_scripts", "phase6", "data_cache_holdout", "decoded")
OUT_DIR = os.path.join(ROOT, "server", "research_scripts", "phase6", "data")
os.makedirs(OUT_DIR, exist_ok=True)

BUFFER_START = datetime(2021, 11, 1, tzinfo=timezone.utc)
HOLDOUT_START = datetime(2022, 2, 4, tzinfo=timezone.utc)
HOLDOUT_END = datetime(2023, 2, 3, tzinfo=timezone.utc)
BAR_HOURS = 4


def h4_bucket(ts_ms: int) -> int:
    dt = datetime.fromtimestamp(ts_ms / 1000, tz=timezone.utc)
    bucket_hour = (dt.hour // BAR_HOURS) * BAR_HOURS
    bucket_dt = dt.replace(hour=bucket_hour, minute=0, second=0, microsecond=0)
    return int(bucket_dt.timestamp())


def decoded_path_for(day: datetime) -> str:
    """Il buffer (< 2022-02-04) vive nella cache Phase 4; l'holdout vero
    e proprio vive nella nuova cache Phase 6."""
    if day < HOLDOUT_START:
        return os.path.join(PHASE4_DECODED_DIR, f"{day.year:04d}", f"{day.strftime('%Y-%m-%d')}.csv.gz")
    return os.path.join(PHASE6_DECODED_DIR, f"{day.year:04d}", f"{day.strftime('%Y-%m-%d')}.csv.gz")


def main():
    bars = {}
    day = BUFFER_START
    n_days = 0
    n_ticks = 0
    while day <= HOLDOUT_END:
        path = decoded_path_for(day)
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
                        }
                    else:
                        if ts < rec["open_ts"]:
                            rec["open"] = bid; rec["open_ts"] = ts
                        if ts >= rec["close_ts"]:
                            rec["close"] = bid; rec["close_ts"] = ts
                        if bid > rec["high"]:
                            rec["high"] = bid
                        if bid < rec["low"]:
                            rec["low"] = bid
                        rec["spread_sum"] += (ask - bid)
                        rec["n_ticks"] += 1
                    n_ticks += 1
            n_days += 1
        else:
            print(f"WARNING: missing decoded file for {day.date()}: {path}")
        day += timedelta(days=1)

    buckets = sorted(bars.keys())
    out_path = os.path.join(OUT_DIR, "xauusd_h4_bars_holdout.csv")
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["bar_time_utc", "bar_epoch", "open", "high", "low", "close", "avg_spread", "n_ticks", "is_buffer"])
        for b in buckets:
            rec = bars[b]
            avg_spread = rec["spread_sum"] / rec["n_ticks"]
            bar_dt = datetime.fromtimestamp(b, tz=timezone.utc)
            is_buffer = bar_dt < HOLDOUT_START
            w.writerow([
                bar_dt.isoformat(), b, rec["open"], rec["high"], rec["low"], rec["close"],
                round(avg_spread, 5), rec["n_ticks"], is_buffer,
            ])

    n_buffer_bars = sum(1 for b in buckets if datetime.fromtimestamp(b, tz=timezone.utc) < HOLDOUT_START)
    n_holdout_bars = len(buckets) - n_buffer_bars

    meta = {
        "buffer_start_utc": BUFFER_START.isoformat(),
        "holdout_start_utc": HOLDOUT_START.isoformat(),
        "holdout_end_utc": HOLDOUT_END.isoformat(),
        "n_days_source_files_found": n_days,
        "n_ticks_aggregated": n_ticks,
        "n_bars_total": len(buckets),
        "n_buffer_bars": n_buffer_bars,
        "n_holdout_bars": n_holdout_bars,
        "note": "buffer bars used ONLY for feature warmup, never evaluated as test observations",
        "built_at": datetime.now(timezone.utc).isoformat(),
        "script": "server/research_scripts/phase6/build_h4_bars_holdout.py",
    }
    json.dump(meta, open(os.path.join(OUT_DIR, "xauusd_h4_bars_holdout.meta.json"), "w", encoding="utf-8"), indent=2)
    print(json.dumps(meta, indent=2))


if __name__ == "__main__":
    main()
