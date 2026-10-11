"""Read-only RI-01/RI-02 projection for the NEXUS Research Control Center.

The canonical ResearchMemory remains the only source.  This module does not
run a loop, rank hypotheses, decide proposals, or touch protected datasets.
"""
from __future__ import annotations

import os
import sys
from datetime import datetime, timezone
from pathlib import Path


SERVER = Path(__file__).resolve().parent
RI_SCRIPTS = SERVER / "research_scripts"
if str(RI_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(RI_SCRIPTS))

from research_intelligence_v1.agents import ROLES, STEP_OWNER, validate_roles  # noqa: E402
from research_intelligence_v1.loop import STEPS  # noqa: E402
from research_intelligence_v1.memory import DEFAULT_PATH, ResearchMemory  # noqa: E402


def _now():
    return datetime.now(timezone.utc).isoformat()


class ResearchIntelligenceReadModel:
    def __init__(self, memory_path: str | Path = DEFAULT_PATH):
        self.memory_path = str(memory_path)

    @staticmethod
    def _current_records(memory, record_type):
        rows = memory.of_type(record_type)
        superseded = {rel["target"] for row in memory.records for rel in row.get("relations", [])
                      if rel.get("type") == "SUPERSEDES"}
        return [row for row in rows if row["record_id"] not in superseded]

    @staticmethod
    def _provenance(row):
        return [{"kind": item.get("kind"), "ref": item.get("ref"),
                 "sha256": item.get("sha256")} for item in row.get("provenance", [])]

    def _empty(self, code, detail):
        source = os.path.relpath(self.memory_path, SERVER.parent).replace("\\", "/")
        return {
            "schema_version": "research-control-center-v1", "generated_at": _now(),
            "status": "UNAVAILABLE", "warnings": [{"code": code, "detail": detail}],
            "provenance": {"source": source, "verified": False, "head_hash": None, "records": 0},
            "research_loop": {"status": "UNAVAILABLE", "current_cycle": None,
                              "current_phase": None, "last_cycle": None, "next_actions": []},
            "experiment_registry": {"items": [], "count": 0, "datasets": []},
            "hypothesis_queue": {"status": "UNAVAILABLE", "items": [], "limits": None,
                                 "reason": detail},
            "improvement_center": {"items": [], "count": 0},
            "research_memory": {"items": [], "count": 0},
            "agent_activity": {"items": [], "count": 0},
            "approval_center": {"actions_enabled": False, "items": [], "count": 0,
                                "reason": "Read-only RI-03 contract"},
        }

    def build(self):
        if not os.path.exists(self.memory_path):
            return self._empty("RESEARCH_MEMORY_NOT_FOUND", "Canonical research memory is not materialized")
        try:
            memory = ResearchMemory(self.memory_path)
            integrity = memory.verify()
        except Exception as exc:  # fail closed: invalid JSON/schema is never presented as real state
            return self._empty("RESEARCH_MEMORY_READ_FAILED", f"{type(exc).__name__}: {str(exc)[:180]}")

        warnings = [{"code": "RESEARCH_MEMORY_INTEGRITY_FAILED", "detail": problem}
                    for problem in integrity[:20]]
        warnings += [{"code": "AGENT_ROLE_CONTRACT_INVALID", "detail": problem}
                     for problem in validate_roles()]
        transitions = memory.of_type("LOOP_TRANSITION")
        cycles = {}
        for row in transitions:
            cycles.setdefault(row["body"]["cycle_id"], []).append(row)
        current_cycle = next((cid for cid in sorted(cycles, reverse=True)
                              if not any(r["body"]["status"] in ("CYCLE_CLOSED", "CYCLE_ABANDONED")
                                         for r in cycles[cid])), None)
        last_cycle = sorted(cycles)[-1] if cycles else None
        cycle_rows = cycles.get(current_cycle or last_cycle, [])
        completed = {row["body"]["step"] for row in cycle_rows
                     if row["body"]["status"] == "COMPLETED"}
        started = [row for row in cycle_rows if row["body"]["status"] == "STARTED"]
        current_phase = started[-1]["body"]["step"] if started else \
            next((step for step in STEPS if step not in completed), None)
        last_transition = transitions[-1] if transitions else None
        loop_status = "IDLE_NOT_RUN" if not transitions else \
            ("RUNNING" if current_cycle else last_transition["body"]["status"])

        experiments, datasets = [], {}
        for row in self._current_records(memory, "EXPERIMENT"):
            body = row["body"]
            ds = []
            for item in body.get("datasets", []):
                safe = {key: item.get(key) for key in ("dataset_id", "split", "exposure", "period", "sha256")}
                ds.append(safe)
                datasets[safe["dataset_id"]] = safe
            experiments.append({
                "record_id": row["record_id"], "family": row["family"],
                "hypothesis_id": body.get("hypothesis_id"), "status": body.get("status"),
                "result": body.get("result"), "decision": body.get("decision"),
                "evidence_level": body.get("evidence_level"), "datasets": ds,
                "created_at": row["created_at"], "provenance": self._provenance(row),
            })

        priorities = memory.of_type("PRIORITIZATION")
        priority = priorities[-1] if priorities else None
        queue_items = []
        if priority:
            for item in priority["body"].get("ranked", []):
                queue_items.append({"record_id": item.get("record_id"), "family": item.get("family"),
                                    "priority": item.get("total"), "scores": item.get("scores"),
                                    "evidence_level": item.get("evidence_level")})

        proposals = []
        for row in self._current_records(memory, "IMPROVEMENT_PROPOSAL"):
            body = row["body"]
            trial_rows = [trial for trial in memory.of_type("IMPROVEMENT_TRIAL")
                          if trial["body"].get("proposal_record") in (row["record_id"],)]
            proposals.append({
                "record_id": row["record_id"], "family": row["family"], "title": body.get("title"),
                "proposal_class": body.get("proposal_class"), "status": body.get("status"),
                "baseline": body.get("baseline"), "success_criterion": body.get("success_criterion"),
                "requires": body.get("requires", []), "touches_frozen_or_live": body.get("touches_frozen_or_live"),
                "results": [{"phase": t["body"].get("phase"), "verdict": t["body"].get("verdict"),
                             "record_id": t["record_id"]} for t in trial_rows],
                "created_at": row["created_at"], "provenance": self._provenance(row),
            })

        knowledge = []
        for row in memory.records:
            if row["record_type"] == "OBSERVATION":
                summary = row["body"].get("statement") or row["body"].get("description") or row["record_id"]
            elif row["record_type"] == "REVIEW":
                findings = row["body"].get("findings", [])
                summary = f"{len(findings)} findings for {row['body'].get('reviewed_record')}"
            else:
                continue
            knowledge.append({"record_id": row["record_id"], "type": row["record_type"],
                              "family": row["family"], "summary": summary,
                              "created_at": row["created_at"], "origin": row["origin"],
                              "provenance": self._provenance(row)})

        activities = []
        for role_id, role in ROLES.items():
            owned = [row for row in transitions if STEP_OWNER.get(row["body"]["step"]) == role_id]
            latest = owned[-1] if owned else None
            activities.append({
                "role_id": role_id, "executor": role["executor"], "escalation": role["escalation"],
                "steps": role["steps"], "status": "ACTIVE" if latest and current_cycle and
                latest["body"]["status"] == "STARTED" else ("IDLE" if latest else "INACTIVE"),
                "last_operation": latest["body"]["step"] if latest else None,
                "last_outcome": latest["body"]["status"] if latest else None,
                "last_updated": latest["created_at"] if latest else None,
            })

        approvals = [{"kind": "IMPROVEMENT_PROPOSAL", "record_id": p["record_id"],
                      "title": p["title"], "status": p["status"], "requires": p["requires"]}
                     for p in proposals if p["status"] in ("PROPOSED", "ACCEPTED")]
        approvals += [{"kind": "RESEARCH_ACTION", "record_id": row["record_id"],
                       "title": row["body"].get("kind"), "status": row["body"].get("status"),
                       "requires": row["body"].get("reasons", [])}
                      for row in memory.of_type("ACTION") if row["body"].get("status") == "AWAITING_APPROVAL"]

        source = os.path.relpath(self.memory_path, SERVER.parent).replace("\\", "/")
        return {
            "schema_version": "research-control-center-v1", "generated_at": _now(),
            "status": "HEALTHY" if not warnings else "DEGRADED", "warnings": warnings,
            "provenance": {"source": source, "verified": not integrity,
                           "head_hash": memory.head_hash(), "records": len(memory.records)},
            "research_loop": {"status": loop_status, "current_cycle": current_cycle,
                              "current_phase": current_phase if current_cycle else None,
                              "last_cycle": last_cycle,
                              "last_transition_at": last_transition["created_at"] if last_transition else None,
                              "completed_steps": [s for s in STEPS if s in completed],
                              "next_actions": ([current_phase] if current_cycle and current_phase else
                                               ["Start a cycle explicitly"] if not transitions else [])},
            "experiment_registry": {"items": experiments, "count": len(experiments),
                                    "datasets": list(datasets.values())},
            "hypothesis_queue": {"status": "AVAILABLE" if priority else "NOT_MATERIALIZED",
                                 "items": queue_items,
                                 "limits": priority["body"].get("budget") if priority else None,
                                 "deduplication": "candidate_signature.py",
                                 "reason": None if priority else "No persisted PRIORITIZATION record"},
            "improvement_center": {"items": proposals, "count": len(proposals)},
            "research_memory": {"items": knowledge, "count": len(knowledge)},
            "agent_activity": {"items": activities, "count": len(activities)},
            "approval_center": {"actions_enabled": False, "items": approvals, "count": len(approvals),
                                "reason": "RI-03 is read-only; decisions remain behind RI-02 safety gates"},
        }


CATALOG = ResearchIntelligenceReadModel()
