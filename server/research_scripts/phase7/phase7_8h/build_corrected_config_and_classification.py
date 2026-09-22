#!/usr/bin/env python3
"""Phase 7.8H - Minimal config correction + classificazione esplicita.

Parte ESATTAMENTE dal tester config finale congelato in 7.8F e aggiunge
UN SOLO campo: InpStrat_VolBreakoutConfirmed=true (il master-switch
mancante, root cause del run 7.8G a 0 trade). Nessun altro input cambia.
Il run 7.8G resta classificato TECHNICALLY_INVALID_ZERO_TRADE_RUN, MAI
reinterpretato come FAIL/INSUFFICIENT_SAMPLE.
"""
import os
import sys

PHASE78H_DIR = os.path.dirname(os.path.abspath(__file__))
PHASE7_DIR = os.path.abspath(os.path.join(PHASE78H_DIR, ".."))
ROOT = os.path.abspath(os.path.join(PHASE78H_DIR, "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase6_6"))
from canonical_utils import canonical_sha256, load_json, save_json, wrap_with_provenance  # noqa: E402

PRIOR_78F_PATH = os.path.join(PHASE7_DIR, "phase7_8f", "volatility_breakout_execution_config_audit_v1.json")
PRIOR_78G_ROOT_CAUSE_PATH = os.path.join(PHASE7_DIR, "phase7_8g", "volatility_breakout_zero_trade_root_cause_v1.json")


def build():
    prior_78f_doc = load_json(PRIOR_78F_PATH)
    prior_78g_rc_doc = load_json(PRIOR_78G_ROOT_CAUSE_PATH)
    frozen_78f_text = prior_78f_doc["payload"]["tester_execution_config_final"]["raw_text"]

    lines = frozen_78f_text.splitlines()
    insert_at = lines.index("InpUseStrategyProfiles=true") + 1
    new_lines = lines[:insert_at] + ["InpStrat_VolBreakoutConfirmed=true"] + lines[insert_at:]
    corrected_text = "\n".join(new_lines)

    added_lines = [ln for ln in new_lines if ln not in lines]
    removed_lines = [ln for ln in lines if ln not in new_lines]

    tester_config_corrected = {
        "base": "server/research_scripts/phase7/phase7_8f/volatility_breakout_execution_config_audit_v1.json"
               " (tester_execution_config_final.raw_text, invariato)",
        "base_sha256": prior_78f_doc["payload"]["tester_execution_config_final"]["sha256"],
        "raw_text": corrected_text,
        "sha256": canonical_sha256({"tester_config_text": corrected_text}),
        "single_field_added": "InpStrat_VolBreakoutConfirmed=true",
        "fields_added": added_lines,
        "fields_removed": removed_lines,
        "not_launched_yet_at_build_time": True,
    }

    correction_classification = {
        "correction_type": "TECHNICAL_ENABLEMENT_FIX",
        "changes_strategy_identity": False,
        "changes_strategy_parameters": False,
        "changes_verdict_rules": False,
        "changes_data_window": False,
        "rationale": "InpStrategySelector=56 indicava gia' VOLATILITY_BREAKOUT_CONFIRMED come strategia "
                    "da testare (verificato in tutte le fasi 7.8B-7.8F). Il master-switch dimenticato "
                    "(InpStrat_VolBreakoutConfirmed, default false) impediva SOLO al codice di "
                    "raggiungere la funzione del segnale (return immediato di DIR_NONE) - non introduce, "
                    "modifica o rimuove alcuna logica di rilevazione/rischio/uscita della strategia.",
        "prior_run_classification": {
            "run_id": "7.8G_run1",
            "classification": "TECHNICALLY_INVALID_ZERO_TRADE_RUN",
            "not_reinterpreted_as": ["FAIL", "INSUFFICIENT_SAMPLE", "BORDERLINE", "PASS"],
            "source_root_cause_artifact_sha256": prior_78g_rc_doc["canonical_sha256"],
            "archived_separately_and_unmodified": True,
        },
        "single_field_diff": {
            "added": added_lines,
            "removed": removed_lines,
            "is_exactly_one_field": len(added_lines) == 1 and len(removed_lines) == 0,
        },
    }

    return tester_config_corrected, correction_classification


def main():
    tester_config_corrected, correction_classification = build()
    payload = {
        "phase": "7.8H",
        "artifact_role": "CORRECTED_CONFIG_AND_CLASSIFICATION",
        "candidate_id": "VOLATILITY_BREAKOUT_CONFIRMED",
        "tester_execution_config_corrected": tester_config_corrected,
        "correction_classification": correction_classification,
        "serious_validation_not_executed_at_this_step": True,
    }
    doc = wrap_with_provenance(payload, os.path.basename(__file__))
    out_path = os.path.join(PHASE78H_DIR, "volatility_breakout_corrected_config_v1.json")
    save_json(out_path, doc)
    print(f"canonical_sha256={doc['canonical_sha256']}")
    print(f"corrected_tester_config_sha256={tester_config_corrected['sha256']}")
    print(f"single_field_diff={correction_classification['single_field_diff']}")
    return doc


if __name__ == "__main__":
    main()
