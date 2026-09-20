#!/usr/bin/env python3
"""Phase 7.4A Integrity Patch sec.2 - costruisce e valida
seq0015_statistical_test_contract_v1.json: per OGNI outcome
inferenziale (1 primary + 6 secondary) dichiara variable_type,
estimand, statistiche, uncertainty_method, hypothesis_test,
p_value_method, dependence_adjustment, missing/censored_handling.
NON esegue alcun test su dati reali - assembla solo il contratto e lo
valida strutturalmente."""
import json
import os

PHASE74_DIR = os.path.dirname(os.path.abspath(__file__))

BINARY_UNCERTAINTY = "WILSON_CI95 (primario) + MOVING_BLOCK_BOOTSTRAP_CI come diagnostica di robustezza SOLO se il candidato risulta DEPENDENCE_SENSITIVE"
BINARY_TEST = "two_proportion_z_test"
BINARY_PVALUE = "multiple_testing_v2.two_proportion_p (z-test su proporzioni pooled, gia' in uso da Phase 5.5) - alimenta BH-FDR"
BINARY_DEPENDENCE = ("Se il segno di Delta_P differisce fra EPISODE_VIEW e INDEPENDENT_VIEW (sequence_episode_engine."
                      "build_outcome_independent_view, embargo=natural_horizon-1=39), oppure l'ESS stimato da "
                      "moving_block_bootstrap_ci sulla INDEPENDENT_VIEW < effective_n_minimum=20 mentre "
                      "n_nominal(INDEPENDENT_VIEW)>=30: DEPENDENCE_SENSITIVE=true, riportato MOVING_BLOCK_BOOTSTRAP_CI "
                      "come diagnostica aggiuntiva - mai come sostituto del p-value primario.")
BINARY_MISSING = ("Riuso della convenzione atr_outcome_for_bar (Phase 5/edge_discovery.py): finestra troncata da fine "
                   "split/dataset -> osservazione esclusa (None, mai contata); ne' +targetATR ne' -1ATR raggiunti entro "
                   "l'orizzonte (40 barre) -> CENSORED, escluso da vinte/perse ma tallied separatamente (wl_censored).")

CONTINUOUS_UNCERTAINTY = ("MOVING_BLOCK_BOOTSTRAP_CI (L=ceil(n^(1/3)), phase6_5/block_bootstrap.py, riusato senza "
                           "modifiche) sulla serie evento (INDEPENDENT_VIEW); bootstrap i.i.d. sul pool di baseline "
                           "(stesso limite dichiarato in block_bootstrap.py) - Wilson NON applicabile (variabile "
                           "continua, non una proporzione).")
CONTINUOUS_TEST = "two_sample_block_bootstrap_percentile_p"
CONTINUOUS_PVALUE = ("engine/two_sample_bootstrap_test.py:two_sample_block_bootstrap_percentile_p - p=2*min(P(Delta_E_"
                      "boot<=0),P(Delta_E_boot>=0)) troncato a 1.0, n_boot=2000 - alimenta BH-FDR (estensione esplicita "
                      "di statistical_methods_policy.json, sec.2).")
CONTINUOUS_DEPENDENCE = ("Il block bootstrap sulla INDEPENDENT_VIEW e' esso stesso l'aggiustamento per dipendenza - "
                          "a differenza del caso binario non esiste qui un metodo 'naive' primario da correggere con "
                          "una diagnostica separata: e' l'UNICO metodo usato, dichiarato ORA prima di vedere risultati.")
CONTINUOUS_MISSING = ("Osservazione esclusa (None) se la finestra e' troncata da fine split/dataset; la statistica "
                       "continua e' calcolata su qualunque numero di barre disponibili fino a min(t+40, fine_split) "
                       "indipendentemente dall'esito CENSORED/TARGET_FIRST/STOP_FIRST del corrispondente outcome "
                       "binario (stessa convenzione H006/Phase5: mfe_ATR/mae_ATR calcolati anche per righe CENSORED).")

CONTRACT_ENTRIES = [
    {
        "outcome_id": "P_PLUS_1ATR_BEFORE_MINUS_1ATR", "tier": "PRIMARY_OUTCOME", "variable_type": "BINARY",
        "estimand": "Delta_P = P(TARGET_FIRST=+1ATR | evento, INDEPENDENT_VIEW) - P(TARGET_FIRST=+1ATR | baseline matched)",
        "event_statistic": "proporzione di TARGET_FIRST fra le osservazioni evento nella INDEPENDENT_VIEW",
        "baseline_statistic": "proporzione di TARGET_FIRST fra i controlli matched (Baseline Engine v4, stesso split, stessa direzione)",
        "effect_definition": "Delta_P = event_statistic - baseline_statistic",
        "uncertainty_method": BINARY_UNCERTAINTY, "hypothesis_test": BINARY_TEST, "p_value_method": BINARY_PVALUE,
        "dependence_adjustment": BINARY_DEPENDENCE, "missing_censored_handling": BINARY_MISSING,
    },
    {
        "outcome_id": "P_PLUS_0_5ATR_BEFORE_MINUS_1ATR", "tier": "SECONDARY_PREDECLARED_OUTCOMES", "variable_type": "BINARY",
        "estimand": "Delta_P = P(TARGET_FIRST=+0.5ATR | evento, INDEPENDENT_VIEW) - P(TARGET_FIRST=+0.5ATR | baseline matched)",
        "event_statistic": "proporzione di TARGET_FIRST fra le osservazioni evento nella INDEPENDENT_VIEW",
        "baseline_statistic": "proporzione di TARGET_FIRST fra i controlli matched",
        "effect_definition": "Delta_P = event_statistic - baseline_statistic",
        "uncertainty_method": BINARY_UNCERTAINTY, "hypothesis_test": BINARY_TEST, "p_value_method": BINARY_PVALUE,
        "dependence_adjustment": BINARY_DEPENDENCE, "missing_censored_handling": BINARY_MISSING,
    },
    {
        "outcome_id": "P_PLUS_1_5ATR_BEFORE_MINUS_1ATR", "tier": "SECONDARY_PREDECLARED_OUTCOMES", "variable_type": "BINARY",
        "estimand": "Delta_P = P(TARGET_FIRST=+1.5ATR | evento, INDEPENDENT_VIEW) - P(TARGET_FIRST=+1.5ATR | baseline matched)",
        "event_statistic": "proporzione di TARGET_FIRST fra le osservazioni evento nella INDEPENDENT_VIEW",
        "baseline_statistic": "proporzione di TARGET_FIRST fra i controlli matched",
        "effect_definition": "Delta_P = event_statistic - baseline_statistic",
        "uncertainty_method": BINARY_UNCERTAINTY, "hypothesis_test": BINARY_TEST, "p_value_method": BINARY_PVALUE,
        "dependence_adjustment": BINARY_DEPENDENCE, "missing_censored_handling": BINARY_MISSING,
    },
    {
        "outcome_id": "MFE", "tier": "SECONDARY_PREDECLARED_OUTCOMES", "variable_type": "CONTINUOUS",
        "estimand": "Delta_E = mean(MFE_ATR | evento, INDEPENDENT_VIEW) - mean(MFE_ATR | baseline matched)",
        "event_statistic": "media campionaria di MFE_ATR sulle osservazioni evento della INDEPENDENT_VIEW",
        "baseline_statistic": "media campionaria di MFE_ATR sui controlli matched",
        "effect_definition": "Delta_E = event_statistic - baseline_statistic",
        "uncertainty_method": CONTINUOUS_UNCERTAINTY, "hypothesis_test": CONTINUOUS_TEST, "p_value_method": CONTINUOUS_PVALUE,
        "dependence_adjustment": CONTINUOUS_DEPENDENCE, "missing_censored_handling": CONTINUOUS_MISSING,
    },
    {
        "outcome_id": "MAE", "tier": "SECONDARY_PREDECLARED_OUTCOMES", "variable_type": "CONTINUOUS",
        "estimand": "Delta_E = mean(MAE_ATR | evento, INDEPENDENT_VIEW) - mean(MAE_ATR | baseline matched)",
        "event_statistic": "media campionaria di MAE_ATR sulle osservazioni evento della INDEPENDENT_VIEW",
        "baseline_statistic": "media campionaria di MAE_ATR sui controlli matched",
        "effect_definition": "Delta_E = event_statistic - baseline_statistic",
        "uncertainty_method": CONTINUOUS_UNCERTAINTY, "hypothesis_test": CONTINUOUS_TEST, "p_value_method": CONTINUOUS_PVALUE,
        "dependence_adjustment": CONTINUOUS_DEPENDENCE, "missing_censored_handling": CONTINUOUS_MISSING,
    },
    {
        "outcome_id": "TIME_TO_MFE", "tier": "SECONDARY_PREDECLARED_OUTCOMES", "variable_type": "CONTINUOUS",
        "estimand": "Delta_E = mean(barre fino al MFE | evento, INDEPENDENT_VIEW) - mean(barre fino al MFE | baseline matched)",
        "event_statistic": "media campionaria del numero di barre fino al MFE sulle osservazioni evento della INDEPENDENT_VIEW",
        "baseline_statistic": "media campionaria del numero di barre fino al MFE sui controlli matched",
        "effect_definition": "Delta_E = event_statistic - baseline_statistic",
        "uncertainty_method": CONTINUOUS_UNCERTAINTY, "hypothesis_test": CONTINUOUS_TEST, "p_value_method": CONTINUOUS_PVALUE,
        "dependence_adjustment": CONTINUOUS_DEPENDENCE,
        "missing_censored_handling": CONTINUOUS_MISSING + " TIME_TO_MFE e' sempre definito quando la finestra non e' troncata (esiste sempre un massimo, anche piccolo).",
    },
    {
        "outcome_id": "PATH_EFFICIENCY", "tier": "SECONDARY_PREDECLARED_OUTCOMES", "variable_type": "CONTINUOUS",
        "estimand": "Delta_E = mean(path_efficiency | evento, INDEPENDENT_VIEW) - mean(path_efficiency | baseline matched)",
        "event_statistic": "media campionaria di |close_end-close_prediction_start|/sum(|close_i-close_i-1|) sulle osservazioni evento della INDEPENDENT_VIEW",
        "baseline_statistic": "stessa statistica sui controlli matched",
        "effect_definition": "Delta_E = event_statistic - baseline_statistic",
        "uncertainty_method": CONTINUOUS_UNCERTAINTY, "hypothesis_test": CONTINUOUS_TEST, "p_value_method": CONTINUOUS_PVALUE,
        "dependence_adjustment": CONTINUOUS_DEPENDENCE, "missing_censored_handling": CONTINUOUS_MISSING,
    },
]

DIAGNOSTIC_ONLY_OUTCOMES = [
    "P_PLUS_0_25ATR_BEFORE_MINUS_1ATR", "P_PLUS_2ATR_BEFORE_MINUS_1ATR", "TIME_TO_TARGET",
    "CONTINUATION_PROBABILITY", "REVERSAL_PROBABILITY", "REALIZED_VOLATILITY_AFTER_SETUP",
]


class InvalidUncertaintyMethodError(Exception):
    pass


def assert_uncertainty_method_valid_for_variable_type(entry: dict):
    """Phase 7.4A sec.6 test 'Wilson rejected for continuous outcome' -
    Wilson CI95 e' valido SOLO per variable_type=BINARY; un metodo
    bootstrap-only e' richiesto per CONTINUOUS."""
    vt = entry["variable_type"]
    um = entry["uncertainty_method"]
    if vt == "CONTINUOUS" and "WILSON" in um.split("(")[0].upper() and "BOOTSTRAP" not in um.upper():
        raise InvalidUncertaintyMethodError(
            f"outcome_id={entry['outcome_id']}: variable_type=CONTINUOUS non puo' usare WILSON_CI95 - "
            f"non e' una proporzione, serve un metodo bootstrap."
        )
    if vt == "BINARY" and "WILSON" not in um.upper() and "BETA_BINOMIAL" not in um.upper():
        raise InvalidUncertaintyMethodError(
            f"outcome_id={entry['outcome_id']}: variable_type=BINARY dovrebbe usare WILSON_CI95 o BETA_BINOMIAL "
            f"come metodo primario, non solo bootstrap."
        )
    return True


def build_contract():
    for entry in CONTRACT_ENTRIES:
        assert_uncertainty_method_valid_for_variable_type(entry)  # fail-fast se qualcosa e' inconsistente
    n_with_pvalue_method = sum(1 for e in CONTRACT_ENTRIES if e.get("p_value_method"))
    return {
        "contract_id": "SEQ0015_STATISTICAL_TEST_CONTRACT_V1",
        "sequence_family_id": "SEQFAM-SEQ0015_MOMENTUM_BURST_CONTINUATION_V1",
        "principle": "Ogni outcome inferenziale (primary+secondary) DEVE avere un metodo di incertezza e un p-value predefiniti PRIMA della run - nessun test scelto dopo aver visto le distribuzioni reali. Gli outcome DIAGNOSTIC_ONLY non hanno un contratto qui per costruzione (sec.3: mai promossi a evidenza nella stessa run).",
        "independent_view_definition": (
            "Tutte le statistiche event_statistic sono calcolate sulla INDEPENDENT_VIEW "
            "(sequence_episode_engine.build_outcome_independent_view, embargo=natural_horizon-1=39 barre), "
            "MAI su EVENT_VIEW ne' su EPISODE_VIEW direttamente - vedi Phase 7.4A Integrity Patch sec.1."
        ),
        "entries": CONTRACT_ENTRIES,
        "diagnostic_only_outcomes_excluded": DIAGNOSTIC_ONLY_OUTCOMES,
        "n_inferential_outcomes_with_frozen_pvalue_method": n_with_pvalue_method,
        "n_candidates": 3,
        "fdr_family_size_check": {
            "n_candidates": 3, "n_outcomes_with_pvalue_method": n_with_pvalue_method,
            "declared_family_size": 3 * n_with_pvalue_method,
            "rule": "family_size = n_candidates x n_outcomes_with_pvalue_method - se un outcome non avesse un p_value_method dichiarato qui, dovrebbe essere spostato a DIAGNOSTIC_ONLY e rimosso da questo contratto PRIMA della run (sec.3).",
        },
    }


def main():
    contract = build_contract()
    assert contract["n_inferential_outcomes_with_frozen_pvalue_method"] == 7, "attesi 7/7 outcome con metodo p-value congelato (nessuna demotion necessaria)"
    assert contract["fdr_family_size_check"]["declared_family_size"] == 21
    out_path = os.path.join(PHASE74_DIR, "seq0015_statistical_test_contract_v1.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(contract, f, indent=2, ensure_ascii=False)
    print(f"n_inferential_outcomes_with_frozen_pvalue_method = {contract['n_inferential_outcomes_with_frozen_pvalue_method']}/7")
    print(f"fdr_family_size = {contract['fdr_family_size_check']['declared_family_size']}")
    print(f"Scritto: {out_path}")
    return True


if __name__ == "__main__":
    main()
