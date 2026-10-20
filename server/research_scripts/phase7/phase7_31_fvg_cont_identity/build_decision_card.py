#!/usr/bin/env python3
"""Phase 7.31 Decision Card — FVG_CONT identity audit (not an edge claim)."""
from __future__ import annotations

import json
import os
import sys

PHASE_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(PHASE_DIR, "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase6_6"))
from canonical_utils import load_json, save_json, wrap_with_provenance  # noqa: E402


def build() -> dict:
    m = load_json(os.path.join(PHASE_DIR, "fvg_cont_identity_map_v1.json"))["payload"]
    decision = "ISOLATION_READY"
    # Safety: if map claimed canonical CTF, flip
    if "CONTAMINATION class does NOT apply" not in m["mql5_canonical"]["tf_guard"]:
        decision = "CTF_DEFECT_ON_CANONICAL"
    if "ONLY the canonical gate" not in m["collector_gates"]["isolation_implication"]:
        decision = "VARIANT_CONTAMINATION_BLOCKS_ISOLATION"

    return {
        "phase": "7.31",
        "hypothesis_id": m["hypothesis_id"],
        "status": "IDENTITY_AUDIT_COMPLETE",
        "decision": decision,
        "promotable": False,
        "live_ready": False,
        "not_an_edge_claim": True,
        "not_ready_for_deploy": True,
        "headline": (
            "FVG_CONT canonical path is STATELESS, selector=8 isolable, variants are "
            "SEPARATE_FUNCTION (not OB_MIT-style wrappers). Python exit uses "
            "_liq_sweep_target ≠ MQL5 DefaultSLTP — forbid Python PF promotion. "
            "FVG_MIT_WINDOW alone carries CTF zone-state risk."
        ),
        "numbers": {
            "canonical_selector": 8,
            "variant_count": len(m["variants_sharing_enum_STRAT_FVG_CONT"]),
            "python_exit_mismatch": True,
            "canonical_ctf_risk": False,
        },
        "prereg_commit_sha": m["prereg_commit_sha"],
        "identity_map_sha_ref": "fvg_cont_identity_map_v1.json",
        "next": (
            "Commit a NEW MT5 diagnostic prereg (separate hypothesis_id), then run "
            "selector=8 GOLD H4 isolation on research PC via "
            "launch_fvg_cont_isolation_diagnostic.py. Size the window for trade density / "
            "power — do not reuse the 3-week LIQ_SWEEP confirmatory window that yielded n=0."
        ),
        "explicit_non_goals_honored": True,
    }


def main() -> int:
    payload = build()
    doc = wrap_with_provenance(payload, "phase7_31_fvg_cont_identity/build_decision_card.py")
    save_json(os.path.join(PHASE_DIR, "decision_card_v1.json"), doc)
    print(json.dumps({
        "decision": payload["decision"],
        "promotable": payload["promotable"],
        "sha": doc["canonical_sha256"][:16],
    }))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
