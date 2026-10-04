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


_EXPLICIT_RESUME_TASK = re.compile(
    r"\b(riprendi|riattiva|resume)\b.*\bTASK_[A-Z0-9_]+\b|"
    r"\bTASK_[A-Z0-9_]+\b.*\b(riprendi|riattiva|resume)\b", re.I)

# NATURAL_CONVERSATION_V3 -----------------------------------------------------
# Explicit mutation verbs - including common Italian clitic-pronoun
# contractions ("approvala", "rifiutala", "riprendila", "annullala") that the
# older plain \bapprova\b-style regexes never matched (no word boundary
# between the verb stem and "la"/"lo").
_TASK_ID_RE = re.compile(r"\bTASK_[A-Z0-9_]+\b", re.I)
_RESUME_VERB_RE = re.compile(r"\b(riprendi(?:la|lo)?|riattiva(?:la|lo)?|resume)\b", re.I)
_APPROVE_VERB_RE = re.compile(r"\bapprov(?:o|a(?:la|lo|le)?|iamo)\b|\bapprove\b", re.I)
_REJECT_VERB_RE = re.compile(r"\brifiut(?:o|a(?:la|lo|le)?|iamo)\b|\breject\b", re.I)
_CANCEL_VERB_RE = re.compile(r"\b(annulla(?:la|lo)?|cancella(?:la|lo)?|cancel)\b", re.I)
# A bare reference word with no explicit TASK_<id> - resolved ONLY against
# this conversation's own last_task_id (see _resolve_contextual_task_id),
# never guessed from a repo-wide "most recent task" heuristic.
_REFERENCE_WORD_RE = re.compile(
    r"\b(quella|quello|questa|questo|prima)\b", re.I)
_TECHNICAL_VIEW_RE = re.compile(r"\b(pi[uù]\s+tecnic\w*|tecnic\w*)\b", re.I)
_NOTIFICATION_PREF_RE = re.compile(
    r"\b(non disturbarmi|fammi sapere solo|dimmi solo|avvisami|aggiornami)\b", re.I)
_PROVIDER_PREF_RE = re.compile(
    r"\b(falla controllare da|fammi fare (?:la )?review da|usa (?:groq|codex|claude|locale)|"
    r"non usare premium|niente premium|solo locale|premium solo se serve)\b", re.I)

# JARVIS_EXECUTIVE_CONVERSATION_V4 --------------------------------------------
# "l'ultima" (singular) / "approvale" (plural clitic) are deliberately NOT in
# _REFERENCE_WORD_RE above - "approva l'ultima" must resolve against the set
# of tasks actually WAITING_APPROVAL (_resolve_waiting_approval_reference),
# never against last_task_id (which could be in ANY state) the way "quella"
# correctly still does.
_LAST_PENDING_APPROVAL_RE = re.compile(
    r"\b(l[’']ultima|ultima task|quelle da approvare|quali devo approvare|approvale)\b", re.I)
_GOAL_TO_TASK_RE = re.compile(
    r"\b(iniziamo una (?:nuova )?task|inizia una (?:nuova )?task|possiamo (?:iniziare|lavorare su)|"
    r"voglio ottenere|trova(?:re)? un modo per|il mio obiettivo [eè])\b", re.I)
_EXECUTIVE_INTENT_RE = re.compile(
    r"\b(cosa facciamo (?:ora|adesso)|qual[eè] la prossima cosa|continua tu|cosa consigli|"
    r"cosa manca|cosa [eè] pi[uù] importante|risolvi tu)\b", re.I)
_CONFIRM_RE = re.compile(r"\b(s[iì]|conferma|procedi|vai|ok|va bene)\b", re.I)
_DECLINE_RE = re.compile(r"\b(no|annulla|lascia stare|non (?:ora|adesso))\b", re.I)


def _extract_task_id(text):
    match = _TASK_ID_RE.search(text or "")
    return match.group(0).upper() if match else None


def classify(text: str, metadata: dict | None = None) -> str:
    value = (text or "").strip().lower()
    metadata = metadata or {}
    action = str(metadata.get("approval_action") or "").upper()
    if metadata.get("confirm_cancel"):
        return "COMMAND"
    # SAFE_ORPHANED_TASK_RESUME_V1: an explicit "riprendi/riattiva/resume
    # TASK_<id>" must win absolute precedence over generic conversational
    # task creation below - is_programming_request() already claims the bare
    # word "riprendi" for a DIFFERENT, pre-existing meaning (continue/follow
    # up on the last referenced programming task, via _REFERENCE_WORDS in
    # programming.py). Only the explicit-task-id form is intercepted here;
    # a bare "riprendi" with no task_id still flows through exactly as
    # before (TASK_REQUEST -> conversational follow-up), zero regression.
    if _EXPLICIT_RESUME_TASK.search(text or ""):
        return "COMMAND"
    # JARVIS_EXECUTIVE_CONVERSATION_V4: "l'ultima"/"approvale"/"quali devo
    # approvare" must win over everything below, including the generic
    # mutation-verb block (which would otherwise treat a bare "approva" here
    # as matching nothing, or QUERY's "quali" catch-all would misfire on a
    # pure listing question) - checked before any explicit-id requirement
    # since this phrase is itself the full reference, no TASK_<id> involved.
    if _LAST_PENDING_APPROVAL_RE.search(value):
        return "EXECUTIVE_APPROVAL_REFERENCE"
    # NATURAL_CONVERSATION_V3: an explicit mutation verb paired with EITHER
    # an explicit TASK_<id> OR a resolvable contextual reference word must
    # win over every generic/task-creation branch below (is_programming_request()
    # already claims several of these bare verbs for a different, pre-existing
    # meaning). A bare verb alone (no id, no reference word) is left
    # completely untouched here - it falls through to the exact same
    # branches as before this change, zero regression.
    def _ends_with_clitic(match):
        # "approvala"/"rifiutala"/"annullala"/"riprendila" - the attached
        # "la"/"lo" IS the contextual reference, no separate word needed.
        return bool(match) and match.group(0).lower().endswith(("la", "lo"))

    explicit_task_id = _extract_task_id(text)
    has_reference = bool(_REFERENCE_WORD_RE.search(value))
    mutation_ready = bool(explicit_task_id or has_reference)
    approve_match = _APPROVE_VERB_RE.search(value)
    reject_match = _REJECT_VERB_RE.search(value)
    cancel_match = _CANCEL_VERB_RE.search(value)
    resume_match = _RESUME_VERB_RE.search(value)
    if approve_match and (mutation_ready or _ends_with_clitic(approve_match)):
        return "APPROVAL"
    if reject_match and (mutation_ready or _ends_with_clitic(reject_match)):
        return "REJECTION"
    if cancel_match and (mutation_ready or _ends_with_clitic(cancel_match)):
        return "COMMAND"
    if resume_match and (has_reference or _ends_with_clitic(resume_match)):
        return "COMMAND"
    if _TECHNICAL_VIEW_RE.search(value) and not is_programming_request(value):
        return "COMMAND"
    if _NOTIFICATION_PREF_RE.search(value):
        return "NOTIFICATION_PREFERENCE"
    if _PROVIDER_PREF_RE.search(value):
        return "PROVIDER_PREFERENCE"
    # JARVIS_EXECUTIVE_CONVERSATION_V4: "continua tu" would otherwise match
    # the generic COMMAND regex's bare \bcontinua\b below (-> follow_up());
    # "cosa facciamo adesso?"/"cosa manca?" would otherwise fall into QUERY's
    # generic "cosa/quali/?" catch-all much further down. Both need to be
    # recognized as a request for a concrete executive suggestion instead.
    if _GOAL_TO_TASK_RE.search(value):
        return "GOAL_TO_TASK"
    if _EXECUTIVE_INTENT_RE.search(value):
        return "EXECUTIVE_INTENT"
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
    if re.search(r"\b(a che punto|stato|status|come procede)\b", value) or re.search(
            r"\bperch[eé]\b.{0,20}\b(bloccat\w*|fallit\w*|non va|non funziona)\b", value):
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
        # NATURAL_CONVERSATION_V3: bounded conversational memory - opportunistic,
        # cheap cleanup rather than a background scheduler this module doesn't have.
        self.conversation_store.purge_stale()
        if message.get("input_type") != "TEXT":
            return self._response(message, "ERROR", "Input type not supported in V1.",
                                  status="UNAVAILABLE", confidence="HIGH")
        # JARVIS_EXECUTIVE_CONVERSATION_V4 (A): a pending TASK_DRAFT
        # confirmation is resolved BEFORE normal classify()-based routing -
        # a bare "sì"/"no" reply has no intent signal of its own and would
        # otherwise fall through to UNKNOWN. Anything else leaves the draft
        # in place and falls through to normal routing unchanged (never
        # traps the user in a forced yes/no loop).
        draft_reply = self._resolve_pending_task_draft(message)
        if draft_reply is not None:
            return draft_reply
        request_class = message.get("request_class")
        if request_class in (None, "UNKNOWN"):
            request_class = classify(message.get("text", ""), message.get("metadata"))
        message["request_class"] = request_class
        self.ledger.append("USER_MESSAGE_RECEIVED", None,
                           {"message_id": message["message_id"], "channel": message["channel"],
                            "request_class": request_class}, actor="jarvis_gateway")
        if message.get("metadata", {}).get("ui_action"):
            return self.interactive_action(message)
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
        if request_class == "NOTIFICATION_PREFERENCE":
            return self.set_notification_preference(message)
        if request_class == "PROVIDER_PREFERENCE":
            return self.set_provider_preference(message)
        if request_class == "EXECUTIVE_APPROVAL_REFERENCE":
            return self.executive_approval_reference(message)
        if request_class == "GOAL_TO_TASK":
            return self.propose_task_from_goal(message)
        if request_class == "EXECUTIVE_INTENT":
            return self.executive_intent(message)
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
        # NATURAL_CONVERSATION_V3: bounded per-conversation preferences
        # (set_provider_preference/set_notification_preference) ride along
        # as ordinary metadata/policy_hints on the task this creates - never
        # a bypass of _policy()/select_reviewer_candidates(), which are
        # completely untouched.
        prefs = self.conversation_store.get(message["conversation_id"])
        programming_plan = None
        if is_programming_request(text):
            allowed_paths = list(attrs.get("files_allowed") or extract_repo_paths(text))
            programming_plan = build_plan(
                text, last_task_id=prefs.get("last_task_id"),
                allowed_paths=allowed_paths)
        required = ["summaries"]
        if programming_plan:
            required = ["small_python_functions", "unit_test_writing"]
        if attrs.get("second_opinion"): required.append("review")
        task_id = new_task_id()
        work_type = "complex_code" if programming_plan else classify_work_type(text, attrs)
        premium_allowed = work_type in ("scientific_research", "complex_code")
        if prefs.get("premium_allowed") is False:
            premium_allowed = False
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
        policy_hints = {}
        if prefs.get("preferred_provider"):
            policy_hints["preferred_provider"] = prefs["preferred_provider"]
        if prefs.get("notification_mode"):
            policy_hints["notification_mode"] = prefs["notification_mode"]
        if policy_hints:
            action_params["policy_hints"] = policy_hints
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
        details = self._task_details(record, technical=False)
        details.update({"approval_required": manifest["approval_required"],
                        "work_type": work_type, "execution_plan": programming_plan,
                        "review_required": get_matrix_entry(work_type)["review_required"],
                        "source_refs": ["TASK_MANIFEST_V1", "orchestrator queue"]})
        return self._response(message, "TASK_ACK", f"Task {task_id} created.", task_id=task_id,
                              status=record["state"], details=details)

    def _user_scoped_tasks(self, message, *, states=None):
        """Every task this conversation/user actually owns - same ownership
        test _latest_compatible_task() always used, factored out so
        JARVIS_EXECUTIVE_CONVERSATION_V4's new resolvers reuse it instead of
        re-implementing the filter. Newest first; optionally narrowed to a
        set of states (e.g. only WAITING_APPROVAL)."""
        conversation_id = message["conversation_id"]
        user_id = str(message["user_id"])
        items = []
        for record in self.queue.list_all():
            params = record.get("action_params") or {}
            created_by = (record.get("manifest") or {}).get("created_by")
            if params.get("conversation_id") == conversation_id or created_by == f"jarvis:{user_id}":
                if states is None or record.get("state") in states:
                    items.append(record)
        items.sort(key=lambda item: item.get("updated_at") or item.get("created_at") or "", reverse=True)
        return items

    def _latest_compatible_task(self, message):
        items = self._user_scoped_tasks(message)
        return items[0]["task_id"] if items else None

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

    def _resolve_contextual_task_id(self, message):
        """NATURAL_CONVERSATION_V3: strict, fail-closed resolution used ONLY
        by mutation intents (approve/reject/resume via a bare reference word
        or clitic contraction - 'approva quella', 'rifiutala'). An explicit
        TASK_<id> in text or metadata always wins outright. Otherwise this
        resolves against THIS conversation's own last_task_id and nothing
        else - deliberately never falling back to _latest_compatible_task()'s
        looser cross-task heuristic (that stays reserved for the older,
        non-mutating commands - cancel/follow_up/resume_orphaned via
        _resolve_task_id - so they keep behaving exactly as before).
        Returns (task_id_or_None, ambiguous)."""
        explicit = message.get("metadata", {}).get("task_id") or _extract_task_id(message.get("text") or "")
        if explicit:
            return explicit, False
        context = self.conversation_store.get(message["conversation_id"])
        last_task_id = context.get("last_task_id")
        if not last_task_id:
            return None, True
        return last_task_id, False

    def _resume_or_continue(self, message):
        """riprendi/riattiva/resume: an explicit TASK_<id> always goes
        straight to resume_orphaned_task() (existing, already-shipped
        behaviour, unchanged). A bare reference ('riprendi quella' /
        'riprendila', no explicit id) tries that SAME orphan-resume first
        and only falls back to the older conversational-programming
        continuation (create_task(), itself unchanged) when the resolved
        task is not actually BLOCKED/ORPHANED_RUNNING_AFTER_RESTART - one
        observable fact decides it, never a guess."""
        explicit = message.get("metadata", {}).get("task_id") or _extract_task_id(message.get("text") or "")
        if explicit:
            message.setdefault("metadata", {})["task_id"] = explicit
            return self.resume_orphaned(message)
        task_id, ambiguous = self._resolve_contextual_task_id(message)
        if ambiguous:
            return self._response(message, "CLARIFICATION_REQUIRED",
                "Non ho un riferimento chiaro a quale task riprendere - puoi indicarmi il task_id?",
                status="AMBIGUOUS")
        if not task_id:
            return self.create_task(message)
        try:
            record = self.queue.get(task_id)
        except KeyError:
            return self.create_task(message)
        recovery = record.get("recovery") or {}
        if record["state"] == "BLOCKED" and recovery.get("classification") == "ORPHANED_RUNNING_AFTER_RESTART":
            self.ledger.append("CONVERSATION_REFERENCE_RESOLVED", task_id,
                {"message_id": message["message_id"], "resolved_as": "RESUME"}, actor="jarvis_service")
            message.setdefault("metadata", {})["task_id"] = task_id
            return self.resume_orphaned(message)
        return self.create_task(message)

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
            latest_failure = next((event.get("payload") or {} for event in reversed(events)
                                   if (event.get("payload") or {}).get("failure_class")), {})
            verifier = (record.get("result_packet") or {}).get("verifier") or {}
            details.update({
                "action": record.get("action"),
                "dispatch_last_error": record.get("dispatch_last_error"), "recovery": record.get("recovery"),
                "escalation": {key: escalation.get(key) for key in ("target", "classification")
                               if escalation.get(key) is not None},
                "result_decision": (record.get("result_packet") or {}).get("decision"),
                "verifier": {"passed": verifier.get("passed"),
                             "failure_class": latest_failure.get("failure_class"),
                             "errors": verifier.get("errors") or []},
                "lifecycle": [{"event_type": event.get("event_type"), "timestamp": event.get("timestamp"),
                               "payload": {key: value for key, value in (event.get("payload") or {}).items()
                                           if key in safe_event_keys}} for event in events],
            })
        return details

    def _state_matches(self, record, message):
        expected = message.get("metadata", {}).get("expected_state")
        return not expected or record.get("state") == expected

    def interactive_action(self, message):
        """Execute Telegram UI intents through canonical service methods only."""
        meta = message.get("metadata", {})
        action = meta.get("ui_action")
        if action in ("TASK_STATUS", "TECHNICAL_DETAILS", "DIAGNOSTICS"):
            if action != "TASK_STATUS":
                meta["technical_details"] = True
            return self.follow_up(message)
        if action == "LIFECYCLE":
            return self.task_lifecycle(message)
        if action in ("APPROVE", "REJECT"):
            meta["approval_action"] = action
            return self.approval(message)
        if action == "RESUME":
            return self.resume_orphaned(message)
        if action in ("AGENT_DETAILS", "AGENT_CAPABILITIES", "PROVIDER_STATUS"):
            return self.agent_view(message)
        if action == "QUICK_ACTION":
            command = {"STATUS": "/status", "TASKS": "/tasks", "AGENTS": "/agents",
                       "HELP": "/help"}.get(meta.get("quick_action"))
            if command:
                message["text"] = command
                return self.command(message)
        return self._response(message, "ERROR", "Azione interattiva non valida.",
                              status="UNKNOWN", confidence="HIGH")

    def task_lifecycle(self, message):
        task_id = self._resolve_task_id(message)
        if not task_id:
            return self._response(message, "ERROR", "Task context unavailable.", status="UNKNOWN")
        try:
            record = self.queue.get(task_id)
        except KeyError:
            return self._response(message, "ERROR", "Task not found.", task_id=task_id, status="UNKNOWN")
        page = max(0, int(message.get("metadata", {}).get("lifecycle_page") or 0))
        page_size = 6
        events = self._task_details(record, technical=True).get("lifecycle") or []
        events = list(reversed(events))
        start = page * page_size
        details = self._task_details(record, technical=False)
        details.update({"view": "TASK_LIFECYCLE", "lifecycle": events[start:start + page_size],
                        "lifecycle_page": page, "lifecycle_has_more": start + page_size < len(events),
                        "lifecycle_total": len(events)})
        return self._response(message, "TASK_STATUS", f"Lifecycle di {task_id}.", task_id=task_id,
                              status=record["state"], details=details)

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

    def _executive_next_action(self, record):
        """JARVIS_EXECUTIVE_CONVERSATION_V4: a concrete suggested next step
        (not just the raw state), plus matching quick actions - reused by
        follow_up(), approval()'s wrong-state response and
        executive_intent(). Never performs anything itself, only proposes -
        the same 'parser/narrator never mutates' boundary as the rest of
        this module. Technical failure_class/classification strings stay
        available separately via technical_details, never lost."""
        task_id = record["task_id"]
        state = record.get("state")
        escalation = record.get("escalation") or {}
        recovery = record.get("recovery") or {}
        if state == "WAITING_REVIEW_PROVIDER":
            states = escalation.get("candidate_states") or {}
            unavailable = ", ".join(f"{p} {s}" for p, s in states.items()) or "nessun reviewer configurato"
            return (f"Nessun reviewer è disponibile ora ({unavailable}). Posso aspettare che torni "
                   "disponibile oppure mostrarti il motivo esatto del fallimento locale.",
                   [{"type": "DETAILS", "task_id": task_id}])
        if state == "ESCALATION_REQUIRED" and escalation.get("target") == "MANUAL_REVIEW":
            return ("Serve una revisione manuale: il budget di tentativi automatici è esaurito o "
                   "nessun provider può procedere da solo. Posso mostrarti i dettagli tecnici del "
                   "fallimento.", [{"type": "DETAILS", "task_id": task_id}])
        if state == "ESCALATION_REQUIRED":
            return ("È in attesa che un provider risponda; nessuna azione premium parte senza la "
                   "policy esistente.", [{"type": "DETAILS", "task_id": task_id}])
        if state == "BLOCKED" and recovery.get("classification") == "ORPHANED_RUNNING_AFTER_RESTART":
            return ("Si è bloccata per un riavvio del sistema durante l'esecuzione, ma è "
                   "recuperabile in sicurezza. Vuoi che la riprenda?",
                   [{"type": "RESUME", "task_id": task_id}])
        if state == "BLOCKED":
            return ("È bloccata e serve una verifica manuale della causa prima di un eventuale "
                   "recupero.", [{"type": "DETAILS", "task_id": task_id}])
        if state == "WAITING_APPROVAL":
            return ("Aspetta la tua approvazione.", [{"type": "APPROVE", "task_id": task_id},
                                                     {"type": "REJECT", "task_id": task_id}])
        if state == "QUEUED":
            return ("Il dispatcher la prenderà al prossimo turno disponibile.", [])
        if state == "RUNNING":
            return ("È in esecuzione in questo momento; lo stop forzato non è sicuro.", [])
        if state == "COMPLETED":
            return ("È completata. Posso mostrarti il risultato.", [{"type": "DETAILS", "task_id": task_id}])
        if state in ("FAILED", "CANCELLED"):
            return ("Puoi chiedermi di crearne una nuova con lo stesso obiettivo, se serve.", [])
        return (self._next_step(record), [])

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
        next_text, next_actions = self._executive_next_action(record)
        summary = f"La task {task_id} {_STATE_MESSAGES.get(record['state'], 'ha stato ' + record['state'])}. {next_text}"
        actions = [{"type": "DETAILS", "task_id": task_id}, {"type": "CANCEL", "task_id": task_id}]
        for item in next_actions:
            if item not in actions:
                actions.append(item)
        self.conversation_store.update(message["conversation_id"], last_task_id=task_id,
                                       last_view="TECHNICAL" if technical else "SUMMARY",
                                       user_id=str(message["user_id"]))
        return self._response(message, "TASK_STATUS", summary, task_id=task_id,
                              status=record["state"], details=self._task_details(record, technical=technical),
                              actions=actions)

    def command(self, message):
        text = (message.get("text") or "").strip()
        value = text.lower()
        if value in ("/start", "/help") or re.search(r"\b(help|aiuto)\b", value):
            return self._response(message, "ANSWER",
                "Sono Jarvis. Posso creare task, mostrarne stato e dettagli, annullare task non in esecuzione, "
                "gestire approval e mostrare stato NEXUS, agenti e approval. Comandi: /status /tasks /approvals /agents.",
                details={"commands": ["/start", "/help", "/status", "/tasks", "/approvals", "/agents"]})
        if value == "/agents" or re.search(r"\b(agents|agenti)\b", value):
            items = self.agents(detailed=True)
            return self._response(message, "ANSWER", f"Agenti registrati: {len(items)}.",
                                  details={"view": "AGENT_LIST", "items": items,
                                           "source_refs": ["agent registry"]})
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
        if re.search(r"\b(dettagli|details|diagnostic)\b", value) or (
                _TECHNICAL_VIEW_RE.search(value) and not is_programming_request(value)):
            if re.search(r"\b(tecnic|technical|diagnostic)\w*\b", value):
                message.setdefault("metadata", {})["technical_details"] = True
            return self.follow_up(message)
        if re.search(r"\b(continua|continue)\b", value):
            return self.follow_up(message)
        if _RESUME_VERB_RE.search(value):
            return self._resume_or_continue(message)
        if message.get("metadata", {}).get("confirm_cancel") or _CANCEL_VERB_RE.search(value) or re.search(
                r"\bannullamento\b", value):
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

    def resume_orphaned(self, message):
        """Telegram front-end for SAFE_ORPHANED_TASK_RESUME_V1 - calls the
        exact same Orchestrator.resume_orphaned_task() the HTTP endpoint
        uses, no duplicated precondition logic here."""
        task_id = self._resolve_task_id(message)
        if not task_id:
            return self._response(message, "ERROR", "Non trovo una task da riprendere.",
                                  status="UNKNOWN")
        try:
            current = self.queue.get(task_id)
            if not self._state_matches(current, message):
                return self._response(message, "ERROR", "La card non è più valida: aggiorna lo stato.",
                                      task_id=task_id, status=current["state"])
            record = self.orchestrator.resume_orphaned_task(
                task_id, requested_by=f"jarvis:{message['user_id']}")
        except KeyError:
            return self._response(message, "ERROR", "Task non trovata.", task_id=task_id,
                                  status="UNKNOWN")
        except AssertionError as exc:
            return self._response(message, "ERROR", f"Non posso riprendere {task_id}: {exc}",
                                  task_id=task_id, status="REFUSED")
        self.conversation_store.update(message["conversation_id"], last_task_id=task_id,
                                       last_action="RESUME", user_id=str(message["user_id"]))
        return self._response(message, "TASK_STATUS",
                              f"Task {task_id} ripresa: torna in coda per il dispatcher normale.",
                              task_id=task_id, status=record["state"],
                              details=self._task_details(record, technical=True))

    def set_provider_preference(self, message):
        """NATURAL_CONVERSATION_V3: captures a provider/premium preference as
        a bounded, per-conversation hint - never a direct provider call and
        never a bypass of ProviderConnectorV1's existing availability/policy
        gate. 'non usare premium' sets manifest.premium_allowed=False on the
        NEXT task this conversation creates (the already-wired _policy()
        check in provider_connector.py, untouched). A named provider
        ('usa groq', 'falla controllare da codex') is attached as
        action_params.policy_hints.preferred_provider for visibility/audit -
        select_reviewer_candidates()'s capability>availability>cost>preference
        ordering is deliberately NOT modified by this task (see residual
        risks); the hint is stored, never enforced as a bypass."""
        text = message.get("text") or ""
        value = text.lower()
        no_premium = bool(re.search(
            r"\b(non usare premium|niente premium|solo locale|usa locale)\b", value))
        provider_match = re.search(r"\b(groq|codex|claude)\b", value, re.I)
        updates = {}
        if no_premium:
            updates["premium_allowed"] = False
        if provider_match:
            updates["preferred_provider"] = provider_match.group(1).upper()
        if not updates:
            return self._response(message, "ANSWER",
                "Non ho capito quale preferenza di provider impostare.", status="PARTIAL")
        self.conversation_store.update(message["conversation_id"], user_id=str(message["user_id"]),
                                       **updates)
        self.ledger.append("CONVERSATION_PREFERENCE_SET", None,
            {"message_id": message["message_id"], **updates}, actor="jarvis_service")
        parts = []
        if "premium_allowed" in updates: parts.append("nessun provider premium")
        if "preferred_provider" in updates: parts.append(f"reviewer preferito: {updates['preferred_provider']}")
        return self._response(message, "PREFERENCE_SET", "Impostato: " + ", ".join(parts),
                              details={"preferences": updates})

    def set_notification_preference(self, message):
        """NATURAL_CONVERSATION_V3: a per-conversation notification_mode,
        consulted by JarvisService.should_notify() - never logic baked into
        telegram_adapter.py's formatter (TELEGRAM_INTERACTIVE_UX_V1 owns
        that surface)."""
        text = message.get("text") or ""
        value = text.lower()
        if re.search(r"\bnon disturbarmi\b", value):
            mode = "SILENT"
        elif re.search(r"\b(fammi sapere solo se si blocca|avvisami se (si )?blocca)\b", value):
            mode = "BLOCKED_ONLY"
        elif re.search(r"\b(dimmi solo quando finisce|aggiornami (solo )?quando finisce)\b", value):
            mode = "ON_COMPLETE"
        elif re.search(r"\bavvisami se serve approvazione\b", value):
            mode = "APPROVAL_ONLY"
        else:
            return self._response(message, "ANSWER",
                "Non ho capito quale preferenza di notifica impostare.", status="PARTIAL")
        self.conversation_store.update(message["conversation_id"], notification_mode=mode,
                                       user_id=str(message["user_id"]))
        self.ledger.append("CONVERSATION_PREFERENCE_SET", None,
            {"message_id": message["message_id"], "notification_mode": mode}, actor="jarvis_service")
        return self._response(message, "PREFERENCE_SET", f"Impostata preferenza di notifica: {mode}.",
                              details={"notification_mode": mode})

    _NOTIFY_STATUS_RULES = {
        "SILENT": frozenset(),
        "BLOCKED_ONLY": frozenset({"BLOCKED", "MANUAL_REVIEW", "WAITING_REVIEW_PROVIDER"}),
        "ON_COMPLETE": frozenset({"WAITING_APPROVAL", "COMPLETED", "FINALIZED"}),
        "APPROVAL_ONLY": frozenset({"WAITING_APPROVAL"}),
    }

    def should_notify(self, task_id, status):
        """Per-task (falling back to the creating conversation's own
        preference) gate for a proactive push - the filtering decision lives
        here, in the service layer, not in telegram_adapter.py. Fails open
        (notify) on any lookup error or when no preference was ever set -
        silence must be an explicit choice, never an accidental default."""
        try:
            record = self.queue.get(task_id)
        except KeyError:
            return True
        hints = (record.get("action_params") or {}).get("policy_hints") or {}
        mode = hints.get("notification_mode")
        if not mode:
            conversation_id = (record.get("action_params") or {}).get("conversation_id")
            if conversation_id:
                mode = self.conversation_store.get(conversation_id).get("notification_mode")
        if not mode or mode == "ALL":
            return True
        allowed = self._NOTIFY_STATUS_RULES.get(mode)
        if allowed is None:
            return True
        return status in allowed

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
        meta = message.get("metadata", {})
        text = message.get("text") or ""
        approval_action = str(meta.get("approval_action") or "").upper()
        if approval_action in ("APPROVE", "APPROVAL", "APPROVA"):
            action = "APPROVE"
        elif approval_action in ("REJECT", "RIFIUTA"):
            action = "REJECT"
        elif _APPROVE_VERB_RE.search(text):
            action = "APPROVE"
        elif _REJECT_VERB_RE.search(text):
            action = "REJECT"
        else:
            action = ""
        task_id = meta.get("task_id") or _extract_task_id(text)
        ambiguous = False
        if not task_id:
            # NATURAL_CONVERSATION_V3: a free-text "approva quella"/"rifiutala"
            # with no explicit id resolves strictly against this
            # conversation's own last_task_id - fails closed (no mutation,
            # ask for clarification) rather than ever guessing.
            task_id, ambiguous = self._resolve_contextual_task_id(message)
        if ambiguous:
            self.ledger.append("CONVERSATION_CLARIFICATION_REQUESTED", None,
                {"message_id": message["message_id"], "intent": action or "APPROVAL"}, actor="jarvis_service")
            return self._response(message, "CLARIFICATION_REQUIRED",
                "Non ho un riferimento chiaro a quale task - puoi indicarmi il task_id?",
                status="AMBIGUOUS")
        if not task_id:
            return self._response(message, "ERROR", "Approval requires task_id.", status="UNKNOWN")
        try: record = self.queue.get(task_id)
        except KeyError: return self._response(message, "ERROR", "Task not found.", task_id=task_id, status="UNKNOWN")
        if not self._state_matches(record, message):
            return self._response(message, "ERROR", "La card non è più valida: aggiorna lo stato.",
                                  task_id=task_id, status=record["state"])
        if record["state"] != "WAITING_APPROVAL":
            # JARVIS_EXECUTIVE_CONVERSATION_V4 (response style): natural
            # phrasing instead of a raw state string, plus what to do next -
            # the technical state/failure_class remain available unchanged
            # via status= and technical_details, never lost, just not the
            # ONLY thing said.
            pending = self._user_scoped_tasks(message, states={"WAITING_APPROVAL"})
            next_text, _ = self._executive_next_action(record)
            if pending:
                others = ", ".join(p["task_id"] for p in pending[:5])
                guidance = f" Ho invece {len(pending)} task in attesa della tua approvazione: {others}."
            else:
                guidance = " Al momento non ci sono altre task in attesa della tua approvazione."
            state_text = _STATE_MESSAGES.get(record["state"], "ha stato " + record["state"])
            return self._response(message, "ERROR",
                f"Quella task non è in attesa di approvazione: {state_text}. {next_text}{guidance}",
                task_id=task_id, status=record["state"],
                details={"pending_approvals": [p["task_id"] for p in pending]})
        if not (meta.get("task_id")):
            self.ledger.append("CONVERSATION_REFERENCE_RESOLVED", task_id,
                {"message_id": message["message_id"], "resolved_as": action or "APPROVAL"}, actor="jarvis_service")
        if action == "APPROVE":
            self.queue.transition(task_id, "QUEUED")
            self.ledger.append("APPROVAL_GRANTED", task_id, {"message_id": message["message_id"]}, actor="jarvis_gateway")
        elif action == "REJECT":
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
        self.conversation_store.update(message["conversation_id"], last_task_id=task_id,
                                       last_action=action, user_id=str(message["user_id"]))
        return self._response(message, "APPROVAL", f"{task_id}: {updated['state']}", task_id=task_id,
                              status=updated["state"])

    def executive_approval_reference(self, message):
        """JARVIS_EXECUTIVE_CONVERSATION_V4 (D): 'approva/rifiuta l'ultima',
        'quali devo approvare', 'approvale?' - resolved against the set of
        tasks actually WAITING_APPROVAL for this user, never last_task_id
        (which could be in any state at all - that was the exact bug this
        closes: 'approvo l'ultima task' approving/rejecting whatever was
        last touched, not whatever is actually pending). Zero matches ->
        nothing to do, said plainly. Exactly one -> delegates to the
        existing approval() unchanged (metadata.task_id set explicitly, so
        no further resolution happens there). 2+ -> listed, NEVER guessed -
        same fail-closed principle as _resolve_contextual_task_id."""
        text = message.get("text") or ""
        action = "REJECT" if _REJECT_VERB_RE.search(text) else ("APPROVE" if _APPROVE_VERB_RE.search(text) else None)
        candidates = self._user_scoped_tasks(message, states={"WAITING_APPROVAL"})
        if action is None:
            # Pure listing - "quali devo approvare" / "quelle da approvare".
            if not candidates:
                return self._response(message, "ANSWER",
                    "Non ci sono task in attesa della tua approvazione al momento.")
            items = [{"task_id": c["task_id"], "state": c["state"],
                     "title": (c.get("manifest") or {}).get("title"), "updated_at": c.get("updated_at")}
                    for c in candidates]
            return self._response(message, "ANSWER",
                f"Ci sono {len(candidates)} task in attesa della tua approvazione.",
                details={"view": "TASK_LIST", "items": items, "source_refs": ["orchestrator queue"]})
        if not candidates:
            return self._response(message, "ERROR",
                "Non c'è nessuna task in attesa della tua approvazione in questo momento.",
                status="NONE_PENDING")
        if len(candidates) > 1:
            self.ledger.append("CONVERSATION_CLARIFICATION_REQUESTED", None,
                {"message_id": message["message_id"], "intent": action,
                 "candidates": [c["task_id"] for c in candidates]}, actor="jarvis_service")
            items = [{"task_id": c["task_id"], "state": c["state"],
                     "title": (c.get("manifest") or {}).get("title")} for c in candidates]
            return self._response(message, "CLARIFICATION_REQUIRED",
                f"Ci sono {len(candidates)} task in attesa di approvazione - quale intendi?",
                status="AMBIGUOUS", details={"view": "TASK_LIST", "items": items})
        meta = message.setdefault("metadata", {})
        meta["task_id"] = candidates[0]["task_id"]
        meta["approval_action"] = action
        return self.approval(message)

    def _resolve_pending_task_draft(self, message):
        """Returns a response if this message resolved a pending TASK_DRAFT
        confirmation (yes -> create_task() with the stored goal text, no ->
        discard), or None if there is no pending draft or the message is
        unrelated to it (in which case normal routing proceeds untouched)."""
        conversation_id = message["conversation_id"]
        pending = self.conversation_store.get(conversation_id).get("pending_confirmation") or {}
        if pending.get("type") != "TASK_DRAFT":
            return None
        text = (message.get("text") or "").strip()
        if _DECLINE_RE.search(text):
            self.conversation_store.update(conversation_id, pending_confirmation=None,
                                           user_id=str(message["user_id"]))
            return self._response(message, "ANSWER", "Va bene, non creo nessuna task.",
                                  status="COMPLETED")
        if _CONFIRM_RE.search(text):
            self.conversation_store.update(conversation_id, pending_confirmation=None,
                                           user_id=str(message["user_id"]))
            draft_message = dict(message)
            draft_message["text"] = pending["text"]
            return self.create_task(draft_message)
        return None

    def propose_task_from_goal(self, message):
        """JARVIS_EXECUTIVE_CONVERSATION_V4 (A): recognizes a goal statement
        ('iniziamo una task per…', 'voglio ottenere…', 'il mio obiettivo è…')
        and turns it into a task through the EXACT same create_task() every
        other task-creation path already uses - no second manifest-building
        path, no direct external/business action just because a goal was
        expressed. An imperative phrasing ('inizia/iniziamo una (nuova)
        task...') is itself the confirmation and creates directly; a more
        exploratory/question phrasing ('possiamo…', 'voglio ottenere…')
        is held as a one-field draft in conversation_store.pending_confirmation
        and only created once the user replies yes - never guessed."""
        text = message.get("text") or ""
        match = _GOAL_TO_TASK_RE.search(text.lower())
        trigger = match.group(1) if match else ""
        imperative = bool(re.match(r"inizi[ao]", trigger))
        remainder = (text[match.end():] if match else text).strip(" .,:;!?")
        if len(remainder) < 8:
            return self._response(message, "ANSWER",
                "Capisco che vuoi iniziare qualcosa di nuovo, ma mi serve un obiettivo più "
                "concreto - cosa vuoi ottenere esattamente?", status="PARTIAL")
        if imperative:
            return self.create_task(message)
        self.conversation_store.update(message["conversation_id"],
                                       pending_confirmation={"type": "TASK_DRAFT", "text": text},
                                       user_id=str(message["user_id"]))
        title = text.strip()[:120]
        return self._response(message, "ANSWER",
            f'Vuoi che apra una nuova task con questo obiettivo: "{title}"? Rispondi sì per procedere.',
            status="CONFIRMATION_REQUIRED",
            actions=[{"type": "CONFIRM_TASK_DRAFT"}, {"type": "DISCARD_TASK_DRAFT"}])

    def _executive_priorities(self, message):
        """Canonical-state-only priority ordering for executive_intent():
        WAITING_APPROVAL first (needs the user directly), then BLOCKED/
        ESCALATION_REQUIRED (needs attention), then the rest - reads ONLY
        this user's own tasks via _user_scoped_tasks, no cross-agent view.
        Deliberate extension point: Shared Cognitive State V1 (Codex) can
        later supply a richer, cross-workstream ordering here without any
        caller needing to change."""
        order = {"WAITING_APPROVAL": 0, "BLOCKED": 1, "ESCALATION_REQUIRED": 1,
                 "WAITING_REVIEW_PROVIDER": 2, "WAITING_PROVIDER": 3, "QUEUED": 4, "RUNNING": 4}
        items = self._user_scoped_tasks(message)
        open_items = [r for r in items if r.get("state") not in ("COMPLETED", "CANCELLED", "FAILED")]
        open_items.sort(key=lambda r: order.get(r.get("state"), 9))
        return [{"task_id": r["task_id"], "state": r["state"],
                "title": (r.get("manifest") or {}).get("title")} for r in open_items[:10]]

    def executive_intent(self, message):
        """JARVIS_EXECUTIVE_CONVERSATION_V4 (E): 'cosa facciamo adesso?',
        'continua tu', 'cosa consigli?', 'risolvi tu se puoi' - reads ONLY
        canonical state, proposes ONE concrete priority + quick actions.
        'risolvi tu' performs the SAME already-existing, already-safe
        mutation (resume_orphaned_task via resume_orphaned()) only when one
        clearly applies - never a new autonomous action, never a direct
        provider call, never trading."""
        text = (message.get("text") or "").lower()
        priorities = self._executive_priorities(message)
        if not priorities:
            return self._response(message, "ANSWER",
                "Non ho task aperte che richiedano attenzione in questo momento.", status="COMPLETED")
        top = priorities[0]
        task_id = top["task_id"]
        if re.search(r"\brisolvi tu\b", text):
            record = self.queue.get(task_id)
            recovery = record.get("recovery") or {}
            if record["state"] == "BLOCKED" and recovery.get("classification") == "ORPHANED_RUNNING_AFTER_RESTART":
                meta = message.setdefault("metadata", {}); meta["task_id"] = task_id
                return self.resume_orphaned(message)
            next_text, actions = self._executive_next_action(record)
            return self._response(message, "ANSWER",
                f"Non posso risolverla da solo in sicurezza: {next_text}", task_id=task_id,
                status=record["state"], actions=actions)
        record = self.queue.get(task_id)
        next_text, actions = self._executive_next_action(record)
        summary = f"La priorità più concreta ora è {task_id} ({top['title'] or 'senza titolo'}): {next_text}"
        if len(priorities) > 1:
            summary += f" Ci sono anche altre {len(priorities) - 1} task che aspettano."
        return self._response(message, "ANSWER", summary, task_id=task_id,
                              status=record["state"], actions=actions,
                              details={"view": "TASK_LIST", "items": priorities})

    def agents(self, detailed=False):
        agents = []
        for agent in load_registry().get("agents", []):
            state = agent.get("quota_state") or agent.get("availability") or "UNKNOWN"
            if agent.get("availability") != "ONLINE": state = "OFFLINE"
            item = {"agent_id": agent.get("agent_id"), "provider": agent.get("provider"),
                    "status": state, "availability": agent.get("availability"),
                    "quota_state": agent.get("quota_state")}
            if detailed:
                item.update({"role": agent.get("specialist_role"),
                             "capabilities": agent.get("capabilities") or [],
                             "model_or_runtime": agent.get("model_or_runtime"),
                             "integration_status": agent.get("integration_status")})
            agents.append(item)
        return agents

    def agent_view(self, message):
        meta = message.get("metadata", {})
        agent_id = meta.get("agent_id")
        agent = next((item for item in self.agents(detailed=True) if item.get("agent_id") == agent_id), None)
        if not agent:
            return self._response(message, "ERROR", "Agent not found.", status="UNKNOWN")
        view = {"AGENT_DETAILS": "AGENT_DETAIL", "AGENT_CAPABILITIES": "AGENT_CAPABILITIES",
                "PROVIDER_STATUS": "PROVIDER_STATUS"}.get(meta.get("ui_action"), "AGENT_DETAIL")
        return self._response(message, "ANSWER", f"{agent_id} · {agent.get('role') or 'ruolo non disponibile'}.",
                              details={"view": view, "agent": agent,
                                       "source_refs": ["agent registry"]})
