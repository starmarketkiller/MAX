"""Research loop (RI-02): authorization, planning, overfitting controls, approval bridge,
persistent state machine, improvement evaluation.

Every dataset, summary and number here is synthetic. No tick data is read.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import pytest

RESEARCH = Path(__file__).resolve().parents[1] / "research_scripts"
sys.path.insert(0, str(RESEARCH))

from research_intelligence_v1 import (agents, authorization, evaluation, overfitting, pilot,  # noqa: E402
                                      planner, proposals)
from research_intelligence_v1.approval_bridge import ApprovalBridge  # noqa: E402
from research_intelligence_v1.hypotheses import register  # noqa: E402
from research_intelligence_v1.loop import STEPS, ResearchLoop  # noqa: E402
from research_intelligence_v1.memory import MemoryViolation, ResearchMemory, canonical, sha256_text  # noqa: E402

T0 = "2026-10-11T00:00:00+00:00"
FRESH = "SYNTH_FRESH_TICKS"


@pytest.fixture
def mem(tmp_path):
    return ResearchMemory(str(tmp_path / "memory.jsonl"))


@pytest.fixture
def bridge(tmp_path):
    return ApprovalBridge(str(tmp_path / "queue.json"), str(tmp_path / "ledger.jsonl"), tenant_id="tenant-1")


def base_spec(**over):
    s = {"event_family": "SYNTH_IMPULSE", "direction": "WITH_IMPULSE",
         "state_conditions": [{"feature_id": "impulse_atr", "operator": ">=", "threshold": 1.5},
                              {"feature_id": "retrace", "operator": ">=", "threshold": 0.382}],
         "outcome_definition": "+2R before -1R", "mechanism": "synthetic continuation flow",
         "falsification": "p_target_first not above control on fresh data", "data_needed": [FRESH],
         "overfitting_risk": "MEDIUM", "expected_information_value": "HIGH"}
    s.update(over)
    return s


def seed_base(memory):
    return register(memory, "SYN-BASE-001", base_spec(), statement="synthetic base", origin="HUMAN",
                    author="test", project="SYNTH", family="SYN", lifecycle_state="PREREGISTERED", created_at=T0)


def summary(tmp_path, run_id, *, n_closed=12, with_hash=False, decision="INVESTIGATE"):
    s = {"run_id": run_id, "hypothesis_id": "SYN-BASE-001", "split": "discovery", "split_start": "2027-01-01",
         "split_end": "2027-06-01", "params_sha256": "a" * 64, "git_commit": "b" * 40,
         "decision": {"decision": decision},
         "events": {"n_closed": n_closed, "expectancy_r_net": 0.01,
                    "expectancy_r_net_ci95_month_blocks": [-0.2, 0.2], "p_target_first": 0.34},
         "detector_health": {"impulse": {"n_events": 50, "firing_rate": 0.03, "status": "NORMAL"}},
         "data_checks": {"tick_audit": {"verdict": "PASS"}, "alignment_mismatches": [], "reference_h4_mismatches": [],
                         "manifest": {"verdict": "OK", **({"sha256": "e" * 64} if with_hash else {})}},
         "total_seconds": 30, "peak_rss_mb": 200}
    path = tmp_path / f"{run_id}.json"
    path.write_text(json.dumps(s))
    return str(path)


def catalog(expected_events=2000, dataset_id=FRESH):
    return {FRESH: {"dataset_id": dataset_id, "split": "discovery", "period": "2027-01..2027-06",
                    "real_data": True, "estimated_seconds": 600, "expected_events": expected_events}}


def make_loop(memory, bridge, **kw):
    kw.setdefault("availability", {FRESH: True})
    kw.setdefault("dataset_catalog", catalog())
    kw.setdefault("created_at", T0)
    return ResearchLoop(memory, bridge=bridge, **kw)


# ---- authorization ------------------------------------------------------------------------------
@pytest.mark.parametrize("kind,params,mode", [
    ("REVIEW_EXPERIMENT", {}, "AUTO_SAFE"),
    ("SYNTHETIC_DRY_RUN", {"rows": 1000, "estimated_seconds": 1}, "AUTO_SAFE"),
    ("SYNTHETIC_DRY_RUN", {"rows": 10_000_000}, "APPROVAL_REQUIRED"),
    ("SYNTHETIC_DRY_RUN", {"estimated_seconds": 600}, "APPROVAL_REQUIRED"),
    ("REVIEW_EXPERIMENT", {"real_data": True}, "APPROVAL_REQUIRED"),
    ("RUN_EXPERIMENT_REAL_DATA", {"real_data": True}, "APPROVAL_REQUIRED"),
    ("NEW_VARIANT", {}, "APPROVAL_REQUIRED"),
    ("METHOD_CHANGE", {}, "APPROVAL_REQUIRED"),
    ("INGEST_AVAILABLE_REPORT", {"requires_authorization": True}, "APPROVAL_REQUIRED"),
    ("RUN_EXPERIMENT_REAL_DATA", {"dataset": {"split": "final_holdout"}}, "PROHIBITED"),
    ("REVIEW_EXPERIMENT", {"split": "locked_validation"}, "PROHIBITED"),
    ("RUN_EXPERIMENT_REAL_DATA", {"params_sha256": "1", "preregistered_params_sha256": "2"}, "PROHIBITED"),
    ("GENERATE_PROPOSALS", {"target_lifecycle": "SUPPORTED"}, "PROHIBITED"),
    ("METHOD_CHANGE", {"paths": ["server/research_scripts/research_intelligence_v1/gates.py"]}, "PROHIBITED"),
    ("GENERATE_PROPOSALS", {"description": "raise RiskPercent in NEXUS_EA_v2.mq5"}, "PROHIBITED"),
    ("LIVE_TRADING", {}, "PROHIBITED"),
    ("PROMOTE_STRATEGY", {}, "PROHIBITED"),
    ("SOMETHING_NEW", {}, "PROHIBITED"),
])
def test_authorization_modes(kind, params, mode):
    assert authorization.classify(kind, params)[0] == mode


def test_dynamic_checks_only_tighten():
    for kind, base in authorization.CATALOG.items():
        for params in ({"real_data": True}, {"split": "final_holdout"}, {"estimated_seconds": 10 ** 6}):
            got = authorization.classify(kind, params)[0]
            assert authorization.ORDER.index(got) >= authorization.ORDER.index(base)


def _action_body(kind, params, mode, status, **extra):
    body = {"cycle_id": "C9", "kind": kind, "mode": mode, "reasons": [], "params": params,
            "params_sha256": sha256_text(canonical(params)), "status": status}
    body.update(extra)
    return body


def test_action_records_cannot_lie_about_authorization(mem):
    raw = dict(author="x", origin="RULE_ENGINE", project="P", family="F")
    with pytest.raises(MemoryViolation, match="classifies as"):
        mem.append("ACTION", "ACT-LIE-1", _action_body("RUN_EXPERIMENT_REAL_DATA", {"real_data": True},
                                                       "AUTO_SAFE", "EXECUTED"), **raw)
    with pytest.raises(MemoryViolation, match="cannot be EXECUTED"):
        mem.append("ACTION", "ACT-LIE-2", _action_body("RUN_EXPERIMENT_REAL_DATA", {"real_data": True},
                                                       "APPROVAL_REQUIRED", "EXECUTED"), **raw)
    with pytest.raises(MemoryViolation, match="cannot be EXECUTED"):
        mem.append("ACTION", "ACT-LIE-3", _action_body("LIVE_TRADING", {}, "PROHIBITED", "EXECUTED"), **raw)
    with pytest.raises(MemoryViolation, match="orchestrator task"):
        mem.append("ACTION", "ACT-LIE-4", _action_body("NEW_VARIANT", {}, "APPROVAL_REQUIRED",
                                                       "AWAITING_APPROVAL"), **raw)
    with pytest.raises(MemoryViolation, match="params"):
        bad = _action_body("DEDUP_CHECK", {}, "AUTO_SAFE", "EXECUTED")
        bad["params"] = {"x": 1}
        mem.append("ACTION", "ACT-LIE-5", bad, **raw)
    mem.append("ACTION", "ACT-OK-1", _action_body("LIVE_TRADING", {}, "PROHIBITED", "REFUSED"), **raw)


# ---- approval bridge (existing orchestrator queue) ------------------------------------------------
def test_approval_bridge_reuses_accept_only_and_never_executes(bridge):
    action = {"kind": "RUN_EXPERIMENT_REAL_DATA", "params_sha256": "c" * 64, "reasons": ["uses real market data"],
              "objective": "run SYN on fresh data"}
    task_id, created = bridge.request("ACT-X", action)
    again, created2 = bridge.request("ACT-X", action)
    assert created and not created2 and again == task_id
    rec = bridge.queue.get(task_id)
    assert rec["state"] == "WAITING_APPROVAL" and rec["approval_effect"] == "ACCEPT_ONLY"
    assert rec["manifest"]["approval_required"] == "EXPLICIT_USER_APPROVAL"
    assert bridge.queue.claim_next("dispatcher-test") is None
    assert bridge.status(task_id) == "WAITING"
    assert [e["event_type"] for e in bridge.ledger.read_for_task(task_id)] == ["APPROVAL_REQUIRED"]
    bridge.queue.decide_accept_only(task_id, "APPROVE")
    assert bridge.status(task_id) == "APPROVED"
    assert bridge.queue.get(task_id)["state"] == "PROPOSAL_ACCEPTED"
    with pytest.raises(AssertionError):
        bridge.queue.transition(task_id, "QUEUED")


# ---- planning and overfitting controls ------------------------------------------------------------
def test_near_equivalence():
    from research_intelligence_v1.hypotheses import signature_of
    a = signature_of(base_spec())[0]
    near = signature_of(base_spec(state_conditions=[{"feature_id": "impulse_atr", "operator": ">=", "threshold": 1.52},
                                                    {"feature_id": "retrace", "operator": ">=", "threshold": 0.38}]))[0]
    far = signature_of(base_spec(state_conditions=[{"feature_id": "impulse_atr", "operator": ">=", "threshold": 2.0},
                                                   {"feature_id": "retrace", "operator": ">=", "threshold": 0.382}]))[0]
    other_op = signature_of(base_spec(state_conditions=[{"feature_id": "impulse_atr", "operator": "<=", "threshold": 1.5},
                                                        {"feature_id": "retrace", "operator": ">=", "threshold": 0.382}]))[0]
    assert planner.near_equivalent(a, near) and not planner.near_equivalent(a, far)
    assert not planner.near_equivalent(a, other_op)


def _ranked(*ids):
    return {"ranked": [{"record_id": i} for i in ids]}


def test_planner_skips_equivalent_and_rejects_post_hoc(mem):
    base = seed_base(mem)
    near = register(mem, "SYN-NEAR", base_spec(state_conditions=[
        {"feature_id": "impulse_atr", "operator": ">=", "threshold": 1.51},
        {"feature_id": "retrace", "operator": ">=", "threshold": 0.382}]),
        statement="near", origin="AI_PROPOSAL", author="t", project="SYNTH", family="SYN2",
        relations=[{"type": "ALTERNATIVE_TO", "target": base["record_id"]}])
    out = planner.plan_cycle(mem, _ranked(base["record_id"], near["record_id"]), "C1", catalog(),
                             budget={"max_plans_per_family": 5})
    assert len(out["planned"]) == 1
    assert "substantially equivalent" in out["skipped"][0]["reason"]
    again = planner.plan_cycle(mem, _ranked(base["record_id"]), "C2", catalog())
    assert "already planned" in again["skipped"][0]["reason"]

    obs = mem.append("OBSERVATION", "OBS-SYN-FOUND", {
        "statement": "pattern seen", "scope": "EXPLORATORY",
        "dataset": {"dataset_id": "SYN_OLD", "split": "outside_splits", "exposure": "DISCOVERY_REUSE"},
        "values": {}, "evidence_level": "EXPLORATORY", "not_evidence_for": ["anything"]},
        author="t", origin="HUMAN", project="SYNTH", family="SYN3")
    post = register(mem, "SYN-POSTHOC", base_spec(direction="AGAINST_IMPULSE"), statement="from obs",
                    origin="RULE_ENGINE", author="t", project="SYNTH", family="SYN3",
                    relations=[{"type": "DERIVED_FROM", "target": obs["record_id"]}])
    res = planner.plan_cycle(mem, _ranked(post["record_id"]), "C3", catalog(dataset_id="SYN_OLD"))
    assert res["planned"] == [] and any("POST_HOC" in i for i in res["rejected_by_review"][0]["issues"])
    ok = planner.plan_cycle(mem, _ranked(post["record_id"]), "C4", {FRESH: dict(catalog()[FRESH], period="other")})
    assert ok["planned"]


def test_statistical_review_rejects_unfalsifiable_and_underpowered(mem):
    h = register(mem, "SYN-VAGUE", base_spec(falsification="not declared in source registry"), statement="v",
                 origin="REGISTRY_BACKFILL", author="t", project="SYNTH", family="SYN")
    out = planner.plan_cycle(mem, _ranked(h["record_id"]), "C1", catalog(expected_events=10))
    issues = out["rejected_by_review"][0]["issues"]
    assert any("falsification" in i for i in issues) and any("underpowered" in i for i in issues)
    plan = mem.get(out["rejected_by_review"][0]["plan"])["body"]
    assert plan["status"] == "REJECTED_BY_REVIEW" and plan["actions"] == []


def test_overfitting_checks(mem):
    base = seed_base(mem)
    for i in range(3):
        mem.append("EXPERIMENT", f"EXP-SYN-REUSE-{i}", {
            "hypothesis_id": "OTHER", "status": "COMPLETED", "result": "INCONCLUSIVE",
            "datasets": [{"dataset_id": FRESH, "split": "discovery", "period": "2027-01..2027-06", "exposure": "UNSEEN"}],
            "method": {"description": "s", "params_sha256": "UNKNOWN", "code_commit": "UNKNOWN", "preregistered": False},
            "metrics": {}, "limits": [], "anomalies": [], "alternative_explanations": [], "conclusions": [],
            "evidence_level": "DISCOVERY_ONLY", "decision": "x"}, author="t", origin="HUMAN", project="P", family="F")
    ds = {"dataset_id": FRESH, "split": "discovery", "period": "2027-01..2027-06"}
    checks, alpha, cap = overfitting.check_plan(mem, base["record_id"], ds)
    by = {c["check"]: c["status"] for c in checks}
    assert by["PERIOD_REUSE"] == "WARN" and cap == "DISCOVERY_ONLY"
    mem.append("EXPERIMENT", "EXP-SYN-REUSE-3", dict(mem.get("EXP-SYN-REUSE-0")["body"]), author="t",
               origin="HUMAN", project="P", family="F")
    by = {c["check"]: c["status"] for c in overfitting.check_plan(mem, base["record_id"], ds)[0]}
    assert by["PERIOD_REUSE"] == "BLOCK"
    by = {c["check"]: c["status"] for c in overfitting.check_plan(
        mem, base["record_id"], {"dataset_id": "X", "split": "final_holdout"})[0]}
    assert by["PROTECTED_SPLIT"] == "BLOCK"
    for i in range(3):
        register(mem, f"SYN-ALT-{i}", base_spec(direction=f"D{i}"), statement="a", origin="RULE_ENGINE", author="t",
                 project="SYNTH", family="SYN", relations=[{"type": "ALTERNATIVE_TO", "target": base["record_id"]}])
    _, alpha4, _ = overfitting.check_plan(mem, base["record_id"], {"dataset_id": "Y", "split": "discovery"})
    assert alpha4 == pytest.approx(0.05 / 4)


def test_plan_records_enforce_split_and_review(mem):
    seed_base(mem)
    body = {"cycle_id": "C1", "hypothesis_record": "HYP-SYN-BASE-001", "equivalence_key": "d" * 64,
            "dataset": {"dataset_id": "X", "split": "discovery", "exposure": "UNSEEN"},
            "evidence_target": "INTERNAL_VALIDATION", "decision_rule": "r", "falsification": "f", "alpha": 0.05,
            "min_sample": 30, "compute_estimate": {}, "overfitting_checks": [],
            "statistical_review": {"verdict": "PASS"}, "status": "DRAFT_PREREGISTRATION", "actions": []}
    raw = dict(author="x", origin="RULE_ENGINE", project="P", family="F")
    with pytest.raises(MemoryViolation, match="evidence target"):
        mem.append("EXPERIMENT_PLAN", "PLAN-BAD-1", body, **raw)
    with pytest.raises(MemoryViolation, match="statistical review"):
        mem.append("EXPERIMENT_PLAN", "PLAN-BAD-2", dict(body, evidence_target="DISCOVERY_ONLY",
                                                          statistical_review={"verdict": "REJECT"}), **raw)
    with pytest.raises(MemoryViolation, match="one-shot"):
        mem.append("EXPERIMENT_PLAN", "PLAN-BAD-3", dict(body, evidence_target="DISCOVERY_ONLY", dataset={
            "dataset_id": "X", "split": "locked_validation", "exposure": "UNSEEN"}), **raw)


# ---- loop mechanics ---------------------------------------------------------------------------------
class SimulatedCrash(BaseException):
    """Stands for a killed process: not an Exception, so the loop cannot record it."""


def test_resume_after_crash_reconciles_and_does_not_duplicate(mem, bridge, tmp_path):
    seed_base(mem)
    first = summary(tmp_path, "SYN-RUN-1")

    def crash(step, attempt):
        if step == "PLAN" and attempt == 1:
            raise SimulatedCrash()
    with pytest.raises(SimulatedCrash):
        make_loop(mem, bridge, inbox=[first], fault=crash).run_cycle()
    reopened = ResearchMemory(mem.path)
    loop = make_loop(reopened, bridge, inbox=[first])
    st = loop.status()
    assert st["open_cycle"] == "C0001" and st["next_step"] == "PLAN"
    assert st["completed_steps"] == STEPS[:5]
    result = loop.run_cycle()
    assert result["status"] == "CLOSED"
    plan_tr = [t["body"] for t in loop.transitions("C0001") if t["body"]["step"] == "PLAN"]
    assert [(t["status"], t["attempt"]) for t in plan_tr] == [("STARTED", 1), ("FAILED", 1), ("STARTED", 2),
                                                               ("COMPLETED", 2)]
    assert plan_tr[1]["error"].startswith("interrupted")
    assert len(reopened.of_type("EXPERIMENT")) == 1
    assert reopened.verify() == []


def test_failing_step_is_retried_then_abandoned(mem, bridge):
    seed_base(mem)
    calls = []

    def flaky(step, attempt):
        if step == "LEARN":
            calls.append(attempt)
            raise RuntimeError("synthetic failure")
    out = make_loop(mem, bridge, fault=flaky).run_cycle()
    assert out == {"cycle_id": "C0001", "status": "ABANDONED", "failed_step": "LEARN"} and calls == [1, 2, 3]
    nxt = make_loop(mem, bridge).run_cycle()
    assert nxt["cycle_id"] == "C0002" and nxt["status"] == "CLOSED"
    assert mem.verify() == []


def test_retry_after_transient_failure_succeeds(mem, bridge):
    seed_base(mem)

    def once(step, attempt):
        if step == "PRIORITIZE" and attempt == 1:
            raise RuntimeError("transient")
    out = make_loop(mem, bridge, fault=once).run_cycle()
    assert out["status"] == "CLOSED"
    assert len(mem.of_type("PRIORITIZATION")) == 1


def test_cycle_budgets(mem, bridge, tmp_path):
    seed_base(mem)
    out = make_loop(mem, bridge, inbox=[summary(tmp_path, "SYN-RUN-1")], max_new_hypotheses=1,
                    cycle_budget={"max_plans": 1}).run_cycle()["outputs"]
    assert len(out["HYPOTHESIZE"]["registered"]) == 1 and out["HYPOTHESIZE"]["cycle_limit"]
    assert len(out["PLAN"]["planned"]) <= 1


def test_loop_learns_underpowered_dataset_across_cycles(mem, bridge, tmp_path):
    seed_base(mem)
    loop = make_loop(mem, bridge, inbox=[summary(tmp_path, "SYN-RUN-1")], dataset_catalog=catalog(expected_events=60),
                     cycle_budget={"max_plans": 1})
    first = loop.run_cycle()["outputs"]
    refused = [a for a in mem.of_type("ACTION") if a["body"]["kind"] == "RUN_EXPERIMENT_REAL_DATA"]
    assert refused and refused[0]["body"]["status"] == "REFUSED" and "power" in refused[0]["body"]["reasons"][-1]
    assert first["PLAN"]["planned"]
    second = loop.run_cycle()["outputs"]
    assert second["PLAN"]["planned"] == []
    assert any("learned from" in s["reason"] for s in second["PLAN"]["skipped"])
    assert bridge.queue.list_all() == []


def test_roles_bind_to_existing_registry():
    assert agents.validate_roles() == []
    assert set(agents.STEP_OWNER) == set(STEPS)


def test_package_adds_no_scheduler_network_or_paid_client():
    pkg = RESEARCH / "research_intelligence_v1"
    text = "\n".join(p.read_text() for p in pkg.glob("*.py"))
    for banned in ("import sched", "crontab", "APScheduler", "time.sleep", "requests.", "urllib", "socket",
                   "subprocess", "import anthropic", "import openai", "MetaTrader5", "OrderSend("):
        assert banned not in text, banned


# ---- end to end acceptance (synthetic) ------------------------------------------------------------------
def test_end_to_end_research_loop(mem, bridge, tmp_path):
    seed_base(mem)
    loop = make_loop(mem, bridge, inbox=[summary(tmp_path, "SYN-RUN-1")],
                     extra_actions=[{"kind": "READ_PROTECTED_SPLIT", "params": {"split": "final_holdout"}},
                                    {"kind": "MODIFY_PREREGISTERED_PARAMS",
                                     "params": {"params_sha256": "1", "preregistered_params_sha256": "2"}}])
    out = loop.run_cycle()
    assert out["status"] == "CLOSED"
    o = out["outputs"]
    # 1. acquire a result
    exp_id = o["OBSERVE"]["ingested"][0]
    original = mem.get(exp_id)["record_hash"]
    # 2. find a methodological limit
    rev = mem.get(o["REVIEW"]["reviews"][0])["body"]
    checks = {f["check"] for f in rev["findings"]}
    assert {"LOW_SAMPLE", "NO_ALTERNATIVE_EXPLANATIONS", "DATASET_HASH_MISSING"} <= checks
    # 3. a non-duplicate, classified proposal, with baseline and success criterion
    props = [mem.get(p) for p in o["REVIEW"]["new_proposals"]]
    assert props and all("baseline" in p["body"] and p["body"]["success_criterion"] for p in props)
    assert len({p["record_id"] for p in props}) == len(props)
    # 4. new falsifiable hypotheses (proposal only)
    new_h = [mem.get(h)["body"] for h in o["HYPOTHESIZE"]["registered"]]
    assert new_h and all(h["falsification"] and h["mechanism"] and h["evidence_level"] == "NONE_PROPOSAL"
                         for h in new_h)
    # 5. an experiment planned as a draft preregistration
    plan = mem.get(o["PLAN"]["planned"][0])["body"]
    assert plan["status"] == "DRAFT_PREREGISTRATION" and plan["evidence_target"] == "DISCOVERY_ONLY"
    assert plan["alpha"] < 0.05 and plan["statistical_review"]["verdict"] == "PASS"
    # 6-7. only AUTO_SAFE executed; real-data run blocked for approval; prohibited refused
    acts = {a["body"]["kind"]: a["body"] for a in mem.of_type("ACTION")}
    assert all(a["mode"] == "AUTO_SAFE" for a in acts.values() if a["status"] == "EXECUTED")
    assert acts["SYNTHETIC_DRY_RUN"]["status"] == "EXECUTED"
    assert acts["SYNTHETIC_DRY_RUN"]["result"]["verdict"] == "ADEQUATE"
    real = acts["RUN_EXPERIMENT_REAL_DATA"]
    assert real["status"] == "AWAITING_APPROVAL" and bridge.status(real["orchestrator_task_id"]) == "WAITING"
    assert acts["READ_PROTECTED_SPLIT"]["status"] == "REFUSED"
    assert acts["MODIFY_PREREGISTERED_PARAMS"]["status"] == "REFUSED"
    assert all(t["state"] == "WAITING_APPROVAL" for t in bridge.queue.list_all())
    # 8. results, decisions and knowledge stored, evaluated and checkpointed
    ev = mem.get(f"EVAL-{out['cycle_id']}")["body"]["metrics"]
    assert ev["errors_identified"] >= 0 and ev["new_information"]["findings"] >= 3
    assert ev["hypotheses"]["new_proposals"] == len(new_h)
    assert ev["conclusion_reliability"]["ai_or_rule_results_counted_as_evidence"] == 0
    assert mem.checkpoints()[-1]["count"] == len(mem.records)

    # 9. interruption: a second cycle crashes in EXECUTE and resumes without duplicate requests
    decided = bridge.queue.decide_accept_only(real["orchestrator_task_id"], "APPROVE")[0]
    assert decided["state"] == "PROPOSAL_ACCEPTED"

    def crash(step, attempt):
        if step == "EXECUTE" and attempt == 1:
            raise SimulatedCrash()
    with pytest.raises(SimulatedCrash):
        make_loop(mem, bridge, fault=crash).run_cycle()
    resumed = make_loop(ResearchMemory(mem.path), bridge).run_cycle()
    assert resumed["status"] == "CLOSED"
    assert resumed["outputs"]["OBSERVE"]["approvals"] == {next(a["record_id"] for a in mem.of_type("ACTION")
                                                              if a["body"]["kind"] == "RUN_EXPERIMENT_REAL_DATA"):
                                                         "APPROVED"}
    tasks = bridge.queue.list_all()
    assert len(tasks) == len({t["idempotency"]["key"] for t in tasks})

    # 10. improvement vs baseline: a person accepts two proposals, both are implemented,
    # three later independent experiments are reviewed; one improves, one does not, both are kept.
    mem2 = ResearchMemory(mem.path)
    hash_prop = next(p["record_id"] for p in props if "DATASET_HASH_MISSING" in p["record_id"])
    sample_prop = next(p["record_id"] for p in props if "LOW_SAMPLE" in p["record_id"])
    for pid in (hash_prop, sample_prop):
        proposals.decide(mem2, pid, "ACCEPTED", decided_by="max", note="try it")
        proposals.decide(mem2, pid, "IMPLEMENTED", decided_by="max", note="PR with test")
    later = [summary(tmp_path, f"SYN-RUN-{i}", with_hash=True) for i in (2, 3, 4)]
    final = make_loop(mem2, bridge, inbox=later).run_cycle()
    assert final["status"] == "CLOSED"
    verdicts = {mem2.get(t)["body"]["proposal_record"]: mem2.get(t)["body"]["verdict"]
                for t in final["outputs"]["LEARN"]["trials_written"] + final["outputs"]["EVALUATE"]["trials_written"]
                if mem2.get(t)["body"]["phase"] == "RESULT"}
    assert verdicts == {hash_prop: "IMPROVED", sample_prop: "NOT_IMPROVED"}
    for pid in (hash_prop, sample_prop):
        base = next(t for t in mem2.of_type("IMPROVEMENT_TRIAL")
                    if t["body"]["proposal_record"] == pid and t["body"]["phase"] == "BASELINE")
        assert base["body"]["baseline"]["rate"] == 1.0
    assert mem2.get(exp_id)["record_hash"] == original
    assert mem2.verify() == []
