"""ZERO_BUDGET_REVENUE_PORTFOLIO_V1 shared venture projection.

This module records evidence and proposals.  It cannot contact prospects,
change prices, make payments, or mutate trading/runtime code.
"""
from __future__ import annotations

import copy
import importlib.util
import json
import os
import threading
from datetime import datetime, timezone
from pathlib import Path


VENTURE_STATUSES = {"IDEA", "READY_TO_TEST", "TESTING", "KEEP", "SCALE", "PAUSE", "KILL"}
VENTURE_IDS = (
    "LEAD_RESEARCH_SERVICE", "EA_MQL5_AUDIT_SERVICE",
    "STRATEGY_ROBUSTNESS_AUDIT", "COMPETITOR_SUPPLIER_INTELLIGENCE",
)
VENTURE_TASKS = {
    "LEAD_RESEARCH_SERVICE": "VENTURE_LEAD_RESEARCH",
    "EA_MQL5_AUDIT_SERVICE": "VENTURE_EA_MQL5_AUDIT",
    "STRATEGY_ROBUSTNESS_AUDIT": "VENTURE_STRATEGY_ROBUSTNESS_AUDIT",
    "COMPETITOR_SUPPLIER_INTELLIGENCE": "VENTURE_INTELLIGENCE",
}

_DEFINITIONS = {
    "LEAD_RESEARCH_SERVICE": ("Lead Research Service", "Evidence-backed prospect list",
                              "small businesses and agencies", "prospect criteria and source records",
                              "15-20 ranked prospects with provenance"),
    "EA_MQL5_AUDIT_SERVICE": ("EA MQL5 Audit Service", "Static EA engineering audit",
                              "EA developers and traders", ".mq5/.mqh or code and optional report",
                              "EA_AUDIT_REPORT_V1"),
    "STRATEGY_ROBUSTNESS_AUDIT": ("Strategy Robustness Audit", "Scientific robustness review",
                                  "strategy owners", "rules, CSV, report, summary or trade list",
                                  "STRATEGY_ROBUSTNESS_REPORT_V1"),
    "COMPETITOR_SUPPLIER_INTELLIGENCE": ("Competitor / Supplier Intelligence",
                                         "Source-backed market intelligence", "operators and founders",
                                         "entities, question and source records", "INTELLIGENCE_REPORT_V1"),
}

DEFAULT_SCORE_WEIGHTS = {
    "revenue_potential": 0.25, "time_cost": 0.20, "cash_speed": 0.20,
    "automation_share": 0.15, "evidence": 0.10, "recurrence": 0.10,
}


def _now():
    return datetime.now(timezone.utc).isoformat()


def _seed():
    ventures = []
    for venture_id, values in _DEFINITIONS.items():
        name, offer, target, inputs, output = values
        ventures.append({
            "venture_id": venture_id, "name": name, "status": "READY_TO_TEST",
            "status_meaning": "STRUCTURE_READY_FOR_REAL_MARKET_TEST_NOT_VALIDATED",
            "offer_description": offer, "target_customer": target,
            "required_inputs": inputs, "deliverable": output,
            "estimated_human_time_minutes": 20, "estimated_automation_share": 0.8,
            "current_price_hypothesis": {"amount": None, "currency": "EUR", "human_reviewed": False},
            "cost_month_eur": 0, "incremental_monthly_cost_eur": 0,
            "revenue_eur": 0, "leads": 0, "qualified_leads": 0,
            "sales": 0, "hours_spent": 0, "local_tasks": 0, "total_tasks": 0,
            "retries": 0, "verifier_rejects": 0, "premium_escalations": 0,
            "human_interventions": 0, "updated_at": _now(),
        })
    return {"schema_version": "REVENUE_VENTURE_REGISTRY_V1", "revision": 0,
            "ventures": ventures, "idempotency_keys": []}


class RevenueVentureRegistry:
    def __init__(self, path):
        self.path = Path(path); self._lock = threading.RLock()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists(): self._save(_seed())

    def _load(self):
        value = json.loads(self.path.read_text(encoding="utf-8"))
        if value.get("schema_version") != "REVENUE_VENTURE_REGISTRY_V1":
            raise RuntimeError("unsupported venture registry")
        return value

    def _save(self, value):
        temp = self.path.with_name(self.path.name + f".{os.getpid()}.tmp")
        temp.write_text(json.dumps(value, indent=2, ensure_ascii=False), encoding="utf-8")
        os.replace(temp, self.path)

    def snapshot(self):
        with self._lock: return copy.deepcopy(self._load())

    def record(self, venture_id, delta, *, idempotency_key):
        if venture_id not in VENTURE_IDS or not idempotency_key: raise ValueError("invalid venture update")
        allowed = {"revenue_eur", "leads", "qualified_leads", "sales", "hours_spent",
                   "local_tasks", "total_tasks", "retries", "verifier_rejects",
                   "premium_escalations", "human_interventions"}
        if set(delta) - allowed or any(not isinstance(x, (int, float)) or x < 0 for x in delta.values()):
            raise ValueError("metric deltas must be non-negative and allowlisted")
        with self._lock:
            state = self._load()
            if idempotency_key in state["idempotency_keys"]: return copy.deepcopy(state)
            venture = next(x for x in state["ventures"] if x["venture_id"] == venture_id)
            for key, amount in delta.items(): venture[key] += amount
            venture["updated_at"] = _now(); state["revision"] += 1
            state["idempotency_keys"] = (state["idempotency_keys"] + [idempotency_key])[-1000:]
            self._save(state); return copy.deepcopy(state)

    def set_status(self, venture_id, status, *, approved_by):
        if status not in VENTURE_STATUSES or not approved_by: raise ValueError("human approval required")
        with self._lock:
            state = self._load(); venture = next(x for x in state["ventures"] if x["venture_id"] == venture_id)
            venture["status"] = status; venture["status_approved_by"] = approved_by
            venture["updated_at"] = _now(); state["revision"] += 1; self._save(state)


def venture_metrics(venture):
    hours = venture.get("hours_spent", 0); qualified = venture.get("qualified_leads", 0)
    total = venture.get("total_tasks", 0)
    return {"revenue_per_hour": venture.get("revenue_eur", 0) / hours if hours else 0,
            "conversion_rate": venture.get("sales", 0) / qualified if qualified else 0,
            "automation_share": venture.get("local_tasks", 0) / total if total else 0}


def comparative_score(dimensions, weights=None):
    weights = weights or DEFAULT_SCORE_WEIGHTS
    if set(weights) != set(DEFAULT_SCORE_WEIGHTS) or abs(sum(weights.values()) - 1) > 1e-9:
        raise ValueError("all documented weights must be supplied and sum to one")
    if set(dimensions) != set(weights) or any(not 0 <= x <= 1 for x in dimensions.values()):
        raise ValueError("dimensions must be explicit 0..1 values")
    return {"score": sum(dimensions[k] * weights[k] for k in weights), "weights": dict(weights),
            "dimensions": dict(dimensions), "decision": "HUMAN_REVIEW_REQUIRED"}


def portfolio_summary(snapshot):
    return [{**{k: v[k] for k in ("venture_id", "name", "status", "revenue_eur", "sales")},
             **venture_metrics(v)} for v in snapshot["ventures"]]


def load_mql5_skill_findings(path, repo_root):
    """Reuse the canonical MQL5 skill verifier without copying its rules."""
    verifier_path = Path(repo_root) / ".claude/skills/mql5-engineering/verifier.py"
    spec = importlib.util.spec_from_file_location("nexus_mql5_skill_verifier", verifier_path)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    findings = module.check_file(Path(path))
    return [{"finding_id": f"MQL5_SKILL_{index}", "source": str(verifier_path),
             "message": finding, "file": str(path)}
            for index, finding in enumerate(findings, 1)]


def venture_event(venture_id, event_type, *, reason, requires_action=False):
    allowed = {"VENTURE_TEST_READY", "VENTURE_DELIVERABLE_READY", "VENTURE_REVIEW_DUE",
               "VENTURE_LOW_EFFICIENCY", "VENTURE_SCALE_CANDIDATE"}
    if event_type not in allowed: raise ValueError("unsupported venture event")
    return {"event_type": event_type, "venture_id": venture_id, "reason": reason,
            "requires_human_action": requires_action, "generated_at": _now(),
            "proposal_only": True}


class RevenuePortfolioCoordinator:
    """Thin adapter over the canonical RevenueAgentCoordinator.

    It owns no router or queue and records only verified terminal outcomes.
    """
    def __init__(self, registry, revenue_agent, *, event_sink=None):
        self.registry = registry; self.revenue_agent = revenue_agent
        self.event_sink = event_sink or (lambda event: None)

    def submit(self, venture_id, *, context, references=None):
        if venture_id not in VENTURE_TASKS: raise ValueError("unknown venture")
        refs = {**(references or {}), "venture_id": venture_id}
        return self.revenue_agent.submit(VENTURE_TASKS[venture_id], context=context,
                                         references=refs, created_by="revenue_portfolio_v1")

    def record_terminal_result(self, venture_id, task_id):
        record = self.revenue_agent.orchestrator.queue.get(task_id)
        if record["state"] not in {"COMPLETED", "ESCALATION_REQUIRED"}:
            raise ValueError("task is not terminal")
        local = record.get("executor") in {"LOCAL_FAST_MINISTRAL3B", "LOCAL_STRONG_MINISTRAL3B"}
        delta = {"total_tasks": 1, "local_tasks": int(local),
                 "retries": record.get("retry_count", 0),
                 "verifier_rejects": int(record.get("retry_count", 0) > 0),
                 "premium_escalations": int(record["state"] == "ESCALATION_REQUIRED")}
        self.registry.record(venture_id, delta, idempotency_key=f"terminal:{task_id}")
        event_type = ("VENTURE_DELIVERABLE_READY" if record["state"] == "COMPLETED"
                      else "VENTURE_REVIEW_DUE")
        event = venture_event(venture_id, event_type, reason=f"task {task_id}: {record['state']}",
                              requires_action=True)
        self.event_sink(event); return event
