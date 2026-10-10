"""Sector workflows on the existing queue.

Trading, finance and council do not call a model: a model can invent a
number. Revenue and social call the gateway with the same fail-closed flags
as the fashion handoff, and they do not reuse that prompt. Nothing here
publishes, spends, trades, contacts or deploys.
"""
from __future__ import annotations

import json
import re
import uuid
from datetime import datetime, timezone

from jarvis_v1.authenticated_scope import canonical_tenant_id
from jarvis_v1.floor_workflow import owns_floor_task

_ID = re.compile(r"[A-Za-z0-9_.:-]{1,80}")
_DATASET = re.compile(r"dataset:[A-Za-z0-9_.:-]{1,64}\Z")
_NUMBER = re.compile(r"\d+")
_EVIDENCE_FIELDS = {"evidence_id", "note", "text", "source", "source_url"}


class LaunchRejected(Exception):
    def __init__(self, code, status=422):
        super().__init__(code)
        self.code = code
        self.status = status


def _now():
    return datetime.now(timezone.utc).isoformat()


def evidence_problem(evidence):
    if not isinstance(evidence, list) or not (1 <= len(evidence) <= 50):
        return "INVALID_EVIDENCE_RECORDS"
    for item in evidence:
        if not isinstance(item, dict) or set(item) - _EVIDENCE_FIELDS:
            return "INVALID_EVIDENCE_RECORDS"
        evidence_id = item.get("evidence_id")
        if not isinstance(evidence_id, str) or not _ID.fullmatch(evidence_id):
            return "INVALID_EVIDENCE_RECORDS"
        if evidence_id.startswith("USER_CONTEXT"):
            return "INVALID_EVIDENCE_RECORDS"
        source = str(item.get("source") or item.get("source_url") or "").strip()
        note = str(item.get("note") or item.get("text") or "").strip()
        if not source or source == note:
            return "INVALID_EVIDENCE_RECORDS"
        for key, value in item.items():
            if key != "evidence_id" and (not isinstance(value, str) or len(value) > 4000):
                return "INVALID_EVIDENCE_RECORDS"
    if len({item["evidence_id"] for item in evidence}) != len(evidence):
        return "DUPLICATE_EVIDENCE_ID"
    return None


def sourced_records(evidence):
    rows = []
    for item in evidence or []:
        if not isinstance(item, dict):
            continue
        evidence_id = str(item.get("evidence_id") or "")
        source = str(item.get("source") or item.get("source_url") or "").strip()
        note = str(item.get("note") or item.get("text") or "").strip()
        if evidence_id and source and source != note and not evidence_id.startswith("USER_CONTEXT"):
            rows.append(item)
    return rows


def _append_step(ledger, task_id, workflow_id, step_id, station_id, output_ref,
                 provenance, event_type="STEP_COMPLETED", state="RECORDED"):
    for event in ledger.read_for_task(task_id):
        payload = event.get("payload") or {}
        if event.get("event_type") == event_type and payload.get("step_id") == step_id:
            return
    ledger.append(event_type, task_id, {
        "step_id": step_id,
        "station_id": station_id,
        "state": state,
        "output_ref": output_ref,
        "provenance": provenance,
        "workflow_id": workflow_id,
        "side_effects": "none",
    }, actor="sector_workflow_v1")


def _manifest(title, objective, created_by, tenant_id, verifier):
    return {
        "task_id": f"TASK_{uuid.uuid4().hex[:12].upper()}",
        "title": title,
        "objective": objective,
        "task_type": "MAINTENANCE", "work_type": "business_analysis",
        "priority": "NORMAL", "risk_level": "A1", "scientific_risk": "NONE",
        "code_risk": "NONE", "financial_risk": "NONE",
        "required_capabilities": ["json_structured_output", "artifact_field_extraction"],
        "deterministic_tools_available": False, "repo_scope": "NONE",
        "files_allowed": [], "files_forbidden": ["**/*", ".env"],
        "dependencies": [], "blockers": [], "expected_artifacts": ["RESULT_PACKET_V1"],
        "success_criteria": ["schema valid", "stopped before any external action"],
        "verifier": verifier,
        "estimated_complexity": "SMALL", "estimated_runtime": "2m",
        "premium_allowed": False, "preferred_executor": "TIER1_LOCAL_CHEAP",
        "fallback_executors": ["TIER2_LOCAL_STRONG"],
        "approval_required": "REVIEW_REQUIRED", "created_by": created_by,
        "created_at": _now(), "tenant_id": tenant_id, "account_scope_id": None,
    }


def _owned_action(record, action, owner, tenant_id):
    if not owner or record.get("action") != action:
        return False
    manifest = record.get("manifest") or {}
    return (manifest.get("created_by") == f"jarvis:{owner}"
            and manifest.get("tenant_id") == (tenant_id or canonical_tenant_id()))


def project_sector_trace(queue, ledger, task_id, *, owner, tenant_id, action, workflow_id, not_run):
    record = None
    if task_id:
        try:
            candidate = queue.get(task_id)
        except KeyError:
            candidate = None
        if candidate is not None and _owned_action(candidate, action, owner, tenant_id):
            record = candidate
    else:
        rows = [row for row in queue.list_all() if _owned_action(row, action, owner, tenant_id)]
        record = max(rows, key=lambda row: row.get("updated_at") or "") if rows else None
    if record is None:
        return {"source": "ledger", "task_id": None, "state": None, "approval_effect": None,
                "decision": None, "artifact_count": 0, "artifacts": [], "delivery": "not_sent",
                "steps": [], "not_run": list(not_run)}
    steps = []
    for event in ledger.read_for_task(record["task_id"]):
        if event.get("event_type") not in {"STEP_COMPLETED", "TASK_WAITING_APPROVAL"}:
            continue
        payload = event.get("payload") or {}
        if payload.get("workflow_id") != workflow_id:
            continue
        if payload.get("state") not in {"RECORDED", "WAITING_APPROVAL"}:
            continue
        steps.append({
            "step_id": payload.get("step_id"),
            "station_id": payload.get("station_id"),
            "state": payload.get("state"),
            "output_ref": payload.get("output_ref"),
            "provenance": payload.get("provenance"),
            "workflow_id": payload.get("workflow_id"),
            "recorded_at": event.get("timestamp"),
        })
    packet = record.get("result_packet") or {}
    artifacts = []
    for value in packet.get("artifacts_created") or []:
        artifacts.append({"kind": str(value).split(":", 1)[0][:48], "available": True})
    return {
        "source": "ledger",
        "task_id": record["task_id"],
        "state": record.get("state"),
        "approval_effect": record.get("approval_effect"),
        "decision": packet.get("decision"),
        "artifact_count": len(packet.get("artifacts_created") or []),
        "artifacts": artifacts,
        "delivery": "not_sent",
        "steps": steps,
        "not_run": list(not_run),
    }


def _submit(orchestrator, manifest, action, params, scope, key):
    return orchestrator.submit_idempotent(
        manifest, action=action, action_params=params,
        idempotency_scope=scope, idempotency_key=key)


class _ProposalHandler:
    fail_closed_without_premium = True

    def __init__(self, ledger, workflow_id):
        self.ledger = ledger
        self.workflow_id = workflow_id

    def apply(self, record, verify_result):
        from orchestrator_v1.core.orchestrator import ApplyResult
        artifacts = list(getattr(self, "artifacts_for", lambda *_: [])(record, verify_result))
        return ApplyResult(artifacts_created=artifacts, touches_real_repo_files=False,
                           proposal_only=True)


TRADING_WORKFLOW_ID = "jarvis.trading.research.v1"
TRADING_ACTION = "nexus_trading_research_workflow"
TRADING_NOT_RUN = (
    {"station_id": "trading.news", "reason": "no_sourced_headline"},
    {"station_id": "trading.struct", "reason": "series_absent"},
    {"station_id": "trading.implement", "reason": "no_second_sample"},
    {"station_id": "trading.backtest", "reason": "no_second_sample"},
    {"station_id": "trading.oos", "reason": "no_second_sample"},
    {"station_id": "trading.robust", "reason": "no_second_sample"},
    {"station_id": "trading.valid", "reason": "no_second_sample"},
    {"station_id": "trading.risk", "reason": "not_in_this_workflow"},
    {"station_id": "trading.book", "reason": "not_in_this_workflow"},
    {"station_id": "trading.shadow", "reason": "not_in_this_workflow"},
    {"station_id": "trading.perf", "reason": "not_in_this_workflow"},
    {"station_id": "trading.lift", "reason": "not_in_this_workflow"},
)


def dataset_source(evidence):
    for item in sourced_records(evidence):
        source = str(item.get("source") or item.get("source_url") or "").strip()
        if _DATASET.fullmatch(source):
            return source
    return None


class TradingResearchHandler(_ProposalHandler):
    skip_model = True

    def __init__(self, ledger):
        super().__init__(ledger, TRADING_WORKFLOW_ID)

    def deterministic_response(self, record):
        source = dataset_source((record.get("action_params") or {}).get("context", {}).get("evidence_records"))
        if not source:
            return json.dumps({"dataset": "", "hypothesis": ""})
        return json.dumps({
            "dataset": source,
            "hypothesis": f"cites {source}; no second sample; no execution",
        })

    def verify(self, record, response_text):
        from orchestrator_v1.core.orchestrator import VerifyResult
        try:
            parsed = json.loads(response_text)
        except (TypeError, ValueError):
            parsed = None
        source = dataset_source((record.get("action_params") or {}).get("context", {}).get("evidence_records"))
        if not isinstance(parsed, dict) or not source or parsed.get("dataset") != source:
            return VerifyResult(passed=False, errors=["dataset required"], is_logic_error=True)
        hypothesis = str(parsed.get("hypothesis") or "")
        if not hypothesis.startswith(f"cites {source};"):
            return VerifyResult(passed=False, errors=["hypothesis must cite the dataset"], is_logic_error=True)
        if any(number not in source for number in _NUMBER.findall(hypothesis)):
            return VerifyResult(passed=False, errors=["hypothesis invented a number"], is_logic_error=True)
        return VerifyResult(passed=True, parsed_output=parsed)

    def artifacts_for(self, record, verify_result):
        source = verify_result.parsed_output["dataset"]
        return [f"dataset:{source}", f"hypothesis:{record['task_id']}"]

    def record_committed_steps(self, task_id):
        source = "dataset:unknown"
        getter = getattr(self, "queue_get", None)
        if getter is not None:
            source = (getter(task_id).get("action_params") or {}).get("dataset") or source
        self._write(task_id, source)

    def _write(self, task_id, source):
        _append_step(self.ledger, task_id, self.workflow_id, "data", "trading.data",
                     f"dataset:{source}", "DETERMINISTIC")
        _append_step(self.ledger, task_id, self.workflow_id, "research", "trading.research",
                     f"hypothesis:{task_id}", "DETERMINISTIC")
        _append_step(self.ledger, task_id, self.workflow_id, "approval", "jarvis.approval",
                     f"packet:{task_id}", "DETERMINISTIC",
                     event_type="TASK_WAITING_APPROVAL", state="WAITING_APPROVAL")


class TradingResearchCoordinator:
    def __init__(self, orchestrator):
        self.orchestrator = orchestrator
        self.handler = TradingResearchHandler(orchestrator.ledger)
        orchestrator.register_local_handler(TRADING_ACTION, self.handler)
        self.handler.queue_get = orchestrator.queue.get

    def submit(self, *, objective, context, created_by, tenant_id=None, idempotency_key):
        evidence = context.get("evidence_records") if isinstance(context, dict) else None
        problem = evidence_problem(evidence)
        if problem:
            raise LaunchRejected(problem)
        source = dataset_source(evidence)
        if not source:
            raise LaunchRejected("DATASET_REQUIRED")
        if not isinstance(objective, str) or not (3 <= len(objective.strip()) <= 500):
            raise LaunchRejected("INVALID_OBJECTIVE")
        tenant_id = tenant_id or canonical_tenant_id()
        manifest = _manifest("Trading research, no execution", objective.strip(),
                             created_by, tenant_id, "jarvis_v1.sector_workflows:trading")
        params = {"objective": objective.strip(), "context": {"evidence_records": evidence},
                  "workflow_id": TRADING_WORKFLOW_ID, "dataset": source}
        scope = f"{tenant_id}:{created_by}:{TRADING_WORKFLOW_ID}"
        task_id, created = _submit(self.orchestrator, manifest, TRADING_ACTION, params, scope, idempotency_key)
        return task_id, created


class RevenueFloorHandler(_ProposalHandler):
    json_mode = True
    require_inference_gateway = True
    model_timeout = 20

    def __init__(self, ledger):
        super().__init__(ledger, REVENUE_WORKFLOW_ID)

    def build_prompt(self, record):
        context = (record.get("action_params") or {}).get("context") or {}
        shape = {"fit": "INSUFFICIENT_EVIDENCE", "matched_problem": "text",
                 "evidence": ["E1"], "conflicts": []}
        return (
            "Return one JSON object with exactly these keys and no prose. "
            "Do not invent a price, a customer, or a send. "
            "Use only evidence_id values present in CONTEXT. "
            + json.dumps(shape)
            + "\nCONTEXT: " + json.dumps(context, ensure_ascii=False, sort_keys=True)
        )

    def verify(self, record, response_text):
        from funding_v1.revenue_agent import verify_revenue_output
        from orchestrator_v1.core.orchestrator import VerifyResult
        context = (record.get("action_params") or {}).get("context") or {}
        try:
            parsed = json.loads(response_text)
        except (TypeError, ValueError):
            parsed = None
        ok, errors = verify_revenue_output("OFFER_FIT_ANALYSIS", parsed, context)
        if ok and _NUMBER.search(str(parsed.get("matched_problem") or "")):
            ok = False
            errors = list(errors) + ["price is not evidence"]
        cited = set(parsed.get("evidence") or []) if isinstance(parsed, dict) else set()
        sourced = {item["evidence_id"] for item in sourced_records(context.get("evidence_records"))}
        if ok and (not cited or not cited.issubset(sourced)):
            ok = False
            errors = list(errors) + ["evidence source required"]
        return VerifyResult(passed=ok, parsed_output=parsed if ok else None,
                            errors=errors, is_logic_error=not ok)

    def artifacts_for(self, record, verify_result):
        return [f"offer:{record['task_id']}", f"proposal:{record['task_id']}"]

    def record_committed_steps(self, task_id):
        for step_id, station_id, output_ref in (
            ("find", "revenue.find", f"source:{task_id}"),
            ("market", "revenue.market", f"note:{task_id}"),
            ("offer", "revenue.offer", "price:unknown"),
            ("proposal", "revenue.proposal", f"proposal:{task_id}"),
        ):
            _append_step(self.ledger, task_id, self.workflow_id, step_id, station_id,
                         output_ref, "REVENUE_SKILL")
        _append_step(self.ledger, task_id, self.workflow_id, "outrev", "revenue.outrev",
                     f"packet:{task_id}", "DETERMINISTIC",
                     event_type="TASK_WAITING_APPROVAL", state="WAITING_APPROVAL")


REVENUE_WORKFLOW_ID = "jarvis.revenue.proposal.v1"
REVENUE_ACTION = "nexus_revenue_proposal_workflow"
REVENUE_NOT_RUN = (
    {"station_id": "revenue.prospect", "reason": "no_real_name_in_source"},
    {"station_id": "revenue.qualify", "reason": "no_real_name_in_source"},
    {"station_id": "revenue.crm", "reason": "no_external_crm"},
    {"station_id": "revenue.follow", "reason": "no_send"},
    {"station_id": "revenue.nego", "reason": "no_send"},
    {"station_id": "revenue.deliver", "reason": "no_contract"},
    {"station_id": "revenue.care", "reason": "no_customer"},
    {"station_id": "revenue.keep", "reason": "no_customer"},
    {"station_id": "revenue.stats", "reason": "revenue_absent"},
    {"station_id": "revenue.lift", "reason": "not_in_this_workflow"},
)


def _has_url(evidence):
    for item in sourced_records(evidence):
        source = str(item.get("source") or item.get("source_url") or "")
        if "://" in source:
            return True
    return False


class RevenueFloorCoordinator:
    def __init__(self, orchestrator):
        self.orchestrator = orchestrator
        self.handler = RevenueFloorHandler(orchestrator.ledger)
        orchestrator.register_local_handler(REVENUE_ACTION, self.handler)

    def submit(self, *, objective, context, created_by, tenant_id=None, idempotency_key):
        evidence = context.get("evidence_records") if isinstance(context, dict) else None
        problem = evidence_problem(evidence)
        if problem:
            raise LaunchRejected(problem)
        if not _has_url(evidence):
            raise LaunchRejected("URL_REQUIRED")
        if not isinstance(objective, str) or not (3 <= len(objective.strip()) <= 500):
            raise LaunchRejected("INVALID_OBJECTIVE")
        tenant_id = tenant_id or canonical_tenant_id()
        manifest = _manifest("Revenue proposal, no outreach", objective.strip(),
                             created_by, tenant_id, "funding_v1.revenue_agent:OFFER_FIT_ANALYSIS")
        params = {"objective": objective.strip(), "context": {"evidence_records": evidence},
                  "workflow_id": REVENUE_WORKFLOW_ID, "revenue_task_type": "OFFER_FIT_ANALYSIS"}
        scope = f"{tenant_id}:{created_by}:{REVENUE_WORKFLOW_ID}"
        return _submit(self.orchestrator, manifest, REVENUE_ACTION, params, scope, idempotency_key)


SOCIAL_WORKFLOW_ID = "jarvis.social.draft.v1"
SOCIAL_ACTION = "nexus_social_draft_workflow"
SOCIAL_NOT_RUN = (
    {"station_id": "social.trend", "reason": "no_channel"},
    {"station_id": "social.audience", "reason": "no_channel"},
    {"station_id": "social.cut", "reason": "not_in_this_workflow"},
    {"station_id": "social.adapt", "reason": "not_in_this_workflow"},
    {"station_id": "social.sched", "reason": "publish_disabled"},
    {"station_id": "social.pub", "reason": "publish_disabled"},
    {"station_id": "social.community", "reason": "no_channel"},
    {"station_id": "social.stats", "reason": "no_channel"},
    {"station_id": "social.lead", "reason": "no_channel"},
    {"station_id": "social.opt", "reason": "not_in_this_workflow"},
)


class SocialFloorHandler(_ProposalHandler):
    json_mode = True
    require_inference_gateway = True
    model_timeout = 20

    def __init__(self, ledger):
        super().__init__(ledger, SOCIAL_WORKFLOW_ID)

    def build_prompt(self, record):
        context = (record.get("action_params") or {}).get("context") or {}
        shape = {"verdict": "REVISE", "issues": [], "evidence": ["E1"]}
        return (
            "Return one JSON object for an internal review. APPROVE is not a publish. "
            "Cite only evidence_id values in CONTEXT. "
            + json.dumps(shape)
            + "\nCONTEXT: " + json.dumps(context, ensure_ascii=False, sort_keys=True)
        )

    def verify(self, record, response_text):
        from business_units.ai_fashion_agency.skills import verify_agency_output
        from orchestrator_v1.core.orchestrator import VerifyResult
        context = (record.get("action_params") or {}).get("context") or {}
        try:
            parsed = json.loads(response_text)
        except (TypeError, ValueError):
            parsed = None
        ok, errors = verify_agency_output("CONTENT_REVIEW", parsed, context)
        return VerifyResult(passed=ok, parsed_output=parsed if ok else None,
                            errors=errors, is_logic_error=not ok)

    def artifacts_for(self, record, verify_result):
        return [f"draft:{record['task_id']}"]

    def record_committed_steps(self, task_id):
        for step_id, station_id in (
            ("edit", "social.edit"),
            ("script", "social.script"),
            ("create", "social.create"),
            ("qc", "social.qc"),
        ):
            _append_step(self.ledger, task_id, self.workflow_id, step_id, station_id,
                         f"draft:{task_id}", "AGENCY_SKILL")
        _append_step(self.ledger, task_id, self.workflow_id, "ok", "social.ok",
                     f"packet:{task_id}", "DETERMINISTIC",
                     event_type="TASK_WAITING_APPROVAL", state="WAITING_APPROVAL")


class SocialFloorCoordinator:
    def __init__(self, orchestrator):
        self.orchestrator = orchestrator
        self.handler = SocialFloorHandler(orchestrator.ledger)
        orchestrator.register_local_handler(SOCIAL_ACTION, self.handler)

    def submit(self, *, source_task_id, created_by, owner, tenant_id=None, idempotency_key):
        tenant_id = tenant_id or canonical_tenant_id()
        try:
            source = self.orchestrator.queue.get(source_task_id)
        except KeyError as exc:
            raise LaunchRejected("TASK_NOT_FOUND", 404) from exc
        manifest = source.get("manifest") or {}
        if manifest.get("created_by") != created_by or manifest.get("tenant_id") != tenant_id:
            raise LaunchRejected("TASK_NOT_FOUND", 404)
        if not owns_floor_task(source, owner=owner, tenant_id=tenant_id):
            raise LaunchRejected("SOURCE_NOT_HANDOFF", 409)
        if source.get("state") != "PROPOSAL_ACCEPTED":
            raise LaunchRejected("SOURCE_NOT_ACCEPTED", 409)
        evidence = sourced_records(((source.get("action_params") or {}).get("context") or {}).get("evidence_records"))
        if not evidence:
            raise LaunchRejected("SOURCE_HAS_NO_EVIDENCE", 409)
        copied = [{key: item[key] for key in item if key in _EVIDENCE_FIELDS} for item in evidence]
        objective = f"Internal draft from {source_task_id}"
        task_manifest = _manifest("Social draft from an accepted handoff", objective,
                                  created_by, tenant_id, "business_units.ai_fashion_agency.skills:CONTENT_REVIEW")
        params = {"source_task_id": source_task_id, "context": {"evidence_records": copied},
                  "workflow_id": SOCIAL_WORKFLOW_ID}
        scope = f"{tenant_id}:{created_by}:{SOCIAL_WORKFLOW_ID}:{source_task_id}"
        return _submit(self.orchestrator, task_manifest, SOCIAL_ACTION, params, scope, idempotency_key)


FINANCE_STATIONS = (
    "finance.inrev", "finance.inexp", "finance.recon", "finance.attr", "finance.budget",
    "finance.margin", "finance.cash", "finance.roi", "finance.fore", "finance.risk",
    "finance.report", "finance.invest", "finance.opt",
)
FINANCE_WORKFLOW_ID = "jarvis.finance.report.v1"
FINANCE_ACTION = "nexus_finance_report_workflow"


def finance_empty():
    return {"source": "ledger", "task_id": None, "state": None, "delivery": "not_sent",
            "steps": [], "not_run": [{"station_id": station, "reason": "no_cost_document"}
                                     for station in FINANCE_STATIONS]}


def _cost_events(ledger):
    return [event for event in ledger.read_all()
            if event.get("event_type") == "COST_RECORDED"
            and str((event.get("payload") or {}).get("evidence_id") or "")
            and str((event.get("payload") or {}).get("source") or "").strip()]


def _corpus(evidence):
    parts = []
    for item in sourced_records(evidence):
        parts.append(str(item.get("source") or ""))
        parts.append(str(item.get("source_url") or ""))
        parts.append(str(item.get("note") or ""))
        parts.append(str(item.get("text") or ""))
    return "\n".join(parts)


class FinanceFloorHandler(_ProposalHandler):
    skip_model = True

    def __init__(self, ledger):
        super().__init__(ledger, FINANCE_WORKFLOW_ID)

    def deterministic_response(self, record):
        claim = str((record.get("action_params") or {}).get("claim") or "")
        return json.dumps({"claim": claim})

    def verify(self, record, response_text):
        from orchestrator_v1.core.orchestrator import VerifyResult
        params = record.get("action_params") or {}
        try:
            parsed = json.loads(response_text)
        except (TypeError, ValueError):
            parsed = None
        claim = str(parsed.get("claim") or "") if isinstance(parsed, dict) else ""
        corpus = _corpus((params.get("context") or {}).get("evidence_records"))
        orphans = [number for number in _NUMBER.findall(claim) if number not in corpus]
        if orphans:
            return VerifyResult(passed=False, errors=["figure without evidence"], is_logic_error=True)
        if not _cost_events(self.ledger):
            return VerifyResult(passed=False, errors=["no cost document"], is_logic_error=True)
        return VerifyResult(passed=True, parsed_output={"claim": claim})

    def artifacts_for(self, record, verify_result):
        return [f"recon:{record['task_id']}"]

    def record_committed_steps(self, task_id):
        _append_step(self.ledger, task_id, self.workflow_id, "recon", "finance.recon",
                     f"recon:{task_id}", "DETERMINISTIC")
        _append_step(self.ledger, task_id, self.workflow_id, "approval", "jarvis.approval",
                     f"packet:{task_id}", "DETERMINISTIC",
                     event_type="TASK_WAITING_APPROVAL", state="WAITING_APPROVAL")


class FinanceFloorCoordinator:
    def __init__(self, orchestrator):
        self.orchestrator = orchestrator
        self.handler = FinanceFloorHandler(orchestrator.ledger)
        orchestrator.register_local_handler(FINANCE_ACTION, self.handler)

    def empty(self):
        return finance_empty()

    def submit(self, *, claim, context, created_by, tenant_id=None, idempotency_key):
        evidence = context.get("evidence_records") if isinstance(context, dict) else None
        problem = evidence_problem(evidence)
        if problem:
            raise LaunchRejected(problem)
        if not isinstance(claim, str) or not (1 <= len(claim.strip()) <= 500):
            raise LaunchRejected("INVALID_CLAIM")
        corpus = _corpus(evidence)
        orphans = [number for number in _NUMBER.findall(claim) if number not in corpus]
        if not orphans and not _cost_events(self.orchestrator.ledger):
            return None
        tenant_id = tenant_id or canonical_tenant_id()
        manifest = _manifest("Finance report refuses unsourced figures", claim.strip(),
                             created_by, tenant_id, "jarvis_v1.sector_workflows:finance")
        params = {"claim": claim.strip(), "context": {"evidence_records": evidence},
                  "workflow_id": FINANCE_WORKFLOW_ID}
        scope = f"{tenant_id}:{created_by}:{FINANCE_WORKFLOW_ID}"
        return _submit(self.orchestrator, manifest, FINANCE_ACTION, params, scope, idempotency_key)


COUNCIL_STATIONS_NOT_RUN = (
    {"station_id": "council.exp", "reason": "no_experiment_outside_prod"},
    {"station_id": "council.measure", "reason": "no_experiment_outside_prod"},
    {"station_id": "council.review", "reason": "no_experiment_outside_prod"},
    {"station_id": "council.propose", "reason": "no_experiment_outside_prod"},
)
COUNCIL_WORKFLOW_ID = "jarvis.council.hypothesis.v1"
COUNCIL_ACTION = "nexus_council_hypothesis_workflow"
_FAILURES = {"TASK_FAILED", "TEST_FAILED"}


def council_empty():
    stations = (
        {"station_id": "council.obs", "reason": "no_failure_events"},
        {"station_id": "council.detect", "reason": "no_failure_events"},
        {"station_id": "council.diag", "reason": "no_failure_events"},
        {"station_id": "council.hypo", "reason": "no_failure_events"},
    ) + COUNCIL_STATIONS_NOT_RUN
    return {"source": "ledger", "task_id": None, "state": None, "delivery": "not_sent",
            "steps": [], "not_run": list(stations)}


def failure_event_ids(ledger):
    found = []
    for event in ledger.read_all():
        if event.get("event_type") in _FAILURES and event.get("event_id"):
            found.append(event["event_id"])
    return found[:20]


class CouncilFloorHandler(_ProposalHandler):
    skip_model = True

    def __init__(self, ledger):
        super().__init__(ledger, COUNCIL_WORKFLOW_ID)

    def deterministic_response(self, record):
        ids = list((record.get("action_params") or {}).get("event_ids") or [])
        return json.dumps({"hypothesis": "hypothesis", "event_ids": ids})

    def verify(self, record, response_text):
        from orchestrator_v1.core.orchestrator import VerifyResult
        try:
            parsed = json.loads(response_text)
        except (TypeError, ValueError):
            parsed = None
        if not isinstance(parsed, dict) or parsed.get("hypothesis") != "hypothesis":
            return VerifyResult(passed=False, errors=["hypothesis required"], is_logic_error=True)
        known = {event.get("event_id") for event in self.ledger.read_all()}
        cited = parsed.get("event_ids")
        if not isinstance(cited, list) or not cited or any(item not in known for item in cited):
            return VerifyResult(passed=False, errors=["event id is not in the ledger"], is_logic_error=True)
        return VerifyResult(passed=True, parsed_output=parsed)

    def artifacts_for(self, record, verify_result):
        return [f"hypothesis:{record['task_id']}"]

    def record_committed_steps(self, task_id):
        for step_id, station_id in (
            ("obs", "council.obs"),
            ("detect", "council.detect"),
            ("diag", "council.diag"),
            ("hypo", "council.hypo"),
        ):
            _append_step(self.ledger, task_id, self.workflow_id, step_id, station_id,
                         f"hypothesis:{task_id}", "DETERMINISTIC")
        _append_step(self.ledger, task_id, self.workflow_id, "approval", "jarvis.approval",
                     f"packet:{task_id}", "DETERMINISTIC",
                     event_type="TASK_WAITING_APPROVAL", state="WAITING_APPROVAL")


class CouncilFloorCoordinator:
    def __init__(self, orchestrator):
        self.orchestrator = orchestrator
        self.handler = CouncilFloorHandler(orchestrator.ledger)
        orchestrator.register_local_handler(COUNCIL_ACTION, self.handler)

    def submit(self, *, created_by, tenant_id=None, idempotency_key):
        ids = failure_event_ids(self.orchestrator.ledger)
        if not ids:
            return None
        tenant_id = tenant_id or canonical_tenant_id()
        manifest = _manifest("Council hypothesis from ledger failures",
                             "Read recorded failures. Do not adopt.",
                             created_by, tenant_id, "jarvis_v1.sector_workflows:council")
        params = {"event_ids": ids, "workflow_id": COUNCIL_WORKFLOW_ID}
        scope = f"{tenant_id}:{created_by}:{COUNCIL_WORKFLOW_ID}"
        return _submit(self.orchestrator, manifest, COUNCIL_ACTION, params, scope, idempotency_key)
