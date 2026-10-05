"""Fail-closed verifier for scientific/component/defect separation."""
from __future__ import annotations

import hashlib
import json
from collections import Counter
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
REGISTRY = ROOT / "contracts" / "edge-validation-registry.json"
DEFECT_AUDIT = ROOT / "server/research_scripts/phase7/phase7_10/phase_7_10_final_synthesis_report_v1.json"
ALLOWED = {"UNVALIDATED", "CANDIDATE", "BORDERLINE", "VALIDATED", "FAILED", "DEFECT_BLOCKED", "FORWARD_REQUIRED"}
COMPONENT_ALLOWED = {"UNKNOWN", "PROMISING", "SUPPORTED", "WEAK", "REDUNDANT", "NOT_EVALUATED"}


def historical_defect_ids() -> set[str]:
    audit = json.loads(DEFECT_AUDIT.read_text(encoding="utf-8"))
    return set(audit["payload"]["q3_other_exposed_strategies"]["defect_confirmed"])


def verify(value: dict, *, audit_defects: set[str] | None = None) -> tuple[list[str], list[dict]]:
    errors, alerts, seen = [], [], set()
    for record in value.get("strategies", []):
        sid = record.get("strategy_id")
        status = record.get("standalone_edge_status")
        component_status = record.get("component_value_status")
        if sid in seen:
            errors.append(f"duplicate strategy_id: {sid}")
        seen.add(sid)
        if status not in ALLOWED:
            errors.append(f"{sid}: invalid standalone_edge_status {status}")
        if component_status not in COMPONENT_ALLOWED:
            errors.append(f"{sid}: invalid component_value_status {component_status}")
        if len(record.get("edge_validation_source", [])) != len(record.get("edge_validation_sha", [])):
            errors.append(f"{sid}: source/hash cardinality mismatch")
        if record.get("known_defects") and record.get("defect_status") in (None, "NONE_KNOWN"):
            alerts.append({"strategy_id": sid, "code": "KNOWN_DEFECT_WITHOUT_REMEDIATION_STATE"})
        if record.get("default_enabled") and status in {"FAILED", "DEFECT_BLOCKED", "UNVALIDATED"}:
            alerts.append({"strategy_id": sid, "code": "DEFAULT_ENABLED_" + status})
        if record.get("default_enabled") and record.get("defect_status") == "DEFECT_BLOCKED":
            alerts.append({"strategy_id": sid, "code": "DEFAULT_ENABLED_DEFECT_BLOCKED"})
        if status == "FAILED" and component_status is None:
            alerts.append({"strategy_id": sid, "code": "FAILED_WITHOUT_COMPONENT_VALUE_STATUS"})
        if (status == "DEFECT_BLOCKED" or record.get("defect_status") == "DEFECT_BLOCKED") and not record.get("needs_reimplementation_review"):
            alerts.append({"strategy_id": sid, "code": "DEFECT_BLOCKED_WITHOUT_REIMPLEMENTATION_REVIEW"})
        if record.get("potential_reusable_components") and not record.get("role_in_system"):
            alerts.append({"strategy_id": sid, "code": "COMPONENTS_WITHOUT_SYSTEM_ROLE"})
        if status == "VALIDATED" and not record.get("edge_validation_source"):
            alerts.append({"strategy_id": sid, "code": "VALIDATED_WITHOUT_PROVENANCE"})
        if component_status == "SUPPORTED" and not any(
                item.get("evidence_references") for item in record.get("potential_reusable_components", [])):
            alerts.append({"strategy_id": sid, "code": "SUPPORTED_COMPONENT_WITHOUT_EVIDENCE_REFERENCE"})
        latest = record.get("latest_relevant_note_date")
        if latest and record.get("edge_validation_date") and date.fromisoformat(latest) > date.fromisoformat(record["edge_validation_date"]):
            alerts.append({"strategy_id": sid, "code": "SCIENTIFIC_REGISTRY_STALE"})
    projected = {item["strategy_id"] for item in value.get("strategies", []) if item.get("known_defects")}
    for sid in sorted((audit_defects or set()) - projected):
        alerts.append({"strategy_id": sid, "code": "HISTORICAL_DEFECT_NOT_PROJECTED_REQUIRES_RECONCILIATION"})
    if any(item.get("strategy_id") == "SH_BMS_RTO_V2" and item.get("implementation_status") == "RESEARCH_ONLY"
           for item in value.get("strategies", [])):
        alerts.append({"strategy_id": "SH_BMS_RTO_V2", "code": "CODE_PRESENT_REGISTRY_RESEARCH_ONLY"})
    return errors, alerts


def verify_canonical_reconciliation(value: dict) -> list[str]:
    try:
        from research_scripts.edge_validation_registry_v1.build_edge_validation_registry import CANONICAL_STANDALONE, RECONCILIATION_COMMIT, SOURCES
    except ModuleNotFoundError:  # direct script execution from repository root
        from build_edge_validation_registry import CANONICAL_STANDALONE, RECONCILIATION_COMMIT, SOURCES
    errors = []
    records = {item["strategy_id"]: item for item in value.get("strategies", [])}
    for sid, expected in CANONICAL_STANDALONE.items():
        if records.get(sid, {}).get("standalone_edge_status") != expected:
            errors.append(f"{sid}: scientific state stale; expected {expected}")
    source = ROOT / SOURCES["RECONCILIATION"]
    expected_sha = hashlib.sha256(source.read_bytes()).hexdigest()
    reconciliation = value.get("base_registry", {}).get("reconciliation_input", {})
    if reconciliation.get("source_sha256") != expected_sha:
        errors.append("canonical reconciliation content hash is stale")
    if reconciliation.get("source_commit") != RECONCILIATION_COMMIT:
        errors.append("canonical reconciliation commit is stale")
    return errors


def main() -> int:
    value = json.loads(REGISTRY.read_text(encoding="utf-8"))
    errors, alerts = verify(value, audit_defects=historical_defect_ids())
    errors.extend(verify_canonical_reconciliation(value))
    standalone = Counter(item["standalone_edge_status"] for item in value["strategies"])
    defects = Counter(item["defect_status"] for item in value["strategies"])
    components = Counter(item["component_value_status"] for item in value["strategies"])
    print(json.dumps({"valid": not errors, "standalone_counts": dict(sorted(standalone.items())),
                      "defect_counts": dict(sorted(defects.items())),
                      "component_counts": dict(sorted(components.items())),
                      "errors": errors, "alerts": alerts}, indent=2))
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
