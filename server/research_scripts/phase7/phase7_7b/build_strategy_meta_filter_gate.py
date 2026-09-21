#!/usr/bin/env python3
"""Phase 7.7B - Strategy Readiness & Meta-Filter Gate.

Il reviewer ha identificato che `strategy_meta_filter_eligibility_v1.json`
(Phase 7.7A, `e641598`) mescolava DUE concetti distinti sotto un'unica
etichetta `META_FILTER_ELIGIBLE`/`META_FILTER_NOT_READY`/
`META_FILTER_INAPPROPRIATE`:
  1. E' STRUTTURALMENTE possibile applicare un meta-filter (lifecycle
     completo, success/failure definiti, execution semantics definite)?
  2. E' SCIENTIFICAMENTE MATURO farlo ADESSO (l'evidenza raccolta finora
     lo giustifica)?

Una strategia FULL_STRATEGY_SPEC (livello 1) non deve MAI diventare
automaticamente META_FILTER_READY (livello 2) - questo modulo separa i
due assi esplicitamente, SENZA cambiare la sostanza di alcun risultato
gia' congelato (stessi dati sorgente di Phase 7.7A, nessun nuovo
backtest, nessuna nuova lettura di outcome).

NON riscrive silenziosamente `strategy_meta_filter_eligibility_v1.json`
(Phase 7.7A) - quell'artifact resta invariato, questo e' un NUOVO
artifact che lo supera in granularita', con un cross-reference esplicito
verso la vecchia etichetta.

NESSUN nuovo backtest. NESSUNA applicazione di MECH-23. NESSUNA modifica
ai risultati storici."""
import os
import sys

PHASE77B_DIR = os.path.dirname(os.path.abspath(__file__))
PHASE7_DIR = os.path.abspath(os.path.join(PHASE77B_DIR, ".."))
ROOT = os.path.abspath(os.path.join(PHASE77B_DIR, "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase6_6"))
from canonical_utils import file_sha256, load_json, save_json, wrap_with_provenance  # noqa: E402

BASELINE_COMMIT = "6ac26cc0ee8ee088a94e2cee038c12c1d1195316"

LIFECYCLE_REGISTRY_PATH = os.path.join(PHASE7_DIR, "phase7_7a", "strategy_lifecycle_registry_v1.json")
OLD_META_FILTER_PATH = os.path.join(PHASE7_DIR, "phase7_7a", "strategy_meta_filter_eligibility_v1.json")

# ---- Sec.1 della richiesta: due assi distinti, mai collassati in uno ----
STRUCTURAL_ELIGIBLE = "ELIGIBLE"
STRUCTURAL_NOT_ELIGIBLE = "NOT_ELIGIBLE"

READY = "READY"
NEEDS_MORE_EVIDENCE = "NEEDS_MORE_EVIDENCE"
BORDERLINE_LOW_PRIORITY = "BORDERLINE_LOW_PRIORITY"
REFUTED_INAPPROPRIATE = "REFUTED_INAPPROPRIATE"
EXECUTION_FAILED_INAPPROPRIATE = "EXECUTION_FAILED_INAPPROPRIATE"
NOT_READY = "NOT_READY"
VALID_READINESS = (READY, NEEDS_MORE_EVIDENCE, BORDERLINE_LOW_PRIORITY, REFUTED_INAPPROPRIATE,
                    EXECUTION_FAILED_INAPPROPRIATE, NOT_READY)


def compute_structural_eligibility(candidate_id, candidate):
    """ELIGIBLE richiede: classificazione Phase 7.7A = FULL_STRATEGY_SPEC E i campi-chiave del
    lifecycle_contract (entry, direction, e ALMENO UNO fra invalidation_stop/target_exit) REALMENTE
    estratti (non null) in quell'audit - MAI dedotto dalla sola classificazione di alto livello.
    Fail-closed: se i campi non sono stati estratti, NOT_ELIGIBLE con un blocker che distingue
    esplicitamente 'audit non abbastanza approfondito' da 'struttura realmente assente'."""
    lc = candidate["lifecycle_contract"]
    classification = candidate["classification"]
    core_populated = bool(lc["entry"]) and bool(lc["direction"]) and \
        (bool(lc["invalidation_stop"]) or bool(lc["target_exit"]))

    if classification == "FULL_STRATEGY_SPEC" and core_populated:
        return STRUCTURAL_ELIGIBLE, None
    if classification == "FULL_STRATEGY_SPEC" and not core_populated:
        missing = [f for f in ("entry", "direction") if not lc[f]]
        if not (lc["invalidation_stop"] or lc["target_exit"]):
            missing.append("invalidation_stop_or_target_exit")
        return STRUCTURAL_NOT_ELIGIBLE, (
            f"Lifecycle_contract NON interamente estratto in Phase 7.7A (limite di SCOPE di quell'audit, "
            f"NON necessariamente assenza di struttura reale nel codice sorgente) - campi mancanti: "
            f"{missing}. Richiede un deep-dive dedicato del codice reale (NXS_Strategies.mqh/"
            f"NXS_StrategyProfiles.mqh o server/backtest.py) prima di poter dichiarare ELIGIBLE."
        )
    return STRUCTURAL_NOT_ELIGIBLE, (
        f"Classificazione lifecycle Phase 7.7A = {classification} (non FULL_STRATEGY_SPEC) - manca "
        f"un componente reale del lifecycle (es. direzione/invalidazione/target), non solo un limite "
        f"di questo o quell'audit."
    )


def compute_research_readiness(candidate_id, candidate):
    """Derivato ESCLUSIVAMENTE dall'evidence_verdict gia' congelato in Phase 7.7A - nessuna nuova
    lettura di evidenza, nessun nuovo giudizio statistico. READY e' riservato a un verdetto di
    validazione pienamente superata - NESSUN candidato attuale lo raggiunge (fatto onesto, non
    un difetto di questa funzione)."""
    verdict = candidate["evidence_verdict"]
    if verdict == "HOLD_NEEDS_MORE_EVIDENCE":
        return NEEDS_MORE_EVIDENCE, (
            "Serious 3Y backtest (o campione multi-anno equivalente) - il fast structural attuale "
            "(n=14/6 mesi) e' troppo piccolo/concentrato per un verdetto forte (vedi Strategy Foundry "
            "Phase 3 sec.6)."
        )
    if "RETAIN_E2" in verdict or "BORDERLINE" in verdict:
        return BORDERLINE_LOW_PRIORITY, (
            "CROSS_FEED_VALIDATION indipendente (E4, fonte dati diversa) o un nuovo true holdout "
            "dedicato - priorita' BASSA data la natura gia' borderline del risultato (delta_p sotto "
            "soglia di materialita', CI95 sovrapposte) - investire in piu' evidenza qui ha basso valore "
            "atteso rispetto a un candidato non ancora borderline."
        )
    if verdict == "REFUTED_AT_EXECUTION_VALIDATION":
        return EXECUTION_FAILED_INAPPROPRIATE, (
            "Nessuna evidenza aggiuntiva sullo STESSO design di esecuzione la salverebbe - "
            "richiederebbe un fill model dimostrabilmente piu' realistico (non tentato), non piu' "
            "campione."
        )
    if verdict == "REFUTED" or verdict.startswith("REFUTED ("):
        return REFUTED_INAPPROPRIATE, (
            "Nessuna - la strategia e' stata refutata su evidenza sufficiente e pre-registrata; "
            "richiederebbe una nuova ipotesi/design con una nuova identita', non piu' evidenza sullo "
            "stesso design (stessa disciplina di FAIL-002/sec.24 gia' applicata altrove nel progetto)."
        )
    if verdict.startswith("DISCOVERY_SUPPORTED"):
        return NOT_READY, (
            "Trattamento statistico rigoroso (Wilson CI, dependence-aware audit, separazione "
            "discovery/holdout dichiarata) - oggi l'evidenza e' solo R-multiple/PF grezzo su backtest "
            "informale, non sufficiente per un giudizio di maturita' anche se il segno e' positivo."
        )
    return NOT_READY, "Verdetto di evidenza non riconosciuto da nessuna regola esplicita - fail-closed a "\
                       "NOT_READY, mai READY per default."


def compute_gate(structural, readiness):
    """STRATEGY_VALIDATION -> META_FILTER_READY? richiede ENTRAMBI gli assi. Una strategia
    FULL_STRATEGY_SPEC (eligibility strutturale) NON diventa automaticamente pronta - deve anche
    avere readiness=READY, che oggi nessun candidato raggiunge (fatto riportato esplicitamente, non
    nascosto)."""
    return structural == STRUCTURAL_ELIGIBLE and readiness == READY


def build():
    lifecycle_doc = load_json(LIFECYCLE_REGISTRY_PATH)
    lifecycle_payload = lifecycle_doc["payload"]
    deep_dive = lifecycle_payload["deep_dive_candidates"]
    old_meta_doc = load_json(OLD_META_FILTER_PATH)
    old_meta_payload = old_meta_doc["payload"]

    gate_results = {}
    for candidate_id, candidate in deep_dive.items():
        structural, structural_blocker = compute_structural_eligibility(candidate_id, candidate)
        readiness, next_evidence = compute_research_readiness(candidate_id, candidate)
        meta_filter_ready = compute_gate(structural, readiness)
        gate_results[candidate_id] = {
            "meta_filter_structural_eligibility": structural,
            "structural_blocker": structural_blocker,
            "meta_filter_research_readiness": readiness,
            "next_required_evidence": next_evidence,
            "meta_filter_ready_gate_passed": meta_filter_ready,
            "old_phase_7_7a_label": old_meta_payload["eligibility_by_candidate"][candidate_id]["eligibility"],
            "evidence_verdict_unchanged_from_7_7a": candidate["evidence_verdict"],
            "classification_unchanged_from_7_7a": candidate["classification"],
        }

    # ---- Cross-reference: come l'etichetta unica di 7.7A si decompone nei due nuovi assi ----
    crossref = {}
    for candidate_id, g in gate_results.items():
        crossref[candidate_id] = {
            "old_single_label_phase_7_7a": g["old_phase_7_7a_label"],
            "new_structural_eligibility": g["meta_filter_structural_eligibility"],
            "new_research_readiness": g["meta_filter_research_readiness"],
            "semantic_correction": (
                "L'etichetta unica precedente 'META_FILTER_ELIGIBLE' mescolava eligibility strutturale "
                "e maturita' di ricerca - qui separate esplicitamente. Un dashboard futuro NON deve piu' "
                "leggere 'ELIGIBLE' come 'pronto a testare' - solo meta_filter_ready_gate_passed=True lo "
                "e', e nessun candidato lo e' oggi."
                if g["old_phase_7_7a_label"] == "META_FILTER_ELIGIBLE" else
                "Etichetta precedente gia' non-ambigua (META_FILTER_NOT_READY/META_FILTER_INAPPROPRIATE) - "
                "la decomposizione qui e' comunque fornita per coerenza di formato, non perche' l'etichetta "
                "originale fosse fuorviante."
            ),
        }

    # ---- Conteggi (sec. Output della richiesta) ----
    structural_eligible_count = sum(1 for g in gate_results.values() if g["meta_filter_structural_eligibility"] == STRUCTURAL_ELIGIBLE)
    research_ready_count = sum(1 for g in gate_results.values() if g["meta_filter_research_readiness"] == READY)
    blocked_count = sum(1 for g in gate_results.values() if not g["meta_filter_ready_gate_passed"])

    # ---- Incoerenze di governance (riferite da Phase 7.7A, non ri-derivate qui) ----
    governance_inconsistencies = [
        {
            "type": "SEMANTIC_CONFLATION_CORRECTED_THIS_PHASE",
            "description": "strategy_meta_filter_eligibility_v1.json (Phase 7.7A) mescolava eligibility "
                            "strutturale e maturita' di ricerca sotto un'unica etichetta - corretto QUI "
                            "con un nuovo artifact separato, il vecchio file NON e' stato modificato.",
        },
        {
            "type": "ACTIVE_STATUS_VS_REFUTED_EVIDENCE",
            "description": "Gia' documentato in Phase 7.7A: SAR/MACD/RSI_DIV/ADX_RSI/TSI hanno "
                            "status=ACTIVE nel registro canonico nonostante evidenza confermata negativa - "
                            "riferito qui, non ri-derivato.",
            "reference": "server/research_scripts/phase7/phase7_7a/strategy_evidence_matrix_v1.json"
                         "#registry_status_vs_evidence_conflicts",
        },
        {
            "type": "H006_VOCABULARY_DRIFT",
            "description": "Gia' documentato in Phase 7.7A: stesso risultato H006 etichettato WEAK/"
                            "BORDERLINE/RETAIN_E2 in tre artifact diversi - riferito qui, non ri-derivato.",
            "reference": "server/research_scripts/phase7/phase7_7a/strategy_lifecycle_registry_v1.json"
                         "#deep_dive_candidates.H006_LIQUIDITY_SWEEP_RECLAIM.registry_vocabulary_drift_found",
        },
        {
            "type": "STRUCTURAL_ELIGIBILITY_AUDIT_DEPTH_GAP",
            "description": "NUOVO in questa fase: 3 dei 6 candidati esplicitamente richiesti dal reviewer "
                            "(SAR_LIVE, ADX_RSI, BREAKOUT_ACC) risultano NOT_ELIGIBLE non perche' privi di "
                            "struttura reale, ma perche' Phase 7.7A non ne ha estratto il lifecycle_contract "
                            "completo (limite di scope di quell'audit, dichiarato esplicitamente allora) - "
                            "un futuro deep-dive del codice MQL5 reale potrebbe promuoverli a ELIGIBLE senza "
                            "cambiare l'evidenza empirica sottostante.",
        },
    ]

    payload = {
        "phase": "7.7B", "artifact_role": "STRATEGY_META_FILTER_GATE",
        "scope_note": "Separa formalmente META_FILTER_STRUCTURAL_ELIGIBILITY da META_FILTER_RESEARCH_"
                       "READINESS per l'uso futuro di strategie in META_FILTER_RESEARCH - nessun nuovo "
                       "backtest, nessuna applicazione di MECH-23, nessuna modifica ai risultati storici "
                       "(stessi dati sorgente di Phase 7.7A).",
        "baseline_commit": BASELINE_COMMIT,
        "source_lifecycle_registry": {
            "file": "server/research_scripts/phase7/phase7_7a/strategy_lifecycle_registry_v1.json",
            "canonical_sha256": lifecycle_doc["canonical_sha256"],
        },
        "source_old_meta_filter_artifact_untouched": {
            "file": "server/research_scripts/phase7/phase7_7a/strategy_meta_filter_eligibility_v1.json",
            "canonical_sha256": old_meta_doc["canonical_sha256"],
            "modified_in_this_phase": False,
        },
        "gate_definition": {
            "stages": ["STRATEGY_VALIDATION", "META_FILTER_READY?"],
            "requirement": "meta_filter_structural_eligibility == ELIGIBLE AND "
                            "meta_filter_research_readiness == READY",
            "explicit_non_automatic_promotion": "Una strategia FULL_STRATEGY_SPEC (eligibility strutturale) "
                                                 "NON diventa automaticamente META_FILTER_READY - deve anche "
                                                 "superare l'asse di maturita' di ricerca, indipendente.",
        },
        "structural_eligibility_values": [STRUCTURAL_ELIGIBLE, STRUCTURAL_NOT_ELIGIBLE],
        "research_readiness_values": list(VALID_READINESS),
        "gate_results_by_candidate": gate_results,
        "counts": {
            "total_candidates_evaluated": len(gate_results),
            "structural_eligible_count": structural_eligible_count,
            "research_ready_count": research_ready_count,
            "meta_filter_ready_count": sum(1 for g in gate_results.values() if g["meta_filter_ready_gate_passed"]),
            "blocked_count": blocked_count,
        },
        "governance_inconsistencies": governance_inconsistencies,
        "no_new_backtest_executed": True,
        "no_mech23_applied": True,
        "no_historical_results_modified": True,
        "no_edge_discovery_performed": True,
        "no_new_outcome_data_accessed": True,
        "seq0015_status_unchanged": "CLOSED_NOT_REEXAMINED_AS_CANDIDATE",
        "seq0009_status_unchanged": "CLOSED_NOT_REEXAMINED_AS_CANDIDATE",
    }

    crossref_payload = {
        "phase": "7.7B", "artifact_role": "STRATEGY_META_FILTER_GATE_CROSSREF",
        "baseline_commit": BASELINE_COMMIT,
        "scope_note": "Mappa esplicita: come l'etichetta unica strategy_meta_filter_eligibility_v1.json "
                       "(Phase 7.7A) si decompone nei due nuovi assi indipendenti di questa fase. Il file "
                       "originale NON e' stato modificato.",
        "crossref_by_candidate": crossref,
        "old_artifact_reference": {
            "file": "server/research_scripts/phase7/phase7_7a/strategy_meta_filter_eligibility_v1.json",
            "canonical_sha256": old_meta_doc["canonical_sha256"],
        },
    }

    return payload, crossref_payload


def main():
    gate_payload, crossref_payload = build()
    gate_doc = wrap_with_provenance(
        gate_payload, script="server/research_scripts/phase7/phase7_7b/build_strategy_meta_filter_gate.py"
    )
    crossref_doc = wrap_with_provenance(
        crossref_payload, script="server/research_scripts/phase7/phase7_7b/build_strategy_meta_filter_gate.py"
    )
    save_json(os.path.join(PHASE77B_DIR, "strategy_meta_filter_gate_v1.json"), gate_doc)
    save_json(os.path.join(PHASE77B_DIR, "strategy_meta_filter_gate_crossref_v1.json"), crossref_doc)
    print("Written strategy_meta_filter_gate_v1.json, strategy_meta_filter_gate_crossref_v1.json")
    print(f"gate canonical_sha256={gate_doc['canonical_sha256']}")
    print(f"counts={gate_payload['counts']}")


if __name__ == "__main__":
    main()
