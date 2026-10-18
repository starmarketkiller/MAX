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
  plan inside the qualified box (same estimand, benchmark, method and dependence
  model; plan n, effect and dispersion inside the simulated ranges; cell n and
  effect <= plan, cell dispersion >= plan; alpha per test >= simulated alpha), whose
  one-sided 95% Wilson lower bound on power reaches the target, for a method whose
  simulated null rejections are compatible with the nominal 0.05 at every simulated
  n of the plan's range. Anything else is NOT_ASSESSABLE, never extrapolated.
- unseen data only through the canonical phase7_26 exposure registry (record with
  every exposure flag false and the same symbol, timeframe and date range): no
  self-attested manifest is accepted as proof of independence.

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

RULES_VERSION = "POWER_GATE_RULES_V1.2"
Z_ONE_SIDED_95 = 1.6448536
Z_TWO_SIDED_95 = 1.959964
NOMINAL_ALPHA = 0.05
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


def wilson(successes, n, z):
    """Wilson score interval (lo, hi) for a binomial proportion."""
    p = successes / n
    centre = (p + z * z / (2 * n)) / (1 + z * z / n)
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / (1 + z * z / n)
    return max(0.0, centre - half), min(1.0, centre + half)


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
                p, reps = c["rejection_rate"][spec["col"]], c["reps"]
                cells.append({"gen": c["gen"], "n": c["n"], "delta": c["delta_atr"], "method": method,
                              "power": p, "reps": reps, "power_mc_se": round(math.sqrt(p * (1 - p) / reps), 4),
                              "power_lower_95_one_sided": round(wilson(round(p * reps), reps, Z_ONE_SIDED_95)[0], 4),
                              "sigma_d": round(sigma_d[(c["gen"], c["n"])], 4)})
    type1 = {}
    for c in sig:
        if c["delta_atr"] == 0:
            for method, spec in METHODS.items():
                p, reps = c["rejection_rate"][spec["col"]], c["reps"]
                lo, hi = wilson(round(p * reps), reps, Z_TWO_SIDED_95)
                type1[f"{c['gen']}|{method}|{c['n']}"] = {"rate": p, "reps": reps, "wilson95": [round(lo, 4), round(hi, 4)],
                                                          "compatible_with_nominal": lo <= NOMINAL_ALPHA}
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
            "type1": dict(sorted(type1.items())),
            "qualified_ranges": {g: {"n": [min(c["n"] for c in cells if c["gen"] == g),
                                           max(c["n"] for c in cells if c["gen"] == g)],
                                     "delta": [min(c["delta"] for c in cells if c["gen"] == g),
                                               max(c["delta"] for c in cells if c["gen"] == g)],
                                     "sigma_d": [round(min(v for (gg, _), v in sigma_d.items() if gg == g), 4),
                                                 round(max(v for (gg, _), v in sigma_d.items() if gg == g), 4)]}
                                 for g in ("G_U", "G_C")},
            "analytic_minus_simulated_power_max": {k: round(v, 4) for k, v in sorted(over.items())},
            "analytic_note": "empirical maxima over the studied cells only; not a bound and never used to certify",
            "winners_curse": {"config": CURSE_CONFIG, "inflation_by_screening_n": dict(sorted(curse.items()))}}


_REGISTRY_MODULE = None


def _registry_module():
    """phase7_26 build_data_exposure_registry, loaded by path for is_genuinely_untouched (no build at import)."""
    global _REGISTRY_MODULE
    if _REGISTRY_MODULE is None:
        import importlib.util
        path = os.path.join(os.path.dirname(EXPOSURE_REGISTRY_PATH), "build_data_exposure_registry.py")
        spec = importlib.util.spec_from_file_location("phase7_26_build_data_exposure_registry", path)
        _REGISTRY_MODULE = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(_REGISTRY_MODULE)
    return _REGISTRY_MODULE


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


def _dataset_status(ds, registry):
    """Return (status, reason). status: EXPOSED, VERIFIED_UNSEEN, or None (cannot be verified).

    Independence is never self-attested: the only proof of an unseen dataset is a record in
    the canonical phase7_26 exposure registry (a reviewed, committed ledger) with every
    exposure flag false and the same symbol, timeframe and date range the plan declares.
    """
    did = ds.get("dataset_id")
    if "provenance" in ds:
        return None, f"PROVENANCE_MANIFEST_SELF_ATTESTED_NOT_ACCEPTED:{did}"
    rec = registry.get(did)
    if rec is None:
        if ds.get("exposure") == "EXPOSED":
            return "EXPOSED", ""
        return None, f"DATASET_NOT_IN_EXPOSURE_REGISTRY:{did}"
    if any(rec.get(f) for f in EXPOSURE_FLAGS):
        return "EXPOSED", ""
    # The registry's own query: only NOT_USED / UNVERIFIED windows were never traversed. For a
    # confirmation the gate is stricter: UNVERIFIED (availability/quality unknown) does not count,
    # and every exposure flag must be an explicit False (None / "SCONOSCIUTO" is unknown).
    if not _registry_module().is_genuinely_untouched(did, registry):
        return "EXPOSED", ""
    if rec.get("holdout_status", "").split(" - ")[0] != "NOT_USED":
        return None, f"DATASET_UNTOUCHED_STATUS_NOT_PROVEN:{did}"
    if any(rec.get(f) is not False for f in EXPOSURE_FLAGS):
        return None, f"DATASET_EXPOSURE_FLAGS_UNKNOWN:{did}"
    for key in ("symbol", "timeframe", "date_range"):
        if ds.get(key) in (None, "", []) or ds.get(key) != rec.get(key):
            return None, f"DATASET_IDENTITY_MISMATCH_WITH_REGISTRY:{did}:{key}"
    return "VERIFIED_UNSEEN", ""


def _preregistration_mismatches(plan, cfam):
    """Semantic check of the confirmation-family preregistration (hash already verified)."""
    with open(os.path.join(REPO_ROOT, os.path.normpath(cfam["preregistration_path"])), encoding="utf-8") as fh:
        try:
            doc = json.load(fh)
        except ValueError:
            return ["UNPARSEABLE"]
    if not isinstance(doc, dict):
        return ["NOT_A_MAPPING"]
    bad = []
    ids = doc.get("experiment_ids")
    if not isinstance(ids, list) or plan.get("experiment_id") not in ids:
        bad.append("experiment_id")
    if not isinstance(ids, list) or len(ids) != cfam.get("size") or len(set(map(str, ids))) != len(ids):
        bad.append("family_size")
    if doc.get("alpha_allocation") != cfam.get("alpha_allocation"):
        bad.append("alpha_allocation")
    if _num(doc.get("alpha")) is None or doc.get("alpha") != plan.get("alpha", NOMINAL_ALPHA):
        bad.append("alpha")
    if not plan.get("protocol_version") or doc.get("protocol_version") != plan.get("protocol_version"):
        bad.append("protocol_version")
    if cfam.get("alpha_allocation") == "FIXED_SEQUENCE" and isinstance(ids, list) and \
            plan.get("experiment_id") in ids and ids.index(plan.get("experiment_id")) + 1 != cfam.get("position"):
        bad.append("sequence_position")
    return bad


def _dominating_cell(cal, gen, method, n, effect, sigma, target):
    """Simulated cell inside the plan's qualified box whose lower power bound reaches the target."""
    best = None
    for c in cal["cells"]:
        if c["gen"] == gen and c["method"] == method and c["n"] <= n and c["delta"] <= effect \
                and c["sigma_d"] >= sigma and c["power_lower_95_one_sided"] >= target:
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
        st, why = _dataset_status(ds if isinstance(ds, dict) else {}, registry)
        statuses.append(st)
        if st is None:
            reasons.append(why)
    family = plan.get("family_size")
    if purpose == "SCREENING":
        need((isinstance(family, int) and not isinstance(family, bool) and family >= 1) or None, "FAMILY_SIZE_INVALID")
    cfam = plan.get("confirmation_family") if isinstance(plan.get("confirmation_family"), dict) else None
    prereg_mismatch = []
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
            prereg_mismatch = _preregistration_mismatches(plan, cfam) if ok else []
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
    if purpose == "CONFIRMATION":
        reasons.extend(f"PREREGISTRATION_INCOMPATIBLE:{m}" for m in prereg_mismatch)
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
    if gen is not None:
        box = cal["qualified_ranges"][gen]
        if not box["n"][0] <= n_expected <= box["n"][1]:
            uncalibrated.append(f"N_{n_expected:g}_OUTSIDE_SIMULATED_{box['n'][0]}_{box['n'][1]}")
        if not box["delta"][0] <= effect_sizing <= box["delta"][1]:
            uncalibrated.append(f"EFFECT_{effect_sizing:g}_OUTSIDE_SIMULATED_{box['delta'][0]}_{box['delta'][1]}")
        if not box["sigma_d"][0] <= sigma <= box["sigma_d"][1]:
            uncalibrated.append(f"SIGMA_{sigma:g}_OUTSIDE_SIMULATED_{box['sigma_d'][0]}_{box['sigma_d'][1]}")
    if reasons:
        return _card(plan, "NOT_ASSESSABLE", reasons, warnings, numbers, cal)
    if uncalibrated:
        numbers["evidence_needed"] = _evidence_needed(uncalibrated)
        return _card(plan, "NOT_ASSESSABLE", ["POWER_NOT_CALIBRATED_FOR_DESIGN", *uncalibrated], warnings,
                     numbers, cal)

    # 7. Level control: every simulated null cell of this method and dependence model, at the
    # simulated sample sizes from the method minimum up to the plan's n, must be compatible with
    # the nominal 0.05 (two-sided 95% Wilson interval reaches 0.05). The 0.075 ceiling is not used.
    grid = sorted({int(k.rsplit("|", 1)[1]) for k in cal["type1"] if k.startswith(f"{gen}|{method}|")})
    upper = min(g for g in grid if g >= n_expected)  # n_expected <= max(grid) after the box check
    level = {k: v for k, v in cal["type1"].items()
             if k.startswith(f"{gen}|{method}|") and min_n <= int(k.rsplit("|", 1)[1]) <= upper}
    numbers["simulated_null_rejections"] = level
    failing = sorted(k for k, v in level.items() if not v["compatible_with_nominal"])
    if not level or failing:
        return _card(plan, "METHOD_BLOCKED", ["LEVEL_NOT_DEMONSTRATED_AT_NOMINAL_0.05", *failing], warnings,
                     numbers, cal)

    # 8. Power: a dominating simulated cell whose one-sided 95% Wilson lower bound reaches the target.
    cell = _dominating_cell(cal, gen, method, n_expected, effect_sizing, sigma, target)
    numbers["dominating_pr59_cell"] = cell
    if cell is None:
        reasons.append("NO_SIMULATED_PR59_CELL_LOWER_POWER_BOUND_REACHES_TARGET")
        status = "DATA_REQUIRED" if purpose == "CONFIRMATION" else "EXPLORATORY_ONLY"
        return _card(plan, status, reasons, warnings, numbers, cal)
    if disp["source"] != "OBSERVED":
        warnings.append("DISPERSION_IS_A_PRIOR: re-assess when the paired differences are observed")
    return _card(plan, "POWER_READY", [], warnings, numbers, cal)


EVIDENCE_FOR = {
    "UNIT_": "PR #59-style synthetic study of the paired difference in this unit, with this benchmark",
    "BENCHMARK_": "synthetic study with this benchmark's matched-control construction",
    "CONTROLS_PER_EVENT": "synthetic study with this number of controls per event",
    "ALPHA_PER_TEST_": "simulated rejection counts at this alpha per test (PR #59 recorded 0.05 only)",
    "PLAN_SPECIFIC_DEPENDENCE": "synthetic study reproducing this plan's dependence structure",
    "N_": "simulations at the plan's sample size (PR #59 simulated n up to 400)",
    "EFFECT_": "simulations at the plan's effect size (PR #59 simulated 0.1-1.0 ATR)",
    "SIGMA_": "simulations with the plan's paired-difference dispersion",
}


def _evidence_needed(uncalibrated):
    return sorted({text for code in uncalibrated for prefix, text in EVIDENCE_FOR.items() if code.startswith(prefix)})


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
