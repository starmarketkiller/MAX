"""Write the BL-01 power study into Research Memory (append-only, idempotent).

Run from server/research_scripts after run_study:
    python -m bl_power_study_v1.record_knowledge [--memory PATH]
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

REPORT = os.path.join(HERE, "bl01_power_report_v1.json")
DRAFT = os.path.join(HERE, "BL-02_proposal_draft_v0.json")
REL = "server/research_scripts/bl_power_study_v1/"
HYP = "HYP-BL-H4M15-IPC-001"
PROJECT, FAMILY = "NEXUS_TRADING_RESEARCH", "BL-H4M15"
DECIDER = "max (decision 2026-10-11, recorded by claude-trading-research)"


def _pid(check):
    return f"PROP-{check}-{sha256_text(FAMILY + '|' + check)[:10].upper()}"


def record(memory, created_at=None):
    rep = json.load(open(REPORT, encoding="utf-8"))
    rep_src = {"kind": "FILE", "ref": REL + "bl01_power_report_v1.json", "sha256": sha256_file(REPORT)}
    added = []

    def add(rtype, rid, body, origin, author, relations=(), provenance=()):
        if memory.get(rid):
            return
        memory.append(rtype, rid, body, author=author, origin=origin, project=PROJECT, family=FAMILY,
                      relations=list(relations), provenance=list(provenance), created_at=created_at)
        added.append(rid)

    s = rep["inputs_structural"]
    add("OBSERVATION", "OBS-BL-H4-PULLBACK-FREQUENCY-2019-2022", {
        "statement": "H4 setup frequency, not trade count: 55.65 pullbacks per year (167 in 3.0 years), monthly "
                     "counts Poisson-like (dispersion 0.98); BL-01 discovery (1.5 years) should see about 83 "
                     "pullbacks (90%: 68-98) and fewer trades, by an unmeasured pullback-to-trade conversion",
        "scope": "STRUCTURAL_HEALTH",
        "dataset": {"dataset_id": "MARKET_STATE_V1_436265d450475aaa",
                    "sha256": "4f4a248ddfab4f0dafcab5274633e3001c9b6adcb922b71c733069668cf7ebcb",
                    "split": "outside_splits", "period": "2019-02-03..2022-02-03", "exposure": "DISCOVERY_REUSE"},
        "values": s, "evidence_level": "EXPLORATORY",
        "not_evidence_for": ["the number of BL-01 trades (needs M15 confirmation and filters)",
                             "any outcome of BL-H4M15-IPC-001", "any BL-01 split"]},
        "HUMAN", "claude-trading-research", relations=[{"type": "SAME_FAMILY", "target": HYP},
                                                       {"type": "REFINES", "target": "OBS-BL-H4-SELECTIVITY-2019-2022"}],
        provenance=[rep_src])

    b = rep["bl01"]
    lv1 = b["loop_v1_replication"]
    key = {row["delta_p"]: row for row in b["scenarios"]}
    add("OBSERVATION", "OBS-BL01-POWER-ANALYSIS-V1", {
        "statement": "BL-01 as preregistered is a descriptive and feasibility run: under its own decision rule GO "
                     "needs >= 60 trades, reached with probability 0.09 at conversion 0.6 and 0.81 at 0.8; with "
                     "an 8-point true lift GO is 1-14%, INVESTIGATE 75-83% (conversion 0.6-0.8, month SD 0.05). The earlier 24%/372 figure used a "
                     "different test (one-sample z on p_target_first, alpha 0.05/6, n=80 assumed trades, no costs)",
        "scope": "DESCRIPTIVE",
        "dataset": {"dataset_id": "SYNTHETIC_MONTE_CARLO_BL_POWER_V1", "sha256": sha256_file(REPORT),
                    "split": "outside_splits", "exposure": "UNSEEN"},
        "values": {"loop_v1_replication": {k: lv1[k] for k in ("analytic_power", "simulated_power", "n_for_80pct",
                                                                "alpha", "n", "p0", "p1")},
                   "p_trades_ge_60": b["p_trades_ge_60"], "p_trades_ge_30": b["p_trades_ge_30"],
                   "mde_net_r_80pct": b["mde_net_r_80pct"],
                   "rule_decisions_conv0.6_msd0.05": {str(dp): key[dp]["rule_conv0.6_msd0.05"] for dp in key},
                   "rule_decisions_conv0.8_msd0.05": {str(dp): key[dp]["rule_conv0.8_msd0.05"] for dp in key},
                   "assumptions": rep["assumptions"]},
        "evidence_level": "EXPLORATORY",
        "not_evidence_for": ["presence or absence of an edge", "choosing the BL-01 minimum effect",
                             "changing BL-01 parameters or decision rules"]},
        "HUMAN", "claude-trading-research",
        relations=[{"type": "SAME_FAMILY", "target": HYP},
                   {"type": "DERIVED_FROM", "target": "OBS-BL-H4-PULLBACK-FREQUENCY-2019-2022"}],
        provenance=[rep_src])

    placeholder = memory.current("EXP-BL-01-DISCOVERY")
    if placeholder and placeholder["body"]["status"] == "NOT_RUN" and not memory.get("EXP-BL-01-DISCOVERY.R1"):
        body = copy.deepcopy(placeholder["body"])
        body["limits"] += [
            "power: under BL01_DECISION_RULES_V1 the discovery split is expected to give about 33-67 trades; "
            "GO is structurally unlikely below about 0.7 pullback-to-trade conversion (OBS-BL01-POWER-ANALYSIS-V1)",
            "MDE of the CI criterion at 50 trades about 0.57 R net: only large effects are detectable"]
        body["conclusions"] += [
            "decision (max, 2026-10-11): preregistration kept unchanged; no period extension; minimum effect "
            "not raised; discovery reports descriptive results, a preliminary reading and feasibility only",
            "discovery outcomes are never used to change parameters or to pick an effect size afterwards"]
        body["decision"] = "PENDING_DESCRIPTIVE_AND_FEASIBILITY_RUN"
        add("EXPERIMENT", "EXP-BL-01-DISCOVERY.R1", body, "HUMAN", DECIDER,
            relations=[{"type": "SUPERSEDES", "target": placeholder["record_id"]},
                       {"type": "TESTS", "target": HYP},
                       {"type": "DERIVED_FROM", "target": "OBS-BL01-POWER-ANALYSIS-V1"}],
            provenance=[rep_src] + placeholder["provenance"])

    common = {"status": "PROPOSED", "reversible": True, "touches_frozen_or_live": False,
              "revert_plan": "proposal only: nothing is applied; an accepted change is reverted with its PR"}
    add("IMPROVEMENT_PROPOSAL", _pid("POWER_MODEL_MISMATCH"), dict(common,
        proposal_class="PROCESS_IMPROVEMENT",
        title="method: the synthetic dry run must simulate the preregistered decision rule",
        rationale="RI-02 SYNTHETIC_DRY_RUN tested p_target_first with a one-sample z-test at 0.05/6 on an assumed "
                  "80 events; BL-01 decides on a month-block CI of net expectancy, n >= 60, quarters and a cost "
                  "stress. The two give different power (0.20 vs 0.01-0.13 for the same lift).",
        steps=["let a plan name its decision model; use power.simulate_bl01_rule for Behavior Lab plans",
               "derive expected trades from structural rate x conversion, not from the setup count",
               "validate on synthetic worlds where the true power is known"],
        requires=["HUMAN_APPROVAL", "DEDICATED_METHOD_TEST"],
        baseline={"metric": "plans whose dry run models their own decision rule", "rate": 0.0, "n": 1},
        success_criterion="every Behavior Lab plan's dry run reproduces the decision-rule power within 0.05 "
                          "on a synthetic world with known effect"),
        "AI_PROPOSAL", "claude-trading-research",
        relations=[{"type": "DERIVED_FROM", "target": "OBS-BL01-POWER-ANALYSIS-V1"}], provenance=[rep_src])
    add("IMPROVEMENT_PROPOSAL", _pid("PLANNING_ALPHA_FAMILY"), dict(common,
        proposal_class="PROCESS_IMPROVEMENT",
        title="method: planning alpha counts tests that are preregistered, planned or run",
        rationale="overfitting.check_plan divides alpha by every hypothesis of the correlated family, including "
                  "untested AI alternatives. A preregistered primary hypothesis was then held to 0.05/6 although "
                  "its own preregistration declares a family of 1. Untested proposals should enter the family "
                  "when they are planned, which still keeps the bar from loosening.",
        steps=["count run + planned tests, plus the one being planned",
               "keep the conservative count for generated hypotheses planned in the same cycle",
               "regression test: BL-01 primary keeps alpha 0.05; two planned siblings share 0.05/3"],
        requires=["HUMAN_APPROVAL", "DEDICATED_METHOD_TEST"],
        baseline={"metric": "preregistered primaries planned with their declared alpha", "rate": 0.0, "n": 1},
        success_criterion="all preregistered primary hypotheses are planned with their declared alpha while "
                          "sibling tests planned together still share it"),
        "AI_PROPOSAL", "claude-trading-research",
        relations=[{"type": "DERIVED_FROM", "target": "OBS-BL01-POWER-ANALYSIS-V1"}], provenance=[rep_src])
    add("IMPROVEMENT_PROPOSAL", _pid("BL02_POWERED_REPLICATION"), dict(common,
        proposal_class="INSUFFICIENT_EVIDENCE",
        title="BL-02: separate preregistered experiment on unseen 2008-2018 XAUUSD data",
        rationale="BL-01 discovery can only detect net effects of about 0.45-0.7 R. BL-02 tests the same frozen "
                  "hypothesis on data no NEXUS study has read; 11 years reach a 0.19-0.26 R minimum effect "
                  "(conversion 0.8-0.4). Draft: " + REL + "BL-02_proposal_draft_v0.json",
        steps=["person confirms the 0.20 R minimum effect and the window", "register the window as UNSEEN",
               "download and integrity-audit on the research PC", "freeze the preregistration in its own commit",
               "request RUN_EXPERIMENT_REAL_DATA through the approval bridge"],
        requires=["HUMAN_APPROVAL", "MORE_DATA", "BETTER_DESIGN"],
        baseline={"metric": "minimum detectable net effect (R) for BL-H4M15-IPC-001", "value": 0.57,
                  "at_trades": 50},
        success_criterion="a frozen BL-02 preregistration whose expected trades reach 80% power at its declared "
                          "minimum effect, or an explicit UNDERPOWERED label stating the reachable MDE"),
        "AI_PROPOSAL", "claude-trading-research",
        relations=[{"type": "DERIVED_FROM", "target": "OBS-BL01-POWER-ANALYSIS-V1"}],
        provenance=[rep_src, {"kind": "FILE", "ref": REL + "BL-02_proposal_draft_v0.json", "sha256": sha256_file(DRAFT)}])
    if added:
        memory.checkpoint("BL-01 power study recorded")
    return added


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--memory", default=DEFAULT_PATH)
    args = ap.parse_args()
    m = ResearchMemory(args.memory)
    print(json.dumps({"added": record(m), "problems": m.verify()}, indent=1))
