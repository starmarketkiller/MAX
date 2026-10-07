"""NEXUS Local Operations Unification V1.

Additive projections and planning helpers over the canonical Queue, Revenue
store and capability registry.  This module owns no execution authority: it
never runs a tool, changes a lead, sends outreach or grants a permission.
"""
from __future__ import annotations

import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path


STEP_STATES = (
    "PENDING", "RUNNING", "VERIFIED", "RETRY_REQUIRED", "WAITING_CONTEXT",
    "WAITING_APPROVAL", "WAITING_FOR_PREMIUM", "BLOCKED", "COMPLETED", "FAILED",
)
TRUST_STATES = ("TRUSTED_CANONICAL", "VETTED_EXTERNAL", "EXPERIMENTAL",
                "QUARANTINED", "REJECTED")


def _now():
    return datetime.now(timezone.utc).isoformat()


class SkillRegistry:
    """Small allowlisted index.  A skill describes method, never permission."""

    CANONICAL = {
        "mql5-engineering": {
            "relative_path": ".claude/skills/mql5-engineering",
            "capabilities": ["mql5_static_analysis", "artifact_field_extraction"],
            "allowed_contexts": ["EA_MQL5_AUDIT_SERVICE", "CODE_REVIEW"],
            "required_tools": ["read_file"], "verifier": "mql5_engineering_verifier",
        },
        "ui-ux-pro-max": {
            "relative_path": ".claude/skills/ui-ux-pro-max",
            "capabilities": ["ui_review"], "allowed_contexts": ["UI_REVIEW"],
            "required_tools": ["read_file"], "verifier": "human_review",
        },
    }

    def __init__(self, project_root):
        self.project_root = Path(project_root).resolve()

    def list(self):
        result = []
        for skill_id, spec in self.CANONICAL.items():
            path = self.project_root / spec["relative_path"]
            result.append({"skill_id": skill_id, "source": spec["relative_path"],
                           "trust_level": "TRUSTED_CANONICAL" if path.exists() else "QUARANTINED",
                           "capabilities": spec["capabilities"],
                           "allowed_contexts": spec["allowed_contexts"],
                           "required_tools": spec["required_tools"],
                           "verifier": spec["verifier"], "version": "git:current",
                           "available": path.exists()})
        return result

    def resolve(self, capability, context):
        candidates = [item for item in self.list()
                      if item["available"] and item["trust_level"] == "TRUSTED_CANONICAL"
                      and capability in item["capabilities"]
                      and context in item["allowed_contexts"]]
        return candidates


class CapabilityResolver:
    """Combines existing agent capabilities with vetted skill metadata.

    Authorization remains explicit and fail-closed.  This method only returns
    candidates; the Orchestrator Router remains the selector/authority.
    """

    def __init__(self, agent_registry, skill_registry):
        self.agent_registry = agent_registry
        self.skill_registry = skill_registry

    def resolve(self, capability, *, context, authorized_capabilities):
        authorized = capability in set(authorized_capabilities or [])
        agents = [a["agent_id"] for a in self.agent_registry.get("agents", [])
                  if capability in a.get("capabilities", [])
                  and a.get("availability") == "ONLINE"] if authorized else []
        skills = self.skill_registry.resolve(capability, context) if authorized else []
        return {"required_capability": capability, "candidate_skills": skills,
                "candidate_agents": agents, "candidate_tools": sorted({tool for item in skills
                                                                          for tool in item["required_tools"]}),
                "authorization_result": "AUTHORIZED" if authorized else "DENIED",
                "selected_skill": skills[0]["skill_id"] if skills else None,
                "selected_tool": (skills[0]["required_tools"][0] if skills else None),
                "selected_agent": agents[0] if agents else None,
                "verifier": skills[0]["verifier"] if skills else "independent_review"}


def is_complex_mistral_request(text):
    value = (text or "").strip().lower()
    operational = re.search(
        r"\b(analizza|audit|cerca|trova|crea|modifica|verifica|confronta|stato del sistema|revenue|ea)\b",
        value)
    return bool(operational and (len(value) >= 80 or len(value.split()) >= 12))


def build_execution_plan(objective, *, authorized_capabilities, resolver=None):
    """Outcome-blind bounded plan. It records required capability per step."""
    value = objective.lower()
    context = "EA_MQL5_AUDIT_SERVICE" if re.search(r"\b(ea|mq5|mql5)\b", value) else "GENERAL"
    requested = (["mql5_static_analysis", "artifact_field_extraction"] if context.startswith("EA_")
                 else ["summaries", "artifact_field_extraction"])
    steps = []
    for index, capability in enumerate(requested, 1):
        resolution = (resolver.resolve(capability, context=context,
                                       authorized_capabilities=authorized_capabilities)
                      if resolver else {"required_capability": capability,
                                        "authorization_result": ("AUTHORIZED" if capability in
                                                                  authorized_capabilities else "DENIED"),
                                        "selected_skill": None, "selected_tool": None,
                                        "selected_agent": None, "verifier": "independent_review"})
        steps.append({"step_id": f"STEP_{index}", "state": "PENDING", **resolution})
    return {"schema_version": "MULTI_STAGE_EXECUTION_PLAN_V1", "objective": objective,
            "created_at": _now(), "steps": steps, "current_step": "STEP_1",
            "sync_chat_budget_seconds": int(os.environ.get("NEXUS_SYNC_CHAT_BUDGET", "75")),
            "local_model_step_timeout_seconds": int(os.environ.get(
                "NEXUS_LOCAL_MODEL_STEP_TIMEOUT", "120")),
            "task_total_budget_seconds": int(os.environ.get("NEXUS_TASK_TOTAL_BUDGET", "900"))}


class OperationsProjection:
    """Read-only operational view; canonical stores remain authoritative."""

    def __init__(self, *, revenue_store, revenue_runner, revenue_scheduler,
                 portfolio_registry=None, queue=None, ledger=None):
        self.revenue_store = revenue_store
        self.revenue_runner = revenue_runner
        self.revenue_scheduler = revenue_scheduler
        self.portfolio_registry = portfolio_registry
        self.queue = queue
        self.ledger = ledger

    def revenue(self, *, automation_enabled):
        state = self.revenue_store.snapshot()
        prospects, leads = state.get("prospects", []), state.get("leads", [])
        tasks = self.queue.list_all() if self.queue else []
        revenue_tasks = [t for t in tasks if t.get("action") == "revenue_agent_bounded_task"]
        drafts = self.drafts()["items"]
        followups = self.followups()["items"]
        ventures = self.ventures()["items"]
        events = self.ledger.read_all() if self.ledger else []
        last_event = next((e for e in reversed(events) if "REVENUE" in e.get("event_type", "")), None)
        return {"revenue_runner_enabled": bool(automation_enabled),
                "revenue_runner_running": self.revenue_runner.running,
                "prospects_count": len(prospects), "leads_count": len(leads),
                "qualified_count": sum(x.get("status") in {"QUALIFIED", "CONTACT_READY", "CONTACTED",
                                                            "REPLIED", "INTERESTED", "WON"} for x in leads),
                "drafts_ready": sum(x["status"] == "READY_FOR_REVIEW" for x in drafts),
                "followups_due": len(followups),
                "ventures_ready_to_test": sum(x.get("status") == "READY_TO_TEST" for x in ventures),
                "ventures_testing": sum(x.get("status") == "TESTING" for x in ventures),
                "last_revenue_task": revenue_tasks[-1]["task_id"] if revenue_tasks else None,
                "last_revenue_event": last_event,
                "last_jarvis_delivery": self.revenue_runner.delivery.path.stat().st_mtime
                if self.revenue_runner.delivery.path.exists() else None,
                "commercial_actions_enabled": False}

    def leads(self):
        items = []
        for lead in self.revenue_store.snapshot().get("leads", []):
            items.append({key: lead.get(key) for key in (
                "lead_id", "display_name", "company", "website", "email", "phone", "handle",
                "source", "service_interest", "venture_id", "status", "fit_score", "created_at",
                "updated_at", "last_contact", "next_action", "followup_due", "notes",
                "outreach_receipt", "reply_history")})
        return {"count": len(items), "items": items}

    def find_contact(self, name):
        needle = name.casefold()
        prospects = self.revenue_store.snapshot().get("prospects", [])
        leads = self.revenue_store.snapshot().get("leads", [])
        return [item for item in prospects + leads
                if needle in str(item.get("display_name") or "").casefold()]

    def drafts(self):
        items = []
        for record in (self.queue.list_all() if self.queue else []):
            if record.get("action") != "revenue_agent_bounded_task":
                continue
            task_type = (record.get("action_params") or {}).get("revenue_task_type")
            if task_type not in {"OUTREACH_DRAFT", "FOLLOW_UP_DRAFT"}:
                continue
            state = record.get("state")
            status = ("READY_FOR_REVIEW" if state in {"COMPLETED", "WAITING_APPROVAL"}
                      else "REJECTED" if state == "FAILED" else "DRAFT")
            items.append({"draft_id": f"DRAFT_{record['task_id']}", "lead":
                          (record.get("action_params") or {}).get("references", {}).get("lead_id"),
                          "venture": (record.get("action_params") or {}).get("references", {}).get("venture_id"),
                          "type": task_type, "created_at": record.get("created_at"), "status": status,
                          "approval_required": True, "task_id": record["task_id"]})
        return {"count": len(items), "items": items}

    def followups(self):
        state = json.loads(self.revenue_scheduler.path.read_text(encoding="utf-8"))
        leads = {x["lead_id"]: x for x in self.revenue_store.snapshot().get("leads", [])}
        items = []
        for key, item in state.get("scheduled_keys", {}).items():
            if not key.startswith("followup:"):
                continue
            lead_id = key.split(":", 2)[1]
            items.append({"lead_id": lead_id, "lead": leads.get(lead_id, {}).get("display_name"),
                          "due_at": key.split(":", 2)[2], "reason": "FOLLOWUP_DUE",
                          "draft_ready": True, "task_id": item.get("task_id")})
        return {"count": len(items), "items": items}

    def ventures(self):
        if not self.portfolio_registry:
            return {"count": 0, "items": []}
        items = []
        for venture in self.portfolio_registry.snapshot().get("ventures", []):
            real_started = bool(venture.get("leads") or venture.get("sales") or venture.get("revenue_eur"))
            items.append({**venture, "real_market_test_started": real_started,
                          "real_leads": venture.get("leads", 0),
                          "drafts": None, "last_activity": venture.get("updated_at"),
                          "next_action": ("RUN_FIRST_REAL_MARKET_TEST" if not real_started
                                          else "HUMAN_REVIEW")})
        return {"count": len(items), "items": items}
