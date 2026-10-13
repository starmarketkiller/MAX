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
from nexus_tenant import canonical_tenant_id  # noqa: E402

ROOT = str(resolve_project_root(__file__))
RUNTIME_STATE_DIR = os.path.join(ORCH_DIR, "runtime_state")
CONTRACTS_DIR = str(resolve_contracts_dir(__file__))

sys.path.insert(0, ORCH_DIR)
from nxs_schema_validator import validate  # noqa: E402

with open(os.path.join(CONTRACTS_DIR, "nexus-event.schema.json"), encoding="utf-8") as f:
    NEXUS_EVENT_SCHEMA = json.load(f)



def _now_iso():
    return datetime.now(timezone.utc).isoformat()


class EventLedger:
    """Append-only ledger with durable writes and bounded tail recovery.

    A process crash may leave only the final JSONL record incomplete.  That
    final fragment is ignored on reads and removed before the next append.
    Every other malformed record is corruption and is reported explicitly.
    """

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
            "tenant_id": canonical_tenant_id(),
            "payload": {**payload, "actor": actor},
        }
        errors = validate(event, NEXUS_EVENT_SCHEMA)
        if errors:
            raise AssertionError(f"Evento non valido contro NEXUS_EVENT_V1: {errors}")
        with self._lock:
            incomplete_offset, needs_separator = self._inspect_tail_unlocked()
            if incomplete_offset is not None:
                with open(self.path, "r+b") as f:
                    f.truncate(incomplete_offset)
                    f.flush()
                    os.fsync(f.fileno())
                needs_separator = False
            encoded = json.dumps(event, ensure_ascii=False).encode("utf-8") + b"\n"
            with open(self.path, "ab") as f:
                if needs_separator:
                    f.write(b"\n")
                f.write(encoded)
                f.flush()
                os.fsync(f.fileno())
        return event

    def _inspect_tail_unlocked(self):
        """Inspect only the final record before append, avoiding O(ledger size)."""
        if not os.path.exists(self.path) or os.path.getsize(self.path) == 0:
            return None, False
        with open(self.path, "rb") as f:
            f.seek(0, os.SEEK_END)
            size = f.tell()
            f.seek(size - 1)
            if f.read(1) in (b"\n", b"\r"):
                return None, False

            position = size
            tail_start = 0
            while position > 0:
                start = max(0, position - 4096)
                f.seek(start)
                chunk = f.read(position - start)
                separator = chunk.rfind(b"\n")
                if separator >= 0:
                    tail_start = start + separator + 1
                    break
                position = start
            f.seek(tail_start)
            tail = f.read(size - tail_start).rstrip(b"\r")
        try:
            if not tail:
                raise ValueError("empty JSONL tail")
            json.loads(tail.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError, ValueError):
            return tail_start, False
        return None, True

    def read_all(self):
        if not os.path.exists(self.path):
            return []
        with self._lock:
            events, _incomplete_offset, _needs_separator = self._read_unlocked()
            return events

    def _read_unlocked(self):
        """Return events plus recoverable-tail metadata; caller holds lock."""
        if not os.path.exists(self.path):
            return [], None, False
        with open(self.path, "rb") as f:
            data = f.read()
        events = []
        offset = 0
        lines = data.splitlines(keepends=True)
        for index, line in enumerate(lines, start=1):
            complete = line.endswith((b"\n", b"\r"))
            raw = line.rstrip(b"\r\n")
            try:
                if not raw:
                    raise ValueError("empty JSONL record")
                events.append(json.loads(raw.decode("utf-8")))
            except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
                is_incomplete_tail = index == len(lines) and not complete
                if is_incomplete_tail:
                    return events, offset, False
                raise LedgerCorruptionError(
                    f"Activity Ledger corruption at complete record {index}"
                ) from exc
            offset += len(line)
        needs_separator = bool(data) and not data.endswith((b"\n", b"\r"))
        return events, None, needs_separator

    def read_for_task(self, task_id):
        return [e for e in self.read_all() if e["task_id"] == task_id]


class LedgerCorruptionError(RuntimeError):
    """A complete Activity Ledger record is malformed and cannot be hidden."""
