#!/usr/bin/env python3
"""Phase 7.28 — batch Decision Card for remaining cross-TF state defects."""
from __future__ import annotations

import json
import os
import sys

PHASE_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(PHASE_DIR, "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase6_6"))
from canonical_utils import load_json, save_json, wrap_with_provenance  # noqa: E402

STRAT_FILES = {
    "BAR_UPDN": "MQL5/Include/NEXUS_v1/NXS_Strategies.mqh",
    "PIVOT_WICK": "MQL5/Include/NEXUS_v1/NXS_Strategies.mqh",
    "PMAX": "MQL5/Include/NEXUS_v1/NXS_Strategies.mqh",
    "BB_SQUEEZE": "MQL5/Include/NEXUS_v1/NXS_Strategies.mqh",
    "TSI": "MQL5/Include/NEXUS_v1/NXS_Strategies.mqh",
    "SH_BMS_RTO": "MQL5/Include/NEXUS_v1/NXS_Strategies_SMC.mqh",
    "SH_BMS_RTO_V2": "MQL5/Include/NEXUS_v1/NXS_Strategies_SMC.mqh",
    "SILVER_BULLET": "MQL5/Include/NEXUS_v1/NXS_Strategies_SMC.mqh",
    "RANGE_FADE": "MQL5/Include/NEXUS_v1/NXS_Strategies_Institutional.mqh",
}


def _has_guard(text: str, name: str) -> bool:
    needle = f'if(tf != NXS_Profile_TF("{name}"))'
    needle2 = f'if(execTF != NXS_Profile_TF("{name}"))'
    return needle in text or needle2 in text


def build() -> dict:
    bar = load_json(os.path.join(PHASE_DIR, "bar_updn_abc_impact_v1.json"))["payload"]
    bbs = load_json(os.path.join(PHASE_DIR, "bb_squeeze_abc_impact_v1.json"))["payload"]
    guards = {}
    for sid, rel in STRAT_FILES.items():
        text = open(os.path.join(ROOT, rel), encoding="utf-8").read()
        guards[sid] = _has_guard(text, sid)

    silver_profile = 'if(name == "SILVER_BULLET")' in open(
        os.path.join(ROOT, "MQL5/Include/NEXUS_v1/NXS_StrategyProfiles.mqh"), encoding="utf-8"
    ).read()

    return {
        "phase": "7.28",
        "title": "DEFECT_IMPACT_BATCH_V1",
        "principle": (
            "Same-feed A/B where offline data allows; TF-scoped early guard "
            "(validated on BREAKOUT_ACC/ORDER_BLOCK/TSI) applied to all remaining "
            "DEFECT_CONFIRMED persistent-state strategies. Remediation ≠ edge."
        ),
        "measured": {
            "BAR_UPDN": {
                "decision": bar["decision"],
                "A_signals": bar["stream_A_contaminated_signals_on_profile_pass"],
                "B_signals": bar["stream_B_tf_scoped_signals"],
                "suppression_vs_scoped": bar["suppression_vs_scoped"],
                "artifact": "bar_updn_abc_impact_v1.json",
            },
            "BB_SQUEEZE": {
                "decision": bbs["decision"],
                "A_signals": bbs["stream_A_contaminated_signals_on_profile_pass"],
                "B_signals": bbs["stream_B_tf_scoped_signals"],
                "suppression_vs_scoped": bbs["suppression_vs_scoped"],
                "artifact": "bb_squeeze_abc_impact_v1.json",
                "caveat": bbs["data"]["higher_tf_note"],
            },
        },
        "structural_guard_applied": guards,
        "silver_bullet_profile_tf_fixed": silver_profile,
        "tsi_reconcile": {
            "prior_registry": "DEFECT_BLOCKED",
            "code_before_this_phase": "guard already present (Phase 7.18)",
            "action": "registry → REMEDIATED (recover only)",
        },
        "not_mt5_event_parity": True,
        "not_an_edge_claim": True,
        "production_status": "NO-GO unchanged",
        "next": [
            "Keep DEFECT_BLOCKED strategies default_enabled=false until dedicated forward/edge work",
            "Optional: MT5 A/B/C for SH_BMS_RTO / SILVER_BULLET / PMAX when Tester automation exists",
            "Resume shortlist edge work (FVG_CONT/LIQ_SWEEP/…) — not these defect repairs",
        ],
    }


def main():
    payload = build()
    doc = wrap_with_provenance(payload, "phase7_28_defect_impact_batch/build_decision_batch.py")
    save_json(os.path.join(PHASE_DIR, "defect_impact_batch_decision_v1.json"), doc)
    missing = [k for k, v in payload["structural_guard_applied"].items() if not v]
    print(json.dumps({
        "guards_ok": not missing,
        "missing_guards": missing,
        "bar_updn": payload["measured"]["BAR_UPDN"]["decision"],
        "bb_squeeze": payload["measured"]["BB_SQUEEZE"]["decision"],
        "sha": doc["canonical_sha256"][:16],
    }))
    return 1 if missing else 0


if __name__ == "__main__":
    raise SystemExit(main())
