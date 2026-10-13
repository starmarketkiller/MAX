"""NEXUS Execution Control V1.

Policy and reporting layer over ``SharedCognitiveState.work_graph``. Runtime
execution remains owned by ``TaskQueue`` and history remains in ``EventLedger``.
No GitHub Issue, merge, deploy, or external action is performed here.
"""
from __future__ import annotations

import copy
import json
from datetime import datetime, timezone
from pathlib import Path


EXECUTION_CONTROL_SCHEMA = "NEXUS_EXECUTION_CONTROL_V1"
WORKFLOW_STATES = (
    "BACKLOG", "READY", "IN_PROGRESS", "BLOCKED", "REVIEW", "VERIFIED", "DELIVERED",
)
TERMINAL_STATES = {"DELIVERED"}
IMPLEMENTATION_ACTIVE_STATE = "IN_PROGRESS"
DEFAULT_IMPLEMENTATION_WIP_LIMIT = 2

ALLOWED_TRANSITIONS = {
    "BACKLOG": {"READY", "BLOCKED"},
    "READY": {"BACKLOG", "IN_PROGRESS", "BLOCKED"},
    "IN_PROGRESS": {"READY", "BLOCKED", "REVIEW"},
    "BLOCKED": {"BACKLOG", "READY"},
    "REVIEW": {"IN_PROGRESS", "BLOCKED", "VERIFIED"},
    "VERIFIED": {"REVIEW", "BLOCKED", "DELIVERED"},
    "DELIVERED": set(),
}


class ExecutionControlError(RuntimeError):
    """Base class for deterministic control-policy failures."""


class InvalidTransition(ExecutionControlError):
    pass


class WorkInProgressLimit(ExecutionControlError):
    pass


class UnmetDependency(ExecutionControlError):
    pass


def _iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _owner_id(owner) -> str:
    return owner.get("agent_id", "") if isinstance(owner, dict) else str(owner or "")


class ExecutionControl:
    """Enforce portfolio workflow policy on the existing shared work graph."""

    def __init__(self, shared_state, *, implementation_wip_limit: int = 2):
        if implementation_wip_limit < 1:
            raise ValueError("implementation WIP limit must be positive")
        self.shared_state = shared_state
        self.implementation_wip_limit = implementation_wip_limit

    @staticmethod
    def _validate_record(record: dict) -> None:
        required = {
            "id", "title", "kind", "status", "owner", "completion_criteria",
            "dependencies", "blockers", "provenance",
        }
        missing = required - set(record)
        if missing:
            raise ValueError(f"execution item missing fields: {sorted(missing)}")
        if record["status"] not in WORKFLOW_STATES:
            raise ValueError("invalid execution-control status")
        if not record["id"] or not record["title"] or not _owner_id(record["owner"]):
            raise ValueError("id, title and owner are required")
        if not isinstance(record["completion_criteria"], list) or not record["completion_criteria"]:
            raise ValueError("at least one completion criterion is required")
        if record["status"] == "BLOCKED" and not record["blockers"]:
            raise ValueError("BLOCKED item requires a blocker")
        if record["status"] in {"VERIFIED", "DELIVERED"} and not (
                record.get("verification") or {}).get("evidence"):
            raise ValueError("VERIFIED or DELIVERED item requires verification evidence")
        if record["provenance"].get("confidence") not in {"VERIFIED", "DECLARED"}:
            raise ValueError("execution item provenance must be VERIFIED or DECLARED")

    @staticmethod
    def _find(graph: dict, item_id: str) -> dict:
        item = next((entry for entry in graph["workstreams"] if entry["id"] == item_id), None)
        if item is None:
            raise KeyError(item_id)
        return item

    @staticmethod
    def _dependencies_satisfied(graph: dict, record: dict) -> list[str]:
        by_id = {entry["id"]: entry for entry in graph["workstreams"]}
        return [dependency for dependency in record.get("dependencies", [])
                if dependency not in by_id or by_id[dependency]["status"] not in
                {"VERIFIED", "DELIVERED"}]

    def _check_wip(self, graph: dict, candidate: dict) -> None:
        if candidate.get("kind") != "IMPLEMENTATION" or candidate["status"] != "IN_PROGRESS":
            return
        active = [entry for entry in graph["workstreams"]
                  if entry.get("kind") == "IMPLEMENTATION"
                  and entry.get("status") == IMPLEMENTATION_ACTIVE_STATE
                  and entry.get("id") != candidate["id"]]
        if len(active) >= self.implementation_wip_limit:
            raise WorkInProgressLimit(
                f"implementation WIP limit {self.implementation_wip_limit} reached")

    @staticmethod
    def _sync_edges(graph: dict, record: dict) -> None:
        graph["dependencies"] = [edge for edge in graph["dependencies"]
                                 if edge.get("from_id") != record["id"]]
        graph["dependencies"].extend({
            "from_id": record["id"], "to_id": dependency, "relation": "DEPENDS_ON",
            "provenance": copy.deepcopy(record["provenance"]),
        } for dependency in record.get("dependencies", []))

    def register(self, record: dict, *, idempotency_key: str | None = None) -> dict:
        self._validate_record(record)
        value = copy.deepcopy(record)

        def apply(graph):
            if any(item["id"] == value["id"] for item in graph["workstreams"]):
                raise ValueError("execution item already exists; use transition or handoff")
            if value["status"] in {"READY", "IN_PROGRESS"}:
                missing = self._dependencies_satisfied(graph, value)
                if missing:
                    raise UnmetDependency(f"unmet dependencies: {missing}")
            self._check_wip(graph, value)
            now = _iso()
            value.setdefault("created_at", now)
            value["updated_at"] = now
            value.setdefault("transition_history", [{
                "from": None, "to": value["status"], "reason": "REGISTERED", "at": now,
            }])
            value.setdefault("handoffs", [])
            graph["workstreams"].append(value)
            self._sync_edges(graph, value)

        return self.shared_state.apply_work_graph_transaction(
            apply, idempotency_key=idempotency_key)

    def transition(self, item_id: str, target: str, *, reason: str,
                   blockers: list[dict] | None = None, verification: dict | None = None,
                   idempotency_key: str | None = None) -> dict:
        if target not in WORKFLOW_STATES or not reason.strip():
            raise ValueError("valid target and non-empty reason required")

        def apply(graph):
            item = self._find(graph, item_id)
            current = item["status"]
            if target == current:
                return
            if target not in ALLOWED_TRANSITIONS[current]:
                raise InvalidTransition(f"{current} -> {target} is not allowed")
            if target in {"READY", "IN_PROGRESS"}:
                missing = self._dependencies_satisfied(graph, item)
                if missing:
                    raise UnmetDependency(f"unmet dependencies: {missing}")
            candidate = {**item, "status": target}
            self._check_wip(graph, candidate)
            if target == "BLOCKED":
                effective = blockers if blockers is not None else item.get("blockers", [])
                if not effective:
                    raise ValueError("BLOCKED transition requires a blocker")
                item["blockers"] = copy.deepcopy(effective)
            elif blockers is not None:
                item["blockers"] = copy.deepcopy(blockers)
            elif current == "BLOCKED":
                item["blockers"] = []
            if target == "VERIFIED":
                if not verification or not verification.get("evidence"):
                    raise ValueError("VERIFIED transition requires evidence")
                item["verification"] = copy.deepcopy(verification)
            now = _iso()
            item["status"] = target
            item["updated_at"] = now
            item.setdefault("transition_history", []).append({
                "from": current, "to": target, "reason": reason, "at": now,
            })

        return self.shared_state.apply_work_graph_transaction(
            apply, idempotency_key=idempotency_key)

    def handoff(self, item_id: str, *, from_owner: str, to_owner: dict, reason: str,
                acceptance: list[str], idempotency_key: str | None = None) -> dict:
        if not _owner_id(to_owner) or not reason.strip() or not acceptance:
            raise ValueError("target owner, reason and acceptance are required")

        def apply(graph):
            item = self._find(graph, item_id)
            if item["status"] in TERMINAL_STATES:
                raise InvalidTransition("DELIVERED item cannot be handed off")
            if _owner_id(item["owner"]) != from_owner:
                raise PermissionError("handoff owner mismatch")
            now = _iso()
            item.setdefault("handoffs", []).append({
                "from_owner": from_owner, "to_owner": _owner_id(to_owner),
                "reason": reason, "acceptance": list(acceptance), "at": now,
            })
            item["owner"] = copy.deepcopy(to_owner)
            item["updated_at"] = now

        return self.shared_state.apply_work_graph_transaction(
            apply, idempotency_key=idempotency_key)

    def import_seed(self, seed: dict, *, idempotency_prefix: str = "execution-control-seed") -> dict:
        if seed.get("schema_version") != EXECUTION_CONTROL_SCHEMA:
            raise ValueError("unsupported execution-control seed")
        for record in seed.get("items", []):
            self.register(record, idempotency_key=f"{idempotency_prefix}:{record['id']}")
        return self.report()

    def report(self) -> dict:
        graph = self.shared_state.snapshot()["work_graph"]
        runtime_tasks = self.shared_state.build_context_packet()["active_tasks"]
        items = sorted(graph["workstreams"], key=lambda item: item["id"])
        counts = {status: sum(item.get("status") == status for item in items)
                  for status in WORKFLOW_STATES}
        active_impl = [item["id"] for item in items
                       if item.get("kind") == "IMPLEMENTATION"
                       and item.get("status") == "IN_PROGRESS"]
        return {
            "schema_version": "EXECUTION_CONTROL_REPORT_V1",
            "generated_at": _iso(),
            "canonical_source": "NEXUS_SHARED_COGNITIVE_STATE_V1.work_graph",
            "runtime_source": "TASK_QUEUE_V1",
            "history_source": "EVENT_LEDGER_V1",
            "github_sync": "DISABLED_NOT_AUTHORIZED",
            "active_runtime_tasks": runtime_tasks,
            "counts": counts,
            "implementation_wip": {
                "limit": self.implementation_wip_limit,
                "active": len(active_impl), "items": active_impl,
                "within_limit": len(active_impl) <= self.implementation_wip_limit,
            },
            "milestones": [item for item in items if item.get("kind") == "MILESTONE"],
            "suspended": [item for item in items if item.get("status") == "BLOCKED"],
            "items": items,
        }

    def render_markdown(self) -> str:
        report = self.report()
        lines = ["# NEXUS Execution Control V1", "",
                 f"Canonical source: `{report['canonical_source']}`", "",
                 f"Implementation WIP: {report['implementation_wip']['active']}/"
                 f"{report['implementation_wip']['limit']}", "", "## Work", ""]
        for item in report["items"]:
            lines.append(f"- **{item['id']}** — {item['status']} — {_owner_id(item['owner'])} — "
                         f"{item['title']}")
        lines.extend(["", "## Suspended", ""])
        if not report["suspended"]:
            lines.append("- None")
        else:
            for item in report["suspended"]:
                reasons = "; ".join(blocker.get("reason", "UNKNOWN")
                                    for blocker in item.get("blockers", []))
                lines.append(f"- **{item['id']}** — {reasons}")
        lines.extend(["", "## Runtime queue", ""])
        if not report["active_runtime_tasks"]:
            lines.append("- No active TaskQueue records")
        else:
            for item in report["active_runtime_tasks"]:
                lines.append(f"- **{item['task_id']}** — {item['state']} — "
                             f"{item.get('title') or 'Untitled'}")
        return "\n".join(lines) + "\n"


def load_seed(path: str | Path) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))
