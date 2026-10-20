#!/usr/bin/env python3
"""Phase 7.29 Decision Card — LIQ_SWEEP OOS failure mode."""
from __future__ import annotations

import json
import os
import sys

PHASE_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(PHASE_DIR, "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase6_6"))
from canonical_utils import load_json, save_json, wrap_with_provenance  # noqa: E402


def build() -> dict:
    diag = load_json(os.path.join(PHASE_DIR, "liq_sweep_oos_failure_mode_v1.json"))["payload"]
    supported = [h["id"] for h in diag["hypotheses"] if h.get("supported")]
    rejected = [h["id"] for h in diag["hypotheses"] if h.get("rejected")]
    return {
        "phase": "7.29",
        "strategy": "LIQ_SWEEP",
        "question": diag["question"],
        "decision": diag["decision"],
        "primary_failure_mode": diag["primary_failure_mode"],
        "supported_hypotheses": supported,
        "rejected_hypotheses": rejected,
        "headline": (
            "OOS (−0.52R/trade, n=6) is explained by habitat + setup-mix shift: "
            "IS was 93% BUY inside a +119% gold bull; OOS drew 50% SELL and all "
            "SELLS stopped out while gold kept rising (+12%). Not an execution bug."
        ),
        "numbers": {
            "IS_mean_R": diag["windows"]["IS"]["stats"]["mean_R"],
            "OOS_mean_R": diag["windows"]["OOS"]["stats"]["mean_R"],
            "IS_gold_ret_pct": diag["windows"]["IS"]["gold_drift"]["ret_pct"],
            "OOS_gold_ret_pct": diag["windows"]["OOS"]["gold_drift"]["ret_pct"],
            "oos_buy_only_mean_R": diag["oos_buy_only_mean_R"],
        },
        "edge_implication": diag["edge_implication"],
        "registry_action": (
            "Keep standalone_edge_status=CANDIDATE; add validation note "
            "REGIME_CONDITIONAL; do not promote; do not mark FAILED from n=6 alone."
        ),
        "next_experiment": diag["recommended_next_experiment"],
        "not_ready_for_deploy": True,
        "not_an_edge_claim": True,
    }


def main():
    payload = build()
    doc = wrap_with_provenance(payload, "phase7_29_liq_sweep_oos_failure/build_decision_card.py")
    save_json(os.path.join(PHASE_DIR, "liq_sweep_oos_failure_decision_card_v1.json"), doc)
    print(json.dumps({"decision": payload["decision"], "sha": doc["canonical_sha256"][:16]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
