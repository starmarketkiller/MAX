#!/usr/bin/env python3
"""Phase 6.6 sec.9 - Artifact Manifest: SHA-256 di ogni artifact prodotto
in questa fase, path relativi (MAI assoluti), schema_version dichiarata,
generated_from (quale script l'ha prodotto), generator script/versione.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from canonical_utils import wrap_with_provenance, save_json, rel_path, file_sha256  # noqa: E402

PHASE66_DIR = os.path.dirname(os.path.abspath(__file__))

ARTIFACTS = [
    {"file": "evidence_record_v2.schema.json", "schema_version": 2, "generated_from": None, "generator": None},
    {"file": "h006_evidence_v2.json", "schema_version": 2, "generated_from": ["server/research_scripts/phase6/h006_primary_result.json", "server/research_scripts/phase6_5/h006_dependence_audit.json", "server/research_scripts/phase6_5/h006_block_bootstrap_audit.json", "server/research_scripts/phase6_5/h006_directional_baseline_v3.json"], "generator": "build_h006_evidence_v2.py"},
    {"file": "h006_decision_card_v2.json", "schema_version": 1, "generated_from": ["server/research_scripts/phase6/h006_primary_result.json", "server/research_scripts/phase6_5/h006_dependence_audit.json"], "generator": "build_h006_decision_card_v2.py"},
    {"file": "post_hoc_observations_v1.json", "schema_version": 1, "generated_from": ["server/research_scripts/phase6_5/h006_directional_baseline_v3.json", "server/research_scripts/phase6_5/directional_diagnostics_policy.json"], "generator": "build_post_hoc_observations.py"},
    {"file": "research_evidence_ledger_v1.json", "schema_version": 1, "generated_from": ["Phase5/5.5/6/6.5 reports and artifacts (manually curated transition history)"], "generator": "build_research_ledger.py"},
    {"file": "research_relations_v1.json", "schema_version": 1, "generated_from": ["h006_evidence_v2.json", "post_hoc_observations_v1.json", "dependence_audit_gate_result_H006.json (Phase6.5)"], "generator": "build_research_relations.py"},
    {"file": "integrity_test_report.json", "schema_version": 1, "generated_from": ["h006_evidence_v2.json", "h006_decision_card_v2.json", "post_hoc_observations_v1.json", "research_evidence_ledger_v1.json", "research_relations_v1.json"], "generator": "validate_integrity.py"},
    {"file": "canonical_utils.py", "schema_version": None, "generated_from": None, "generator": None},
    {"file": "build_h006_evidence_v2.py", "schema_version": None, "generated_from": None, "generator": None},
    {"file": "build_h006_decision_card_v2.py", "schema_version": None, "generated_from": None, "generator": None},
    {"file": "build_post_hoc_observations.py", "schema_version": None, "generated_from": None, "generator": None},
    {"file": "build_research_ledger.py", "schema_version": None, "generated_from": None, "generator": None},
    {"file": "build_research_relations.py", "schema_version": None, "generated_from": None, "generator": None},
    {"file": "validate_integrity.py", "schema_version": None, "generated_from": None, "generator": None},
]


def build():
    entries = []
    for a in ARTIFACTS:
        path = os.path.join(PHASE66_DIR, a["file"])
        if not os.path.exists(path):
            continue
        entries.append({
            "relative_path": rel_path(path),
            "sha256": file_sha256(path),
            "schema_version": a["schema_version"],
            "generated_from": a["generated_from"],
            "generator_script": a["generator"],
        })
    manifest = {
        "schema_version": 1,
        "phase": "Phase6.6",
        "entries": entries,
        "n_artifacts": len(entries),
        "rule": "Nessun path locale assoluto - tutti i relative_path sono relativi alla root del repository.",
    }
    return manifest


if __name__ == "__main__":
    manifest = build()
    wrapped = wrap_with_provenance(manifest, script="server/research_scripts/phase6_6/build_artifact_manifest.py")
    out_path = os.path.join(PHASE66_DIR, "artifact_manifest.json")
    save_json(out_path, wrapped)
    print(json_summary := f"n_artifacts={manifest['n_artifacts']}")
    for e in manifest["entries"]:
        print(f"  {e['relative_path']}: {e['sha256'][:16]}...")
    print(f"\nwritten: {out_path}")
