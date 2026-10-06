import json
from pathlib import Path
import sys

import pytest

from funding_v1.revenue_agent import verify_revenue_output
from funding_v1.revenue_agent import RevenueAgentCoordinator
from funding_v1.revenue_portfolio import (
    DEFAULT_SCORE_WEIGHTS, RevenuePortfolioCoordinator, RevenueVentureRegistry, comparative_score,
    load_mql5_skill_findings, portfolio_summary, venture_event, venture_metrics,
)
from orchestrator_v1.nxs_schema_validator import validate
from orchestrator_v1.core.orchestrator import Orchestrator
from funding_v1.first_revenue import FirstRevenueStore


ROOT = Path(__file__).resolve().parents[2]


def evidence(n=20):
    return [{"evidence_id": f"E{i}", "text": f"Source fact {i}"} for i in range(1, n + 1)]


def test_registry_persistence_idempotency_metrics_and_visible_score(tmp_path):
    path = tmp_path / "ventures.json"; registry = RevenueVentureRegistry(path)
    state = registry.snapshot()
    assert len(state["ventures"]) == 4
    assert all(v["cost_month_eur"] == 0 for v in state["ventures"])
    assert all(v["incremental_monthly_cost_eur"] == 0 for v in state["ventures"])
    assert all(v["status_meaning"] == "STRUCTURE_READY_FOR_REAL_MARKET_TEST_NOT_VALIDATED"
               for v in state["ventures"])
    registry.record("LEAD_RESEARCH_SERVICE", {"revenue_eur": 75, "hours_spent": 2,
                    "qualified_leads": 4, "sales": 2, "local_tasks": 3, "total_tasks": 4},
                    idempotency_key="run-1")
    registry.record("LEAD_RESEARCH_SERVICE", {"revenue_eur": 75}, idempotency_key="run-1")
    restored = RevenueVentureRegistry(path).snapshot()
    venture = restored["ventures"][0]
    assert venture["revenue_eur"] == 75 and venture_metrics(venture) == {
        "revenue_per_hour": 37.5, "conversion_rate": .5, "automation_share": .75}
    assert portfolio_summary(restored)[0]["revenue_per_hour"] == 37.5
    score = comparative_score({key: .5 for key in DEFAULT_SCORE_WEIGHTS})
    assert score["score"] == .5 and score["weights"] == DEFAULT_SCORE_WEIGHTS
    assert score["decision"] == "HUMAN_REVIEW_REQUIRED"


def test_lead_research_smoke_and_hallucinated_reference_rejected():
    prospects = [{"name": f"P{i}", "source_ref": f"E{i}", "public_contact": None,
                  "fit_reason": "source-backed", "priority": "MEDIUM"} for i in range(1, 16)]
    output = {"prospects": prospects, "summary": "15 prospects", "limitations": []}
    assert verify_revenue_output("VENTURE_LEAD_RESEARCH", output,
                                 {"evidence_records": evidence()}) == (True, [])
    output["prospects"][0]["source_ref"] = "INVENTED"
    assert not verify_revenue_output("VENTURE_LEAD_RESEARCH", output,
                                     {"evidence_records": evidence()})[0]


def test_mql5_audit_reuses_skill_and_report_verifier(tmp_path):
    mq5 = tmp_path / "client.mq5"; mq5.write_text("void f(){ OrderSend(); }", encoding="utf-8")
    findings = load_mql5_skill_findings(mq5, ROOT)
    assert findings and "mql5-engineering/verifier.py" in findings[0]["source"].replace("\\", "/")
    issue = {"severity": "HIGH", "evidence": findings[0]["finding_id"], "file": str(mq5),
             "line": 1, "issue": "Exposure path requires review", "impact": "Risk gate uncertainty",
             "recommended_action": "Review call graph", "confidence": "MEDIUM"}
    output = {"issues": [issue], "summary": "Advisory audit", "limitations": ["Static only"]}
    assert verify_revenue_output("VENTURE_EA_MQL5_AUDIT", output,
                                 {"static_findings": findings}) == (True, [])


def test_strategy_robustness_smoke_is_fail_closed_without_holdout():
    names = ["sample_size", "oos", "holdout", "cost_sensitivity", "parameter_sensitivity",
             "long_short_asymmetry", "regime_dependency", "drawdown", "clustering", "leakage",
             "proxy_broker_caveat", "multiple_testing"]
    checks = [{"check": name, "status": "UNKNOWN", "evidence_ref": None} for name in names]
    base = {"verdict": "INSUFFICIENT_EVIDENCE", "checks": checks,
            "summary": "Evidence incomplete", "limitations": ["No holdout"]}
    assert verify_revenue_output("VENTURE_STRATEGY_ROBUSTNESS_AUDIT", base, {}) == (True, [])
    robust = {**base, "verdict": "ROBUST"}
    assert not verify_revenue_output("VENTURE_STRATEGY_ROBUSTNESS_AUDIT", robust, {})[0]


def test_intelligence_smoke_separates_facts_from_inference():
    output = {"mode": "SUPPLIER_RESEARCH", "entities": ["Supplier A"], "comparison": [],
              "ranking": [], "risks": [], "opportunities": [],
              "facts": [{"claim": "Published MOQ", "source_ref": "E1"}],
              "inferences": [{"inference": "May suit pilot", "based_on": ["E1"]}],
              "limitations": ["No contact made"]}
    assert verify_revenue_output("VENTURE_INTELLIGENCE", output,
                                 {"evidence_records": evidence(1)}) == (True, [])
    output["facts"][0]["source_ref"] = "E9"
    assert not verify_revenue_output("VENTURE_INTELLIGENCE", output,
                                     {"evidence_records": evidence(1)})[0]


def test_jarvis_events_are_proposal_only_and_no_irreversible_action():
    event = venture_event("EA_MQL5_AUDIT_SERVICE", "VENTURE_DELIVERABLE_READY",
                          reason="verified report", requires_action=True)
    assert event["proposal_only"] and event["requires_human_action"]
    assert not any(key in event for key in ("send_email", "payment", "price", "execute"))


@pytest.mark.parametrize("name", ["revenue-venture-registry-v1.schema.json",
    "lead-research-report-v1.schema.json", "ea-audit-report-v1.schema.json",
    "strategy-robustness-report-v1.schema.json", "intelligence-report-v1.schema.json"])
def test_contracts_are_valid_json_schema(name):
    schema = json.loads((ROOT / "contracts" / name).read_text(encoding="utf-8"))
    assert schema["type"] == "object"


def test_seed_registry_validates_against_contract(tmp_path):
    state = RevenueVentureRegistry(tmp_path / "v.json").snapshot()
    schema = json.loads((ROOT / "contracts/revenue-venture-registry-v1.schema.json").read_text())
    assert validate(state, schema) == []


def test_venture_task_fast_rejection_gets_one_strong_correction(tmp_path, monkeypatch):
    store = FirstRevenueStore(tmp_path / "revenue.json")
    orch = Orchestrator(queue_path=str(tmp_path / "queue.json"),
                        ledger_path=str(tmp_path / "ledger.jsonl"))
    coordinator = RevenueAgentCoordinator(store, orch)
    valid = {"mode": "COMPETITOR_ANALYSIS", "entities": ["A"], "comparison": [],
             "ranking": [], "risks": [], "opportunities": [],
             "facts": [{"claim": "Observed fact", "source_ref": "E1"}],
             "inferences": [], "limitations": []}
    responses = ['{"invalid":true}', json.dumps(valid)]
    orchestrator_module = sys.modules[Orchestrator.__module__]
    monkeypatch.setattr(orchestrator_module.ollama_worker, "call_local_model",
                        lambda *a, **k: {"success": True, "response_text": responses.pop(0),
                                        "model": "ministral-3:3b", "wall_seconds": .01})
    task_id = coordinator.submit("VENTURE_INTELLIGENCE",
        context={"evidence_records": [{"evidence_id": "E1", "text": "Observed fact"}]},
        references={"venture_id": "COMPETITOR_SUPPLIER_INTELLIGENCE"})
    result = orch.process_task(task_id)
    assert result["state"] == "COMPLETED"
    assert result["retry_count"] == 1
    assert result["executor"] == "LOCAL_STRONG_MINISTRAL3B"
    assert result["manifest"]["premium_allowed"] is False
    events = []
    portfolio = RevenuePortfolioCoordinator(
        RevenueVentureRegistry(tmp_path / "ventures.json"), coordinator, event_sink=events.append)
    event = portfolio.record_terminal_result("COMPETITOR_SUPPLIER_INTELLIGENCE", task_id)
    assert event["event_type"] == "VENTURE_DELIVERABLE_READY" and len(events) == 1
    metrics = portfolio.registry.snapshot()["ventures"][3]
    assert metrics["local_tasks"] == metrics["total_tasks"] == 1
    # Delivery bookkeeping is idempotent.
    portfolio.record_terminal_result("COMPETITOR_SUPPLIER_INTELLIGENCE", task_id)
    assert portfolio.registry.snapshot()["ventures"][3]["total_tasks"] == 1
