#!/usr/bin/env python3
"""Phase 7.0B sec.5 - Applica event_firing_rate_guard.py ai detector
REALI gia' esistenti (Phase 5, events_v1.csv/events_v1.meta.json) - SOLO
conteggi e row_index, MAI outcome/ΔP (sec.19: no edge evaluation in
questa fase). Nessun nuovo detector, nessuna ricalibrazione - stesso
codice/dati di Phase 5, letti in sola lettura.
"""
import csv
import json
import os
import sys
from collections import defaultdict

PHASE7_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(PHASE7_DIR, "..", "..", ".."))
sys.path.insert(0, os.path.join(PHASE7_DIR, "engine"))
sys.path.insert(0, os.path.join(PHASE7_DIR, "..", "phase6_6"))

from event_firing_rate_guard import build_detector_health  # noqa: E402
from canonical_utils import wrap_with_provenance, save_json  # noqa: E402

EVENTS_CSV = os.path.join(REPO_ROOT, "server", "research_scripts", "phase5", "data", "events_v1.csv")
EVENTS_META = os.path.join(REPO_ROOT, "server", "research_scripts", "phase5", "data", "events_v1.meta.json")
MARKET_STATE_CSV = os.path.join(REPO_ROOT, "server", "research_scripts", "phase5", "data", "market_state_dataset_v1.csv")


def count_bars(path: str) -> int:
    with open(path, encoding="utf-8") as f:
        return sum(1 for _ in f) - 1  # meno l'header


def main():
    n_bars = count_bars(MARKET_STATE_CSV)

    rows_by_family = defaultdict(list)
    with open(EVENTS_CSV, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            rows_by_family[row["event_family"]].append(int(row["row_index"]))

    with open(EVENTS_META, encoding="utf-8") as f:
        meta = json.load(f)

    families_health = []
    for family, row_indices in sorted(rows_by_family.items()):
        health = build_detector_health(family, n_bars, row_indices)
        families_health.append(health)

    n_pathological = sum(1 for h in families_health if h["status"] == "PATHOLOGICAL")
    n_high = sum(1 for h in families_health if h["status"] == "HIGH")

    payload = {
        "source_events_file": "server/research_scripts/phase5/data/events_v1.csv",
        "source_events_meta": "server/research_scripts/phase5/data/events_v1.meta.json",
        "source_bars_file": "server/research_scripts/phase5/data/market_state_dataset_v1.csv",
        "note": "Health strutturale (firing rate/clustering) dei detector REALI di Phase 5 - nessun outcome/ΔP calcolato qui (sec.19 Phase 7.0B: no edge evaluation). Nessun detector nuovo, nessuna ricalibrazione.",
        "n_bars_total": n_bars,
        "n_families": len(families_health),
        "n_pathological": n_pathological,
        "n_high": n_high,
        "families": families_health,
        "default_policy": "Nessun detector e' ammesso per default in una futura discovery run senza questo health assessment - un detector assente da questo file non e' 'implicitamente ammesso', e' 'non ancora valutato' (allowed_for_discovery deve essere letto esplicitamente da qui).",
    }
    out_path = os.path.join(PHASE7_DIR, "event_detector_health_v1.json")
    save_json(out_path, wrap_with_provenance(payload, "phase7/build_event_detector_health_v1.py"))
    print(f"n_bars={n_bars} n_families={len(families_health)} n_pathological={n_pathological} n_high={n_high}")
    for h in families_health:
        print(f"  {h['event_family']:24s} firing_rate={h['firing_rate']:.3f} status={h['status']:12s} allowed={h['allowed_for_discovery']}")
    print(f"written: {out_path}")


if __name__ == "__main__":
    main()
