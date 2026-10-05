"""Build the scientific/component registry without changing runtime behavior."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
BASE = ROOT / "contracts" / "strategy-registry.json"
OUTPUT = ROOT / "contracts" / "edge-validation-registry.json"
GENERATED_AT = "2026-10-06T00:01:09+02:00"
RECONCILIATION_COMMIT = "364deec32476d35509dbc97d5a8d3263cd9d44e1"

SOURCES = {
    "MACD_3Y": "vault/01-Trading/NEXUS - First Serious 3Y Validation SAR MACD.md",
    "LIQ_725": "vault/01-Trading/NEXUS - Phase 7.25 LIQ_SWEEP Edge Validation V1.md",
    "ORDER_722": "vault/01-Trading/NEXUS - Phase 7.22 ORDER_BLOCK Edge Validation V1.md",
    "FOUNDATION": "vault/01-Trading/NEXUS - Market Intelligence Foundation.md",
    "COST_REEVAL": "vault/01-Trading/NEXUS - 37 Strategy Cost-Calibrated Re-Evaluation.md",
    "DEFECT_AUDIT": "server/research_scripts/phase7/phase7_10/phase_7_10_final_synthesis_report_v1.json",
    "RECONCILIATION": "docs/TRADING_EDGE_STATUS_RECONCILIATION_V1.md",
}

# Part 4 ("Tabella finale per Codex") is the projection authority.
CANONICAL_STANDALONE = {
    "ADX_RSI": "CANDIDATE", "BAR_UPDN": "UNVALIDATED", "BB_SQUEEZE": "UNVALIDATED",
    "BOLLINGER": "BORDERLINE", "BREAKOUT_ACC": "FORWARD_REQUIRED", "CRT": "FAILED",
    "EMA_PULLBACK": "CANDIDATE", "FVG_CONT": "CANDIDATE", "ICHIMOKU": "CANDIDATE",
    "JUDAS_SWING": "CANDIDATE", "LIQ_SWEEP": "CANDIDATE", "LONDON_BO": "BORDERLINE",
    "MACD": "FAILED", "MALAYSIAN_SNR": "CANDIDATE", "NY_REVERSAL": "BORDERLINE",
    "ORDER_BLOCK": "FORWARD_REQUIRED", "PIVOT_WICK": "UNVALIDATED", "PMAX": "UNVALIDATED",
    "RANGE_FADE": "UNVALIDATED", "RSI_DIV": "FAILED", "SAR": "BORDERLINE",
    "SH_BMS_RTO": "UNVALIDATED", "SH_BMS_RTO_V2": "UNVALIDATED",
    "SILVER_BULLET": "UNVALIDATED", "STRUCT_REACT": "CANDIDATE", "TSI": "UNVALIDATED",
    "Z_SCORE_BREAKOUT": "CANDIDATE", "ELLIOTT": "UNVALIDATED", "SWING_FALSEBREAK": "UNVALIDATED",
}
AMBIGUOUS = {"AMD_REVERSAL", "OTE_CONT", "PO3", "SMS_BMS_RTO", "WEEKLY_EXP"}
FORWARD_STATUS = {
    "BREAKOUT_ACC": "INSUFFICIENT", "ORDER_BLOCK": "INSUFFICIENT",
    "LIQ_SWEEP": "NEGATIVE_INSUFFICIENT", "MACD": "COMPLETE_NEGATIVE",
}
DEFECTS = {
    "BREAKOUT_ACC": ("COOLDOWN_STATE_CONTAMINATION", "REMEDIATED"),
    "ORDER_BLOCK": ("STATE_MACHINE_CONTAMINATION", "REMEDIATED"),
    "BAR_UPDN": ("COOLDOWN_STATE_CONTAMINATION", "DEFECT_BLOCKED"),
    "PIVOT_WICK": ("COOLDOWN_STATE_CONTAMINATION", "DEFECT_BLOCKED"),
    "PMAX": ("RECURSIVE_VALUE_STATE_CONTAMINATION", "DEFECT_BLOCKED"),
    "RANGE_FADE": ("STATE_MACHINE_CONTAMINATION", "DEFECT_BLOCKED"),
    "SH_BMS_RTO_V2": ("STATE_MACHINE_CONTAMINATION", "DEFECT_BLOCKED"),
    "BB_SQUEEZE": ("CROSS_TIMEFRAME_STATE_CONTAMINATION", "DEFECT_BLOCKED"),
    "SH_BMS_RTO": ("CROSS_TIMEFRAME_STATE_CONTAMINATION", "DEFECT_BLOCKED"),
    "SILVER_BULLET": ("CROSS_TIMEFRAME_STATE_CONTAMINATION", "DEFECT_BLOCKED"),
    "TSI": ("CROSS_TIMEFRAME_STATE_CONTAMINATION", "DEFECT_BLOCKED"),
    "FVG_CONT": ("SLRECLAIM_ACCOUNT_PROTECTION_BYPASS", "UNKNOWN_REMEDIATION"),
    "BOLLINGER": ("CROSS_TIMEFRAME_STATE_CONTAMINATION", "SUSPECT"),
}
EVIDENCE_NOTES = {
    "ADX_RSI": "Regime-confounded in Phase 7.27; standalone confidence reduced, not falsified.",
    "BOLLINGER": "Prior confirmation invalidated by buy-and-hold comparison; contamination remains suspect only.",
    "BREAKOUT_ACC": "Defect remediated; CI95 includes zero and forward sample remains insufficient.",
    "FVG_CONT": "Research candidate; SLReclaim remediation is not confirmed.",
    "LIQ_SWEEP": "OOS n=6 is negative but insufficient for final refutation.",
    "MACD": "SERIOUS_VALIDATION_FAIL; two of three years negative.",
    "ORDER_BLOCK": "Defect remediated; CI95 includes zero and forward evidence remains insufficient.",
    "SAR": "SERIOUS_VALIDATION_BORDERLINE; this supersedes the incomplete placeholder UNVALIDATED state.",
}

ROLE_VOCABULARY = [
    "REGIME_DETECTOR", "CONTEXT_FEATURE", "LOCATION_FEATURE", "MOMENTUM_FEATURE",
    "VOLATILITY_FEATURE", "LIQUIDITY_EVENT", "ENTRY_TRIGGER", "CONFIRMATION", "FILTER",
    "RISK_FEATURE", "EXIT_FEATURE", "POSITION_MANAGEMENT", "RESEARCH_ONLY",
]
COMPONENT_VALUE_VOCABULARY = [
    "UNKNOWN", "PROMISING", "SUPPORTED", "WEAK", "REDUNDANT", "NOT_EVALUATED",
]


def component(name: str, role: str, *references: str) -> dict:
    return {"component": name, "role": role, "evidence_status": "NOT_EVALUATED",
            "evidence_references": list(references)}


# Mechanics visible in implementation/notes; not evidence of component edge.
COMPONENT_PROJECTIONS = {
    "ORDER_BLOCK": {"roles": ["LOCATION_FEATURE", "ENTRY_TRIGGER"], "components": [
        component("order_block_zone_location", "LOCATION_FEATURE", "MQL5/Include/NEXUS_v1/NXS_Strategies.mqh", SOURCES["ORDER_722"]),
        component("order_block_retest_trigger", "ENTRY_TRIGGER", "MQL5/Include/NEXUS_v1/NXS_Strategies.mqh", SOURCES["ORDER_722"])]},
    "LIQ_SWEEP": {"roles": ["LIQUIDITY_EVENT", "ENTRY_TRIGGER"], "components": [
        component("liquidity_sweep_detection", "LIQUIDITY_EVENT", "MQL5/Include/NEXUS_v1/NXS_Strategies.mqh", SOURCES["LIQ_725"]),
        component("sweep_reversal_trigger", "ENTRY_TRIGGER", "MQL5/Include/NEXUS_v1/NXS_Strategies.mqh", SOURCES["LIQ_725"])]},
    "ADX_RSI": {"roles": ["REGIME_DETECTOR", "MOMENTUM_FEATURE", "ENTRY_TRIGGER"], "components": [
        component("adx_trend_strength", "REGIME_DETECTOR", "MQL5/Include/NEXUS_v1/NXS_Strategies.mqh", SOURCES["FOUNDATION"]),
        component("rsi_momentum_condition", "MOMENTUM_FEATURE", "MQL5/Include/NEXUS_v1/NXS_Strategies.mqh", SOURCES["FOUNDATION"]),
        component("adx_rsi_entry_trigger", "ENTRY_TRIGGER", "MQL5/Include/NEXUS_v1/NXS_Strategies.mqh")]},
    "FVG_CONT": {"roles": ["LOCATION_FEATURE", "ENTRY_TRIGGER"], "components": [
        component("fair_value_gap_location", "LOCATION_FEATURE", "MQL5/Include/NEXUS_v1/NXS_Strategies.mqh", SOURCES["COST_REEVAL"]),
        component("fvg_continuation_trigger", "ENTRY_TRIGGER", "MQL5/Include/NEXUS_v1/NXS_Strategies.mqh", SOURCES["COST_REEVAL"])]},
    "MACD": {"roles": ["MOMENTUM_FEATURE", "CONFIRMATION", "ENTRY_TRIGGER"], "components": [
        component("macd_momentum", "MOMENTUM_FEATURE", "MQL5/Include/NEXUS_v1/NXS_Strategies.mqh", SOURCES["MACD_3Y"]),
        component("macd_cross_trigger", "ENTRY_TRIGGER", "MQL5/Include/NEXUS_v1/NXS_Strategies.mqh", SOURCES["MACD_3Y"])]},
    "SAR": {"roles": ["MOMENTUM_FEATURE", "ENTRY_TRIGGER"], "components": [
        component("parabolic_sar_trend_direction", "MOMENTUM_FEATURE", "MQL5/Include/NEXUS_v1/NXS_Strategies.mqh", SOURCES["MACD_3Y"]),
        component("sar_flip_trigger", "ENTRY_TRIGGER", "MQL5/Include/NEXUS_v1/NXS_Strategies.mqh", SOURCES["MACD_3Y"])]},
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build() -> dict:
    base = json.loads(BASE.read_text(encoding="utf-8"))
    reconciliation_path = SOURCES["RECONCILIATION"]
    records = []
    for runtime in base["strategies"]:
        sid = runtime["strategy_id"]
        projection = COMPONENT_PROJECTIONS.get(sid)
        defect = DEFECTS.get(sid)
        defect_status = defect[1] if defect else "NONE_KNOWN"
        notes = [EVIDENCE_NOTES[sid]] if sid in EVIDENCE_NOTES else []
        if sid in AMBIGUOUS:
            notes.append("Canonical reconciliation marks the evidence AMBIGUOUS; represented conservatively as UNVALIDATED.")
        elif sid not in CANONICAL_STANDALONE:
            notes.append("Canonical reconciliation groups this identity among strategies without a scientific decision.")
        records.append({
            "strategy_id": sid, "implementation_status": runtime["status"],
            "default_enabled": runtime["default_enabled"],
            "standalone_edge_status": CANONICAL_STANDALONE.get(sid, "UNVALIDATED"),
            "component_value_status": "NOT_EVALUATED" if projection else "UNKNOWN",
            "role_in_system": projection["roles"] if projection else [],
            "potential_reusable_components": projection["components"] if projection else [],
            "needs_reimplementation_review": defect_status in {"DEFECT_BLOCKED", "UNKNOWN_REMEDIATION"},
            "edge_validation_date": "2026-10-06",
            "edge_validation_source": [reconciliation_path],
            "edge_validation_sha": [sha256(ROOT / reconciliation_path)],
            "edge_validation_evidence_grade": None,
            "known_defects": ([{"defect_id": defect[0], "source": reconciliation_path,
                                 "remediation_state": defect_status}] if defect else []),
            "defect_status": defect_status,
            "forward_validation_status": FORWARD_STATUS.get(sid, "UNKNOWN"),
            "latest_relevant_note_date": "2026-10-06", "validation_notes": notes,
        })
    return {
        "schema_version": 1, "generated_at": GENERATED_AT,
        "base_registry": {
            "source": "contracts/strategy-registry.json", "sha256": sha256(BASE),
            "strategy_count": len(records), "runtime_behavior_changed": False,
            "reconciliation_input": {
                "name": "TRADING_EDGE_STATUS_RECONCILIATION_V1",
                "artifact_availability": "CANONICAL_SOURCE_VISIBLE",
                "source": reconciliation_path, "source_sha256": sha256(ROOT / reconciliation_path),
                "source_commit": RECONCILIATION_COMMIT,
                "handling": "Part 4 final table is authoritative; AMBIGUOUS is conservatively represented as UNVALIDATED with an explicit note.",
            }},
        "status_vocabulary": ["UNVALIDATED", "CANDIDATE", "BORDERLINE", "VALIDATED", "FAILED", "DEFECT_BLOCKED", "FORWARD_REQUIRED"],
        "component_value_vocabulary": COMPONENT_VALUE_VOCABULARY,
        "role_vocabulary": ROLE_VOCABULARY, "strategies": records,
    }


if __name__ == "__main__":
    value = build()
    OUTPUT.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"wrote {OUTPUT} ({len(value['strategies'])} strategies)")
