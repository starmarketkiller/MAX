#!/usr/bin/env python3
"""Phase 6.6 sec.3 - normalizza H006 (Phase 6 primary result + Phase 6.5
audit metodologico) nello schema canonico evidence_record_v2.

VINCOLO ASSOLUTO (sec.1 della richiesta): questo script NON ricalcola
NULLA - legge solo gli artifact gia' prodotti in Phase 6/Phase 6.5 e li
riformatta. Il grade/conclusion AUTORITATIVI restano quelli di
`primary_evidence` (Phase 6, invariati: E2, BORDERLINE). Il blocco
`retroactive_methodological_audit` (Phase 6.5) e' tenuto SEPARATO,
nessuna fusione epistemica: non ha un proprio "grade" che possa
sovrascrivere quello primario, ha `evidence_type: RETROACTIVE_METHODOLOGICAL_AUDIT`
e `conclusion: AUDIT_ONLY` per costruzione.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from canonical_utils import ROOT, load_json, save_json, wrap_with_provenance, rel_path, file_sha256  # noqa: E402

PHASE5_DIR = os.path.join(ROOT, "server", "research_scripts", "phase5")
PHASE55_DIR = os.path.join(ROOT, "server", "research_scripts", "phase5_5")
PHASE6_DIR = os.path.join(ROOT, "server", "research_scripts", "phase6")
PHASE65_DIR = os.path.join(ROOT, "server", "research_scripts", "phase6_5")
PHASE66_DIR = os.path.dirname(os.path.abspath(__file__))

HYPOTHESIS_ID = "H006_LIQUIDITY_SWEEP_RECLAIM_TRUE_HOLDOUT"


def build():
    p6_file = os.path.join(PHASE6_DIR, "h006_primary_result.json")
    p6 = load_json(p6_file)["primary_result"]
    spec_file = os.path.join(PHASE6_DIR, "H006_frozen_spec.json")
    spec = load_json(spec_file)
    holdout_decl_file = os.path.join(PHASE6_DIR, "true_holdout_declaration.json")

    leakage_file = os.path.join(PHASE55_DIR, "leakage_guard_report_v1.json")
    leakage = load_json(leakage_file)

    dep_file = os.path.join(PHASE65_DIR, "h006_dependence_audit.json")
    dep = load_json(dep_file)
    boot_file = os.path.join(PHASE65_DIR, "h006_block_bootstrap_audit.json")
    boot = load_json(boot_file)
    dirb_file = os.path.join(PHASE65_DIR, "h006_directional_baseline_v3.json")
    dirb = load_json(dirb_file)
    gate_file = os.path.join(PHASE65_DIR, "dependence_audit_gate_result_H006.json")
    gate = load_json(gate_file)

    # ---------------- PRIMARY_EVIDENCE (Phase 6, invariata) ----------------
    primary_evidence = {
        "identity": {
            "evidence_id": "EVD-H006-PRIMARY-001",
            "schema_version": 2,
            "hypothesis_id": HYPOTHESIS_ID,
            "experiment_id": "EXP-P6-001-H006-TRUE-HOLDOUT",
            "dataset_id": "DUKASCOPY_HOLDOUT_2022H2_2023H1_V1",
            "created_at": "2026-09-18T00:00:00Z",
            "source_phase": "Phase6",
        },
        "evidence_classification": {
            "evidence_grade": "E2",
            "evidence_type": "PRIMARY_EVIDENCE",
            "validation_integrity": "TEMPORAL_HOLDOUT",
            "conclusion": p6["VERDICT"],
            "grade_cap_reason": None,
        },
        "effect": {
            "primary_outcome": spec["primary_outcome"]["definition"],
            "event_probability": p6["event_probability"],
            "baseline_probability": p6["baseline_probability"],
            "delta_p": p6["delta_p"],
            "delta_e": p6["delta_e_mfe_atr"],
            "materiality_threshold": spec["minimum_material_effect"]["delta_p_minimum"],
        },
        "sample": {
            "n_nominal": p6["n_events"],
            "n_effective": None,
            "n_clusters": None,
            "largest_cluster": None,
            "overlap_rate": None,
            "dependence_flag": None,
        },
        "uncertainty": {
            "wilson_ci": {
                "event": [p6["event_probability"]["wilson_ci95_low"], p6["event_probability"]["wilson_ci95_high"]],
                "baseline": [p6["baseline_probability"]["wilson_ci95_low"], p6["baseline_probability"]["wilson_ci95_high"]],
                "non_overlapping": p6["ci95_non_overlapping"],
            },
            "posterior_interval": {
                "event": [p6["event_probability"]["beta_binomial"]["posterior_ci95_low"], p6["event_probability"]["beta_binomial"]["posterior_ci95_high"]],
                "baseline": [p6["baseline_probability"]["beta_binomial"]["posterior_ci95_low"], p6["baseline_probability"]["beta_binomial"]["posterior_ci95_high"]],
            },
            "iid_bootstrap_ci": None,
            "dependence_aware_ci": None,
            "bootstrap_method": None,
            "block_length": None,
        },
        "baseline": {
            "baseline_engine_version": "v2 (coarsened + nearest-neighbour standardized, frozen normalization from Phase 5 discovery)",
            "matching_method": "coarsened(vol,trend,year) + NN standardized, direction-conditioned per-event",
            "direction_aware": True,
            "match_quality": p6["match_quality_distribution"],
        },
        "integrity": {
            "leakage_guard": None,
            "dependence_audit": None,
            "multiple_testing_status": "family_size=1 (unica ipotesi primaria, sec.7 Phase6)",
            "preregistration_status": "H006_frozen_spec.json congelata prima di acquisire il dataset di holdout",
            "detector_frozen": True,
        },
        "provenance": {
            "source_files": [rel_path(p6_file), rel_path(spec_file), rel_path(holdout_decl_file)],
            "source_hashes": {
                rel_path(p6_file): file_sha256(p6_file),
                rel_path(spec_file): file_sha256(spec_file),
                rel_path(holdout_decl_file): file_sha256(holdout_decl_file),
            },
            "code_commit": "b9414e6",
            "limitations": [
                "Holdout dalla stessa fonte dati di Phase 5 (Dukascopy) - TEMPORAL_HOLDOUT, non CROSS_FEED (E4)",
                "n_effective/dependence non calcolati al momento di questo record - vedi retroactive_methodological_audit",
            ],
            "conflicts": [],
        },
    }

    # ---------------- RETROACTIVE_METHODOLOGICAL_AUDIT (Phase 6.5) ----------------
    ess = dep["n_effective"]
    retroactive_audit = {
        "identity": {
            "evidence_id": "EVD-H006-AUDIT-001",
            "schema_version": 2,
            "hypothesis_id": HYPOTHESIS_ID,
            "experiment_id": "EXP-P6.5-001-H006-DEPENDENCE-AUDIT",
            "dataset_id": "DUKASCOPY_HOLDOUT_2022H2_2023H1_V1",
            "created_at": "2026-09-18T00:00:00Z",
            "source_phase": "Phase6.5",
        },
        "evidence_classification": {
            "evidence_grade": None,
            "evidence_type": "RETROACTIVE_METHODOLOGICAL_AUDIT",
            "validation_integrity": "NOT_APPLICABLE",
            "conclusion": "AUDIT_ONLY",
            "grade_cap_reason": (
                "dependence_flag=HIGH (overlap_rate={:.3f}, largest_cluster={}): anche se il DeltaP nominale "
                "fosse stato sopra soglia, questo audit avrebbe comunque richiesto un grade_cap_reason esplicito "
                "prima di qualunque promozione - non applicabile qui perche' H006 NON e' stato promosso "
                "(resta E2 per decisione di Phase 6, non per questo audit)."
            ).format(dep["overlap_rate"], dep["largest_cluster"]),
        },
        "effect": {
            "primary_outcome": None,
            "event_probability": None,
            "baseline_probability": None,
            "delta_p": None,
            "delta_e": None,
            "materiality_threshold": None,
        },
        "sample": {
            "n_nominal": dep["n_nominal"],
            "n_effective": {
                "cluster_count_approximation": ess["cluster_count_approximation"],
                "autocorrelation_based": ess["autocorrelation_based"],
                "block_bootstrap_variance_based": boot["ess_from_block_bootstrap_variance"],
                "methods_agree": False,
            },
            "n_clusters": dep["n_clusters"],
            "largest_cluster": dep["largest_cluster"],
            "overlap_rate": dep["overlap_rate"],
            "dependence_flag": dep["dependence_flag"],
        },
        "uncertainty": {
            "wilson_ci": None,
            "posterior_interval": None,
            "iid_bootstrap_ci": [boot["iid_bootstrap"]["ci_low"], boot["iid_bootstrap"]["ci_high"]],
            "dependence_aware_ci": [boot["block_bootstrap"]["ci_low"], boot["block_bootstrap"]["ci_high"]],
            "bootstrap_method": "moving block bootstrap",
            "block_length": boot["block_bootstrap"]["block_length"],
        },
        "baseline": {
            "baseline_engine_version": "v3 (directional - BUY-vs-BUY, SELL-vs-SELL, frozen normalization)",
            "matching_method": dirb["methodology"],
            "direction_aware": True,
            "match_quality": dirb["match_quality_distribution"],
        },
        "integrity": {
            "leakage_guard": leakage["overall_verdict"],
            "dependence_audit": gate["verdict"],
            "multiple_testing_status": "N/A - audit retroattivo, non un nuovo test di ipotesi",
            "preregistration_status": "N/A - audit metodologico eseguito dopo il fatto per costruzione (e' un audit, non un test)",
            "detector_frozen": True,
        },
        "provenance": {
            "source_files": [rel_path(dep_file), rel_path(boot_file), rel_path(dirb_file), rel_path(gate_file), rel_path(leakage_file)],
            "source_hashes": {
                rel_path(dep_file): file_sha256(dep_file),
                rel_path(boot_file): file_sha256(boot_file),
                rel_path(dirb_file): file_sha256(dirb_file),
                rel_path(gate_file): file_sha256(gate_file),
                rel_path(leakage_file): file_sha256(leakage_file),
            },
            "code_commit": "0e78972",
            "limitations": [
                "I tre metodi di n_effective divergono sostanzialmente (46/115/91.1) - nessuno e' trattato come definitivo",
                "Il block bootstrap e' applicato alla sola sequenza di eventi, non al pool di baseline (limite dichiarato in Phase 6.5)",
                "Questo record NON PUO' essere usato per cambiare evidence_classification.evidence_grade di primary_evidence",
            ],
            "conflicts": [],
        },
    }

    record = {
        "hypothesis_id": HYPOTHESIS_ID,
        "authoritative_grade_source": "primary_evidence",
        "authoritative_statement": "Il grade E2 e il verdetto BORDERLINE di H006 sono determinati ESCLUSIVAMENTE da primary_evidence. retroactive_methodological_audit non ha autorita' di modificarli (nessuna fusione epistemica, per costruzione dello schema).",
        "primary_evidence": primary_evidence,
        "retroactive_methodological_audit": retroactive_audit,
    }
    return record


if __name__ == "__main__":
    record = build()
    wrapped = wrap_with_provenance(record, script="server/research_scripts/phase6_6/build_h006_evidence_v2.py")
    out_path = os.path.join(PHASE66_DIR, "h006_evidence_v2.json")
    save_json(out_path, wrapped)
    print(f"canonical_sha256: {wrapped['canonical_sha256']}")
    print(f"written: {out_path}")
