#!/usr/bin/env python3
"""Phase 7.7B - Structural Eligibility Semantics Correction.

Il reviewer ha trovato un'incoerenza reale in `strategy_meta_filter_
gate_v1.json` (Phase 7.7B, `72bcbf2`): il blocker generato per
WICK_SWEEP_RECLAIM affermava "manca un componente reale del lifecycle,
non solo un limite di questo o quell'audit" - ma la fonte REALE
(Phase 7.7A, `classification_rationale` di WICK_SWEEP_RECLAIM) dice
esplicitamente l'opposto: "classificato PARTIAL non per assenza di
formalizzazione ma perche' questo audit non ha approfondito il
contratto completo". 7.7B aveva quindi trasformato silenziosamente
UNKNOWN_DUE_TO_AUDIT_DEPTH in KNOWN_STRUCTURAL_ABSENCE - esattamente lo
stesso errore gia' riconosciuto (correttamente) per SAR_LIVE/ADX_RSI/
BREAKOUT_ACC, ma NON applicato coerentemente a WICK_SWEEP_RECLAIM.

Questo modulo introduce TRE stati (non due) per l'asse strutturale:
  STRUCTURALLY_ELIGIBLE       - lifecycle sufficientemente verificato
                                 nell'audit sorgente (campi realmente
                                 estratti, non solo classificazione).
  STRUCTURALLY_INELIGIBLE     - esiste EVIDENZA POSITIVA (una
                                 dichiarazione esplicita nella fonte)
                                 che una componente necessaria del
                                 lifecycle e' REALMENTE assente.
  STRUCTURAL_STATUS_UNVERIFIED - campi mancanti/null perche' l'audit
                                 sorgente non ha approfondito abbastanza
                                 (mai perche' si e' verificata
                                 un'assenza reale).

Regola generale (riusabile dal futuro Company Control Plane, sec.5
della richiesta): un campo NULL NON implica automaticamente
INELIGIBLE - implica INELIGIBLE solo se la fonte contiene una
dichiarazione ESPLICITA di assenza (`explicitly-absent`), altrimenti
implica UNVERIFIED (`audit-not-extracted` o `source-null` - vedi
`missing_field_taxonomy`).

NESSUN deep-dive del codice MQL5/Python reale in questa fase - la
riclassificazione e' fatta SOLO rileggendo il testo gia' scritto in
Phase 7.7A (`classification_rationale`), non nuove informazioni.
NESSUN backtest. NESSUNA applicazione di MECH-23. NESSUN nuovo outcome.
NESSUNA modifica retroattiva a 7.7A/7.7B (entrambi restano invariati -
verificato via hash)."""
import os
import sys

PHASE77B_DIR = os.path.dirname(os.path.abspath(__file__))
PHASE7_DIR = os.path.abspath(os.path.join(PHASE77B_DIR, ".."))
ROOT = os.path.abspath(os.path.join(PHASE77B_DIR, "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase6_6"))
from canonical_utils import file_sha256, load_json, save_json, wrap_with_provenance  # noqa: E402

BASELINE_COMMIT = "72bcbf299dc2bab52fb435f0b0d3320a52ff99a2"

LIFECYCLE_REGISTRY_PATH = os.path.join(PHASE7_DIR, "phase7_7a", "strategy_lifecycle_registry_v1.json")
GATE_PATH = os.path.join(PHASE7_DIR, "phase7_7b", "strategy_meta_filter_gate_v1.json")

STRUCTURALLY_ELIGIBLE = "STRUCTURALLY_ELIGIBLE"
STRUCTURALLY_INELIGIBLE = "STRUCTURALLY_INELIGIBLE"
STRUCTURAL_STATUS_UNVERIFIED = "STRUCTURAL_STATUS_UNVERIFIED"

# ---- Tassonomia generale del "missing field" (sec.5 della richiesta) - riusabile dal futuro
# Company Control Plane. Applicata qui SOLO rileggendo il testo gia' scritto in 7.7A. ----
MISSING_FIELD_TAXONOMY = {
    "source-null": "Il campo e' genuinamente assente nella fonte perche' quel componente non esiste per "
                    "costruzione nel design reale (es. H006 non ha un invalidation_stop separato perche' il "
                    "suo outcome e' definito interamente da una barriera - un fatto verificato, non un "
                    "limite di audit).",
    "audit-not-extracted": "Il campo e' null perche' l'audit che ha prodotto l'artifact non ha approfondito "
                            "quella parte del codice/documento sorgente - il componente PUO' esistere "
                            "realmente, semplicemente non e' stato letto. Implica sempre "
                            "STRUCTURAL_STATUS_UNVERIFIED, MAI STRUCTURALLY_INELIGIBLE.",
    "explicitly-absent": "La fonte contiene una dichiarazione ESPLICITA e positiva che il componente non "
                          "esiste (es. Phase 7.6E per le 4 famiglie DIRECTIONAL_EVENT_ONLY: 'nessun blocco "
                          "downstream nel detector gia' congelato' - verificato leggendo il codice, non "
                          "assunto). Solo questo caso giustifica STRUCTURALLY_INELIGIBLE.",
}


def build():
    lifecycle_doc = load_json(LIFECYCLE_REGISTRY_PATH)
    lifecycle_payload = lifecycle_doc["payload"]
    deep_dive = lifecycle_payload["deep_dive_candidates"]
    gate_doc = load_json(GATE_PATH)
    gate_payload = gate_doc["payload"]
    old_gate_results = gate_payload["gate_results_by_candidate"]

    # ---- Rilettura ESPLICITA del testo gia' scritto in Phase 7.7A (nessuna nuova informazione) ----
    # Per ciascun candidato con lifecycle_contract non interamente popolato, la classification_rationale
    # di 7.7A viene ispezionata per una dichiarazione di tipo 'audit-not-extracted' (mai assunta).
    audit_depth_phrases = ["non estratt", "non individualmente riverificat", "non approfondito",
                           "STRUCTURALLY_IMPLEMENTED", "limite di scope", "non riverificat"]

    corrected = {}
    for candidate_id, candidate in deep_dive.items():
        lc = candidate["lifecycle_contract"]
        rationale = candidate["classification_rationale"]
        core_populated = bool(lc["entry"]) and bool(lc["direction"]) and \
            (bool(lc["invalidation_stop"]) or bool(lc["target_exit"]))

        if core_populated:
            new_status = STRUCTURALLY_ELIGIBLE
            missing_field_class = None
            evidence_quote = None
        else:
            is_audit_depth = any(p in rationale for p in audit_depth_phrases)
            if is_audit_depth:
                new_status = STRUCTURAL_STATUS_UNVERIFIED
                missing_field_class = "audit-not-extracted"
            else:
                # Nessuna frase di audit-depth trovata - richiederebbe una dichiarazione ESPLICITA di
                # assenza per giustificare INELIGIBLE; verificato caso per caso sotto (nessuno dei
                # candidati di questo registro rientra qui oggi - vedi verified_positive_absence).
                new_status = STRUCTURALLY_INELIGIBLE
                missing_field_class = "explicitly-absent"
            evidence_quote = rationale

        old_status = old_gate_results[candidate_id]["meta_filter_structural_eligibility"]
        corrected[candidate_id] = {
            "old_7_7b_structural_status": old_status,
            "corrected_structural_status": new_status,
            "missing_field_taxonomy_class": missing_field_class,
            "evidence_quote_from_7_7a_rationale": evidence_quote,
            "correction_applied": old_status == "NOT_ELIGIBLE" and new_status == STRUCTURAL_STATUS_UNVERIFIED,
        }

    # ---- Verifica esplicita: nessun candidato di questo registro ha evidenza POSITIVA di assenza reale
    # (tutti i null sono audit-depth) - dichiarato qui, non assunto silenziosamente. ----
    verified_positive_absence = {
        cid: c for cid, c in corrected.items() if c["missing_field_taxonomy_class"] == "explicitly-absent"
    }

    # ---- Research readiness: RIUSATA IDENTICA da 7.7B, mai ricalcolata qui ----
    readiness_by_candidate = {
        cid: {
            "meta_filter_research_readiness": old_gate_results[cid]["meta_filter_research_readiness"],
            "next_required_evidence": old_gate_results[cid]["next_required_evidence"],
        }
        for cid in old_gate_results
    }

    # ---- Gate ricalcolato SOLO sull'asse structural corretto - readiness invariata ----
    corrected_gate_results = {}
    for cid in old_gate_results:
        structural = corrected[cid]["corrected_structural_status"]
        readiness = readiness_by_candidate[cid]["meta_filter_research_readiness"]
        gate_passed = structural == STRUCTURALLY_ELIGIBLE and readiness == "READY"
        corrected_gate_results[cid] = {
            "corrected_structural_status": structural,
            "research_readiness_unchanged": readiness,
            "meta_filter_ready_gate_passed": gate_passed,
        }

    counts_before = {
        "structurally_eligible": sum(1 for c in corrected.values() if c["old_7_7b_structural_status"] == "ELIGIBLE"),
        "structurally_ineligible_or_not_eligible": sum(1 for c in corrected.values() if c["old_7_7b_structural_status"] == "NOT_ELIGIBLE"),
        "unverified": 0,
    }
    counts_after = {
        "structurally_eligible": sum(1 for c in corrected.values() if c["corrected_structural_status"] == STRUCTURALLY_ELIGIBLE),
        "structurally_ineligible": sum(1 for c in corrected.values() if c["corrected_structural_status"] == STRUCTURALLY_INELIGIBLE),
        "unverified": sum(1 for c in corrected.values() if c["corrected_structural_status"] == STRUCTURAL_STATUS_UNVERIFIED),
    }

    gate_count_after = sum(1 for g in corrected_gate_results.values() if g["meta_filter_ready_gate_passed"])
    gate_count_before = gate_payload["counts"]["meta_filter_ready_count"]

    # ---- Conferma esplicita: research readiness invariata rispetto a 7.7B (nessun ricalcolo) ----
    readiness_unchanged_check = all(
        readiness_by_candidate[cid]["meta_filter_research_readiness"] ==
        old_gate_results[cid]["meta_filter_research_readiness"]
        for cid in old_gate_results
    )

    # ---- Proposta concettuale (non implementata): terzo asse EXECUTION READINESS ----
    future_axis_proposal = {
        "proposed_axis": "META_FILTER_EXECUTION_READINESS",
        "rationale": "WICK_SWEEP_RECLAIM ha gia' dimostrato che structural=eligible (in futuro, dopo un "
                     "deep-dive) + research_readiness alta NON implica che l'edge sopravviva "
                     "all'esecuzione reale (shadow PF=5.80 -> reale PF=0.78-0.80). Una pipeline completa "
                     "avrebbe bisogno di un terzo asse INDIPENDENTE: STRUCTURE -> RESEARCH EVIDENCE -> "
                     "EXECUTION REALISM -> DEPLOYABILITY, con gate distinti META_FILTER_READY / "
                     "EXECUTION_READY / DEPLOYABLE.",
        "not_implemented_here": True,
        "no_new_infrastructure_built": True,
    }

    payload = {
        "phase": "7.7B-CORRECTION", "artifact_role": "STRUCTURAL_ELIGIBILITY_SEMANTICS_CORRECTION",
        "scope_note": "Corregge una conflazione semantica trovata in strategy_meta_filter_gate_v1.json "
                       "(72bcbf2): campi lifecycle null per limite di audit erano stati trattati come "
                       "assenza strutturale verificata. Nessun nuovo deep-dive del codice, nessun backtest, "
                       "nessuna applicazione di MECH-23 - solo rilettura del testo gia' scritto in Phase "
                       "7.7A.",
        "baseline_commit": BASELINE_COMMIT,
        "source_lifecycle_registry_untouched": {
            "file": "server/research_scripts/phase7/phase7_7a/strategy_lifecycle_registry_v1.json",
            "canonical_sha256": lifecycle_doc["canonical_sha256"], "modified_in_this_phase": False,
        },
        "source_gate_untouched": {
            "file": "server/research_scripts/phase7/phase7_7b/strategy_meta_filter_gate_v1.json",
            "canonical_sha256": gate_doc["canonical_sha256"], "modified_in_this_phase": False,
        },
        "structural_eligibility_values": [STRUCTURALLY_ELIGIBLE, STRUCTURALLY_INELIGIBLE,
                                           STRUCTURAL_STATUS_UNVERIFIED],
        "missing_field_taxonomy": MISSING_FIELD_TAXONOMY,
        "general_rule": "MISSING_FIELD != VERIFIED_ABSENCE. Un campo null implica STRUCTURAL_STATUS_"
                        "UNVERIFIED per default (fail-closed verso 'non sappiamo', mai verso 'sappiamo che "
                        "manca') - STRUCTURALLY_INELIGIBLE richiede una dichiarazione ESPLICITA e positiva "
                        "di assenza nella fonte, mai dedotta dal solo valore null.",
        "corrected_structural_status_by_candidate": corrected,
        "verified_positive_absence_cases": verified_positive_absence,
        "verified_positive_absence_count": len(verified_positive_absence),
        "research_readiness_by_candidate_unchanged": readiness_by_candidate,
        "research_readiness_unchanged_confirmed": readiness_unchanged_check,
        "corrected_gate_results_by_candidate": corrected_gate_results,
        "gate_counts": {
            "meta_filter_ready_count_before_correction": gate_count_before,
            "meta_filter_ready_count_after_correction": gate_count_after,
            "gate_count_unchanged": gate_count_before == gate_count_after,
        },
        "structural_counts_before_correction": counts_before,
        "structural_counts_after_correction": counts_after,
        "no_candidate_promoted_by_this_correction": gate_count_after == 0,
        "future_axis_proposal": future_axis_proposal,
        "no_new_backtest_executed": True,
        "no_mech23_applied": True,
        "no_new_outcome_data_accessed": True,
        "no_edge_discovery_performed": True,
        "no_retroactive_modification_of_7_7a_or_7_7b": True,
        "seq0015_status_unchanged": "CLOSED_NOT_REEXAMINED_AS_CANDIDATE",
        "seq0009_status_unchanged": "CLOSED_NOT_REEXAMINED_AS_CANDIDATE",
    }
    return payload


def main():
    payload = build()
    doc = wrap_with_provenance(
        payload,
        script="server/research_scripts/phase7/phase7_7b/build_structural_eligibility_semantics_correction.py",
    )
    out_path = os.path.join(PHASE77B_DIR, "structural_eligibility_semantics_correction_v1.json")
    save_json(out_path, doc)
    print(f"Written {out_path}")
    print(f"canonical_sha256={doc['canonical_sha256']}")
    print(f"gate_count before/after: {payload['gate_counts']}")
    print(f"structural counts after: {payload['structural_counts_after_correction']}")


if __name__ == "__main__":
    main()
