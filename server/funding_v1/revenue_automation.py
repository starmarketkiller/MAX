"""Provenance-first prospect acquisition and persistent Revenue Agent scheduler."""
from __future__ import annotations

import hashlib
import json
import os
import threading
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlparse

from jarvis_v1.ministral_task_compiler import decode_bounded_output


def _now():
    return datetime.now(timezone.utc).isoformat()


def _normalized_domain(value):
    if not value:
        return ""
    parsed = urlparse(value if "://" in value else "https://" + value)
    return parsed.netloc.casefold().removeprefix("www.").strip()


def prospect_dedup_key(record):
    identity = (_normalized_domain(record.get("website")) or
                str(record.get("email", "")).casefold().strip() or
                "|".join((str(record.get("display_name", "")).casefold().strip(),
                          str(record.get("location", "")).casefold().strip())))
    if not identity.strip("|"):
        raise ValueError("prospect requires website, email, or name/location identity")
    return "sha256:" + hashlib.sha256(identity.encode("utf-8")).hexdigest()


class ProspectAcquisition:
    """Ingest records from an authorized adapter; never browse autonomously."""

    def __init__(self, store):
        self.store = store

    def ingest(self, records, *, source, source_reference, confidence="VERIFIED"):
        accepted, duplicates, rejected = [], [], []
        before = {item["dedup_key"] for item in self.store.snapshot().get("prospects", [])}
        for index, raw in enumerate(records):
            try:
                evidence = raw.get("evidence")
                if not isinstance(evidence, list) or not evidence:
                    raise ValueError("prospect requires source evidence")
                key = prospect_dedup_key(raw)
                prospect_id = "PROSPECT_" + hashlib.sha256(
                    (source + "|" + key).encode("utf-8")).hexdigest()[:12].upper()
                record = {
                    "prospect_id": prospect_id, "dedup_key": key,
                    "display_name": raw.get("display_name") or "UNAVAILABLE",
                    "website": raw.get("website"), "email": raw.get("email"),
                    "location": raw.get("location"), "source": source,
                    "source_reference": source_reference, "evidence": evidence,
                    "observed_at": raw.get("observed_at") or _now(),
                    "provenance": {"source": source, "reference": source_reference,
                                   "confidence": confidence},
                }
                self.store.register_prospect(
                    record, idempotency_key=f"prospect:{source}:{source_reference}:{index}:{key}")
                (duplicates if key in before else accepted).append(prospect_id)
                before.add(key)
            except (AttributeError, TypeError, ValueError) as exc:
                rejected.append({"index": index, "reason": str(exc)})
        return {"accepted": accepted, "duplicates": duplicates, "rejected": rejected}


class RevenueScheduler:
    """Persistent trigger planner: creates tasks, never executes commercial actions."""

    def __init__(self, path, coordinator, store, notification_sink=None,
                 follow_up_after=timedelta(days=3), stale_after=timedelta(days=7)):
        self.path = Path(path)
        self.coordinator = coordinator
        self.store = store
        self.notification_sink = notification_sink
        self.follow_up_after = follow_up_after
        self.stale_after = stale_after
        self._lock = threading.RLock()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self._save({"schema_version": 1, "revision": 0, "scheduled_keys": {},
                        "last_tick_at": None})

    def _load(self):
        return json.loads(self.path.read_text(encoding="utf-8"))

    def _save(self, value):
        temp = self.path.with_name(f"{self.path.name}.{os.getpid()}.tmp")
        temp.write_text(json.dumps(value, indent=2), encoding="utf-8")
        os.replace(temp, self.path)

    def tick(self, *, reply_events=None, experiments=None, now=None):
        with self._lock:
            now_dt = now or datetime.now(timezone.utc)
            state = self._load()
            scheduled = []
            snapshot = self.store.snapshot()
            work = []
            for prospect in snapshot.get("prospects", []):
                work.append((f"prospect:{prospect['prospect_id']}", "PROSPECT_FACT_EXTRACTION",
                             {"prospect": prospect, "prospect_facts": prospect["evidence"]},
                             {"prospect_id": prospect["prospect_id"]}))
            for lead in snapshot.get("leads", []):
                if lead["status"] == "DISCOVERED":
                    work.append((f"qualify:{lead['lead_id']}", "LEAD_QUALIFICATION",
                                 {"lead": lead,
                                  "prospect_facts": [lead["display_name"], lead["source"]]},
                                 {"lead_id": lead["lead_id"]}))
                if lead["status"] == "CONTACTED" and lead.get("outreach_receipt"):
                    sent = datetime.fromisoformat(lead["outreach_receipt"]["recorded_at"])
                    due = sent + self.follow_up_after
                    if due <= now_dt:
                        work.append((f"followup:{lead['lead_id']}:{due.isoformat()}",
                                     "FOLLOW_UP_DRAFT",
                                     {"lead": lead, "prospect_facts": [lead["display_name"],
                                       lead["outreach_receipt"]["reference"]]},
                                     {"lead_id": lead["lead_id"]}))
                if lead["status"] in {"QUALIFIED", "CONTACT_READY"}:
                    updated = datetime.fromisoformat(lead["updated_at"])
                    if updated + self.stale_after <= now_dt:
                        work.append((f"stale:{lead['lead_id']}:{lead['updated_at']}",
                                     "PIPELINE_SUMMARY",
                                     {"lead": lead, "stale_reason": "NO_PROGRESS_WITHIN_POLICY"},
                                     {"lead_id": lead["lead_id"]}))
            leads = {item["lead_id"]: item for item in snapshot.get("leads", [])}
            for reply in reply_events or []:
                lead = leads.get(reply.get("lead_id"))
                if lead and lead.get("status") == "CONTACTED":
                    work.append((f"reply:{reply['message_id']}", "INBOUND_CLASSIFICATION",
                                 {"lead": lead, "inbound_message": reply["text"],
                                  "prospect_facts": [reply["text"]]},
                                 {"lead_id": lead["lead_id"],
                                  "message_id": reply["message_id"]}))
            for experiment in experiments or []:
                if experiment.get("review_due"):
                    work.append((f"experiment:{experiment['experiment_id']}:{experiment['review_due']}",
                                 "REVENUE_EXPERIMENT_SUMMARY", {"experiment": experiment},
                                 {"experiment_id": experiment["experiment_id"]}))
            for key, task_type, context, references in work:
                if key in state["scheduled_keys"]:
                    continue
                task_id = self.coordinator.submit(
                    task_type, context=context, references=references,
                    created_by="revenue_scheduler")
                state["scheduled_keys"][key] = {"task_id": task_id, "scheduled_at": _now()}
                scheduled.append({"key": key, "task_id": task_id, "task_type": task_type})
            state["revision"] += 1
            state["last_tick_at"] = _now()
            self._save(state)
            if scheduled and self.notification_sink:
                self.notification_sink({"type": "REVENUE_TASKS_SCHEDULED", "items": scheduled,
                                        "action_required": False})
            return {"scheduled": scheduled, "revision": state["revision"]}


class RevenueResultDelivery:
    """Idempotently delivers verified revenue task outcomes to a Jarvis sink."""

    TERMINAL_OR_ATTENTION = ("COMPLETED", "WAITING_APPROVAL", "ESCALATION_REQUIRED", "BLOCKED")

    def __init__(self, path, queue, notification_sink):
        self.path = Path(path)
        self.queue = queue
        self.notification_sink = notification_sink
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self.path.write_text(json.dumps({"delivered": []}), encoding="utf-8")

    def poll(self):
        state = json.loads(self.path.read_text(encoding="utf-8"))
        delivered = set(state.get("delivered", []))
        sent = []
        for task_state in self.TERMINAL_OR_ATTENTION:
            for record in self.queue.list_by_state(task_state):
                if record.get("action") != "revenue_agent_bounded_task":
                    continue
                task_id = record["task_id"]
                if task_id in delivered:
                    continue
                packet = record.get("result_packet") or {}
                output = decode_bounded_output(packet.get("artifacts_created", []))
                response = {
                    "response_type": "REVENUE_AGENT_RESULT",
                    "summary": f"Revenue Agent: {record['manifest']['title']} → {task_state}",
                    "task_id": task_id,
                    "status": task_state,
                    "priority": "IMPORTANT" if task_state != "COMPLETED" else "INFO",
                    "details": {
                        "view": "REVENUE_RESULT", "state": task_state,
                        "verified_output": output,
                        "references": (record.get("action_params") or {}).get("references", {}),
                        "premium_calls": 0,
                    },
                    "actions": ([{"type": "DETAILS", "task_id": task_id}]
                                if task_state == "COMPLETED" else
                                [{"type": "REVIEW_TASK", "task_id": task_id}]),
                    "generated_by": "NEXUS_REVENUE_AGENT_V1",
                }
                self.notification_sink(response)
                delivered.add(task_id)
                sent.append(task_id)
        temp = self.path.with_suffix(".tmp")
        temp.write_text(json.dumps({"delivered": sorted(delivered)}, indent=2), encoding="utf-8")
        os.replace(temp, self.path)
        return sent


class RevenueAutomationRunner:
    """Small lifecycle wrapper for scheduler + result delivery.

    It never executes outreach or payment actions. The scheduler only submits
    bounded work to the canonical Queue; the normal Dispatcher remains the
    sole execution authority.
    """

    def __init__(self, scheduler, delivery, *, interval_seconds=60,
                 error_sink=None):
        self.scheduler = scheduler
        self.delivery = delivery
        self.interval_seconds = max(1.0, float(interval_seconds))
        self.error_sink = error_sink
        self._stop = threading.Event()
        self._thread = None
        self.last_tick_at = None
        self.last_error_class = None

    @property
    def running(self):
        return bool(self._thread and self._thread.is_alive())

    def start(self):
        if self.running:
            return False
        self._stop.clear()
        self._thread = threading.Thread(target=self._run_loop,
                                        name="nexus-revenue-automation", daemon=True)
        self._thread.start()
        return True

    def stop(self, timeout_seconds=10):
        self._stop.set()
        if self._thread and self._thread is not threading.current_thread():
            self._thread.join(timeout=max(0.1, float(timeout_seconds)))
        return not self.running

    def run_once(self):
        scheduled = self.scheduler.tick()
        delivered = self.delivery.poll()
        self.last_tick_at = _now()
        self.last_error_class = None
        return {"scheduled": scheduled["scheduled"], "delivered": delivered}

    def status(self):
        return {"running": self.running, "last_tick_at": self.last_tick_at,
                "last_error_class": self.last_error_class,
                "interval_seconds": self.interval_seconds}

    def _run_loop(self):
        while not self._stop.is_set():
            try:
                self.run_once()
            except Exception as exc:  # fail isolated; never log payloads or secrets
                self.last_error_class = type(exc).__name__
                if self.error_sink:
                    self.error_sink({"type": "REVENUE_AUTOMATION_DEGRADED",
                                     "failure_class": self.last_error_class})
            self._stop.wait(self.interval_seconds)
