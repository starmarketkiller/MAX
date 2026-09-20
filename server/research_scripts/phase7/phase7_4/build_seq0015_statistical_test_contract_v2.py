#!/usr/bin/env python3
"""Phase 7.4A Final Statistical Integrity Patch sec.6-7 - contratto
statistico v2: metodo UNIFICATO (block_sign_flip_permutation_matched_pair)
per tutti i 7 outcome inferenziali (3 binari + 4 continui), sostituendo
sia WILSON_CI95+two_proportion_z_test (binari) sia
two_sample_block_bootstrap_percentile_p (continui) del v1 - entrambi
appiattivano la struttura matched o non imponevano H0 esplicitamente
(vedi audit sec.1/sec.6). supersedes: seq0015_statistical_test_contract_v1.json."""
import json
import os

PHASE74_DIR = os.path.dirname(os.path.abspath(__file__))

METHOD_DESC = "block_sign_flip_permutation_matched_pair (engine/matched_pair_permutation_test.py)"
UNCERTAINTY = "BLOCK_SIGN_FLIP_PERMUTATION (impone esplicitamente H0:E[d]=0 - vedi statistical_methods_policy.json)"
HYPOTHESIS_TEST = "block_sign_flip_permutation (test di permutazione a blocchi su differenze accoppiate)"
PVALUE_METHOD = ("engine/matched_pair_permutation_test.py:block_sign_flip_permutation_p su d_i - "
                  "p=(1+#{|T_boot|>=|T_obs|})/(n_boot+1), n_boot=2000 - alimenta BH-FDR.")
DEPENDENCE_ADJUSTMENT = (
    "Il block sign-flip (L=ceil(n^(1/3)) su blocchi contigui di d_i in ordine temporale) e' esso stesso "
    "l'aggiustamento per dipendenza seriale residua fra osservazioni INDEPENDENT_VIEW gia' embargate. "
    "Calibrazione verificata per simulazione (phase7_4_null_calibration_v1.json): ben calibrato per "
    "gaussian/skewed/pochi-controlli-rumorosi e per il caso dimostrativo di shock di regime condiviso; "
    "sotto autocorrelazione FORTE (AR(1) phi>=0.5-0.7) fra osservazioni gia' embargate resta "
    "anti-conservativo (~2-4x il nominale) - limite di risoluzione noto dei test di permutazione a blocchi "
    "con n piccolo, non risolvibile aumentando la block length (che collassa la risoluzione del test - "
    "verificato empiricamente). Mitigato dal gate DEPENDENCE_SENSITIVE esistente (obbligatorio prima di "
    "qualunque promozione oltre INTERNAL_VALIDATION)."
)
MISSING_HANDLING_BASE = (
    "d_i richiede sia outcome(event_i) sia almeno 1 controllo matched valido - un evento senza controlli "
    "matched validi (REJECTED_INSUFFICIENT_POOL o pool filtrato a zero da ControlReuseLedger) e' escluso "
    "dalla serie d_i, mai imputato. Finestra troncata da fine split/dataset -> outcome(event_i) non "
    "calcolabile -> stessa esclusione."
)

CONTRACT_ENTRIES_V2 = [
    {
        "outcome_id": "P_PLUS_1ATR_BEFORE_MINUS_1ATR", "tier": "PRIMARY_OUTCOME", "variable_type": "BINARY",
        "estimand": "mean(d_i), d_i = outcome_binario(event_i) - mean(outcome_binario(matched_controls_i)) sulla INDEPENDENT_VIEW",
        "event_statistic": "outcome_binario(event_i) in {0,1} (TARGET_FIRST=+1ATR=1, STOP_FIRST=0; CENSORED escluso da QUELLA specifica osservazione d_i)",
        "baseline_statistic": "media degli outcome binari 0/1 dei k controlli matched a QUELL'evento specifico (mai un pool condiviso)",
        "effect_definition": "mean(d_i) su tutte le osservazioni indipendenti con almeno 1 controllo valido",
        "uncertainty_method": UNCERTAINTY, "hypothesis_test": HYPOTHESIS_TEST, "p_value_method": PVALUE_METHOD,
        "dependence_adjustment": DEPENDENCE_ADJUSTMENT,
        "missing_censored_handling": MISSING_HANDLING_BASE + " CENSORED (ne' +1ATR ne' -1ATR entro 40 barre) su event_i o su un controllo -> quella singola osservazione (event o quel controllo) esclusa dal calcolo di d_i corrispondente, non l'intera osservazione indipendente se altri controlli restano validi.",
        "independent_two_sample_assumption_valid": False,
        "independent_two_sample_assumption_note": "NON valida (sec.6): evento e controlli matched non sono campioni indipendenti per costruzione (i controlli sono scelti proprio perche' nello stesso stato di mercato dell'evento) - sostituito two_proportion_z_test con il test matched-pair sopra.",
    },
    {
        "outcome_id": "P_PLUS_0_5ATR_BEFORE_MINUS_1ATR", "tier": "SECONDARY_PREDECLARED_OUTCOMES", "variable_type": "BINARY",
        "estimand": "mean(d_i), d_i = outcome_binario(event_i) - mean(outcome_binario(matched_controls_i)) sulla INDEPENDENT_VIEW",
        "event_statistic": "outcome_binario(event_i) in {0,1} per soglia +0.5ATR",
        "baseline_statistic": "media degli outcome binari 0/1 dei k controlli matched a QUELL'evento specifico",
        "effect_definition": "mean(d_i)",
        "uncertainty_method": UNCERTAINTY, "hypothesis_test": HYPOTHESIS_TEST, "p_value_method": PVALUE_METHOD,
        "dependence_adjustment": DEPENDENCE_ADJUSTMENT, "missing_censored_handling": MISSING_HANDLING_BASE,
        "independent_two_sample_assumption_valid": False,
        "independent_two_sample_assumption_note": "NON valida (sec.6) - stesso motivo del primary.",
    },
    {
        "outcome_id": "P_PLUS_1_5ATR_BEFORE_MINUS_1ATR", "tier": "SECONDARY_PREDECLARED_OUTCOMES", "variable_type": "BINARY",
        "estimand": "mean(d_i), d_i = outcome_binario(event_i) - mean(outcome_binario(matched_controls_i)) sulla INDEPENDENT_VIEW",
        "event_statistic": "outcome_binario(event_i) in {0,1} per soglia +1.5ATR",
        "baseline_statistic": "media degli outcome binari 0/1 dei k controlli matched a QUELL'evento specifico",
        "effect_definition": "mean(d_i)",
        "uncertainty_method": UNCERTAINTY, "hypothesis_test": HYPOTHESIS_TEST, "p_value_method": PVALUE_METHOD,
        "dependence_adjustment": DEPENDENCE_ADJUSTMENT, "missing_censored_handling": MISSING_HANDLING_BASE,
        "independent_two_sample_assumption_valid": False,
        "independent_two_sample_assumption_note": "NON valida (sec.6) - stesso motivo del primary.",
    },
    {
        "outcome_id": "MFE", "tier": "SECONDARY_PREDECLARED_OUTCOMES", "variable_type": "CONTINUOUS",
        "estimand": "mean(d_i), d_i = MFE_ATR(event_i) - mean(MFE_ATR(matched_controls_i)) sulla INDEPENDENT_VIEW",
        "event_statistic": "MFE_ATR(event_i)", "baseline_statistic": "media di MFE_ATR sui k controlli matched a QUELL'evento specifico",
        "effect_definition": "mean(d_i)",
        "uncertainty_method": UNCERTAINTY, "hypothesis_test": HYPOTHESIS_TEST, "p_value_method": PVALUE_METHOD,
        "dependence_adjustment": DEPENDENCE_ADJUSTMENT, "missing_censored_handling": MISSING_HANDLING_BASE,
        "independent_two_sample_assumption_valid": False, "independent_two_sample_assumption_note": "N/A gia' trattato come matched dal v1 - confermato invariato.",
    },
    {
        "outcome_id": "MAE", "tier": "SECONDARY_PREDECLARED_OUTCOMES", "variable_type": "CONTINUOUS",
        "estimand": "mean(d_i), d_i = MAE_ATR(event_i) - mean(MAE_ATR(matched_controls_i)) sulla INDEPENDENT_VIEW",
        "event_statistic": "MAE_ATR(event_i)", "baseline_statistic": "media di MAE_ATR sui k controlli matched a QUELL'evento specifico",
        "effect_definition": "mean(d_i)",
        "uncertainty_method": UNCERTAINTY, "hypothesis_test": HYPOTHESIS_TEST, "p_value_method": PVALUE_METHOD,
        "dependence_adjustment": DEPENDENCE_ADJUSTMENT, "missing_censored_handling": MISSING_HANDLING_BASE,
        "independent_two_sample_assumption_valid": False, "independent_two_sample_assumption_note": "N/A gia' trattato come matched dal v1 - confermato invariato.",
    },
    {
        "outcome_id": "TIME_TO_MFE", "tier": "SECONDARY_PREDECLARED_OUTCOMES", "variable_type": "CONTINUOUS",
        "estimand": "mean(d_i), d_i = barre_fino_a_MFE(event_i) - mean(barre_fino_a_MFE(matched_controls_i)) sulla INDEPENDENT_VIEW",
        "event_statistic": "barre fino al MFE di event_i", "baseline_statistic": "media delle barre fino al MFE sui k controlli matched a QUELL'evento specifico",
        "effect_definition": "mean(d_i)",
        "uncertainty_method": UNCERTAINTY, "hypothesis_test": HYPOTHESIS_TEST, "p_value_method": PVALUE_METHOD,
        "dependence_adjustment": DEPENDENCE_ADJUSTMENT, "missing_censored_handling": MISSING_HANDLING_BASE,
        "independent_two_sample_assumption_valid": False, "independent_two_sample_assumption_note": "N/A gia' trattato come matched dal v1 - confermato invariato.",
    },
    {
        "outcome_id": "PATH_EFFICIENCY", "tier": "SECONDARY_PREDECLARED_OUTCOMES", "variable_type": "CONTINUOUS",
        "estimand": "mean(d_i), d_i = path_efficiency(event_i) - mean(path_efficiency(matched_controls_i)) sulla INDEPENDENT_VIEW",
        "event_statistic": "path_efficiency(event_i)", "baseline_statistic": "media di path_efficiency sui k controlli matched a QUELL'evento specifico",
        "effect_definition": "mean(d_i)",
        "uncertainty_method": UNCERTAINTY, "hypothesis_test": HYPOTHESIS_TEST, "p_value_method": PVALUE_METHOD,
        "dependence_adjustment": DEPENDENCE_ADJUSTMENT, "missing_censored_handling": MISSING_HANDLING_BASE,
        "independent_two_sample_assumption_valid": False, "independent_two_sample_assumption_note": "N/A gia' trattato come matched dal v1 - confermato invariato.",
    },
]

DIAGNOSTIC_ONLY_OUTCOMES = [
    "P_PLUS_0_25ATR_BEFORE_MINUS_1ATR", "P_PLUS_2ATR_BEFORE_MINUS_1ATR", "TIME_TO_TARGET",
    "CONTINUATION_PROBABILITY", "REVERSAL_PROBABILITY", "REALIZED_VOLATILITY_AFTER_SETUP",
]


def build_contract_v2():
    n_with_pvalue = sum(1 for e in CONTRACT_ENTRIES_V2 if e.get("p_value_method"))
    return {
        "contract_id": "SEQ0015_STATISTICAL_TEST_CONTRACT_V2",
        "supersedes": "seq0015_statistical_test_contract_v1.json",
        "supersession_reason": (
            "Phase 7.4A Final Statistical Integrity Patch (2026-09-20): audit formale + null-calibration "
            "simulation hanno mostrato che (a) two_sample_block_bootstrap_percentile_p (metodo v1 per i 4 "
            "outcome continui) e' anti-conservativo sotto H0 vera in tutti gli scenari testati; (b) sia "
            "quel metodo sia two_proportion_z_test (v1, outcome binari) appiattiscono la struttura matched "
            "(un pool evento/baseline condiviso invece della differenza per-evento rispetto ai propri "
            "controlli k-NN). Sostituiti entrambi da un unico metodo validato: block_sign_flip_permutation_"
            "matched_pair, applicato uniformemente a TUTTI i 7 outcome inferenziali."
        ),
        "sequence_family_id": "SEQFAM-SEQ0015_MOMENTUM_BURST_CONTINUATION_V1",
        "principle": "Ogni outcome inferenziale ha ORA lo stesso metodo validato per simulazione, che preserva la struttura matched per costruzione (d_i per-evento, mai un pool appiattito).",
        "independent_view_definition": "Tutte le statistiche sono calcolate sulla INDEPENDENT_VIEW (embargo=39 barre) - invariato dal v1.",
        "entries": CONTRACT_ENTRIES_V2,
        "diagnostic_only_outcomes_excluded": DIAGNOSTIC_ONLY_OUTCOMES,
        "n_inferential_outcomes_with_frozen_pvalue_method": n_with_pvalue,
        "n_candidates": 3,
        "fdr_family_size_check": {
            "n_candidates": 3, "n_outcomes_with_pvalue_method": n_with_pvalue,
            "declared_family_size": 3 * n_with_pvalue,
            "rule": "family_size = n_candidates x n_outcomes_with_pvalue_method - nessun outcome spostato a DIAGNOSTIC_ONLY: tutti e 7 hanno un metodo validato dalla stessa simulazione di calibrazione (sec.7).",
        },
        "null_calibration_reference": "server/research_scripts/phase7/phase7_4/phase7_4_null_calibration_v1.json",
    }


def main():
    contract = build_contract_v2()
    assert contract["n_inferential_outcomes_with_frozen_pvalue_method"] == 7
    assert contract["fdr_family_size_check"]["declared_family_size"] == 21
    out_path = os.path.join(PHASE74_DIR, "seq0015_statistical_test_contract_v2.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(contract, f, indent=2, ensure_ascii=False)
    print(f"n_inferential_outcomes_with_frozen_pvalue_method = {contract['n_inferential_outcomes_with_frozen_pvalue_method']}/7")
    print(f"fdr_family_size = {contract['fdr_family_size_check']['declared_family_size']}")
    print(f"Scritto: {out_path}")
    return True


if __name__ == "__main__":
    main()
