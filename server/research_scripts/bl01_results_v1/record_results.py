"""Write the BL-01 discovery analysis into Research Memory (append-only, idempotent).

The run itself enters memory through the RI-02 loop (OBSERVE ingests the declared
transcription of summary.json). This module adds what a person reading the run
concluded, without touching the preregistration, the parameters or the run record:
  - EXPERIMENT revision of the run record: alternative explanations, anomalies, conclusions;
  - OBSERVATION: feasibility observed vs the power study's predictions;
  - IMPROVEMENT_PROPOSALs (PROPOSED only, nothing is applied).

Run from server/research_scripts, after `cli loop-run --inbox <summary.transcribed.json>`:
    python -m bl01_results_v1.record_results [--memory PATH]
"""
from __future__ import annotations

import argparse
import copy
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
from research_intelligence_v1.memory import DEFAULT_PATH, ResearchMemory, sha256_file, sha256_text  # noqa: E402

RUN_DIR = os.path.join(os.path.dirname(HERE), "behavior_lab_v1", "results", "BL-01_discovery_20261012T083523Z")
SUMMARY = os.path.join(RUN_DIR, "summary.transcribed.json")
POWER = os.path.join(os.path.dirname(HERE), "bl_power_study_v1", "bl01_power_report_v1.json")
REL = "server/research_scripts/"
RUN_RECORD = "EXP-BL-H4M15-IPC-001_DISCOVERY_20261012T083523Z"
HYP = "HYP-BL-H4M15-IPC-001"
PROJECT, FAMILY = "NEXUS_TRADING_RESEARCH", "BL-H4M15"
AUTHOR = "claude-trading-research"


def _pid(check):
    return f"PROP-{check}-{sha256_text(FAMILY + '|' + check)[:10].upper()}"


def _src(path):
    return {"kind": "FILE", "ref": REL + os.path.relpath(path, os.path.dirname(HERE)).replace(os.sep, "/"),
            "sha256": sha256_file(path)}


def record(memory, created_at=None):
    run = memory.current(RUN_RECORD)
    if run is None:
        raise SystemExit(f"{RUN_RECORD} not in memory: run the RI-02 loop with the transcription in --inbox first")
    s = json.load(open(SUMMARY, encoding="utf-8"))
    power = json.load(open(POWER, encoding="utf-8"))["bl01"]
    rep = s["report_md"]
    added = []

    def add(rtype, rid, body, origin, relations=(), provenance=()):
        if memory.get(rid):
            return
        memory.append(rtype, rid, body, author=AUTHOR, origin=origin, project=PROJECT, family=FAMILY,
                      relations=list(relations), provenance=list(provenance), created_at=created_at)
        added.append(rid)

    pullbacks = s["selection"]["events_seen"]
    closed = s["events"]["n_closed"]
    conversion = round(closed / pullbacks, 3)
    cells = s["vs_control_stratified"]["cells"]
    singletons = [c for c in cells if c["events"]["n"] == 1]

    if run["record_id"] == RUN_RECORD:  # analysis revision, written once
        body = copy.deepcopy(run["body"])
        body["alternative_explanations"] = [
            "sampling noise: 49 closed trades over 16 month blocks; the month-block CI95 of net expectancy "
            "[-0.061, 0.528] R contains 0",
            "direction drift: BUY n=29 +0.448 R vs SELL n=20 -0.008 R during a rising gold market; the stratified "
            "comparison controls for direction but cannot separate the H4 context from the trend itself",
            f"thin strata: {len(singletons)} of {len(cells)} usable cells hold a single event; the adjusted delta "
            "+0.269 R rests on few trades per cell and events beat controls in only 13/25 cells",
            "session concentration: TOKYO holds 18/49 trades (+0.524 R); other sessions are mixed",
            f"selection: {s['selection']['events_closed_share']:.3f} of setups close as trades vs "
            f"{s['selection']['controls_closed_share']:.3f} of controls; the confirmation and risk filters "
            "may select different market states for events and controls",
            "costs: Dukascopy spread (mean 0.055 R), no broker feed, no slippage or commission"]
        body["conclusions"] += [
            "INVESTIGATE under BL01_DECISION_RULES_V1: failed n_closed >= 60, month-block CI95 low > 0, "
            "event better in >= 60% of cells; passed the other six checks",
            "not evidence of an edge; no trading, sizing or EA change follows from it",
            "internal_validation is not read on an INVESTIGATE; preregistration and parameters unchanged",
            "next: a new preregistered question with its own hypothesis_id (H4 context vs matched control), "
            "or BL-02 on unseen data (PROP-BL02_POWERED_REPLICATION)"]
        body["limits"] += ["analysis revision: alternative explanations written after reading the run, "
                           "they are explanations to test, not findings",
                           "peak_rss_mb not recorded on Windows (null): memory cost of a rerun unknown "
                           "(PROP-WINDOWS_PEAK_RSS)", "tick audit PASS_WITH_NOTES: 0 anomalies, "
                           "325 ticks above the spread cap out of 72,159,303; no data anomaly"]
        add("EXPERIMENT", RUN_RECORD + ".A1", body, "HUMAN",
            relations=[{"type": "SUPERSEDES", "target": RUN_RECORD}, {"type": "TESTS", "target": HYP}],
            provenance=run["provenance"] + [_src(os.path.join(RUN_DIR, "report.transcribed.md"))])

    mde = power["mde_net_r_80pct"]
    add("OBSERVATION", "OBS-BL01-FEASIBILITY-OBSERVED-V1", {
        "statement": f"BL-01 discovery saw {pullbacks} H4 pullbacks (power study 90% range "
                     f"{power['expected_pullbacks_90pct']}) and {closed} closed trades: conversion {conversion}, "
                     "below the 0.6 scenario; P(n >= 60) was 0.093 at 0.6, and the run ended INVESTIGATE as the "
                     f"study expected. The observed +0.262 R is below the 0.568 R minimum effect detectable at 50 "
                     "trades, so a CI excluding 0 was not expected even if the effect were real",
        "scope": "STRUCTURAL_HEALTH",
        "dataset": {"dataset_id": s["dataset_id"], "sha256": s["data_checks"]["manifest"]["sha256"],
                    "split": "discovery", "period": "2023-02-04..2024-08-04", "exposure": "UNSEEN"},
        "values": {"h4_bars": s["detector_health"]["IMPULSE"]["n_bars"],
                   "impulses": s["detector_health"]["IMPULSE"]["n_events"], "pullbacks": pullbacks,
                   "closed_trades": closed, "pullback_to_trade_conversion": conversion,
                   "funnel_events": s["funnel_events"], "predicted_expected_pullbacks": power["expected_pullbacks"],
                   "predicted_p_trades_ge_60": power["p_trades_ge_60"], "predicted_mde_net_r_80pct": mde,
                   "observed_net_expectancy_r": s["events"]["expectancy_r_net"],
                   "observed_ci95_month_blocks": [s["events"]["expectancy_r_net_ci95_month_blocks"]["low"],
                                                  s["events"]["expectancy_r_net_ci95_month_blocks"]["high"]],
                   "run_seconds": s["total_seconds"], "read_ticks_seconds": s["timings_s"]["read_ticks_and_build_bars"]},
        "evidence_level": "EXPLORATORY",
        "not_evidence_for": ["presence or absence of an edge", "changing BL-01 parameters or decision rules",
                             "choosing a minimum effect for BL-02 from the observed mean"]},
        "HUMAN", relations=[{"type": "DERIVED_FROM", "target": RUN_RECORD},
                            {"type": "REFINES", "target": "OBS-BL01-POWER-ANALYSIS-V1"}],
        provenance=[_src(SUMMARY), _src(POWER)])

    common = {"status": "PROPOSED", "reversible": True, "touches_frozen_or_live": False,
              "revert_plan": "proposal only: nothing is applied; an accepted change is reverted with its PR"}
    add("IMPROVEMENT_PROPOSAL", _pid("H4_CONTEXT_VS_MATCHED_CONTROL"), dict(common,
        proposal_class="NEW_HYPOTHESIS",
        title="new question: does the H4 impulse-pullback context change M15 outcomes against a matched control?",
        rationale="BL-01 ended INVESTIGATE: +0.269 R adjusted delta vs control but events better in 13/25 cells, "
                  "most cells with 1-2 events. The runner's own next step is a separate preregistered question on "
                  "the context effect alone. The BL-H4M15 family has used its 6-hypothesis budget, so this needs "
                  "an explicit budget decision first.",
        steps=["person decides whether the family budget is raised or an existing proposal-only hypothesis retired",
               "write the question with a new hypothesis_id: matched control (same direction, session, ATR tercile, "
               "month), primary outcome the paired difference",
               "size it with power.simulate_bl01_rule on data it has not seen (BL-02 window), not on discovery",
               "freeze the preregistration in its own commit before any data access"],
        requires=["HUMAN_APPROVAL", "NEW_PREREGISTRATION"],
        baseline={"metric": "preregistered questions on the H4 context effect", "value": 0},
        success_criterion="a frozen preregistration with its own hypothesis_id, sized on unseen data"),
        "AI_PROPOSAL", relations=[{"type": "DERIVED_FROM", "target": RUN_RECORD}], provenance=[_src(SUMMARY)])
    add("IMPROVEMENT_PROPOSAL", _pid("RUN_ARTIFACT_TRANSFER"), dict(common,
        proposal_class="PROCESS_IMPROVEMENT",
        title="tooling: a reviewed channel for byte-identical run outputs from the research PC",
        rationale="BL-01 summary.json (47935 bytes, sha256 61a5cd9b...) stays on the research PC: the bridge "
                  "session's safety policy refuses to encode whole files. Memory holds a declared transcription "
                  "with the original hash; the hash cannot be recomputed from the cloud.",
        steps=["person picks the channel: the PC session commits data/bl01/<run>/discovery/summary.json to a "
               "results branch, or the runner writes a summary with only aggregate fields",
               "the importer recomputes the sha256 and refuses a mismatch",
               "keep events.csv and controls.csv on the PC unless the person decides otherwise"],
        requires=["HUMAN_APPROVAL", "DEDICATED_METHOD_TEST"],
        baseline={"metric": "real runs in memory whose summary sha256 is recomputable in the repo", "rate": 0.0,
                  "n": 1},
        success_criterion="the next real run's summary is imported from a file whose sha256 the importer checks"),
        "AI_PROPOSAL", relations=[{"type": "DERIVED_FROM", "target": RUN_RECORD}], provenance=[_src(SUMMARY)])
    add("IMPROVEMENT_PROPOSAL", _pid("WINDOWS_PEAK_RSS"), dict(common,
        proposal_class="PROCESS_IMPROVEMENT",
        title="tooling: record peak memory on Windows runs",
        rationale="run_experiment.peak_rss_mb returned null on the research PC (resource module is POSIX only); "
                  f"the discovery took {s['total_seconds']} s, {s['timings_s']['read_ticks_and_build_bars']} s "
                  "of it reading ticks, and its memory cost is unknown.",
        steps=["fall back to psutil or GetProcessMemoryInfo when resource is missing",
               "unit test with the fallback mocked"],
        requires=["HUMAN_APPROVAL", "DEDICATED_METHOD_TEST"],
        baseline={"metric": "Windows runs with peak memory recorded", "rate": 0.0, "n": 1},
        success_criterion="the next Windows run records a non-null peak_rss_mb"),
        "AI_PROPOSAL", relations=[{"type": "DERIVED_FROM", "target": RUN_RECORD}], provenance=[_src(SUMMARY)])
    if added:
        memory.checkpoint("BL-01 discovery analysis recorded")
    return added


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--memory", default=DEFAULT_PATH)
    args = ap.parse_args()
    m = ResearchMemory(args.memory)
    print(json.dumps({"added": record(m), "problems": m.verify()}, indent=1))
