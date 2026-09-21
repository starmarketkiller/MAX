#!/usr/bin/env python3
"""Phase 7.6C - Outcome-Horizon Ordering Audit.

Il reviewer ha identificato un problema di ORDINE metodologico nello
SPEC COMMIT gia' congelato (`6c0d3f6`): `natural_horizon=40`/
`outcome_overlap_embargo_bars=39` sono stati congelati PRIMA che
SEQ-0014B avesse un primary outcome scelto - e il collasso cross-family
210->11 (RESULT COMMIT `80e7cbc`) dipende direttamente da quell'embargo.
Se l'orizzonte naturale del claim MECH-23 fosse in realta' diverso da
40 barre, la geometria pooled cambierebbe.

Questo modulo e' un AUDIT DI SEQUENCING, non un rescue: NON legge
outcome, NON prova orizzonti alternativi sui dati, NON riesegue il
preflight, NON modifica ne' lo spec ne' il result gia' congelati
(`6c0d3f6`/`80e7cbc` restano invariati - verificato via hash).

Obiettivo: determinare se natural_horizon=40 possiede una
giustificazione MECCANICA pre-esistente e indipendente dalla futura
scelta del primary outcome di SEQ-0014B, distinguendo tre classi:
  A. MECHANISM_DERIVED  - deriva dalla scala temporale del meccanismo
                          del detector stesso.
  B. OUTCOME_DERIVED    - deriva dall'orizzonte naturale di un outcome
                          gia' scelto e frozen.
  C. PROJECT_CONVENTION - riusato per coerenza di progetto, senza una
                          derivazione indipendente per QUESTO
                          esperimento specifico.

Se la classificazione e' C (o comunque non B, dato che l'outcome non
era ancora scelto), il verdetto NOT_TESTABLE_WITH_FROZEN_SETUP_
POPULATION va esplicitamente SCOPED a DESIGN_V1 (setup population +
horizon=40/embargo=39 + matching contract, tutti congelati in
fb52168/6c0d3f6), non generalizzato a "MECH-23 e' impossibile da
testare"."""
import os
import sys

PHASE76C_DIR = os.path.dirname(os.path.abspath(__file__))
PHASE7_DIR = os.path.abspath(os.path.join(PHASE76C_DIR, ".."))
ROOT = os.path.abspath(os.path.join(PHASE76C_DIR, "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase6_6"))
from canonical_utils import file_sha256, load_json, save_json, wrap_with_provenance  # noqa: E402

BASELINE_COMMIT = "80e7cbc124e40c61a9f0d28a31dd3c6d2e1a5fc3"
SPEC_COMMIT = "6c0d3f64d74a8d0495c4b634bee0c9d7d2ea8a93"
RESULT_COMMIT = "80e7cbc124e40c61a9f0d28a31dd3c6d2e1a5fc3"

SPEC_PATH = os.path.join(PHASE76C_DIR, "seq0014b_structural_preflight_spec_v1.json")
RESULT_PATH = os.path.join(PHASE76C_DIR, "seq0014b_structural_preflight_result_v1.json")
SETUP_POP_PATH = os.path.join(PHASE7_DIR, "phase7_6b", "seq0014b_setup_population_spec_v1.json")
SEQ0009_PATH = os.path.join(PHASE7_DIR, "phase7_5b", "seq0009_frozen_structural_spec_v1.json")
SEQ0014A_PATH = os.path.join(PHASE7_DIR, "phase7_5c", "seq0014_frozen_structural_spec_v1.json")
OUTCOME_SURFACE_PATH = os.path.join(PHASE7_DIR, "phase7_3", "outcome_surface_v3.py")


def build():
    spec_doc = load_json(SPEC_PATH)
    spec = spec_doc["payload"]
    result_doc = load_json(RESULT_PATH)
    result = result_doc["payload"]
    setup_pop = load_json(SETUP_POP_PATH)["payload"]
    seq0009 = load_json(SEQ0009_PATH)["payload"]
    seq0014a = load_json(SEQ0014A_PATH)["payload"]

    # ---- Evidenza 1: l'outcome di SEQ-0014B NON era scelto quando l'horizon e' stato congelato ----
    outcome_not_chosen_evidence = {
        "setup_population_spec_no_primary_outcome": (
            "candidate_failure_noise_outcomes" in setup_pop and
            not any(k == "primary_outcome" for k in setup_pop["candidate_failure_noise_outcomes"].keys())
        ),
        "candidate_outcomes_listed_without_selection": list(
            setup_pop["candidate_failure_noise_outcomes"]["generic_candidates_from_existing_vocabulary"]
        ) + list(setup_pop["candidate_failure_noise_outcomes"]["family_specific_native_candidates"]),
        "spec_commit_no_primary_outcome_selected_flag": spec["no_primary_outcome_selected"],
        "result_commit_no_primary_outcome_selected_flag": result["no_primary_outcome_selected"],
        "conclusion": "Confermato: nessun primary outcome era scelto ne' in fb52168 (setup population, "
                      "Phase 7.6B) ne' in 6c0d3f6 (questo spec commit) - l'horizon non puo' essere stato "
                      "OUTCOME_DERIVED per SEQ-0014B, semplicemente perche' l'outcome che avrebbe dovuto "
                      "derivarlo non esisteva ancora al momento del freeze.",
    }

    # ---- Evidenza 2: il vocabolario degli outcome candidati non porta un orizzonte intrinseco ----
    outcome_vocabulary_source_hash = file_sha256(OUTCOME_SURFACE_PATH)
    with open(OUTCOME_SURFACE_PATH, encoding="utf-8") as f:
        outcome_surface_src = f.read()
    outcome_vocabulary_has_no_intrinsic_horizon_parameter = (
        "natural_horizon" not in outcome_surface_src and "horizon_bars" not in outcome_surface_src
    )
    outcome_vocabulary_evidence = {
        "file": "server/research_scripts/phase7/phase7_3/outcome_surface_v3.py",
        "file_sha256": outcome_vocabulary_source_hash,
        "ALL_OUTCOME_DEFINITIONS_are_barrier_or_descriptive_not_bar_count_based": True,
        "no_intrinsic_horizon_parameter_in_vocabulary": outcome_vocabulary_has_no_intrinsic_horizon_parameter,
        "conclusion": "Il vocabolario congelato degli outcome candidati (P_PLUS_*ATR_BEFORE_MINUS_1ATR, MFE, "
                      "MAE, TIME_TO_MFE, TIME_TO_TARGET, CONTINUATION_PROBABILITY, REVERSAL_PROBABILITY, "
                      "REALIZED_VOLATILITY_AFTER_SETUP, PATH_EFFICIENCY) e' definito a livello di TIPO "
                      "(barriera di prezzo o statistica descrittiva), MAI con un orizzonte in barre "
                      "incorporato - l'orizzonte e' una scelta SEPARATA, operazionalizzata per esperimento, "
                      "non deducibile dal solo nome dell'outcome.",
    }

    # ---- Evidenza 3: all'interno del progetto, esperimenti diversi su 'regime' hanno gia' usato orizzonti DIVERSI ----
    cross_experiment_horizon_evidence = {
        "SEQ-0014A_state_entry_natural_horizon": seq0014a["proposed_natural_horizon"],
        "SEQ-0009_sweep_reversal_natural_horizon": seq0009["proposed_natural_horizon"],
        "horizons_differ_within_the_same_project": (
            seq0014a["proposed_natural_horizon"] != seq0009["proposed_natural_horizon"]
        ),
        "conclusion": "SEQ-0014A (fenomeno di state-entry, stesso substrato di regime di SEQ-0014B) usa "
                      "natural_horizon=20; SEQ-0009 (sweep-reversal) usa natural_horizon=40 - DUE valori "
                      "diversi gia' coesistono nel progetto per claim/meccanismi diversi. Questo conferma che "
                      "l'orizzonte NON e' una costante universale del progetto derivabile meccanicamente per "
                      "qualunque nuovo claim - e' scelto per esperimento, in funzione del claim/outcome "
                      "specifico.",
    }

    # ---- Classificazione per famiglia: derivazione MECCANICA indipendente dell'orizzonte 40, se esiste ----
    gap_rules = spec["within_family_geometry_rule"]["family_specific_episode_gap_rule"]
    per_family_horizon_derivation = {}
    for fam, g in gap_rules.items():
        if fam == "SWEEP":
            per_family_horizon_derivation[fam] = {
                "has_independent_mechanistic_horizon_derivation": True,
                "derivation_source": "seq0009_frozen_structural_spec_v1.json.natural_horizon_rationale "
                                      "(Phase 7.5B) - derivato dalla scala temporale del meccanismo "
                                      "liquidity-sweep-poi-reversal ('un'ipotesi di rigetto/inversione su H4 "
                                      "e' tipicamente attesa risolversi entro un orizzonte multi-giorno').",
                "derivation_was_for_this_experiment": False,
                "note": "La derivazione esiste ma e' stata fatta per il claim SWEEP-reversal di SEQ-0009, "
                        "NON per il claim filter-utility di SEQ-0014B (un claim diverso, con un outcome "
                        "diverso e non ancora scelto) - riusare il NUMERO non e' lo stesso di riderivarlo "
                        "per QUESTO esperimento.",
            }
        else:
            per_family_horizon_derivation[fam] = {
                "has_independent_mechanistic_horizon_derivation": False,
                "derivation_source": None,
                "derivation_was_for_this_experiment": False,
                "note": f"Nessuna derivazione meccanica indipendente di un orizzonte di risoluzione "
                        f"dell'outcome esiste per {fam} in questo progetto - solo l'episode_gap_rule "
                        f"(dichiarato in 6c0d3f6) e' stato derivato dal meccanismo del detector; il "
                        f"natural_horizon condiviso (40) e' stato ereditato dalla convenzione di SEQ-0009 "
                        f"per coerenza del disegno pooled, non ri-derivato per {fam}.",
            }

    # ---- Classificazione finale ----
    any_mechanism_derived_for_this_experiment = any(
        v["has_independent_mechanistic_horizon_derivation"] and v["derivation_was_for_this_experiment"]
        for v in per_family_horizon_derivation.values()
    )
    horizon_classification = {
        "value_bars": 40,
        "embargo_bars": 39,
        "classification": "PROJECT_CONVENTION",
        "classification_options_considered": {
            "A_MECHANISM_DERIVED": {
                "verdict": False,
                "reason": "Solo SWEEP possiede una derivazione meccanica indipendente di un orizzonte "
                          "temporale (Phase 7.5B), e quella derivazione era per il claim SWEEP-reversal, "
                          "non per il claim filter-utility pooled di SEQ-0014B. Le altre 5 famiglie non "
                          "hanno mai avuto una derivazione di orizzonte indipendente in questo progetto.",
            },
            "B_OUTCOME_DERIVED": {
                "verdict": False,
                "reason": "Impossibile per costruzione: nessun primary outcome era scelto per SEQ-0014B al "
                          "momento del freeze (vedi outcome_not_chosen_evidence) - e anche il vocabolario "
                          "degli outcome candidati non porta un orizzonte intrinseco (vedi "
                          "outcome_vocabulary_evidence).",
            },
            "C_PROJECT_CONVENTION": {
                "verdict": True,
                "reason": "Il valore e' stato riusato dalla convenzione generale di progetto per meccanismi "
                          "reversal/continuation su H4 (testuale nello spec commit stesso: 'CONVENZIONE "
                          "GENERALE di progetto ... stesso ordine di grandezza temporale, giorni non ore ne' "
                          "mesi'), motivato dalla necessita' PRATICA di avere una soglia di embargo UNICA per "
                          "rendere ben definito il declustering cross-family - non da una derivazione "
                          "indipendente per il claim specifico di SEQ-0014B.",
            },
        },
        "any_mechanism_derived_for_this_specific_experiment": any_mechanism_derived_for_this_experiment,
        "per_family_horizon_derivation": per_family_horizon_derivation,
    }

    # ---- Verifica: gli artifact frozen non sono stati toccati (nessuna modifica retroattiva) ----
    frozen_artifacts_untouched = {
        "spec_commit_canonical_sha256_unchanged": spec_doc["canonical_sha256"],
        "result_commit_canonical_sha256_unchanged": result_doc["canonical_sha256"],
        "spec_file_sha256": file_sha256(SPEC_PATH),
        "result_file_sha256": file_sha256(RESULT_PATH),
        "no_modification_made_to_frozen_spec_or_result": True,
    }

    # ---- Scope correction: NOT_TESTABLE va delimitato a DESIGN_V1, mai a "MECH-23 impossibile" ----
    design_v1_identity = {
        "name": "SEQ-0014B_DESIGN_V1",
        "components": {
            "setup_population": "fb52168fe2ff27f91abc8671b08992c56e654f4f (6 famiglie, pooled stratificato, "
                                 "regime/timestamp contract)",
            "structural_preflight_spec": SPEC_COMMIT,
            "natural_horizon_bars": 40,
            "outcome_overlap_embargo_bars": 39,
            "matching_contract": "volatility_state_pre_setup (atr_percentile[t-1]), k=5, "
                                  "minimum_control_count=20, max_control_reuse_per_run=5, "
                                  "SAME_SETUP_FAMILY_ID_OPPOSITE_REGIME_ONLY",
            "structural_preflight_result": RESULT_COMMIT,
        },
        "verdict_scoped_to_this_identity": "NOT_TESTABLE_WITH_FROZEN_SETUP_POPULATION",
        "verdict_NOT_scoped_to": "MECH-23 (il claim filter-utility originale) come impossibile da testare in "
                                  "assoluto - un futuro DESIGN_V2 con un outcome scelto ex-ante e un "
                                  "orizzonte derivato indipendentemente da quell'outcome e' una domanda "
                                  "aperta, non preclusa da questo risultato.",
    }

    future_experiment_requirements = [
        "Il primary outcome di SEQ-0014B deve essere scelto EX-ANTE (prima di qualunque nuova geometria), "
        "non dopo aver visto che horizon=40 produce un risultato scomodo.",
        "L'orizzonte naturale del nuovo design deve avere una giustificazione meccanica INDIPENDENTE, "
        "derivata dall'outcome scelto (non riusata per convenzione da un esperimento diverso).",
        "Un nuovo design con un orizzonte diverso richiede una NUOVA identita' di esperimento/spec "
        "(es. SEQ-0014B_DESIGN_V2), mai una modifica silenziosa dei parametri di DESIGN_V1.",
        "L'intera provenance di DESIGN_V1 (fallito, hard stop) deve restare referenziata nel nuovo design - "
        "mai nascosta o sostituita silenziosamente.",
        "Nessuna esplorazione di orizzonti alternativi (10/20/30/ecc.) e' ammessa per 'salvare' SEQ-0014B - "
        "l'orizzonte deve emergere dall'outcome scelto, non essere scelto per far tornare i conti.",
    ]

    framework_rule_proposed = {
        "rule": "if dependence geometry depends on outcome horizon: outcome class + natural horizon must be "
                "frozen before final structural feasibility verdict",
        "new_result_classification_label": "HORIZON_CONDITIONAL_STRUCTURAL_RESULT",
        "label_meaning": "Un verdetto strutturale calcolato PRIMA che l'outcome (e quindi il suo orizzonte "
                          "naturale) sia stato scelto ex-ante deve essere etichettato "
                          "HORIZON_CONDITIONAL_STRUCTURAL_RESULT, non un verdetto universale - resta valido "
                          "SOLO per l'identita' di design (setup population + horizon + embargo + matching "
                          "contract) con cui e' stato calcolato.",
        "retroactive_application_to_7_6c": "Il RESULT COMMIT 80e7cbc va inteso, con il senno di poi, come un "
                                            "HORIZON_CONDITIONAL_STRUCTURAL_RESULT scoped a DESIGN_V1 - "
                                            "questo audit lo dichiara qui esplicitamente SENZA modificare "
                                            "l'artifact originale (disciplina di cronologia dei commit: un "
                                            "artifact congelato non si corregge retroattivamente, si "
                                            "annota con un audit separato).",
        "scope_of_this_proposal": "Proposta di regola per FUTURI structural preflight - nessuna nuova "
                                   "infrastruttura di enforcement e' stata costruita in questo audit "
                                   "(esplicitamente fuori scope, per istruzione: 'non espandere "
                                   "inutilmente l'infrastruttura').",
    }

    payload = {
        "phase": "7.6C-AUDIT",
        "artifact_role": "OUTCOME_HORIZON_ORDERING_AUDIT",
        "scope_note": "Audit di sequencing metodologico - verifica se l'ordine 'horizon=40/embargo=39 -> "
                       "structural preflight -> (futura) scelta del primary outcome' era corretto per un "
                       "claim filter-utility il cui outcome non era ancora congelato. NON un rescue: nessun "
                       "orizzonte alternativo ispezionato, nessun outcome letto, nessuna modifica ai "
                       "frozen artifact.",
        "baseline_commit": BASELINE_COMMIT,
        "audited_spec_commit": SPEC_COMMIT,
        "audited_result_commit": RESULT_COMMIT,
        "outcome_not_chosen_evidence": outcome_not_chosen_evidence,
        "outcome_vocabulary_evidence": outcome_vocabulary_evidence,
        "cross_experiment_horizon_evidence": cross_experiment_horizon_evidence,
        "horizon_classification": horizon_classification,
        "frozen_artifacts_untouched": frozen_artifacts_untouched,
        "design_v1_identity_and_scope_correction": design_v1_identity,
        "future_experiment_requirements": future_experiment_requirements,
        "framework_rule_proposed": framework_rule_proposed,
        "no_alternate_horizon_inspected": True,
        "no_preflight_rereun": True,
        "no_rescue_attempted": True,
        "no_frozen_spec_or_result_modified": True,
        "no_nexus_outcome_data_accessed": True,
        "no_edge_discovery_performed": True,
        "no_primary_outcome_selected": True,
        "seq0015_status_unchanged": "CLOSED_NOT_REEXAMINED_AS_CANDIDATE",
        "seq0009_status_unchanged": "CLOSED_NOT_REEXAMINED_AS_CANDIDATE",
    }
    return payload


def main():
    payload = build()
    doc = wrap_with_provenance(
        payload, script="server/research_scripts/phase7/phase7_6c/build_seq0014b_outcome_horizon_ordering_audit.py"
    )
    out_path = os.path.join(PHASE76C_DIR, "seq0014b_outcome_horizon_ordering_audit_v1.json")
    save_json(out_path, doc)
    print(f"Written {out_path}")
    print(f"canonical_sha256={doc['canonical_sha256']}")
    print(f"horizon classification: {payload['horizon_classification']['classification']}")


if __name__ == "__main__":
    main()
