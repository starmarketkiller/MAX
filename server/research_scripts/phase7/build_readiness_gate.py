#!/usr/bin/env python3
"""Phase 7.0B sec.21-22 - phase7_1_readiness_gate_v1.json: cancello
binario, hard blocker per hard blocker - NESSUNA media pesata. Legge gli
artifact gia' prodotti dalle fasi precedenti di Phase 7.0B (mai
ricalcola nulla da solo) e verifica che OGNI gate richiesta sia vera.

ready_for_phase_7_1=true SOLO se tutte le gate hard sono chiuse.
"""
import json
import os
import sys

PHASE7_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(PHASE7_DIR, "..", "phase6_6"))
from canonical_utils import wrap_with_provenance, save_json  # noqa: E402


def read_json(path):
    if not os.path.exists(path):
        return None
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def main():
    preflight_manifest = read_json(os.path.join(PHASE7_DIR, "preflight_output", "discovery_run_manifest_v2.json"))
    integrity_report = read_json(os.path.join(PHASE7_DIR, "new_dataset_integrity_report_v1.json"))
    partition_manifest = read_json(os.path.join(PHASE7_DIR, "partition_manifest_v1.json"))
    holdout_seal = read_json(os.path.join(PHASE7_DIR, "final_holdout_seal_v1.json"))
    detector_health = read_json(os.path.join(PHASE7_DIR, "event_detector_health_v1.json"))
    baseline_quality = read_json(os.path.join(PHASE7_DIR, "baseline_quality_report_v4.json"))

    preflight_checks = preflight_manifest["payload"]["checks_detail"] if preflight_manifest else []
    preflight_n_fail = preflight_manifest["payload"]["checks_summary"]["n_fail"] if preflight_manifest else None

    def check_names_pass(*names):
        by_name = {c["check"]: c["status"] for c in preflight_checks}
        return all(by_name.get(n) == "PASS" for n in names)

    gates = {}
    gates["baseline_engine_v4_implemented"] = os.path.exists(os.path.join(PHASE7_DIR, "engine", "baseline_engine_v4.py")) and baseline_quality is not None
    gates["baseline_split_safe"] = check_names_pass("baseline_v4_cross_split_blocked", "baseline_full_pass_no_violations_when_correct", "baseline_corrupted_case_detected")
    gates["baseline_direction_aware"] = check_names_pass("baseline_v4_direction_mismatch_blocked")
    gates["event_firing_rate_guard_pass"] = check_names_pass("event_firing_rate_pathological_detector_blocked", "event_firing_rate_normal_detector_allowed") and detector_health is not None
    gates["validation_access_guard_pass"] = check_names_pass("second_locked_validation_access_blocked", "second_final_holdout_access_blocked")
    gates["holdout_one_shot_enforced"] = gates["validation_access_guard_pass"]
    gates["dataset_version_guard_pass"] = check_names_pass("dataset_identical_rebuild_same_hash")
    gates["dataset_drift_guard_pass"] = check_names_pass("dataset_drift_detected")
    gates["new_dataset_integrity_pass"] = bool(integrity_report and integrity_report["payload"]["verdict"] in ("PASS", "PASS_WITH_NOTES"))
    gates["partition_materialized"] = bool(partition_manifest and partition_manifest["payload"]["materialized"])
    gates["final_holdout_sealed"] = bool(holdout_seal and holdout_seal["payload"]["sealed_status"] == "SEALED")
    gates["fit_isolation_pass"] = check_names_pass("fit_on_validation_blocked")
    gates["preflight_pass"] = preflight_n_fail == 0

    unresolved_blockers = [name for name, ok in gates.items() if not ok]
    # Gap noti dichiarati esplicitamente (Phase 7.0/7.0B), che restano
    # aperti anche quando le gate tecniche sopra passano tutte - non
    # sono blocker HARD di questo gate (non c'e' codice da verificare
    # per loro in questa fase), ma vanno comunque riportati.
    known_declared_gaps = [
        "CANDIDATE_SURVIVORSHIP (rischio di processo, non chiudibile con solo codice)",
        "feed_robustness/market_transferability restano UNTESTED (singolo feed/mercato - vedi cross_market_readiness_policy.json)",
    ]

    ready = len(unresolved_blockers) == 0

    payload = {
        "baseline_engine_v4_implemented": gates["baseline_engine_v4_implemented"],
        "baseline_split_safe": gates["baseline_split_safe"],
        "baseline_direction_aware": gates["baseline_direction_aware"],
        "event_firing_rate_guard_pass": gates["event_firing_rate_guard_pass"],
        "validation_access_guard_pass": gates["validation_access_guard_pass"],
        "holdout_one_shot_enforced": gates["holdout_one_shot_enforced"],
        "dataset_version_guard_pass": gates["dataset_version_guard_pass"],
        "dataset_drift_guard_pass": gates["dataset_drift_guard_pass"],
        "new_dataset_integrity_pass": gates["new_dataset_integrity_pass"],
        "partition_materialized": gates["partition_materialized"],
        "final_holdout_sealed": gates["final_holdout_sealed"],
        "fit_isolation_pass": gates["fit_isolation_pass"],
        "preflight_pass": gates["preflight_pass"],
        "preflight_n_fail": preflight_n_fail,
        "unresolved_blockers": unresolved_blockers,
        "known_declared_gaps_not_counted_as_hard_blockers": known_declared_gaps,
        "ready_for_phase_7_1": ready,
        "rule": "ready_for_phase_7_1=true SOLO se tutti i blocker hard sopra sono chiusi - nessuna media pesata, nessun punteggio.",
    }
    out_path = os.path.join(PHASE7_DIR, "phase7_1_readiness_gate_v1.json")
    save_json(out_path, wrap_with_provenance(payload, "phase7/build_readiness_gate.py"))
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    print(f"\nwritten: {out_path}")
    return ready


if __name__ == "__main__":
    ready = main()
    sys.exit(0 if ready else 1)
