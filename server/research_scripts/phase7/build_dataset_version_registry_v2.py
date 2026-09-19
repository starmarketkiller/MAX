#!/usr/bin/env python3
"""Phase 7.0B sec.8 - Registra il dataset REALE appena acquisito
(server/research_scripts/phase7/data_cache_new_period/) in
dataset_version_registry_v2.json, usando engine/dataset_version_guard.py
- non un esempio sintetico, l'hash del dataset realmente scaricato.
"""
import json
import os
import sys

PHASE7_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(PHASE7_DIR, "engine"))
sys.path.insert(0, os.path.join(PHASE7_DIR, "..", "phase6_6"))

from dataset_version_guard import DatasetVersionRegistry, compute_manifest_content_hash  # noqa: E402
from canonical_utils import save_json  # noqa: E402

MANIFEST_PATH = os.path.join(PHASE7_DIR, "data_cache_new_period", "manifest.json")
REGISTRY_PATH = os.path.join(PHASE7_DIR, "dataset_version_registry_v2.json")
DATASET_ID = "DUKASCOPY_NEWPERIOD_2023H1_ONWARD_V1"


def main():
    manifest_hash = compute_manifest_content_hash(MANIFEST_PATH)
    with open(MANIFEST_PATH, encoding="utf-8") as f:
        manifest = json.load(f)
    dates = sorted(manifest.keys())

    components = {
        "source_manifest_hash": manifest_hash,
        "date_range": [dates[0], dates[-1]] if dates else [None, None],
        "instrument": "XAUUSD",
        "timeframe": "TICK",
        "transform_version": "phase7_dukascopy_downloader_v1 (identico al downloader Phase 4/6, solo START/END/ROOT diversi)",
    }

    registry = DatasetVersionRegistry(REGISTRY_PATH)
    result = registry.register_or_check(DATASET_ID, components)
    registry.save()

    print(f"dataset_id={DATASET_ID}")
    print(f"status={result['status']}")
    print(f"hash={result['hash']}")
    print(f"n_days_in_manifest={len(dates)} date_range={components['date_range']}")
    print(f"written: {REGISTRY_PATH}")
    return result


if __name__ == "__main__":
    main()
