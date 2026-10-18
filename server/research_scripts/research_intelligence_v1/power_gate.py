"""Power Gate V1: pre-experiment power assessment for NEXUS trading experiments.

Deterministic, stdlib only. It reads no market data and no protected dataset: the
only files it opens are the frozen PR #59 results, the phase7_26 exposure registry
and small repo-relative manifests/preregistrations whose SHA-256 the plan declares.

It composes what already exists:
- power.py for the indicative analytic n_required / mde (never used to certify);
- gates.protected_splits() for one-shot splits;
- review.MIN_CLOSED_FOR_FIRST_READ as the minimum closed sample;
- phase7_26 data_exposure_registry_v1.json for dataset exposure;
- edge_detection_capability_v1 (PR #59) frozen results as the ONLY source that can
  certify power: POWER_READY requires a simulated PR #59 cell that dominates the
  plan (same estimand, benchmark, method and dependence model; smaller or equal n
  and effect; larger or equal dispersion; same or larger alpha) and reached the
  target power. Anything PR #59 did not study is NOT_ASSESSABLE, never extrapolated.

POWER_READY means "enough evidence to go to protocol review"; it never means
EDGE_VALIDATED and never authorizes execution. Nothing here writes to
ResearchMemory or any registry.
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import re

from . import gates, power
from .memory import canonical, sha256_text
from .review import MIN_CLOSED_FOR_FIRST_READ

RULES_VERSION = "POWER_GATE_RULES_V1.1"
HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
CALIBRATION_PATH = os.path.join(HERE, "..", "edge_detection_capability_v1", "results_v1.json")
EXPOSURE_REGISTRY_PATH = os.path.join(HERE, "..", "phase7", "phase7_26", "data_exposure_registry_v1.json")

STATUSES = ("POWER_READY", "EXPLORATORY_ONLY", "DATA_REQUIRED", "METHOD_BLOCKED", "NOT_ASSESSABLE")
PURPOSES = ("SCREENING", "CONFIRMATION")
UNITS = ("R", "ATR")
DEPENDENCE = ("INDEPENDENT", "CLUSTERED", "OVERLAPPING")
ESTIMANDS = ("PAIRED_DIFFERENCE_VS_BENCHMARK",)
BENCHMARKS_KNOWN = ("REGIME_MATCHED", "RANDOM_TIMESTAMP_MATCHED", "UNCONDITIONAL", "ZERO")
SOURCES = ("OBSERVED", "PRIOR")
ALLOCATIONS = ("BONFERRONI", "HOLM", "FIXED_SEQUENCE")
# Methods and their PR #59 column; minimum n from PR #59 (sign-flip no power at 12, HAC liberal at 12).
METHODS = {
    "STUDENTIZED_BLOCK_BOOTSTRAP": {"col": "M3", "dependence_ok": True, "min_n": MIN_CLOSED_FOR_FIRST_READ},
    "BLOCK_SIGN_FLIP": {"col": "M2", "dependence_ok": True, "min_n": 25},
    "HAC_NEWEY_WEST": {"col": "M4", "dependence_ok": True, "min_n": 47},
    "IID_BOOTSTRAP": {"col": "M1", "dependence_ok": False, "min_n": 47},
}
EXPOSURE_FLAGS = ("development_exposure", "integrity_audit_exposure", "mechanism_discovery_exposure",
                  "visual_review_exposure", "optimization_exposure", "validation_exposure", "oos_exposure",
                  "forward_exposure")
# The one design PR #59 simulated with a benchmark: paired ATR difference vs one regime-matched control,
# 10-bar outcome, no control reuse, alpha 0.05 two-sided. G_U = independent events; G_C = clusters of
# 4 events 2 bars apart (overlapping 10-bar windows).
CALIBRATED_DESIGN = {"unit": "ATR", "estimand": "PAIRED_DIFFERENCE_VS_BENCHMARK", "benchmark": "REGIME_MATCHED",
                     "controls_per_event": 1, "control_reuse": False, "alpha": 0.05,
                     "pr59_cluster_model": {"cluster_size": 4, "spacing_bars": 2, "horizon_bars": 10}}
# The one screening configuration PR #59 simulated (winner's curse): R units, 67 candidates, BH q=0.10.
CURSE_CONFIG = {"unit": "R", "family_size": 67, "selection_rule": "BH_Q0.10"}
MAX_MANIFEST_BYTES = 1_000_000
FORBIDDEN_PATH = re.compile(r"(^|/)(data_cache|raw_data)(/|$)|holdout|\.(csv|parquet|bin|zip|gz)$", re.I)


def _sha_file(path):
    with open(path, "rb") as handle:
        return hashlib.sha256(handle.read()).hexdigest()


def _num(x, *, lo=None, hi=None, lo_open=False):
    """A finite real number (not bool) inside the domain, else None."""
    if isinstance(x, bool) or not isinstance(x, (int, float)) or not math.isfinite(x):
        return None
    if lo is not None and (x < lo or (lo_open and x == lo)):
        return None
    if hi is not None and x > hi:
        return None
    return float(x)


def calibration():
    """PR #59 frozen results reduced to what the gate may use (read only)."""
    with open(CALIBRATION_PATH, encoding="utf-8") as handle:
        res = json.load(handle)
    sig = [c for c in res["signal"] if c["cost_atr"] == 0 and c["gen"] in ("G_U", "G_C")]
    sigma_d = {(c["gen"], c["n"]): c["sd_estimate"] * math.sqrt(c["n"]) for c in sig if c["delta_atr"] == 0}
    cells = []
    for c in sig:
        if c["delta_atr"] > 0:
            for method, spec in METHODS.items():
                cells.append({"gen": c["gen"], "n": c["n"], "delta": c["delta_atr"], "method": method,
                              "power": c["rejection_rate"][spec["col"]], "sigma_d": round(sigma_d[(c["gen"], c["n"])], 4)})
    type1 = {}
    for c in sig:
        if c["delta_atr"] == 0:
            for method, spec in METHODS.items():
                type1[(c["gen"], method)] = max(type1.get((c["gen"], method), 0), c["rejection_rate"][spec["col"]])
    sd = res["meta"]["trade_dist_sd"]
    over = {}
    for c in res["trade"]:
        if c["costR"] == 0 and c["deltaR"] > 0:
            a = power.power_ci_low_positive(c["deltaR"], sd[c["dist"]], c["n"])
            over["trade_R_vs_zero"] = max(over.get("trade_R_vs_zero", 0.0), a - c["power_lower_ci_gt_0"])
    for c in cells:
        a = power.power_ci_low_positive(c["delta"], c["sigma_d"], c["n"])
        key = f"signal_paired_{c['gen']}_{c['method']}"
        over[key] = max(over.get(key, -1.0), a - c["power"])
    curse = {c["n"]: c["winners_curse_inflation_true_edges"] for c in res["screen_confirm"]
             if c["m_true"] and c["winners_curse_inflation_true_edges"]}
    return {"source": "server/research_scripts/edge_detection_capability_v1/results_v1.json",
            "source_sha256": _sha_file(CALIBRATION_PATH), "design": CALIBRATED_DESIGN, "cells": cells,
            "type1_max": {f"{g}|{m}": v for (g, m), v in sorted(type1.items())},
            "analytic_minus_simulated_power_max": {k: round(v, 4) for k, v in sorted(over.items())},
            "analytic_note": "empirical maxima over the studied cells only; not a bound and never used to certify",
            "winners_curse": {"config": CURSE_CONFIG, "inflation_by_screening_n": dict(sorted(curse.items()))}}


def exposure_registry():
    with open(EXPOSURE_REGISTRY_PATH, encoding="utf-8") as handle:
        doc = json.load(handle)
    payload = doc.get("payload", doc)
    return {r["dataset_id"]: r for r in payload["records"]}


def verify_repo_file(rel_path, declared_sha256):
    """Hash a small repo-relative manifest/preregistration. Never opens data or holdout paths."""
    if not isinstance(rel_path, str) or not isinstance(declared_sha256, str) or os.path.isabs(rel_path):
        return False, "PATH_OR_HASH_INVALID"
    norm = os.path.normpath(rel_path).replace(os.sep, "/")
    if norm.startswith("..") or FORBIDDEN_PATH.search(norm):
        return False, "PATH_NOT_ALLOWED"
    full = os.path.join(REPO_ROOT, norm)
    if not os.path.isfile(full):
        return False, "FILE_NOT_FOUND"
    if os.path.getsize(full) > MAX_MANIFEST_BYTES:
        return False, "FILE_TOO_LARGE_FOR_A_MANIFEST"
    return (_sha_file(full) == declared_sha256.lower()), "SHA256_MISMATCH"


def _dataset_status(ds, registry, purpose):
    """Return (status, reason). status: EXPOSED, VERIFIED_UNSEEN, or None (cannot be verified)."""
    rec = registry.get(ds.get("dataset_id"))
    if rec is not None:
        return ("EXPOSED", "") if any(rec.get(f) for f in EXPOSURE_FLAGS) else ("VERIFIED_UNSEEN", "")
    if ds.get("exposure") == "EXPOSED":
        return "EXPOSED", ""
    prov = ds.get("provenance")
    if not isinstance(prov, dict):
        return None, f"DATASET_PROVENANCE_UNVERIFIED:{ds.get('dataset_id')}"
    ok, why = verify_repo_file(prov.get("manifest_path"), prov.get("manifest_sha256"))
    if not ok:
        return None, f"DATASET_PROVENANCE_UNVERIFIED:{ds.get('dataset_id')}:{why}"
    dates = [prov.get(k) for k in ("declared_at", "data_start", "data_end")]
    if not all(isinstance(d, str) and re.fullmatch(r"\d{4}-\d{2}-\d{2}", d) for d in dates) or \
            not (dates[0] < dates[1] <= dates[2]) or prov.get("declared_before_collection") is not True:
        return None, f"DATASET_INDEPENDENCE_UNPROVEN:{ds.get('dataset_id')}"
    return "VERIFIED_UNSEEN", ""


def _dominating_cell(cal, gen, method, n, effect, sigma, target):
    best = None
    for c in cal["cells"]:
        if c["gen"] == gen and c["method"] == method and c["n"] <= n and c["delta"] <= effect \
                and c["sigma_d"] >= sigma and c["power"] >= target:
            if best is None or (c["n"], c["delta"]) > (best["n"], best["delta"]):
                best = c
    return best


def assess(plan, *, cal=None, registry=None):
    """Return a Power Decision Card. Pure function of (plan, calibration, registry, declared repo files)."""
    cal = cal or calibration()
    registry = registry if registry is not None else exposure_registry()
    reasons, warnings = [], []
    if not isinstance(plan, dict):
        return _card({}, "NOT_ASSESSABLE", ["PLAN_NOT_A_MAPPING"], [], {}, cal)

    def need(value, code):
        if value is None or value is False:
            reasons.append(code)
        return value

    purpose = plan.get("purpose")
    eff = plan.get("effect") if isinstance(plan.get("effect"), dict) else {}
    disp = plan.get("dispersion") if isinstance(plan.get("dispersion"), dict) else {}
    freq = plan.get("frequency") if isinstance(plan.get("frequency"), dict) else {}
    dep = plan.get("dependence") if isinstance(plan.get("dependence"), dict) else {}
    costs = plan.get("costs") if isinstance(plan.get("costs"), dict) else {}
    datasets = plan.get("datasets") if isinstance(plan.get("datasets"), list) else []

    # 1. Fundamentals and domains: anything missing, non-finite or incoherent -> NOT_ASSESSABLE.
    need(purpose in PURPOSES or None, "PURPOSE_UNKNOWN")
    econ = need(_num(eff.get("economic_min_net_effect"), lo=0, lo_open=True), "ECONOMIC_MIN_EFFECT_INVALID")
    unit = eff.get("unit")
    need(unit in UNITS or None, "EFFECT_UNIT_INVALID")
    need(disp.get("estimand") in ESTIMANDS or None, "ESTIMAND_NOT_PAIRED_DIFFERENCE_VS_BENCHMARK")
    sigma = need(_num(disp.get("sigma_paired_difference"), lo=0, lo_open=True), "PAIRED_DIFFERENCE_SIGMA_INVALID")
    need(disp.get("source") in SOURCES or None, "DISPERSION_SOURCE_UNKNOWN")
    k_ctl = disp.get("controls_per_event")
    need((isinstance(k_ctl, int) and not isinstance(k_ctl, bool) and k_ctl >= 1) or None, "CONTROLS_PER_EVENT_INVALID")
    need(isinstance(disp.get("control_reuse"), bool) or None, "CONTROL_REUSE_UNDECLARED")
    epy = need(_num(freq.get("events_per_year"), lo=0, lo_open=True), "EVENTS_PER_YEAR_INVALID")
    yrs = need(_num(freq.get("window_years"), lo=0, lo_open=True), "WINDOW_YEARS_INVALID")
    base = need(_num(costs.get("base"), lo=0), "COST_BASE_INVALID")
    stress = need(_num(costs.get("stress"), lo=0), "COST_STRESS_INVALID")
    if base is not None and stress is not None and stress < base:
        reasons.append("COST_STRESS_BELOW_BASE")
    if unit in UNITS and (disp.get("unit") != unit or costs.get("unit") != unit):
        reasons.append("UNITS_INCOHERENT")
    alpha = need(_num(plan.get("alpha", 0.05), lo=0, hi=0.5, lo_open=True), "ALPHA_INVALID")
    target = need(_num(plan.get("power_target", 0.8), lo=0.5, hi=0.99), "POWER_TARGET_INVALID")
    need(dep.get("structure") in DEPENDENCE or None, "DEPENDENCE_UNKNOWN")
    horizon = need(_num(dep.get("horizon_bars"), lo=1), "HORIZON_BARS_INVALID")
    spacing = need(_num(dep.get("min_spacing_bars"), lo=0), "MIN_SPACING_BARS_INVALID")
    need(bool(datasets) or None, "DATASETS_UNDECLARED")
    n_expected = None
    if epy is not None and yrs is not None:
        n_expected = epy * yrs
        if n_expected < 1:
            reasons.append("N_EXPECTED_BELOW_ONE")
    statuses = []
    for ds in datasets:
        st, why = _dataset_status(ds if isinstance(ds, dict) else {}, registry, purpose)
        statuses.append(st)
        if st is None:
            reasons.append(why)
    family = plan.get("family_size")
    if purpose == "SCREENING":
        need((isinstance(family, int) and not isinstance(family, bool) and family >= 1) or None, "FAMILY_SIZE_INVALID")
    cfam = plan.get("confirmation_family") if isinstance(plan.get("confirmation_family"), dict) else None
    if purpose == "CONFIRMATION":
        if cfam is None:
            reasons.append("CONFIRMATION_FAMILY_UNDECLARED")
        else:
            size = cfam.get("size")
            need((isinstance(size, int) and not isinstance(size, bool) and size >= 1) or None,
                 "CONFIRMATION_FAMILY_SIZE_INVALID")
            need(cfam.get("alpha_allocation") in ALLOCATIONS or None, "CONFIRMATION_ALPHA_ALLOCATION_INVALID")
            ok, why = verify_repo_file(cfam.get("preregistration_path"), cfam.get("preregistration_sha256"))
            if not ok:
                reasons.append(f"CONFIRMATION_PREREGISTRATION_UNVERIFIED:{why}")
    scr = eff.get("screening")
    if scr is not None:
        if not isinstance(scr, dict) or _num(scr.get("estimate"), lo=0, lo_open=True) is None \
                or not isinstance(scr.get("n"), int) or isinstance(scr.get("n"), bool) or scr.get("n", 0) < 1 \
                or not isinstance(scr.get("family_size"), int) or isinstance(scr.get("family_size"), bool) \
                or scr.get("family_size", 0) < 1 or not scr.get("selection_rule"):
            reasons.append("SCREENING_ESTIMATE_INCOMPLETE")
    if reasons:
        return _card(plan, "NOT_ASSESSABLE", reasons, warnings, {}, cal)

    # 2. Method: benchmark, inference vs dependence, declared structure vs geometry, protected splits.
    bench, method = plan.get("benchmark"), plan.get("inference_method")
    if bench not in BENCHMARKS_KNOWN:
        reasons.append("BENCHMARK_MISSING")
    elif bench == "ZERO":
        reasons.append("BENCHMARK_ZERO_COUNTS_DRIFT_AS_EDGE")
    elif bench == "UNCONDITIONAL" and purpose == "CONFIRMATION":
        reasons.append("BENCHMARK_CANNOT_SEPARATE_ALPHA_FROM_EXPOSURE")
    overlapping = spacing < horizon
    if dep["structure"] == "INDEPENDENT" and overlapping:
        reasons.append("DECLARED_INDEPENDENT_BUT_OUTCOME_WINDOWS_OVERLAP")
    if method not in METHODS:
        reasons.append("INFERENCE_METHOD_UNKNOWN")
    elif (dep["structure"] != "INDEPENDENT" or overlapping) and not METHODS[method]["dependence_ok"]:
        reasons.append("IID_INFERENCE_UNDER_DEPENDENCE")
    if disp["control_reuse"]:
        reasons.append("CONTROL_REUSE_NOT_MODELLED")
    for ds in datasets:
        try:
            gates.assert_no_automatic_protected_access(ds.get("split"))
        except gates.GateViolation:
            reasons.append(f"PROTECTED_SPLIT:{ds.get('split')}")
    if reasons:
        return _card(plan, "METHOD_BLOCKED", reasons, warnings, {}, cal)

    # 3. Effects: economic minimum, selection-corrected screening estimate, MDE of the screening.
    stress_extra = stress - base
    numbers = {"n_expected": round(n_expected, 1), "sigma_paired_difference": sigma, "unit": unit,
               "economic_min_net_effect": econ, "stress_cost_extra": stress_extra}
    effect_sizing = econ - stress_extra
    if scr is not None:
        curse = cal["winners_curse"]
        factor = None
        if unit == curse["config"]["unit"] and scr["family_size"] == curse["config"]["family_size"] \
                and scr["selection_rule"] == curse["config"]["selection_rule"]:
            factor = curse["inflation_by_screening_n"].get(scr["n"])
        if factor is None:
            reasons.append("WINNERS_CURSE_NOT_CALIBRATED_FOR_SCREENING_CONFIG")
        else:
            corrected = scr["estimate"] / factor
            numbers["screening_estimate"] = scr["estimate"]
            numbers["selection_corrected_effect"] = round(corrected, 4)
            numbers["winners_curse_inflation"] = factor
            effect_sizing = min(econ, corrected) - stress_extra
        numbers["mde_of_screening_estimate_indicative"] = round(power.mde(
            scr["n"], sigma, alpha_two_sided=alpha / scr["family_size"], power=target), 4)
    numbers["effect_used_for_sizing"] = round(effect_sizing, 4)

    # 4. Alpha per test (screening family, preregistered confirmation family).
    if purpose == "SCREENING":
        alpha_test = alpha / family
    elif cfam["alpha_allocation"] in ("BONFERRONI", "HOLM"):
        alpha_test = alpha / cfam["size"]  # Holm's first step is the binding one for planning
    else:
        pos = cfam.get("position")
        if not (isinstance(pos, int) and not isinstance(pos, bool) and 1 <= pos <= cfam["size"]):
            reasons.append("FIXED_SEQUENCE_POSITION_INVALID")
        elif pos > 1:
            reasons.append("FIXED_SEQUENCE_POWER_DEPENDS_ON_EARLIER_TESTS")
        alpha_test = alpha
    numbers["alpha_per_test"] = alpha_test

    # Indicative analytic numbers (never certify).
    deff_decl = _num(dep.get("design_effect"), lo=1)
    deff_ind = deff_decl or 1.0
    if effect_sizing > 0:
        numbers["indicative_analytic"] = {
            "n_required": power.n_required(effect_sizing, sigma, deff=deff_ind, alpha_two_sided=alpha_test,
                                           power=target),
            "mde_at_n_expected": round(power.mde(n_expected, sigma, deff=deff_ind, alpha_two_sided=alpha_test,
                                                 power=target), 4),
            "note": "analytic CI-low approximation; overstates block-method power by up to "
                    f"{max(v for k, v in cal['analytic_minus_simulated_power_max'].items() if k.startswith('signal')):.3f} "
                    "in PR #59 cells; not used to certify"}

    # 5. Dataset exposure.
    exposed = any(s == "EXPOSED" for s in statuses)
    if purpose == "CONFIRMATION" and exposed:
        reasons.append("CONFIRMATION_ON_EXPOSED_DATA")
    if effect_sizing <= 0:
        reasons.append("EFFECT_DOES_NOT_SURVIVE_STRESS_COSTS_OR_SELECTION_CORRECTION")
    min_n = max(MIN_CLOSED_FOR_FIRST_READ, METHODS[method]["min_n"])
    if n_expected < min_n:
        reasons.append(f"N_BELOW_METHOD_MINIMUM:{min_n}")
    if reasons:
        status = "DATA_REQUIRED" if purpose == "CONFIRMATION" and effect_sizing > 0 and \
            not any(r.startswith(("WINNERS_CURSE", "FIXED_SEQUENCE")) for r in reasons) else "EXPLORATORY_ONLY"
        if any(r.startswith(("WINNERS_CURSE", "FIXED_SEQUENCE")) for r in reasons):
            status = "NOT_ASSESSABLE"
        return _card(plan, status, reasons, warnings, numbers, cal)

    # 6. Certification: only a dominating simulated PR #59 cell can make the plan POWER_READY.
    d = cal["design"]
    gen, uncalibrated = None, []
    if unit != d["unit"]:
        uncalibrated.append(f"UNIT_{unit}_NOT_SIMULATED_WITH_A_BENCHMARK")
    if bench != d["benchmark"]:
        uncalibrated.append(f"BENCHMARK_{bench}_NOT_SIMULATED")
    if disp["controls_per_event"] != d["controls_per_event"]:
        uncalibrated.append("CONTROLS_PER_EVENT_NOT_SIMULATED")
    if alpha_test < d["alpha"]:
        uncalibrated.append(f"ALPHA_PER_TEST_{alpha_test:.4g}_BELOW_SIMULATED_{d['alpha']}")
    if dep["structure"] == "INDEPENDENT":
        gen = "G_U"
    else:
        basis = dep.get("design_effect_basis") if isinstance(dep.get("design_effect_basis"), dict) else {}
        model = d["pr59_cluster_model"]
        if basis.get("type") == "PR59_CLUSTER_MODEL_MATCH" and dep.get("cluster_size") == model["cluster_size"] \
                and spacing == model["spacing_bars"] and horizon == model["horizon_bars"]:
            gen = "G_C"
        elif basis.get("type") in ("MEASURED_ON_PLAN_DATA", "SIMULATED_FOR_PLAN") and deff_decl:
            ok, why = verify_repo_file(basis.get("source_path"), basis.get("source_sha256"))
            if not ok:
                reasons.append(f"DESIGN_EFFECT_SOURCE_UNVERIFIED:{why}")
            uncalibrated.append("PLAN_SPECIFIC_DEPENDENCE_NOT_SIMULATED_IN_PR59")
        else:
            reasons.append("DESIGN_EFFECT_UNJUSTIFIED")
    if reasons:
        return _card(plan, "NOT_ASSESSABLE", reasons, warnings, numbers, cal)
    if uncalibrated:
        return _card(plan, "NOT_ASSESSABLE", ["POWER_NOT_CALIBRATED_FOR_DESIGN", *uncalibrated], warnings,
                     numbers, cal)
    cell = _dominating_cell(cal, gen, method, n_expected, effect_sizing, sigma, target)
    numbers["dominating_pr59_cell"] = cell
    if cell is None:
        reasons.append("NO_SIMULATED_PR59_CELL_REACHES_TARGET_FOR_THIS_PLAN")
        status = "DATA_REQUIRED" if purpose == "CONFIRMATION" else "EXPLORATORY_ONLY"
        return _card(plan, status, reasons, warnings, numbers, cal)
    if n_expected > max(c["n"] for c in cal["cells"]):
        warnings.append("N_ABOVE_SIMULATED_RANGE: power argued by dominance of a smaller simulated sample")
    if disp["source"] != "OBSERVED":
        warnings.append("DISPERSION_IS_A_PRIOR: re-assess when the paired differences are observed")
    t1 = cal["type1_max"][f"{gen}|{method}"]
    numbers["simulated_type1_max_for_method"] = t1
    if t1 > 0.075:
        return _card(plan, "METHOD_BLOCKED", [f"METHOD_TYPE1_{t1}_ABOVE_0.075_FOR_THIS_DEPENDENCE"], warnings,
                     numbers, cal)
    return _card(plan, "POWER_READY", [], warnings, numbers, cal)


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
            "calibration_source_sha256": cal["source_sha256"],
            "plan_sha256": sha256_text(json.dumps(plan, sort_keys=True, separators=(",", ":"), default=repr))
            if plan else None}
    card["card_sha256"] = sha256_text(canonical(card))
    return card


if __name__ == "__main__":
    import sys
    with open(sys.argv[1], encoding="utf-8") as fh:
        print(json.dumps(assess(json.load(fh)), indent=1))
