"""Channel-agnostic Jarvis service over the existing NEXUS Orchestrator.

Jarvis classifies and projects user intent. It never selects an executor and
never bypasses TaskQueue, Router, EventLedger or the Orchestrator approval gate.
"""
from __future__ import annotations

import json
import os
import re
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

SERVER = Path(__file__).resolve().parents[1]
ROOT = SERVER.parent
ORCH = SERVER / "orchestrator_v1"
REVIEW_PIPELINE = SERVER / "review_pipeline_v1"
sys.path.insert(0, str(ORCH))
sys.path.insert(0, str(REVIEW_PIPELINE))

from core.capability import load_registry  # noqa: E402
from core.ledger import EventLedger  # noqa: E402
from core.ollama_worker import call_local_model, is_ollama_reachable  # noqa: E402
from core.orchestrator import Orchestrator  # noqa: E402
from core.task_queue import new_task_id  # noqa: E402
import jarvis_delivery  # noqa: E402
from review_engine import process_work_product  # noqa: E402
from review_matrix import get_matrix_entry  # noqa: E402

# NEXUS TASK #0009 - default per le task create da Jarvis quando nessun
# work_type esplicito e' dichiarato in metadata. 'business_analysis' impone
# review_required=True nella Review Matrix: e' la scelta onesta (Jarvis fa
# tipicamente analisi, non backfill/codice), non la piu' comoda - se un
# provider di review non e' ancora connesso il risultato sara' davvero
# ESCALATION_READY_FOR_MANUAL_DELIVERY, mai una consegna finale non revisionata.
_DEFAULT_JARVIS_WORK_TYPE = "business_analysis"

TENANT_ID = "tenant-1"
CONTROL_PLANE_PATH = "/app/company"


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def classify(text: str, metadata: dict | None = None) -> str:
    value = (text or "").strip().lower()
    metadata = metadata or {}
    action = str(metadata.get("approval_action") or "").upper()
    if action in ("REJECT", "RIFIUTA") or re.search(r"\b(rifiuta|reject)\b", value):
        return "REJECTION"
    if action in ("APPROVE", "APPROVAL", "APPROVA") or re.search(r"\b(approva|approve)\b", value):
        return "APPROVAL"
    if re.search(r"\b(crea|create|avvia|analizza|analyze)\b.*\b(task|nexus task|opportunit)", value):
        return "TASK_REQUEST"
    if re.search(r"\b(a che punto|stato|status|come procede)\b", value):
        return "FOLLOW_UP"
    if "?" in value or re.search(r"\b(cosa|quali|chi|perché|perche|why|what|today|oggi)\b", value):
        return "QUERY"
    return "UNKNOWN"


_WORK_TYPES = {
    "routine_summary", "registry_backfill", "business_analysis", "scientific_research",
    "complex_code", "architecture_design", "deployment", "trading_critical",
}


def classify_work_type(text: str, metadata: dict | None = None) -> str:
    """Choose Review Matrix policy deterministically, never an executor.

    An explicit valid value wins. Otherwise only narrow routine/status requests
    receive the no-premium routine policy; ambiguous analysis remains fail-closed
    as business_analysis.
    """
    metadata = metadata or {}
    explicit = metadata.get("work_type")
    if explicit in _WORK_TYPES:
        return explicit
    value = (text or "").lower()
    if re.search(r"\b(deploy|release|rilascio)\b", value):
        return "deployment"
    if re.search(r"\b(trading|ordine|order|position|posizione|risk limit)\b", value):
        return "trading_critical"
    if re.search(r"\b(codice|code|bug|fix|patch|refactor)\b", value):
        return "complex_code"
    if re.search(r"\b(scientific|research|ricerca|ipotesi|hypothesis|backtest)\b", value):
        return "scientific_research"
    if re.search(r"\b(riassum\w*|riassunt\w*|summary|riepilog\w*|stato|status)\b", value) and not re.search(
            r"\b(analizza|analyze|valuta|evaluate|opportunit)\b", value):
        return "routine_summary"
    return _DEFAULT_JARVIS_WORK_TYPE


class JarvisService:
    def __init__(self, queue_path=None, ledger_path=None):
        self.orchestrator = Orchestrator(queue_path=queue_path, ledger_path=ledger_path)
        self.queue = self.orchestrator.queue
        self.ledger = self.orchestrator.ledger
        self.conversations: dict[str, str] = {}
        # NEXUS TASK #0009 - cache process-local (stessa disciplina gia'
        # dichiarata per self.conversations): un WORK_PRODUCT_V1 va calcolato
        # una sola volta per task_id, mai ricalcolato/ri-escalato a ogni
        # singolo follow-up ("a che punto e'?").
        self._work_product_cache: dict[str, tuple] = {}

    def _response(self, message, response_type, summary, *, details=None, task_id=None,
                  status="COMPLETED", actions=None, confidence="HIGH", generated_by="jarvis_v1"):
        return {
            "response_id": f"rsp_{uuid.uuid4().hex[:16]}",
            "conversation_id": message["conversation_id"], "response_type": response_type,
            "summary": summary, "details": details or {},
            "source_refs": (details or {}).get("source_refs", []), "task_id": task_id,
            "status": status, "priority": message.get("priority", "NORMAL"),
            "actions": actions or [], "deep_link": CONTROL_PLANE_PATH,
            "voice_summary": None, "generated_by": generated_by, "confidence": confidence,
        }

    def handle(self, message: dict) -> dict:
        if message.get("input_type") != "TEXT":
            return self._response(message, "ERROR", "Input type not supported in V1.",
                                  status="UNAVAILABLE", confidence="HIGH")
        request_class = message.get("request_class")
        if request_class in (None, "UNKNOWN"):
            request_class = classify(message.get("text", ""), message.get("metadata"))
        message["request_class"] = request_class
        self.ledger.append("USER_MESSAGE_RECEIVED", None,
                           {"message_id": message["message_id"], "channel": message["channel"],
                            "request_class": request_class}, actor="jarvis_gateway")
        if request_class == "QUERY":
            return self.query(message)
        if request_class in ("TASK", "TASK_REQUEST"):
            return self.create_task(message)
        if request_class == "FOLLOW_UP":
            return self.follow_up(message)
        if request_class in ("APPROVAL", "REJECTION"):
            return self.approval(message)
        return self._response(message, "ERROR", "Request class unavailable.",
                              status="UNKNOWN", confidence="UNKNOWN")

    def _facts_today(self):
        today = datetime.now(timezone.utc).date().isoformat()
        events = [e for e in self.ledger.read_all() if str(e.get("timestamp", "")).startswith(today)]
        tasks = self.queue.list_all()
        funding = SERVER / "funding_v1" / "opportunity_priority_queue_v1.json"
        source_refs = ["server/orchestrator_v1/runtime_state/event_ledger_v1.jsonl",
                       "server/orchestrator_v1/runtime_state/task_queue_v1.json"]
        funding_summary = None
        vault_notes = []
        knowledge_root = Path(os.environ.get("NEXUS_KNOWLEDGE_ROOT", ROOT))
        vault = knowledge_root / "vault"
        if vault.is_dir():
            candidates = sorted(vault.glob("**/*.md"), key=lambda p: p.stat().st_mtime, reverse=True)[:12]
            vault_notes = [{"title": path.stem, "source": path.relative_to(knowledge_root).as_posix(),
                            "updated_at": datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).isoformat()}
                           for path in candidates]
            source_refs.extend(note["source"] for note in vault_notes)
        if funding.is_file():
            try:
                data = json.loads(funding.read_text(encoding="utf-8"))
                payload = data.get("payload", {})
                funding_summary = {"count": len(payload.get("ranked_opportunities", [])),
                                   "generated_at": data.get("generated_at")}
                source_refs.append("server/funding_v1/opportunity_priority_queue_v1.json")
            except (OSError, json.JSONDecodeError):
                funding_summary = None
        return {
            "date": today,
            "completed": [t["task_id"] for t in tasks if t["state"] == "COMPLETED"],
            "in_progress": [t["task_id"] for t in tasks if t["state"] in ("QUEUED", "RUNNING", "WAITING_PROVIDER")],
            "escalations": [t["task_id"] for t in tasks if t["state"] == "ESCALATION_REQUIRED"],
            "pending_approvals": [t["task_id"] for t in tasks if t["state"] == "WAITING_APPROVAL"],
            "events": events[-50:], "funding": funding_summary, "recent_vault_notes": vault_notes,
            "agents": self.agents(),
            "build": {"git_sha": os.environ.get("RENDER_GIT_COMMIT") or os.environ.get("NEXUS_GIT_SHA") or "UNKNOWN"},
            "source_refs": source_refs,
        }

    def query(self, message):
        facts = self._facts_today()
        premium_calls = 0
        local_used = False
        summary = (f"Oggi: {len(facts['completed'])} task completate, "
                   f"{len(facts['in_progress'])} in corso, {len(facts['escalations'])} escalation, "
                   f"{len(facts['pending_approvals'])} approval pendenti.")
        if is_ollama_reachable(timeout=1):
            prompt = ("Riassumi in italiano questi fatti canonici senza aggiungere fatti o giudizi. "
                      "Rispondi in massimo 6 frasi. JSON:\n" + json.dumps(facts, ensure_ascii=False))
            call = call_local_model(prompt, timeout=45, ensure_single_resident=False)
            if call["success"] and call.get("response_text"):
                summary = call["response_text"].strip(); local_used = True
        self.ledger.append("QUERY_EXECUTED", None,
                           {"message_id": message["message_id"], "local_model_used": local_used,
                            "premium_calls": premium_calls}, actor="jarvis_service")
        response = self._response(message, "ANSWER", summary,
                                  details={**facts, "premium_calls": premium_calls,
                                           "local_model_used": local_used},
                                  status="COMPLETED" if local_used else "PARTIAL",
                                  confidence="HIGH" if local_used else "MEDIUM",
                                  generated_by="ministral-3:3b" if local_used else "jarvis_deterministic_fallback")
        self.ledger.append("RESULT_DELIVERED", None, {"response_id": response["response_id"]},
                           actor="jarvis_service")
        return response

    def create_task(self, message):
        text = (message.get("text") or "").strip()
        attrs = message.get("metadata", {})
        required = ["summaries"]
        if attrs.get("second_opinion"): required.append("review")
        task_id = new_task_id()
        work_type = classify_work_type(text, attrs)
        manifest = {
            "task_id": task_id, "title": text[:120] or "Jarvis task", "objective": text,
            "task_type": "RESEARCH", "work_type": work_type,
            "priority": message.get("priority", "NORMAL"),
            "risk_level": "A1", "scientific_risk": "LOW", "code_risk": "NONE",
            "financial_risk": "NONE", "required_capabilities": required,
            "deterministic_tools_available": False, "repo_scope": "read-only analysis",
            "files_allowed": [], "files_forbidden": ["MQL5/**", "server/research_scripts/**"],
            "dependencies": attrs.get("dependencies", []), "blockers": [],
            "expected_artifacts": ["RESULT_PACKET_V1"],
            "success_criteria": ["Result is source-backed", "No irreversible action"],
            "verifier": "independent_review", "estimated_complexity": "MEDIUM",
            "estimated_runtime": "durable", "premium_allowed": False,
            "preferred_executor": "TIER1_LOCAL_CHEAP",
            "fallback_executors": ["TIER2_LOCAL_STRONG", "TIER3_CLAUDE", "TIER4_CODEX"],
            "approval_required": "REVIEW_REQUIRED", "created_by": f"jarvis:{message['user_id']}",
            "created_at": now_iso(), "tenant_id": TENANT_ID, "account_scope_id": None,
        }
        self.orchestrator.submit(manifest, dependencies=manifest["dependencies"], action="jarvis_task",
                                 action_params={"request_class": "TASK_REQUEST", "source_message_id": message["message_id"]})
        self.conversations[message["conversation_id"]] = task_id
        record = self.queue.get(task_id)
        return self._response(message, "TASK_ACK", f"Task {task_id} created.", task_id=task_id,
                              status=record["state"], details={"executor": record.get("executor"),
                              "approval_required": manifest["approval_required"],
                              "work_type": work_type,
                              "review_required": get_matrix_entry(work_type)["review_required"],
                              "source_refs": ["TASK_MANIFEST_V1", "orchestrator queue"]})

    def follow_up(self, message):
        task_id = message.get("metadata", {}).get("task_id") or self.conversations.get(message["conversation_id"])
        if not task_id:
            return self._response(message, "ERROR", "No task context available.", status="UNKNOWN")
        try: record = self.queue.get(task_id)
        except KeyError: return self._response(message, "ERROR", "Task not found.", task_id=task_id, status="UNKNOWN")
        self.ledger.append("TASK_STATUS_REQUESTED", task_id, {"message_id": message["message_id"]}, actor="jarvis_service")
        if record["state"] == "COMPLETED":
            return self._deliver_finalized_result(message, task_id, record)
        return self._response(message, "TASK_STATUS", f"{task_id}: {record['state']}", task_id=task_id,
                              status=record["state"], details={"executor": record.get("executor"),
                              "dependencies": record.get("dependencies"), "source_refs": ["orchestrator queue"]})

    def _run_review_pipeline(self, task_id, record):
        """NEXUS TASK #0009 - collega la Multi-Agent Review & Finalization
        Pipeline V1 (#0008) al primo punto in cui Jarvis osserva un producer
        output REALE (record['result_packet'], scritto da chi ha eseguito il
        task - il Router resta l'unico che sceglie l'executor, Jarvis legge
        solo il risultato). Nessun output senza verifier.passed=True viene
        mai trattato come una verifica riuscita per default."""
        result_packet = record.get("result_packet") or {}
        manifest = record.get("manifest") or {}
        work_type = (manifest.get("work_type") or
                     (manifest.get("metadata") or {}).get("work_type") or
                     _DEFAULT_JARVIS_WORK_TYPE)
        verifier_info = result_packet.get("verifier") or {}

        def attempt():
            return {"agent_id": record.get("executor") or "UNKNOWN",
                   "specialist_role": "LOCAL_GENERALIST", "output": result_packet,
                   "verify_passed": bool(verifier_info.get("passed")),
                   "verify_errors": verifier_info.get("errors") or []}

        wp, frp, _events = process_work_product(
            task_id=task_id, work_type=work_type, attempts=[attempt], ledger=self.ledger,
            sources=result_packet.get("files_read", []),
            changed_files=result_packet.get("files_changed", []),
            tests=result_packet.get("tests") or {"ran": False, "passed": 0, "failed": 0})
        return wp, frp

    def _deliver_finalized_result(self, message, task_id, record):
        if task_id in self._work_product_cache:
            wp, frp = self._work_product_cache[task_id]
        else:
            wp, frp = self._run_review_pipeline(task_id, record)
            self._work_product_cache[task_id] = (wp, frp)

        if frp is not None:
            summary = jarvis_delivery.format_task_completed_summary(frp)
            return self._response(message, "TASK_STATUS", summary, task_id=task_id, status="FINALIZED",
                                  details={"final_result_packet": frp, "source_refs": frp["sources"]},
                                  confidence=frp["confidence"], generated_by="review_pipeline_v1")

        if wp["blocked_reason"] and "ESCALATION_READY_FOR_MANUAL_DELIVERY" in wp["blocked_reason"]:
            reviewer_role = (wp.get("reviewer") or {}).get("specialist_role", "specialist")
            text = (f"Il lavoro locale è completato, ma la policy richiede una review "
                   f"{reviewer_role} - il provider non è ancora connesso in automatico. "
                   "Ho preparato il pacchetto di escalation, serve invio manuale.")
            return self._response(message, "TASK_STATUS", text, task_id=task_id,
                                  status="ESCALATION_READY_FOR_MANUAL_DELIVERY",
                                  details={"blocked_reason": wp["blocked_reason"]}, confidence="MEDIUM")

        return self._response(message, "TASK_STATUS", f"Lavoro bloccato: {wp['blocked_reason']}",
                              task_id=task_id, status="BLOCKED",
                              details={"blocked_reason": wp["blocked_reason"]}, confidence="LOW")

    def approval(self, message):
        meta = message.get("metadata", {}); task_id = meta.get("task_id")
        action = str(meta.get("approval_action") or message.get("text") or "").upper()
        if not task_id:
            return self._response(message, "ERROR", "Approval requires task_id.", status="UNKNOWN")
        try: record = self.queue.get(task_id)
        except KeyError: return self._response(message, "ERROR", "Task not found.", task_id=task_id, status="UNKNOWN")
        if record["state"] != "WAITING_APPROVAL":
            return self._response(message, "ERROR", "Task is not waiting for approval.", task_id=task_id,
                                  status=record["state"])
        if action in ("APPROVE", "APPROVAL", "APPROVA"):
            self.queue.transition(task_id, "QUEUED")
            self.ledger.append("APPROVAL_GRANTED", task_id, {"message_id": message["message_id"]}, actor="jarvis_gateway")
        elif action in ("REJECT", "RIFIUTA"):
            self.queue.transition(task_id, "FAILED")
            self.ledger.append("APPROVAL_REJECTED", task_id, {"message_id": message["message_id"]}, actor="jarvis_gateway")
        else:
            return self._response(message, "ERROR", "Unknown approval action.", task_id=task_id, status=record["state"])
        updated = self.queue.get(task_id)
        return self._response(message, "APPROVAL", f"{task_id}: {updated['state']}", task_id=task_id,
                              status=updated["state"])

    def agents(self):
        agents = []
        for agent in load_registry().get("agents", []):
            state = agent.get("quota_state") or agent.get("availability") or "UNKNOWN"
            if agent.get("availability") != "ONLINE": state = "OFFLINE"
            agents.append({"agent_id": agent.get("agent_id"), "provider": agent.get("provider"),
                           "status": state, "availability": agent.get("availability"),
                           "quota_state": agent.get("quota_state")})
        return agents
