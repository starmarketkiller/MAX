#!/usr/bin/env python3
"""NEXUS Orchestrator V1 Core - Task Queue (Fase 2 del task).

Persistenza: JSON locale (runtime_state/task_queue_v1.json) - un dict
task_id -> record. V1 e' deliberatamente single-process: un RLock protegge
i thread web/dispatcher e i salvataggi usano replace atomico. Il multi-process
richiede una queue transazionale condivisa e resta fuori scope.

Ogni record incapsula un TASK_MANIFEST_V1 (contracts/task-manifest.schema.json,
validato) + stato di esecuzione (non parte dello schema del manifest, che
descrive SOLO l'intento del task, non il suo stato runtime - separazione
deliberata)."""
import json
import os
import sys
import threading
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

CORE_DIR = os.path.dirname(os.path.abspath(__file__))
ORCH_DIR = os.path.dirname(CORE_DIR)
SERVER_DIR = str(Path(__file__).resolve().parents[2])
sys.path.insert(0, SERVER_DIR)
from path_resolver import resolve_contracts_dir, resolve_project_root  # noqa: E402

ROOT = str(resolve_project_root(__file__))
RUNTIME_STATE_DIR = os.path.join(ORCH_DIR, "runtime_state")
CONTRACTS_DIR = str(resolve_contracts_dir(__file__))

sys.path.insert(0, ORCH_DIR)
from nxs_schema_validator import validate  # noqa: E402

with open(os.path.join(CONTRACTS_DIR, "task-manifest.schema.json"), encoding="utf-8") as f:
    TASK_MANIFEST_SCHEMA = json.load(f)

STATES = ["CREATED", "QUEUED", "RUNNING", "WAITING_DEPENDENCY", "WAITING_APPROVAL",
         "WAITING_PROVIDER", "COMPLETED", "FAILED", "BLOCKED", "ESCALATION_REQUIRED",
         "CANCELLED"]

# Transizioni di stato permesse - fail-closed: una transizione non elencata qui
# viene rifiutata con un'eccezione, non applicata silenziosamente.
ALLOWED_TRANSITIONS = {
    "CREATED": {"QUEUED", "BLOCKED", "WAITING_DEPENDENCY", "CANCELLED"},
    "QUEUED": {"RUNNING", "WAITING_DEPENDENCY", "BLOCKED", "CANCELLED"},
    "WAITING_DEPENDENCY": {"QUEUED", "BLOCKED", "CANCELLED"},
    "RUNNING": {"COMPLETED", "FAILED", "WAITING_APPROVAL", "WAITING_PROVIDER",
               "ESCALATION_REQUIRED", "QUEUED", "RUNNING", "BLOCKED"},  # QUEUED = retry delimitato;
               # RUNNING->RUNNING = self-transition per bookkeeping (es. retry_count) senza
               # cambiare stato - un vero cambio di stato resta sempre esplicito altrove
    "WAITING_APPROVAL": {"COMPLETED", "FAILED", "QUEUED", "CANCELLED"},
    "WAITING_PROVIDER": {"RUNNING", "COMPLETED", "FAILED", "CANCELLED"},
    "ESCALATION_REQUIRED": {"WAITING_PROVIDER", "FAILED", "QUEUED", "WAITING_APPROVAL",
                          "COMPLETED", "CANCELLED"},  # WAITING_APPROVAL/COMPLETED = la risoluzione
                          # dell'escalation (TIER3_CLAUDE/TIER4_CODEX) e' arrivata e verificata
                          # - se tocca/crea file reali che richiedono revisione va a
                          # WAITING_APPROVAL, altrimenti direttamente COMPLETED (scoperto in
                          # NEXUS TASK #0005, la prima escalation di questo Core risolta con
                          # un intero nuovo framework invece di un singolo campo dato)
    "BLOCKED": {"QUEUED", "CANCELLED"},
    "COMPLETED": set(),
    "FAILED": {"QUEUED"},  # solo se un umano decide di ritentare esplicitamente
    "CANCELLED": set(),
}


def _now_iso():
    return datetime.now(timezone.utc).isoformat()


class TaskQueue:
    def __init__(self, path=None):
        self.path = path or os.path.join(RUNTIME_STATE_DIR, "task_queue_v1.json")
        self._lock = threading.RLock()
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        if not os.path.exists(self.path):
            self._save({})

    def _load(self):
        with open(self.path, encoding="utf-8") as f:
            return json.load(f)

    def _save(self, data):
        temp_path = f"{self.path}.{os.getpid()}.{threading.get_ident()}.tmp"
        with open(temp_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
            f.flush()
            os.fsync(f.fileno())
        os.replace(temp_path, self.path)

    def submit(self, manifest, dependencies=None, action=None, action_params=None):
        """Registra un nuovo TASK_MANIFEST_V1 - valida contro lo schema PRIMA
        di accettarlo (fail-closed: un manifest non valido non entra mai in
        coda).

        `action`/`action_params` sono metadati SOLO di orchestrazione (quale
        funzione del deterministic/ollama worker eseguire e con quali
        parametri) - vivono nel record del TaskQueue, MAI dentro il manifest
        stesso, perche' TASK_MANIFEST_V1 e' additionalProperties:false per
        design (niente campi liberi nel contratto schema-validato - vedi
        §3-4 dell'architettura) - questa e' la separazione deliberata fra
        'intento del task' (manifest, contrattuale) e 'come orchestrarlo in
        pratica' (record, interno)."""
        errors = validate(manifest, TASK_MANIFEST_SCHEMA)
        if errors:
            raise AssertionError(f"TASK_MANIFEST_V1 non valido: {errors}")
        task_id = manifest["task_id"]
        with self._lock:
            data = self._load()
            if task_id in data:
                raise AssertionError(f"task_id gia' esistente: {task_id}")
            record = {
                "task_id": task_id, "manifest": manifest, "state": "CREATED",
                "priority": manifest["priority"], "dependencies": dependencies or [],
                "action": action, "action_params": action_params or {},
                "executor": None, "retry_count": 0,
                "created_at": _now_iso(), "updated_at": _now_iso(),
                "started_at": None, "completed_at": None,
                "result_packet": None,
                "provenance": {"source": "orchestrator_v1_core", "created_by": manifest.get("created_by")},
                "escalation": None, "dispatch_claim": None,
                "dispatch_attempts": 0, "dispatch_next_attempt_at": None,
                "dispatch_last_error": None,
            }
            data[task_id] = record
            self._save(data)
            return record

    def get(self, task_id):
        with self._lock:
            data = self._load()
            if task_id not in data:
                raise KeyError(f"task_id sconosciuto: {task_id}")
            return data[task_id]

    def list_all(self):
        with self._lock:
            return list(self._load().values())

    def list_by_state(self, state):
        return [t for t in self.list_all() if t["state"] == state]

    def transition(self, task_id, new_state, **updates):
        with self._lock:
            data = self._load()
            record = data[task_id]
            current = record["state"]
            if new_state not in ALLOWED_TRANSITIONS.get(current, set()):
                raise AssertionError(f"Transizione non permessa: {current} -> {new_state} "
                                    f"(task {task_id})")
            record["state"] = new_state
            record["updated_at"] = _now_iso()
            if new_state == "RUNNING" and record["started_at"] is None:
                record["started_at"] = _now_iso()
            if new_state in ("COMPLETED", "FAILED", "CANCELLED"):
                record["completed_at"] = _now_iso()
            for k, v in updates.items():
                record[k] = v
            data[task_id] = record
            self._save(data)
            return record

    def try_promote(self, task_id):
        """Se un task e' WAITING_DEPENDENCY e tutte le sue dependencies sono
        ora COMPLETED, lo promuove a QUEUED. Necessario perche' un task puo'
        essere sottomesso PRIMA che la sua dipendenza sia stata processata
        (submit() controlla le dependencies una sola volta, al momento
        della sottomissione - senza questa promozione esplicita il task
        resterebbe bloccato per sempre)."""
        with self._lock:
            data = self._load()
            record = data[task_id]
            if record["state"] != "WAITING_DEPENDENCY":
                return record
            deps_ok = all(data.get(d, {}).get("state") == "COMPLETED" for d in record["dependencies"])
            if deps_ok:
                return self.transition(task_id, "QUEUED")
            return record

    def next_runnable(self):
        """Ritorna il prossimo task QUEUED con priorita' piu' alta e tutte le
        dependencies COMPLETED - None se nessuno e' eseguibile ora."""
        with self._lock:
            data = self._load()
            queued = [t for t in data.values() if t["state"] == "QUEUED"]
            priority_rank = {"URGENT": 0, "HIGH": 1, "NORMAL": 2, "LOW": 3}
            runnable = []
            for t in queued:
                deps_ok = all(data.get(d, {}).get("state") == "COMPLETED"
                              for d in t["dependencies"])
                if deps_ok:
                    runnable.append(t)
            if not runnable:
                return None
            runnable.sort(key=lambda t: (priority_rank.get(t["priority"], 9), t["created_at"]))
            return runnable[0]

    def claim_next(self, owner_id, lease_seconds=900):
        """Atomically claim one runnable task without bypassing the Router."""
        with self._lock:
            data = self._load()
            now = datetime.now(timezone.utc)
            priority_rank = {"URGENT": 0, "HIGH": 1, "NORMAL": 2, "LOW": 3}
            candidates = []
            changed = False
            for record in data.values():
                if record["state"] == "WAITING_DEPENDENCY" and all(
                        data.get(dep, {}).get("state") == "COMPLETED"
                        for dep in record.get("dependencies", [])):
                    record["state"] = "QUEUED"
                    record["updated_at"] = _now_iso()
                    changed = True
                if record["state"] != "QUEUED":
                    continue
                next_at = record.get("dispatch_next_attempt_at")
                if next_at and datetime.fromisoformat(next_at) > now:
                    continue
                claim = record.get("dispatch_claim")
                if claim:
                    expires = datetime.fromisoformat(claim["lease_expires_at"])
                    if expires > now:
                        continue
                    record["dispatch_claim"] = None
                    changed = True
                if all(data.get(dep, {}).get("state") == "COMPLETED"
                       for dep in record.get("dependencies", [])):
                    candidates.append(record)
            if not candidates:
                if changed:
                    self._save(data)
                return None
            candidates.sort(key=lambda item: (
                priority_rank.get(item.get("priority"), 9), item.get("created_at", "")))
            record = candidates[0]
            token = uuid.uuid4().hex
            record["dispatch_claim"] = {
                "owner_id": owner_id, "token": token, "claimed_at": now.isoformat(),
                "lease_expires_at": (now + timedelta(seconds=lease_seconds)).isoformat(),
            }
            record["dispatch_attempts"] = int(record.get("dispatch_attempts") or 0) + 1
            record["updated_at"] = _now_iso()
            data[record["task_id"]] = record
            self._save(data)
            return record

    def assert_claim(self, task_id, token):
        with self._lock:
            record = self.get(task_id)
            claim = record.get("dispatch_claim")
            if claim and claim.get("token") != token:
                raise AssertionError(f"task {task_id} claimed by another dispatcher")
            if token and (not claim or claim.get("token") != token):
                raise AssertionError(f"invalid or expired dispatch claim for {task_id}")
            return record

    def release_claim(self, task_id, token, *, retry_after_seconds=None, error=None):
        with self._lock:
            data = self._load()
            record = data[task_id]
            claim = record.get("dispatch_claim")
            if not claim or claim.get("token") != token:
                return False
            record["dispatch_claim"] = None
            # A successful claim release must not erase a fail-closed diagnostic
            # persisted by the dispatcher after the task already became BLOCKED.
            if error is not None:
                record["dispatch_last_error"] = str(error)[:500]
            record["dispatch_next_attempt_at"] = (
                (datetime.now(timezone.utc) + timedelta(seconds=retry_after_seconds)).isoformat()
                if retry_after_seconds else None)
            record["updated_at"] = _now_iso()
            self._save(data)
            return True

    def recover_orphaned_running(self, owner_id):
        """Classify ambiguous in-flight work fail-closed after a restart."""
        with self._lock:
            data = self._load()
            recovered = []
            for record in data.values():
                if record["state"] != "RUNNING":
                    continue
                record["state"] = "BLOCKED"
                record["dispatch_claim"] = None
                record["dispatch_last_error"] = "ORPHANED_RUNNING_AFTER_RESTART"
                record["recovery"] = {"classification": "ORPHANED_RUNNING_AFTER_RESTART",
                                      "recovered_by": owner_id, "recovered_at": _now_iso()}
                record["updated_at"] = _now_iso()
                recovered.append(record["task_id"])
            if recovered:
                self._save(data)
            return recovered


def new_task_id(prefix="TASK"):
    return f"{prefix}_{uuid.uuid4().hex[:12].upper()}"
