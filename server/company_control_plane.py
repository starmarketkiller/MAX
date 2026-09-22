"""Read-only, fault-isolated company control-plane projection.

The module never mutates research artifacts.  It exposes only explicit facts
already present in canonical JSON and keeps raw scientific labels alongside a
small operational status vocabulary.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import sequence_research_read_model
import strategy_pipeline_read_model

ROOT = Path(__file__).resolve().parent
P7 = ROOT / "research_scripts" / "phase7"

DEPARTMENT_SLOTS = (
    ("DATA", "Data", "PARTIAL"),
    ("QUANT_RESEARCH", "Quant Research", "ACTIVE"),
    ("SCIENTIFIC_QA", "Scientific QA", "PARTIAL"),
    ("COMPUTE_INFRA", "Compute / Infra", "PARTIAL"),
    ("EXECUTION", "Execution", "SKELETON"),
    ("RISK_PORTFOLIO", "Risk / Portfolio", "SKELETON"),
    ("KNOWLEDGE_INTELLIGENCE", "Knowledge / Intelligence", "PARTIAL"),
)

SOURCES = {
    "dataset_registry": P7 / "dataset_version_registry_v2.json",
    "dataset_integrity": P7 / "new_dataset_integrity_report_v1.json",
    "holdout_seal": P7 / "final_holdout_seal_v1.json",
    "p73_gate": P7 / "phase7_3" / "phase7_3_engine_readiness_gate_v1.json",
    "candidate_queue": P7 / "phase7_5" / "phase7_5_candidate_queue_v1.json",
    "structural_results": P7 / "phase7_5" / "phase7_5_structural_feasibility_results_v1.json",
    "seq0009_result": P7 / "phase7_5b" / "seq0009_structural_feasibility_result_v1.json",
    "seq0014_result": P7 / "phase7_5c" / "seq0014_structural_feasibility_result_v1.json",
    "seq0014_prereg": P7 / "phase7_6a" / "seq0014_statistical_preregistration_v1.json",
    "seq0014b_spec": P7 / "phase7_6b" / "seq0014b_setup_population_spec_v1.json",
    "seq0014b_result": P7 / "phase7_6c" / "seq0014b_structural_preflight_result_v1.json",
    "seq0014b_audit": P7 / "phase7_6c" / "seq0014b_outcome_horizon_ordering_audit_v1.json",
    "seq0014b_horizon_contract": P7 / "phase7_6d" / "seq0014b_outcome_horizon_contract_v1.json",
    "seq0014b_native_setup_audit": P7 / "phase7_6e" / "seq0014b_native_setup_failure_audit_v1.json",
    "strategy_lifecycle": P7 / "phase7_7a" / "strategy_lifecycle_registry_v1.json",
    "strategy_evidence": P7 / "phase7_7a" / "strategy_evidence_matrix_v1.json",
    "strategy_meta_filter": P7 / "phase7_7a" / "strategy_meta_filter_eligibility_v1.json",
    "strategy_meta_filter_gate": P7 / "phase7_7b" / "strategy_meta_filter_gate_v1.json",
    "strategy_structural_semantics": P7 / "phase7_7b" / "structural_eligibility_semantics_correction_v1.json",
    "strategy_missing_field_semantics": P7 / "phase7_7b" / "missing_field_semantics_refinement_v1.json",
}

STATUS_MAP = {
    "READY_FOR_FORMALIZATION": "READY", "READY_FOR_PREREGISTRATION": "READY",
    "READY": "READY", "ACTIVE": "ACTIVE", "PASS": "PASSED", "PASSED": "PASSED",
    "FAIL": "FAILED", "FAILED": "FAILED", "BLOCKED": "BLOCKED",
    "NOT_IMPLEMENTABLE_AS_DESCRIBED": "BLOCKED",
    "NEEDS_ADDITIONAL_SPECIFICATION": "BLOCKED",
    "NEEDS_MATCHING_FORMALIZATION": "BLOCKED",
    "STRUCTURALLY_BLOCKED_ON_CURRENT_PARTITION": "BLOCKED",
    "MATCHING_STRUCTURALLY_INFEASIBLE": "BLOCKED",
    "REVIEW": "REVIEW", "PARTIAL": "REVIEW", "SKELETON": "SKELETON",
    "ARCHIVED": "ARCHIVED", "NOT_STARTED": "NOT_STARTED",
}


def normalize_status(raw: Any) -> str:
    if raw is None: return "NOT_STARTED"
    text = str(raw).upper()
    if text in STATUS_MAP: return STATUS_MAP[text]
    if "BLOCK" in text or "NOT_TESTABLE" in text: return "BLOCKED"
    if "PASS" in text or text is True: return "PASSED"
    if "FAIL" in text: return "FAILED"
    if "READY" in text: return "READY"
    return "REVIEW"


def _repo_path(path: Path) -> str:
    return path.relative_to(ROOT.parent).as_posix()


def _load(path: Path, warnings: list[dict]) -> dict | None:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(value, dict): raise ValueError("root must be an object")
        return value
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        warnings.append({"source": _repo_path(path), "error": type(exc).__name__})
        return None


def _payload(doc: dict | None) -> dict:
    value = (doc or {}).get("payload", doc or {})
    return value if isinstance(value, dict) else {}


class CompanyControlPlane:
    def build(self) -> dict:
        warnings: list[dict] = []
        docs = {key: _load(path, warnings) for key, path in SOURCES.items()}
        seq_catalog = sequence_research_read_model.CATALOG.build()
        strategy_catalog = strategy_pipeline_read_model.CATALOG.build()
        warnings.extend(seq_catalog.get("warnings", []))
        warnings.extend(strategy_catalog.get("warnings", []))
        now = datetime.now(timezone.utc).isoformat()

        artifacts = []
        for key, path in SOURCES.items():
            doc = docs[key]
            if doc is None: continue
            artifacts.append({
                "id": f"ART-{key.upper()}", "name": path.name, "type": "RESEARCH_ARTIFACT",
                "status": "AVAILABLE", "raw_status": "AVAILABLE", "normalized_status": "PASSED",
                "owner_type": "DEPARTMENT", "owner_id": "QUANT_RESEARCH" if key not in {"dataset_registry", "dataset_integrity"} else "DATA",
                "source_path": _repo_path(path), "sha": doc.get("canonical_sha256"),
                "created_at": doc.get("generated_at"), "updated_at": doc.get("generated_at"),
                "provenance": {"mode": "RESEARCH", "direct": True, "source_artifact": _repo_path(path)},
            })

        work_items = []
        for item in seq_catalog.get("sequences", {}).values():
            raw = item.get("implementation_status")
            work_items.append({
                "id": f"WI-{item['sequence_id']}", "name": item.get("description") or item["sequence_id"],
                "type": "SEQUENCE_RESEARCH", "department_id": "QUANT_RESEARCH",
                "raw_status": raw, "normalized_status": normalize_status(raw),
                "owner_type": "DEPARTMENT", "source_entity_id": item["sequence_id"],
                "gate_id": f"GATE-{item['sequence_id']}", "created_at": None, "updated_at": None,
                "provenance": item.get("provenance"),
            })

        gates = []
        for item in seq_catalog.get("sequences", {}).values():
            raw = item.get("implementation_status")
            gates.append({
                "id": f"GATE-{item['sequence_id']}", "name": "Sequence implementation readiness",
                "work_item_id": f"WI-{item['sequence_id']}", "raw_status": raw,
                "normalized_status": normalize_status(raw), "owner_type": "DEPARTMENT",
                "department_id": "SCIENTIFIC_QA", "limitations": item.get("limitations") or [],
                "provenance": item.get("provenance"), "created_at": None, "updated_at": None,
            })

        dependencies = []
        for wi in work_items:
            dependencies.append({"id": f"DEP-{wi['id']}-GATE", "source_id": wi["id"],
                                 "target_id": wi["gate_id"], "relation": "REVIEWED_BY",
                                 "status": wi["normalized_status"], "owner_type": "SYSTEM",
                                 "provenance": wi["provenance"], "created_at": None, "updated_at": None})

        datasets = []
        registry = docs.get("dataset_registry") or {}
        for dataset_id, record in registry.items():
            if not isinstance(record, dict): continue
            datasets.append({"id": dataset_id, "name": dataset_id, "status": record.get("status"),
                             "raw_status": record.get("status"), "normalized_status": normalize_status(record.get("status")),
                             "owner_type": "DEPARTMENT", "source": record.get("source"), "period": record.get("period"),
                             "row_count": record.get("row_count") or record.get("n_rows"), "hash": record.get("sha256") or record.get("hash"),
                             "split_status": record.get("split_status"), "quality_status": record.get("quality_status"),
                             "consumer_references": record.get("consumer_references"),
                             "provenance": {"mode": "RESEARCH", "direct": True, "source_artifact": _repo_path(SOURCES["dataset_registry"])},
                             "created_at": record.get("created_at"), "updated_at": record.get("updated_at")})

        leakage_counts: dict[str, int] = {}
        for item in seq_catalog.get("sequences", {}).values():
            label = item.get("semantic_leakage_status_after_correction") or "UNAVAILABLE"
            leakage_counts[label] = leakage_counts.get(label, 0) + 1
        holdout = _payload(docs.get("holdout_seal"))
        prereg = _payload(docs.get("seq0014_prereg"))
        qa_state = {
            "regression_status": None,
            "frozen_artifact_integrity": "AVAILABLE" if all(a.get("sha") for a in artifacts if a["owner_id"] == "QUANT_RESEARCH") else "PARTIAL",
            "leakage_status_counts": leakage_counts,
            "preregistration_status": prereg.get("preregistration_status"),
            "holdout_access_status": holdout.get("sealed_status"),
            "blocker_count": sum(g["normalized_status"] == "BLOCKED" for g in gates),
        }

        strategies = strategy_catalog["items"]

        departments = []
        for dept_id, name, raw_status in DEPARTMENT_SLOTS:
            related_work = [w for w in work_items if w["department_id"] == dept_id]
            related_artifacts = [a for a in artifacts if a["owner_id"] == dept_id]
            skeleton = raw_status == "SKELETON"
            departments.append({
                "id": dept_id, "name": name, "status": raw_status, "raw_status": raw_status,
                "normalized_status": "ACTIVE" if raw_status == "ACTIVE" else normalize_status(raw_status),
                "owner_type": "COMPANY", "purpose": self._purpose(dept_id),
                "capabilities": self._capabilities(dept_id), "accepted_inputs": self._contracts(dept_id)[0],
                "emitted_outputs": self._contracts(dept_id)[1], "required_dependencies": self._contracts(dept_id)[2],
                "work_item_count": len(related_work), "artifact_count": len(related_artifacts),
                "blocked_count": sum(w["normalized_status"] == "BLOCKED" for w in related_work),
                "skeleton": skeleton, "message": "no operational pipeline yet" if skeleton else None,
                "created_at": None, "updated_at": now,
                "provenance": {"mode": "DERIVED", "direct": False, "sources": sorted({a["source_path"] for a in related_artifacts})},
                "operational_state": qa_state if dept_id == "SCIENTIFIC_QA" else (
                    {"dataset_count": len(datasets)} if dept_id == "DATA" else (
                    {"strategy_count": len(strategies), "governance_conflict_count": strategy_catalog["governance_conflict_count"],
                     "meta_filter_ready_count": strategy_catalog["meta_filter_ready_count"]} if dept_id == "QUANT_RESEARCH" else (
                    {"state": "WAITING_FOR_QUANT_GATE", "execution_candidate_count": strategy_catalog["execution_candidate_count"]} if dept_id == "EXECUTION" else (
                    {"state": "WAITING_FOR_DEPLOYABLE_STRATEGIES", "deployable_strategy_count": 0} if dept_id == "RISK_PORTFOLIO" else None)))),
            })

        return {"company": {"id": "NEXUS", "name": "NEXUS", "status": "ACTIVE", "owner_type": "PRIVATE",
                              "created_at": None, "updated_at": now, "provenance": {"mode": "DERIVED", "direct": False}},
                "departments": departments, "work_items": work_items, "artifacts": artifacts, "gates": gates,
                "dependencies": dependencies, "datasets": datasets, "strategies": strategies, "warnings": warnings}

    @staticmethod
    def _purpose(dept):
        return {"DATA":"Versioned datasets and integrity evidence.", "QUANT_RESEARCH":"Canonical sequence research and formalization.",
                "SCIENTIFIC_QA":"Read-only scientific gates and integrity review.", "COMPUTE_INFRA":"Existing application, scripts and delivery infrastructure.",
                "EXECUTION":"Runtime execution domain.", "RISK_PORTFOLIO":"Risk and portfolio governance.",
                "KNOWLEDGE_INTELLIGENCE":"Canonical research memory and provenance."}[dept]

    @staticmethod
    def _capabilities(dept):
        return {"DATA":["dataset_registry", "integrity_projection"], "QUANT_RESEARCH":["sequence_registry", "research_read_model"],
                "SCIENTIFIC_QA":["leakage_projection", "readiness_gates", "holdout_status"],
                "COMPUTE_INFRA":["backend", "frontend", "research_scripts", "ci"], "EXECUTION":[], "RISK_PORTFOLIO":[],
                "KNOWLEDGE_INTELLIGENCE":["library", "knowledge_browser"]}[dept]

    @staticmethod
    def _contracts(dept):
        return {"DATA":(["source_data"],["dataset_version", "provenance"],[]),
                "QUANT_RESEARCH":(["dataset_version", "hypothesis"],["research_artifact", "strategy_evidence_status", "research_gate_status"],["DATA"]),
                "SCIENTIFIC_QA":(["research_artifact"],["review_status", "gate_status"],["QUANT_RESEARCH"]),
                "COMPUTE_INFRA":(["source_code", "configuration"],["application_build", "ci_result"],[]),
                "EXECUTION":(["quant_gate_passed", "runtime_configuration"],["execution_telemetry"],["QUANT_RESEARCH", "COMPUTE_INFRA"]),
                "RISK_PORTFOLIO":(["execution_telemetry"],["risk_state"],["EXECUTION"]),
                "KNOWLEDGE_INTELLIGENCE":(["research_artifact", "review_status"],["canonical_knowledge"],["QUANT_RESEARCH", "SCIENTIFIC_QA"])}[dept]

    def department(self, department_id: str):
        model = self.build(); dept = next((d for d in model["departments"] if d["id"] == department_id), None)
        if not dept: return None
        return {**dept, "active_work_items": [w for w in model["work_items"] if w["department_id"] == department_id],
                "recent_artifacts": [a for a in model["artifacts"] if a["owner_id"] == department_id],
                "gates": [g for g in model["gates"] if g["department_id"] == department_id or (department_id == "QUANT_RESEARCH" and g["work_item_id"].startswith("WI-"))],
                "datasets": model["datasets"] if department_id == "DATA" else [],
                "dependencies": [d for d in model["dependencies"] if d["source_id"].startswith("WI-")],
                "strategies": model["strategies"] if department_id == "QUANT_RESEARCH" else []}

    def overview(self):
        model = self.build()
        return {"company": model["company"], "departments": model["departments"],
                "active_work": [w for w in model["work_items"] if w["normalized_status"] in {"ACTIVE", "READY", "REVIEW"}],
                "blockers": [w for w in model["work_items"] if w["normalized_status"] == "BLOCKED"],
                "pending_gates": [g for g in model["gates"] if g["normalized_status"] not in {"PASSED", "ARCHIVED"}],
                "recent_artifacts": model["artifacts"][-8:], "dependencies": model["dependencies"],
                "warnings": model["warnings"]}


CONTROL_PLANE = CompanyControlPlane()
