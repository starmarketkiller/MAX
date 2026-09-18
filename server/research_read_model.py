"""Canonical, read-only Research catalog built from versioned Phase 5-6 artifacts."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Iterable


H006_ID = "H006_LIQUIDITY_SWEEP_RECLAIM_TRUE_HOLDOUT"
H006_EXPERIMENT_ID = "EXP-P6-H006-TRUE-HOLDOUT"
H006_DATASET_ID = "DATASET-P6-H006-HOLDOUT-20220204-20230203"
H006_EVIDENCE_ID = "EVIDENCE-P6-H006-TRUE-HOLDOUT"
H006_EDGE_ID = "EC-LIQUIDITY_SWEEP_RECLAIM"
H006_DECISION_ID = "DECISION-P6-H006"

RELATION_TYPES = frozenset({
    "HYPOTHESIS_TESTED_BY_EXPERIMENT",
    "EXPERIMENT_USES_DATASET",
    "EXPERIMENT_PRODUCES_EVIDENCE",
    "EVIDENCE_SUPPORTS",
    "EVIDENCE_REFUTES",
    "EVIDENCE_LIMITS",
    "EDGE_COMPONENT_DERIVED_FROM_HYPOTHESIS",
    "DECISION_CARD_SUMMARIZES",
})


def _sha256(path: Path) -> str | None:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError:
        return None


def _source(root: Path, path: Path, direct: bool = True) -> dict[str, Any]:
    try:
        relative = path.relative_to(root).as_posix()
    except ValueError:
        relative = path.name
    return {
        "source_file": relative,
        "source_hash": _sha256(path),
        "source_version": None,
        "mode": "DIRECT" if direct else "DERIVED",
    }


def _relation(kind: str, source_id: str, target_id: str) -> dict[str, str]:
    return {"type": kind, "source_id": source_id, "target_id": target_id}


class ResearchCatalog:
    """Build a deterministic catalog; bad individual artifacts become warnings."""

    def __init__(self, root: Path | None = None):
        module_dir = Path(__file__).resolve().parent
        supplied_root = root.resolve() if root is not None else None
        if ((root is None and (module_dir / "research_scripts").is_dir()) or
                (supplied_root is not None and (supplied_root / "research_scripts").is_dir())):
            # Production image: COPY server/ ./ places the package at /app.
            self.root = supplied_root or module_dir
            server_root = self.root
        else:
            # Repository checkout and tests: artifacts live below <root>/server.
            self.root = (root or module_dir.parent).resolve()
            server_root = self.root / "server"
        self.phase55 = server_root / "research_scripts" / "phase5_5"
        self.phase6 = server_root / "research_scripts" / "phase6"

    def _json(self, path: Path, warnings: list[dict[str, str]]) -> Any:
        if not path.is_file():
            warnings.append({"code": "MISSING_ARTIFACT", "source_file": self._rel(path)})
            return None
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            warnings.append({
                "code": "MALFORMED_ARTIFACT",
                "source_file": self._rel(path),
                "detail": type(exc).__name__,
            })
            return None

    def _rel(self, path: Path) -> str:
        try:
            return path.relative_to(self.root).as_posix()
        except ValueError:
            return path.name

    @staticmethod
    def _dedupe(items: Iterable[dict[str, Any]], entity_type: str,
                warnings: list[dict[str, str]]) -> list[dict[str, Any]]:
        by_id: dict[str, dict[str, Any]] = {}
        for item in items:
            entity_id = item.get("id") if isinstance(item, dict) else None
            if not isinstance(entity_id, str) or not entity_id:
                warnings.append({"code": "INVALID_RECORD", "entity_type": entity_type})
                continue
            if entity_id in by_id:
                warnings.append({"code": "DUPLICATE_ID", "entity_type": entity_type,
                                 "entity_id": entity_id})
                continue
            by_id[entity_id] = item
        return [by_id[key] for key in sorted(by_id)]

    @staticmethod
    def _base(entity_id: str, entity_type: str, title: str | None, status: str | None,
              source: dict[str, Any], version: Any = None, created_at: Any = None,
              updated_at: Any = None) -> dict[str, Any]:
        return {
            "id": entity_id,
            "entity_type": entity_type,
            "title": title,
            "status": status,
            "provenance": "RESEARCH",
            "source": {**source, "source_version": version},
            "version": version,
            "created_at": created_at,
            "updated_at": updated_at,
            "relations": [],
            "limitations": [],
            "conflicts": [],
            "uncertainty": None,
            "grade_cap_reason": None,
            "validation_integrity": None,
        }

    def build(self) -> dict[str, Any]:
        warnings: list[dict[str, str]] = []
        hypothesis_path = self.phase55 / "hypothesis_registry_v1.json"
        experiment_path = self.phase55 / "experiment_registry_v1.json"
        dataset_path = self.phase55 / "dataset_version_v1.json"
        spec_path = self.phase6 / "H006_frozen_spec.json"
        result_path = self.phase6 / "h006_primary_result.json"
        declaration_path = self.phase6 / "true_holdout_declaration.json"
        robustness_path = self.phase6 / "h006_robustness_diagnostics.json"

        hypothesis_raw = self._json(hypothesis_path, warnings)
        experiment_raw = self._json(experiment_path, warnings)
        dataset_raw = self._json(dataset_path, warnings)
        spec = self._json(spec_path, warnings)
        result_doc = self._json(result_path, warnings)
        declaration = self._json(declaration_path, warnings)
        robustness = self._json(robustness_path, warnings)

        hypotheses: list[dict[str, Any]] = []
        if isinstance(hypothesis_raw, list):
            for raw in hypothesis_raw:
                if not isinstance(raw, dict):
                    warnings.append({"code": "INVALID_RECORD", "entity_type": "Hypothesis"})
                    continue
                entity_id = raw.get("hypothesis_id")
                if not isinstance(entity_id, str) or not entity_id:
                    warnings.append({"code": "INVALID_RECORD", "entity_type": "Hypothesis"})
                    continue
                item = self._base(entity_id, "Hypothesis", raw.get("family_or_name") or entity_id,
                                  raw.get("status"), _source(self.root, hypothesis_path), 1,
                                  raw.get("created_at"), raw.get("created_at"))
                item.update({
                    "hypothesis": raw.get("condition_desc") or raw.get("primary_outcome"),
                    "primary_outcome": raw.get("primary_outcome"),
                    "evidence_grade": "E2" if entity_id == H006_ID and isinstance(spec, dict) else None,
                    "evidence_grade_provenance": self._rel(spec_path)
                    if entity_id == H006_ID and isinstance(spec, dict) else None,
                    "true_holdout_performed": isinstance(result_doc, dict)
                    if entity_id == H006_ID else None,
                    "promoted_to_e3": False
                    if entity_id == H006_ID and isinstance(result_doc, dict) else None,
                    "metrics": {},
                    "execution_status": "NOT_TESTED" if entity_id == H006_ID else None,
                })
                if entity_id == H006_ID:
                    primary = result_doc.get("primary_result", {}) if isinstance(result_doc, dict) else {}
                    item["status"] = primary.get("VERDICT") or raw.get("status")
                    item["status_detail"] = raw.get("status")
                    item["metrics"] = {
                        "delta_p_holdout": primary.get("delta_p"),
                        "delta_e_holdout_mfe_atr": primary.get("delta_e_mfe_atr"),
                        "ci_overlap": (not primary.get("ci95_non_overlapping"))
                        if primary.get("ci95_non_overlapping") is not None else None,
                        "buy_delta_p": (primary.get("buy") or {}).get("delta_p_vs_overall_baseline"),
                        "sell_delta_p_diagnostic": (primary.get("sell") or {}).get("delta_p_vs_overall_baseline"),
                    }
                    item["relations"].append(_relation(
                        "HYPOTHESIS_TESTED_BY_EXPERIMENT", entity_id, H006_EXPERIMENT_ID))
                    item["limitations"] = [
                        "Holdout effect below the preregistered minimum material effect.",
                        "SELL asymmetry is post-hoc diagnostic only and is not a validated edge.",
                        "Execution feasibility was not tested because the holdout did not pass.",
                    ]
                    item["conflicts"] = ["BUY delta is negative while aggregate delta is positive."]
                    item["uncertainty"] = {
                        "ci_overlap": item["metrics"]["ci_overlap"],
                        "bootstrap_ci95": [
                            (robustness.get("bootstrap_delta_p", {})
                             if isinstance(robustness, dict) else {}).get("ci95_low"),
                            (robustness.get("bootstrap_delta_p", {})
                             if isinstance(robustness, dict) else {}).get("ci95_high"),
                        ] if isinstance(robustness, dict) else None,
                    }
                    item["grade_cap_reason"] = "true holdout BORDERLINE, no E3 promotion"
                    item["validation_integrity"] = "TRUE_HOLDOUT_PERFORMED_BORDERLINE"
                hypotheses.append(item)
        elif hypothesis_raw is not None:
            warnings.append({"code": "INVALID_ARTIFACT_SHAPE", "entity_type": "Hypothesis"})
        hypotheses = self._dedupe(hypotheses, "Hypothesis", warnings)

        experiments: list[dict[str, Any]] = []
        if isinstance(experiment_raw, list):
            for raw in experiment_raw:
                if not isinstance(raw, dict) or not isinstance(raw.get("experiment_id"), str):
                    warnings.append({"code": "INVALID_RECORD", "entity_type": "Experiment"})
                    continue
                entity_id = raw["experiment_id"]
                item = self._base(entity_id, "Experiment", raw.get("description"), "COMPLETED",
                                  _source(self.root, experiment_path), 1)
                item.update({"code_version": raw.get("code_version_commit"),
                             "split_definition": raw.get("split_definition"),
                             "execution_assumptions": raw.get("execution_assumptions")})
                for hypothesis_id in raw.get("hypothesis_ids") or []:
                    item["relations"].append(_relation(
                        "HYPOTHESIS_TESTED_BY_EXPERIMENT", hypothesis_id, entity_id))
                dataset_ref = raw.get("dataset_version")
                if dataset_ref:
                    item["dataset_reference"] = dataset_ref
                experiments.append(item)
        elif experiment_raw is not None:
            warnings.append({"code": "INVALID_ARTIFACT_SHAPE", "entity_type": "Experiment"})

        if isinstance(spec, dict) and isinstance(result_doc, dict):
            p6 = self._base(H006_EXPERIMENT_ID, "Experiment", "H006 true temporal holdout",
                            "COMPLETED", _source(self.root, result_path, direct=False), 1,
                            spec.get("frozen_at"), declaration.get("declared_at")
                            if isinstance(declaration, dict) else None)
            p6.update({
                "code_version": None,
                "split_definition": (declaration.get("period") if isinstance(declaration, dict) else None),
                "execution_assumptions": spec.get("execution_status_ceiling"),
                "relations": [
                    _relation("HYPOTHESIS_TESTED_BY_EXPERIMENT", H006_ID, H006_EXPERIMENT_ID),
                    _relation("EXPERIMENT_USES_DATASET", H006_EXPERIMENT_ID, H006_DATASET_ID),
                    _relation("EXPERIMENT_PRODUCES_EVIDENCE", H006_EXPERIMENT_ID, H006_EVIDENCE_ID),
                ],
                "validation_integrity": "UNTOUCHED_TEMPORAL_HOLDOUT",
            })
            experiments.append(p6)
        experiments = self._dedupe(experiments, "Experiment", warnings)

        datasets: list[dict[str, Any]] = []
        if isinstance(dataset_raw, dict) and isinstance(dataset_raw.get("dataset_id"), str):
            dataset_id = dataset_raw["dataset_id"]
            item = self._base(dataset_id, "Dataset", dataset_id, "VERSIONED",
                              _source(self.root, dataset_path), dataset_raw.get("schema_version"),
                              dataset_raw.get("built_at"), dataset_raw.get("built_at"))
            item.update({"time_range": dataset_raw.get("time_range"),
                         "symbols": dataset_raw.get("symbols"),
                         "source_hashes": dataset_raw.get("source_hashes")})
            datasets.append(item)
        if isinstance(declaration, dict):
            item = self._base(H006_DATASET_ID, "Dataset", "H006 untouched temporal holdout",
                              "VERSIONED", _source(self.root, declaration_path, direct=False), 1,
                              declaration.get("declared_at"), declaration.get("declared_at"))
            item.update({"time_range": declaration.get("period"), "symbols": ["XAUUSD"],
                         "source_hashes": None, "limitations": declaration.get("known_limitations") or []})
            datasets.append(item)
        datasets = self._dedupe(datasets, "Dataset", warnings)

        evidence: list[dict[str, Any]] = []
        primary = result_doc.get("primary_result") if isinstance(result_doc, dict) else None
        if isinstance(primary, dict):
            item = self._base(H006_EVIDENCE_ID, "Evidence", "H006 true holdout evidence",
                              primary.get("VERDICT"), _source(self.root, result_path), 1,
                              spec.get("frozen_at") if isinstance(spec, dict) else None,
                              declaration.get("declared_at") if isinstance(declaration, dict) else None)
            item.update({
                "evidence_grade": "E2",
                "evidence_grade_provenance": self._rel(spec_path),
                "metrics": {"n": primary.get("n_events"), "delta_p": primary.get("delta_p"),
                            "delta_e_mfe_atr": primary.get("delta_e_mfe_atr"),
                            "ci_overlap": not primary.get("ci95_non_overlapping")
                            if primary.get("ci95_non_overlapping") is not None else None},
                "relations": [
                    _relation("EXPERIMENT_PRODUCES_EVIDENCE", H006_EXPERIMENT_ID, H006_EVIDENCE_ID),
                    _relation("EVIDENCE_LIMITS", H006_EVIDENCE_ID, H006_ID),
                ],
                "limitations": [primary.get("verdict_reason")],
                "conflicts": ["BUY instability; SELL result is post-hoc diagnostic only."],
                "uncertainty": {"bootstrap": robustness.get("bootstrap_delta_p")
                                if isinstance(robustness, dict) else None},
                "grade_cap_reason": "true holdout BORDERLINE, no E3 promotion",
                "validation_integrity": "UNTOUCHED_TEMPORAL_HOLDOUT",
            })
            evidence.append(item)
        evidence = self._dedupe(evidence, "Evidence", warnings)

        edges: list[dict[str, Any]] = []
        if any(item["id"] == H006_ID for item in hypotheses):
            item = self._base(H006_EDGE_ID, "EdgeComponent", "Liquidity Sweep Reclaim",
                              "CANDIDATE_LIMITED", _source(self.root, result_path, direct=False), 1)
            item.update({
                "evidence_grade": "E2",
                "execution_status": "NOT_TESTED",
                "relations": [_relation("EDGE_COMPONENT_DERIVED_FROM_HYPOTHESIS",
                                        H006_EDGE_ID, H006_ID)],
                "limitations": ["True holdout was BORDERLINE; component is not validated at E3."],
                "conflicts": ["BUY instability; SELL asymmetry is diagnostic, not a canonical edge."],
                "grade_cap_reason": "true holdout BORDERLINE, no E3 promotion",
                "validation_integrity": "TRUE_HOLDOUT_PERFORMED_BORDERLINE",
            })
            edges.append(item)

        decisions: list[dict[str, Any]] = []
        if primary:
            item = self._base(H006_DECISION_ID, "DecisionCard", "H006 evidence decision",
                              "NO_PROMOTION", _source(self.root, result_path, direct=False), 1)
            item.update({
                "decision": "RETAIN_E2",
                "summary": "True holdout is BORDERLINE; do not promote to E3 and do not test execution.",
                "relations": [_relation("DECISION_CARD_SUMMARIZES", H006_DECISION_ID, H006_ID)],
                "limitations": [primary.get("verdict_reason")],
                "grade_cap_reason": "true holdout BORDERLINE, no E3 promotion",
                "validation_integrity": "TRUE_HOLDOUT_PERFORMED_BORDERLINE",
            })
            decisions.append(item)

        entities = {
            "hypotheses": hypotheses,
            "experiments": experiments,
            "datasets": datasets,
            "evidence": evidence,
            "edge_components": edges,
            "decision_cards": decisions,
        }
        self._validate_relations(entities, warnings)
        return {"schema_version": "1.0", "entities": entities,
                "warnings": sorted(warnings, key=lambda x: json.dumps(x, sort_keys=True))}

    @staticmethod
    def _validate_relations(entities: dict[str, list[dict[str, Any]]],
                            warnings: list[dict[str, str]]) -> None:
        known = {item["id"] for group in entities.values() for item in group}
        # Phase 5 experiment dataset strings are legacy descriptions rather than stable IDs;
        # only explicit canonical relations are validated here.
        for group in entities.values():
            for item in group:
                valid = []
                for relation in item.get("relations", []):
                    if relation.get("type") not in RELATION_TYPES:
                        warnings.append({"code": "UNKNOWN_RELATION", "entity_id": item["id"]})
                        continue
                    missing = [value for value in (relation.get("source_id"), relation.get("target_id"))
                               if value not in known]
                    if missing:
                        warnings.append({"code": "BROKEN_RELATION", "entity_id": item["id"],
                                         "missing_id": missing[0]})
                        continue
                    valid.append(relation)
                item["relations"] = valid

    def list(self, kind: str, filters: dict[str, str | None] | None = None) -> dict[str, Any]:
        catalog = self.build()
        items = catalog["entities"][kind]
        filters = filters or {}
        for key in ("status", "evidence_grade", "hypothesis_id", "dataset_id"):
            value = filters.get(key)
            if not value:
                continue
            if key == "hypothesis_id":
                items = [item for item in items if item["id"] == value or any(
                    relation.get("source_id") == value or relation.get("target_id") == value
                    for relation in item.get("relations", []))]
            elif key == "dataset_id":
                items = [item for item in items if item["id"] == value or any(
                    relation.get("target_id") == value for relation in item.get("relations", []))]
            else:
                items = [item for item in items if str(item.get(key) or "").upper() == value.upper()]
        return {"schema_version": catalog["schema_version"], "items": items,
                "count": len(items), "warnings": catalog["warnings"]}

    def detail(self, kind: str, entity_id: str) -> dict[str, Any] | None:
        for item in self.build()["entities"][kind]:
            if item["id"] == entity_id:
                return item
        return None


CATALOG = ResearchCatalog()
