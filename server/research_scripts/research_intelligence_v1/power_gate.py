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
import fnmatch
import re
import statistics

from . import gates, power
from .memory import canonical, sha256_text
from .review import MIN_CLOSED_FOR_FIRST_READ

RULES_VERSION = "POWER_GATE_RULES_V1.4"
# Frozen PR #59 identities (canonical Git-blob SHA-256), pinned in code so that a substitute file or an
# edited manifest cannot pass: changing them requires a reviewed code change.
PR59_RESULTS_SHA256 = "c538a5d2f3d65a42ac2f71bc52039e67636e9d16e25c6e443134f6e1732a05d4"
PR59_PROTOCOL_SHA256 = "8dd988251b280e390162c979cf446eb782e3b35371c732f9215bb6624359a698"
Z_ONE_SIDED_95 = 1.6448536
Z_TWO_SIDED_95 = 1.959964
NOMINAL_ALPHA = 0.05
HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
CALIBRATION_PATH = os.path.join(HERE, "..", "edge_detection_capability_v1", "results_v1.json")
CALIBRATION_PROTOCOL_PATH = os.path.join(HERE, "..", "edge_detection_capability_v1", "protocol_v1.json")
CALIBRATION_MANIFEST_PATH = os.path.join(HERE, "..", "edge_detection_capability_v1", "manifest_v1.json")
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
                     "controls_per_event": 1, "control_reuse": False, "alpha": 0.05, "test_sidedness": "TWO_SIDED",
                     "pr59_cluster_model": {"cluster_size": 4, "spacing_bars": 2, "horizon_bars": 10}}
# The one screening configuration PR #59 simulated (winner's curse): R units, 67 candidates, BH q=0.10.
CURSE_CONFIG = {"unit": "R", "family_size": 67, "selection_rule": "BH_Q0.10"}
MAX_MANIFEST_BYTES = 1_000_000
FORBIDDEN_PATH = re.compile(r"(^|/)(data_cache|raw_data)(/|$)|holdout|\.(csv|parquet|bin|zip|gz)$", re.I)


def _sha_file(path):
    with open(path, "rb") as handle:
        return hashlib.sha256(handle.read()).hexdigest()


def _repo_root(path):
    d = os.path.dirname(os.path.abspath(path))
    while True:
        if os.path.exists(os.path.join(d, ".git")):
            return d
        parent = os.path.dirname(d)
        if parent == d:
            return None
        d = parent


def _git_text_conversion_disabled(root, rel):
    """True if .gitattributes marks the path binary / -text / text=false (no eol conversion)."""
    attrs = os.path.join(root, ".gitattributes")
    if not os.path.isfile(attrs):
        return False
    disabled = False
    with open(attrs, encoding="utf-8") as handle:
        for line in handle:
            parts = line.split()
            if not parts or parts[0].startswith("#"):
                continue
            pattern, values = parts[0], parts[1:]
            target = rel if "/" in pattern.strip("/") else os.path.basename(rel)
            if fnmatch.fnmatchcase(target, pattern.strip("/")):
                for v in values:  # later lines override earlier ones, as in Git
                    if v in ("binary", "-text", "text=false"):
                        disabled = True
                    elif v in ("text", "text=auto") or v.startswith("eol="):
                        disabled = False
    return disabled


def artifact_sha256(path):
    """SHA-256 of a versioned artifact, as (sha256, representation). Stdlib only, no external process.

    The hash covers Git's canonical (blob) representation, not the physical checkout bytes:
    - "GIT_CANONICAL_EOL_NORMALIZED": text files, with CRLF turned into LF, i.e. the content Git's
      clean conversion stores in the blob. A Windows CRLF checkout and a Linux LF checkout of the
      same blob give the same hash.
    - "GIT_CANONICAL_BINARY_AS_IS": files marked binary / -text in .gitattributes, hashed as is
      (their blob bytes are their checkout bytes; e.g. the frozen CRLF datasets).
    - "PHYSICAL_BYTES_NO_GIT_REPO": no repository found; callers that attest versioned artifacts
      must not accept it.
    A text blob that genuinely contains CRLF would hash differently from its recorded value and the
    verification fails closed.
    """
    full = os.path.abspath(path)
    with open(full, "rb") as handle:
        data = handle.read()
    root = _repo_root(full)
    if root is None:
        return hashlib.sha256(data).hexdigest(), "PHYSICAL_BYTES_NO_GIT_REPO"
    rel = os.path.relpath(full, root).replace(os.sep, "/")
    if _git_text_conversion_disabled(root, rel):
        return hashlib.sha256(data).hexdigest(), "GIT_CANONICAL_BINARY_AS_IS"
    return hashlib.sha256(data.replace(b"\r\n", b"\n")).hexdigest(), "GIT_CANONICAL_EOL_NORMALIZED"


CANONICAL_REPRESENTATIONS = ("GIT_CANONICAL_EOL_NORMALIZED", "GIT_CANONICAL_BINARY_AS_IS")


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
    """PR #59 frozen results reduced to what the gate may use (read only).

    source_integrity is "VERIFIED" only when the canonical Git-blob SHA-256 of results_v1.json and of
    protocol_v1.json equal the pinned PR #59 identities, the manifest records the same hashes and
    the results name the same protocol. No level qualification is ever read from a file: PR #59 froze
    none, and an independent, time-proven qualification does not exist (see _evaluate()).
    """
    source_sha, rep = artifact_sha256(CALIBRATION_PATH)
    protocol_sha, protocol_rep = artifact_sha256(CALIBRATION_PROTOCOL_PATH)
    with open(CALIBRATION_MANIFEST_PATH, encoding="utf-8") as handle:
        manifest_hashes = json.load(handle)["artifacts_sha256"]
    with open(CALIBRATION_PATH, encoding="utf-8") as handle:
        results_protocol_sha = json.load(handle)["meta"]["protocol_sha256"]
    problems = []
    if rep not in CANONICAL_REPRESENTATIONS or source_sha != PR59_RESULTS_SHA256 \
            or manifest_hashes.get("results_v1.json") != PR59_RESULTS_SHA256:
        problems.append("RESULTS_IDENTITY")
    if protocol_rep not in CANONICAL_REPRESENTATIONS or protocol_sha != PR59_PROTOCOL_SHA256 \
            or manifest_hashes.get("protocol_v1.json") != PR59_PROTOCOL_SHA256 \
            or results_protocol_sha != PR59_PROTOCOL_SHA256:
        problems.append("PROTOCOL_IDENTITY")
    integrity = "VERIFIED" if not problems else "FAILED:" + "+".join(problems)
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
                type1[f"{c['gen']}|{method}|{c['n']}"] = {"rate": p, "rejections": round(p * reps), "reps": reps,
                                                          "wilson95_descriptive": [round(lo, 4), round(hi, 4)]}
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
            "source_sha256": source_sha, "source_integrity": integrity,
            "protocol_sha256": protocol_sha, "level_qualification": None,
            "design": CALIBRATED_DESIGN, "cells": cells,
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
    sha, representation = artifact_sha256(full)
    if representation not in CANONICAL_REPRESENTATIONS:
        return False, f"NOT_A_VERIFIED_VERSIONED_ARTIFACT:{representation}"
    return (sha == declared_sha256.lower()), "SHA256_MISMATCH"


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


def assess(plan):
    """Production interface: a Power Decision Card computed only from the pinned PR #59 calibration
    and the committed exposure registry. There is no way to inject another calibration or registry."""
    return _evaluate(plan, calibration(), exposure_registry(), test_only=False)


def assess_test_only(plan, *, cal, registry):
    """Isolated logic tests with synthetic calibrations/registries. The card is marked TEST_ONLY:
    its status is prefixed "TEST_ONLY:", it is never authorizing and can never read POWER_READY."""
    return _evaluate(plan, cal, registry, test_only=True)


def _evaluate(plan, cal, registry, *, test_only):
    reasons, warnings = [], []
    if not isinstance(plan, dict):
        return _card(test_only, {}, "NOT_ASSESSABLE", ["PLAN_NOT_A_MAPPING"], [], {}, cal)

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
    need(plan.get("test_sidedness") in ("TWO_SIDED", "ONE_SIDED") or None, "TEST_SIDEDNESS_UNDECLARED")
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
        return _card(test_only, plan, "NOT_ASSESSABLE", reasons, warnings, {}, cal)

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
        return _card(test_only, plan, "METHOD_BLOCKED", reasons, warnings, {}, cal)

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
        return _card(test_only, plan, status, reasons, warnings, numbers, cal)

    # 6. Certification: only a dominating simulated PR #59 cell can make the plan POWER_READY.
    if cal.get("source_integrity") != "VERIFIED":
        return _card(test_only, plan, "NOT_ASSESSABLE", [f"CALIBRATION_SOURCE_INTEGRITY_{cal.get('source_integrity')}"],
                     warnings, numbers, cal)
    d = cal["design"]
    gen, uncalibrated = None, []
    if unit != d["unit"]:
        uncalibrated.append(f"UNIT_{unit}_NOT_SIMULATED_WITH_A_BENCHMARK")
    if bench != d["benchmark"]:
        uncalibrated.append(f"BENCHMARK_{bench}_NOT_SIMULATED")
    if disp["controls_per_event"] != d["controls_per_event"]:
        uncalibrated.append("CONTROLS_PER_EVENT_NOT_SIMULATED")
    if alpha_test != d["alpha"]:
        uncalibrated.append(f"ALPHA_PER_TEST_{alpha_test:.4g}_NOT_SIMULATED_{d['alpha']}")
    if plan.get("test_sidedness") != d["test_sidedness"]:
        uncalibrated.append(f"TEST_SIDEDNESS_{plan.get('test_sidedness')}_NOT_SIMULATED_{d['test_sidedness']}")
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
        return _card(test_only, plan, "NOT_ASSESSABLE", reasons, warnings, numbers, cal)
    if uncalibrated:
        numbers["evidence_needed"] = _evidence_needed(uncalibrated)
        return _card(test_only, plan, "NOT_ASSESSABLE", ["POWER_NOT_CALIBRATED_FOR_DESIGN", *uncalibrated], warnings,
                     numbers, cal)

    # 7. Level control. A pre-registered level qualification of the calibration study is required:
    # criterion "Wilson upper bound <= nominal alpha" at the declared confidence, Bonferroni over the
    # cells used, a minimum number of replications per cell, frozen before results. "The interval
    # contains 0.05" and the 0.075 band are not evidence of calibration. PR #59 froze only a
    # point-estimate band [0.025, 0.075], so its simulations cannot qualify the level: NOT_ASSESSABLE.
    grid = sorted({int(k.rsplit("|", 1)[1]) for k in cal["type1"] if k.startswith(f"{gen}|{method}|")})
    upper = min(g for g in grid if g >= n_expected)  # n_expected <= max(grid) after the box check
    level = {k: v for k, v in cal["type1"].items()
             if k.startswith(f"{gen}|{method}|") and min_n <= int(k.rsplit("|", 1)[1]) <= upper}
    numbers["simulated_null_rejections_descriptive"] = level
    # Production never accepts a level qualification: none is bound to an independent protocol whose
    # freezing before the results can be demonstrated. Only isolated TEST_ONLY runs exercise the check.
    lq = cal.get("level_qualification") if test_only else None
    problem = _level_qualification_problem(lq)
    if problem:
        numbers["evidence_needed"] = [LEVEL_EVIDENCE]
        return _card(test_only, plan, "NOT_ASSESSABLE", ["LEVEL_CALIBRATION_NOT_PREREGISTERED", problem], warnings,
                     numbers, cal)
    if not level:
        return _card(test_only, plan, "NOT_ASSESSABLE", ["NO_SIMULATED_NULL_CELLS_IN_RANGE"], warnings, numbers, cal)
    z = statistics.NormalDist().inv_cdf(1 - (1 - lq["confidence"]) / len(level))
    failing = []
    for key, v in sorted(level.items()):
        bound = wilson(v["rejections"], v["reps"], z)[1]
        v["upper_bound_bonferroni"] = round(bound, 4)
        if v["reps"] < lq["min_reps_per_cell"] or bound > lq["nominal_alpha"]:
            failing.append(key)
    if failing:
        return _card(test_only, plan, "METHOD_BLOCKED", ["LEVEL_NOT_DEMONSTRATED_AT_NOMINAL", *failing], warnings, numbers, cal)

    # 8. Power: a dominating simulated cell whose one-sided 95% Wilson lower bound reaches the target.
    cell = _dominating_cell(cal, gen, method, n_expected, effect_sizing, sigma, target)
    numbers["dominating_pr59_cell"] = cell
    if cell is None:
        reasons.append("NO_SIMULATED_PR59_CELL_LOWER_POWER_BOUND_REACHES_TARGET")
        status = "DATA_REQUIRED" if purpose == "CONFIRMATION" else "EXPLORATORY_ONLY"
        return _card(test_only, plan, status, reasons, warnings, numbers, cal)
    if disp["source"] != "OBSERVED":
        warnings.append("DISPERSION_IS_A_PRIOR: re-assess when the paired differences are observed")
    return _card(test_only, plan, "POWER_READY", [], warnings, numbers, cal)


LEVEL_EVIDENCE = ("independent level-calibration study with a pre-registered criterion: Wilson upper bound "
                  "of the null rejection rate <= 0.05 at the declared confidence, Bonferroni over the cells "
                  "used, a minimum replication count per cell sized to make that bound reachable (e.g. "
                  ">= 2000), protocol frozen before results (PR #59 froze only the point band [0.025, 0.075])")
LEVEL_FIELDS = {"criterion": "WILSON_UPPER_BOUND_LE_NOMINAL", "multiplicity": "BONFERRONI_OVER_CELLS"}


def _level_qualification_problem(lq):
    if not isinstance(lq, dict):
        return "CALIBRATION_PROTOCOL_HAS_NO_LEVEL_QUALIFICATION"
    for key, value in LEVEL_FIELDS.items():
        if lq.get(key) != value:
            return f"LEVEL_QUALIFICATION_{key.upper()}_NOT_{value}"
    if lq.get("nominal_alpha") != NOMINAL_ALPHA or _num(lq.get("confidence"), lo=0.9, hi=0.999) is None:
        return "LEVEL_QUALIFICATION_ALPHA_OR_CONFIDENCE_INVALID"
    if not isinstance(lq.get("min_reps_per_cell"), int) or lq["min_reps_per_cell"] < 1:
        return "LEVEL_QUALIFICATION_MIN_REPS_INVALID"
    if lq.get("frozen_before_results") is not True:
        return "LEVEL_QUALIFICATION_NOT_FROZEN_BEFORE_RESULTS"
    return None


EVIDENCE_FOR = {
    "TEST_SIDEDNESS_": "simulated rejections with this test sidedness (PR #59: two-sided only)",
    "UNIT_": "PR #59-style synthetic study of the paired difference in this unit, with this benchmark",
    "BENCHMARK_": "synthetic study with this benchmark's matched-control construction",
    "CONTROLS_PER_EVENT": "synthetic study with this number of controls per event",
    "ALPHA_PER_TEST_": "simulated rejection counts at exactly this alpha per test (PR #59: 0.05 two-sided only)",
    "PLAN_SPECIFIC_DEPENDENCE": "synthetic study reproducing this plan's dependence structure",
    "N_": "simulations at the plan's sample size (PR #59 simulated n up to 400)",
    "EFFECT_": "simulations at the plan's effect size (PR #59 simulated 0.1-1.0 ATR)",
    "SIGMA_": "simulations with the plan's paired-difference dispersion",
}


def _evidence_needed(uncalibrated):
    return sorted({text for code in uncalibrated for prefix, text in EVIDENCE_FOR.items() if code.startswith(prefix)})


def _card(test_only, plan, status, reasons, warnings, numbers, cal):
    evidence_ceiling = {"POWER_READY": "DISCOVERY_ONLY" if plan.get("purpose") == "SCREENING"
                        else "INTERNAL_VALIDATION (after protocol review)",
                        "EXPLORATORY_ONLY": "EXPLORATORY", "DATA_REQUIRED": "EXPLORATORY",
                        "METHOD_BLOCKED": "NONE", "NOT_ASSESSABLE": "NONE"}[status]
    if test_only:
        status, evidence_ceiling = f"TEST_ONLY:{status}", "NONE (TEST_ONLY)"
    card = {"rules_version": RULES_VERSION, "experiment_id": plan.get("experiment_id"),
            "purpose": plan.get("purpose"), "status": status, "test_only": test_only,
            "authorizing": False, "reasons": reasons, "warnings": warnings,
            "numbers": numbers, "evidence_ceiling": evidence_ceiling,
            "not_an_authorization": "POWER_READY is not EDGE_VALIDATED and does not authorize execution, "
                                    "holdout access, deploy or trading."
                                    + (" TEST_ONLY cards come from synthetic fixtures and certify nothing."
                                       if test_only else ""),
            "calibration_source_sha256": cal.get("source_sha256"),
            "calibration_source_integrity": cal.get("source_integrity"),
            "hash_representation": "Git canonical blob bytes (CRLF->LF for text, as-is for binary attributes); "
                                   "independent of CRLF/LF checkout",
            "plan_sha256": sha256_text(json.dumps(plan, sort_keys=True, separators=(",", ":"), default=repr))
            if plan else None}
    card["card_sha256"] = sha256_text(canonical(card))
    return card


if __name__ == "__main__":
    import sys
    with open(sys.argv[1], encoding="utf-8") as fh:
        print(json.dumps(assess(json.load(fh)), indent=1))
