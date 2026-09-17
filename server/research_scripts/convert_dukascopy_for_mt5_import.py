#!/usr/bin/env python3
"""
convert_dukascopy_for_mt5_import.py

Phase 5 (task L, "SAR vs XM" independent Dukascopy validation).

Reads the ALREADY-VALIDATED Phase 4 Dukascopy XAUUSD tick dataset:
  server/data_cache/dukascopy_phaseH/decoded/<year>/<YYYY-MM-DD>.csv.gz
  columns: epoch_ms,bid,ask,bid_vol,ask_vol  (epoch_ms = UTC, price already
  divided by the correct point divisor -> real XAUUSD prices ~1500-2000)
  manifest.json = per-day completeness ledger (verdict
  DUKASCOPY_TICK_DATA_VALID, 148,097,525 ticks, 0 anomalies - see
  vault/01-Trading/_phase4_artifacts/dukascopy_integrity_audit.json)

and reformats it into a compact binary format the MQL5 importer script
(MQL5/Scripts/NXS_ImportDukascopyCustomSymbol.mq5) reads directly with
FileReadStruct, one fixed-size record per tick:

    struct DukaTick { long epoch_ms; double bid; double ask; };  // 24 bytes
    little-endian, matches x64 Windows native layout exactly.

This script does NOT re-fetch anything from Dukascopy - it only reads the
local, already-integrity-audited Phase 4 cache. It is intentionally
separate from server/research_scripts/export_dukascopy_ticks_mt5.py (the
older 2026-08-09 helper), which re-fetches from Dukascopy itself and
targets MT5's GUI "Import ticks" text format - not used here.

Timezone handling (see report for full reasoning): NEXUS's own H4 bars are
built by MT5 on the broker's SERVER clock, and every session/AMD/HTF helper
in MQL5/Include/NEXUS_v1/*.mqh converts server time -> UTC with the fixed
formula `gmt = server - InpServerGMTOffset*3600` (InpServerGMTOffset
defaults to 2, see NXS_Inputs.mqh:1120). Dukascopy epoch_ms is true UTC.
To make the custom symbol's H4 bar boundaries land on the same wall-clock
grid NEXUS assumes elsewhere, this script feeds MT5 tick timestamps equal
to `dukascopy_utc_ms + gmt_offset_hours*3600000` (i.e. the inverse of that
formula) - the same "server time" convention as the rest of the project,
using the same constant, not a new assumption.

Usage:
  python convert_dukascopy_for_mt5_import.py \
      --start 2019-02-03 --end 2022-02-03 \
      --gmt-offset-hours 2 \
      --out-dir "C:/Users/User/.claude/jobs/703d44b4/tmp/phase5_sar/dukascopy_bin"
"""

import argparse
import csv
import gzip
import io
import json
import os
import struct
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
PHASEH_DIR = REPO_ROOT / "server" / "data_cache" / "dukascopy_phaseH"
DECODED_DIR = PHASEH_DIR / "decoded"
MANIFEST_PATH = PHASEH_DIR / "manifest.json"

RECORD_FMT = "<qdd"  # epoch_ms(shifted, int64), bid(double), ask(double) = 24 bytes
RECORD_SIZE = struct.calcsize(RECORD_FMT)
assert RECORD_SIZE == 24, RECORD_SIZE


def daterange(d0: date, d1: date):
    d = d0
    while d <= d1:
        yield d
        d += timedelta(days=1)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--start", required=True, help="YYYY-MM-DD, inclusive (UTC calendar day of the Dukascopy file)")
    ap.add_argument("--end", required=True, help="YYYY-MM-DD, inclusive")
    ap.add_argument("--gmt-offset-hours", type=float, default=2.0,
                    help="Shift applied to UTC epoch_ms to match NEXUS's InpServerGMTOffset convention (default 2, matches NXS_Inputs.mqh default)")
    ap.add_argument("--out-dir", required=True, help="Output directory for .bin files + index.csv")
    ap.add_argument("--symbol-name", default="XAUUSD_DSC", help="Only recorded in index.csv metadata header, informational")
    args = ap.parse_args()

    d0 = datetime.strptime(args.start, "%Y-%m-%d").date()
    d1 = datetime.strptime(args.end, "%Y-%m-%d").date()
    shift_ms = int(round(args.gmt_offset_hours * 3600 * 1000))

    if not MANIFEST_PATH.exists():
        print(f"ERROR: manifest not found at {MANIFEST_PATH}", file=sys.stderr)
        sys.exit(1)
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    index_rows = []
    total_ticks = 0
    total_days = 0
    mismatches = []
    missing_days = []

    for d in daterange(d0, d1):
        ds = d.strftime("%Y-%m-%d")
        year = str(d.year)
        src = DECODED_DIR / year / f"{ds}.csv.gz"
        if not src.exists():
            missing_days.append(ds)
            continue
        man_entry = manifest.get(ds)
        if man_entry is None:
            missing_days.append(ds + " (no manifest entry)")

        out_sub = out_dir / year
        out_sub.mkdir(parents=True, exist_ok=True)
        out_path = out_sub / f"{ds}.bin"

        n_written = 0
        epoch_first = None
        epoch_last = None
        with gzip.open(src, "rt", newline="") as fh, open(out_path, "wb") as outh:
            reader = csv.reader(fh)
            header = next(reader, None)
            if header != ["epoch_ms", "bid", "ask", "bid_vol", "ask_vol"]:
                print(f"WARNING: unexpected header in {src}: {header}", file=sys.stderr)
            buf = io.BytesIO()
            for row in reader:
                epoch_ms = int(row[0])
                bid = float(row[1])
                ask = float(row[2])
                shifted = epoch_ms + shift_ms
                if epoch_first is None:
                    epoch_first = shifted
                epoch_last = shifted
                buf.write(struct.pack(RECORD_FMT, shifted, bid, ask))
                n_written += 1
                if buf.tell() >= 1 << 20:  # flush every ~1MB
                    outh.write(buf.getvalue())
                    buf = io.BytesIO()
            outh.write(buf.getvalue())

        if man_entry is not None and man_entry.get("n_ticks") != n_written:
            mismatches.append((ds, man_entry.get("n_ticks"), n_written))

        rel_path = f"{year}/{ds}.bin"
        index_rows.append([ds, n_written, epoch_first or 0, epoch_last or 0, rel_path])
        total_ticks += n_written
        total_days += 1
        if total_days % 100 == 0:
            print(f"... {total_days} days converted, {total_ticks} ticks so far", file=sys.stderr)

    index_path = out_dir / "index.csv"
    with open(index_path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["date", "n_ticks", "epoch_first_ms_shifted", "epoch_last_ms_shifted", "rel_path"])
        for row in index_rows:
            w.writerow(row)

    summary = {
        "start": args.start,
        "end": args.end,
        "gmt_offset_hours_applied": args.gmt_offset_hours,
        "days_converted": total_days,
        "total_ticks": total_ticks,
        "record_size_bytes": RECORD_SIZE,
        "missing_days": missing_days,
        "manifest_tick_count_mismatches": mismatches,
        "out_dir": str(out_dir),
        "index_csv": str(index_path),
    }
    summary_path = out_dir / "conversion_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    print(json.dumps(summary, indent=2))
    if missing_days:
        print(f"WARNING: {len(missing_days)} missing days", file=sys.stderr)
    if mismatches:
        print(f"WARNING: {len(mismatches)} days with tick-count mismatch vs manifest", file=sys.stderr)


if __name__ == "__main__":
    main()
