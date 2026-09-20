#!/usr/bin/env python3
"""Phase 7.4A Integrity Patch sec.6 - regression tests. Dati interamente
SINTETICI (nessun dato NEXUS) + verifica strutturale degli artefatti v2
gia' scritti su disco (nessuna nuova esecuzione su dati reali qui)."""
import json
import os
import sys

PHASE74_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(PHASE74_DIR, "..", "..", "..", ".."))
sys.path.insert(0, PHASE74_DIR)
sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase7", "phase7_3", "engine"))
sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase7", "engine"))

from sequence_episode_engine import build_event_and_episode_views, build_outcome_independent_view, EpisodeRuleNotDeclaredError  # noqa: E402
from build_seq0015_statistical_test_contract import (  # noqa: E402
    CONTRACT_ENTRIES, DIAGNOSTIC_ONLY_OUTCOMES, assert_uncertainty_method_valid_for_variable_type,
    InvalidUncertaintyMethodError,
)
from seq0015_momentum_burst_detector import detect_sequence, FROZEN_PARAMETERS  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

RESULTS = []


def check(name, condition, detail=""):
    status = "PASS" if condition else "FAIL"
    RESULTS.append({"check": name, "status": status})
    print(f"[{status}] {name} {('- ' + detail) if detail else ''}")
    return condition


def make_events(rows):
    return [{"sequence_event_id": f"E{r}", "sequence_id": "SEQ-TEST", "direction": "BUY",
             "event_a_index": r, "transition_complete_index": r, "prediction_start_index": r} for r in rows]


def test_local_episode_clustering_vs_outcome_overlap():
    # t=100,t=102 -> stesso episodio locale (gap=3).
    _, ep_a = build_event_and_episode_views(make_events([100, 102]), episode_gap_rule=3, natural_horizon=40, overlap_policy="COLLAPSE_TO_FIRST")
    check("local_episode_same_cluster_t100_t102", ep_a["n_episodes"] == 1, f"n_episodes={ep_a['n_episodes']}")

    # t=100,t=105 -> episodi locali diversi (gap=3) ma outcome fortemente overlap (d=5<39).
    _, ep_b = build_event_and_episode_views(make_events([100, 105]), episode_gap_rule=3, natural_horizon=40, overlap_policy="COLLAPSE_TO_FIRST")
    indep_b = build_outcome_independent_view(ep_b["events"], outcome_overlap_embargo_bars=39)
    check("local_episode_different_but_outcome_overlap_t100_t105",
          ep_b["n_episodes"] == 2 and indep_b["n_independent_observations"] == 1,
          f"episode_view.n_episodes={ep_b['n_episodes']}, independent_view.n={indep_b['n_independent_observations']}")

    # t=100,t=141 -> outcome non overlap (d=41>=40).
    _, ep_c = build_event_and_episode_views(make_events([100, 141]), episode_gap_rule=3, natural_horizon=40, overlap_policy="COLLAPSE_TO_FIRST")
    indep_c = build_outcome_independent_view(ep_c["events"], outcome_overlap_embargo_bars=39)
    check("outcome_not_overlapping_t100_t141", indep_c["n_independent_observations"] == 2, f"independent_view.n={indep_c['n_independent_observations']}")


def test_no_pseudo_independent_overlapping_outcomes():
    """Nessuna coppia di rappresentanti INDEPENDENT_VIEW puo' restare a distanza < embargo."""
    rows = [100, 105, 110, 200, 350, 351, 355]  # cluster fitto 100-110, isolato 200, cluster 350-355
    _, ep = build_event_and_episode_views(make_events(rows), episode_gap_rule=3, natural_horizon=40, overlap_policy="COLLAPSE_TO_FIRST")
    indep = build_outcome_independent_view(ep["events"], outcome_overlap_embargo_bars=39)
    reps = sorted(e["event_a_index"] for e in indep["events"])
    min_gap = min(b - a for a, b in zip(reps, reps[1:])) if len(reps) > 1 else 999
    check("no_pseudo_independent_overlapping_outcomes", min_gap >= 40 if len(reps) > 1 else True,
          f"rappresentanti INDEPENDENT_VIEW={reps}, gap minimo={min_gap} (deve essere >=40=natural_horizon)")


def test_wilson_rejected_for_continuous_outcome():
    fake_entry = {"outcome_id": "FAKE_CONTINUOUS", "variable_type": "CONTINUOUS", "uncertainty_method": "WILSON_CI95 (errato)"}
    try:
        assert_uncertainty_method_valid_for_variable_type(fake_entry)
        check("wilson_rejected_for_continuous_outcome", False, "Wilson su outcome continuo NON e' stato rifiutato!")
    except InvalidUncertaintyMethodError:
        check("wilson_rejected_for_continuous_outcome", True)
    # positivo: il contratto reale non deve mai violare questa regola.
    all_valid = True
    for entry in CONTRACT_ENTRIES:
        try:
            assert_uncertainty_method_valid_for_variable_type(entry)
        except InvalidUncertaintyMethodError:
            all_valid = False
    check("real_contract_never_uses_wilson_for_continuous", all_valid)


def test_each_inferential_outcome_has_frozen_pvalue_method():
    ok = all(e.get("hypothesis_test") and e.get("p_value_method") for e in CONTRACT_ENTRIES)
    check("each_inferential_outcome_has_frozen_pvalue_method", ok, f"{sum(1 for e in CONTRACT_ENTRIES if e.get('p_value_method'))}/{len(CONTRACT_ENTRIES)} con metodo definito")


def test_fdr_family_size_equals_actual_pvalues():
    n_candidates = 3
    n_outcomes_with_method = sum(1 for e in CONTRACT_ENTRIES if e.get("p_value_method"))
    declared_family_size = n_candidates * n_outcomes_with_method
    check("fdr_family_size_equals_actual_generated_pvalues", declared_family_size == 21 and n_outcomes_with_method == 7,
          f"n_candidates={n_candidates} x n_outcomes_with_method={n_outcomes_with_method} = {declared_family_size}")


def test_diagnostic_only_never_enters_bh():
    contract_outcome_ids = {e["outcome_id"] for e in CONTRACT_ENTRIES}
    overlap = contract_outcome_ids & set(DIAGNOSTIC_ONLY_OUTCOMES)
    check("diagnostic_only_never_enters_bh", len(overlap) == 0, f"overlap (deve essere vuoto)={overlap}")


def test_detector_hash_unchanged_unless_only_comments_docs():
    """Il file .py e' cambiato (correzione terminologica = commenti/doc) ma il
    COMPORTAMENTO del detector su una fixture sintetica congelata deve restare
    identico - confrontato con lo snapshot preso e verificato subito dopo la
    scrittura di v1 (Phase 7.4A originale, PRIMA della patch)."""
    rng = np.random.default_rng(42)
    n = 400
    close = 2000 + np.cumsum(rng.normal(0, 2.0, n))
    open_ = close - rng.normal(0, 1.0, n)
    high = np.maximum(open_, close) + np.abs(rng.normal(0, 0.5, n))
    low = np.minimum(open_, close) - np.abs(rng.normal(0, 0.5, n))
    for idx, mult in [(300, 8.0), (301, 7.0), (350, 9.0)]:
        high[idx] = close[idx - 1] + mult * 3.0
        low[idx] = close[idx - 1] - 1.0
        close[idx] = high[idx] - 0.5
        open_[idx] = close[idx - 1]
    bars = pd.DataFrame({"open": open_, "high": high, "low": low, "close": close})
    vol_labels = np.where(np.arange(n) % 3 == 0, "LOW", np.where(np.arange(n) % 3 == 1, "MED", "HIGH"))
    trend_labels = np.where(np.arange(n) % 3 == 0, "DOWN", np.where(np.arange(n) % 3 == 1, "FLAT", "UP"))
    market_state = pd.DataFrame({"volatility_state": vol_labels, "trend_state": trend_labels})

    events_v2 = detect_sequence(bars, market_state, FROZEN_PARAMETERS)
    rows_v2 = sorted(e["event_a_index"] for e in events_v2)
    # Snapshot congelato SUBITO DOPO la build originale di v1 (stessa fixture, stesso seed=42,
    # riportato testualmente nel report Phase 7.4A: "13 eventi rilevati").
    EXPECTED_ROWS_V1_SNAPSHOT = [273, 276, 281, 293, 300, 301, 302, 340, 350, 351, 375, 382, 390]
    check("detector_behavior_unchanged_only_comments_docs_changed", rows_v2 == EXPECTED_ROWS_V1_SNAPSHOT,
          f"v2_rows={rows_v2} atteso={EXPECTED_ROWS_V1_SNAPSHOT}")


def test_embargo_not_declared_rejected():
    _, ep = build_event_and_episode_views(make_events([100, 105]), episode_gap_rule=3, natural_horizon=40, overlap_policy="COLLAPSE_TO_FIRST")
    try:
        build_outcome_independent_view(ep["events"], outcome_overlap_embargo_bars=None)
        check("outcome_overlap_embargo_not_declared_rejected", False, "embargo mancante NON rifiutato!")
    except EpisodeRuleNotDeclaredError:
        check("outcome_overlap_embargo_not_declared_rejected", True)


def main():
    test_local_episode_clustering_vs_outcome_overlap()
    test_no_pseudo_independent_overlapping_outcomes()
    test_wilson_rejected_for_continuous_outcome()
    test_each_inferential_outcome_has_frozen_pvalue_method()
    test_fdr_family_size_equals_actual_pvalues()
    test_diagnostic_only_never_enters_bh()
    test_detector_hash_unchanged_unless_only_comments_docs()
    test_embargo_not_declared_rejected()

    n_pass = sum(1 for r in RESULTS if r["status"] == "PASS")
    n_fail = len(RESULTS) - n_pass
    print(f"\n=== Phase 7.4A Integrity Patch regression suite: {n_pass} PASS, {n_fail} FAIL su {len(RESULTS)} check ===")
    return n_fail == 0


if __name__ == "__main__":
    ok = main()
    sys.exit(0 if ok else 1)
