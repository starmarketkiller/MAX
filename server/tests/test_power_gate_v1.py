"""Power Gate V1 (rules V1.1): classification, fail-closed behaviour, PR #59 calibration,
and one regression per Codex finding on PR #60.

Synthetic plans, two small synthetic fixtures (provenance manifest, preregistration) and
cases already published in the repository. No market data, no protected dataset, no
simulation re-run.
"""
from __future__ import annotations

import copy
import hashlib
import math
import sys
from pathlib import Path

import pytest

RESEARCH = Path(__file__).resolve().parents[1] / "research_scripts"
sys.path.insert(0, str(RESEARCH))

from research_intelligence_v1 import power_gate as G  # noqa: E402

CAL = G.calibration()
REG = G.exposure_registry()
FIX = "server/tests/fixtures/power_gate"
ROOT = Path(G.REPO_ROOT)


def _sha(rel):
    return hashlib.sha256((ROOT / rel).read_bytes()).hexdigest()


MANIFEST = f"{FIX}/forward_provenance_manifest.json"
PREREG = f"{FIX}/confirmation_preregistration.json"
PROVENANCE = {"manifest_path": MANIFEST, "manifest_sha256": _sha(MANIFEST), "declared_at": "2026-10-18",
              "data_start": "2026-11-01", "data_end": "2028-10-31", "declared_before_collection": True}

# Inside the one design PR #59 simulated: paired ATR difference vs one regime-matched control.
READY = {
    "experiment_id": "SYNTH_READY",
    "purpose": "CONFIRMATION",
    "effect": {"economic_min_net_effect": 1.0, "unit": "ATR"},
    "dispersion": {"estimand": "PAIRED_DIFFERENCE_VS_BENCHMARK", "sigma_paired_difference": 3.0, "unit": "ATR",
                   "source": "OBSERVED", "controls_per_event": 1, "control_reuse": False},
    "frequency": {"events_per_year": 100, "window_years": 2},
    "dependence": {"structure": "INDEPENDENT", "horizon_bars": 10, "min_spacing_bars": 10},
    "costs": {"base": 0.0, "stress": 0.0, "unit": "ATR"},
    "benchmark": "REGIME_MATCHED",
    "inference_method": "STUDENTIZED_BLOCK_BOOTSTRAP",
    "datasets": [{"dataset_id": "SYNTH_FORWARD_2026Q4", "split": "discovery", "provenance": PROVENANCE}],
    "confirmation_family": {"size": 1, "alpha_allocation": "BONFERRONI", "preregistration_path": PREREG,
                            "preregistration_sha256": _sha(PREREG)},
}

# The V1 fixture that V1 classified POWER_READY (raw-R sigma, caller-declared UNSEEN_FORWARD).
V1_READY_FIXTURE = {
    "experiment_id": "SYNTH_READY_V1",
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


def plan(**changes):
    p = copy.deepcopy(READY)
    for path, value in changes.items():
        node, keys = p, path.split("__")
        for k in keys[:-1]:
            node = node[k]
        if value is DROP:
            node.pop(keys[-1], None)
        else:
            node[keys[-1]] = value
    return p


DROP = object()


def assess(p):
    return G.assess(p, cal=CAL, registry=REG)


# ---------- baseline and calibration ----------

def test_calibration_comes_from_pr59_results():
    assert CAL["source_sha256"] == "c538a5d2f3d65a42ac2f71bc52039e67636e9d16e25c6e443134f6e1732a05d4"
    assert CAL["winners_curse"]["inflation_by_screening_n"][47] == pytest.approx(3.845, abs=1e-3)
    assert CAL["type1_max"]["G_C|IID_BOOTSTRAP"] > 0.075 and CAL["type1_max"]["G_U|STUDENTIZED_BLOCK_BOOTSTRAP"] <= 0.075


def test_ready_only_by_a_dominating_simulated_cell():
    card = assess(READY)
    assert card["status"] == "POWER_READY", card["reasons"]
    cell = card["numbers"]["dominating_pr59_cell"]
    assert cell["n"] <= 200 and cell["delta"] <= 1.0 and cell["sigma_d"] >= 3.0 and cell["power"] >= 0.8
    assert "not EDGE_VALIDATED" in card["not_an_authorization"]


def test_deterministic_card():
    assert assess(READY)["card_sha256"] == assess(READY)["card_sha256"]


# ---------- P0: dataset provenance ----------

def test_p0_v1_ready_fixture_is_no_longer_ready():
    card = assess(V1_READY_FIXTURE)
    assert card["status"] == "NOT_ASSESSABLE"


def test_p0_caller_declaration_alone_is_not_provenance():
    card = assess(plan(datasets=[{"dataset_id": "SYNTH_FORWARD_2027", "split": "discovery",
                                  "exposure": "UNSEEN_FORWARD"}]))
    assert card["status"] == "NOT_ASSESSABLE"
    assert any(r.startswith("DATASET_PROVENANCE_UNVERIFIED") for r in card["reasons"])


@pytest.mark.parametrize("bad", [
    {"manifest_sha256": "0" * 64},
    {"manifest_path": "server/data_cache/dukascopy_phaseH/manifest.json"},
    {"manifest_path": "server/research_scripts/phase7/final_holdout_seal_v1.json"},
    {"manifest_path": "server/research_scripts/phase7/phase7_9h/raw_data/nxs_d1_gold_phase79h.csv"},
    {"manifest_path": "/etc/passwd"},
    {"declared_before_collection": False},
    {"data_start": "2026-10-01"},
])
def test_p0_unverifiable_provenance_fails_closed(bad):
    prov = {**PROVENANCE, **bad}
    card = assess(plan(datasets=[{"dataset_id": "SYNTH_FORWARD_2026Q4", "split": "discovery", "provenance": prov}]))
    assert card["status"] == "NOT_ASSESSABLE"


def test_p0_exposed_registry_dataset_needs_new_data():
    card = assess(plan(datasets=[{"dataset_id": "BREAKOUT_ACC::2019.02.21_2026.06.09", "split": "discovery"}]))
    assert card["status"] == "DATA_REQUIRED" and "CONFIRMATION_ON_EXPOSED_DATA" in card["reasons"]


def test_p0_protected_split_blocked_without_opening_it():
    card = assess(plan(datasets=[{"dataset_id": "SYNTH_FORWARD_2026Q4", "split": "final_holdout",
                                  "provenance": PROVENANCE}]))
    assert card["status"] == "METHOD_BLOCKED" and "PROTECTED_SPLIT:final_holdout" in card["reasons"]


# ---------- P1-2: estimand, benchmark variance, control reuse ----------

def test_p1_raw_outcome_sigma_is_not_the_estimand():
    card = assess(plan(dispersion__estimand="RAW_OUTCOME"))
    assert card["status"] == "NOT_ASSESSABLE" and "ESTIMAND_NOT_PAIRED_DIFFERENCE_VS_BENCHMARK" in card["reasons"]


@pytest.mark.parametrize("change,code", [
    ({"effect__unit": "R", "dispersion__unit": "R", "costs__unit": "R"}, "UNIT_R_NOT_SIMULATED_WITH_A_BENCHMARK"),
    ({"benchmark": "RANDOM_TIMESTAMP_MATCHED"}, "BENCHMARK_RANDOM_TIMESTAMP_MATCHED_NOT_SIMULATED"),
    ({"dispersion__controls_per_event": 3}, "CONTROLS_PER_EVENT_NOT_SIMULATED"),
])
def test_p1_uncalibrated_designs_are_not_ready(change, code):
    card = assess(plan(**change))
    assert card["status"] == "NOT_ASSESSABLE" and "POWER_NOT_CALIBRATED_FOR_DESIGN" in card["reasons"]
    assert code in card["reasons"]


def test_p1_control_reuse_blocks():
    card = assess(plan(dispersion__control_reuse=True))
    assert card["status"] == "METHOD_BLOCKED" and "CONTROL_REUSE_NOT_MODELLED" in card["reasons"]


@pytest.mark.parametrize("bench,code", [(DROP, "BENCHMARK_MISSING"), ("ZERO", "BENCHMARK_ZERO_COUNTS_DRIFT_AS_EDGE"),
                                        ("UNCONDITIONAL", "BENCHMARK_CANNOT_SEPARATE_ALPHA_FROM_EXPOSURE")])
def test_p1_missing_or_inadequate_benchmark(bench, code):
    card = assess(plan(benchmark=bench))
    assert card["status"] == "METHOD_BLOCKED" and code in card["reasons"]


# ---------- P1-3: design effect ----------

def test_p1_clustered_without_justified_deff_is_not_assessable():
    card = assess(plan(dependence={"structure": "CLUSTERED", "horizon_bars": 10, "min_spacing_bars": 2}))
    assert card["status"] == "NOT_ASSESSABLE" and "DESIGN_EFFECT_UNJUSTIFIED" in card["reasons"]


def test_p1_pr59_cluster_model_match_uses_clustered_cells():
    dep = {"structure": "CLUSTERED", "horizon_bars": 10, "min_spacing_bars": 2, "cluster_size": 4,
           "design_effect_basis": {"type": "PR59_CLUSTER_MODEL_MATCH"}}
    card = assess(plan(dependence=dep, dispersion__sigma_paired_difference=4.5))
    assert card["status"] == "POWER_READY" and card["numbers"]["dominating_pr59_cell"]["gen"] == "G_C"
    other = assess(plan(dependence={**dep, "cluster_size": 8}, dispersion__sigma_paired_difference=4.5))
    assert other["status"] == "NOT_ASSESSABLE" and "DESIGN_EFFECT_UNJUSTIFIED" in other["reasons"]


def test_p1_plan_specific_deff_is_verified_but_not_certified():
    dep = {"structure": "OVERLAPPING", "horizon_bars": 10, "min_spacing_bars": 5, "design_effect": 3.0,
           "design_effect_basis": {"type": "MEASURED_ON_PLAN_DATA", "source_path": MANIFEST,
                                   "source_sha256": _sha(MANIFEST)}}
    card = assess(plan(dependence=dep))
    assert card["status"] == "NOT_ASSESSABLE"
    assert "PLAN_SPECIFIC_DEPENDENCE_NOT_SIMULATED_IN_PR59" in card["reasons"]


def test_p1_independence_contradicted_by_geometry():
    card = assess(plan(dependence={"structure": "INDEPENDENT", "horizon_bars": 10, "min_spacing_bars": 3}))
    assert card["status"] == "METHOD_BLOCKED"
    assert "DECLARED_INDEPENDENT_BUT_OUTCOME_WINDOWS_OVERLAP" in card["reasons"]


def test_p1_iid_bootstrap_under_dependence_blocked():
    dep = {"structure": "CLUSTERED", "horizon_bars": 10, "min_spacing_bars": 2, "cluster_size": 4,
           "design_effect_basis": {"type": "PR59_CLUSTER_MODEL_MATCH"}}
    card = assess(plan(dependence=dep, inference_method="IID_BOOTSTRAP"))
    assert card["status"] == "METHOD_BLOCKED" and "IID_INFERENCE_UNDER_DEPENDENCE" in card["reasons"]


# ---------- P1-4: analytic margin never certifies ----------

def test_p1_analytic_power_does_not_certify():
    # Analytic CI-low power ~0.91 here; the simulated studentized block bootstrap reached only 0.66.
    p = plan(effect__economic_min_net_effect=0.5, frequency={"events_per_year": 200, "window_years": 2})
    card = assess(p)
    assert card["status"] == "DATA_REQUIRED"
    assert "NO_SIMULATED_PR59_CELL_REACHES_TARGET_FOR_THIS_PLAN" in card["reasons"]
    assert "not used to certify" in card["numbers"]["indicative_analytic"]["note"]


# ---------- P1-5: winner's curse and MDE ----------

def test_p1_screening_estimate_requires_n_and_family():
    card = assess(plan(effect__screening={"estimate": 2.0}))
    assert card["status"] == "NOT_ASSESSABLE" and "SCREENING_ESTIMATE_INCOMPLETE" in card["reasons"]


def test_p1_curse_factor_not_transferred_to_other_family():
    scr = {"estimate": 2.0, "n": 47, "family_size": 21, "selection_rule": "BH_Q0.10"}
    card = assess(plan(effect__screening=scr))
    assert card["status"] == "NOT_ASSESSABLE"
    assert "WINNERS_CURSE_NOT_CALIBRATED_FOR_SCREENING_CONFIG" in card["reasons"]


def test_p1_three_effects_are_distinguished():
    scr = {"estimate": 0.9, "n": 47, "family_size": 67, "selection_rule": "BH_Q0.10"}
    p = plan(effect__unit="R", dispersion__unit="R", costs__unit="R", effect__economic_min_net_effect=0.3,
             dispersion__sigma_paired_difference=2.38, effect__screening=scr)
    n = assess(p)["numbers"]
    assert n["economic_min_net_effect"] == 0.3
    assert n["selection_corrected_effect"] == pytest.approx(0.9 / 3.845, abs=1e-3)
    assert n["effect_used_for_sizing"] == pytest.approx(min(0.3, 0.9 / 3.845), abs=1e-3)
    assert n["mde_of_screening_estimate_indicative"] > 0.9


# ---------- P1-6: inputs and domains ----------

@pytest.mark.parametrize("change", [
    {"alpha": 0}, {"alpha": float("nan")}, {"alpha": 1.5}, {"alpha": True}, {"alpha": None},
    {"power_target": 1.2}, {"effect__economic_min_net_effect": float("nan")},
    {"effect__economic_min_net_effect": -0.1}, {"dispersion__sigma_paired_difference": float("inf")},
    {"dispersion__sigma_paired_difference": 0}, {"frequency__events_per_year": 0.1, "frequency__window_years": 1},
    {"costs__stress": float("-inf")}, {"costs__base": 0.2, "costs__stress": 0.1},
    {"dispersion__unit": "R"}, {"costs__unit": DROP}, {"effect__unit": "pips"},
    {"purpose": DROP}, {"effect": DROP}, {"dispersion": DROP}, {"frequency": DROP}, {"dependence": DROP},
    {"costs": DROP}, {"datasets": DROP}, {"dispersion__control_reuse": DROP}, {"dependence__horizon_bars": DROP},
])
def test_p1_invalid_inputs_fail_closed_without_exceptions(change):
    card = assess(plan(**change))
    assert card["status"] == "NOT_ASSESSABLE" and card["reasons"]


def test_p1_not_a_mapping():
    assert G.assess(["not", "a", "plan"], cal=CAL, registry=REG)["status"] == "NOT_ASSESSABLE"


def test_p1_small_sample_below_25_is_not_ready():
    card = assess(plan(frequency={"events_per_year": 10, "window_years": 2}))
    assert card["status"] == "DATA_REQUIRED" and any(r.startswith("N_BELOW_METHOD_MINIMUM") for r in card["reasons"])


def test_p1_large_sample_only_by_dominance_with_warning():
    card = assess(plan(frequency={"events_per_year": 450, "window_years": 2}))
    assert card["status"] == "POWER_READY"
    assert any(w.startswith("N_ABOVE_SIMULATED_RANGE") for w in card["warnings"])


def test_p1_dispersion_above_calibration_not_ready():
    card = assess(plan(dispersion__sigma_paired_difference=6.0, frequency={"events_per_year": 200, "window_years": 2}))
    assert card["status"] == "DATA_REQUIRED"


# ---------- confirmatory multiplicity ----------

def test_conf_family_required():
    card = assess(plan(confirmation_family=DROP))
    assert card["status"] == "NOT_ASSESSABLE" and "CONFIRMATION_FAMILY_UNDECLARED" in card["reasons"]


def test_conf_family_alpha_split_is_not_full_alpha():
    card = assess(plan(confirmation_family__size=3))
    assert card["numbers"]["alpha_per_test"] == pytest.approx(0.05 / 3)
    assert card["status"] == "NOT_ASSESSABLE"
    assert any(r.startswith("ALPHA_PER_TEST_") for r in card["reasons"])


def test_conf_preregistration_must_verify():
    card = assess(plan(confirmation_family__preregistration_sha256="f" * 64))
    assert card["status"] == "NOT_ASSESSABLE"
    assert any(r.startswith("CONFIRMATION_PREREGISTRATION_UNVERIFIED") for r in card["reasons"])


def test_conf_fixed_sequence():
    first = assess(plan(confirmation_family__alpha_allocation="FIXED_SEQUENCE", confirmation_family__size=3,
                        confirmation_family__position=1))
    assert first["status"] == "POWER_READY"
    second = assess(plan(confirmation_family__alpha_allocation="FIXED_SEQUENCE", confirmation_family__size=3,
                         confirmation_family__position=2))
    assert second["status"] == "NOT_ASSESSABLE"


# ---------- screening and published case ----------

def test_screening_ceiling_and_family_alpha():
    base = plan(purpose="SCREENING", confirmation_family=DROP)
    assert assess(base)["status"] == "NOT_ASSESSABLE"
    one = copy.deepcopy(base); one["family_size"] = 1
    card = assess(one)
    assert card["status"] == "POWER_READY" and card["evidence_ceiling"] == "DISCOVERY_ONLY"
    many = copy.deepcopy(base); many["family_size"] = 21
    assert assess(many)["status"] == "NOT_ASSESSABLE"


def test_published_breakout_acc_confirmation_needs_new_data():
    p = plan(effect__unit="R", dispersion__unit="R", costs__unit="R", effect__economic_min_net_effect=0.3,
             dispersion__sigma_paired_difference=2.38, costs__stress=0.08,
             frequency={"events_per_year": 6.7, "window_years": 7.3},
             datasets=[{"dataset_id": "BREAKOUT_ACC::2019.02.21_2026.06.09", "split": "discovery"}])
    card = assess(p)
    assert card["status"] == "DATA_REQUIRED" and "CONFIRMATION_ON_EXPOSED_DATA" in card["reasons"]
    assert card["numbers"]["indicative_analytic"]["n_required"] > 900
    assert math.isfinite(card["numbers"]["indicative_analytic"]["mde_at_n_expected"])
