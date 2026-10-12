"""Adapters that bring existing evidence into Research Memory, read-only.

Sources are never modified. Each record cites the source file and its
sha256; re-running an import skips records already present and reports, but
does not rewrite, a source that changed since.
"""
from __future__ import annotations

import json
import os
import re

from .hypotheses import register as register_hypothesis
from .gates import EVIDENCE_ORDER
from .memory import sha256_file

HERE = os.path.dirname(os.path.abspath(__file__))
RESEARCH = os.path.abspath(os.path.join(HERE, ".."))
ROOT = os.path.abspath(os.path.join(RESEARCH, "..", ".."))
P726 = os.path.join(RESEARCH, "phase7", "phase7_26")

# phase7_26 verdict -> (result, evidence_level). Explicit, reviewable.
VERDICT_MAP = {
    "EDGE_CANDIDATE_REQUIRES_FORWARD_VALIDATION": ("INCONCLUSIVE", "DISCOVERY_ONLY"),
    "INSUFFICIENT_OOS_SAMPLE": ("INCONCLUSIVE", "DISCOVERY_ONLY"),
    "FIX_CAUSALLY_VALIDATED": ("POSITIVE", "MECHANICAL_VERIFICATION"),
    "INTEGRITY_PARTIALLY_VALIDATED": ("INCONCLUSIVE", "MECHANICAL_VERIFICATION"),
    "SAMPLE_SUFFICIENT_FOR_A_FIRST_READ": ("NEGATIVE", "INDEPENDENT_FORWARD"),
    "BUY_DOMINANCE_LARGELY_EXPLAINED_BY_MARKET_REGIME": ("POSITIVE", "DISCOVERY_ONLY"),
}
# Per-experiment corrections, each with the reason found in the source itself.
VERDICT_OVERRIDES = {
    "EXP_LIQ_SWEEP_INTEGRITY_AUDIT": ("NEGATIVE", "MECHANICAL_VERIFICATION",
                                      "source limitations: 'Ipotesi verificata e RESPINTA - nessun mismatch trovato'"),
}
EXPOSURE_MAP = {
    "EXPOSED_DISCOVERY_AND_BASELINE": "SEEN_FOR_ECONOMICS", "NO_EVENTS": "SEEN_FOR_SIGNALS",
    "CONSUMED_AS_OOS": "CONSUMED_AS_OOS", "UNVERIFIED": "UNKNOWN", "NOT_USED": "UNSEEN",
    "SEEN_FOR_SIGNALS_NOT_FOR_ECONOMICS": "SEEN_FOR_SIGNALS",
    "NOT_APPLICABLE_NO_ECONOMIC_DATASET": "SEEN_FOR_SIGNALS",
    "SEEN_FOR_NET_PNL_TOTALE_NOT_FOR_GRANULAR_STATS": "SEEN_FOR_ECONOMICS",
    "DERIVED_FROM_DISCOVERY_DATASETS": "DISCOVERY_REUSE",
}


def rid(prefix, raw):
    clean = re.sub(r"[^A-Z0-9_.-]", "_", str(raw).upper()).strip("_")
    return f"{prefix}-{clean}"[:86]


def _payload(path):
    with open(path, encoding="utf-8") as handle:
        doc = json.load(handle)
    return doc.get("payload", doc)


def _source(path, note=None):
    src = {"kind": "FILE", "ref": os.path.relpath(path, ROOT).replace(os.sep, "/"), "sha256": sha256_file(path)}
    if note:
        src["note"] = note
    return src


def import_phase7_26(memory, author="registry-backfill"):
    """Hypotheses, experiments, exposure and failure modes from phase7_26."""
    report = {"added": [], "skipped": [], "source_changed": []}
    hyp_path = os.path.join(P726, "hypothesis_registry_v1.json")
    exp_path = os.path.join(P726, "experiment_registry_v1.json")
    exp_reg_path = os.path.join(P726, "data_exposure_registry_v1.json")
    fail_path = os.path.join(P726, "failure_map_v1.json")
    exposure = {r["dataset_id"]: r["holdout_status"].split(" ")[0]
                for r in _payload(exp_reg_path)["records"]}
    failures = _payload(fail_path)["strategies"]
    best = {}
    for e in _payload(exp_path)["experiments"]:
        lvl = (VERDICT_OVERRIDES.get(e["experiment_id"]) or VERDICT_MAP.get(e["verdict"]) or (None, None))[1]
        if lvl and EVIDENCE_ORDER.index(lvl) > EVIDENCE_ORDER.index(best.get(e["hypothesis_id"], "DISCOVERY_ONLY")):
            best[e["hypothesis_id"]] = lvl

    for h in _payload(hyp_path)["hypotheses"]:
        record_id = rid("HYP", h["hypothesis_id"])
        if _skip(memory, record_id, hyp_path, report):
            continue
        spec = {"event_family": f"REGISTRY:{h['hypothesis_id']}", "direction": "ANY", "state_conditions": [],
                "outcome_definition": h["statement"], "mechanism": "not declared in source registry",
                "falsification": "not declared in source registry",
                "data_needed": [h.get("discovery_dataset_id") or "unknown"],
                "overfitting_risk": "UNKNOWN", "expected_information_value": "UNKNOWN"}
        register_hypothesis(memory, record_id[4:], spec, statement=h["statement"], origin="REGISTRY_BACKFILL",
                            author=author, project="NEXUS_TRADING_RESEARCH",
                            family=(h.get("originating_strategies") or ["UNKNOWN"])[0],
                            lifecycle_state=h["lifecycle_state"],
                            evidence_level=("MECHANICAL_VERIFICATION" if h.get("mechanical_verification_exception")
                                            else best.get(h["hypothesis_id"], "DISCOVERY_ONLY")),
                            provenance=[_source(hyp_path, h["hypothesis_id"])])
        report["added"].append(record_id)

    for e in _payload(exp_path)["experiments"]:
        record_id = rid("EXP", e["experiment_id"])
        if _skip(memory, record_id, exp_path, report):
            continue
        result, level = VERDICT_MAP.get(e["verdict"], ("INCONCLUSIVE", "DISCOVERY_ONLY"))
        limits = [e["limitations"]] if isinstance(e.get("limitations"), str) else list(e.get("limitations") or [])
        if e["experiment_id"] in VERDICT_OVERRIDES:
            result, level, why = VERDICT_OVERRIDES[e["experiment_id"]]
            limits.append(f"result mapped by override: {why}")
        status = exposure.get(e["dataset_id"], "UNVERIFIED")
        dataset = {"dataset_id": e["dataset_id"], "split": "forward" if status == "CONSUMED_AS_OOS" else "unknown",
                   "exposure": EXPOSURE_MAP.get(status, "UNKNOWN")}
        if e.get("period"):
            dataset["period"] = str(e["period"])
        strategy = e.get("strategy_identity") or "UNKNOWN"
        modes = [m["mode"] for m in (failures.get(strategy) or {}).get("failure_modes", [])]
        hyp_record = rid("HYP", e["hypothesis_id"])
        body = {"hypothesis_id": e["hypothesis_id"], "status": "COMPLETED", "result": result,
                "datasets": [dataset],
                "method": {"description": str(e.get("method") or ""), "params_sha256": str(e.get("config_hash") or "UNKNOWN"),
                           "code_commit": str(e.get("code_sha") or "UNKNOWN"), "preregistered": False},
                "metrics": e.get("metrics") if isinstance(e.get("metrics"), dict) else {"raw": e.get("metrics")},
                "limits": limits, "anomalies": [], "alternative_explanations": [],
                "conclusions": [f"source verdict: {e['verdict']}"], "failure_modes": modes,
                "evidence_level": level, "decision": e["verdict"]}
        relations = [{"type": "TESTS", "target": hyp_record}] if memory.get(hyp_record) else []
        memory.append("EXPERIMENT", record_id, body, author=author, origin="REGISTRY_BACKFILL",
                      project="NEXUS_TRADING_RESEARCH", family=strategy, relations=relations,
                      provenance=[_source(exp_path, e["experiment_id"]), _source(exp_reg_path),
                                  _source(fail_path)])
        report["added"].append(record_id)
    return report


def _skip(memory, record_id, path, report):
    existing = memory.get(record_id)
    if not existing:
        return False
    old = next((p.get("sha256") for p in existing["provenance"] if p["ref"].endswith(os.path.basename(path))), None)
    if old and old != sha256_file(path):
        report["source_changed"].append(record_id)
    report["skipped"].append(record_id)
    return True


DECISION_TO_RESULT = {"GO": "POSITIVE", "INVESTIGATE": "INCONCLUSIVE", "SMOKE_PASSED": "NOT_AVAILABLE"}


def _interval(ci):
    """Month-block bootstrap intervals come as {"low", "high", ...}; review checks expect [low, high]."""
    if isinstance(ci, dict):
        return [ci.get("low"), ci.get("high")]
    return ci


def import_behavior_lab_summary(memory, summary_path, hypothesis_record, *, author="behavior-lab-adapter",
                                prereg_relpath=None, supersedes=None):
    """One Behavior Lab run (summary.json from behavior_lab_v1) as an EXPERIMENT record.

    `supersedes` names the NOT_RUN placeholder of the same experiment: it stays
    in memory, the run record points at it.

    A summary carrying a `transcription` block is a declared copy of a summary.json
    that stays on the research PC: the RUN provenance then holds the sha256 of the
    original file, the transcription itself is recorded as a FILE, and the record
    lists the transcription among its limits."""
    with open(summary_path, encoding="utf-8") as handle:
        s = json.load(handle)
    tr = s.get("transcription")
    decision = (s.get("decision") or {}).get("decision", "STOP")
    kind = (s.get("decision") or {}).get("kind")
    if decision == "STOP" and kind == "DATA_OR_DETECTOR":
        status, result = "ABORTED", "NOT_AVAILABLE"
    elif decision == "STOP":
        status, result = "COMPLETED", "NEGATIVE"
    else:
        status = "PARTIAL" if s.get("smoke") else "COMPLETED"
        result = DECISION_TO_RESULT.get(decision, "INCONCLUSIVE")
    ev = s.get("events") or {}
    metrics = {"n_closed": ev.get("n_closed"), "expectancy_r_net": ev.get("expectancy_r_net"),
               "expectancy_ci95": _interval(ev.get("expectancy_r_net_ci95_month_blocks")),
               "p_target_first": ev.get("p_target_first"),
               "controls": {k: (s.get("controls") or {}).get(k) for k in ("n_closed", "expectancy_r_net")},
               "vs_control_stratified": {k: (s.get("vs_control_stratified") or {}).get(k)
                                         for k in ("adjusted_delta_expectancy_r", "cells_used",
                                                   "cells_event_better")},
               "detector_health": {k: {"n": v.get("n_events"), "firing_rate": v.get("firing_rate"),
                                       "status": v.get("status")}
                                   for k, v in (s.get("detector_health") or {}).items()},
               "funnel_events": s.get("funnel_events")}
    checks = s.get("data_checks") or {}
    body = {"hypothesis_id": s.get("hypothesis_id", "UNKNOWN"), "status": status, "result": result,
            "datasets": [{"dataset_id": s.get("dataset_id") or "DUKASCOPY_NEWPERIOD_2023H1_ONWARD_V1",
                          "sha256": (checks.get("manifest") or {}).get("sha256", "UNVERIFIED"),
                          "split": s.get("split", "unknown"), "period": f"{s.get('split_start')}..{s.get('split_end')}",
                          "exposure": "UNSEEN"}],
            "method": {"description": "behavior_lab_v1 H4 impulse -> pullback -> M15 confirmation",
                       "params_sha256": s.get("params_sha256", "UNKNOWN"), "code_commit": s.get("git_commit") or "UNKNOWN",
                       "preregistered": True, "control": "same M15 rule at other H4 closes, no H4 context",
                       "multiple_testing_family": "BL-H4M15"},
            "metrics": metrics,
            "data_checks": {"tick_audit": (checks.get("tick_audit") or {}).get("verdict"),
                            "alignment_mismatches": len(checks.get("alignment_mismatches") or []),
                            "reference_h4": checks.get("reference_h4_mismatches") if isinstance(
                                checks.get("reference_h4_mismatches"), str) else len(checks.get("reference_h4_mismatches") or []),
                            "manifest": (checks.get("manifest") or {}).get("verdict")},
            "resources": {"total_seconds": s.get("total_seconds"), "peak_rss_mb": s.get("peak_rss_mb"),
                          "timings_s": s.get("timings_s")},
            "limits": ["Dukascopy prices, not the broker feed", "no slippage, no commission",
                       "descriptive control, not baseline v4", "dependence diagnostics not applied"]
                      + ([f"transcribed from {tr['source_file']} (sha256 {tr['source_sha256']}): {tr['method']}"]
                         if tr else []),
            "anomalies": [], "alternative_explanations": [],
            "conclusions": [f"decision {decision}" + (f" ({kind})" if kind else "")],
            "evidence_level": "DISCOVERY_ONLY" if s.get("split") == "discovery" else "INTERNAL_VALIDATION",
            "decision": decision}
    if tr:
        provenance = [{"kind": "RUN", "ref": s.get("run_id", "unknown"), "sha256": tr["source_sha256"],
                       "note": f"original {tr['source_file']}, not transferred"},
                      {"kind": "FILE", "ref": tr.get("relpath", os.path.basename(summary_path)),
                       "sha256": sha256_file(summary_path), "note": "declared transcription of the RUN summary"}]
    else:
        provenance = [{"kind": "RUN", "ref": s.get("run_id", "unknown"), "sha256": sha256_file(summary_path)}]
    if prereg_relpath:
        provenance.append({"kind": "FILE", "ref": prereg_relpath})
    return memory.append("EXPERIMENT", rid("EXP", s.get("run_id", "BL-RUN")), body, author=author,
                         origin="RULE_ENGINE", project="NEXUS_TRADING_RESEARCH", family="BL-H4M15",
                         provenance=provenance, relations=[{"type": "TESTS", "target": hypothesis_record}]
                         + ([{"type": "SUPERSEDES", "target": supersedes}] if supersedes else []))
