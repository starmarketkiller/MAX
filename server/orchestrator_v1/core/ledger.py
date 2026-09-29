#!/usr/bin/env python3
"""NEXUS Orchestrator V1 Core - Activity Ledger (Fase 8 del task).

Append-only, JSONL (una riga = un evento NEXUS_EVENT_V1, validato contro
contracts/nexus-event.schema.json). Jarvis e qualunque UI devono leggere
SOLO da qui per "cosa e' successo" - mai dalla memoria di un LLM (principio
gia' stabilito in docs/architecture/18_ORCHESTRATOR_AGENT_ROUTING_V1.md §12).

Implementazione concreta scelta in questa fase: JSONL locale (non SQLite) -
piu' semplice da ispezionare/diffare a mano, coerente con lo stile
"solo stdlib, nessuna dipendenza pesante" gia' usato in tutto orchestrator_v1."""
import json
import os
import sys
import threading
import uuid
from datetime import datetime, timezone
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

with open(os.path.join(CONTRACTS_DIR, "nexus-event.schema.json"), encoding="utf-8") as f:
    NEXUS_EVENT_SCHEMA = json.load(f)

TENANT_ID = "tenant-1"


def _now_iso():
    return datetime.now(timezone.utc).isoformat()


class EventLedger:
    """Append-only. Nessun metodo di update/delete per costruzione."""

    def __init__(self, path=None):
        self.path = path or os.path.join(RUNTIME_STATE_DIR, "event_ledger_v1.jsonl")
        self._lock = threading.RLock()
        os.makedirs(os.path.dirname(self.path), exist_ok=True)

    def append(self, event_type, task_id, payload, actor="orchestrator_v1_core"):
        event = {
            "event_id": f"evt_{uuid.uuid4().hex[:16]}",
            "event_type": event_type,
            "task_id": task_id,
            "timestamp": _now_iso(),
            "tenant_id": TENANT_ID,
            "payload": {**payload, "actor": actor},
        }
        errors = validate(event, NEXUS_EVENT_SCHEMA)
        if errors:
            raise AssertionError(f"Evento non valido contro NEXUS_EVENT_V1: {errors}")
        with self._lock:
            with open(self.path, "a", encoding="utf-8") as f:
                f.write(json.dumps(event, ensure_ascii=False) + "\n")
                f.flush()
        return event

    def read_all(self):
        if not os.path.exists(self.path):
            return []
        with self._lock:
            events = []
            with open(self.path, encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        events.append(json.loads(line))
            return events

    def read_for_task(self, task_id):
        return [e for e in self.read_all() if e["task_id"] == task_id]
