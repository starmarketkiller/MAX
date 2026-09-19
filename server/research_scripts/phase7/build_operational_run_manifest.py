#!/usr/bin/env python3
"""Phase 7.0B sec.18 - discovery_run_manifest_v2.json OPERATIVO (non
sintetico) per la run di readiness assessment stessa. mode=
OPERATIONAL_READINESS_ONLY - questa run non esegue discovery, assembla
solo i riferimenti di versione dei componenti gia' costruiti.
"""
import json
import os
import subprocess
import sys
from datetime import datetime, timezone

PHASE7_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(PHASE7_DIR, "..", "..", ".."))
sys.path.insert(0, os.path.join(PHASE7_DIR, "..", "phase6_6"))
from canonical_utils import wrap_with_provenance, save_json, canonical_sha256  # noqa: E402


def read_json(path):
    if not os.path.exists(path):
        return None
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def content_hash(obj):
    """Alcuni artifact Phase 7 (es. feature_registry_v2.json) sono stati
    scritti PRIMA di canonical_utils.wrap_with_provenance (introdotto in
    Phase 6.6) e restano JSON piatti senza campo canonical_sha256 - qui
    si calcola l'hash al volo per uniformita', senza modificare il file
    originale (fuori scope di questa fase)."""
    if obj is None:
        return None
    if "canonical_sha256" in obj:
        return obj["canonical_sha256"]
    return canonical_sha256(obj)


def get_commit():
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO_ROOT, text=True).strip()
    except Exception:
        return "UNKNOWN"


def main():
    feature_registry = read_json(os.path.join(PHASE7_DIR, "feature_registry_v2.json"))
    baseline_contract = read_json(os.path.join(PHASE7_DIR, "baseline_contract_v4.json"))
    partition_contract = read_json(os.path.join(PHASE7_DIR, "partition_contract_v2.json"))
    detector_health = read_json(os.path.join(PHASE7_DIR, "event_detector_health_v1.json"))
    candidate_gen_policy = read_json(os.path.join(PHASE7_DIR, "policies", "candidate_generation_policy.json"))
    threshold_policy = read_json(os.path.join(PHASE7_DIR, "policies", "threshold_policy.json"))
    dataset_registry = read_json(os.path.join(PHASE7_DIR, "dataset_version_registry_v2.json"))
    holdout_seal = read_json(os.path.join(PHASE7_DIR, "final_holdout_seal_v1.json"))
    partition_manifest = read_json(os.path.join(PHASE7_DIR, "partition_manifest_v1.json"))

    dataset_hash = None
    if dataset_registry:
        # dataset_version_registry_v2.json non usa l'involucro canonico
        # (e' scritto direttamente da DatasetVersionRegistry.save(), un
        # dict piatto {dataset_id: entry}) - a differenza degli altri
        # artifact di Phase 7 che passano da wrap_with_provenance().
        entry = dataset_registry.get("DUKASCOPY_NEWPERIOD_2023H1_ONWARD_V1")
        dataset_hash = entry["hash"] if entry else None

    payload = {
        "run_id": "PHASE7_0B-OPERATIONAL-READINESS-001",
        "mode": "OPERATIONAL_READINESS_ONLY",
        "readiness_only_no_discovery_flag": True,
        "purpose": "Assemblare/verificare le versioni dei componenti dell'infrastruttura di discovery - NON esegue alcuna discovery, nessun H007, nessun edge, nessun backtest.",
        "code_commit": get_commit(),
        "dataset_version": {
            "dataset_id": "DUKASCOPY_NEWPERIOD_2023H1_ONWARD_V1",
            "hash": dataset_hash,
            "registry_file": "server/research_scripts/phase7/dataset_version_registry_v2.json",
        },
        "feature_registry_version": {
            "hash": content_hash(feature_registry),
            "file": "server/research_scripts/phase7/feature_registry_v2.json",
        },
        "baseline_contract_version": {
            "contract_id": baseline_contract.get("contract_id") if baseline_contract else None,
            "schema_version": baseline_contract.get("schema_version") if baseline_contract else None,
            "file": "server/research_scripts/phase7/baseline_contract_v4.json",
        },
        "partition_contract_version": {
            "contract_id": partition_contract.get("contract_id") if partition_contract else None,
            "file": "server/research_scripts/phase7/partition_contract_v2.json",
        },
        "detector_health_version": {
            "hash": content_hash(detector_health),
            "file": "server/research_scripts/phase7/event_detector_health_v1.json",
        },
        "candidate_generation_policy_version": {
            "hash": content_hash(candidate_gen_policy),
            "file": "server/research_scripts/phase7/policies/candidate_generation_policy.json",
        },
        "threshold_policy_version": {
            "file": "server/research_scripts/phase7/policies/threshold_policy.json",
        },
        "multiple_testing_family_policy_reference": "server/research_scripts/phase7/engine/multiple_testing_v2.py (run_family)",
        "access_ledger_reference": "server/research_scripts/phase7/engine/validation_access_ledger.py + policies/validation_access_policy_v1.json",
        "holdout_sealed_status": holdout_seal["payload"]["sealed_status"] if holdout_seal else "NOT_SEALED",
        "partition_materialized": partition_manifest["payload"]["materialized"] if partition_manifest else False,
        "generated_at_declared": datetime.now(timezone.utc).isoformat(),
    }
    out_path = os.path.join(PHASE7_DIR, "discovery_run_manifest_v2.json")
    save_json(out_path, wrap_with_provenance(payload, "phase7/build_operational_run_manifest.py"))
    print(json.dumps(payload, indent=2, default=str, ensure_ascii=False))
    print(f"\nwritten: {out_path}")


if __name__ == "__main__":
    main()
