"""Artifact-backed Research Control Plane V2 (read-only).

The catalog projects canonical artifacts verbatim and adds only navigation,
freshness and descriptive counts. It never derives scientific verdicts.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import strategy_census_read_model

ROOT = Path(__file__).resolve().parent
P7 = ROOT / "research_scripts" / "phase7"
P726 = P7 / "phase7_26"
TENANT = {"tenant_id": "tenant-1", "ea_instance_id": None, "account_scope_id": None}

SOURCES = {
    "experiments": P726 / "experiment_registry_v1.json",
    "hypotheses": P726 / "hypothesis_registry_v1.json",
    "data_exposure": P726 / "data_exposure_registry_v1.json",
    "learning_packets": P726 / "cross_strategy_learning_packets_v1.json",
    "failure_map": P726 / "failure_map_v1.json",
    "priority_queue": P726 / "research_priority_queue_v1.json",
    "synthesis": P726 / "cross_strategy_synthesis_v1.json",
}

COLLECTION_KEYS = {
    "experiments": "experiments", "hypotheses": "hypotheses",
    "data_exposure": "records", "learning_packets": "packets",
    "failure_map": "strategies", "priority_queue": "ranked_candidates",
}

def _repo(path: Path) -> str:
    return path.relative_to(ROOT.parent).as_posix()

def _load(path: Path, warnings: list[dict]) -> dict | None:
    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(doc, dict) or not isinstance(doc.get("payload"), dict):
            raise ValueError("root and payload must be objects")
        return doc
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        warnings.append({"source": _repo(path), "error": type(exc).__name__})
        return None

def _items(payload: dict, key: str) -> list[dict]:
    value = payload.get(key, [])
    if isinstance(value, list): return [item for item in value if isinstance(item, dict)]
    if isinstance(value, dict):
        return [{"strategy_identity": identity, **item} for identity, item in value.items() if isinstance(item, dict)]
    return []

def _prov(path: Path, doc: dict | None) -> dict:
    return {"source_artifact": _repo(path), "canonical_sha256": doc.get("canonical_sha256") if doc else None,
            "generated_at": doc.get("generated_at") if doc else None, "mode": "CANONICAL_ARTIFACT", **TENANT}

class ResearchControlPlane:
    def build(self) -> dict:
        warnings: list[dict] = []
        docs = {name: _load(path, warnings) for name, path in SOURCES.items()}
        catalogs: dict[str, list[dict]] = {}
        for name, key in COLLECTION_KEYS.items():
            doc = docs[name]
            rows = _items(doc["payload"], key) if doc else []
            catalogs[name] = [{**row, "provenance": _prov(SOURCES[name], doc), **TENANT} for row in rows]

        experiments = catalogs["experiments"]
        hypotheses = catalogs["hypotheses"]
        failures = catalogs["failure_map"]
        exposures = catalogs["data_exposure"]
        census = strategy_census_read_model.CATALOG.build()
        warnings.extend({**warning, "scope": "STRATEGY_CENSUS"} for warning in census.get("warnings", []))
        census_by_id = {row["strategy_id"]: row for row in census.get("items", [])}
        strategy_ids = sorted(
            set(census_by_id)
            | {str(row.get("strategy_identity")) for row in experiments + failures if row.get("strategy_identity")}
        )
        strategy_summaries = []
        for strategy in strategy_ids:
            exps = [row for row in experiments if row.get("strategy_identity") == strategy]
            packet = next((row for row in catalogs["learning_packets"] if row.get("strategy_identity") == strategy), None)
            failure = next((row for row in failures if row.get("strategy_identity") == strategy), None)
            census_row = census_by_id.get(strategy, {})
            strategy_summaries.append({
                "strategy_id": strategy, "experiment_count": len(exps),
                "canonical_identity": census_row.get("strategy_id") or strategy,
                "aliases": census_row.get("aliases", []),
                "variant_of": census_row.get("variant_of"),
                "lineage_notes": census_row.get("lineage_notes", []),
                "implementation_identity": census_row.get("implementation"),
                "integrity_status": census_row.get("audit_coverage"),
                "scientific_evidence": census_row.get("scientific_evidence"),
                "known_defects": census_row.get("known_defects"),
                "deployment_eligibility": census_row.get("operational_eligibility"),
                "latest_verdict": exps[-1].get("verdict") if exps else None,
                "failure_modes": [mode.get("mode") for mode in (failure or {}).get("failure_modes", []) if isinstance(mode, dict)],
                "oos_behavior": (packet or {}).get("oos_behavior"), "fidelity": (packet or {}).get("fidelity"),
                "mvc": (packet or {}).get("capital_efficiency"),
                "freshness": {"projected_through": "7.26", "canonical_research_through": "7.26", "state": "CURRENT",
                              "reason": "Safety Net registries projected directly.", "source_artifact": _repo(P726 / "cross_strategy_learning_packets_v1.json")},
                **TENANT,
            })
        overview = {
            "census_count": census.get("declared_count") or census.get("count"),
            "experiment_count": len(experiments), "hypothesis_count": len(hypotheses),
            "dataset_count": len(exposures), "strategy_count": len(strategy_ids),
            "failure_mode_count": sum(len(row.get("failure_modes", [])) for row in failures),
            "forward_or_oos_experiments": sum("OOS" in str(row.get("verdict", "")).upper() or "FORWARD" in str(row.get("method", "")).upper() for row in experiments),
            "implementation_defect_strategies": sum(any(m.get("mode") == "IMPLEMENTATION_DEFECT" for m in row.get("failure_modes", []) if isinstance(m, dict)) for row in failures),
            "integrity_check_strategies": len({row.get("strategy_identity") for row in experiments if "INTEGRITY" in str(row.get("experiment_id", "")) or "FIX_CAUSAL" in str(row.get("experiment_id", ""))}),
            "edge_validated_count": sum(str(row.get("verdict", "")).startswith("EDGE_VALIDATED") for row in experiments),
            "insufficient_evidence_count": sum("INSUFFICIENT" in str(row.get("verdict", "")) for row in experiments),
            "oos_negative_or_inconclusive_count": None,
            "fresh_canonical_dataset_count": None,
            "verdict_counts": {verdict: sum(row.get("verdict") == verdict for row in experiments) for verdict in sorted({row.get("verdict") for row in experiments if row.get("verdict")})},
            "freshness": "CURRENT" if not warnings else "PARTIAL", "projected_through": "7.26", "canonical_research_through": "7.26",
            "provenance": [_prov(path, docs[name]) for name, path in SOURCES.items()], **TENANT,
        }
        return {"overview": overview, "strategies": strategy_summaries, "catalogs": catalogs,
                "synthesis": docs["synthesis"]["payload"] if docs["synthesis"] else None,
                "visual_audits": self._visual_audits(), "runs": self._runs(), "forward_validation": self._forward(experiments),
                "mvc": self._mvc(), "warnings": warnings, **TENANT}

    def catalog(self, name: str) -> dict:
        model = self.build(); items = model["catalogs"].get(name, [])
        return {"items": items, "count": len(items), "warnings": model["warnings"], **TENANT}

    def _visual_audits(self) -> list[dict]:
        rows = []
        for path in sorted(P7.glob("phase7_*/**/charts/*.svg")):
            stem = path.stem.lower(); stage = next((s for s in ("stagea", "stageb", "stagec") if s in stem), None)
            rows.append({"id": path.stem, "stage": stage.upper() if stage else "NOT_AVAILABLE", "source": _repo(path),
                         "fidelity_grade": "NOT_AVAILABLE", "event_id": path.stem.split("_stage")[0], "run_id": None, **TENANT})
        return rows

    def visual_path(self, artifact_id: str) -> Path | None:
        for item in self._visual_audits():
            if item["id"] == artifact_id:
                path = (ROOT.parent / item["source"]).resolve()
                if path.is_file() and path.is_relative_to(P7.resolve()): return path
        return None

    def _runs(self) -> list[dict]:
        rows = []
        for path in sorted(P7.glob("phase7_*/runs/**/*.manifest.json")):
            try: data = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError): continue
            rows.append({"run_id": data.get("run_id") or path.stem.replace(".manifest", ""), "strategy": data.get("strategy"),
                         "date_range": data.get("date_range"), "code_sha": data.get("code_sha"), "config_hash": data.get("config_hash"),
                         "source": _repo(path), "reconciliation_status": data.get("reconciliation_status"), **TENANT})
        return rows

    def _forward(self, experiments: list[dict]) -> list[dict]:
        return [{"strategy": row.get("strategy_identity"), "experiment_id": row.get("experiment_id"), "verdict": row.get("verdict"),
                 "period": row.get("period"), "run_id": row.get("run_id"), "no_tuning": "no tuning" in str(row.get("method", "")).lower(),
                 "provenance": row.get("provenance"), **TENANT} for row in experiments
                if "OOS" in str(row.get("experiment_id", "")).upper() or "FORWARD" in str(row.get("method", "")).upper()]

    def _mvc(self) -> list[dict]:
        rows = []
        for path in sorted(P7.glob("phase7_*/minimum_viable_capital_v1.json")):
            warnings: list[dict] = []; doc = _load(path, warnings)
            if doc: rows.append({"source": _repo(path), "payload": doc["payload"], "provenance": _prov(path, doc), **TENANT})
        return rows

CONTROL_PLANE = ResearchControlPlane()
