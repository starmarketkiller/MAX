"""Post-experiment review: deterministic rules over one EXPERIMENT record.

Tier 0 in the routing of docs/architecture/18 (no model call). Each rule
reads the immutable experiment record and emits findings; findings that
call for action become IMPROVEMENT_PROPOSAL records, each passed through
gates.check_proposal before it is written. A proposal already open for the
same (family, check) is not duplicated: the review only links to it.

The reviewed record is never modified. Running the same rules version on the
same record twice writes nothing the second time.
"""
from __future__ import annotations

from . import gates
from .memory import sha256_text

RULES_VERSION = "RI_REVIEW_RULES_V1"
MIN_CLOSED_FOR_FIRST_READ = 30
SLOW_RUN_SECONDS = 3600
HEAVY_RUN_MB = 4096
EXPOSED_FOR_CONFIRMATION = {"DISCOVERY_REUSE", "SEEN_FOR_SIGNALS", "SEEN_FOR_ECONOMICS", "CONSUMED_AS_OOS"}
CONFIRMATORY_LEVELS = {"INTERNAL_VALIDATION", "LOCKED_VALIDATION", "INDEPENDENT_FORWARD"}
UNKNOWN = {"", "UNKNOWN", "UNVERIFIED", None}


def _f(check, area, severity, detail, proposal_class):
    return {"check": check, "area": area, "severity": severity, "detail": detail, "proposal_class": proposal_class}


def findings_for(exp):
    """The rule set. Pure function of the experiment body: same input, same findings."""
    b = exp["body"]
    m = b.get("metrics") or {}
    out = []
    for ds in b["datasets"]:
        if ds.get("sha256") in UNKNOWN:
            out.append(_f("DATASET_HASH_MISSING", "DATA_QUALITY", "WARNING",
                          f"dataset {ds['dataset_id']} has no content hash: the run cannot be reproduced bit for bit",
                          "PROCESS_IMPROVEMENT"))
        if ds.get("split") in gates.protected_splits():
            out.append(_f("PROTECTED_SPLIT_READ", "CAUSALITY_LEAKAGE", "BLOCKER",
                          f"dataset {ds['dataset_id']} is on one-shot split '{ds['split']}': confirm a ledgered "
                          "human decision exists for this single read", "INSUFFICIENT_EVIDENCE"))
        if ds.get("exposure") in EXPOSED_FOR_CONFIRMATION and b.get("evidence_level") in CONFIRMATORY_LEVELS \
                and ds.get("split") != "forward":
            out.append(_f("EXPOSED_DATA_AS_CONFIRMATION", "CAUSALITY_LEAKAGE", "BLOCKER",
                          f"evidence level {b['evidence_level']} claimed on data already exposed "
                          f"({ds['exposure']})", "INSUFFICIENT_EVIDENCE"))
        if ds.get("exposure") == "UNKNOWN":
            out.append(_f("EXPOSURE_UNKNOWN", "CAUSALITY_LEAKAGE", "WARNING",
                          f"exposure of {ds['dataset_id']} is not in the data exposure registry",
                          "PROCESS_IMPROVEMENT"))

    checks = b.get("data_checks") or {}
    bad = [k for k, v in checks.items() if (isinstance(v, (int, float)) and not isinstance(v, bool) and v > 0)
           or (isinstance(v, str) and v.upper() in ("FAIL", "FAILED", "MISMATCH"))]
    if bad:
        out.append(_f("DATA_CHECK_FAILED", "DATA_QUALITY", "BLOCKER",
                      f"data checks not clean: {sorted(bad)}", "DEFECT_FIX"))

    method = b["method"]
    if method["params_sha256"] in UNKNOWN or method["code_commit"] in UNKNOWN:
        out.append(_f("NOT_REPRODUCIBLE", "METHODOLOGY", "WARNING",
                      "parameters hash or code commit not recorded", "PROCESS_IMPROVEMENT"))
    if not method["preregistered"] and b.get("evidence_level") in CONFIRMATORY_LEVELS:
        out.append(_f("CONFIRMATION_WITHOUT_PREREG", "METHODOLOGY", "WARNING",
                      "confirmatory evidence level without a preregistration on record", "INSUFFICIENT_EVIDENCE"))
    if b["status"] == "COMPLETED" and not method.get("control"):
        out.append(_f("NO_CONTROL", "METHODOLOGY", "WARNING",
                      "no control or baseline declared: the result has nothing to be compared with",
                      "PROCESS_IMPROVEMENT"))
    if not method.get("multiple_testing_family"):
        out.append(_f("NO_MULTIPLE_TESTING_FAMILY", "METHODOLOGY", "INFO",
                      "experiment not assigned to a multiple-testing family", "PROCESS_IMPROVEMENT"))

    n = m.get("n_closed")
    if isinstance(n, (int, float)) and n < MIN_CLOSED_FOR_FIRST_READ:
        out.append(_f("LOW_SAMPLE", "STATISTICAL_POWER", "WARNING",
                      f"{n} closed events < {MIN_CLOSED_FOR_FIRST_READ}: no economic reading possible",
                      "INSUFFICIENT_EVIDENCE"))
    ci = m.get("expectancy_ci95")
    if isinstance(ci, (list, tuple)) and len(ci) == 2 and None not in ci and ci[0] < 0 < ci[1]:
        out.append(_f("CI_CROSSES_ZERO", "STATISTICAL_POWER", "INFO",
                      f"95% interval {ci} contains zero", "INSUFFICIENT_EVIDENCE"))
    if "LOW_SAMPLE" in b.get("failure_modes", []) and not any(f["check"] == "LOW_SAMPLE" for f in out):
        out.append(_f("LOW_SAMPLE", "STATISTICAL_POWER", "WARNING",
                      "failure map lists LOW_SAMPLE for this family", "INSUFFICIENT_EVIDENCE"))

    for name, h in sorted((m.get("detector_health") or {}).items()):
        if isinstance(h, dict) and h.get("status") not in (None, "NORMAL"):
            out.append(_f("DETECTOR_UNHEALTHY", "DATA_QUALITY", "WARNING",
                          f"detector {name} firing status {h.get('status')} (rate {h.get('firing_rate')})",
                          "DEFECT_FIX"))
    if "IMPLEMENTATION_DEFECT" in b.get("failure_modes", []):
        out.append(_f("IMPLEMENTATION_DEFECT_OPEN", "METHODOLOGY", "BLOCKER",
                      "failure map lists IMPLEMENTATION_DEFECT", "DEFECT_FIX"))

    res = b.get("resources") or {}
    if isinstance(res.get("total_seconds"), (int, float)) and res["total_seconds"] > SLOW_RUN_SECONDS:
        out.append(_f("SLOW_RUN", "RESOURCES", "INFO",
                      f"run took {res['total_seconds']:.0f}s: cache intermediate bars/events between runs",
                      "PROCESS_IMPROVEMENT"))
    if isinstance(res.get("peak_rss_mb"), (int, float)) and res["peak_rss_mb"] > HEAVY_RUN_MB:
        out.append(_f("HEAVY_RUN", "RESOURCES", "INFO", f"peak memory {res['peak_rss_mb']} MB",
                      "PROCESS_IMPROVEMENT"))
    if not res and b["status"] == "COMPLETED":
        out.append(_f("RESOURCES_NOT_RECORDED", "TOOLING", "INFO",
                      "compute time and memory not recorded: cost of re-running is unknown", "PROCESS_IMPROVEMENT"))

    if b["result"] in ("INCONCLUSIVE", "NEGATIVE") and not b.get("alternative_explanations"):
        out.append(_f("NO_ALTERNATIVE_EXPLANATIONS", "INFORMATION_VALUE", "WARNING",
                      f"{b['result']} result without alternative explanations: the next experiment is not "
                      "informed by this one", "NEW_HYPOTHESIS"))
    if b.get("anomalies"):
        out.append(_f("ANOMALIES_UNEXPLAINED", "INFORMATION_VALUE", "WARNING",
                      f"{len(b['anomalies'])} anomalies recorded", "NEW_HYPOTHESIS"))
    if b["status"] == "NOT_RUN":
        out.append(_f("NOT_RUN", "INFORMATION_VALUE", "INFO", "experiment registered but not executed yet",
                      "NONE"))
    return out


# What each proposal class requires before anything is applied (checked again by gates).
REQUIREMENTS = {
    "PROCESS_IMPROVEMENT": ["HUMAN_APPROVAL", "DEDICATED_METHOD_TEST"],
    "NEW_HYPOTHESIS": ["HUMAN_APPROVAL", "NEW_PREREGISTRATION"],
    "DEFECT_FIX": ["HUMAN_APPROVAL", "DETERMINISTIC_REPRODUCTION", "REGRESSION_TEST", "IMPACT_ANALYSIS"],
    "INSUFFICIENT_EVIDENCE": ["MORE_DATA", "BETTER_DESIGN"],
}
STEPS = {
    "DATASET_HASH_MISSING": ["compute sha256 of the dataset manifest", "record it in future experiment records"],
    "EXPOSURE_UNKNOWN": ["add the dataset to phase7_26/data_exposure_registry_v1.json via a reviewed PR"],
    "NOT_REPRODUCIBLE": ["record params sha256 and git commit in the run summary"],
    "NO_CONTROL": ["declare a baseline or control in the next preregistration"],
    "NO_MULTIPLE_TESTING_FAMILY": ["assign the family in multiple_testing_registry_v1"],
    "SLOW_RUN": ["cache intermediate bars and events keyed by dataset sha", "compare outputs bit for bit"],
    "HEAVY_RUN": ["stream ticks per month instead of loading the full period"],
    "RESOURCES_NOT_RECORDED": ["record total_seconds and peak_rss_mb in the run summary"],
    "DATA_CHECK_FAILED": ["reproduce the failing check deterministically", "fix the loader or detector",
                          "add a regression test", "list experiments affected by the defect"],
    "DETECTOR_UNHEALTHY": ["reproduce the firing rate on a fixed sample", "fix and add a regression test",
                           "list experiments affected"],
    "IMPLEMENTATION_DEFECT_OPEN": ["reproduce", "fix with regression test", "impact analysis on past results"],
    "NO_ALTERNATIVE_EXPLANATIONS": ["write at least two alternative explanations",
                                    "turn each into a hypothesis with a falsification test"],
    "ANOMALIES_UNEXPLAINED": ["describe each anomaly as a hypothesis with mechanism and falsification"],
}


def _proposal(exp, finding):
    cls = finding["proposal_class"]
    title = f"{finding['check']}: {exp['family']}"
    if cls == "PROCESS_IMPROVEMENT" and finding["area"] == "METHODOLOGY":
        title = f"method {title}"
    return {"proposal_class": cls, "title": title, "rationale": finding["detail"],
            "steps": STEPS.get(finding["check"], ["collect more data or redesign before re-reading the result"]),
            "status": "PROPOSED", "reversible": True,
            "revert_plan": "proposal only: nothing is applied; an accepted change is reverted by reverting its PR",
            "touches_frozen_or_live": False, "requires": list(REQUIREMENTS[cls])}


def proposal_id(family, check):
    return f"PROP-{check}-{sha256_text(family + '|' + check)[:10].upper()}"


def review(memory, experiment_record_id, *, author="improvement-reviewer-rules", created_at=None):
    """Review one experiment. Returns (review_record, new_proposals, linked_existing)."""
    exp = memory.get(experiment_record_id)
    if exp is None or exp["record_type"] != "EXPERIMENT":
        raise ValueError(f"{experiment_record_id} is not an experiment in memory")
    review_id = f"REV-{sha256_text(RULES_VERSION + exp['record_hash'])[:12].upper()}"
    if memory.get(review_id):
        return memory.get(review_id), [], []
    findings = findings_for(exp)
    rev = memory.append("REVIEW", review_id,
                        {"reviewed_record": experiment_record_id, "rules_version": RULES_VERSION,
                         "input_sha256": exp["record_hash"], "findings": findings},
                        author=author, origin="RULE_ENGINE", project=exp["project"], family=exp["family"],
                        provenance=[{"kind": "RECORD", "ref": experiment_record_id, "sha256": exp["record_hash"]}],
                        relations=[{"type": "REVIEWS", "target": experiment_record_id}], created_at=created_at)
    new, linked = [], []
    for finding in findings:
        if finding["proposal_class"] == "NONE":
            continue
        pid = proposal_id(exp["family"], finding["check"])
        if memory.get(pid) or pid in (p["record_id"] for p in new):
            linked.append(pid)
            continue
        if len(new) >= gates.MAX_PROPOSALS_PER_REVIEW:
            break
        body = _proposal(exp, finding)
        gates.check_proposal(body)
        new.append(memory.append("IMPROVEMENT_PROPOSAL", pid, body, author=author, origin="RULE_ENGINE",
                                 project=exp["project"], family=exp["family"],
                                 provenance=[{"kind": "RECORD", "ref": review_id, "sha256": rev["record_hash"]}],
                                 relations=[{"type": "PROPOSED_BY", "target": review_id}],
                                 created_at=created_at))
    return rev, new, linked
