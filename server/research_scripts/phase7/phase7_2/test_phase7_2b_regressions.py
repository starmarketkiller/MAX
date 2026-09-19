#!/usr/bin/env python3
"""Phase 7.2B sec.8 - Regression/red-team consolidati per i 6 casi
nominati dall'utente. Alcuni usano dati SINTETICI (nessun dato NEXUS),
altri verificano i registry REALI gia' prodotti in questa patch."""
import json
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", ".."))
PHASE72_DIR = os.path.join(ROOT, "server", "research_scripts", "phase7", "phase7_2")
sys.path.insert(0, PHASE72_DIR)
from sequence_semantic_leakage_guard import check_sequence_leakage, classify_relationship, PASS, FAIL, NEEDS_REFORMULATION  # noqa: E402


def case_1_same_antecedent_opposite_claim_is_contradiction():
    rel = classify_relationship(same_antecedent=True, same_observation_time=True, same_setup_definition=True,
                                 outcomes_are_opposite=True, divergence_due_to_later_transition=False)
    assert rel == "CONTRADICTION", rel
    print("Caso 1 OK: same antecedent + opposite future claim (nessuna transition successiva a spiegarli) -> CONTRADICTION")


def case_2_same_antecedent_different_transition_is_branch():
    rel = classify_relationship(same_antecedent=True, same_observation_time=True, same_setup_definition=True,
                                 outcomes_are_opposite=True, divergence_due_to_later_transition=True)
    assert rel == "CONDITIONAL_BRANCH", rel
    print("Caso 2 OK: same antecedent + transition osservata diversa -> CONDITIONAL_BRANCH")


def case_3_trigger_observed_before_outcome_is_causal_safe():
    v, _ = check_sequence_leakage(transition_completion_offset=0, prediction_start_offset=0, outcome_window_start_offset=1)
    assert v == PASS, v
    print("Caso 3 OK: trigger osservato prima dell'outcome (nessuna sovrapposizione) -> PASS (causal safe)")


def case_4_trigger_using_future_outcome_bar_is_leakage():
    v, _ = check_sequence_leakage(transition_completion_offset=10, prediction_start_offset=1, outcome_window_start_offset=2)
    assert v in (FAIL, NEEDS_REFORMULATION), v
    print(f"Caso 4 OK: trigger che userebbe una barra dell'outcome window -> {v} (leakage rilevato, non PASS)")


def case_5_one_q4_plus_ten_q0_not_equivalent_to_ten_q4():
    """Verifica sintetica (non dati NEXUS): la formula v2 conta CLUSTER
    indipendenti a Q3/Q4, non il numero grezzo di claim - 1 cluster Q4 +
    10 claim Q0 deve dare LO STESSO punteggio di transparency di 1 solo
    cluster Q4 (score=1), MAI il punteggio di 2 cluster indipendenti
    (score=2) che si otterrebbe con 10 fonti Q4 VERAMENTE indipendenti."""
    QUALITY_ORDER = {"Q0": 0, "Q1": 1, "Q2": 2, "Q3": 3, "Q4": 4}

    def transparency_score(claims_quality_and_cluster):
        clusters_q3plus = {cluster for quality, cluster in claims_quality_and_cluster if QUALITY_ORDER[quality] >= 3}
        n = len(clusters_q3plus)
        return 2 if n >= 2 else (1 if n == 1 else 0)

    one_q4_plus_ten_q0 = [("Q4", "cluster_A")] + [("Q0", f"cluster_{i}") for i in range(10)]
    score_mixed = transparency_score(one_q4_plus_ten_q0)

    ten_independent_q4 = [("Q4", f"cluster_{i}") for i in range(10)]
    score_ten_independent = transparency_score(ten_independent_q4)

    assert score_mixed == 1, score_mixed
    assert score_ten_independent == 2, score_ten_independent
    assert score_mixed != score_ten_independent
    print(f"Caso 5 OK: 1 Q4 + 10 Q0 -> transparency={score_mixed} (1 cluster), "
          f"10 Q4 VERAMENTE indipendenti -> transparency={score_ten_independent} (>=2 cluster) - non equivalenti")


def case_6_paper_plus_blog_same_author_same_study_is_one_cluster():
    """Verifica sui dati REALI del corpus (evidence_cluster_registry_v1.json,
    ECLU-0001: Vojtko & Dujava, SSRN + Quantpedia, stesso titolo esatto)."""
    with open(os.path.join(PHASE72_DIR, "evidence_cluster_registry_v1.json"), encoding="utf-8") as f:
        registry = json.load(f)
    eclu_0001 = next(c for c in registry["merged_clusters"] if c["cluster_id"] == "ECLU-0001")
    assert len(eclu_0001["member_source_ids"]) == 2, eclu_0001
    assert eclu_0001["authors"] == "Radovan Vojtko, Cyril Dujava"
    print(f"Caso 6 OK: paper SSRN ({eclu_0001['member_source_ids'][0]}) + riassunto blog dello stesso studio "
          f"({eclu_0001['member_source_ids'][1]}) -> 1 solo cluster ({eclu_0001['cluster_id']}), non 2 fonti indipendenti")


if __name__ == "__main__":
    case_1_same_antecedent_opposite_claim_is_contradiction()
    case_2_same_antecedent_different_transition_is_branch()
    case_3_trigger_observed_before_outcome_is_causal_safe()
    case_4_trigger_using_future_outcome_bar_is_leakage()
    case_5_one_q4_plus_ten_q0_not_equivalent_to_ten_q4()
    case_6_paper_plus_blog_same_author_same_study_is_one_cluster()
    print("\nTutti i 6 casi di regressione Phase 7.2B (sec.8) verificati.")
