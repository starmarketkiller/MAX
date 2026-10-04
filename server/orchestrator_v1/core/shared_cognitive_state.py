"""NEXUS_SHARED_COGNITIVE_STATE_V1.

Materialized, current-state view over canonical sources.  This module does not
replace the append-only EventLedger or TaskQueue.  It stores only explicit
operator/system declarations and advisory leases; task state and result packets
are projected from TaskQueue when CONTEXT_PACKET_V2 is built.
"""
from __future__ import annotations

import copy
import json
import os
import threading
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path


ACTIVE_TASK_STATES = {
    "CREATED", "QUEUED", "RUNNING", "WAITING_DEPENDENCY", "WAITING_APPROVAL",
    "WAITING_PROVIDER", "BLOCKED", "ESCALATION_REQUIRED", "WAITING_REVIEW_PROVIDER",
}
CANONICAL_CONFIDENCE = {"VERIFIED", "DECLARED"}


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(value: datetime | None = None) -> str:
    return (value or _now()).isoformat()


def _empty_state() -> dict:
    return {
        "schema_version": "NEXUS_SHARED_COGNITIVE_STATE_V1",
        "revision": 0,
        "updated_at": None,
        "idempotency_keys": [],
        "current_state": {
            "production": {"git_sha": None, "environment": None, "updated_at": None,
                           "provenance": None},
            "current_milestone": None,
            "closed_milestones": [],
            "roadmap_completion": None,
            "next_priorities": [],
            "blockers": [],
            "agent_provider_state": [],
        },
        "work_graph": {"workstreams": [], "dependencies": []},
        "decisions": [],
        "reservations": [],
    }


class RevisionConflict(RuntimeError):
    pass


class ReservationConflict(RuntimeError):
    pass


class SharedCognitiveState:
    """Thread-safe JSON materialization with atomic replace and CAS revisions.

    V1 deliberately targets the existing single-process deployment.  The
    revision check prevents lost updates between cooperating callers; a future
    multi-process deployment must move this store to a transactional database.
    """

    def __init__(self, path: str | Path, *, task_queue=None, ledger=None):
        self.path = Path(path)
        self.task_queue = task_queue
        self.ledger = ledger
        self._lock = threading.RLock()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self._save(_empty_state())

    def _load(self) -> dict:
        try:
            with self.path.open(encoding="utf-8") as handle:
                value = json.load(handle)
        except (OSError, ValueError, TypeError):
            # Corruption must never be silently promoted to canonical state.
            raise RuntimeError("shared cognitive state unavailable or malformed")
        if value.get("schema_version") != "NEXUS_SHARED_COGNITIVE_STATE_V1":
            raise RuntimeError("unsupported shared cognitive state schema")
        return value

    def _save(self, value: dict) -> None:
        temp = self.path.with_name(
            f"{self.path.name}.{os.getpid()}.{threading.get_ident()}.tmp")
        with temp.open("w", encoding="utf-8") as handle:
            json.dump(value, handle, indent=2, ensure_ascii=False)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp, self.path)

    @staticmethod
    def provenance(source: str, *, confidence: str = "DECLARED", reference: str | None = None,
                   observed_at: str | None = None) -> dict:
        if confidence not in {"VERIFIED", "DECLARED", "UNVERIFIED"}:
            raise ValueError("invalid provenance confidence")
        return {"source": source, "reference": reference, "confidence": confidence,
                "observed_at": observed_at or _iso()}

    def snapshot(self) -> dict:
        with self._lock:
            state = self._load()
            self._mark_stale_reservations(state)
            return copy.deepcopy(state)

    def _transaction(self, mutator, *, expected_revision: int | None = None,
                     idempotency_key: str | None = None) -> dict:
        with self._lock:
            state = self._load()
            if expected_revision is not None and state["revision"] != expected_revision:
                raise RevisionConflict(
                    f"expected revision {expected_revision}, current {state['revision']}")
            if idempotency_key and idempotency_key in state["idempotency_keys"]:
                return copy.deepcopy(state)
            mutator(state)
            state["revision"] += 1
            state["updated_at"] = _iso()
            if idempotency_key:
                state["idempotency_keys"] = (
                    state["idempotency_keys"] + [idempotency_key])[-500:]
            self._save(state)
            return copy.deepcopy(state)

    def update_current_state(self, patch: dict, *, provenance: dict,
                             expected_revision: int | None = None,
                             idempotency_key: str | None = None) -> dict:
        if provenance.get("confidence") not in CANONICAL_CONFIDENCE:
            raise ValueError("unverified information cannot become canonical current state")
        allowed = set(_empty_state()["current_state"])
        unknown = set(patch) - allowed
        if unknown:
            raise ValueError(f"unknown current-state fields: {sorted(unknown)}")

        def apply(state):
            for key, value in patch.items():
                if key == "production" and isinstance(value, dict):
                    state["current_state"][key] = {**value, "provenance": provenance,
                                                     "updated_at": _iso()}
                else:
                    state["current_state"][key] = value
            state["current_state"]["provenance"] = provenance
        return self._transaction(apply, expected_revision=expected_revision,
                                 idempotency_key=idempotency_key)

    def upsert_workstream(self, record: dict, *, expected_revision: int | None = None,
                          idempotency_key: str | None = None) -> dict:
        required = {"id", "name", "status", "owner", "provenance"}
        if not required.issubset(record):
            raise ValueError(f"workstream missing fields: {sorted(required - set(record))}")
        if record["provenance"].get("confidence") not in CANONICAL_CONFIDENCE:
            raise ValueError("unverified workstream cannot become canonical")

        def apply(state):
            items = state["work_graph"]["workstreams"]
            value = {**record, "updated_at": _iso()}
            for index, item in enumerate(items):
                if item["id"] == record["id"]:
                    items[index] = value
                    break
            else:
                value.setdefault("created_at", _iso())
                items.append(value)
        return self._transaction(apply, expected_revision=expected_revision,
                                 idempotency_key=idempotency_key)

    def set_dependencies(self, dependencies: list[dict], *, provenance: dict,
                         expected_revision: int | None = None,
                         idempotency_key: str | None = None) -> dict:
        if provenance.get("confidence") not in CANONICAL_CONFIDENCE:
            raise ValueError("unverified dependencies cannot become canonical")
        for item in dependencies:
            if not {"from_id", "to_id", "relation"}.issubset(item):
                raise ValueError("dependency requires from_id, to_id and relation")

        def apply(state):
            state["work_graph"]["dependencies"] = [
                {**item, "provenance": provenance} for item in dependencies]
        return self._transaction(apply, expected_revision=expected_revision,
                                 idempotency_key=idempotency_key)

    def upsert_decision(self, decision: dict, *, expected_revision: int | None = None,
                        idempotency_key: str | None = None) -> dict:
        required = {"decision_id", "title", "status", "decision", "provenance"}
        if not required.issubset(decision):
            raise ValueError(f"decision missing fields: {sorted(required - set(decision))}")
        if decision["status"] not in {"PROPOSED", "ACTIVE", "SUPERSEDED", "RETIRED"}:
            raise ValueError("invalid decision status")
        if decision["provenance"].get("confidence") not in CANONICAL_CONFIDENCE:
            raise ValueError("unverified decision cannot become canonical")

        def apply(state):
            items = state["decisions"]
            value = {**decision, "updated_at": _iso()}
            for index, item in enumerate(items):
                if item["decision_id"] == decision["decision_id"]:
                    items[index] = value
                    break
            else:
                value.setdefault("created_at", _iso())
                items.append(value)
        return self._transaction(apply, expected_revision=expected_revision,
                                 idempotency_key=idempotency_key)

    def reserve_artifacts(self, *, owner_id: str, task_id: str, artifacts: list[str],
                          ttl_seconds: int, provenance: dict,
                          idempotency_key: str | None = None) -> dict:
        normalized = sorted({str(Path(item).as_posix()).lstrip("/") for item in artifacts if item})
        if not normalized or ttl_seconds < 1:
            raise ValueError("non-empty artifacts and positive TTL required")
        if provenance.get("confidence") not in CANONICAL_CONFIDENCE:
            raise ValueError("unverified reservation owner is not canonical")
        token = uuid.uuid4().hex
        now = _now()

        def apply(state):
            self._mark_stale_reservations(state, now=now)
            active = [item for item in state["reservations"] if item["status"] == "ACTIVE"]
            conflicts = sorted({path for item in active if item["owner_id"] != owner_id
                                for path in normalized if path in item["artifacts"]})
            if conflicts:
                raise ReservationConflict(f"artifacts already reserved: {conflicts}")
            state["reservations"].append({
                "reservation_id": f"res_{uuid.uuid4().hex[:16]}", "lease_token": token,
                "owner_id": owner_id, "task_id": task_id, "artifacts": normalized,
                "status": "ACTIVE", "created_at": now.isoformat(),
                "expires_at": (now + timedelta(seconds=ttl_seconds)).isoformat(),
                "released_at": None, "provenance": provenance,
            })
        result = self._transaction(apply, idempotency_key=idempotency_key)
        created = next((item for item in reversed(result["reservations"])
                        if item["lease_token"] == token), None)
        return created or {"idempotent": True}

    def release_reservation(self, reservation_id: str, lease_token: str,
                            *, idempotency_key: str | None = None) -> dict:
        def apply(state):
            for item in state["reservations"]:
                if item["reservation_id"] == reservation_id:
                    if item["status"] == "RELEASED":
                        return
                    if item["lease_token"] != lease_token:
                        raise PermissionError("invalid reservation lease token")
                    item["status"] = "RELEASED"
                    item["released_at"] = _iso()
                    return
            raise KeyError(reservation_id)
        return self._transaction(apply, idempotency_key=idempotency_key)

    @staticmethod
    def _mark_stale_reservations(state: dict, *, now: datetime | None = None) -> None:
        now = now or _now()
        for item in state["reservations"]:
            if item["status"] == "ACTIVE" and datetime.fromisoformat(item["expires_at"]) <= now:
                item["status"] = "STALE"

    def build_context_packet(self, *, agent_states: list[dict] | None = None,
                             provider_states: list[dict] | None = None,
                             production_identity: dict | None = None) -> dict:
        state = self.snapshot()
        tasks = self.task_queue.list_all() if self.task_queue else []
        active = [{
            "task_id": item.get("task_id"),
            "title": (item.get("manifest") or {}).get("title"),
            "objective": (item.get("manifest") or {}).get("objective"),
            "state": item.get("state"),
            "owner": item.get("executor"),
            "priority": item.get("priority"),
            "dependencies": item.get("dependencies", []),
            "blocker": item.get("dispatch_last_error"),
            "updated_at": item.get("updated_at"),
            "provenance": {"source": "TASK_QUEUE_V1", "reference": item.get("task_id"),
                           "confidence": "VERIFIED", "observed_at": _iso()},
        } for item in tasks if item.get("state") in ACTIVE_TASK_STATES]
        latest_results = [{"task_id": item["task_id"], "state": item["state"],
                           "result_packet": item.get("result_packet"),
                           "updated_at": item.get("updated_at")}
                          for item in sorted(tasks, key=lambda value: value.get("updated_at") or "",
                                             reverse=True) if item.get("result_packet")][:10]
        production = production_identity or state["current_state"].get("production") or {}
        packet = {
            "schema_version": "CONTEXT_PACKET_V2",
            "generated_at": _iso(),
            "state_revision": state["revision"],
            "freshness": "CURRENT" if state.get("updated_at") else "UNKNOWN",
            "production": production,
            "current_milestone": state["current_state"].get("current_milestone"),
            "closed_milestones": state["current_state"].get("closed_milestones", []),
            "roadmap_completion": state["current_state"].get("roadmap_completion"),
            "next_priorities": state["current_state"].get("next_priorities", []),
            "blockers": state["current_state"].get("blockers", []),
            "active_tasks": active,
            "work_graph": state["work_graph"],
            # Lease tokens are write credentials and never leave the internal store.
            "artifact_reservations": [
                {key: value for key, value in item.items() if key != "lease_token"}
                for item in state["reservations"] if item["status"] in {"ACTIVE", "STALE"}],
            "active_decisions": [item for item in state["decisions"] if item["status"] == "ACTIVE"],
            "latest_result_packets": latest_results,
            "agents": agent_states if agent_states is not None else
                      state["current_state"].get("agent_provider_state", []),
            "providers": provider_states or [],
            "source_refs": {
                "shared_state": str(self.path.name),
                "task_queue": str(Path(self.task_queue.path).name) if self.task_queue else None,
                "ledger": str(Path(self.ledger.path).name) if self.ledger else None,
            },
        }
        return packet
