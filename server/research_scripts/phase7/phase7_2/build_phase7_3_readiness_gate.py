#!/usr/bin/env python3
"""Phase 7.2B sec.7 - phase7_3_readiness_gate_v1.json: cancello binario,
gate per gate, come i readiness gate gia' usati in Phase 7.0B - nessuna
media pesata. Una sequence con semantic leakage non risolto non deve
risultare READY_FOR_FORMALIZATION."""
import json
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", ".."))
PHASE72_DIR = os.path.join(ROOT, "server", "research_scripts", "phase7", "phase7_2")
sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase6_6"))
from canonical_utils import wrap_with_provenance, save_json  # noqa: E402


def load(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def main():
    seq_doc = load(os.path.join(PHASE72_DIR, "market_sequence_registry_v1.json"))
    sequences = seq_doc["sequences"]
    leakage_report = load(os.path.join(PHASE72_DIR, "sequence_semantic_leakage_guard_v1.json"))["payload"]
    contradiction_reg = load(os.path.join(PHASE72_DIR, "contradiction_registry_v1.json"))
    branch_reg = load(os.path.join(PHASE72_DIR, "conditional_branch_registry_v1.json"))
    priority_v2 = load(os.path.join(PHASE72_DIR, "research_priority_queue_v2.json"))["payload"]

    # Gate 1: ontology_branching_clean - i vecchi CG-000x superseded, nessuna
    # sequence marcata come parte di un CONTRADICTION non ancora riclassificato.
    ontology_branching_clean = (
        len(contradiction_reg["contradiction_groups"]) == 0 and
        "integrity_patch_2026_09_20" in contradiction_reg and
        len(branch_reg["branches"]) == 2
    )

    # Gate 2: semantic_leakage_guard_pass - OGNI sequence deve risultare
    # PASS dopo correzione (nessuna FAIL residua, nessuna sequence con
    # semantic_leakage_status_after_correction != PASS puo' essere
    # READY_FOR_FORMALIZATION).
    all_after_correction_pass = all(r["verdict_after_correction"] == "PASS" for r in leakage_report["results"])
    no_ready_with_unresolved_leakage = all(
        not (seq.get("semantic_leakage_status_after_correction") != "PASS" and seq["implementation_status"] == "READY_FOR_FORMALIZATION")
        for seq in sequences
    )
    semantic_leakage_guard_pass = all_after_correction_pass and no_ready_with_unresolved_leakage

    # Gate 3: priority_score_v2_generated
    priority_score_v2_generated = os.path.exists(os.path.join(PHASE72_DIR, "research_priority_queue_v2.json")) and \
        priority_v2.get("scoring_rule_ref") == "research_priority_scoring_rule_v2.json"

    # Gate 4: hindsight_penalty_active
    hindsight_penalty_active = all("hindsight_awareness" in r["components"] for r in priority_v2["all_scores"])

    # Gate 5: independent_evidence_clustering_active
    evidence_clusters = load(os.path.join(PHASE72_DIR, "evidence_cluster_registry_v1.json"))
    independent_evidence_clustering_active = len(evidence_clusters["merged_clusters"]) >= 1 and \
        all("n_independent_q3plus_clusters" in r for r in priority_v2["all_scores"])

    # Gate 6: no_nexus_outcome_data_accessed - verifica STRUTTURALE: nessuno
    # script di questa fase importa moduli/legge path di dataset NEXUS
    # (market_state, outcomes, validation, holdout).
    forbidden_tokens = ["market_state_dataset", "outcomes_holdout", "data_cache_new_period",
                        "phase7_1_run_results", "validation_access_log", "final_holdout_seal"]
    self_name = os.path.basename(os.path.abspath(__file__))
    phase72_scripts = [f for f in os.listdir(PHASE72_DIR) if f.endswith(".py") and f != self_name]
    offenders = []
    for fname in phase72_scripts:
        with open(os.path.join(PHASE72_DIR, fname), encoding="utf-8") as f:
            content = f.read()
        for tok in forbidden_tokens:
            if tok in content:
                offenders.append((fname, tok))
    no_nexus_outcome_data_accessed = len(offenders) == 0

    gates = {
        "ontology_branching_clean": ontology_branching_clean,
        "semantic_leakage_guard_pass": semantic_leakage_guard_pass,
        "priority_score_v2_generated": priority_score_v2_generated,
        "hindsight_penalty_active": hindsight_penalty_active,
        "independent_evidence_clustering_active": independent_evidence_clustering_active,
        "no_nexus_outcome_data_accessed": no_nexus_outcome_data_accessed,
    }
    unresolved_blockers = [name for name, ok in gates.items() if not ok]
    ready = len(unresolved_blockers) == 0

    payload = dict(gates)
    payload.update({
        "nexus_data_scan_offenders": offenders,
        "sequences_still_not_ready_for_formalization": [
            {"sequence_id": s["sequence_id"], "implementation_status": s["implementation_status"]}
            for s in sequences if s["implementation_status"] != "READY_FOR_FORMALIZATION"
        ],
        "unresolved_blockers": unresolved_blockers,
        "ready_for_phase_7_3": ready,
        "rule": "ready_for_phase_7_3=true SOLO se tutte le gate sopra sono vere - nessuna media pesata, nessun punteggio.",
    })
    save_json(os.path.join(PHASE72_DIR, "phase7_3_readiness_gate_v1.json"), wrap_with_provenance(payload, "phase7/phase7_2/build_phase7_3_readiness_gate.py"))
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    return ready


if __name__ == "__main__":
    ready = main()
    sys.exit(0 if ready else 1)
