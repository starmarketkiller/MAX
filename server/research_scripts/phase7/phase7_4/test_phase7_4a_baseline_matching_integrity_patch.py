#!/usr/bin/env python3
"""Phase 7.4A Structural Closure + Baseline Matching Integrity Patch -
regression tests per l'infrastruttura generale di matching
(BaselineEngineV4/ControlReuseLedger/SequenceBaselineAdapter). Dati
interamente SINTETICI. Nessun dato NEXUS, nessun outcome."""
import os
import random
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", ".."))
ENGINE_DIR = os.path.join(ROOT, "server", "research_scripts", "phase7", "engine")
PHASE73_DIR = os.path.join(ROOT, "server", "research_scripts", "phase7", "phase7_3")
sys.path.insert(0, ENGINE_DIR)
sys.path.insert(0, PHASE73_DIR)

from baseline_engine_v4 import BaselineEngineV4, FitIsolationViolation  # noqa: E402
from control_reuse_ledger import ControlReuseLedger  # noqa: E402
from sequence_baseline_adapter_v1 import SequenceBaselineAdapter  # noqa: E402
from cross_split_safety import CrossSplitViolation  # noqa: E402

RESULTS = []
BOUNDARIES = {"discovery": (0, 200), "internal_validation": (200, 280),
              "locked_validation": (280, 360), "final_holdout": (360, 440)}


def check(name, condition, detail=""):
    status = "PASS" if condition else "FAIL"
    RESULTS.append({"check": name, "status": status})
    print(f"[{status}] {name} {('- ' + detail) if detail else ''}")
    return condition


def test_direction_included_and_no_control_exceeds_cap():
    pool = [100, 102, 104, 106, 108, 110, 112, 114, 116]
    row = {c: c for c in pool}
    direction = {c: "BUY" for c in pool}
    feat = {c: {"volatility_state": "HIGH"} for c in pool}
    engine = BaselineEngineV4(match_dimensions=["volatility_state"], k=3, split_boundaries=BOUNDARIES,
                              minimum_control_count=3, max_control_reuse_per_run=2)
    all_selected = []
    for i in range(6):
        r = engine.match(event_id=f"E{i}", event_row=120 + i, event_direction="BUY",
                         event_features={"volatility_state": "HIGH"}, control_pool=pool,
                         control_row_by_id=row, control_direction_by_id=direction, control_features_by_id=feat)
        all_selected.extend(m["control_id"] for m in r["matches"])
        for m in r["matches"]:
            check_key = f"direction_present_in_match_record_{i}_{m['control_id']}"
            RESULTS.append({"check": check_key, "status": "PASS" if "control_direction" in m else "FAIL"})
    check("direction_field_present_in_every_match_record", all("control_direction" in m for r in [engine.match(
        event_id="EX", event_row=127, event_direction="BUY", event_features={"volatility_state": "HIGH"},
        control_pool=pool, control_row_by_id=row, control_direction_by_id=direction, control_features_by_id=feat)] for m in r["matches"]))
    from collections import Counter
    counts = Counter(all_selected)
    check("no_control_ever_exceeds_cap", all(c <= 2 for c in counts.values()), f"counts={dict(counts)}")


def test_insufficient_pool_after_reuse_cap():
    pool = [10, 12, 14]
    row = {c: c for c in pool}
    direction = {c: "BUY" for c in pool}
    feat = {c: {"volatility_state": "HIGH"} for c in pool}
    engine = BaselineEngineV4(match_dimensions=["volatility_state"], k=2, split_boundaries=BOUNDARIES,
                              minimum_control_count=3, max_control_reuse_per_run=1)
    r1 = engine.match(event_id="A", event_row=20, event_direction="BUY", event_features={"volatility_state": "HIGH"},
                      control_pool=pool, control_row_by_id=row, control_direction_by_id=direction, control_features_by_id=feat)
    check("first_match_succeeds", r1["status"] in ("MATCHED", "MATCHED_K_SHORTFALL"))
    r2 = engine.match(event_id="B", event_row=22, event_direction="BUY", event_features={"volatility_state": "HIGH"},
                      control_pool=pool, control_row_by_id=row, control_direction_by_id=direction, control_features_by_id=feat)
    check("second_match_rejected_insufficient_pool_after_cap", r2["status"] == "REJECTED_INSUFFICIENT_POOL",
          f"status={r2['status']}, pool={pool} cap=1 (solo 3 controlli, 2 gia' usati da A, ne restano <3)")


def test_stable_deterministic_and_shuffled_input():
    pool = [20, 22, 24, 26, 28, 30, 32, 34]  # tutti in discovery (0,200) - stesso split dell'evento
    row = {c: c for c in pool}
    direction = {c: "BUY" for c in pool}
    feat = {c: {"volatility_state": "HIGH"} for c in pool}

    def run_once(input_pool, seed=None):
        eng = BaselineEngineV4(match_dimensions=["volatility_state"], k=3, split_boundaries=BOUNDARIES, minimum_control_count=3)
        r = eng.match(event_id="E", event_row=10, event_direction="BUY", event_features={"volatility_state": "HIGH"},
                     control_pool=input_pool, control_row_by_id=row, control_direction_by_id=direction, control_features_by_id=feat)
        return sorted(m["control_id"] for m in r["matches"])

    baseline_result = run_once(pool)
    for seed in [1, 2, 3, 42]:
        shuffled = list(pool)
        random.Random(seed).shuffle(shuffled)
        result = run_once(shuffled)
        check(f"shuffled_input_seed_{seed}_produces_same_matches", result == baseline_result,
              f"baseline={baseline_result}, shuffled_result={result}")


def test_numeric_distance_beats_farther_candidate_regardless_of_reuse():
    engine = BaselineEngineV4(match_dimensions=["proximity"], k=1, split_boundaries=BOUNDARIES, minimum_control_count=2)
    engine.fit_normalization({50: {"proximity": 0.0}, 52: {"proximity": 10.0}})
    pool = [50, 52]
    row = {50: 50, 52: 52}
    direction = {50: "BUY", 52: "BUY"}
    feat = {50: {"proximity": 0.1}, 52: {"proximity": 9.9}}
    engine._reuse_ledger = ControlReuseLedger(max_control_reuse_per_run=10)
    engine._reuse_ledger.register_controls_used([50] * 5)  # 50 vicinissimo ma gia' riusato 5 volte
    r = engine.match(event_id="E", event_row=10, event_direction="BUY", event_features={"proximity": 0.0},
                     control_pool=pool, control_row_by_id=row, control_direction_by_id=direction, control_features_by_id=feat)
    check("closer_candidate_wins_despite_higher_reuse", r["matches"][0]["control_id"] == 50,
          f"selected={r['matches'][0]['control_id']} (atteso 50, il piu' vicino, anche se gia' riusato 5 volte)")


def test_equal_distance_uses_lower_reuse_then_stable_id():
    engine = BaselineEngineV4(match_dimensions=["volatility_state"], k=1, split_boundaries=BOUNDARIES, minimum_control_count=2)
    pool = [60, 62]  # nessuna dim numerica -> distanza sempre None per entrambi (equidistanti per costruzione)
    row = {60: 60, 62: 62}
    direction = {60: "BUY", 62: "BUY"}
    feat = {60: {"volatility_state": "HIGH"}, 62: {"volatility_state": "HIGH"}}
    engine._reuse_ledger = ControlReuseLedger(max_control_reuse_per_run=10)
    engine._reuse_ledger.register_controls_used([62])  # 62 usato 1 volta, 60 mai
    r = engine.match(event_id="E", event_row=10, event_direction="BUY", event_features={"volatility_state": "HIGH"},
                     control_pool=pool, control_row_by_id=row, control_direction_by_id=direction, control_features_by_id=feat)
    check("equal_distance_prefers_lower_reuse", r["matches"][0]["control_id"] == 60,
          f"selected={r['matches'][0]['control_id']} (atteso 60, mai usato, contro 62 gia' usato 1 volta)")

    # Ora pareggio anche sul reuse (entrambi 0) -> deve risolvere per control_id crescente (stabile, mai casuale).
    engine2 = BaselineEngineV4(match_dimensions=["volatility_state"], k=1, split_boundaries=BOUNDARIES, minimum_control_count=2)
    r2 = engine2.match(event_id="E2", event_row=10, event_direction="BUY", event_features={"volatility_state": "HIGH"},
                       control_pool=[62, 60], control_row_by_id=row, control_direction_by_id=direction, control_features_by_id=feat)
    check("equal_distance_equal_reuse_resolves_by_stable_lowest_id", r2["matches"][0]["control_id"] == 60,
          f"selected={r2['matches'][0]['control_id']} (atteso 60, il control_id piu' basso, indipendentemente dall'ordine [62,60] nel pool)")


def test_usage_report_correct():
    pool = [70, 72, 74, 76, 78]
    row = {c: c for c in pool}
    direction = {c: "BUY" for c in pool}
    feat = {c: {"volatility_state": "HIGH"} for c in pool}
    engine = BaselineEngineV4(match_dimensions=["volatility_state"], k=2, split_boundaries=BOUNDARIES,
                              minimum_control_count=2, max_control_reuse_per_run=3)
    for i in range(4):
        engine.match(event_id=f"E{i}", event_row=100 + i, event_direction="BUY",
                    event_features={"volatility_state": "HIGH"}, control_pool=pool,
                    control_row_by_id=row, control_direction_by_id=direction, control_features_by_id=feat)
    report = engine.reuse_usage_report()
    check("usage_report_not_none_when_ledger_active", report is not None)
    check("usage_report_total_assignments_correct", report["n_controls_used"] * report["mean_reuse"] == 8,
          f"report={report} (4 eventi x k=2 = 8 assegnazioni totali)")
    check("usage_report_max_never_exceeds_cap", report["max_reuse_observed"] <= 3)

    engine_no_ledger = BaselineEngineV4(match_dimensions=["volatility_state"], k=2, split_boundaries=BOUNDARIES, minimum_control_count=2)
    check("usage_report_none_when_no_ledger_declared", engine_no_ledger.reuse_usage_report() is None)


def test_cross_split_safety_preserved():
    pool = list(range(0, 40, 2)) + [200, 202]  # 200/202 sono in internal_validation
    row = {c: c for c in pool}
    direction = {c: "BUY" for c in pool}
    feat = {c: {"volatility_state": "HIGH"} for c in pool}
    engine = BaselineEngineV4(match_dimensions=["volatility_state"], k=5, split_boundaries=BOUNDARIES,
                              minimum_control_count=5, max_control_reuse_per_run=5)
    r = engine.match(event_id="E", event_row=10, event_direction="BUY", event_features={"volatility_state": "HIGH"},
                     control_pool=pool, control_row_by_id=row, control_direction_by_id=direction, control_features_by_id=feat)
    matched_ids = {m["control_id"] for m in r["matches"]}
    check("cross_split_controls_never_selected_even_with_reuse_ledger_active", not ({200, 202} & matched_ids),
          f"matched_ids={matched_ids}")


def test_sequence_baseline_adapter_requires_max_reuse():
    try:
        SequenceBaselineAdapter(match_dimensions=["volatility_state"], k=5, split_boundaries=BOUNDARIES, max_control_reuse_per_run=None)
        check("adapter_rejects_missing_max_control_reuse_per_run", False, "avrebbe dovuto sollevare ValueError!")
    except ValueError:
        check("adapter_rejects_missing_max_control_reuse_per_run", True)
    try:
        SequenceBaselineAdapter(match_dimensions=["volatility_state"], k=5, split_boundaries=BOUNDARIES, max_control_reuse_per_run=0)
        check("adapter_rejects_zero_max_control_reuse_per_run", False, "avrebbe dovuto sollevare ValueError!")
    except ValueError:
        check("adapter_rejects_zero_max_control_reuse_per_run", True)


def test_no_outcome_access():
    """Verifica strutturale: nessuno dei moduli engine coinvolti in questa
    patch importa o referenzia concetti di outcome."""
    for path in [
        os.path.join(ENGINE_DIR, "baseline_engine_v4.py"),
        os.path.join(ENGINE_DIR, "control_reuse_ledger.py"),
        os.path.join(PHASE73_DIR, "sequence_baseline_adapter_v1.py"),
    ]:
        with open(path, encoding="utf-8") as f:
            content = f.read().lower()
        for forbidden in ["mfe", "mae", "delta_p", "delta_e", "target_hit", "stop_hit", "pnl", "profitab"]:
            check(f"no_outcome_token_'{forbidden}'_in_{os.path.basename(path)}", forbidden not in content)


def main():
    test_direction_included_and_no_control_exceeds_cap()
    test_insufficient_pool_after_reuse_cap()
    test_stable_deterministic_and_shuffled_input()
    test_numeric_distance_beats_farther_candidate_regardless_of_reuse()
    test_equal_distance_uses_lower_reuse_then_stable_id()
    test_usage_report_correct()
    test_cross_split_safety_preserved()
    test_sequence_baseline_adapter_requires_max_reuse()
    test_no_outcome_access()

    n_pass = sum(1 for r in RESULTS if r["status"] == "PASS")
    n_fail = len(RESULTS) - n_pass
    print(f"\n=== Phase 7.4A Baseline Matching Integrity Patch regression suite: {n_pass} PASS, {n_fail} FAIL su {len(RESULTS)} check ===")
    return n_fail == 0


if __name__ == "__main__":
    ok = main()
    sys.exit(0 if ok else 1)
