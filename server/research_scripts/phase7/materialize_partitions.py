#!/usr/bin/env python3
"""Phase 7.0B sec.12-13 - Materializzazione dei 3 segmenti dichiarati in
partition_contract_v2.json (proposed_future_split_NOT_YET_EXECUTED) sul
nuovo periodo Dukascopy acquisito, PIU' sigillo del FINAL_HOLDOUT.

Le date di confine sono quelle GIA' dichiarate in Phase 7.0 (PRIMA che
questi dati esistessero) - non ricalcolate ora per adattarsi ai dati
osservati. Se new_dataset_integrity_report_v1.json non e' almeno
PASS_WITH_NOTES, NON materializza nulla - dichiara esplicitamente
NOT_READY_FOR_PHASE_7_1 (sec.12: 'non forzare').

Materializzazione LOGICA (per date-range), non fisica: nessun tick viene
copiato/duplicato - i segmenti sono definiti come intervalli di date sul
manifest gia' scaricato.
"""
import json
import os
import sys
from datetime import datetime, timezone

PHASE7_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(PHASE7_DIR, "..", "phase6_6"))
from canonical_utils import wrap_with_provenance, save_json, canonical_sha256  # noqa: E402

MANIFEST_PATH = os.path.join(PHASE7_DIR, "data_cache_new_period", "manifest.json")
INTEGRITY_REPORT_PATH = os.path.join(PHASE7_DIR, "new_dataset_integrity_report_v1.json")

# Confini GIA' dichiarati in partition_contract_v2.json - copiati qui
# verbatim, non ridiscussi guardando i dati.
DECLARED_SEGMENTS = [
    {"name": "development_discovery", "start": "2023-02-04", "end": "2024-08-03"},
    {"name": "development_internal_validation", "start": "2024-08-04", "end": "2025-05-03"},
    {"name": "locked_validation", "start": "2025-05-04", "end": "2026-02-03"},
    {"name": "final_holdout", "start": "2026-02-04", "end": "2026-09-16"},
]


def days_in_range(manifest: dict, start: str, end: str) -> list:
    return sorted(d for d in manifest if start <= d <= end)


def main():
    if not os.path.exists(INTEGRITY_REPORT_PATH):
        print("NOT_READY_FOR_PHASE_7_1: new_dataset_integrity_report_v1.json non esiste ancora - eseguire check_new_dataset_integrity.py prima.")
        return False
    with open(INTEGRITY_REPORT_PATH, encoding="utf-8") as f:
        integrity = json.load(f)["payload"]
    verdict = integrity["verdict"]
    if verdict == "FAIL":
        print(f"NOT_READY_FOR_PHASE_7_1: new_dataset_integrity_report_v1.json verdict={verdict} - "
              f"partizioni NON materializzate (sec.12: 'non forzare'). Hard failures: {integrity['hard_failures']}")
        return False

    with open(MANIFEST_PATH, encoding="utf-8") as f:
        manifest = json.load(f)

    segments = []
    for seg in DECLARED_SEGMENTS:
        days = days_in_range(manifest, seg["start"], seg["end"])
        n_complete = sum(1 for d in days if manifest[d].get("complete"))
        n_ticks = sum(manifest[d].get("n_ticks", 0) for d in days)
        segments.append({
            "name": seg["name"], "declared_start": seg["start"], "declared_end": seg["end"],
            "n_days_in_manifest": len(days), "n_days_complete": n_complete,
            "n_days_incomplete": len(days) - n_complete, "n_ticks_total": n_ticks,
            "first_day": days[0] if days else None, "last_day": days[-1] if days else None,
        })
        print(f"{seg['name']:34s} [{seg['start']}..{seg['end']}] giorni={len(days)} completi={n_complete} ticks={n_ticks}")

    any_empty_segment = any(s["n_days_in_manifest"] == 0 for s in segments)
    if any_empty_segment:
        print("NOT_READY_FOR_PHASE_7_1: almeno un segmento dichiarato non ha giorni disponibili nel manifest - split non sensato, non forzato.")
        payload_fail = {"materialized": False, "reason": "EMPTY_SEGMENT", "segments": segments}
        save_json(os.path.join(PHASE7_DIR, "partition_manifest_v1.json"),
                  wrap_with_provenance(payload_fail, "phase7/materialize_partitions.py"))
        return False

    partition_payload = {
        "materialized": True,
        "materialization_method": "LOGICAL (intervallo di date sul manifest esistente - nessuna duplicazione fisica dei tick)",
        "source_integrity_report_verdict": verdict,
        "segments": segments,
        "declared_before_data_existed": True,
        "declared_in": "server/research_scripts/phase7/partition_contract_v2.json (proposed_future_split_NOT_YET_EXECUTED, Phase 7.0)",
    }
    save_json(os.path.join(PHASE7_DIR, "partition_manifest_v1.json"),
              wrap_with_provenance(partition_payload, "phase7/materialize_partitions.py"))

    # Sigillo del FINAL_HOLDOUT (sec.13): manifest separato, hash congelato
    # sul SOLO sottoinsieme di manifest che ricade nel holdout, nessun
    # preprocessing-fit ammesso (enforcement in baseline_engine_v4.py -
    # FitIsolationViolation - e nel test negativo dedicato del preflight v3).
    holdout_seg = next(s for s in segments if s["name"] == "final_holdout")
    holdout_days = days_in_range(manifest, holdout_seg["declared_start"], holdout_seg["declared_end"])
    holdout_subset_manifest = {d: manifest[d] for d in holdout_days}
    holdout_hash = canonical_sha256(holdout_subset_manifest)
    seal_payload = {
        "sealed_at": datetime.now(timezone.utc).isoformat(),
        "date_range": {"start": holdout_seg["declared_start"], "end": holdout_seg["declared_end"]},
        "n_days": len(holdout_days),
        "frozen_manifest_subset_hash": holdout_hash,
        "rules": [
            "Nessun fit di scaler/soglia/normalizzazione e' ammesso su questo intervallo - vedi engine/baseline_engine_v4.py FitIsolationViolation.",
            "Accesso one-shot per candidate_id - vedi engine/validation_access_ledger.py e policies/validation_access_policy_v1.json.",
            "Qualunque lettura di questo intervallo DEVE passare da ValidationAccessLedger.record_access() - nessun accesso diretto al manifest/decoded e' un percorso legittimo per una discovery run futura.",
        ],
        "sealed_status": "SEALED",
    }
    save_json(os.path.join(PHASE7_DIR, "final_holdout_seal_v1.json"),
              wrap_with_provenance(seal_payload, "phase7/materialize_partitions.py"))

    print(f"\nPartizioni materializzate (logicamente). FINAL_HOLDOUT sigillato: {len(holdout_days)} giorni, hash={holdout_hash[:16]}...")
    return True


if __name__ == "__main__":
    ok = main()
    sys.exit(0 if ok else 1)
