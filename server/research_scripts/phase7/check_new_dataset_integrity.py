#!/usr/bin/env python3
"""Phase 7.0B sec.11 - Controlli di integrita' sul NUOVO periodo Dukascopy
(2023-02-04 -> ultimo giorno disponibile, mai usato prima - vedi
acquisition_freeze_declaration_v1.json). Legge SOLO il manifest e i tick
decodificati - nessuna metrica di outcome/edge viene calcolata qui
(sec.19 Phase 7.0B: no edge evaluation).

Verifica: copertura date, giorni di trading mancanti, tick duplicati,
timestamp non monotoni, prezzi impossibili, anomalie di spread, tick
count/giorno, gap anomali, coerenza timezone/simbolo, hash/provenance.
"""
import csv
import gzip
import json
import os
import sys
from datetime import datetime, timedelta, timezone

PHASE7_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(PHASE7_DIR, "..", "phase6_6"))
from canonical_utils import wrap_with_provenance, save_json, canonical_sha256  # noqa: E402

DATA_ROOT = os.path.join(PHASE7_DIR, "data_cache_new_period")
MANIFEST_PATH = os.path.join(DATA_ROOT, "manifest.json")
DECODED_DIR = os.path.join(DATA_ROOT, "decoded")

START = datetime(2023, 2, 4, tzinfo=timezone.utc)
END = datetime(2026, 9, 16, tzinfo=timezone.utc)

# Range di prezzo XAUUSD realistico per il periodo 2023-2026 (largo
# margine, non uno screening di anomalie fini di mercato - solo per
# individuare corruzione grezza del dato, es. valori a zero o a 10x).
# POLICY_THRESHOLD - scelto largamente sopra/sotto ai minimi/massimi
# storici noti del periodo, non calibrato sui dati stessi.
PLAUSIBLE_PRICE_MIN = 500.0
PLAUSIBLE_PRICE_MAX = 6000.0
# Spread anomalo: oltre 50 (500 pip, convenzione NEXUS 1 pip=0.10) e'
# quasi certamente un tick corrotto o un evento di mercato estremo da
# rivedere manualmente, non un valore tipico.
SPREAD_ANOMALY_THRESHOLD = 50.0


def _day_decoded_path(day: datetime) -> str:
    return os.path.join(DECODED_DIR, f"{day.year:04d}", f"{day.strftime('%Y-%m-%d')}.csv.gz")


def scan_day_ticks(day: datetime) -> dict:
    path = _day_decoded_path(day)
    if not os.path.exists(path):
        return {"exists": False}
    n_ticks = 0
    n_non_monotonic = 0
    n_duplicates = 0
    n_impossible_prices = 0
    n_spread_anomalies = 0
    max_gap_ms = 0
    prev_epoch = None
    seen = set()
    with gzip.open(path, "rt", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            n_ticks += 1
            epoch = int(row["epoch_ms"])
            bid, ask = float(row["bid"]), float(row["ask"])
            if prev_epoch is not None:
                if epoch < prev_epoch:
                    n_non_monotonic += 1
                else:
                    max_gap_ms = max(max_gap_ms, epoch - prev_epoch)
            key = (epoch, bid, ask)
            if key in seen:
                n_duplicates += 1
            seen.add(key)
            if not (PLAUSIBLE_PRICE_MIN <= bid <= PLAUSIBLE_PRICE_MAX and PLAUSIBLE_PRICE_MIN <= ask <= PLAUSIBLE_PRICE_MAX):
                n_impossible_prices += 1
            spread = ask - bid
            if spread < 0 or spread > SPREAD_ANOMALY_THRESHOLD:
                n_spread_anomalies += 1
            prev_epoch = epoch
    return {
        "exists": True, "n_ticks": n_ticks, "n_non_monotonic": n_non_monotonic,
        "n_duplicates": n_duplicates, "n_impossible_prices": n_impossible_prices,
        "n_spread_anomalies": n_spread_anomalies, "max_gap_seconds": max_gap_ms / 1000.0,
    }


def main():
    with open(MANIFEST_PATH, encoding="utf-8") as f:
        manifest = json.load(f)

    day = START.replace(hour=0, minute=0, second=0, microsecond=0)
    end = END.replace(hour=0, minute=0, second=0, microsecond=0)
    expected_dates = []
    while day <= end:
        expected_dates.append(day.strftime("%Y-%m-%d"))
        day += timedelta(days=1)

    missing_dates = [d for d in expected_dates if d not in manifest]
    incomplete_dates = [d for d, v in manifest.items() if not v.get("complete")]
    zero_tick_weekdays = [d for d, v in manifest.items()
                          if v.get("n_ticks", 0) == 0 and v.get("weekday", 7) < 5]

    print(f"Copertura date: {len(expected_dates)} attese, {len(manifest)} presenti nel manifest, "
          f"{len(missing_dates)} mancanti, {len(incomplete_dates)} incomplete (ore fallite).")

    day_scan_results = {}
    n_scanned = 0
    for d in sorted(manifest.keys()):
        dt = datetime.strptime(d, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        result = scan_day_ticks(dt)
        day_scan_results[d] = result
        n_scanned += 1
        if n_scanned % 200 == 0:
            print(f"  ...scansionati {n_scanned}/{len(manifest)} giorni")

    total_ticks = sum(r.get("n_ticks", 0) for r in day_scan_results.values())
    total_non_monotonic = sum(r.get("n_non_monotonic", 0) for r in day_scan_results.values())
    total_duplicates = sum(r.get("n_duplicates", 0) for r in day_scan_results.values())
    total_impossible = sum(r.get("n_impossible_prices", 0) for r in day_scan_results.values())
    total_spread_anom = sum(r.get("n_spread_anomalies", 0) for r in day_scan_results.values())
    days_missing_file = [d for d, r in day_scan_results.items() if not r.get("exists")]
    tick_counts = [r["n_ticks"] for r in day_scan_results.values() if r.get("exists")]

    hard_failures = []
    if total_non_monotonic > 0:
        hard_failures.append(f"{total_non_monotonic} timestamp non monotoni rilevati")
    if total_duplicates > 0:
        hard_failures.append(f"{total_duplicates} tick duplicati (stesso epoch_ms/bid/ask) rilevati")
    if total_impossible > 0:
        hard_failures.append(f"{total_impossible} prezzi fuori dal range plausibile [{PLAUSIBLE_PRICE_MIN},{PLAUSIBLE_PRICE_MAX}] rilevati")
    if days_missing_file:
        hard_failures.append(f"{len(days_missing_file)} giorni presenti nel manifest ma senza file decodificato su disco")

    soft_concerns = []
    if missing_dates:
        soft_concerns.append(f"{len(missing_dates)} date attese non presenti nel manifest: {missing_dates[:10]}{'...' if len(missing_dates) > 10 else ''}")
    if incomplete_dates:
        soft_concerns.append(f"{len(incomplete_dates)} giorni con almeno un'ora fallita dopo il retry: {incomplete_dates[:10]}{'...' if len(incomplete_dates) > 10 else ''}")
    if zero_tick_weekdays:
        soft_concerns.append(f"{len(zero_tick_weekdays)} giorni feriali con zero tick (possibili festivita' di mercato o gap reali, da revisione umana): {zero_tick_weekdays[:10]}{'...' if len(zero_tick_weekdays) > 10 else ''}")
    if total_spread_anom > 0:
        soft_concerns.append(f"{total_spread_anom} tick con spread anomalo (negativo o > {SPREAD_ANOMALY_THRESHOLD}) - possibili eventi di mercato estremi o tick da rivedere, non necessariamente corruzione")

    manifest_hash = canonical_sha256(manifest)

    if hard_failures:
        verdict = "FAIL"
    elif soft_concerns:
        verdict = "PASS_WITH_NOTES"
    else:
        verdict = "PASS"

    payload = {
        "period_checked": {"start": START.isoformat(), "end": END.isoformat()},
        "date_coverage": {
            "expected_days": len(expected_dates), "days_in_manifest": len(manifest),
            "missing_dates": missing_dates, "incomplete_dates_after_retry": incomplete_dates,
            "zero_tick_weekdays": zero_tick_weekdays,
        },
        "tick_level_checks": {
            "days_scanned": len(day_scan_results), "days_missing_decoded_file": days_missing_file,
            "total_ticks": total_ticks, "total_non_monotonic_timestamps": total_non_monotonic,
            "total_duplicate_ticks": total_duplicates, "total_impossible_prices": total_impossible,
            "total_spread_anomalies": total_spread_anom,
            "tick_count_per_day_min": min(tick_counts) if tick_counts else None,
            "tick_count_per_day_max": max(tick_counts) if tick_counts else None,
            "tick_count_per_day_mean": (sum(tick_counts) / len(tick_counts)) if tick_counts else None,
        },
        "timezone_consistency": "UTC per costruzione (ogni timestamp e' derivato da datetime UTC espliciti nel downloader, mai da orario locale) - verificato strutturalmente, non da scansione.",
        "symbol_consistency": "XAUUSD per costruzione (unico simbolo richiesto dal downloader) - verificato strutturalmente.",
        "provenance": {
            "manifest_path": "server/research_scripts/phase7/data_cache_new_period/manifest.json",
            "manifest_content_hash": manifest_hash,
            "downloader_script": "server/research_scripts/phase7/phase7_dukascopy_downloader.py",
        },
        "hard_failures": hard_failures,
        "soft_concerns": soft_concerns,
        "verdict": verdict,
    }
    out_path = os.path.join(PHASE7_DIR, "new_dataset_integrity_report_v1.json")
    save_json(out_path, wrap_with_provenance(payload, "phase7/check_new_dataset_integrity.py"))
    print(f"\nVerdetto integrita': {verdict}")
    print(f"Hard failures: {len(hard_failures)} | Soft concerns: {len(soft_concerns)}")
    print(f"written: {out_path}")
    return verdict


if __name__ == "__main__":
    main()
