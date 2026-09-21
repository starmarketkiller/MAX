#!/usr/bin/env python3
"""Phase 7.6A - SEQ-0014 Outcome & Statistical Preregistration.

Costruisce il contratto statistico PRIMA di leggere qualunque outcome
(outcomes_v1.csv non e' mai aperto da questo script - verificato anche
da test_seq0014_statistical_preregistration.py). NESSUNA discovery
viene eseguita qui.

STATO: BLOCCATO su un punto solo (control-pool / baseline estimand -
sec.2 della richiesta Phase 7.6A) - vedi baseline_estimand_audit sotto.
Le altre sezioni (domanda scientifica, outcome family, inference/
dependence/multiplicity contract) sono LOGICAMENTE INDIPENDENTI dalla
scelta del control pool (definiscono COSA misurare, non CHI sono i
controlli) e sono congelate qui comunque - saranno riusate senza
modifica quando il blocco sara' risolto da una nuova structural
spec/preflight (fase separata, MAI una modifica silenziosa dopo
FEASIBLE)."""
import os
import sys

import pandas as pd

PHASE76A_DIR = os.path.dirname(os.path.abspath(__file__))
PHASE7_DIR = os.path.abspath(os.path.join(PHASE76A_DIR, ".."))
ROOT = os.path.abspath(os.path.join(PHASE76A_DIR, "..", "..", "..", ".."))
PHASE75C_DIR = os.path.join(PHASE7_DIR, "phase7_5c")
PHASE71_DATA = os.path.join(PHASE7_DIR, "phase7_1", "data")

sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase6_6"))
sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase6_5"))
sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase7", "phase7_3"))
sys.path.insert(0, PHASE75C_DIR)
from canonical_utils import wrap_with_provenance, save_json, load_json, canonical_sha256  # noqa: E402
from dependence_diagnostics import assign_clusters  # noqa: E402
from outcome_surface_v3 import OutcomeSurfaceV3  # noqa: E402
from seq0014_state_entry_detector import compute_in_state, compute_state_entry_rows  # noqa: E402

STATE_PATH = os.path.join(PHASE71_DATA, "market_state_dataset_p71.csv")
FROZEN_SPEC_PATH = os.path.join(PHASE75C_DIR, "seq0014_frozen_structural_spec_v1.json")
RESULT_PATH = os.path.join(PHASE75C_DIR, "seq0014_structural_feasibility_result_v1.json")


def audit_control_pool_contamination():
    """Quantifica STRUTTURALMENTE (nessun outcome) quale frazione del pool
    di controllo attualmente eleggibile per ciascun evento (sotto la
    control_pool_construction_policy GIA' congelata in Phase 7.5C) e'
    essa stessa in LOW_INFORMATION_STATE - la contaminazione descritta
    nella review."""
    frozen = load_json(FROZEN_SPEC_PATH)["payload"]
    ms = frozen["matching_spec"]
    discovery_start, discovery_end = ms["split_boundaries"]["discovery"]
    horizon = frozen["proposed_natural_horizon"]
    episode_gap_rule = frozen["episode_gap_rule"]
    discovery_rows = list(range(discovery_start, discovery_end))

    state = pd.read_csv(STATE_PATH, parse_dates=["bar_time_utc"]).sort_values("bar_time_utc").reset_index(drop=True)
    de_cut = frozen["state_definition"]["tercile_cutpoints_fit_on_discovery_only"]
    de_by_row = {r: float(state["directional_efficiency"].iloc[r]) for r in discovery_rows}
    in_state = compute_in_state(de_by_row, cutpoint_low_med=de_cut["q1_low_med"])
    events = compute_state_entry_rows(in_state)

    clusters, _ = assign_clusters(events, episode_gap_rule)
    episode_of_row = {r: cid for cid, members in enumerate(clusters) for r in members}

    def control_pool_for(t):
        same_episode = set(clusters[episode_of_row[t]])
        excluded = same_episode | {r for r in discovery_rows if abs(r - t) <= horizon}
        return [r for r in discovery_rows if r not in excluded]

    total_pool_rows, contaminated_rows = 0, 0
    for t in events:
        pool = control_pool_for(t)
        total_pool_rows += len(pool)
        contaminated_rows += sum(1 for r in pool if in_state[r])

    base_rate = sum(in_state.values()) / len(discovery_rows)
    return {
        "n_events": len(events),
        "overall_base_rate_of_in_state_across_discovery": base_rate,
        "fraction_of_current_eligible_control_pool_also_in_state": (contaminated_rows / total_pool_rows),
        "interpretation": "La frazione di pool di controllo 'anche in stato' (~1/3) coincide quasi esattamente "
                           "con il base rate generale dello stato su tutta development_discovery - la policy "
                           "attuale (esclusione per finestra+episodio) NON filtra per appartenenza allo stato: "
                           "un control bar ha la STESSA probabilita' di essere esso stesso LOW_INFORMATION_"
                           "STATE che avrebbe una barra estratta a caso da tutta la partition. La control pool "
                           "attuale implementa quindi l'estimand A (barra comparabile generica), non "
                           "l'estimand B (barra comparabile MA specificamente non-choppy).",
    }


def main():
    contamination = audit_control_pool_contamination()

    # ---- sec.5 - outcome surface: riusa OutcomeSurfaceV3 (Phase 7.3, invariato) ----
    # Vocabolario RIUSATO da ALL_OUTCOME_DEFINITIONS (outcome_surface_v3.py, gia' esistente,
    # MAI esteso qui) - degli outcome gia' definiti, SOLO REALIZED_VOLATILITY_AFTER_SETUP e
    # PATH_EFFICIENCY sono genuinamente NON_DIRECTIONAL (tutti gli altri - P_PLUS_*ATR_BEFORE_
    # MINUS_1ATR, MFE/MAE, TIME_TO_TARGET, CONTINUATION/REVERSAL_PROBABILITY - assumono
    # implicitamente una direzione di riferimento BUY/SELL, non applicabile a SEQ-0014).
    # Corrisponde 1:1 all'expected_outcome_family di MECH-23 gia' dichiarato in Phase 7.2
    # (market_sequence_registry_v1.json: ["EXECUTION_FRIENDLINESS", "REALIZED_VOLATILITY_
    # AFTER_SETUP"] - PATH_EFFICIENCY e' l'operazionalizzazione gia' disponibile piu' vicina a
    # EXECUTION_FRIENDLINESS). Famiglia ridotta al minimo indispensabile (sec.3 della
    # richiesta) - nessun outcome diagnostic aggiuntivo registrato, nessuna estensione del
    # vocabolario generale di outcome_surface_v3.py.
    surface = OutcomeSurfaceV3(
        primary_outcome="REALIZED_VOLATILITY_AFTER_SETUP",
        secondary_outcomes=["PATH_EFFICIENCY"],
        diagnostic_outcomes=[],
    )
    assert surface.inferential_family_size() == 2, "1 primary + 1 secondary attesi, nessun diagnostic"

    payload = {
        "sequence_family_id": "SEQFAM-SEQ0014-LOWINFO-STATE-STRUCTURAL-V1",
        "sequence_ids": ["SEQ-0014"],
        "phase": "Phase 7.6A - SEQ-0014 Outcome & Statistical Preregistration",
        "structural_gate_result_ref": "server/research_scripts/phase7/phase7_5c/"
                                       "seq0014_structural_feasibility_result_v1.json",
        "structural_gate_summary": {
            "EVENT_VIEW": 189, "EPISODE_VIEW": 128, "INDEPENDENT_VIEW": 49,
            "independent_units_with_valid_match": 49, "final_structural_verdict": "FEASIBLE",
        },

        # =================================================================
        # PREREGISTRATION STATUS - vedi sec.14/2 della richiesta.
        # =================================================================
        "preregistration_status": "BLOCKED_ON_CONTROL_POOL_ESTIMAND_AMBIGUITY",
        "discovery_authorized": False,
        "blocker_summary": "Il control pool GIA' congelato nello structural spec (Phase 7.5C, mai modificato "
            "qui) non distingue 'barra comparabile generica' (estimand A) da 'barra comparabile "
            "specificamente NON in LOW_INFORMATION_STATE' (estimand B). Evidenza pre-esistente (Phase 7.2, "
            "market_sequence_registry_v1.json, PRIMA di questa preregistrazione) indica che il contrasto "
            "nativo del meccanismo MECH-23 e' l'estimand B ('choppy' vs 'trending'), non A. Correggere la "
            "control_pool_construction_policy richiede una NUOVA structural spec e un NUOVO preflight (fase "
            "separata, MAI una modifica silenziosa dopo un verdetto FEASIBLE gia' raggiunto) - vedi "
            "baseline_estimand_contract sotto per l'audit completo.",

        # =================================================================
        # SEZIONE 1 - Domanda scientifica precisa (congelata, indipendente da A/B)
        # =================================================================
        "scientific_question": {
            "frozen": True,
            "statement": "L'ingresso in LOW_INFORMATION_STATE (MECH-23: directional_efficiency nel proprio "
                         "terzile LOW su development_discovery) modifica la distribuzione del movimento/range "
                         "di prezzo futuro (orizzonte 20 barre H4) rispetto a una baseline comparabile per "
                         "regime di volatilita' - SENZA alcuna direzione BUY/SELL implicita.",
            "falsifiability": "Il claim e' falso se, per il primary endpoint (FORWARD_REALIZED_RANGE_ATR), la "
                               "differenza media accoppiata d_i tra l'osservazione dell'evento e la media dei "
                               "controlli matchati non e' distinguibile da zero (dopo correzione BH sulla "
                               "famiglia di 2 outcome inferenziali) E l'effetto stimato e' sotto la soglia di "
                               "materialita' (sec.10).",
            "pre_existing_mechanism_definition": "Coerente con market_sequence_registry_v1.json (Phase 7.2, "
                "PRIMA di questa preregistrazione): MECH-23 falsification_definition originale contrasta "
                "esplicitamente 'stato choppy' vs 'stato trending' - citato qui SOLO come evidenza che "
                "l'estimand B non e' stato scelto guardando outcome di questa fase, ma era gia' la "
                "formulazione nativa del meccanismo prima che SEQ-0014 fosse mai strutturalmente testata.",
            "non_directional_confirmation": "event_direction_policy=NON_DIRECTIONAL (congelato in Phase 7.5C, "
                                             "invariato) - nessun outcome tipo P(+1ATR before -1ATR) riusato.",
        },

        # =================================================================
        # SEZIONE 2 - Baseline estimand contract (BLOCCATO)
        # =================================================================
        "baseline_estimand_contract": {
            "status": "BLOCKED",
            "candidate_estimands": {
                "A_generic_comparable_bar": "EVENT = state-entry; CONTROL = qualunque barra comparabile "
                    "(stesso split, stesso regime di volatilita' pre-evento, fuori dalla finestra di "
                    "esclusione ed episodio dell'evento) A PRESCINDERE dal fatto che sia essa stessa in "
                    "LOW_INFORMATION_STATE. Risponde a: 'il comportamento futuro dopo un ingresso in chop e' "
                    "diverso dal comportamento futuro tipico del mercato IN GENERALE?'",
                "B_non_low_info_comparable_bar": "EVENT = state-entry; CONTROL = barra comparabile CHE NON e' "
                    "essa stessa in LOW_INFORMATION_STATE (in_state[control_row]=False). Risponde a: 'il "
                    "comportamento futuro dopo un ingresso in chop e' diverso dal comportamento futuro dopo "
                    "una barra comparabile ma NON-choppy (es. trending)?' - isola il contributo marginale "
                    "dello STATO stesso, non confuso con barre 'controllo' che sono a loro volta chop.",
            },
            "current_implementation": "La control_pool_construction_policy GIA' congelata in Phase 7.5C "
                "(server/research_scripts/phase7/phase7_5c/seq0014_frozen_structural_spec_v1.json, MAI "
                "modificata da questo script) implementa l'estimand A - esclude solo per finestra temporale "
                "(|r-t|<=natural_horizon) e stesso episode_id, MAI per appartenenza allo stato.",
            "contamination_audit": contamination,
            "scientific_derivation": "L'estimand B e' preferito per la domanda formalizzata in sec.1, con "
                "evidenza dal record PRE-ESISTENTE del progetto (falsification_definition originale di "
                "MECH-23 in market_sequence_registry_v1.json, scritta in Phase 7.2 - PRIMA che SEQ-0014 fosse "
                "mai sottoposta al gate strutturale, quindi non influenzata da alcun outcome di questa fase): "
                "quella definizione contrasta esplicitamente 'choppy' vs 'trending', non 'choppy' vs 'barra "
                "generica'. Un contrasto contro un pool contaminato al ~33% da barre esse stesse choppy "
                "diluirebbe qualunque differenza reale verso zero, indipendentemente dal fatto che un "
                "fenomeno esista - un errore di STIMA, non solo di potenza.",
            "resolution_required": "Una nuova control_pool_construction_policy (control pool filtrato per "
                "in_state[control_row]=False) DEVE essere formalizzata come una NUOVA structural spec "
                "(nuova sequence_family_id o v2 esplicita) e ri-sottoposta al Sequence Structural Feasibility "
                "Gate (nuovo preflight) - il pool piu' piccolo (~67% del pool attuale) potrebbe cambiare "
                "n_matched/match_quality/reuse per alcuni eventi. MAI una modifica silenziosa del "
                "matching_spec dopo il verdetto FEASIBLE gia' raggiunto in Phase 7.5C.",
            "not_resolved_here": "Questo script NON modifica seq0014_frozen_structural_spec_v1.json, NON "
                                 "ricalcola un nuovo preflight, e NON legge alcun outcome per 'capire meglio' "
                                 "quale estimand scegliere - la scelta e' derivata SOLO dalla domanda "
                                 "scientifica e dal record pre-esistente del progetto.",
        },

        # =================================================================
        # SEZIONE 3-5 - Outcome contract (congelato, indipendente da A/B:
        # definisce COSA si misura per ogni barra, non CHI sono i controlli)
        # =================================================================
        "outcome_contract": {
            "note": "Le formule sotto si applicano IDENTICHE sia all'evento sia a qualunque barra di controllo "
                    "(A o B) - la definizione della MISURA non dipende da quale estimand verra' infine "
                    "adottato, solo il CONTRASTO (sec.6) ne dipende.",
            "common_definitions": {
                "horizon_bars": 20,
                "horizon_source": "proposed_natural_horizon, congelato in Phase 7.5C (frozen structural spec) "
                                   "- riusato senza modifica, non un nuovo numero scelto qui.",
                "normalization_atr": "ATR_t (Wilder ATR fino e incluso il bar t, il bar dell'evento/controllo "
                    "stesso) - STESSA convenzione di SEQ-0015 (outcome_atr_normalization: 'gia' interamente "
                    "noto a prediction_start=close(t), nessuna barra futura richiesta'). MAI un ATR "
                    "ricalcolato sulla finestra futura (che sarebbe normalizzare per una quantita' essa "
                    "stessa parte dell'outcome).",
                "censoring": "Finestra fissa [t+1, t+20] - NESSUN early stopping, nessun troncamento "
                             "condizionale sull'osservazione stessa (censoring solo per fine-dataset, gestito "
                             "come dato mancante, mai imputato).",
            },
            "primary_outcome": {
                "id": surface.primary_outcome, "tier": "PRIMARY_OUTCOME",
                "formula": "(max(high[t+1..t+20]) - min(low[t+1..t+20])) / ATR_t",
                "matches_registry_family": "REALIZED_VOLATILITY_AFTER_SETUP (market_sequence_registry_v1.json, "
                                            "expected_outcome_family di MECH-23, dichiarato in Phase 7.2; nome "
                                            "gia' presente in outcome_surface_v3.py:ALL_OUTCOME_DEFINITIONS, "
                                            "riusato senza estendere il vocabolario generale)",
                "hypothesis_direction": "DUE_CODE (non direzionale sul segno dell'effetto - nessuna ragione "
                    "ex-ante per aspettarsi che il chop preceda SOLO espansione o SOLO persistenza di range "
                    "ridotto; entrambe le narrative (compressione-poi-rilascio vs persistenza del regime) sono "
                    "plausibili a priori) - test a due code sul segno di d_i (sec.6).",
                "interpretation": "d_i>0: il regime low-info precede un range realizzato futuro MAGGIORE del "
                                   "baseline matchato (compressione-poi-rilascio). d_i<0: precede un range "
                                   "MINORE (persistenza di quiete/chop).",
            },
            "secondary_outcomes": [
                {"id": surface.secondary_outcomes[0], "tier": "SECONDARY_PREDECLARED_OUTCOMES",
                 "formula": "|close[t+20]-close[t]| / sum(|close.diff()|, barre t+1..t+20) - stessa formula "
                            "Kaufman Efficiency Ratio di directional_efficiency, ma calcolata SU UNA FINESTRA "
                            "STRETTAMENTE FUTURA (t+1..t+20) - nessuna sovrapposizione con le barre usate per "
                            "definire lo stato a t, quindi non circolare.",
                 "matches_registry_family": "Corrisponde concettualmente a EXECUTION_FRIENDLINESS "
                            "(market_sequence_registry_v1.json) - operazionalizzato con PATH_EFFICIENCY, "
                            "nome gia' presente in outcome_surface_v3.py:ALL_OUTCOME_DEFINITIONS.",
                 "rationale": "Testa se il regime choppy si risolve in un movimento piu' o meno 'efficiente'/"
                              "tradeable rispetto al baseline matchato."},
            ],
            "diagnostic_only_outcomes": [],
            "diagnostic_outcomes_considered_but_not_registered": "Misure aggiuntive (tempo-a-espansione con "
                "soglia ATR, escursione assoluta massima) sono state considerate ma NON registrate come "
                "outcome formali: richiederebbero un ulteriore parametro arbitrario (la soglia di espansione) "
                "o sarebbero fortemente ridondanti col primary - omesse per restare al minimo indispensabile "
                "(sec.3 della richiesta), non per mancanza di interesse. Nessuna estensione del vocabolario "
                "generale di outcome_surface_v3.py e' stata necessaria per SEQ-0014.",
            "inferential_family_size_verified_programmatically": surface.inferential_family_size(),
        },

        # =================================================================
        # SEZIONE 6 - Estimand (formula del contrasto, PENDING la risoluzione A/B)
        # =================================================================
        "matched_difference_contract": {
            "formula": "d_i = outcome_i(event_i) - mean(outcome_i(matched_controls_i))",
            "units": "Stesse unita' del rispettivo outcome (multipli di ATR_t, adimensionali).",
            "sign_convention": "d_i>0 significa 'piu' del quanto misurato dopo l'evento rispetto al baseline "
                                "matchato'; d_i<0 il contrario. Nessuna direzione BUY/SELL implicita.",
            "control_set_used_in_mean": "PENDING - dipende dalla risoluzione dell'estimand A/B (sec.2, "
                                         "BLOCKED). La FORMULA del contrasto e' la stessa in entrambi i casi - "
                                         "cambia solo l'insieme di controlli su cui si calcola la media.",
        },

        # =================================================================
        # SEZIONE 7-8 - Inference & dependence contract (congelato, generale)
        # =================================================================
        "inference_contract": {
            "candidate_primary_method": "block_sign_flip_permutation_matched_pair",
            "candidate_method_source": "server/research_scripts/phase7/engine/ - stessa infrastruttura generale "
                "gia' calibrata in Phase 7.4A (null_calibration_simulation.py, AR(1) sintetico phi=0.0-0.7) - "
                "NON reinventata qui, NON un nuovo metodo non calibrato.",
            "applicability_to_non_directional_continuous_outcome": "Il test e' un test di simmetria sul segno "
                "di d_i sotto H0 - si applica IDENTICO a qualunque outcome continuo accoppiato (range/"
                "displacement/efficiency ATR-normalizzati), non assume che l'outcome sotto test sia un "
                "rendimento direzionale con segno BUY/SELL. Nessuna modifica al metodo necessaria per "
                "l'applicazione NON_DIRECTIONAL di SEQ-0014.",
            "validation_status": "PRIMARY_INFERENCE_METHOD_NOT_YET_VALIDATED",
            "validation_status_rationale": "STESSA classificazione onesta gia' usata per SEQ-0015 (mai "
                "'validato' significa 'mai applicato+verificato end-to-end su una discovery run reale di "
                "QUESTA family specifica', non 'privo di qualunque calibrazione' - la calibrazione sintetica "
                "generale (dependence_validity_gate) resta valida e riusabile, ma non e' stata ancora "
                "esercitata su un dataset reale con questo estimand/estimator specifico). Nessun metodo "
                "alternativo non calibrato e' stato inventato per aggirare questo stato.",
            "dependence_gate_reused": {
                "module": "server/research_scripts/phase7/engine/dependence_validity_gate.py - riusato SENZA "
                          "modifiche.",
                "diagnostics_frozen_ex_ante": ["acf_lag1", "ljung_box_h3", "ess_ratio", "sample_skewness"],
                "frozen_thresholds_reused_unchanged": {"acf_lag1_sensitive": 0.2, "acf_lag1_invalid": 0.45,
                                                        "ljung_box_p_sensitive": 0.1, "ljung_box_p_invalid": 0.01,
                                                        "ess_ratio_sensitive": 0.7, "ess_ratio_invalid": 0.4},
                "granularity": "1 candidato (NON_DIRECTIONAL, nessuno split BUY/SELL/BOTH) x 2 outcome "
                               "inferenziali (primary+1 secondary) = 2 celle, ciascuna classificata "
                               "indipendentemente INFERENCE_VALID/DEPENDENCE_SENSITIVE/INFERENCE_INVALID_"
                               "DEPENDENCE PRIMA di entrare in BH-FDR - stessa policy fail-closed di SEQ-0015.",
            },
            "control_reuse_and_temporal_ordering_checks": "reuse_report gia' calcolato nel preflight strutturale "
                "(Phase 7.5C: max_reuse_observed=1, ben sotto il tetto=5) - riverificato meccanicamente ad "
                "ogni futura esecuzione di discovery, mai assunto invariato.",
            "no_uncalibrated_method_applied": True,
        },

        # =================================================================
        # SEZIONE 9 - Multiplicity contract
        # =================================================================
        "multiplicity_contract": {
            "inferential_family_id": "SEQFAM-SEQ0014-LOWINFO-FULL-COMPARISON-FAMILY-V1",
            "family_members": "1 candidato (NON_DIRECTIONAL, nessuno split direzionale) x 2 outcome "
                               "inferenziali (1 primary + 1 secondary) = 2 confronti.",
            "n_comparisons": 2,
            "method": "Benjamini-Hochberg FDR, q=0.10 (server/research_scripts/phase7/engine/"
                       "multiple_testing_v2.py:benjamini_hochberg, riusato senza modifiche - stessa q "
                       "gia' usata per SEQ-0015).",
            "diagnostic_exclusion": "Nessun outcome DIAGNOSTIC_ONLY registrato in questa formalizzazione minimale "
                                     "(verificato programmaticamente da OutcomeSurfaceV3.inferential_"
                                     "family_size()==2).",
            "no_family_inflation": "Famiglia deliberatamente minima (nessuno split BUY/SELL essendo "
                                    "NON_DIRECTIONAL, solo 2 outcome non-diagnostic) - non gonfiata "
                                    "artificialmente rispetto a SEQ-0015 (21 membri, 3 candidati x 7 outcome).",
        },

        # =================================================================
        # SEZIONE 10 - Effect size first
        # =================================================================
        "effect_size_contract": {
            "primacy_rule": "Il risultato di ogni outcome deve riportare SEMPRE, prima di qualunque p-value: "
                             "effect estimate (d_i medio o mediano), intervallo di incertezza (dal metodo di "
                             "inferenza scelto), e confronto con la soglia di materialita' sotto.",
            "minimum_material_effect_size": {
                "value": 0.10,
                "definition": "|mean(outcome su eventi) - mean(outcome su controlli matchati)| / "
                               "mean(outcome su controlli matchati) >= 0.10 (differenza RELATIVA minima "
                               "del 10%).",
                "rationale": "STESSA soglia numerica e STESSA motivazione filosofica gia' congelata in "
                             "minimum_evidence_gates.json (minimum_material_delta_p_default=0.10 - 'floor per "
                             "impedire che un effetto trascurabile venga chiamato materiale solo perche' "
                             "statisticamente distinguibile da zero su un campione grande') - qui riespressa "
                             "come differenza RELATIVA (non assoluta in punti di probabilita', dato che "
                             "l'outcome e' un rapporto ATR-normalizzato continuo, non una proporzione). Non "
                             "un nuovo numero scelto ad-hoc per SEQ-0014.",
            },
            "no_bare_p_value_verdict": "Nessun verdetto di discovery sara' basato SOLO su p<0.05 senza "
                                        "riportare congiuntamente effect size e soglia di materialita'.",
        },

        # =================================================================
        # SEZIONE 11-12 - Accesso ai dati e cronologia dei commit
        # =================================================================
        "data_access_policy": {
            "authorized_for_future_discovery_run": ["development_discovery"],
            "locked_until_separately_authorized": ["development_internal_validation", "locked_validation",
                                                    "final_holdout"],
            "enforcement_reference": "server/research_scripts/phase7/engine/validation_access_ledger.py "
                                      "(gia' esistente, riusato senza modifica).",
        },
        "commit_chronology": {
            "this_commit": "PREREGISTRATION COMMIT - SOLO contratto, nessun outcome calcolato.",
            "next_step_not_taken_here": "outcome computation / discovery - richiede risoluzione del blocco "
                                        "sec.2 (nuova structural spec + preflight) PRIMA di procedere, poi "
                                        "un commit separato.",
            "future_step_after_that": "RESULT COMMIT (solo dopo discovery, mai combinato con la "
                                       "preregistrazione).",
        },

        "no_nexus_outcome_data_accessed": True,
        "no_edge_discovery_performed": True,
        "no_internal_validation_locked_or_final_holdout_opened": True,
        "seq0015_status_unchanged": "CLOSED_NOT_REEXAMINED_AS_CANDIDATE",
        "seq0009_status_unchanged": "CLOSED_NOT_REEXAMINED_AS_CANDIDATE",
    }

    out_path = os.path.join(PHASE76A_DIR, "seq0014_statistical_preregistration_v1.json")
    save_json(out_path, wrap_with_provenance(payload, "phase7/phase7_6a/build_seq0014_statistical_preregistration.py"))
    print(f"Scritto {out_path}")
    print(f"preregistration_status={payload['preregistration_status']}")
    print(f"discovery_authorized={payload['discovery_authorized']}")
    print(f"contamination audit: {contamination['fraction_of_current_eligible_control_pool_also_in_state']:.3f} "
          f"(base rate: {contamination['overall_base_rate_of_in_state_across_discovery']:.3f})")


if __name__ == "__main__":
    main()
