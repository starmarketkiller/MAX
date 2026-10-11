"""Research Intelligence V1 (RI-01): deterministic tests.

All memories are temporary files; source registries are read, never written.
The end-to-end case at the bottom is synthetic: the experiment and its numbers
are invented for the test.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import pytest

RESEARCH = Path(__file__).resolve().parents[1] / "research_scripts"
sys.path.insert(0, str(RESEARCH))

from research_intelligence_v1 import cli, gates, ingest, pilot, priority_queue, proposals, review  # noqa: E402
from research_intelligence_v1.generator import register_candidates  # noqa: E402
from research_intelligence_v1.hypotheses import (BudgetExhausted, DuplicateHypothesis,  # noqa: E402
                                                 FamilyBudget, register)
from research_intelligence_v1.memory import MemoryViolation, ResearchMemory, sha256_file  # noqa: E402

T0 = "2026-10-11T00:00:00+00:00"


@pytest.fixture
def mem(tmp_path):
    return ResearchMemory(str(tmp_path / "memory.jsonl"))


def spec(**over):
    s = {"event_family": "SYNTH_EVENT", "direction": "LONG",
         "state_conditions": [{"feature_id": "atr_ratio", "operator": ">=", "threshold": 1.5},
                              {"feature_id": "session", "operator": "==", "threshold": "london"}],
         "outcome_definition": "+1R before -1R", "mechanism": "synthetic mechanism",
         "falsification": "synthetic falsification", "data_needed": ["SYNTH_DATA"],
         "overfitting_risk": "LOW", "expected_information_value": "HIGH"}
    s.update(over)
    return s


def synth_experiment(memory, exp_id="EXP-SYNTH-001", hyp="HYP-SYNTH-BASE", **body_over):
    body = {"hypothesis_id": hyp[4:], "status": "COMPLETED", "result": "INCONCLUSIVE",
            "datasets": [{"dataset_id": "SYNTH_DATA", "split": "discovery", "exposure": "UNSEEN"}],
            "method": {"description": "synthetic", "params_sha256": "a" * 64, "code_commit": "b" * 40,
                       "preregistered": True, "control": "synthetic control", "multiple_testing_family": "SYN"},
            "metrics": {"n_closed": 12, "expectancy_ci95": [-0.2, 0.3]},
            "data_checks": {"alignment_mismatches": 0}, "resources": {"total_seconds": 10, "peak_rss_mb": 100},
            "limits": [], "anomalies": [], "alternative_explanations": [], "conclusions": ["synthetic"],
            "evidence_level": "DISCOVERY_ONLY", "decision": "INVESTIGATE"}
    body.update(body_over)
    return memory.append("EXPERIMENT", exp_id, body, author="test", origin="HUMAN", project="SYNTH",
                         family="SYN", relations=[{"type": "TESTS", "target": hyp}], created_at=T0)


def base_hypothesis(memory):
    return register(memory, "SYNTH-BASE", spec(), statement="synthetic base", origin="HUMAN", author="test",
                    project="SYNTH", family="SYN", lifecycle_state="PREREGISTERED", created_at=T0)


# ---- memory --------------------------------------------------------------------------------------------
def test_append_validates_and_chains(mem):
    a = base_hypothesis(mem)
    b = synth_experiment(mem)
    assert a["prev_hash"] == "0" * 64 and b["prev_hash"] == a["record_hash"]
    assert mem.verify() == []
    assert ResearchMemory(mem.path).verify() == []


def test_schema_rejects_bad_record(mem):
    with pytest.raises(MemoryViolation):
        mem.append("EXPERIMENT", "EXP-BAD", {"status": "COMPLETED"}, author="t", origin="HUMAN", project="P",
                   family="F")
    with pytest.raises(MemoryViolation):
        mem.append("OBSERVATION", "bad id", {}, author="t", origin="HUMAN", project="P", family="F")


def test_records_are_immutable(mem):
    base_hypothesis(mem)
    with pytest.raises(MemoryViolation):
        register(mem, "SYNTH-BASE", spec(outcome_definition="other"), statement="x", origin="HUMAN",
                 author="t", project="SYNTH", family="SYN")


def test_relations_must_point_to_existing_records(mem):
    with pytest.raises(MemoryViolation):
        synth_experiment(mem, hyp="HYP-NOT-THERE")


def test_tampering_is_detected(mem):
    base_hypothesis(mem)
    synth_experiment(mem)
    lines = Path(mem.path).read_text().splitlines()
    rec = json.loads(lines[1])
    rec["body"]["result"] = "POSITIVE"
    lines[1] = json.dumps(rec)
    Path(mem.path).write_text("\n".join(lines) + "\n")
    problems = ResearchMemory(mem.path).verify()
    assert any("content changed" in p for p in problems)


def test_deleted_line_breaks_chain(mem):
    base_hypothesis(mem)
    synth_experiment(mem)
    synth_experiment(mem, exp_id="EXP-SYNTH-002")
    lines = Path(mem.path).read_text().splitlines()
    Path(mem.path).write_text("\n".join([lines[0], lines[2]]) + "\n")
    assert any("chain broken" in p for p in ResearchMemory(mem.path).verify())


def test_supersedes_keeps_old_record(mem):
    base_hypothesis(mem)
    synth_experiment(mem)
    mem.append("EXPERIMENT", "EXP-SYNTH-001.C1", dict(mem.get("EXP-SYNTH-001")["body"], conclusions=["fixed"]),
               author="t", origin="HUMAN", project="SYNTH", family="SYN",
               relations=[{"type": "SUPERSEDES", "target": "EXP-SYNTH-001"}])
    assert mem.current("EXP-SYNTH-001")["record_id"] == "EXP-SYNTH-001.C1"
    assert mem.get("EXP-SYNTH-001")["body"]["conclusions"] == ["synthetic"]


# ---- dedup and budget -----------------------------------------------------------------------------------
@pytest.mark.parametrize("variant", [
    {"event_family": " synth_event ", "direction": "long"},
    {"state_conditions": [{"feature_id": "SESSION", "operator": "=", "threshold": " LONDON "},
                          {"feature_id": "atr_ratio", "operator": ">=", "threshold": "1.50"}]},
    {"outcome_definition": "+1R   before -1R", "mechanism": "worded differently"},
])
def test_duplicates_are_refused_without_writing(mem, variant):
    base_hypothesis(mem)
    before = Path(mem.path).read_bytes()
    with pytest.raises(DuplicateHypothesis) as exc:
        register(mem, "SYNTH-DUP", spec(**variant), statement="same idea", origin="AI_PROPOSAL", author="t",
                 project="SYNTH", family="SYN")
    assert exc.value.existing_id == "HYP-SYNTH-BASE"
    assert Path(mem.path).read_bytes() == before


def test_generated_hypothesis_is_proposal_only(mem):
    rec = register(mem, "SYNTH-GEN", spec(), statement="g", origin="AI_PROPOSAL", author="t", project="SYNTH",
                   family="SYN", evidence_level="INTERNAL_VALIDATION")
    assert rec["body"]["evidence_level"] == "NONE_PROPOSAL" and rec["body"]["is_proposal_only"]
    with pytest.raises(ValueError):
        register(mem, "SYNTH-GEN2", spec(direction="SHORT"), statement="g", origin="RULE_ENGINE", author="t",
                 project="SYNTH", family="SYN", lifecycle_state="SUPPORTED")


def test_hypothesis_must_declare_mechanism_and_falsification(mem):
    with pytest.raises(ValueError):
        register(mem, "SYNTH-X", spec(falsification=""), statement="x", origin="HUMAN", author="t",
                 project="SYNTH", family="SYN")


def test_family_budget(mem):
    budget = FamilyBudget(mem, max_hypotheses_per_family=2)
    register(mem, "BUD-1", spec(direction="LONG"), statement="1", origin="RULE_ENGINE", author="t", project="P",
             family="F", budget=budget)
    register(mem, "BUD-2", spec(direction="SHORT"), statement="2", origin="RULE_ENGINE", author="t", project="P",
             family="F", budget=budget)
    with pytest.raises(BudgetExhausted):
        register(mem, "BUD-3", spec(direction="ANY"), statement="3", origin="RULE_ENGINE", author="t", project="P",
                 family="F", budget=budget)
    assert len(mem.of_type("HYPOTHESIS")) == 2


# ---- gates ------------------------------------------------------------------------------------------------
def good_proposal(**over):
    p = {"proposal_class": "PROCESS_IMPROVEMENT", "title": "cache bars", "rationale": "slow",
         "steps": ["cache"], "status": "PROPOSED", "reversible": True, "revert_plan": "revert PR",
         "touches_frozen_or_live": False, "requires": ["HUMAN_APPROVAL"]}
    p.update(over)
    return p


def test_gates_on_proposals():
    gates.check_proposal(good_proposal())
    bad = [good_proposal(reversible=False), good_proposal(revert_plan=" "),
           good_proposal(title="raise RiskPercent on NEXUS_EA live"),
           good_proposal(touches_frozen_or_live=True, requires=["REGRESSION_TEST"]),
           good_proposal(proposal_class="NEW_HYPOTHESIS"),
           good_proposal(proposal_class="DEFECT_FIX", requires=["REGRESSION_TEST"]),
           good_proposal(title="method change", requires=["HUMAN_APPROVAL"]),
           good_proposal(status="ACCEPTED")]
    for body in bad:
        with pytest.raises(gates.GateViolation):
            gates.check_proposal(body)


def test_protected_splits_and_promotion():
    assert gates.protected_splits() == {"locked_validation", "final_holdout"}
    for split in ("locked_validation", "final_holdout"):
        with pytest.raises(gates.GateViolation):
            gates.assert_no_automatic_protected_access(split)
    gates.assert_no_automatic_protected_access("discovery")
    with pytest.raises(gates.GateViolation):
        gates.assert_promotion_allowed("SUPPORTED", "DISCOVERY_ONLY")
    gates.assert_promotion_allowed("SUPPORTED", "INTERNAL_VALIDATION")
    with pytest.raises(gates.GateViolation):
        gates.assert_params_frozen(pilot.PARAMS_SHA, "0" * 64)
    gates.assert_params_frozen(pilot.PARAMS_SHA, pilot.PARAMS_SHA)


def test_decisions_are_human_and_reversible(mem):
    base_hypothesis(mem)
    synth_experiment(mem)
    _, new, _ = review.review(mem, "EXP-SYNTH-001", created_at=T0)
    pid = new[0]["record_id"]
    for who in ("rule-engine", "ai-reviewer", "jarvis", "auto", ""):
        with pytest.raises(gates.GateViolation):
            proposals.decide(mem, pid, "ACCEPTED", decided_by=who, note="x")
    with pytest.raises(gates.GateViolation):
        proposals.decide(mem, pid, "IMPLEMENTED", decided_by="max", note="skip acceptance")
    proposals.decide(mem, pid, "ACCEPTED", decided_by="max", note="ok")
    proposals.decide(mem, pid, "IMPLEMENTED", decided_by="max", note="PR #x")
    last = proposals.decide(mem, pid, "REVERTED", decided_by="max", note="worse")
    assert mem.current(pid)["record_id"] == last["record_id"]
    assert mem.get(pid)["body"]["status"] == "PROPOSED"
    assert mem.verify() == []


def test_negative_evidence_preserved(mem):
    base_hypothesis(mem)
    synth_experiment(mem, result="NEGATIVE")
    before = list(mem.records)
    gates.negative_evidence_preserved(before, mem.records)
    with pytest.raises(gates.GateViolation):
        gates.negative_evidence_preserved(before, before[:1])


# ---- review ------------------------------------------------------------------------------------------------
def test_review_findings_and_classes(mem):
    base_hypothesis(mem)
    synth_experiment(mem, data_checks={"alignment_mismatches": 3}, resources={},
                     metrics={"n_closed": 12, "detector_health": {"impulse": {"status": "OVER_FIRING"}}},
                     datasets=[{"dataset_id": "SYNTH_DATA", "split": "final_holdout", "exposure": "UNKNOWN"}])
    rev, new, _ = review.review(mem, "EXP-SYNTH-001", created_at=T0)
    by_check = {f["check"]: f for f in rev["body"]["findings"]}
    assert by_check["DATA_CHECK_FAILED"]["proposal_class"] == "DEFECT_FIX"
    assert by_check["PROTECTED_SPLIT_READ"]["severity"] == "BLOCKER"
    assert by_check["LOW_SAMPLE"]["proposal_class"] == "INSUFFICIENT_EVIDENCE"
    assert by_check["DETECTOR_UNHEALTHY"]["area"] == "DATA_QUALITY"
    assert by_check["NO_ALTERNATIVE_EXPLANATIONS"]["proposal_class"] == "NEW_HYPOTHESIS"
    assert by_check["RESOURCES_NOT_RECORDED"]["area"] == "TOOLING"
    assert {p["body"]["proposal_class"] for p in new} == {"DEFECT_FIX", "INSUFFICIENT_EVIDENCE",
                                                          "NEW_HYPOTHESIS", "PROCESS_IMPROVEMENT"}
    assert len(new) <= gates.MAX_PROPOSALS_PER_REVIEW
    assert all(p["body"]["status"] == "PROPOSED" and not p["body"]["touches_frozen_or_live"] for p in new)


def test_review_is_idempotent_and_does_not_duplicate_open_proposals(mem):
    base_hypothesis(mem)
    synth_experiment(mem)
    rev1, new1, _ = review.review(mem, "EXP-SYNTH-001", created_at=T0)
    n = len(mem.records)
    rev2, new2, _ = review.review(mem, "EXP-SYNTH-001", created_at=T0)
    assert rev2["record_id"] == rev1["record_id"] and new2 == [] and len(mem.records) == n
    synth_experiment(mem, exp_id="EXP-SYNTH-002")
    _, new3, linked = review.review(mem, "EXP-SYNTH-002", created_at=T0)
    assert new3 == [] and sorted(linked) == sorted(p["record_id"] for p in new1)


def test_clean_experiment_has_no_blocker(mem):
    base_hypothesis(mem)
    synth_experiment(mem, metrics={"n_closed": 200, "expectancy_ci95": [0.05, 0.3]}, result="POSITIVE",
                     datasets=[{"dataset_id": "SYNTH_DATA", "sha256": "c" * 64, "split": "discovery",
                                "exposure": "UNSEEN"}])
    rev, new, _ = review.review(mem, "EXP-SYNTH-001", created_at=T0)
    assert [f for f in rev["body"]["findings"] if f["severity"] == "BLOCKER"] == []
    assert new == []


# ---- ingestion -----------------------------------------------------------------------------------------
def test_phase7_26_import_is_idempotent_and_read_only(mem):
    sources = sorted((RESEARCH / "phase7" / "phase7_26").glob("*.json"))
    before = {p: sha256_file(p) for p in sources}
    r1 = ingest.import_phase7_26(mem)
    r2 = ingest.import_phase7_26(mem)
    assert len(r1["added"]) == 18 and r2["added"] == [] and len(r2["skipped"]) == 18
    assert r2["source_changed"] == []
    assert {p: sha256_file(p) for p in sources} == before
    assert mem.verify() == []
    neg = mem.get("EXP-EXP_LIQ_SWEEP_INTEGRITY_AUDIT")["body"]
    assert neg["result"] == "NEGATIVE" and any("override" in x for x in neg["limits"])


def test_behavior_lab_summary_adapter(mem, tmp_path):
    pilot.seed(mem, created_at=T0)
    summary = {"run_id": "BL01-SYNTH-DISCOVERY", "hypothesis_id": "BL-H4M15-IPC-001", "split": "discovery",
               "split_start": "2023-02-04", "split_end": "2024-08-04", "params_sha256": pilot.PARAMS_SHA,
               "git_commit": "d" * 40, "decision": {"decision": "INVESTIGATE"},
               "events": {"n_closed": 41, "expectancy_r_net": 0.02, "expectancy_r_net_ci95_month_blocks": [-0.1, 0.15],
                          "p_target_first": 0.35},
               "detector_health": {"impulse": {"n_events": 120, "firing_rate": 0.03, "status": "NORMAL"}},
               "data_checks": {"tick_audit": {"verdict": "PASS"}, "alignment_mismatches": [],
                               "reference_h4_mismatches": [], "manifest": {"verdict": "OK", "sha256": "e" * 64}},
               "total_seconds": 900, "peak_rss_mb": 800}
    path = tmp_path / "summary.json"
    path.write_text(json.dumps(summary))
    rec = ingest.import_behavior_lab_summary(mem, str(path), "HYP-BL-H4M15-IPC-001",
                                             supersedes="EXP-BL-01-DISCOVERY")
    assert rec["body"]["result"] == "INCONCLUSIVE" and rec["body"]["evidence_level"] == "DISCOVERY_ONLY"
    assert mem.current("EXP-BL-01-DISCOVERY")["record_id"] == rec["record_id"]
    assert mem.get("EXP-BL-01-DISCOVERY")["body"]["status"] == "NOT_RUN"
    rev, _, _ = review.review(mem, rec["record_id"])
    assert "CI_CROSSES_ZERO" in {f["check"] for f in rev["body"]["findings"]}


# ---- BL-01 pilot ---------------------------------------------------------------------------------------
def test_bl01_pilot_keeps_preregistration_and_separates_exploratory(mem):
    pilot.seed(mem, created_at=T0)
    again = pilot.seed(mem, created_at=T0)
    assert again["added"] == []
    hyp = mem.get("HYP-BL-H4M15-IPC-001")["body"]
    obs = mem.get("OBS-BL-H4-SELECTIVITY-2019-2022")["body"]
    assert hyp["lifecycle_state"] == "PREREGISTERED" and not hyp["is_proposal_only"]
    assert obs["evidence_level"] == "EXPLORATORY" and obs["dataset"]["split"] == "outside_splits"
    assert any("BL-H4M15-IPC-001" in x for x in obs["not_evidence_for"])
    assert obs["values"]["conversion_impulse_to_pullback"] == 0.913
    exp = mem.get("EXP-BL-01-DISCOVERY")["body"]
    assert exp["method"]["params_sha256"] == pilot.PARAMS_SHA and exp["status"] == "NOT_RUN"

    hyp_hash = mem.get("HYP-BL-H4M15-IPC-001")["record_hash"]
    report = pilot.generate_alternatives(mem, created_at=T0)
    assert len(report["registered"]) == 5 and len(report["over_budget"]) == 1
    assert mem.get("HYP-BL-H4M15-IPC-001")["record_hash"] == hyp_hash
    for rid in report["registered"]:
        b = mem.get(rid)["body"]
        assert b["is_proposal_only"] and b["evidence_level"] == "NONE_PROPOSAL"
        assert ("ALTERNATIVE_TO", "HYP-BL-H4M15-IPC-001") in [(r["type"], r["target"])
                                                               for r in mem.get(rid)["relations"]]
    # The preregistered hypothesis itself, re-proposed with different spelling, is refused.
    dup = dict(pilot.BL001_SPEC, event_family=pilot.BL001_SPEC["event_family"].lower(),
               state_conditions=list(reversed(pilot.BL001_SPEC["state_conditions"])))
    out = register_candidates(mem, [("BL-H4M15-REPROPOSED", dup, "same as 001")],
                              base_record="HYP-BL-H4M15-IPC-001", source_record="OBS-BL-H4-SELECTIVITY-2019-2022",
                              family="BL-H4M15", budget=None, author="t")
    assert out["duplicates"] == [{"candidate": "BL-H4M15-REPROPOSED", "existing": "HYP-BL-H4M15-IPC-001"}]
    assert mem.verify() == []


def test_queue_excludes_and_ranks(mem):
    pilot.seed(mem, created_at=T0)
    pilot.generate_alternatives(mem, created_at=T0)
    body = priority_queue.build_queue(mem, {pilot.DISCOVERY_DATA: True}, created_at=T0)
    excluded = {e["record_id"]: e["reason"] for e in body["excluded"]}
    assert "MACRO_CALENDAR_HISTORY" in excluded["HYP-BL-H4M15-ALT-MACRO-WINDOW"]
    assert "PREREGISTERED" in excluded["HYP-BL-H4M15-IPC-001"]
    assert [r["record_id"] for r in body["ranked"]][0] == "HYP-BL-H4M15-NULL-NO-PB"
    assert body["budget"]["max_runs_without_approval"] == 0 and body["budget"]["pf_is_a_criterion"] is False
    assert body["budget"]["per_test_alpha_bonferroni"]["BL-H4M15"] == pytest.approx(0.05 / 6)
    n = len(mem.records)
    priority_queue.build_queue(mem, {pilot.DISCOVERY_DATA: True}, created_at=T0)
    assert len(mem.records) == n
    empty = priority_queue.build_queue(mem, {}, write=False)
    assert empty["ranked"] == []


def test_queue_never_ranks_protected_split_data(mem):
    register(mem, "SYN-PROT", spec(data_needed=["XAU_final_holdout_ticks"]), statement="p", origin="AI_PROPOSAL",
             author="t", project="P", family="F")
    body = priority_queue.build_queue(mem, {"XAU_final_holdout_ticks": True}, write=False)
    assert body["ranked"] == [] and "one-shot" in body["excluded"][0]["reason"]


# ---- end to end (acceptance) -----------------------------------------------------------------------------
def test_end_to_end_acceptance(mem, tmp_path):
    """Read a concluded experiment, find a problem, propose a classified improvement,
    avoid a duplicate, register a new hypothesis, keep the original results unchanged."""
    base_hypothesis(mem)
    synth_experiment(mem, result="INCONCLUSIVE", metrics={"n_closed": 9},
                     data_checks={"alignment_mismatches": 2})
    original = Path(mem.path).read_bytes()
    exp_hash = mem.get("EXP-SYNTH-001")["record_hash"]

    # 1-2. read the concluded experiment and find criticalities
    rev, new, _ = review.review(mem, "EXP-SYNTH-001", created_at=T0)
    checks = {f["check"] for f in rev["body"]["findings"]}
    assert {"DATA_CHECK_FAILED", "LOW_SAMPLE", "NO_ALTERNATIVE_EXPLANATIONS"} <= checks
    # 3. classified improvement proposals, gated
    classes = {p["body"]["proposal_class"] for p in new}
    assert {"DEFECT_FIX", "INSUFFICIENT_EVIDENCE", "NEW_HYPOTHESIS"} <= classes
    defect = next(p for p in new if p["body"]["proposal_class"] == "DEFECT_FIX")
    assert {"DETERMINISTIC_REPRODUCTION", "REGRESSION_TEST", "IMPACT_ANALYSIS"} <= set(defect["body"]["requires"])
    # 4. a candidate identical to the base hypothesis is refused
    budget = FamilyBudget(mem)
    candidates = [("SYNTH-SAME", spec(event_family="synth_event "), "re-proposal"),
                  ("SYNTH-ALT", spec(state_conditions=[{"feature_id": "atr_ratio", "operator": ">=",
                                                        "threshold": 2}]), "stricter impulse")]
    out = register_candidates(mem, candidates, base_record="HYP-SYNTH-BASE", source_record=rev["record_id"],
                              family="SYN", budget=budget, author="t", origin="AI_PROPOSAL")
    assert out["duplicates"] == [{"candidate": "SYNTH-SAME", "existing": "HYP-SYNTH-BASE"}]
    # 5. a new hypothesis is registered, as a proposal
    assert out["registered"] == ["HYP-SYNTH-ALT"]
    assert mem.get("HYP-SYNTH-ALT")["body"]["evidence_level"] == "NONE_PROPOSAL"
    # 6. original results unchanged: same bytes at the head of the file, same hash, chain valid
    assert Path(mem.path).read_bytes().startswith(original)
    assert ResearchMemory(mem.path).get("EXP-SYNTH-001")["record_hash"] == exp_hash
    assert ResearchMemory(mem.path).verify() == []


def test_cli_round_trip(tmp_path, capsys):
    path = str(tmp_path / "m.jsonl")
    assert cli.main(["--memory", path, "seed-bl01"]) == 0
    assert cli.main(["--memory", path, "generate-bl01"]) == 0
    assert cli.main(["--memory", path, "review", "EXP-BL-01-DISCOVERY"]) == 0
    assert cli.main(["--memory", path, "queue", "--dry-run"]) == 0
    capsys.readouterr()
    assert cli.main(["--memory", path, "verify"]) == 0
    assert json.loads(capsys.readouterr().out)["problems"] == []


def test_committed_memory_is_valid():
    path = RESEARCH / "research_intelligence_v1" / "memory" / "research_memory_v1.jsonl"
    if not path.exists():
        pytest.skip("no committed memory")
    assert ResearchMemory(str(path)).verify() == []


def test_no_scheduler_or_network_in_package():
    pkg = RESEARCH / "research_intelligence_v1"
    text = "\n".join(p.read_text() for p in pkg.glob("*.py"))
    for banned in ("import sched", "crontab", "APScheduler", "time.sleep", "requests.", "urllib", "socket", "subprocess",
                   "anthropic", "openai", "MetaTrader5", "OrderSend("):
        assert banned not in text, banned
