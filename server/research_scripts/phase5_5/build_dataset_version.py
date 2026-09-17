#!/usr/bin/env python3
"""Phase 5.5 sec.14 - Dataset Versioning.

Calcola un dataset_id REALE (hash SHA256 dei file sorgente + metadata)
per market_state_dataset_v1, cosi' che un cambiamento futuro in
qualunque componente che PUO' modificare i risultati (barre, feature,
detector eventi) cambi visibilmente la versione.
"""
import hashlib
import json
import os
from datetime import datetime, timezone

ROOT = r"C:\Users\User\ClaudeWork\MAX"
PHASE5_DATA = os.path.join(ROOT, "server", "research_scripts", "phase5", "data")
MANIFEST_PATH = os.path.join(ROOT, "server", "data_cache", "dukascopy_phaseH", "manifest.json")
OUT_JSON = os.path.join(ROOT, "server", "research_scripts", "phase5_5", "dataset_version_v1.json")


def sha256_file(path, max_bytes=None):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        if max_bytes:
            h.update(f.read(max_bytes))
        else:
            for chunk in iter(lambda: f.read(1 << 20), b""):
                h.update(chunk)
    return h.hexdigest()


def sha256_manifest_summary(path):
    """Hash di un riassunto deterministico del manifest (non del file
    intero, che e' enorme e contiene ordine di dict non garantito) -
    conta/somma per giorno, ordinato, cosi' l'hash e' stabile e
    riproducibile a parita' di contenuto logico."""
    m = json.load(open(path, encoding="utf-8"))
    rows = []
    for day in sorted(m.keys()):
        v = m[day]
        rows.append(f"{day}:{v.get('n_ticks')}:{v.get('n_hours_ok')}:{v.get('n_hours_empty')}:{v.get('n_hours_failed')}")
    blob = "\n".join(rows).encode("utf-8")
    return hashlib.sha256(blob).hexdigest(), len(rows)


def main():
    tick_manifest_hash, n_days = sha256_manifest_summary(MANIFEST_PATH)

    files_to_hash = {
        "xauusd_h4_bars.csv": os.path.join(PHASE5_DATA, "xauusd_h4_bars.csv"),
        "market_state_dataset_v1.csv": os.path.join(PHASE5_DATA, "market_state_dataset_v1.csv"),
        "events_v1.csv": os.path.join(PHASE5_DATA, "events_v1.csv"),
        "outcomes_v1.csv": os.path.join(PHASE5_DATA, "outcomes_v1.csv"),
    }
    file_hashes = {name: sha256_file(path) for name, path in files_to_hash.items() if os.path.exists(path)}

    code_files = {
        "build_h4_bars.py": os.path.join(ROOT, "server", "research_scripts", "phase5", "build_h4_bars.py"),
        "build_market_state.py": os.path.join(ROOT, "server", "research_scripts", "phase5", "build_market_state.py"),
        "build_events.py": os.path.join(ROOT, "server", "research_scripts", "phase5", "build_events.py"),
        "build_outcomes.py": os.path.join(ROOT, "server", "research_scripts", "phase5", "build_outcomes.py"),
        "edge_discovery.py": os.path.join(ROOT, "server", "research_scripts", "phase5", "edge_discovery.py"),
    }
    code_hashes = {name: sha256_file(path) for name, path in code_files.items() if os.path.exists(path)}

    combined = "\n".join([tick_manifest_hash] + list(file_hashes.values()) + list(code_hashes.values()))
    dataset_id_hash = hashlib.sha256(combined.encode("utf-8")).hexdigest()[:16]

    record = {
        "dataset_id": f"MARKET_STATE_V1_{dataset_id_hash}",
        "schema_version": 1,
        "source_hashes": {
            "dukascopy_tick_manifest_summary_sha256": tick_manifest_hash,
            "dukascopy_manifest_n_days": n_days,
            "data_file_sha256": file_hashes,
            "code_file_sha256": code_hashes,
        },
        "time_range": {"start": "2019-02-03T00:00:00Z", "end": "2022-02-03T00:00:00Z"},
        "symbols": ["XAUUSD"],
        "timezone": "UTC (bar boundary fisso 00/04/08/12/16/20, NON server-time del broker)",
        "bar_construction": "H4 da tick Dukascopy, OHLC su BID, spread medio tracciato separatamente",
        "feature_version": "MARKET_STATE_V1 (vedi feature_provenance_registry_v1.json)",
        "event_detector_version": "EVENT_DETECTORS_V1 (vedi build_events.py CFG dict)",
        "exclusions": "nessuna barra esclusa; NaN di warmup lasciati espliciti (vedi missing_data_policy_v1.md)",
        "missingness_summary": "vedi missing_data_policy_v1.md - max 75/4809 righe (1.56%) per la colonna piu' colpita (atr_percentile), tutte confinate al warmup iniziale",
        "rule": "Se cambia una componente che puo' modificare i risultati (bar construction, feature formula/parametri, detector eventi, orizzonte outcome), il dataset_id_hash cambia perche' cambia almeno uno degli hash sorgente sopra - non serve incrementare un numero di versione a mano e sperare di ricordarsene.",
        "built_at": datetime.now(timezone.utc).isoformat(),
    }
    json.dump(record, open(OUT_JSON, "w", encoding="utf-8"), indent=2, default=str)
    print(json.dumps(record, indent=2, default=str))
    print(f"\nwritten: {OUT_JSON}")


if __name__ == "__main__":
    main()
