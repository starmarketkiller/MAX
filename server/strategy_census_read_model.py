"""Read-only Phase 7.11 census joined to the Phase 7.10 implementation audit.

The census categories overlap by design. Presence, implementation, registry
recognition, enablement configuration, audit coverage, evidence and operational
eligibility are kept as separate fields and are never collapsed into one state.
"""
from __future__ import annotations

import json
from pathlib import Path

from path_provenance import repo_safe_path

ROOT = Path(__file__).resolve().parent
P7 = ROOT / "research_scripts" / "phase7"
SOURCES = {
    "census": P7 / "phase7_11" / "complete_strategy_census_v1.json",
    "summary": P7 / "phase7_11" / "census_summary_v1.json",
    "audit": P7 / "phase7_10" / "stateful_strategy_static_audit_v1.json",
}


def _repo_path(path: Path) -> str:
    return repo_safe_path(path, ROOT.parent)


def _load(path: Path, warnings: list[dict]) -> dict | None:
    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(doc, dict) or not isinstance(doc.get("payload"), dict):
            raise ValueError("root and payload must be objects")
        return doc
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        warnings.append({"source": _repo_path(path), "error": type(exc).__name__, "scope": "STRATEGY_CENSUS"})
        return None


class StrategyCensusCatalog:
    def build(self) -> dict:
        warnings: list[dict] = []
        docs = {name: _load(path, warnings) for name, path in SOURCES.items()}
        census_payload = docs["census"]["payload"] if docs["census"] else {}
        summary_payload = docs["summary"]["payload"] if docs["summary"] else {}
        audit_payload = docs["audit"]["payload"] if docs["audit"] else {}
        audit_rows = {
            row.get("strategy"): row for row in audit_payload.get("candidates", [])
            if isinstance(row, dict) and row.get("strategy")
        }
        rows = []
        for raw in census_payload.get("census_rows", []):
            if not isinstance(raw, dict) or not raw.get("canonical_strategy_id"):
                warnings.append({"source": _repo_path(SOURCES["census"]), "error": "MalformedCensusRow", "scope": "STRATEGY_CENSUS"})
                continue
            strategy_id = raw["canonical_strategy_id"]
            audit = audit_rows.get(strategy_id)
            rows.append({
                "strategy_id": strategy_id,
                "aliases": raw.get("aliases") if isinstance(raw.get("aliases"), list) else [],
                "variant_of": raw.get("variant_of"),
                "lineage_notes": raw.get("lineage_notes") if isinstance(raw.get("lineage_notes"), list) else [],
                "census_presence": True,
                "implementation": {"live_mql5": raw.get("live_mql5"), "python": raw.get("python_implementation")},
                "registry_recognition": raw.get("registry_presence") if isinstance(raw.get("registry_presence"), dict) else {},
                "enablement_configuration": {"raw_status": raw.get("current_status"), "profile": raw.get("profile_presence"), "selector": raw.get("selector_presence"), "effective_enabled": None},
                "audit_coverage": {"covered": audit is not None, "classification": audit.get("classification") if audit else None, "status": audit.get("status") if audit else None, "evidence": audit.get("evidence") if audit else None},
                "scientific_evidence": raw.get("evidence_status"),
                "known_defects": raw.get("known_implementation_defects"),
                "parity_status": raw.get("known_parity_status"),
                "operational_eligibility": None,
                "registry_gap": raw.get("registry_gap_UNKNOWN_STRATEGY_REGISTRY_GAP"),
                "registry_correction_note": raw.get("live_mql5_correction_note"),
                "provenance": {
                    "mode": "RESEARCH", "direct": True, "phase": "7.11",
                    "source": _repo_path(SOURCES["census"]),
                    "sha256": docs["census"].get("canonical_sha256") if docs["census"] else None,
                    "audit_source": _repo_path(SOURCES["audit"]) if audit else None,
                    "audit_sha256": docs["audit"].get("canonical_sha256") if audit and docs["audit"] else None,
                },
            })
        declared_total = summary_payload.get("output_1_total_unique_identities")
        return {
            "items": rows, "count": len(rows), "declared_count": declared_total,
            "counts_by_category": summary_payload.get("output_2_counts_by_category") or {},
            "categories_are_overlapping": True,
            "category_warning": "Categories overlap and must not be summed as disjoint populations. Lack of audit coverage does not mean SAFE.",
            "source_discrepancies": summary_payload.get("output_4_source_presence_discrepancies") or [],
            "possibly_excluded": summary_payload.get("output_5_possibly_excluded_from_prior_audits") or [],
            "provenance": {
                name: {"source": _repo_path(path), "sha256": docs[name].get("canonical_sha256") if docs[name] else None,
                       "phase": docs[name]["payload"].get("phase") if docs[name] else None}
                for name, path in SOURCES.items()
            },
            "warnings": warnings,
        }

    def get(self, strategy_id: str) -> dict | None:
        wanted = strategy_id.upper()
        return next((item for item in self.build()["items"] if item["strategy_id"].upper() == wanted), None)


CATALOG = StrategyCensusCatalog()
