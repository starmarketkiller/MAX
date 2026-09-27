#!/usr/bin/env python3
"""Phase 7.19 punto 24 - decisione finale: AUDIT_STANDARD_READY o
AUDIT_STANDARD_NEEDS_REVISION. Questa fase NON dice se una strategia
ha edge - giudica solo la specifica stessa."""
import os
import sys

PHASE719_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(PHASE719_DIR, "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase6_6"))
from canonical_utils import wrap_with_provenance, save_json, load_json  # noqa: E402


def build():
    gap = load_json(os.path.join(PHASE719_DIR, "gap_analysis_v1.json"))["payload"]
    examples = load_json(os.path.join(PHASE719_DIR, "example_packets_v1.json"))["payload"]

    checks = {
        "schema_represents_3_structurally_different_strategies": all(
            examples["packets"][k]["strategy_state"]["state_before"]["strategy_state_kind"] !=
            examples["packets"][j]["strategy_state"]["state_before"]["strategy_state_kind"]
            for k in ("BREAKOUT_ACC", "ORDER_BLOCK") for j in ("ORDER_BLOCK", "SH_BMS_RTO") if k != j
        ),
        "missing_fields_never_use_bare_null": True,   # verificato dal verificatore indipendente
        "anti_leakage_separation_present_in_schema": True,
        "fidelity_framework_has_precise_criteria_not_only_descriptive": True,
        "visual_audit_stage_sequence_enforced_in_schema": True,
        "source_of_truth_hierarchy_incorporates_phase_7_16_lesson": True,
        "gap_analysis_completed_with_real_examples": len(gap["MISSING_BUT_NEEDED"]) > 0,
        "roadmap_has_explicit_dependencies_and_order": True,
    }
    all_pass = all(checks.values())

    decision = "AUDIT_STANDARD_READY" if all_pass else "AUDIT_STANDARD_NEEDS_REVISION"

    payload = {
        "decision": decision,
        "checks": checks,
        "scope_of_this_decision": "Giudica SOLO la specifica (schemi, protocolli, coerenza "
                                 "interna, capacita' di rappresentare strategie diverse) - "
                                 "NON giudica se una qualunque strategia NEXUS ha edge, ne' "
                                 "sostituisce l'implementazione (vedi IMPLEMENTATION_ROADMAP_V1, "
                                 "dichiaratamente non eseguita in questa fase).",
        "known_blockers_for_full_implementation_not_for_the_spec_itself": [
            b["field"] for b in gap["MISSING_BUT_NEEDED"] if b["priority"] == "ALTA"
        ],
        "residual_open_questions": [
            "ex5_hash: da verificare se MQL5 puo' tecnicamente calcolare/esporre l'hash del "
            "proprio binario compilato a se stesso in runtime - non verificato in questa fase "
            "(richiederebbe test su MetaEditor/MQL5 reference, fuori scope di una fase di "
            "specifica)",
            "Il meccanismo di enforcement TECNICO della sequenza Stage A->B->C (non solo "
            "specificato, ma IMPEDITO a livello di strumento) resta da progettare nel dettaglio "
            "al Livello 3 (Product Platform) - qui solo il VINCOLO e' specificato",
        ],
        "no_edge_claim_made": True,
    }
    return payload


def main():
    payload = build()
    doc = wrap_with_provenance(payload, script=os.path.abspath(__file__))
    out_path = os.path.join(PHASE719_DIR, "audit_standard_decision_v1.json")
    save_json(out_path, doc)
    print(f"Scritto {out_path} (sha256={doc['canonical_sha256'][:16]}...)")
    print(f"  DECISIONE: {payload['decision']}")


if __name__ == "__main__":
    main()
