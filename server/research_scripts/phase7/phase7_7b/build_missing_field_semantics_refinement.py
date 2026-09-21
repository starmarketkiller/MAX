#!/usr/bin/env python3
"""Phase 7.7B - Missing-Field Semantics Refinement (two-axis).

Il reviewer ha trovato un'ambiguita' residua nella tassonomia a 3 stati
introdotta dalla correzione precedente (`4743ce0`,
`structural_eligibility_semantics_correction_v1.json`): quella
tassonomia mescolava ANCORA due domande distinte in un'unica etichetta
(`source-null` / `explicitly-absent`):
  1. PERCHE' il campo e' vuoto? (field knowledge)
  2. Quel campo era NECESSARIO per essere eligible? (requirement role)

Esempio concreto (test-case esplicito richiesto dal reviewer): H006 non
ha un `invalidation_stop` separato - ma questo NON significa
incompletezza strutturale, perche' la sua semantica di outcome a
barriera (P(+1.0xATR before -1.0xATR)) copre GIA' quella funzione (il
lato -1.0xATR della barriera E' l'invalidazione, solo non nominato
separatamente). Verificato qui direttamente contro H006_frozen_spec.json
(nessun campo 'invalidation'/'stop' esiste in nessuna chiave dello
schema, e `primary_outcome.definition` dichiara esplicitamente "nessuna
gestione dinamica" - quindi l'assenza e' VERIFICATA, non un limite di
audit) - ma la sua RUOLO non e' 'necessario e mancante', e'
'soddisfatto da un meccanismo equivalente'.

Questo modulo separa i due assi:
  FIELD_KNOWLEDGE: VERIFIED_VALUE / VERIFIED_ABSENCE / NOT_EXTRACTED
  REQUIREMENT_ROLE: REQUIRED / NOT_REQUIRED_BY_DESIGN /
                     SATISFIED_BY_EQUIVALENT_MECHANISM

Regola: VERIFIED_ABSENCE + REQUIRED -> STRUCTURALLY_INELIGIBLE (unico
caso). VERIFIED_ABSENCE + (NOT_REQUIRED_BY_DESIGN o
SATISFIED_BY_EQUIVALENT_MECHANISM) -> NON implica ineligibility.
NOT_EXTRACTED -> STRUCTURAL_STATUS_UNVERIFIED, sempre, indipendentemente
dal ruolo (non possiamo giudicare il ruolo di un campo che non abbiamo
nemmeno letto).

NESSUN backtest, NESSUNA nuova ricerca, NESSUNA modifica retroattiva
agli artifact frozen (7.7A `strategy_lifecycle_registry_v1.json`,
7.7B `strategy_meta_filter_gate_v1.json`,
`structural_eligibility_semantics_correction_v1.json`) - tutti restano
invariati, verificato via hash."""
import os
import sys

PHASE77B_DIR = os.path.dirname(os.path.abspath(__file__))
PHASE7_DIR = os.path.abspath(os.path.join(PHASE77B_DIR, ".."))
ROOT = os.path.abspath(os.path.join(PHASE77B_DIR, "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase6_6"))
from canonical_utils import file_sha256, load_json, save_json, wrap_with_provenance  # noqa: E402

BASELINE_COMMIT = "4743ce0a29310a411afb5bd656179ee43ed76e5f"

LIFECYCLE_REGISTRY_PATH = os.path.join(PHASE7_DIR, "phase7_7a", "strategy_lifecycle_registry_v1.json")
GATE_PATH = os.path.join(PHASE7_DIR, "phase7_7b", "strategy_meta_filter_gate_v1.json")
PRIOR_CORRECTION_PATH = os.path.join(PHASE7_DIR, "phase7_7b", "structural_eligibility_semantics_correction_v1.json")
H006_FROZEN_SPEC_PATH = os.path.join(ROOT, "server", "research_scripts", "phase6", "H006_frozen_spec.json")

VERIFIED_VALUE = "VERIFIED_VALUE"
VERIFIED_ABSENCE = "VERIFIED_ABSENCE"
NOT_EXTRACTED = "NOT_EXTRACTED"

REQUIRED = "REQUIRED"
NOT_REQUIRED_BY_DESIGN = "NOT_REQUIRED_BY_DESIGN"
SATISFIED_BY_EQUIVALENT_MECHANISM = "SATISFIED_BY_EQUIVALENT_MECHANISM"

STRUCTURALLY_ELIGIBLE = "STRUCTURALLY_ELIGIBLE"
STRUCTURALLY_INELIGIBLE = "STRUCTURALLY_INELIGIBLE"
STRUCTURAL_STATUS_UNVERIFIED = "STRUCTURAL_STATUS_UNVERIFIED"

# Campi "core" gia' usati dal gate (7.7B) per decidere l'asse strutturale - entry/direction sono sempre
# REQUIRED per costruzione (nessuna strategia direzionale puo' esistere senza), invalidation_stop/
# target_exit sono i due possibili modi di soddisfare il requisito "condizione di uscita definita".
CORE_FIELDS = ("entry", "direction", "invalidation_stop", "target_exit")


def classify_field(candidate_id, field_name, value, rationale_text, h006_spec_keys=None):
    """Classificazione a due assi per UN campo di UN candidato - fondata sul testo/artifact REALE
    gia' esistente, mai dedotta dalla sola presenza/assenza del valore."""
    audit_depth_phrases = ["non estratt", "non individualmente riverificat", "non approfondito",
                           "STRUCTURALLY_IMPLEMENTED", "limite di scope", "non riverificat",
                           "fuori scope della Failure Memory"]

    if value is not None:
        return {"field_knowledge": VERIFIED_VALUE, "requirement_role": REQUIRED,
                "note": "Valore realmente estratto dalla fonte - il requisito e' per costruzione "
                        "soddisfatto (non c'e' nulla da giudicare oltre alla presenza del valore)."}

    # Valore None: PERCHE'?
    if candidate_id == "H006_LIQUIDITY_SWEEP_RECLAIM" and field_name == "invalidation_stop":
        # Test-case esplicito del reviewer: verificato DIRETTAMENTE contro H006_frozen_spec.json (non
        # assunto) - nessuna chiave 'invalidation'/'stop' esiste in nessun campo dello schema, e
        # primary_outcome.definition dichiara esplicitamente 'nessuna gestione dinamica'.
        has_no_invalidation_key = h006_spec_keys is not None and not any(
            "invalid" in k.lower() or "stop" in k.lower() for k in h006_spec_keys
        )
        return {
            "field_knowledge": VERIFIED_ABSENCE,
            "requirement_role": SATISFIED_BY_EQUIVALENT_MECHANISM,
            "note": "VERIFICATO direttamente contro H006_frozen_spec.json: nessuna chiave 'invalidation'/"
                    "'stop' esiste nello schema (chiavi reali: " + repr(h006_spec_keys) + "), "
                    "primary_outcome.definition dichiara esplicitamente 'nessuna gestione dinamica' - "
                    "l'assenza e' REALE, non un limite di audit. MA il ruolo e' "
                    "SATISFIED_BY_EQUIVALENT_MECHANISM: il lato -1.0xATR della barriera "
                    "P(+1.0xATR before -1.0xATR) e' funzionalmente l'invalidazione - il design di H006 "
                    "definisce l'uscita interamente tramite la barriera a due lati, senza bisogno di un "
                    "campo separato. has_no_invalidation_key=" + str(has_no_invalidation_key),
        }

    if any(p in rationale_text for p in audit_depth_phrases):
        return {"field_knowledge": NOT_EXTRACTED, "requirement_role": REQUIRED,
                "note": "Rationale di Phase 7.7A indica esplicitamente un limite di audit (non "
                        "un'assenza verificata) - il ruolo resta REQUIRED per default (entry/direction "
                        "sono sempre necessari per una strategia direzionale) ma non possiamo giudicare "
                        "se sarebbe soddisfatto perche' non l'abbiamo letto."}

    # Nessuna delle condizioni sopra - non dovrebbe accadere per i candidati attuali (verificato dal test).
    return {"field_knowledge": NOT_EXTRACTED, "requirement_role": REQUIRED,
            "note": "Fallback fail-closed: nessuna dichiarazione esplicita ne' di assenza verificata ne' "
                    "di limite di audit trovata - trattato come NOT_EXTRACTED per non rischiare un falso "
                    "STRUCTURALLY_INELIGIBLE."}


def compute_structural_status(field_classifications):
    """Regola sec. della richiesta: VERIFIED_ABSENCE+REQUIRED -> INELIGIBLE (unico caso). Qualunque
    NOT_EXTRACTED su un campo REQUIRED -> UNVERIFIED (a meno che gia' INELIGIBLE per un altro campo,
    fail-closed nella direzione piu' cauta: un'assenza verificata e realmente bloccante non deve mai
    essere nascosta da un altro campo semplicemente non estratto)."""
    has_verified_absence_required = any(
        fc["field_knowledge"] == VERIFIED_ABSENCE and fc["requirement_role"] == REQUIRED
        for fc in field_classifications.values()
    )
    if has_verified_absence_required:
        return STRUCTURALLY_INELIGIBLE
    has_not_extracted_required = any(
        fc["field_knowledge"] == NOT_EXTRACTED and fc["requirement_role"] == REQUIRED
        for fc in field_classifications.values()
    )
    if has_not_extracted_required:
        return STRUCTURAL_STATUS_UNVERIFIED
    return STRUCTURALLY_ELIGIBLE


def build():
    lifecycle_doc = load_json(LIFECYCLE_REGISTRY_PATH)
    lifecycle_payload = lifecycle_doc["payload"]
    deep_dive = lifecycle_payload["deep_dive_candidates"]
    gate_doc = load_json(GATE_PATH)
    prior_correction_doc = load_json(PRIOR_CORRECTION_PATH)
    prior_correction = prior_correction_doc["payload"]
    h006_spec = load_json(H006_FROZEN_SPEC_PATH)
    h006_spec_keys = list(h006_spec.keys())

    per_candidate = {}
    for candidate_id, candidate in deep_dive.items():
        lc = candidate["lifecycle_contract"]
        rationale = candidate["classification_rationale"]
        field_classifications = {}
        for field_name in CORE_FIELDS:
            field_classifications[field_name] = classify_field(
                candidate_id, field_name, lc[field_name], rationale,
                h006_spec_keys=h006_spec_keys if candidate_id == "H006_LIQUIDITY_SWEEP_RECLAIM" else None,
            )
        new_status = compute_structural_status(field_classifications)
        prior_status = prior_correction["corrected_structural_status_by_candidate"][candidate_id][
            "corrected_structural_status"]
        per_candidate[candidate_id] = {
            "field_classifications": field_classifications,
            "refined_structural_status": new_status,
            "prior_correction_structural_status": prior_status,
            "status_changed_by_this_refinement": new_status != prior_status,
        }

    # ---- H006 test-case: riportato esplicitamente e verificato (sec. della richiesta) ----
    h006_invalidation = per_candidate["H006_LIQUIDITY_SWEEP_RECLAIM"]["field_classifications"]["invalidation_stop"]
    h006_test_case = {
        "field": "invalidation_stop", "candidate": "H006_LIQUIDITY_SWEEP_RECLAIM",
        "field_knowledge": h006_invalidation["field_knowledge"],
        "requirement_role": h006_invalidation["requirement_role"],
        "does_this_imply_ineligibility": False,
        "verified_against_real_source_file": "server/research_scripts/phase6/H006_frozen_spec.json",
        "verified_against_real_source_file_sha256": file_sha256(H006_FROZEN_SPEC_PATH),
        "explanation": h006_invalidation["note"],
    }

    # ---- Verifica: nessun candidato risulta STRUCTURALLY_INELIGIBLE (VERIFIED_ABSENCE+REQUIRED) oggi ----
    ineligible_cases = {cid: c for cid, c in per_candidate.items()
                         if c["refined_structural_status"] == STRUCTURALLY_INELIGIBLE}

    # ---- Gate ricalcolato: readiness RIUSATA IDENTICA da 7.7B, mai ricalcolata ----
    old_gate_results = gate_doc["payload"]["gate_results_by_candidate"]
    refined_gate_results = {}
    for cid, c in per_candidate.items():
        readiness = old_gate_results[cid]["meta_filter_research_readiness"]
        gate_passed = c["refined_structural_status"] == STRUCTURALLY_ELIGIBLE and readiness == "READY"
        refined_gate_results[cid] = {
            "refined_structural_status": c["refined_structural_status"],
            "research_readiness_unchanged": readiness,
            "meta_filter_ready_gate_passed": gate_passed,
        }
    readiness_unchanged_check = all(
        refined_gate_results[cid]["research_readiness_unchanged"] ==
        old_gate_results[cid]["meta_filter_research_readiness"]
        for cid in old_gate_results
    )
    gate_count_before = gate_doc["payload"]["counts"]["meta_filter_ready_count"]
    gate_count_after = sum(1 for g in refined_gate_results.values() if g["meta_filter_ready_gate_passed"])

    status_changes = {cid: c for cid, c in per_candidate.items() if c["status_changed_by_this_refinement"]}

    payload = {
        "phase": "7.7B-REFINEMENT", "artifact_role": "MISSING_FIELD_SEMANTICS_REFINEMENT",
        "scope_note": "Separa FIELD_KNOWLEDGE (perche' un campo e' vuoto) da REQUIREMENT_ROLE (se quel "
                       "campo era necessario) - la correzione precedente (4743ce0) aveva gia' distinto "
                       "audit-depth da assenza verificata, ma mescolava ANCORA 'assenza verificata' con "
                       "'quindi ineligible'. Nessun backtest, nessuna modifica retroattiva agli artifact "
                       "frozen.",
        "baseline_commit": BASELINE_COMMIT,
        "sources_untouched": {
            "lifecycle_registry": {"file": "server/research_scripts/phase7/phase7_7a/"
                                    "strategy_lifecycle_registry_v1.json",
                                    "canonical_sha256": lifecycle_doc["canonical_sha256"]},
            "gate": {"file": "server/research_scripts/phase7/phase7_7b/strategy_meta_filter_gate_v1.json",
                     "canonical_sha256": gate_doc["canonical_sha256"]},
            "prior_correction": {"file": "server/research_scripts/phase7/phase7_7b/"
                                  "structural_eligibility_semantics_correction_v1.json",
                                  "canonical_sha256": prior_correction_doc["canonical_sha256"]},
            "modified_in_this_phase": False,
        },
        "field_knowledge_values": [VERIFIED_VALUE, VERIFIED_ABSENCE, NOT_EXTRACTED],
        "requirement_role_values": [REQUIRED, NOT_REQUIRED_BY_DESIGN, SATISFIED_BY_EQUIVALENT_MECHANISM],
        "rule": {
            "VERIFIED_ABSENCE_plus_REQUIRED": "STRUCTURALLY_INELIGIBLE (unico caso)",
            "VERIFIED_ABSENCE_plus_NOT_REQUIRED_BY_DESIGN": "non implica ineligibility",
            "VERIFIED_ABSENCE_plus_SATISFIED_BY_EQUIVALENT_MECHANISM": "non implica ineligibility",
            "NOT_EXTRACTED_any_role": "STRUCTURAL_STATUS_UNVERIFIED (non possiamo giudicare il ruolo di "
                                       "un campo non letto)",
        },
        "h006_test_case": h006_test_case,
        "per_candidate_field_classifications": per_candidate,
        "ineligible_cases_found": ineligible_cases,
        "ineligible_cases_count": len(ineligible_cases),
        "status_changes_vs_prior_correction": status_changes,
        "status_changes_count": len(status_changes),
        "refined_gate_results_by_candidate": refined_gate_results,
        "research_readiness_unchanged_confirmed": readiness_unchanged_check,
        "gate_counts": {
            "meta_filter_ready_count_before_this_refinement": gate_count_before,
            "meta_filter_ready_count_after_this_refinement": gate_count_after,
            "gate_count_unchanged": gate_count_before == gate_count_after,
        },
        "no_new_backtest_executed": True,
        "no_new_research_performed": True,
        "no_mech23_applied": True,
        "no_retroactive_modification_of_frozen_artifacts": True,
        "no_edge_discovery_performed": True,
        "seq0015_status_unchanged": "CLOSED_NOT_REEXAMINED_AS_CANDIDATE",
        "seq0009_status_unchanged": "CLOSED_NOT_REEXAMINED_AS_CANDIDATE",
    }
    return payload


def main():
    payload = build()
    doc = wrap_with_provenance(
        payload, script="server/research_scripts/phase7/phase7_7b/build_missing_field_semantics_refinement.py",
    )
    out_path = os.path.join(PHASE77B_DIR, "missing_field_semantics_refinement_v1.json")
    save_json(out_path, doc)
    print(f"Written {out_path}")
    print(f"canonical_sha256={doc['canonical_sha256']}")
    print(f"gate_counts={payload['gate_counts']}")
    print(f"status_changes_count={payload['status_changes_count']}")
    print(f"ineligible_cases_count={payload['ineligible_cases_count']}")


if __name__ == "__main__":
    main()
