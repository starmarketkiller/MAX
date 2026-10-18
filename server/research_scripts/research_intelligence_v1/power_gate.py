"""Power Gate V1: pre-experiment power assessment for NEXUS trading experiments.

Deterministic, stdlib only, no market data read. It composes what already exists:
- power.py for n_required / mde / power of the CI-low criterion;
- gates.protected_splits() for one-shot splits;
- review.MIN_CLOSED_FOR_FIRST_READ as the minimum effective sample;
- phase7_26 data_exposure_registry_v1.json for dataset exposure;
- edge_detection_capability_v1 (PR #59) frozen results to calibrate the analytic
  power (margin), the design effect of clustered events, the calibrated
  inference methods and the winner's-curse shrinkage of screening estimates.

The analytic number is a planning estimate, not a guarantee: the card reports
the calibration it was checked against and where it was extrapolated.
POWER_READY means "enough evidence to go to protocol review"; it never means
EDGE_VALIDATED and never authorizes execution. Nothing here writes to
ResearchMemory or any registry.
"""
from __future__ import annotations

import hashlib
import json
import math
import os

from . import gates, power
from .memory import canonical, sha256_text
from .review import MIN_CLOSED_FOR_FIRST_READ

RULES_VERSION = "POWER_GATE_RULES_V1"
HERE = os.path.dirname(os.path.abspath(__file__))
CALIBRATION_PATH = os.path.join(HERE, "..", "edge_detection_capability_v1", "results_v1.json")
EXPOSURE_REGISTRY_PATH = os.path.join(HERE, "..", "phase7", "phase7_26", "data_exposure_registry_v1.json")

STATUSES = ("POWER_READY", "EXPLORATORY_ONLY", "DATA_REQUIRED", "METHOD_BLOCKED", "NOT_ASSESSABLE")
PURPOSES = ("SCREENING", "CONFIRMATION")
UNITS = ("R", "ATR")
DEPENDENCE = ("INDEPENDENT", "CLUSTERED", "OVERLAPPING")
# Benchmarks able to separate a signal from directional exposure (PR #59, Phase 7.27).
BENCHMARKS_ALPHA = ("REGIME_MATCHED", "RANDOM_TIMESTAMP_MATCHED")
BENCHMARKS_KNOWN = BENCHMARKS_ALPHA + ("UNCONDITIONAL", "ZERO")
# PR #59 type-I results: IID bootstrap 0.17-0.29 under dependence; HAC 0.13-0.22 at n=12;
# block sign-flip has no power at n=12; studentized block bootstrap max 0.0725.
METHODS = {
    "STUDENTIZED_BLOCK_BOOTSTRAP": {"dependence_ok": True, "min_n": MIN_CLOSED_FOR_FIRST_READ},
    "BLOCK_SIGN_FLIP": {"dependence_ok": True, "min_n": 25},
    "HAC_NEWEY_WEST": {"dependence_ok": True, "min_n": 47},
    "IID_BOOTSTRAP": {"dependence_ok": False, "min_n": 47},
}
EFFECT_SOURCES = ("ECONOMIC_MINIMUM", "SCREENING_ESTIMATE", "PRIOR_LITERATURE")
EXPOSURE_FLAGS = ("development_exposure", "integrity_audit_exposure", "mechanism_discovery_exposure",
                  "visual_review_exposure", "optimization_exposure", "validation_exposure", "oos_exposure",
                  "forward_exposure")
UNSEEN_DECLARATIONS = ("UNSEEN_FORWARD", "UNSEEN_NEW_SOURCE")
UNKNOWN = (None, "", "UNKNOWN")


def _sha_file(path):
    with open(path, "rb") as handle:
        return hashlib.sha256(handle.read()).hexdigest()


def calibration():
    """Numbers derived from the frozen PR #59 results (read only)."""
    with open(CALIBRATION_PATH, encoding="utf-8") as handle:
        res = json.load(handle)
    sd = res["meta"]["trade_dist_sd"]
    over = 0.0
    for c in res["trade"]:
        if c["costR"] == 0 and c["deltaR"] > 0:
            analytic = power.power_ci_low_positive(c["deltaR"], sd[c["dist"]], c["n"])
            over = max(over, analytic - c["power_lower_ci_gt_0"])
    sig = {(c["gen"], c["n"]): c["sd_estimate"] for c in res["signal"]
           if c["delta_atr"] == 0 and c["cost_atr"] == 0}
    deff = max((sig[("G_C", n)] / sig[("G_U", n)]) ** 2 for g, n in sig if g == "G_C" and ("G_U", n) in sig)
    curse = {}
    for c in res["screen_confirm"]:
        if c["m_true"] and c["winners_curse_inflation_true_edges"]:
            curse[c["n"]] = c["winners_curse_inflation_true_edges"]
    return {"source": "server/research_scripts/edge_detection_capability_v1/results_v1.json",
            "source_sha256": _sha_file(CALIBRATION_PATH),
            "analytic_power_max_overestimate": round(over, 4),
            "clustered_design_effect": round(deff, 3),
            "winners_curse_inflation_by_n": dict(sorted(curse.items())),
            "calibrated_range": {"n": [25, 800], "sigma_r": [round(min(sd.values()), 3), round(max(sd.values()), 3)]}}


def exposure_registry():
    with open(EXPOSURE_REGISTRY_PATH, encoding="utf-8") as handle:
        doc = json.load(handle)
    payload = doc.get("payload", doc)
    return {r["dataset_id"]: r for r in payload["records"]}


def _dataset_exposure(ds, registry):
    """'EXPOSED', 'UNSEEN' or None (unknown -> fail closed)."""
    rec = registry.get(ds.get("dataset_id"))
    if rec is not None:
        return "EXPOSED" if any(rec.get(f) for f in EXPOSURE_FLAGS) else "UNSEEN"
    declared = ds.get("exposure")
    if declared in UNSEEN_DECLARATIONS:
        return "UNSEEN"
    if declared in ("EXPOSED", "DISCOVERY_REUSE"):
        return "EXPOSED"
    return None


def _inflation(curse, n_screen):
    """Winner's-curse factor for a screening estimate; never below the largest-n value measured."""
    if not curse:
        return None
    eligible = [k for k in curse if k >= n_screen]
    return curse[min(eligible)] if eligible else curse[max(curse)]


def assess(plan, *, cal=None, registry=None):
    """Return a Power Decision Card for a plan. Pure function of (plan, calibration, registry)."""
    cal = cal or calibration()
    registry = registry if registry is not None else exposure_registry()
    reasons, warnings = [], []

    def need(cond, code):
        if not cond:
            reasons.append(code)

    purpose = plan.get("purpose")
    eff = plan.get("effect") or {}
    disp = plan.get("dispersion") or {}
    freq = plan.get("frequency") or {}
    dep = plan.get("dependence") or {}
    costs = plan.get("costs") or {}
    bench = plan.get("benchmark")
    method = plan.get("inference_method")
    datasets = plan.get("datasets") or []
    target_power = plan.get("power_target", 0.8)
    alpha = plan.get("alpha", 0.05)

    # 1. Fundamentals: missing -> NOT_ASSESSABLE (fail closed).
    need(purpose in PURPOSES, "PURPOSE_UNKNOWN")
    need(isinstance(eff.get("min_net_effect"), (int, float)) and eff.get("unit") in UNITS, "EFFECT_UNKNOWN")
    need(eff.get("source") in EFFECT_SOURCES, "EFFECT_SOURCE_UNKNOWN")
    need(isinstance(disp.get("sigma"), (int, float)) and disp.get("sigma", 0) > 0, "DISPERSION_UNKNOWN")
    need(isinstance(freq.get("events_per_year"), (int, float)) and freq.get("events_per_year", 0) > 0
         and isinstance(freq.get("window_years"), (int, float)) and freq.get("window_years", 0) > 0,
         "FREQUENCY_OR_WINDOW_UNKNOWN")
    need(dep.get("structure") in DEPENDENCE, "DEPENDENCE_UNKNOWN")
    need(isinstance(costs.get("base"), (int, float)) and isinstance(costs.get("stress"), (int, float)),
         "COSTS_UNKNOWN")
    need(bool(datasets), "DATASETS_UNDECLARED")
    need(isinstance(target_power, (int, float)) and 0.5 <= target_power < 1, "POWER_TARGET_INVALID")
    exposures = [_dataset_exposure(ds, registry) for ds in datasets]
    need(all(e is not None for e in exposures), "DATASET_EXPOSURE_UNKNOWN")
    if purpose == "SCREENING":
        need(isinstance(plan.get("family_size"), int) and plan.get("family_size", 0) >= 1, "FAMILY_SIZE_UNKNOWN")
    if reasons:
        return _card(plan, "NOT_ASSESSABLE", reasons, warnings, {}, cal)

    # 2. Method: benchmark, inference vs dependence, protected splits -> METHOD_BLOCKED.
    if bench in UNKNOWN or bench not in BENCHMARKS_KNOWN:
        reasons.append("BENCHMARK_MISSING")
    elif bench == "ZERO":
        reasons.append("BENCHMARK_ZERO_COUNTS_DRIFT_AS_EDGE")
    elif bench == "UNCONDITIONAL" and purpose == "CONFIRMATION":
        reasons.append("BENCHMARK_CANNOT_SEPARATE_ALPHA_FROM_EXPOSURE")
    if method not in METHODS:
        reasons.append("INFERENCE_METHOD_UNKNOWN")
    elif dep["structure"] != "INDEPENDENT" and not METHODS[method]["dependence_ok"]:
        reasons.append("IID_INFERENCE_UNDER_DEPENDENCE")
    for ds in datasets:
        try:
            gates.assert_no_automatic_protected_access(ds.get("split"))
        except gates.GateViolation:
            reasons.append(f"PROTECTED_SPLIT:{ds.get('split')}")
    if reasons:
        return _card(plan, "METHOD_BLOCKED", reasons, warnings, {}, cal)

    # 3. Numbers (conservative choices throughout).
    effect = float(eff["min_net_effect"])
    stress_extra = max(0.0, float(costs["stress"]) - float(costs["base"]))
    effect_stress = effect - stress_extra
    inflation = None
    if eff["source"] == "SCREENING_ESTIMATE":
        inflation = _inflation(cal["winners_curse_inflation_by_n"], int(eff.get("screening_n") or 0))
        effect_stress = effect / inflation - stress_extra
    deff = 1.0
    if dep["structure"] != "INDEPENDENT":
        deff = max(float(dep.get("design_effect") or 0), cal["clustered_design_effect"])
    sigma = float(disp["sigma"])
    if disp.get("source") != "OBSERVED":
        warnings.append("DISPERSION_NOT_OBSERVED: sigma is a prior; re-assess when the strategy's own outcomes exist")
    n_expected = int(freq["events_per_year"] * freq["window_years"])
    n_eff = n_expected / deff
    alpha_eff = alpha / plan["family_size"] if purpose == "SCREENING" else alpha
    margin = cal["analytic_power_max_overestimate"]
    n_req = power.n_required(effect_stress, sigma, deff=deff, alpha_two_sided=alpha_eff,
                             power=min(0.999, target_power + margin)) if effect_stress > 0 else math.inf
    power_at_n = power.power_ci_low_positive(effect_stress, sigma, n_expected, deff=deff,
                                             z=power.ND.inv_cdf(1 - alpha_eff / 2)) if effect_stress > 0 else 0.0
    mde_at_n = power.mde(n_expected, sigma, deff=deff, alpha_two_sided=alpha_eff, power=target_power) + stress_extra
    lo, hi = cal["calibrated_range"]["sigma_r"]
    if eff["unit"] != "R" or not (0.5 * lo <= sigma <= 1.5 * hi) or n_expected < cal["calibrated_range"]["n"][0]:
        warnings.append("OUTSIDE_PR59_CALIBRATED_RANGE: analytic power extrapolated")
    if method == "IID_BOOTSTRAP" and dep["structure"] == "INDEPENDENT":
        warnings.append("IID_BOOTSTRAP_REQUIRES_DEMONSTRATED_INDEPENDENCE")
    numbers = {"effect_declared": effect, "effect_used_after_stress_and_shrinkage": round(effect_stress, 4),
               "winners_curse_inflation_applied": inflation, "sigma": sigma, "design_effect": round(deff, 3),
               "n_expected": n_expected, "n_effective": round(n_eff, 1), "alpha_per_test": alpha_eff,
               "power_target": target_power, "analytic_margin_added": margin,
               "n_required": None if math.isinf(n_req) else n_req,
               "analytic_power_at_n_expected": round(power_at_n, 3), "mde_at_n_expected": round(mde_at_n, 4),
               "years_required_at_frequency": None if math.isinf(n_req) else
               round(n_req / freq["events_per_year"], 1)}

    # 4. Classification.
    exposed = any(e == "EXPOSED" for e in exposures)
    min_n = max(MIN_CLOSED_FOR_FIRST_READ, METHODS[method]["min_n"])
    powered = (effect_stress > 0 and n_expected >= n_req and n_eff >= MIN_CLOSED_FOR_FIRST_READ
               and n_expected >= min_n)
    if effect_stress <= 0:
        reasons.append("EFFECT_DOES_NOT_SURVIVE_STRESS_COSTS_OR_SHRINKAGE")
    if n_expected < min_n:
        reasons.append(f"N_BELOW_METHOD_MINIMUM:{min_n}")
    if not powered and effect_stress > 0:
        reasons.append("UNDERPOWERED_AT_EXPECTED_N" if purpose == "CONFIRMATION"
                       else "SCREENING_UNDERPOWERED_AT_FAMILY_ALPHA")
    if purpose == "CONFIRMATION" and exposed:
        reasons.append("CONFIRMATION_ON_EXPOSED_DATA")
        status = "DATA_REQUIRED"
    elif purpose == "CONFIRMATION":
        status = "POWER_READY" if powered else ("DATA_REQUIRED" if effect_stress > 0 else "EXPLORATORY_ONLY")
    else:
        status = "POWER_READY" if powered else "EXPLORATORY_ONLY"
    return _card(plan, status, reasons, warnings, numbers, cal)


def _card(plan, status, reasons, warnings, numbers, cal):
    evidence_ceiling = {"POWER_READY": "DISCOVERY_ONLY" if plan.get("purpose") == "SCREENING"
                        else "INTERNAL_VALIDATION (after protocol review)",
                        "EXPLORATORY_ONLY": "EXPLORATORY", "DATA_REQUIRED": "EXPLORATORY",
                        "METHOD_BLOCKED": "NONE", "NOT_ASSESSABLE": "NONE"}[status]
    card = {"rules_version": RULES_VERSION, "experiment_id": plan.get("experiment_id"),
            "purpose": plan.get("purpose"), "status": status, "reasons": reasons, "warnings": warnings,
            "numbers": numbers, "evidence_ceiling": evidence_ceiling,
            "not_an_authorization": "POWER_READY is not EDGE_VALIDATED and does not authorize execution, "
                                    "holdout access, deploy or trading.",
            "calibration": cal, "plan_sha256": sha256_text(canonical(plan))}
    card["card_sha256"] = sha256_text(canonical(card))
    return card


if __name__ == "__main__":
    import sys
    with open(sys.argv[1], encoding="utf-8") as fh:
        print(json.dumps(assess(json.load(fh)), indent=1))
