#!/usr/bin/env python3
"""Phase 7.33 Decision Card — exploratory habitat replay (NOT promotable)."""
from __future__ import annotations

import json
import os
import sys

PHASE_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(PHASE_DIR, "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase6_6"))
from canonical_utils import load_json, save_json, wrap_with_provenance  # noqa: E402


def build() -> dict:
    r = load_json(os.path.join(PHASE_DIR, "exploratory_replay_result_v1.json"))["payload"]
    assert r["promotable"] is False
    return {
        "phase": "7.33",
        "hypothesis_id": r["hypothesis_id"],
        "status": "EXPLORATORY_REPLAY_COMPLETE_NOT_PROMOTABLE",
        "promotable": False,
        "evidence_grade": "DISCOVERY_REUSE",
        "decision_exploratory": r["decision_exploratory"],
        "headline": (
            f"FVG_CONT BUY habitat exploratory: n_B={r['arm_B_buy_recipe_R']['n']}, "
            f"mean R={r['arm_B_buy_recipe_R']['mean_R']} vs A n={r['arm_A_baseline_recipe_R']['n']} "
            f"mean R={r['arm_A_baseline_recipe_R']['mean_R']}; BUY share={r['arm_A_buy_share']}; "
            f"proxy B−C CI95={r['arm_C_proxy']['paired_delta_iid_bootstrap_ci95']}. "
            "No promotion; confirmatory needs forward after 2026-06-30."
        ),
        "numbers": {
            "A_recipe": r["arm_A_baseline_recipe_R"],
            "B_recipe": r["arm_B_buy_recipe_R"],
            "B_month_ci": r["arm_B_month_block_ci95_recipe_R"],
            "C_proxy_paired_delta": r["arm_C_proxy"]["paired_delta_B_minus_C"],
            "C_proxy_ci": r["arm_C_proxy"]["paired_delta_iid_bootstrap_ci95"],
        },
        "prereg_commit_sha": r["prereg_commit_sha"],
        "next": r["next_confirmatory_step"],
        "not_ready_for_deploy": True,
        "not_an_edge_claim": True,
    }


def main() -> int:
    payload = build()
    doc = wrap_with_provenance(payload, "phase7_33_fvg_cont_habitat/build_decision_card.py")
    save_json(os.path.join(PHASE_DIR, "decision_card_v1.json"), doc)
    print(json.dumps({
        "status": payload["status"],
        "decision": payload["decision_exploratory"],
        "sha": doc["canonical_sha256"][:16],
    }))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
