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
from .conversation_store import ConversationStore
from .programming import build_plan, extract_repo_paths, is_programming_request
from .free_coding_worker import FreeCodingWorkerHandler

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
    if metadata.get("confirm_cancel"):
        return "COMMAND"
    if value.startswith("/") or re.search(
            r"\b(help|aiuto|dettagli|details|annulla|cancella|cancel|continua|agents|agenti|approvals)\b", value):
        return "COMMAND"
    if action in ("REJECT", "RIFIUTA") or re.search(r"\b(rifiuta|reject)\b", value):
        return "REJECTION"
    if action in ("APPROVE", "APPROVAL", "APPROVA") or re.search(r"\b(approva|approve)\b", value):
        return "APPROVAL"
    if re.search(r"\b(crea|create|avvia|analizza|analyze)\b.*\b(task|nexus task|opportunit)", value):
        return "TASK_REQUEST"
    if is_programming_request(value):
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


_STATE_MESSAGES = {
    "QUEUED": "è in coda e attende il dispatcher",
    "RUNNING": "è in esecuzione",
    "BLOCKED": "è bloccata e richiede diagnosi o intervento",
    "ESCALATION_REQUIRED": "richiede escalation; nessun provider premium viene chiamato automaticamente",
    "WAITING_APPROVAL": "attende una tua approvazione",
    "COMPLETED": "è completata",
    "CANCELLED": "è stata annullata",
    "FAILED": "è terminata con errore",
}


class JarvisService:
    def __init__(self, queue_path=None, ledger_path=None, conversation_path=None):
        self.orchestrator = Orchestrator(queue_path=queue_path, ledger_path=ledger_path)
        self.queue = self.orchestrator.queue
        self.ledger = self.orchestrator.ledger
        if conversation_path is None:
            base = Path(queue_path).parent if queue_path else SERVER / "orchestrator_v1" / "runtime_state"
            conversation_path = base / "conversation_context_v2.json"
        self.conversation_store = ConversationStore(conversation_path)
        workspace_root = Path(conversation_path).parent / "coding_workspaces_v1"
        self.orchestrator.register_local_handler(
            "conversational_programming",
            FreeCodingWorkerHandler(project_root=ROOT, workspace_root=workspace_root))
        # NEXUS TASK #0009 - cache process-local (stessa disciplina gia'
        # dichiarata per self.conversations): un WORK_PRODUCT_V1 va calcolato
        # una sola volta per task_id, mai ricalcolato/ri-escalato a ogni
        # singolo follow-up ("a che punto e'?").
        self._work_product_cache: dict[str, tuple] = {}
        self.dispatcher_status_provider = None
        self.provider_connector = None

    def set_dispatcher_status_provider(self, provider):
        """Attach a read-only runtime status projection without owning dispatcher logic."""
        self.dispatcher_status_provider = provider

    def set_provider_connector(self, connector):
        """Attach the existing ProviderConnectorV1 so a human REJECT on a
        conversational_programming task can start the NEXUS Dynamic
        Specialist Review (core/specialist_review.py) instead of dead-ending
        at FAILED. Jarvis still never selects a provider itself - it only
        hands off to the Core component that already owns provider state/
        policy/calls."""
        self.provider_connector = connector

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
        if request_class == "COMMAND":
            return self.command(message)
        return self._response(message, "ANSWER",
            "Non ho riconosciuto una richiesta operativa precisa. Posso creare o controllare task, "
            "mostrare dettagli, approval, agenti e stato NEXUS. Scrivi /help per esempi.",
            status="PARTIAL", confidence="MEDIUM",
            actions=[{"type": "HELP", "label": "Mostra aiuto"}])

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
        programming_plan = None
        if is_programming_request(text):
            context = self.conversation_store.get(message["conversation_id"])
            allowed_paths = list(attrs.get("files_allowed") or extract_repo_paths(text))
            programming_plan = build_plan(
                text, last_task_id=context.get("last_task_id"),
                allowed_paths=allowed_paths)
        required = ["summaries"]
        if programming_plan:
            required = ["small_python_functions", "unit_test_writing"]
        if attrs.get("second_opinion"): required.append("review")
        task_id = new_task_id()
        work_type = "complex_code" if programming_plan else classify_work_type(text, attrs)
        premium_allowed = work_type in ("scientific_research", "complex_code")
        scientific_risk = "MEDIUM" if work_type == "scientific_research" else "LOW"
        code_risk = "HIGH" if work_type == "complex_code" else "NONE"
        manifest = {
            "task_id": task_id, "title": text[:120] or "Jarvis task", "objective": text,
            "task_type": "CODE" if programming_plan else "RESEARCH", "work_type": work_type,
            "priority": message.get("priority", "NORMAL"),
            "risk_level": "A1", "scientific_risk": scientific_risk, "code_risk": code_risk,
            "financial_risk": "NONE", "required_capabilities": required,
            "deterministic_tools_available": False,
            "repo_scope": "task-scoped repository work" if programming_plan else "read-only analysis",
            "files_allowed": (programming_plan or {}).get("capability_scope", {}).get("allowed_paths", []),
            "files_forbidden": ["MQL5/**", "server/research_scripts/**", ".env", "**/.env", "**/*secret*"],
            "dependencies": attrs.get("dependencies", []), "blockers": [],
            "expected_artifacts": ["RESULT_PACKET_V1"],
            "success_criteria": ["Result is source-backed", "No irreversible action"],
            "verifier": "independent_review", "estimated_complexity": "MEDIUM",
            "estimated_runtime": "durable", "premium_allowed": premium_allowed,
            "preferred_executor": "TIER1_LOCAL_CHEAP",
            "fallback_executors": ["TIER2_LOCAL_STRONG", "TIER3_CLAUDE", "TIER4_CODEX"],
            "approval_required": ((programming_plan or {}).get("approval_required") or "REVIEW_REQUIRED"),
            "created_by": f"jarvis:{message['user_id']}",
            "created_at": now_iso(), "tenant_id": TENANT_ID, "account_scope_id": None,
        }
        action = "conversational_programming" if programming_plan else "jarvis_task"
        action_params = {"request_class": "TASK_REQUEST",
                         "source_message_id": message["message_id"],
                         "conversation_id": message["conversation_id"]}
        if programming_plan:
            action_params["execution_plan"] = programming_plan
            action_params["test_commands"] = list(attrs.get("test_commands") or [])
        self.orchestrator.submit(manifest, dependencies=manifest["dependencies"], action=action,
                                 action_params=action_params)
        if programming_plan and programming_plan["approval_required"] == "EXPLICIT_USER_APPROVAL":
            self.queue.transition(task_id, "WAITING_APPROVAL")
            self.ledger.append("APPROVAL_REQUIRED", task_id,
                               {"reason": "conversational programming PUSH boundary",
                                "operation": "PUSH"}, actor="jarvis_service")
        self.conversation_store.update(message["conversation_id"], last_task_id=task_id,
                                       user_id=str(message["user_id"]))
        record = self.queue.get(task_id)
        return self._response(message, "TASK_ACK", f"Task {task_id} created.", task_id=task_id,
                              status=record["state"], details={"executor": record.get("executor"),
                              "approval_required": manifest["approval_required"],
                              "work_type": work_type,
                              "execution_plan": programming_plan,
                              "review_required": get_matrix_entry(work_type)["review_required"],
                              "source_refs": ["TASK_MANIFEST_V1", "orchestrator queue"]})

    def _latest_compatible_task(self, message):
        conversation_id = message["conversation_id"]
        user_id = str(message["user_id"])
        candidates = []
        for record in self.queue.list_all():
            params = record.get("action_params") or {}
            created_by = (record.get("manifest") or {}).get("created_by")
            if params.get("conversation_id") == conversation_id or created_by == f"jarvis:{user_id}":
                candidates.append(record)
        candidates.sort(key=lambda item: item.get("updated_at") or item.get("created_at") or "", reverse=True)
        return candidates[0]["task_id"] if candidates else None

    def _resolve_task_id(self, message):
        explicit = message.get("metadata", {}).get("task_id")
        if not explicit:
            match = re.search(r"\bTASK_[A-Z0-9]+\b", message.get("text") or "", re.I)
            explicit = match.group(0).upper() if match else None
        context = self.conversation_store.get(message["conversation_id"])
        task_id = explicit or context.get("last_task_id") or self._latest_compatible_task(message)
        if task_id:
            self.conversation_store.update(message["conversation_id"], last_task_id=task_id,
                                           user_id=str(message["user_id"]))
        return task_id

    def _task_details(self, record, technical=False):
        task_id = record["task_id"]
        details = {
            "state": record.get("state"), "human_state": _STATE_MESSAGES.get(record.get("state"), "ha stato non noto"),
            "title": (record.get("manifest") or {}).get("title"),
            "executor": record.get("executor"), "dependencies": record.get("dependencies") or [],
            "retry_count": record.get("retry_count"), "dispatch_attempts": record.get("dispatch_attempts"),
            "updated_at": record.get("updated_at"), "started_at": record.get("started_at"),
            "completed_at": record.get("completed_at"),
            "next_step": self._next_step(record),
            "source_refs": ["orchestrator queue", "Activity Ledger"],
        }
        if technical:
            events = self.ledger.read_for_task(task_id)
            escalation = record.get("escalation") or {}
            safe_event_keys = {"reason", "failure_class", "classification", "target", "tier",
                               "executor", "attempt", "final_state", "released", "actor"}
            details.update({
                "action": record.get("action"),
                "dispatch_last_error": record.get("dispatch_last_error"), "recovery": record.get("recovery"),
                "escalation": {key: escalation.get(key) for key in ("target", "classification")
                               if escalation.get(key) is not None},
                "result_decision": (record.get("result_packet") or {}).get("decision"),
                "lifecycle": [{"event_type": event.get("event_type"), "timestamp": event.get("timestamp"),
                               "payload": {key: value for key, value in (event.get("payload") or {}).items()
                                           if key in safe_event_keys}} for event in events],
            })
        return details

    @staticmethod
    def _next_step(record):
        state = record.get("state")
        return {
            "QUEUED": "Il dispatcher la prenderà quando sarà il prossimo lavoro eseguibile.",
            "RUNNING": "Attendi il completamento; lo stop forzato non è sicuro in V2.1.",
            "BLOCKED": "Consulta la causa e il lifecycle prima di decidere un recupero manuale.",
            "ESCALATION_REQUIRED": "Serve il provider o revisore indicato dall’escalation.",
            "WAITING_APPROVAL": "Approva o rifiuta dopo aver controllato i dettagli.",
            "COMPLETED": "Il risultato è disponibile per la revisione finale.",
            "CANCELLED": "Nessuna azione successiva automatica.",
            "FAILED": "Controlla l’errore prima di un eventuale retry manuale.",
        }.get(state, "Controlla i dettagli canonici della task.")

    def follow_up(self, message):
        task_id = self._resolve_task_id(message)
        if not task_id:
            return self._response(message, "ERROR", "No task context available.", status="UNKNOWN")
        try: record = self.queue.get(task_id)
        except KeyError: return self._response(message, "ERROR", "Task not found.", task_id=task_id, status="UNKNOWN")
        self.ledger.append("TASK_STATUS_REQUESTED", task_id, {"message_id": message["message_id"]}, actor="jarvis_service")
        if record["state"] == "COMPLETED":
            return self._deliver_finalized_result(message, task_id, record)
        technical = record["state"] == "BLOCKED" or bool(message.get("metadata", {}).get("technical_details")) or bool(
            re.search(r"\b(tecnic|technical|diagnostic)\w*\b", message.get("text") or "", re.I))
        summary = f"La task {task_id} {_STATE_MESSAGES.get(record['state'], 'ha stato ' + record['state'])}."
        return self._response(message, "TASK_STATUS", summary, task_id=task_id,
                              status=record["state"], details=self._task_details(record, technical=technical),
                              actions=[{"type": "DETAILS", "task_id": task_id},
                                       {"type": "CANCEL", "task_id": task_id}])

    def command(self, message):
        text = (message.get("text") or "").strip()
        value = text.lower()
        if value in ("/start", "/help") or re.search(r"\b(help|aiuto)\b", value):
            return self._response(message, "ANSWER",
                "Sono Jarvis. Posso creare task, mostrarne stato e dettagli, annullare task non in esecuzione, "
                "gestire approval e mostrare stato NEXUS, agenti e approval. Comandi: /status /tasks /approvals /agents.",
                details={"commands": ["/start", "/help", "/status", "/tasks", "/approvals", "/agents"]})
        if value == "/agents" or re.search(r"\b(agents|agenti)\b", value):
            items = self.agents()
            return self._response(message, "ANSWER", f"Agenti registrati: {len(items)}.",
                                  details={"items": items, "source_refs": ["agent registry"]})
        if value == "/approvals" or "approval" in value:
            items = self.queue.list_by_state("WAITING_APPROVAL")
            return self._response(message, "ANSWER", f"Approval pendenti: {len(items)}.",
                                  details={"items": [x["task_id"] for x in items],
                                           "source_refs": ["orchestrator queue"]})
        if value == "/tasks":
            uid = f"jarvis:{message['user_id']}"
            items = [r for r in self.queue.list_all() if (r.get("manifest") or {}).get("created_by") == uid]
            items.sort(key=lambda r: r.get("updated_at") or "", reverse=True)
            recent = items[:10]
            counts = {}
            for record in recent: counts[record["state"]] = counts.get(record["state"], 0) + 1
            return self._response(message, "ANSWER", f"Hai {len(recent)} task recenti.",
                                  details={"view": "TASK_LIST", "items": [{
                                      "task_id": r["task_id"], "state": r["state"],
                                      "title": (r.get("manifest") or {}).get("title"),
                                      "updated_at": r.get("updated_at")}
                                      for r in recent], "counts": counts,
                                      "source_refs": ["orchestrator queue"]})
        if value == "/status" or re.search(r"\b(status nexus|stato nexus)\b", value):
            states = {}
            all_tasks = self.queue.list_all()
            for record in all_tasks: states[record["state"]] = states.get(record["state"], 0) + 1
            recent = sorted(all_tasks, key=lambda record: record.get("updated_at") or "", reverse=True)[:10]
            completed_recent = sum(1 for record in recent if record.get("state") == "COMPLETED")
            dispatcher = {"enabled": None, "running": None, "status": "UNKNOWN"}
            if self.dispatcher_status_provider:
                try:
                    dispatcher = self.dispatcher_status_provider()
                except Exception:
                    dispatcher = {"enabled": None, "running": None, "status": "UNKNOWN"}
            return self._response(message, "ANSWER", "NEXUS è operativo; ecco lo stato canonico della Queue.",
                                  details={"view": "SYSTEM_STATUS", "task_states": states,
                                           "completed_recent": completed_recent,
                                           "dispatcher": dispatcher, "agents": self.agents(),
                                           "source_refs": ["orchestrator queue", "agent registry"]})
        if re.search(r"\b(dettagli|details|diagnostic)\b", value):
            if re.search(r"\b(tecnic|technical|diagnostic)\w*\b", value):
                message.setdefault("metadata", {})["technical_details"] = True
            return self.follow_up(message)
        if re.search(r"\b(continua|continue)\b", value):
            return self.follow_up(message)
        if message.get("metadata", {}).get("confirm_cancel") or re.search(
                r"\b(annulla|annullamento|cancella|cancel)\b", value):
            return self.cancel(message)
        return self._response(message, "ANSWER", "Comando non riconosciuto. Scrivi /help per le opzioni disponibili.",
                              status="PARTIAL", confidence="MEDIUM")

    def cancel(self, message):
        task_id = self._resolve_task_id(message)
        if not task_id:
            return self._response(message, "ERROR", "Non trovo una task da annullare.", status="UNKNOWN")
        try:
            record = self.queue.get(task_id)
        except KeyError:
            return self._response(message, "ERROR", "Task non trovata.", task_id=task_id, status="UNKNOWN")
        metadata = message.get("metadata", {})
        context = self.conversation_store.get(message["conversation_id"])
        confirmed = bool(metadata.get("confirm_cancel")) or bool(re.search(
            r"\b(conferma|confirm)\b", message.get("text") or "", re.I))
        pending = context.get("pending_action") or {}
        if confirmed and pending.get("type") == "CANCEL" and pending.get("task_id") == task_id:
            if record["state"] == "RUNNING":
                return self._response(message, "ERROR", "Non annullo una task RUNNING: serve arresto controllato del worker.",
                                      task_id=task_id, status="RUNNING")
            try:
                updated = self.queue.transition(task_id, "CANCELLED", cancellation={"actor": "jarvis_user"})
            except AssertionError:
                return self._response(message, "ERROR", f"La task in stato {record['state']} non è annullabile.",
                                      task_id=task_id, status=record["state"])
            self.conversation_store.clear_pending(message["conversation_id"])
            self.ledger.append("TASK_CANCELLED", task_id, {"message_id": message["message_id"]}, actor="jarvis_service")
            return self._response(message, "TASK_STATUS", f"Task {task_id} annullata.", task_id=task_id,
                                  status=updated["state"])
        if record["state"] in ("COMPLETED", "FAILED", "CANCELLED"):
            return self._response(message, "ERROR", f"La task in stato {record['state']} non è annullabile.",
                                  task_id=task_id, status=record["state"])
        self.conversation_store.update(message["conversation_id"], last_task_id=task_id,
                                       pending_action={"type": "CANCEL", "task_id": task_id})
        self.ledger.append("TASK_CANCEL_REQUESTED", task_id, {"message_id": message["message_id"]}, actor="jarvis_service")
        return self._response(message, "TASK_STATUS", f"Confermi l’annullamento di {task_id}?",
                              task_id=task_id, status="CONFIRMATION_REQUIRED",
                              actions=[{"type": "CONFIRM_CANCEL", "task_id": task_id},
                                       {"type": "KEEP_TASK", "task_id": task_id}])

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
        provider_execution = record.get("provider_execution") or {}
        if provider_execution.get("finalized") and provider_execution.get("verified"):
            output = provider_execution.get("output") or {}
            summary = output.get("summary") or f"Task {task_id} completata dal provider e verificata."
            return self._response(message, "TASK_STATUS", summary, task_id=task_id,
                status="FINALIZED", details={
                    "provider": provider_execution.get("provider"),
                    "premium_calls": provider_execution.get("premium_calls", 0),
                    "duration_seconds": provider_execution.get("duration_seconds"),
                    "provider_request_id": provider_execution.get("provider_request_id"),
                    "output": output, "source_refs": output.get("source_refs", [])},
                confidence=(record.get("result_packet") or {}).get("confidence", "UNKNOWN"),
                generated_by=f"provider_connector:{provider_execution.get('provider', 'UNKNOWN')}")
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
            self.ledger.append("APPROVAL_REJECTED", task_id, {"message_id": message["message_id"]}, actor="jarvis_gateway")
            # NEXUS Dynamic Specialist Review: only meaningful when a local
            # worker actually exists to rework the patch (conversational_programming)
            # and the connector is wired - every other rejected task keeps the
            # original, already-tested FAILED dead-end unchanged.
            if record.get("action") == "conversational_programming" and self.provider_connector is not None:
                self.provider_connector.request_review(task_id, reject_reason="human rejected the proposed patch")
            else:
                self.queue.transition(task_id, "FAILED")
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
