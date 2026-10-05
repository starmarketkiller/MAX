import json
from copy import deepcopy
from pathlib import Path

from orchestrator_v1.nxs_schema_validator import validate
from research_scripts.edge_validation_registry_v1.build_edge_validation_registry import (
    AMBIGUOUS, CANONICAL_STANDALONE, build)
from research_scripts.edge_validation_registry_v1.verify_edge_validation_registry import (
    historical_defect_ids, verify, verify_canonical_reconciliation)

ROOT = Path(__file__).resolve().parents[2]


def by_id(value, strategy_id):
    return next(item for item in value["strategies"] if item["strategy_id"] == strategy_id)


def test_registry_covers_all_runtime_identities_without_runtime_mutation():
    value = build()
    runtime = json.loads((ROOT / "contracts/strategy-registry.json").read_text(encoding="utf-8"))
    assert len(value["strategies"]) == len(runtime["strategies"]) == 83
    assert value["base_registry"]["runtime_behavior_changed"] is False
    assert {item["strategy_id"] for item in value["strategies"]} == {item["strategy_id"] for item in runtime["strategies"]}


def test_canonical_scientific_statuses_and_no_promotion():
    value = build()
    expected = {
        "MACD": "FAILED", "CRT": "FAILED", "RSI_DIV": "FAILED",
        "LIQ_SWEEP": "CANDIDATE", "ADX_RSI": "CANDIDATE",
        "BREAKOUT_ACC": "FORWARD_REQUIRED", "ORDER_BLOCK": "FORWARD_REQUIRED",
        "SAR": "BORDERLINE", "BOLLINGER": "BORDERLINE",
    }
    for sid, status in expected.items():
        assert by_id(value, sid)["standalone_edge_status"] == status
    assert all(item["standalone_edge_status"] != "VALIDATED" for item in value["strategies"])


def test_defect_and_remediation_projection_is_separate_from_edge():
    value = build()
    for sid in ("BREAKOUT_ACC", "ORDER_BLOCK"):
        assert by_id(value, sid)["defect_status"] == "REMEDIATED"
        assert by_id(value, sid)["standalone_edge_status"] == "FORWARD_REQUIRED"
    for sid in ("BAR_UPDN", "PIVOT_WICK", "PMAX", "RANGE_FADE", "SH_BMS_RTO_V2",
                "BB_SQUEEZE", "SH_BMS_RTO", "SILVER_BULLET", "TSI"):
        assert by_id(value, sid)["defect_status"] == "DEFECT_BLOCKED"
        assert by_id(value, sid)["needs_reimplementation_review"] is True
    assert by_id(value, "FVG_CONT")["defect_status"] == "UNKNOWN_REMEDIATION"
    assert by_id(value, "FVG_CONT")["needs_reimplementation_review"] is True


def test_schema_source_hashes_and_canonical_reconciliation_are_valid():
    value = build()
    schema = json.loads((ROOT / "contracts/edge-validation-registry.schema.json").read_text(encoding="utf-8"))
    assert validate(value, schema) == []
    assert verify_canonical_reconciliation(value) == []
    assert all(len(item["edge_validation_source"]) == len(item["edge_validation_sha"]) for item in value["strategies"])


def test_canonical_verifier_detects_stale_scientific_state():
    value = build()
    by_id(value, "SAR")["standalone_edge_status"] = "UNVALIDATED"
    assert "SAR: scientific state stale; expected BORDERLINE" in verify_canonical_reconciliation(value)


def test_ambiguous_and_grouped_absence_remain_explicitly_unvalidated():
    value = build()
    for sid in ("AMD_REVERSAL", "OTE_CONT", "PO3", "SMS_BMS_RTO", "WEEKLY_EXP"):
        record = by_id(value, sid)
        assert record["standalone_edge_status"] == "UNVALIDATED"
        assert "AMBIGUOUS" in " ".join(record["validation_notes"])
    grouped = next(item for item in value["strategies"]
                   if item["strategy_id"] not in CANONICAL_STANDALONE
                   and item["strategy_id"] not in AMBIGUOUS)
    assert grouped["standalone_edge_status"] == "UNVALIDATED"
    assert "without a scientific decision" in " ".join(grouped["validation_notes"])


def test_default_enabled_scientific_warnings_are_fail_closed():
    errors, alerts = verify(build())
    assert errors == []
    codes = {(item["strategy_id"], item["code"]) for item in alerts}
    assert ("MACD", "DEFAULT_ENABLED_FAILED") in codes
    assert ("TSI", "DEFAULT_ENABLED_DEFECT_BLOCKED") in codes
    assert ("AMD_REVERSAL", "DEFAULT_ENABLED_UNVALIDATED") in codes


def test_component_examples_are_separate_from_standalone_adjudication():
    value = build()
    expected = {
        "ORDER_BLOCK": {"LOCATION_FEATURE", "ENTRY_TRIGGER"},
        "LIQ_SWEEP": {"LIQUIDITY_EVENT", "ENTRY_TRIGGER"},
        "ADX_RSI": {"REGIME_DETECTOR", "MOMENTUM_FEATURE", "ENTRY_TRIGGER"},
        "FVG_CONT": {"LOCATION_FEATURE", "ENTRY_TRIGGER"},
        "MACD": {"MOMENTUM_FEATURE", "CONFIRMATION", "ENTRY_TRIGGER"},
        "SAR": {"MOMENTUM_FEATURE", "ENTRY_TRIGGER"},
    }
    for sid, roles in expected.items():
        record = by_id(value, sid)
        assert record["component_value_status"] == "NOT_EVALUATED"
        assert set(record["role_in_system"]) == roles
        assert record["potential_reusable_components"]
        assert all(item["evidence_references"] for item in record["potential_reusable_components"])
    assert by_id(value, "MACD")["standalone_edge_status"] == "FAILED"
    assert by_id(value, "MACD")["component_value_status"] == "NOT_EVALUATED"


def test_unknown_component_value_does_not_delete_or_promote_identities():
    value = build()
    unknown = [item for item in value["strategies"] if item["component_value_status"] == "UNKNOWN"]
    assert len(unknown) == 77
    assert all(not item["potential_reusable_components"] for item in unknown)


def test_verifier_detects_component_defect_and_provenance_inconsistencies():
    broken = deepcopy(build())
    by_id(broken, "MACD").pop("component_value_status")
    by_id(broken, "TSI")["needs_reimplementation_review"] = False
    by_id(broken, "SAR")["role_in_system"] = []
    order = by_id(broken, "ORDER_BLOCK")
    order["component_value_status"] = "SUPPORTED"
    for item in order["potential_reusable_components"]:
        item["evidence_references"] = []
    amd = by_id(broken, "AMD_REVERSAL")
    amd["standalone_edge_status"] = "VALIDATED"
    amd["edge_validation_source"] = []
    amd["edge_validation_sha"] = []
    _, alerts = verify(broken)
    codes = {(item["strategy_id"], item["code"]) for item in alerts}
    assert ("MACD", "FAILED_WITHOUT_COMPONENT_VALUE_STATUS") in codes
    assert ("TSI", "DEFECT_BLOCKED_WITHOUT_REIMPLEMENTATION_REVIEW") in codes
    assert ("SAR", "COMPONENTS_WITHOUT_SYSTEM_ROLE") in codes
    assert ("ORDER_BLOCK", "SUPPORTED_COMPONENT_WITHOUT_EVIDENCE_REFERENCE") in codes
    assert ("AMD_REVERSAL", "VALIDATED_WITHOUT_PROVENANCE") in codes


def test_known_defect_without_remediation_and_stale_science_are_reported():
    value = build()
    tsi = by_id(value, "TSI")
    tsi["defect_status"] = "NONE_KNOWN"
    tsi["latest_relevant_note_date"] = "2026-10-07"
    _, alerts = verify(value)
    codes = {item["code"] for item in alerts if item["strategy_id"] == "TSI"}
    assert "KNOWN_DEFECT_WITHOUT_REMEDIATION_STATE" in codes
    assert "SCIENTIFIC_REGISTRY_STALE" in codes


def test_all_phase_7_10_defects_are_projected_and_code_registry_mismatch_is_separate():
    value = build()
    _, alerts = verify(value, audit_defects=historical_defect_ids())
    assert not [item for item in alerts if item["code"] == "HISTORICAL_DEFECT_NOT_PROJECTED_REQUIRES_RECONCILIATION"]
    assert {"strategy_id": "SH_BMS_RTO_V2", "code": "CODE_PRESENT_REGISTRY_RESEARCH_ONLY"} in alerts
