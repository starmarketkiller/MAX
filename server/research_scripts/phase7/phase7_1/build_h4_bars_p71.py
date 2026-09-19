#!/usr/bin/env python3
"""Phase 7.1 - costruisce barre H4 per il nuovo periodo (2023-02-04..
2026-09-16) PIU' un buffer di lookback (2022-11-04..2023-02-03, dati
GIA' in cache da Phase 6 True Holdout, contiguo senza gap) - stessa
identica logica di aggregazione di server/research_scripts/phase5/
build_h4_bars.py (OHLC su BID, allineamento UTC fisso 00/04/08/12/16/20),
copiata qui senza modifiche funzionali (stesso pattern di
phase6/build_h4_bars_holdout.py).

Il buffer NON viene mai valutato come osservazione del test - serve solo
a dare a feature come atr_percentile (finestra 252 barre) una storia
sufficiente fin dalla primissima barra ufficiale del periodo
(2023-02-04 00:00 UTC).
"""
import gzip
import csv
import json
import os
from datetime import datetime, timedelta, timezone

# Path portabile (Integrity Patch Phase 7.0 lesson: mai un path assoluto machine-specific hardcoded)
ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", ".."))
PHASE6_DECODED_DIR = os.path.join(ROOT, "server", "research_scripts", "phase6", "data_cache_holdout", "decoded")
PHASE7_DECODED_DIR = os.path.join(ROOT, "server", "research_scripts", "phase7", "data_cache_new_period", "decoded")
OUT_DIR = os.path.join(ROOT, "server", "research_scripts", "phase7", "phase7_1", "data")
os.makedirs(OUT_DIR, exist_ok=True)

BUFFER_START = datetime(2022, 11, 4, tzinfo=timezone.utc)
PERIOD_START = datetime(2023, 2, 4, tzinfo=timezone.utc)
PERIOD_END = datetime(2026, 9, 16, tzinfo=timezone.utc)
BAR_HOURS = 4


def h4_bucket(ts_ms: int) -> int:
    dt = datetime.fromtimestamp(ts_ms / 1000, tz=timezone.utc)
    bucket_hour = (dt.hour // BAR_HOURS) * BAR_HOURS
    bucket_dt = dt.replace(hour=bucket_hour, minute=0, second=0, microsecond=0)
    return int(bucket_dt.timestamp())


def decoded_path_for(day: datetime) -> str:
    """Il buffer (< 2023-02-04) vive nella cache Phase 6 (True Holdout);
    il periodo vero e proprio vive nella nuova cache Phase 7."""
    if day < PERIOD_START:
        return os.path.join(PHASE6_DECODED_DIR, f"{day.year:04d}", f"{day.strftime('%Y-%m-%d')}.csv.gz")
    return os.path.join(PHASE7_DECODED_DIR, f"{day.year:04d}", f"{day.strftime('%Y-%m-%d')}.csv.gz")


def main():
    bars = {}
    day = BUFFER_START
    n_days = 0
    n_ticks = 0
    while day <= PERIOD_END:
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
    out_path = os.path.join(OUT_DIR, "xauusd_h4_bars_p71.csv")
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["bar_time_utc", "bar_epoch", "open", "high", "low", "close", "avg_spread", "n_ticks", "is_buffer"])
        for b in buckets:
            rec = bars[b]
            avg_spread = rec["spread_sum"] / rec["n_ticks"]
            bar_dt = datetime.fromtimestamp(b, tz=timezone.utc)
            is_buffer = bar_dt < PERIOD_START
            w.writerow([
                bar_dt.isoformat(), b, rec["open"], rec["high"], rec["low"], rec["close"],
                round(avg_spread, 5), rec["n_ticks"], is_buffer,
            ])

    n_buffer_bars = sum(1 for b in buckets if datetime.fromtimestamp(b, tz=timezone.utc) < PERIOD_START)
    n_period_bars = len(buckets) - n_buffer_bars

    meta = {
        "buffer_start_utc": BUFFER_START.isoformat(),
        "period_start_utc": PERIOD_START.isoformat(),
        "period_end_utc": PERIOD_END.isoformat(),
        "n_days_source_files_found": n_days,
        "n_ticks_aggregated": n_ticks,
        "n_bars_total": len(buckets),
        "n_buffer_bars": n_buffer_bars,
        "n_period_bars": n_period_bars,
        "note": "buffer bars used ONLY for feature warmup, never evaluated as test observations",
        "built_at": datetime.now(timezone.utc).isoformat(),
        "script": "server/research_scripts/phase7/phase7_1/build_h4_bars_p71.py",
    }
    json.dump(meta, open(os.path.join(OUT_DIR, "xauusd_h4_bars_p71.meta.json"), "w", encoding="utf-8"), indent=2)
    print(json.dumps(meta, indent=2))


if __name__ == "__main__":
    main()
