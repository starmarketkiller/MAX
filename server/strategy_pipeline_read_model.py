"""Canonical, read-only strategy pipeline projection for the Company Control Plane.

Only explicit Phase 7.7A/7.7B facts are projected.  Code registry status,
scientific evidence and meta-filter readiness deliberately remain separate.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent
P77A = ROOT / "research_scripts" / "phase7" / "phase7_7a"
P77B = ROOT / "research_scripts" / "phase7" / "phase7_7b"

SOURCES = {
    "lifecycle": P77A / "strategy_lifecycle_registry_v1.json",
    "evidence": P77A / "strategy_evidence_matrix_v1.json",
    "meta_filter_eligibility": P77A / "strategy_meta_filter_eligibility_v1.json",
    "meta_filter_gate": P77B / "strategy_meta_filter_gate_v1.json",
    "structural_semantics_correction": P77B / "structural_eligibility_semantics_correction_v1.json",
    "missing_field_semantics": P77B / "missing_field_semantics_refinement_v1.json",
}

PIPELINE_STAGES = [
    "EVENT_RESEARCH", "STRATEGY_FORMALIZATION", "STRATEGY_VALIDATION",
    "META_FILTER_RESEARCH", "EXECUTION_VALIDATION", "PORTFOLIO_RISK",
]


def _repo_path(path: Path) -> str:
    return path.relative_to(ROOT.parent).as_posix()


def _load(path: Path, warnings: list[dict]) -> dict | None:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(value, dict):
            raise ValueError("root must be an object")
        payload = value.get("payload")
        if not isinstance(payload, dict):
            raise ValueError("payload must be an object")
        return value
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        warnings.append({"source": _repo_path(path), "error": type(exc).__name__})
        return None


def _payload(doc: dict | None) -> dict:
    return doc["payload"] if isinstance(doc, dict) and isinstance(doc.get("payload"), dict) else {}


def _dict(value: Any) -> dict:
    return value if isinstance(value, dict) else {}


def _list(value: Any) -> list:
    return value if isinstance(value, list) else []


class StrategyPipelineCatalog:
    def build(self) -> dict:
        warnings: list[dict] = []
        docs = {name: _load(path, warnings) for name, path in SOURCES.items()}
        lifecycle = _payload(docs["lifecycle"])
        evidence = _payload(docs["evidence"])
        eligibility = _payload(docs["meta_filter_eligibility"])
        gate = _payload(docs["meta_filter_gate"])
        correction = _payload(docs["structural_semantics_correction"])
        field_refinement = _payload(docs["missing_field_semantics"])

        deep = _dict(lifecycle.get("deep_dive_candidates"))
        survey_rows = _list(_dict(lifecycle.get("full_registry_survey")).get("strategies"))
        survey = {row.get("strategy_id"): row for row in survey_rows if isinstance(row, dict) and row.get("strategy_id")}
        conflicts = _list(evidence.get("registry_status_vs_evidence_conflicts"))
        conflict_by_candidate = {}
        for item in conflicts:
            if not isinstance(item, dict):
                continue
            registry_id = item.get("registry_strategy_id")
            conflict_by_candidate[registry_id] = item
            if registry_id == "SAR":
                conflict_by_candidate["SAR_LIVE"] = item

        eligibility_by_id = _dict(eligibility.get("eligibility_by_candidate"))
        gate_by_id = _dict(gate.get("gate_results_by_candidate"))
        correction_by_id = _dict(correction.get("corrected_structural_status_by_candidate"))
        fields_by_id = _dict(field_refinement.get("per_candidate_field_classifications"))
        verdict_by_id = _dict(evidence.get("evidence_verdicts_by_candidate"))
        strategies = []
        for key in sorted(deep):
            raw = deep[key]
            if not isinstance(raw, dict):
                warnings.append({"source": _repo_path(SOURCES["lifecycle"]), "error": "MalformedStrategy", "strategy_id": key})
                continue
            # The object key is the stable registry identifier.  A few source
            # records carry a descriptive label in `strategy_id`; preserve it
            # separately rather than using it as an API identifier.
            strategy_id = key
            source_strategy_id = raw.get("strategy_id")
            conflict = conflict_by_candidate.get(strategy_id)
            registry_id = conflict.get("registry_strategy_id") if isinstance(conflict, dict) else strategy_id
            code = survey.get(registry_id, {})
            verdict_record = _dict(verdict_by_id.get(strategy_id))
            evidence_verdict = raw.get("evidence_verdict")
            is_refuted = verdict_record.get("is_refuted")
            if is_refuted is None:
                marker = raw.get("evidence_verdict_is_not_refuted")
                is_refuted = False if marker is True else None
            gate_record = _dict(gate_by_id.get(strategy_id))
            correction_record = _dict(correction_by_id.get(strategy_id))
            field_record = _dict(fields_by_id.get(strategy_id))
            field_semantics = []
            for field_name, semantics in _dict(field_record.get("field_classifications")).items():
                if not isinstance(semantics, dict):
                    continue
                field_semantics.append({
                    "field": field_name,
                    "field_knowledge": semantics.get("field_knowledge"),
                    "requirement_role": semantics.get("requirement_role"),
                    "note": semantics.get("note"),
                })
            old_eligibility = _dict(eligibility_by_id.get(strategy_id))
            code_status = code.get("status")
            governance_status = "GOVERNANCE_CONFLICT" if code_status == "ACTIVE" and is_refuted is True else None
            classification = raw.get("classification")
            completed = ["EVENT_RESEARCH"]
            if classification in {"FULL_STRATEGY_SPEC", "PARTIAL_STRATEGY"}:
                completed.append("STRATEGY_FORMALIZATION")
            current_stage = "STRATEGY_VALIDATION"
            readiness = gate_record.get("meta_filter_research_readiness")
            gate_passed = gate_record.get("meta_filter_ready_gate_passed")
            structural_status = correction_record.get("corrected_structural_status") or gate_record.get("meta_filter_structural_eligibility")
            structural_limitation = correction_record.get("evidence_quote_from_7_7a_rationale")
            blocked_stage = "META_FILTER_RESEARCH" if readiness in {
                "REFUTED_INAPPROPRIATE", "EXECUTION_FAILED_INAPPROPRIATE", "NOT_READY"
            } else None
            next_stage = "META_FILTER_RESEARCH" if gate_passed is True else (
                None if readiness in {"REFUTED_INAPPROPRIATE", "EXECUTION_FAILED_INAPPROPRIATE"}
                else "STRATEGY_VALIDATION"
            )
            strategies.append({
                "strategy_id": strategy_id,
                "source_strategy_id": source_strategy_id,
                "lifecycle_class": classification,
                "implementation_status": code_status,
                "code_registry_status": code_status,
                "code_registry_strategy_id": registry_id if code else None,
                "live_implementation": code.get("live_implementation"),
                "research_implementation": code.get("research_implementation"),
                "evidence_status": evidence_verdict,
                "evidence_verdict": evidence_verdict,
                "evidence_is_refuted": is_refuted,
                "evidence_ladder": _dict(raw.get("evidence_ladder")),
                "governance_status": governance_status,
                "governance_conflict": conflict,
                "meta_filter_eligibility": old_eligibility.get("eligibility") or raw.get("meta_filter_eligibility"),
                "meta_filter_structural_eligibility": structural_status,
                "meta_filter_structural_eligibility_raw_7_7b": gate_record.get("meta_filter_structural_eligibility"),
                "structural_status_correction_applied": correction_record.get("correction_applied"),
                "structural_missing_field_taxonomy": correction_record.get("missing_field_taxonomy_class"),
                "structural_limitation": structural_limitation,
                "field_semantics": field_semantics,
                "field_semantics_refined_status": field_record.get("refined_structural_status"),
                "field_semantics_status_changed": field_record.get("status_changed_by_this_refinement"),
                "meta_filter_research_readiness": readiness,
                "meta_filter_ready": gate_passed,
                "meta_filter_blocker": structural_limitation or gate_record.get("structural_blocker"),
                "blockers": [value for value in [structural_limitation or gate_record.get("structural_blocker"), gate_record.get("next_required_evidence")] if value],
                "failure_memory_links": _list(raw.get("failure_memory_links")),
                "current_stage": current_stage,
                "completed_stages": completed,
                "blocked_stage": blocked_stage,
                "next_required_stage": next_stage,
                "next_required_evidence": gate_record.get("next_required_evidence"),
                "deployable": None,
                "execution_candidate": False,
                "source_artifact": raw.get("source_artifact"),
                "provenance": {
                    "mode": "RESEARCH", "direct": False,
                    "sources": [_repo_path(path) for name, path in SOURCES.items() if docs[name] is not None],
                    "canonical_sha256": {name: docs[name].get("canonical_sha256") for name in SOURCES if docs[name] is not None},
                },
            })

        return {
            "items": strategies,
            "count": len(strategies),
            "governance_conflict_count": sum(item["governance_status"] == "GOVERNANCE_CONFLICT" for item in strategies),
            "meta_filter_ready_count": sum(item["meta_filter_ready"] is True for item in strategies),
            "execution_candidate_count": 0,
            "deployable_count": 0,
            "pipeline_stages": PIPELINE_STAGES,
            "warnings": warnings,
        }

    def get(self, strategy_id: str) -> dict | None:
        return next((item for item in self.build()["items"] if item["strategy_id"] == strategy_id), None)


CATALOG = StrategyPipelineCatalog()
