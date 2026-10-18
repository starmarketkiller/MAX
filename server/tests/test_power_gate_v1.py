"""Power Gate V1: classification, fail-closed behaviour and PR #59 calibration.

Synthetic plans plus cases already published in the repository (BREAKOUT_ACC,
LIQ_SWEEP figures from Phase 7.21/7.25 and the Phase 7.26 exposure registry).
No market data is read and no simulation is re-run.
"""
from __future__ import annotations

import copy
import sys
from pathlib import Path

import pytest

RESEARCH = Path(__file__).resolve().parents[1] / "research_scripts"
sys.path.insert(0, str(RESEARCH))

from research_intelligence_v1 import power as P  # noqa: E402
from research_intelligence_v1 import power_gate as G  # noqa: E402

CAL = G.calibration()
REG = G.exposure_registry()

# LIQ_SWEEP-like outcomes (sd 1.44R, Phase 7.25) on new forward data, adequately sized.
READY = {
    "experiment_id": "SYNTH_READY",
    "purpose": "CONFIRMATION",
    "effect": {"min_net_effect": 0.3, "unit": "R", "source": "ECONOMIC_MINIMUM"},
    "dispersion": {"sigma": 1.44, "source": "OBSERVED"},
    "frequency": {"events_per_year": 200, "window_years": 2},
    "dependence": {"structure": "INDEPENDENT"},
    "costs": {"base": 0.0, "stress": 0.02},
    "benchmark": "REGIME_MATCHED",
    "inference_method": "STUDENTIZED_BLOCK_BOOTSTRAP",
    "datasets": [{"dataset_id": "SYNTH_FORWARD_2027", "split": "discovery", "exposure": "UNSEEN_FORWARD"}],
}


def assess(**changes):
    plan = copy.deepcopy(READY)
    for key, value in changes.items():
        if value is None:
            plan.pop(key, None)
        else:
            plan[key] = value
    return G.assess(plan, cal=CAL, registry=REG)


def test_calibration_comes_from_pr59_results():
    assert CAL["source_sha256"] == "c538a5d2f3d65a42ac2f71bc52039e67636e9d16e25c6e443134f6e1732a05d4"
    assert CAL["analytic_power_max_overestimate"] == pytest.approx(0.0344, abs=1e-4)
    assert CAL["clustered_design_effect"] == pytest.approx(2.449, abs=1e-3)
    assert CAL["winners_curse_inflation_by_n"][47] == pytest.approx(3.845, abs=1e-3)


def test_7_adequate_power_is_ready_but_not_an_authorization():
    card = assess()
    assert card["status"] == "POWER_READY"
    assert card["numbers"]["n_expected"] >= card["numbers"]["n_required"]
    assert card["numbers"]["analytic_margin_added"] == CAL["analytic_power_max_overestimate"]
    assert "not EDGE_VALIDATED" in card["not_an_authorization"]


def test_1_small_independent_sample_needs_data():
    card = assess(frequency={"events_per_year": 6.7, "window_years": 7.3},
                  dispersion={"sigma": 2.38, "source": "OBSERVED"})
    assert card["status"] == "DATA_REQUIRED"
    assert "UNDERPOWERED_AT_EXPECTED_N" in card["reasons"]
    screen = assess(purpose="SCREENING", family_size=21,
                    frequency={"events_per_year": 6.7, "window_years": 7.3})
    assert screen["status"] == "EXPLORATORY_ONLY"


def test_2_correlated_events_block_iid_and_inflate_n():
    blocked = assess(dependence={"structure": "CLUSTERED"}, inference_method="IID_BOOTSTRAP")
    assert blocked["status"] == "METHOD_BLOCKED" and "IID_INFERENCE_UNDER_DEPENDENCE" in blocked["reasons"]
    clustered = assess(dependence={"structure": "CLUSTERED"})
    assert clustered["numbers"]["design_effect"] == pytest.approx(CAL["clustered_design_effect"], abs=1e-3)
    assert clustered["numbers"]["n_effective"] < assess()["numbers"]["n_effective"] / 2


def test_3_overlapping_outcomes_use_declared_deff_if_larger():
    card = assess(dependence={"structure": "OVERLAPPING", "design_effect": 4.0})
    assert card["numbers"]["design_effect"] == 4.0
    assert card["numbers"]["n_required"] >= 4 * assess()["numbers"]["n_required"] * 0.95


def test_4_high_costs_remove_the_effect():
    card = assess(costs={"base": 0.0, "stress": 0.35})
    assert card["status"] == "EXPLORATORY_ONLY"
    assert "EFFECT_DOES_NOT_SURVIVE_STRESS_COSTS_OR_SHRINKAGE" in card["reasons"]


@pytest.mark.parametrize("bench,code", [(None, "BENCHMARK_MISSING"), ("ZERO", "BENCHMARK_ZERO_COUNTS_DRIFT_AS_EDGE"),
                                        ("UNCONDITIONAL", "BENCHMARK_CANNOT_SEPARATE_ALPHA_FROM_EXPOSURE")])
def test_5_missing_or_inadequate_benchmark_blocks(bench, code):
    card = assess(benchmark=bench) if bench else assess(benchmark=None)
    assert card["status"] == "METHOD_BLOCKED" and code in card["reasons"]


def test_6_insufficient_or_unusable_datasets():
    published = assess(datasets=[{"dataset_id": "BREAKOUT_ACC::2019.02.21_2026.06.09", "split": "discovery"}])
    assert published["status"] == "DATA_REQUIRED" and "CONFIRMATION_ON_EXPOSED_DATA" in published["reasons"]
    unknown = assess(datasets=[{"dataset_id": "SOMETHING_NEW", "split": "discovery"}])
    assert unknown["status"] == "NOT_ASSESSABLE" and "DATASET_EXPOSURE_UNKNOWN" in unknown["reasons"]
    sealed = assess(datasets=[{"dataset_id": "SYNTH", "split": "final_holdout", "exposure": "UNSEEN_FORWARD"}])
    assert sealed["status"] == "METHOD_BLOCKED" and "PROTECTED_SPLIT:final_holdout" in sealed["reasons"]


@pytest.mark.parametrize("field", ["purpose", "effect", "dispersion", "frequency", "dependence", "costs", "datasets"])
def test_8_unknown_parameters_fail_closed(field):
    card = assess(**{field: None})
    assert card["status"] == "NOT_ASSESSABLE" and card["reasons"]


def test_screening_family_size_required_and_ceiling():
    assert assess(purpose="SCREENING")["status"] == "NOT_ASSESSABLE"
    ready = assess(purpose="SCREENING", family_size=1, frequency={"events_per_year": 400, "window_years": 2})
    assert ready["status"] == "POWER_READY" and ready["evidence_ceiling"] == "DISCOVERY_ONLY"


def test_screening_estimate_is_shrunk_before_sizing_confirmation():
    card = assess(effect={"min_net_effect": 0.9, "unit": "R", "source": "SCREENING_ESTIMATE", "screening_n": 47})
    assert card["numbers"]["winners_curse_inflation_applied"] == pytest.approx(3.845, abs=1e-3)
    assert card["numbers"]["effect_used_after_stress_and_shrinkage"] < 0.25


def test_published_breakout_acc_needs_over_a_century():
    card = assess(purpose="CONFIRMATION", dispersion={"sigma": 2.38, "source": "OBSERVED"},
                  frequency={"events_per_year": 6.7, "window_years": 7.3}, costs={"base": 0.0, "stress": 0.08},
                  datasets=[{"dataset_id": "BREAKOUT_ACC::2019.02.21_2026.06.09", "split": "discovery"}])
    assert card["status"] == "DATA_REQUIRED"
    assert card["numbers"]["years_required_at_frequency"] > 100


def test_analytic_power_tracks_pr59_simulation_within_margin():
    import json
    res = json.loads(Path(G.CALIBRATION_PATH).read_text(encoding="utf-8"))
    sd = res["meta"]["trade_dist_sd"]
    for c in res["trade"]:
        if c["costR"] == 0 and c["deltaR"] > 0:
            analytic = P.power_ci_low_positive(c["deltaR"], sd[c["dist"]], c["n"])
            assert analytic - c["power_lower_ci_gt_0"] <= CAL["analytic_power_max_overestimate"] + 1e-9


def test_deterministic_card():
    assert assess()["card_sha256"] == assess()["card_sha256"]
