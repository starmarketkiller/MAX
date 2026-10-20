#!/usr/bin/env python3
"""Phase 7.31 — static identity / variant map for FVG_CONT (code only)."""
from __future__ import annotations

import os
import sys

PHASE_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(PHASE_DIR, "..", "..", "..", ".."))
PREREG_REL = "server/research_scripts/phase7/phase7_31_fvg_cont_identity/preregistration_v1.json"

sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase7"))
sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase6_6"))
from canonical_utils import save_json, wrap_with_provenance  # noqa: E402
from engine.preregistration_provenance_guard import (  # noqa: E402
    assert_frozen_spec_committed_before_run,
)


def build() -> dict:
    prereg_sha = assert_frozen_spec_committed_before_run(ROOT, PREREG_REL)
    return {
        "phase": "7.31",
        "hypothesis_id": "FVG-CONT-IDENTITY-ISOLATION-001",
        "prereg_commit_sha": prereg_sha,
        "canonical_strategy_identity": "FVG_CONT",
        "mql5_canonical": {
            "function": "NXS_Strat_FVG()",
            "file": "MQL5/Include/NEXUS_v1/NXS_Strategies.mqh",
            "approx_lines": "1498-1522",
            "enum": "STRAT_FVG_CONT",
            "stratName": "FVG_CONT",
            "selector": 8,
            "enable_input": "InpStrat_FVG_CONT",
            "profile_tf": "PERIOD_H4 (NXS_Profile_TF)",
            "profile_sltp": "slMult=1.5, tpMult=6.0, htf=true, beR=InpFvgContBeR",
            "persistent_state": "NONE — function is STATELESS; uses iHigh/iLow/iClose + g_structH1.trend read-only",
            "tf_guard": (
                "NONE inside function. Collector still filters by NXS_Profile_TF at "
                "NXS_CollectAllSignals. No own lastFireTime / zone registry → "
                "CROSS_TIMEFRAME_STATE_CONTAMINATION class does NOT apply to canonical path."
            ),
            "trigger": (
                "3-candle FVG (low[1]>high[3] bull / high[1]<low[3] bear) AND "
                "external H1 structure trend g_structH1.trend aligned; optional "
                "InpUseSMCReactionGate via NXS_SMCReactionOK"
            ),
            "exit": "NXS_DefaultSLTP(s) — ATR multiples from profile (NOT dynamic liq target)",
        },
        "variants_sharing_enum_STRAT_FVG_CONT": [
            {
                "stratName": "IFVG",
                "function": "NXS_Strat_IFVG_Reversal → #define → NXR_Strat_IFVG_Reversal",
                "file": "NXS_Strategies_SMC.mqh / NXS_ReusePerformancePack.mqh",
                "selector": 18,
                "enable_input": "InpStrat_IFVG (default false)",
                "dependency_class": "SEPARATE_FUNCTION",
                "calls_canonical_FVG": False,
                "own_persistent_state": False,
                "notes": "Reversal / MSS logic; not a wrapper of NXS_Strat_FVG.",
            },
            {
                "stratName": "FVG_MIT",
                "function": "NXS_Strat_FVG_Mitigation → #define → NXR_Strat_FVG_Mitigation",
                "file": "NXS_Strategies_SMC.mqh / NXS_ReusePerformancePack.mqh",
                "selector": 19,
                "enable_input": "InpStrat_FVG_Mit",
                "dependency_class": "SEPARATE_FUNCTION",
                "calls_canonical_FVG": False,
                "own_persistent_state": False,
                "notes": "Mature-zone retest+reject; distinct from continuation gap.",
            },
            {
                "stratName": "FVG_MIT_WINDOW",
                "function": "NXS_Strat_FVG_Mitigation_Window",
                "file": "NXS_Strategies_SMC.mqh",
                "selector": 39,
                "enable_input": "InpStrat_FVG_MIT_WINDOW (default true)",
                "dependency_class": "SEPARATE_FUNCTION",
                "calls_canonical_FVG": False,
                "own_persistent_state": True,
                "state_symbols": [
                    "g_fvgMitWBull", "g_fvgMitWBear", "g_fvgMitWLastBar",
                    "NXS_FvgMitWindow_Update",
                ],
                "ctf_risk": (
                    "YES for THIS variant: persistent zone registry updated via NXS_EffTF() "
                    "without an early if(tf != NXS_Profile_TF(...)) return guard — same defect "
                    "class as BREAKOUT_ACC pre-fix. Does NOT infect canonical FVG_CONT path."
                ),
                "notes": "Profile_Enabled currently false for FVG_MIT_WINDOW in profiles map "
                         "(14/08 disable) — still relevant for integrity when re-enabled.",
            },
        ],
        "collector_gates": {
            "file": "MQL5/Experts/NEXUS_EA_v2.mq5",
            "FVG_CONT": "InpStrat_FVG_CONT && NXS_SelectorAllows(8) → NXS_Strat_FVG()",
            "IFVG": "InpStrat_IFVG && NXS_SelectorAllows(18)",
            "FVG_MIT": "InpStrat_FVG_Mit && NXS_SelectorAllows(19)",
            "FVG_MIT_WINDOW": "InpStrat_FVG_MIT_WINDOW && NXS_SelectorAllows(39)",
            "isolation_implication": (
                "InpStrategySelector=8 runs ONLY the canonical gate among these four. "
                "Unlike OB_MIT→ORDER_BLOCK nested selector trap (Phase 7.14), variants do not "
                "call NXS_Strat_FVG internally."
            ),
        },
        "python_parity_flags": {
            "dispatcher": "server/backtest.py STRATEGY_DISPATCH['FVG_CONT']=sig_fvg_cont_ext",
            "entry_alignment": (
                "PARTIALLY_ALIGNED — sig_fvg_cont_ext uses 3-candle gap + choch_ext trend; "
                "MQL5 uses g_structH1.trend + optional SMC reaction gate. Not byte-identical."
            ),
            "exit_mismatch": {
                "severity": "HIGH",
                "finding": (
                    "STRATEGY_TARGETS_OPTIN maps FVG_CONT → _liq_sweep_target (dynamic opposite "
                    "liquidity) while MQL5 uses NXS_DefaultSLTP ATR fixed multiples. Same class of "
                    "invalidation as LIQ_SWEEP Phase 7.23 Python↔MT5 exit split."
                ),
                "forbid_python_pf_as_evidence": True,
            },
        },
        "slreclaim_note": (
            "SLRECLAIM_ACCOUNT_PROTECTION_BYPASS is REMEDIATED (registry 2026-10-19). "
            "Remediation ≠ edge; not re-opened in this audit."
        ),
        "mismatches_verified_this_phase": [
            {
                "area": "ENUM_SHARING",
                "finding": "IFVG/FVG_MIT/FVG_MIT_WINDOW set s.strat=STRAT_FVG_CONT but use distinct "
                           "stratName and separate selectors/functions.",
                "severity": "MEDIUM for attribution if consumer keys on enum only; LOW if "
                            "consumer keys on stratName (NEXUS_trades.csv uses strategy name string).",
            },
            {
                "area": "EXIT_PYTHON_VS_MQL5",
                "finding": "Python opt-in target ≠ MQL5 DefaultSLTP.",
                "severity": "HIGH — blocks promotion from Python/sweep37 PF.",
            },
            {
                "area": "CTF_STATE",
                "finding": "Canonical path clean; FVG_MIT_WINDOW variant has persistent TF-unsafe state.",
                "severity": "HIGH for FVG_MIT_WINDOW if re-enabled; NONE for selector-8 FVG_CONT.",
            },
        ],
    }


def main() -> int:
    payload = build()
    doc = wrap_with_provenance(payload, "phase7_31_fvg_cont_identity/build_fvg_cont_identity_map.py")
    out = os.path.join(PHASE_DIR, "fvg_cont_identity_map_v1.json")
    save_json(out, doc)
    print(out, doc["canonical_sha256"][:16], payload["prereg_commit_sha"][:12])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
