"""Power Gate V1 (rules V1.3): classification, fail-closed behaviour, PR #59 calibration,
and regressions for the three Codex reviews of PR #60.

With the real PR #59 calibration no plan can be POWER_READY (its protocol has no pre-registered
level qualification). Tests that exercise the later stages use QCAL: a HYPOTHETICAL calibration
that carries such a qualification and 4000 replications per null cell (same observed rates), i.e.
the evidence an independent study would have to supply. It never reaches production code.

Synthetic plans, two small synthetic fixtures (provenance manifest, preregistration) and
cases already published in the repository. No market data, no protected dataset, no
simulation re-run.
"""
from __future__ import annotations

import copy
import hashlib
import math
import subprocess
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
    sha, representation = G.artifact_sha256(str(ROOT / rel))
    assert representation in G.CANONICAL_REPRESENTATIONS, representation
    return sha


MANIFEST = f"{FIX}/forward_provenance_manifest.json"
PREREG = f"{FIX}/confirmation_preregistration.json"
PREREG_SEQ = f"{FIX}/confirmation_preregistration_sequence.json"
PROTOCOL = "SYNTH_CONFIRMATION_PROTOCOL_V1"
PROVENANCE = {"manifest_path": MANIFEST, "manifest_sha256": _sha(MANIFEST), "declared_at": "2026-10-18",
              "data_start": "2026-11-01", "data_end": "2028-10-31", "declared_before_collection": True}
# A synthetic registry entry standing in for a reviewed record of the canonical phase7_26 ledger.
SYNTH_RECORD = {"dataset_id": "SYNTH_FORWARD_2026Q4", "symbol": "GOLD", "timeframe": "D1",
                "date_range": ["2026.11.01", "2028.10.31"], "holdout_status": "NOT_USED",
                **{f: False for f in G.EXPOSURE_FLAGS}}
REG = {**REG, SYNTH_RECORD["dataset_id"]: SYNTH_RECORD}
FORWARD = {"dataset_id": "SYNTH_FORWARD_2026Q4", "split": "discovery", "symbol": "GOLD", "timeframe": "D1",
           "date_range": ["2026.11.01", "2028.10.31"]}

# Inside the one design PR #59 simulated: paired ATR difference vs one regime-matched control.
READY = {
    "experiment_id": "SYNTH_READY",
    "protocol_version": PROTOCOL,
    "purpose": "CONFIRMATION",
    "effect": {"economic_min_net_effect": 1.0, "unit": "ATR"},
    "dispersion": {"estimand": "PAIRED_DIFFERENCE_VS_BENCHMARK", "sigma_paired_difference": 3.2, "unit": "ATR",
                   "source": "OBSERVED", "controls_per_event": 1, "control_reuse": False},
    "frequency": {"events_per_year": 100, "window_years": 2},
    "dependence": {"structure": "INDEPENDENT", "horizon_bars": 10, "min_spacing_bars": 10},
    "costs": {"base": 0.0, "stress": 0.0, "unit": "ATR"},
    "benchmark": "REGIME_MATCHED",
    "inference_method": "STUDENTIZED_BLOCK_BOOTSTRAP",
    "test_sidedness": "TWO_SIDED",
    "datasets": [FORWARD],
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


LEVEL_QUALIFICATION = {"criterion": "WILSON_UPPER_BOUND_LE_NOMINAL", "multiplicity": "BONFERRONI_OVER_CELLS",
                       "nominal_alpha": 0.05, "confidence": 0.95, "min_reps_per_cell": 2000,
                       "frozen_before_results": True}


def _qualified(cal, reps=4000, lq=LEVEL_QUALIFICATION):
    q = copy.deepcopy(cal)
    q["level_qualification"] = lq
    for v in q["type1"].values():
        v["rejections"], v["reps"] = round(v["rate"] * reps), reps
    return q


QCAL = _qualified(CAL)


def assess(p, cal=None):
    return G.assess(p, cal=cal or QCAL, registry=REG)


# ---------- baseline and calibration ----------

def test_calibration_comes_from_pr59_results():
    assert CAL["source_sha256"] == "c538a5d2f3d65a42ac2f71bc52039e67636e9d16e25c6e443134f6e1732a05d4"
    assert CAL["winners_curse"]["inflation_by_screening_n"][47] == pytest.approx(3.845, abs=1e-3)
    assert CAL["source_integrity"] == "VERIFIED" and CAL["level_qualification"] is None
    assert CAL["qualified_ranges"]["G_U"]["n"] == [12, 400]


def test_ready_only_by_a_dominating_simulated_cell():
    card = assess(READY)
    assert card["status"] == "POWER_READY", card["reasons"]
    cell = card["numbers"]["dominating_pr59_cell"]
    assert cell["n"] <= 200 and cell["delta"] <= 1.0 and cell["sigma_d"] >= 3.2
    assert cell["power_lower_95_one_sided"] >= 0.8 and cell["power_mc_se"] > 0
    assert all(v["upper_bound_bonferroni"] <= 0.05
               for v in card["numbers"]["simulated_null_rejections_descriptive"].values())
    assert "not EDGE_VALIDATED" in card["not_an_authorization"]


def test_deterministic_card():
    assert assess(READY)["card_sha256"] == assess(READY)["card_sha256"]


# ---------- Review 2, P0: dataset provenance bound to identity, window, origin, exposure ----------

def test_r2_p0_unrelated_manifest_with_valid_hash_is_rejected():
    # Attack on 6a42669: any repo file with a matching hash (here the preregistration) passed as provenance.
    prov = {**PROVENANCE, "manifest_path": PREREG, "manifest_sha256": _sha(PREREG)}
    card = assess(plan(datasets=[{"dataset_id": "ANY_DATASET", "split": "discovery", "provenance": prov}]))
    assert card["status"] == "NOT_ASSESSABLE"
    assert any(r.startswith("PROVENANCE_MANIFEST_SELF_ATTESTED_NOT_ACCEPTED") for r in card["reasons"])


def test_r2_p0_even_a_pertinent_self_attested_manifest_is_not_proof():
    ds = {**FORWARD, "provenance": PROVENANCE}
    card = assess(plan(datasets=[ds]))
    assert card["status"] == "NOT_ASSESSABLE"


def test_p0_v1_ready_fixture_is_no_longer_ready():
    assert assess(V1_READY_FIXTURE)["status"] == "NOT_ASSESSABLE"


def test_p0_caller_declaration_alone_is_not_provenance():
    card = assess(plan(datasets=[{"dataset_id": "SYNTH_FORWARD_2027", "split": "discovery",
                                  "exposure": "UNSEEN_FORWARD"}]))
    assert card["status"] == "NOT_ASSESSABLE"
    assert any(r.startswith("DATASET_NOT_IN_EXPOSURE_REGISTRY") for r in card["reasons"])


@pytest.mark.parametrize("key,value", [("symbol", "XAUUSD"), ("timeframe", "H4"),
                                       ("date_range", ["2026.10.01", "2028.10.31"]), ("symbol", None)])
def test_r2_p0_registry_identity_must_match(key, value):
    card = assess(plan(datasets=[{**FORWARD, key: value}]))
    assert card["status"] == "NOT_ASSESSABLE"
    assert any(r.startswith(f"DATASET_IDENTITY_MISMATCH_WITH_REGISTRY:SYNTH_FORWARD_2026Q4:{key}")
               for r in card["reasons"])


def test_p0_exposed_registry_dataset_needs_new_data():
    card = assess(plan(datasets=[{"dataset_id": "BREAKOUT_ACC::2019.02.21_2026.06.09", "split": "discovery"}]))
    assert card["status"] == "DATA_REQUIRED" and "CONFIRMATION_ON_EXPOSED_DATA" in card["reasons"]


def test_p0_protected_split_blocked_without_opening_it():
    card = assess(plan(datasets=[{**FORWARD, "split": "final_holdout"}]))
    assert card["status"] == "METHOD_BLOCKED" and "PROTECTED_SPLIT:final_holdout" in card["reasons"]


def test_p0_repo_file_verification_refuses_data_and_holdout_paths():
    for path in ("server/data_cache/dukascopy_phaseH/manifest.json",
                 "server/research_scripts/phase7/final_holdout_seal_v1.json",
                 "server/research_scripts/phase7/phase7_9h/raw_data/nxs_d1_gold_phase79h.csv", "/etc/passwd",
                 "../outside.json"):
        assert G.verify_repo_file(path, "0" * 64)[0] is False


# ---------- Review 2, P1: preregistration semantics ----------

def test_r2_p1_unrelated_preregistration_with_valid_hash_is_blocked():
    # Attack on 6a42669: the provenance manifest (valid hash, wrong content) accepted as preregistration.
    card = assess(plan(confirmation_family__preregistration_path=MANIFEST,
                       confirmation_family__preregistration_sha256=_sha(MANIFEST)))
    assert card["status"] == "METHOD_BLOCKED"
    assert {"PREREGISTRATION_INCOMPATIBLE:experiment_id", "PREREGISTRATION_INCOMPATIBLE:protocol_version"} \
        <= set(card["reasons"])


@pytest.mark.parametrize("change,field", [
    ({"experiment_id": "SYNTH_OTHER"}, "experiment_id"),
    ({"protocol_version": "OTHER_PROTOCOL"}, "protocol_version"),
    ({"protocol_version": DROP}, "protocol_version"),
    ({"confirmation_family__size": 2}, "family_size"),
    ({"confirmation_family__alpha_allocation": "HOLM"}, "alpha_allocation"),
    ({"alpha": 0.04}, "alpha"),
])
def test_r2_p1_preregistration_must_match_the_plan(change, field):
    card = assess(plan(**change))
    assert card["status"] == "METHOD_BLOCKED" and f"PREREGISTRATION_INCOMPATIBLE:{field}" in card["reasons"]


def test_conf_preregistration_hash_must_verify():
    card = assess(plan(confirmation_family__preregistration_sha256="f" * 64))
    assert card["status"] == "NOT_ASSESSABLE"
    assert any(r.startswith("CONFIRMATION_PREREGISTRATION_UNVERIFIED") for r in card["reasons"])


def test_conf_family_required():
    card = assess(plan(confirmation_family=DROP))
    assert card["status"] == "NOT_ASSESSABLE" and "CONFIRMATION_FAMILY_UNDECLARED" in card["reasons"]


def _sequence(position, experiment_id="SYNTH_READY"):
    return plan(experiment_id=experiment_id,
                confirmation_family={"size": 3, "alpha_allocation": "FIXED_SEQUENCE", "position": position,
                                     "preregistration_path": PREREG_SEQ, "preregistration_sha256": _sha(PREREG_SEQ)})


def test_conf_fixed_sequence_position_is_checked_against_preregistration():
    assert assess(_sequence(1))["status"] == "POWER_READY"
    wrong = assess(_sequence(2))
    assert wrong["status"] == "METHOD_BLOCKED" and "PREREGISTRATION_INCOMPATIBLE:sequence_position" in wrong["reasons"]
    second = assess(_sequence(2, "SYNTH_SECOND"))
    assert second["status"] == "NOT_ASSESSABLE" and "FIXED_SEQUENCE_POWER_DEPENDS_ON_EARLIER_TESTS" in second["reasons"]


def test_conf_family_alpha_split_is_not_full_alpha():
    # A family of 3 would need a matching preregistration; with Bonferroni alpha/3 is below the simulated 0.05.
    prereg = {"experiment_ids": ["SYNTH_READY", "B", "C"]}
    assert len(prereg["experiment_ids"]) == 3
    card = assess(plan(confirmation_family__size=3))
    assert card["status"] == "METHOD_BLOCKED"  # the 1-member preregistration does not match size 3


# ---------- Review 2, P1: qualified range only, no dominance beyond n=400 ----------

def test_r2_p1_no_promotion_above_simulated_n():
    card = assess(plan(frequency={"events_per_year": 5000, "window_years": 2}))
    assert card["status"] == "NOT_ASSESSABLE" and "POWER_NOT_CALIBRATED_FOR_DESIGN" in card["reasons"]
    assert any(r.startswith("N_10000_OUTSIDE_SIMULATED") for r in card["reasons"])
    assert any("n up to 400" in e for e in card["numbers"]["evidence_needed"])


@pytest.mark.parametrize("change,prefix", [
    ({"effect__economic_min_net_effect": 2.0}, "EFFECT_2_OUTSIDE_SIMULATED"),
    ({"dispersion__sigma_paired_difference": 6.0}, "SIGMA_6_OUTSIDE_SIMULATED"),
    ({"dispersion__sigma_paired_difference": 1.0}, "SIGMA_1_OUTSIDE_SIMULATED"),
])
def test_r2_p1_effect_and_dispersion_must_be_inside_simulated_ranges(change, prefix):
    card = assess(plan(**change))
    assert card["status"] == "NOT_ASSESSABLE"
    assert any(r.startswith(prefix) for r in card["reasons"]) and card["numbers"]["evidence_needed"]


def test_p1_small_sample_below_25_is_not_ready():
    card = assess(plan(frequency={"events_per_year": 10, "window_years": 2}))
    assert card["status"] == "DATA_REQUIRED" and any(r.startswith("N_BELOW_METHOD_MINIMUM") for r in card["reasons"])


# ---------- Review 2, P1: statistical uncertainty and level control ----------

def test_r2_p1_point_power_above_target_is_not_enough():
    # HAC at n=100, delta 1.0: point power 0.82 but one-sided 95% Wilson lower bound < 0.80.
    cell = next(c for c in CAL["cells"] if c["gen"] == "G_U" and c["method"] == "HAC_NEWEY_WEST"
                and c["n"] == 100 and c["delta"] == 1.0)
    assert cell["power"] >= 0.8 > cell["power_lower_95_one_sided"]
    sigma = CAL["qualified_ranges"]["G_U"]["sigma_d"][0]
    assert G._dominating_cell(QCAL, "G_U", "HAC_NEWEY_WEST", 150, 1.0, sigma, 0.8) is None
    point_only = [c for c in QCAL["cells"] if c["gen"] == "G_U" and c["method"] == "HAC_NEWEY_WEST"
                  and c["n"] <= 150 and c["delta"] <= 1.0 and c["sigma_d"] >= sigma and c["power"] >= 0.8]
    assert point_only, "a point-estimate rule would have certified this plan"
    # Through assess() HAC is stopped even earlier: its null rejections fail the level criterion.
    card = assess(plan(inference_method="HAC_NEWEY_WEST", frequency={"events_per_year": 75, "window_years": 2},
                       dispersion__sigma_paired_difference=sigma))
    assert card["status"] in ("METHOD_BLOCKED", "DATA_REQUIRED")


def test_r2_p1_clustered_level_not_compatible_with_nominal_blocks():
    # Attack on 6a42669: clustered studentized block bootstrap promoted with point power 0.8225 and
    # null rejections 0.0725 at n=200 (Wilson 95% [0.051, 0.102] excludes 0.05).
    dep = {"structure": "CLUSTERED", "horizon_bars": 10, "min_spacing_bars": 2, "cluster_size": 4,
           "design_effect_basis": {"type": "PR59_CLUSTER_MODEL_MATCH"}}
    card = assess(plan(dependence=dep, dispersion__sigma_paired_difference=4.5))
    assert card["status"] == "METHOD_BLOCKED"
    assert "LEVEL_NOT_DEMONSTRATED_AT_NOMINAL" in card["reasons"]
    assert "G_C|STUDENTIZED_BLOCK_BOOTSTRAP|200" in card["reasons"]
    real = assess(plan(dependence=dep, dispersion__sigma_paired_difference=4.5), cal=CAL)
    assert real["status"] == "NOT_ASSESSABLE"


# ---------- Review 1 findings (kept) ----------

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
    assert code in card["reasons"] and card["numbers"]["evidence_needed"]


def test_p1_control_reuse_blocks():
    card = assess(plan(dispersion__control_reuse=True))
    assert card["status"] == "METHOD_BLOCKED" and "CONTROL_REUSE_NOT_MODELLED" in card["reasons"]


@pytest.mark.parametrize("bench,code", [(DROP, "BENCHMARK_MISSING"), ("ZERO", "BENCHMARK_ZERO_COUNTS_DRIFT_AS_EDGE"),
                                        ("UNCONDITIONAL", "BENCHMARK_CANNOT_SEPARATE_ALPHA_FROM_EXPOSURE")])
def test_p1_missing_or_inadequate_benchmark(bench, code):
    card = assess(plan(benchmark=bench))
    assert card["status"] == "METHOD_BLOCKED" and code in card["reasons"]


def test_p1_clustered_without_justified_deff_is_not_assessable():
    card = assess(plan(dependence={"structure": "CLUSTERED", "horizon_bars": 10, "min_spacing_bars": 2}))
    assert card["status"] == "NOT_ASSESSABLE" and "DESIGN_EFFECT_UNJUSTIFIED" in card["reasons"]
    other = assess(plan(dependence={"structure": "CLUSTERED", "horizon_bars": 10, "min_spacing_bars": 2,
                                    "cluster_size": 8, "design_effect_basis": {"type": "PR59_CLUSTER_MODEL_MATCH"}}))
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


def test_p1_analytic_power_does_not_certify():
    # Analytic CI-low power ~0.9 here; the simulated studentized block bootstrap reached only 0.66.
    p = plan(effect__economic_min_net_effect=0.5, frequency={"events_per_year": 200, "window_years": 2},
             dispersion__sigma_paired_difference=3.105)
    card = assess(p)
    assert card["status"] == "DATA_REQUIRED"
    assert "NO_SIMULATED_PR59_CELL_LOWER_POWER_BOUND_REACHES_TARGET" in card["reasons"]
    assert "not used to certify" in card["numbers"]["indicative_analytic"]["note"]


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


def test_r2_p0_traversed_window_with_all_flags_false_is_not_unseen():
    # Real registry record: every exposure flag false, but the window was traversed by a run (NO_EVENTS).
    rid = "BREAKOUT_ACC::2026.06.10_2026.08.14"
    rec = G.exposure_registry()[rid]
    assert not any(rec[f] for f in G.EXPOSURE_FLAGS)
    ds = {"dataset_id": rid, "split": "discovery", "symbol": "GOLD", "timeframe": "D1",
          "date_range": rec["date_range"]}
    card = G.assess(plan(datasets=[ds]), cal=CAL, registry=G.exposure_registry())
    assert card["status"] == "DATA_REQUIRED" and "CONFIRMATION_ON_EXPOSED_DATA" in card["reasons"]


def test_r2_p0_untouched_but_unverified_or_unknown_flags_is_not_proof():
    unverified = {**SYNTH_RECORD, "holdout_status": "UNVERIFIED - availability unknown"}
    card = G.assess(READY, cal=CAL, registry={**REG, SYNTH_RECORD["dataset_id"]: unverified})
    assert card["status"] == "NOT_ASSESSABLE" and any(r.startswith("DATASET_UNTOUCHED_STATUS_NOT_PROVEN")
                                                       for r in card["reasons"])
    unknown = {**SYNTH_RECORD, "oos_exposure": None}
    card = G.assess(READY, cal=CAL, registry={**REG, SYNTH_RECORD["dataset_id"]: unknown})
    assert card["status"] == "NOT_ASSESSABLE" and any(r.startswith("DATASET_EXPOSURE_FLAGS_UNKNOWN")
                                                       for r in card["reasons"])


def test_production_registry_has_no_unseen_dataset_today():
    # With the committed ledger no confirmation dataset qualifies as unseen until a forward one is registered.
    real = G.exposure_registry()
    for rid, rec in real.items():
        ds = {"dataset_id": rid, "symbol": rec.get("symbol"), "timeframe": rec.get("timeframe"),
              "date_range": rec.get("date_range")}
        assert G._dataset_status(ds, real)[0] != "VERIFIED_UNSEEN", rid


# ---------- Review 3, finding 1: alpha and test procedure must match the simulation exactly ----------

def test_r3_alpha_010_family_of_one_is_not_ready():
    # Attack on 6d49b6a: screening, family 1, alpha 0.10 -> alpha per test 0.10 >= 0.05 -> POWER_READY.
    p = plan(purpose="SCREENING", confirmation_family=DROP, alpha=0.10)
    p["family_size"] = 1
    card = assess(p)
    assert card["status"] == "NOT_ASSESSABLE"
    assert "ALPHA_PER_TEST_0.1_NOT_SIMULATED_0.05" in card["reasons"]
    assert any("exactly this alpha" in e for e in card["numbers"]["evidence_needed"])


def test_r3_alpha_005_family_of_one_reaches_level_stage():
    p = plan(purpose="SCREENING", confirmation_family=DROP)
    p["family_size"] = 1
    assert assess(p)["status"] == "POWER_READY"                      # hypothetical qualified level
    assert assess(p, cal=CAL)["status"] == "NOT_ASSESSABLE"           # real PR #59 calibration


@pytest.mark.parametrize("family,code", [(3, "ALPHA_PER_TEST_0.01667_NOT_SIMULATED_0.05"),
                                         (21, "ALPHA_PER_TEST_0.002381_NOT_SIMULATED_0.05")])
def test_r3_multiplicity_corrected_alpha_is_not_simulated(family, code):
    p = plan(purpose="SCREENING", confirmation_family=DROP)
    p["family_size"] = family
    card = assess(p)
    assert card["status"] == "NOT_ASSESSABLE" and code in card["reasons"]


@pytest.mark.parametrize("value,status", [("ONE_SIDED", "NOT_ASSESSABLE"), (DROP, "NOT_ASSESSABLE")])
def test_r3_test_sidedness_must_match(value, status):
    assert assess(plan(test_sidedness=value))["status"] == status


# ---------- Review 3, finding 2: level calibration must be pre-registered with MC uncertainty ----------

def test_r3_contains_005_rule_is_gone():
    # The M3 cell Codex cited: 19/400 = 0.0475, Wilson 95% [0.0306, 0.0730]; "contains 0.05" accepted it.
    t = CAL["type1"]["G_U|STUDENTIZED_BLOCK_BOOTSTRAP|25"]
    assert (t["rejections"], t["reps"]) == (19, 400)
    assert t["wilson95_descriptive"] == [0.0306, 0.073]
    assert "compatible_with_nominal" not in t


def test_r3_real_pr59_calibration_cannot_qualify_the_level():
    card = assess(READY, cal=CAL)
    assert card["status"] == "NOT_ASSESSABLE"
    assert card["reasons"] == ["LEVEL_CALIBRATION_NOT_PREREGISTERED", "CALIBRATION_PROTOCOL_HAS_NO_LEVEL_QUALIFICATION"]
    assert "pre-registered criterion" in card["numbers"]["evidence_needed"][0]


def test_r3_pr59_replications_fail_even_a_preregistered_criterion():
    # Applying the strict criterion to the real 400-replication counts (not a tolerance): it fails.
    card = assess(READY, cal=_qualified(CAL, reps=400, lq={**LEVEL_QUALIFICATION, "min_reps_per_cell": 400}))
    assert card["status"] == "METHOD_BLOCKED" and "LEVEL_NOT_DEMONSTRATED_AT_NOMINAL" in card["reasons"]


@pytest.mark.parametrize("lq", [
    {**LEVEL_QUALIFICATION, "frozen_before_results": False},
    {**LEVEL_QUALIFICATION, "criterion": "INTERVAL_CONTAINS_NOMINAL"},
    {**LEVEL_QUALIFICATION, "multiplicity": "NONE"},
    {**LEVEL_QUALIFICATION, "confidence": 0.5},
    {**LEVEL_QUALIFICATION, "nominal_alpha": 0.075},
    {**LEVEL_QUALIFICATION, "min_reps_per_cell": 0},
])
def test_r3_invalid_level_qualification_is_not_assessable(lq):
    card = assess(READY, cal=_qualified(CAL, lq=lq))
    assert card["status"] == "NOT_ASSESSABLE" and "LEVEL_CALIBRATION_NOT_PREREGISTERED" in card["reasons"]


def test_r3_cells_below_min_reps_fail():
    card = assess(READY, cal=_qualified(CAL, reps=1000))
    assert card["status"] == "METHOD_BLOCKED"


# ---------- Review 3, finding 3: integrity on canonical Git blob bytes ----------

def _git(cwd, *args):
    subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True)


def test_r3_pr59_artifact_hash_is_the_git_blob_hash():
    sha, rep = G.artifact_sha256(G.CALIBRATION_PATH)
    assert rep == "GIT_CANONICAL_EOL_NORMALIZED"
    assert sha == "c538a5d2f3d65a42ac2f71bc52039e67636e9d16e25c6e443134f6e1732a05d4"


def test_r3_crlf_checkout_keeps_the_canonical_hash(tmp_path):
    # Simulates a Windows CRLF checkout on any OS: the blob stays LF, the working file becomes CRLF.
    lf = b'{"a": 1,\n "b": 2}\n'
    (tmp_path / "artifact.json").write_bytes(lf)
    _git(tmp_path, "init", "-q")
    _git(tmp_path, "-c", "user.email=t@t", "-c", "user.name=t", "add", "artifact.json")
    _git(tmp_path, "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-qm", "x")
    (tmp_path / ".gitattributes").write_text("*.json text eol=crlf\n")
    (tmp_path / "artifact.json").unlink()
    _git(tmp_path, "checkout", "--", "artifact.json")
    physical = (tmp_path / "artifact.json").read_bytes()
    assert physical == lf.replace(b"\n", b"\r\n")
    sha, rep = G.artifact_sha256(str(tmp_path / "artifact.json"))
    assert rep == "GIT_CANONICAL_EOL_NORMALIZED" and sha == hashlib.sha256(lf).hexdigest()
    assert sha != hashlib.sha256(physical).hexdigest()


def test_r3_modified_content_changes_the_canonical_hash(tmp_path):
    (tmp_path / ".git").mkdir()
    (tmp_path / "a.json").write_bytes(b"{}\n")
    before = G.artifact_sha256(str(tmp_path / "a.json"))[0]
    (tmp_path / "a.json").write_bytes(b'{"tampered": true}\r\n')
    assert G.artifact_sha256(str(tmp_path / "a.json"))[0] != before


def test_r3_binary_attributed_files_are_hashed_as_is(tmp_path):
    # Frozen CRLF datasets are marked binary in the repo's .gitattributes: their CRLF bytes are the blob.
    (tmp_path / ".git").mkdir()
    (tmp_path / ".gitattributes").write_text("data/frozen.csv binary\n")
    (tmp_path / "data").mkdir()
    crlf = b"a,b\r\n1,2\r\n"
    (tmp_path / "data" / "frozen.csv").write_bytes(crlf)
    sha, rep = G.artifact_sha256(str(tmp_path / "data" / "frozen.csv"))
    assert rep == "GIT_CANONICAL_BINARY_AS_IS" and sha == hashlib.sha256(crlf).hexdigest()


def test_r3_repo_binary_attribute_respected_for_real_frozen_dataset():
    path = ROOT / "server/research_scripts/contextual_edge_phase1/macd_selection_manifest_v1.json"
    assert G.artifact_sha256(str(path))[1] == "GIT_CANONICAL_BINARY_AS_IS"


def test_r3_no_repository_is_not_a_versioned_attestation(tmp_path):
    (tmp_path / "x.json").write_bytes(b"{}")
    assert G.artifact_sha256(str(tmp_path / "x.json"))[1] == "PHYSICAL_BYTES_NO_GIT_REPO"


def test_r3_calibration_integrity_failure_is_not_assessable():
    broken = {**QCAL, "source_integrity": "FAILED:WORKTREE_DIFFERS_FROM_GIT_BLOB"}
    card = assess(READY, cal=broken)
    assert card["status"] == "NOT_ASSESSABLE"
    assert card["reasons"] == ["CALIBRATION_SOURCE_INTEGRITY_FAILED:WORKTREE_DIFFERS_FROM_GIT_BLOB"]


def test_r3_windows_crlf_copy_of_frozen_results_keeps_recorded_hash(tmp_path):
    # Windows checkout with core.autocrlf=true: same blob, CRLF working bytes, same attested hash.
    lf = Path(G.CALIBRATION_PATH).read_bytes()
    assert b"\r\n" not in lf
    (tmp_path / ".git").mkdir()
    (tmp_path / "results_v1.json").write_bytes(lf.replace(b"\n", b"\r\n"))
    sha, rep = G.artifact_sha256(str(tmp_path / "results_v1.json"))
    assert rep == "GIT_CANONICAL_EOL_NORMALIZED"
    assert sha == "c538a5d2f3d65a42ac2f71bc52039e67636e9d16e25c6e443134f6e1732a05d4"
    assert hashlib.sha256(lf.replace(b"\n", b"\r\n")).hexdigest() != sha
