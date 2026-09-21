#!/usr/bin/env python3
"""Phase 7.8C - Serious 3Y Blocker Resolution & Run Authorization.

Risolve ex-ante i 3 blocker NOT_YET_JUSTIFIED lasciati aperti in Phase
7.8B (`26be386`) - MAI inventando un numero per farli passare, ma
cercando (e trovando, per 2 dei 3) una regola STRUTTURALE/SCALE-FREE o
un riposizionamento del gate coerente con le policy gia' esistenti.
Corregge anche un'imprecisione di naming: il verdetto primario copre
~2.5 anni FRESH, non l'intera finestra di 3 anni - "3Y OOS" sarebbe
un'etichetta impropria.

NESSUN Serious 3Y eseguito. NESSUN outcome letto. NESSuna optimization
di parametri. NESSUNA modifica retroattiva a 7.8A/7.8B (entrambi
restano invariati - verificato via hash).

Il PRE-RUN MANIFEST/SEAL vero e proprio (con date/hash/tick coverage
REALI) NON viene creato qui - richiede accesso dati live (sync MT5) non
disponibile in questa sessione di ricerca. Questo modulo ne definisce
SOLO lo schema/procedura obbligatoria - un contratto per il passo
successivo, non l'artifact stesso."""
import os
import sys

PHASE78C_DIR = os.path.dirname(os.path.abspath(__file__))
PHASE7_DIR = os.path.abspath(os.path.join(PHASE78C_DIR, ".."))
ROOT = os.path.abspath(os.path.join(PHASE78C_DIR, "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase6_6"))
from canonical_utils import file_sha256, load_json, save_json, wrap_with_provenance  # noqa: E402

BASELINE_COMMIT = "26be3863413682a9e5baef45cb59a0f6f7f5d2d9"
CANDIDATE_ID = "VOLATILITY_BREAKOUT_CONFIRMED"

PREREG_PATH = os.path.join(PHASE7_DIR, "phase7_8b", "volatility_breakout_serious_3y_prereg_v1.json")
VOI_PATH = os.path.join(PHASE7_DIR, "phase7_8a", "volatility_breakout_voi_contract_v1.json")
COST_MODEL_PATH = os.path.join(PHASE7_DIR, "policies", "cost_model_integration.json")
EFFECT_SIZE_POLICY_PATH = os.path.join(PHASE7_DIR, "policies", "effect_size_first_policy.json")
FAILURE_MEMORY_PATH = os.path.join(
    ROOT, "vault", "01-Trading",
    "NEXUS - Failure Memory (Registro Pattern di Fallimento Metodologico) (12-09).md",
)

NOT_YET_JUSTIFIED = "NOT_YET_JUSTIFIED"


def build():
    prereg_doc = load_json(PREREG_PATH)
    prereg = prereg_doc["payload"]
    voi_doc = load_json(VOI_PATH)
    cost_model = load_json(COST_MODEL_PATH)
    effect_size_policy = load_json(EFFECT_SIZE_POLICY_PATH)

    # ================= 1. Naming / fresh-window correction (annotazione, 7.8B non modificato) =================
    naming_correction = {
        "target_artifact": "server/research_scripts/phase7/phase7_8b/"
                           "volatility_breakout_serious_3y_prereg_v1.json",
        "target_artifact_canonical_sha256_unchanged": prereg_doc["canonical_sha256"],
        "modified_in_this_phase": False,
        "issue": "Il test e' chiamato 'Serious 3Y', ma il verdetto primario copre solo la porzione FRESH "
                 "(~2.5 anni) - gli ultimi ~6 mesi sono diagnostici perche' gia' osservati "
                 "(fast-structural). Chiamare la porzione primaria 'pure 3Y OOS' sarebbe impreciso.",
        "corrected_vocabulary": {
            "TOTAL_TEST_WINDOW": "~3 anni (ultimo intervallo continuo disponibile, regola gia' congelata "
                                  "in 7.8B sez.3)",
            "PRIMARY_FRESH_VERDICT_WINDOW": "~2.5 anni (TOTAL_TEST_WINDOW meno la porzione gia' osservata) "
                                             "- SOLO questa porzione alimenta il verdetto PASS/BORDERLINE/"
                                             "FAIL primario",
            "PREVIOUSLY_OBSERVED_DIAGNOSTIC_WINDOW": "~6 mesi (2026-03/2026-09, identica al fast-"
                                                       "structural gia' fatto) - MAI usata per il verdetto "
                                                       "primario, riportata solo come replica diagnostica",
        },
        "forbidden_labels": ["3Y OOS", "pure out-of-sample 3 anni", "full 3-year fresh validation"],
        "correct_label_for_reporting": "Serious 3Y Validation (finestra totale 3 anni) con verdetto "
                                        "primario sulla porzione FRESH (~2.5 anni) e diagnostica di "
                                        "replica sulla porzione gia' osservata (~6 mesi)",
    }

    # ================= 2. Materiality blocker resolution =================
    materiality_resolution = {
        "blocker_from_7_8b": "materiality_threshold_beyond_breakeven (NOT_YET_JUSTIFIED)",
        "question": "E' scientificamente necessario, per lo stage STRATEGY_VALIDATION, un numero R oltre "
                    "breakeven - o l'esistenza/robustezza dell'edge e' un gate sufficiente a questo "
                    "livello, rimandando la soglia economica di allocazione capitale a uno stage "
                    "successivo?",
        "supporting_policy_evidence": {
            "cost_model_integration_two_state_framework": (
                "cost_model_integration.json definisce ESPLICITAMENTE due stati distinti: STRUCTURAL_EDGE "
                "('l'effetto e' valido a costo ZERO') e EXECUTABLE_EDGE_AFTER_COST ('l'effetto SOPRAVVIVE "
                "dopo aver sottratto il costo... usando ALMENO BROKER_BASELINE'). La definizione di "
                "EXECUTABLE_EDGE_AFTER_COST e' un criterio di ESISTENZA-DOPO-COSTO, non di magnitudo "
                "minima - supporta direttamente l'idea che 'sopravvivere ai costi' sia un gate a se', "
                "distinto da 'quanto e' grande l'edge'."
            ),
            "effect_size_first_policy_tension": (
                "effect_size_first_policy.json impone che l'ampiezza dell'effetto sia dichiarata e "
                "giudicata MATERIALE prima del p-value, per evitare che un ΔP minuscolo ma "
                "statisticamente significativo venga chiamato SUPPORTED - questo principio resta valido "
                "in generale e NON viene eliminato qui: viene PRESERVATO tramite l'obbligo di riportare "
                "sempre expectancy_R osservato (mai nascosto), ma la sua applicazione come GATE numerico "
                "e' riposizionata al livello dove la domanda 'quanto conta economicamente' si pone "
                "davvero - PORTFOLIO_RISK/EXECUTION_VALIDATION, non STRATEGY_VALIDATION."
            ),
        },
        "resolution_supportability": "PARTIALLY_SUPPORTED_BY_EXISTING_POLICY_STRUCTURE_ADAPTED",
        "resolution_supportability_note": "Non e' una conseguenza gia' scritta parola-per-parola in una "
                                            "policy esistente (da qui 'PARTIALLY', non 'FULLY') - e' "
                                            "un'estensione coerente della distinzione a due stati gia' "
                                            "presente in cost_model_integration.json, applicata qui per la "
                                            "prima volta a una strategia con execution reale (non un raw "
                                            "event). Adottata perche' l'alternativa (inventare un numero R "
                                            "arbitrario) sarebbe MENO giustificata, non perche' sia l'unica "
                                            "lettura possibile.",
        "adopted_resolution": {
            "executable_edge_gate": "CI95(expectancy_R, BROKER_BASELINE).lower_bound > 0 AND "
                                      "expectancy_R(STRESS) > 0",
            "numeric_materiality_threshold": "NOT_REQUIRED_AT_THIS_STAGE",
            "magnitude_still_always_reported": True,
            "magnitude_reporting_rationale": "Preserva lo spirito di effect_size_first_policy.json (mai "
                                              "nascondere l'ampiezza dell'effetto) senza trasformarla in un "
                                              "gate numerico prematuro - un futuro stage PORTFOLIO_RISK "
                                              "puo' applicare la propria soglia di materialita' economica "
                                              "sullo stesso expectancy_R gia' riportato qui, senza "
                                              "ricalcolare nulla.",
            "deferred_to_stage": "PORTFOLIO_RISK (o EXECUTION_VALIDATION se la sizing gia' vi richiede una "
                                  "soglia) - MAI stabilita ora.",
        },
        "status": "RESOLVED",
    }

    # ================= 3. Temporal stability blocker resolution (scale-free) =================
    temporal_stability_resolution = {
        "blocker_from_7_8b": "temporal_stability_criterion (NOT_YET_JUSTIFIED)",
        "rejected_approach": "Una soglia in unita' R fissa (es. 'anno > -0.05R') - sarebbe un numero "
                              "inventato senza provenienza (vietato da threshold_policy.json, nessuna "
                              "fonte DOMAIN_DEFINED/PREDECLARED_QUANTILE esiste per questo).",
        "adopted_rule": {
            "segmentation": "Frozen PRIMA del run (Year 1/2/3 della finestra PRIMARY_FRESH_VERDICT_WINDOW, "
                             "gia' congelata in 7.8B sez.10 - non ridefinita qui).",
            "criterion_1": "Almeno 2 dei 3 segmenti annuali principali hanno expectancy_R >= 0 (segno, non "
                            "magnitudo - scale-free per costruzione).",
            "criterion_2": "Nessun singolo segmento puo' spiegare piu' del 100% del risultato netto "
                            "aggregato mentre TUTTI gli altri segmenti combinati sono negativi (un rapporto "
                            "fra quantita' della STESSA unita' - scale-free, mai un valore assoluto in R).",
            "why_scale_free": "Entrambi i criteri sono basati su CONFRONTI DI SEGNO e RAPPORTI fra "
                              "quantita' omogenee (expectancy_R di un segmento vs expectancy_R totale), MAI "
                              "un valore assoluto isolato - non richiedono alcuna calibrazione specifica "
                              "della scala R di questa strategia.",
        },
        "outcome_mapping": {
            "both_criteria_satisfied": "Nessun blocco per instabilita' temporale (il criterio non "
                                         "impedisce da solo un PASS).",
            "criterion_1_or_2_violated_moderately": "Contribuisce a un verdetto BORDERLINE, mai un "
                                                      "blocco automatico a FAIL da solo (coerente col "
                                                      "precedente SAR: 7 su 8 criteri passati -> "
                                                      "BORDERLINE).",
            "both_criteria_violated": "Contribuisce fortemente verso FAIL (coerente col precedente MACD: "
                                        "'solo 1 dei 3 anni e' positivo' + un secondo criterio fallito -> "
                                        "FAIL netto).",
        },
        "status": "RESOLVED",
    }

    # ================= 4. Same-bar SL/TP blocker resolution =================
    same_bar_resolution = {
        "blocker_from_7_8b": "same_bar_sl_tp_ambiguity_rule (NOT_YET_JUSTIFIED)",
        "adopted_principle": "REAL_TICK_REQUIRED_FOR_PRIMARY_VERDICT - nessuna tie-break sintetica "
                              "(es. 'assumi SL first') se l'ordine reale dei tick e' disponibile o "
                              "ricostruibile.",
        "resolution_logic": {
            "if_ordering_resolvable": "Usa l'ordine reale dei tick (nessuna assunzione).",
            "if_ordering_not_resolvable": "Flag esplicito EXECUTION_ORDER_UNRESOLVED per QUEL trade "
                                            "specifico - MAI assunto silenziosamente ne' TP-first ne' "
                                            "SL-first (stesso principio gia' in Failure Memory, pattern "
                                            "DATA_COVERAGE_GAP: 'flaggare esplicitamente - non escludere "
                                            "silenziosamente ne' includere senza avviso - gli eventi il cui "
                                            "esito dipende da una finestra dati mancante').",
        },
        "chosen_option_between_A_and_B": "SINTESI (ne' pura A ne' pura B, entrambe insufficienti da sole)",
        "why_neither_pure_A_nor_pure_B": "L'opzione A pura (escludere ex-ante dal primary window) "
                                          "rischierebbe di NASCONDERE silenziosamente un problema (esclude "
                                          "senza dichiarare l'impatto) - esattamente il comportamento "
                                          "vietato dal pattern DATA_COVERAGE_GAP. L'opzione B pura (blocca "
                                          "l'intero run) e' sproporzionata se solo una minoranza di trade "
                                          "e' ambigua e l'ambiguita' non cambia il verdetto.",
        "adopted_synthesis": {
            "primary_point_estimate": "Calcolato SOLO sui trade con ordine risolto (i trade "
                                        "EXECUTION_ORDER_UNRESOLVED sono esclusi dal punto stimato "
                                        "primario).",
            "mandatory_sensitivity_bracket": "Per OGNI trade EXECUTION_ORDER_UNRESOLVED, ricalcolare "
                                              "expectancy_R in DUE scenari limite: (a) tutti risolti a "
                                              "favore di TP-first, (b) tutti risolti a favore di SL-first - "
                                              "un bracket [worst_case, best_case] intorno al punto stimato "
                                              "primario, MAI un singolo numero che nasconde l'ambiguita'.",
            "decision_rule": "Se il bracket [worst_case, best_case] NON cambia la classificazione "
                             "PASS/BORDERLINE/FAIL del punto stimato primario, il verdetto primario resta "
                             "valido (l'ambiguita' e' irrilevante alla decisione). Se il bracket CAMBIA la "
                             "classificazione (es. worst_case=FAIL ma best_case=PASS), il verdetto e' "
                             "'EXECUTION_ORDER_UNRESOLVED_BLOCKS_VERDICT' - un nuovo stato esplicito, mai "
                             "risolto scegliendo arbitrariamente un lato del bracket.",
        },
        "why_this_is_better_than_A_or_B_alone": "Preserva il campione (a differenza di B), non nasconde "
                                                  "l'incertezza (a differenza di A pura), e non richiede "
                                                  "inventare una soglia di 'quanti trade ambigui sono "
                                                  "troppi' (la decisione emerge STRUTTURALMENTE da se' il "
                                                  "bracket cambia la classificazione, non da un conteggio "
                                                  "arbitrario).",
        "status": "RESOLVED",
    }

    # ================= 5. PRE-RUN MANIFEST / SEAL (schema/procedura, NON l'artifact reale) =================
    prerun_manifest_schema = {
        "artifact_not_created_in_this_phase": True,
        "reason_not_created_now": "Richiede sincronizzazione dati MT5 live (date esatte, hash dataset, "
                                    "tick coverage reale) - non disponibile in questa sessione di ricerca "
                                    "(nessun accesso a un terminale MT5 live). Questa fase definisce SOLO "
                                    "lo schema/procedura obbligatoria per il passo successivo.",
        "required_fields": [
            "exact_start_timestamp", "exact_end_timestamp",
            "fresh_window_start", "fresh_window_end",
            "previously_observed_window_start", "previously_observed_window_end",
            "broker_timezone_offset", "symbol", "timeframe", "tester_model",
            "tick_coverage_pct_by_subperiod", "dataset_history_hash",
            "strategy_commit_or_hash", "cost_model_hash", "prereg_hash", "code_commit_sha",
        ],
        "procedural_rule": {
            "step_1": "AFTER data synchronization (i dati storici reali sono scaricati/sincronizzati e "
                      "congelati)",
            "step_2": "BEFORE backtest execution/results (il manifest e' creato e committato PRIMA di "
                      "calcolare qualunque statistica sui trade)",
            "invariant": "Nessun risultato (PF, expectancy, trade count, ecc.) deve comparire nel "
                        "manifest - solo identita'/provenienza dei dati e del protocollo.",
        },
        "hash_references_this_manifest_must_pin": {
            "prereg_hash": prereg_doc["canonical_sha256"],
            "cost_model_hash": file_sha256(COST_MODEL_PATH),
            "strategy_frozen_commit": prereg["strategy_identity_frozen"]["frozen_commit"],
        },
        "verification_before_run": "Un secondo passo ('verify seal') deve confermare che il manifest "
                                    "committato corrisponde ESATTAMENTE ai dati poi effettivamente usati "
                                    "per calcolare le statistiche (stesso hash) - PRIMA di considerare "
                                    "qualunque risultato valido.",
    }

    # ================= 6. Run authorization =================
    blockers_resolved = ["materiality_threshold_beyond_breakeven", "temporal_stability_criterion",
                         "same_bar_sl_tp_ambiguity_rule"]
    run_authorization = {
        "blockers_from_7_8b_status": {b: "RESOLVED" for b in blockers_resolved},
        "conceptual_protocol_status": "FULLY_SPECIFIED",
        "verdict": "READY_FOR_PRE_RUN_SEAL",
        "verdict_options_considered": ["READY_FOR_PRE_RUN_SEAL", "STILL_BLOCKED"],
        "explicitly_not_ready_to_run": True,
        "why_not_ready_to_run": "READY_TO_RUN richiederebbe che il PRE-RUN MANIFEST (sez.5) esista GIA' "
                                 "con date/hash/tick-coverage REALI, committato - un passo procedurale "
                                 "SUCCESSIVO a questa fase, non ancora compiuto (nessun accesso dati live "
                                 "in questa sessione).",
        "next_required_action": "Sincronizzare i dati storici reali (MT5), generare il PRE-RUN MANIFEST "
                                 "con i valori reali secondo lo schema di sez.5, committarlo, verificarlo, "
                                 "e SOLO DOPO autorizzare l'esecuzione del backtest.",
    }

    # ================= 7. Final gate chain (formalizzazione, contratto) =================
    final_gate_chain = {
        "stages": ["7.8C_BLOCKER_RESOLUTION (questa fase)", "PRE_RUN_MANIFEST_SEAL",
                   "VERIFY_SEAL", "EXECUTE_SERIOUS_VALIDATION", "IMMUTABLE_RESULT_ARTIFACT"],
        "rule": "Ogni stage produce un artifact committato PRIMA che il successivo possa iniziare - "
                "nessuno stage puo' essere eseguito fuori ordine o retroattivamente modificato una volta "
                "che il successivo e' iniziato.",
        "not_implemented_as_new_infrastructure": True,
    }

    payload = {
        "phase": "7.8C", "artifact_role": "SERIOUS_3Y_RUN_AUTHORIZATION",
        "candidate_id": CANDIDATE_ID,
        "scope_note": "Risolve i 3 blocker NOT_YET_JUSTIFIED di Phase 7.8B senza inventare numeri, "
                       "corregge il naming fresh-window, definisce lo schema del PRE-RUN MANIFEST/SEAL. "
                       "NESSUN Serious 3Y eseguito, nessun outcome letto, nessuna optimization.",
        "baseline_commit": BASELINE_COMMIT,
        "source_artifacts_untouched": {
            "prereg": {"file": "server/research_scripts/phase7/phase7_8b/"
                       "volatility_breakout_serious_3y_prereg_v1.json",
                       "canonical_sha256": prereg_doc["canonical_sha256"]},
            "voi_contract": {"file": "server/research_scripts/phase7/phase7_8a/"
                              "volatility_breakout_voi_contract_v1.json",
                              "canonical_sha256": voi_doc["canonical_sha256"]},
            "modified_in_this_phase": False,
        },
        "naming_correction": naming_correction,
        "materiality_blocker_resolution": materiality_resolution,
        "temporal_stability_blocker_resolution": temporal_stability_resolution,
        "same_bar_sl_tp_blocker_resolution": same_bar_resolution,
        "prerun_manifest_schema": prerun_manifest_schema,
        "run_authorization": run_authorization,
        "final_gate_chain": final_gate_chain,
        "serious_3y_not_executed": True,
        "no_new_outcome_data_accessed": True,
        "no_parameter_optimization_performed": True,
        "no_edge_discovery_performed": True,
        "no_retroactive_modification_of_frozen_artifacts": True,
        "seq0015_status_unchanged": "CLOSED_NOT_REEXAMINED_AS_CANDIDATE",
        "seq0009_status_unchanged": "CLOSED_NOT_REEXAMINED_AS_CANDIDATE",
    }
    return payload


def main():
    payload = build()
    doc = wrap_with_provenance(
        payload, script="server/research_scripts/phase7/phase7_8c/build_volatility_breakout_run_authorization.py",
    )
    out_path = os.path.join(PHASE78C_DIR, "volatility_breakout_serious_3y_run_authorization_v1.json")
    save_json(out_path, doc)
    print(f"Written {out_path}")
    print(f"canonical_sha256={doc['canonical_sha256']}")
    print(f"verdict={payload['run_authorization']['verdict']}")


if __name__ == "__main__":
    main()
