#!/usr/bin/env python3
"""Phase 6.6 sec.4 - registro delle osservazioni post-hoc, separato dal
registro delle ipotesi vere e proprie. Un'osservazione qui NON e' mai
un edge, per costruzione dello schema (is_edge e' sempre False in questo
file - se un giorno un'osservazione diventasse un'ipotesi testata, si
sposta nel Hypothesis Registry con un proprio hypothesis_id, non si
promuove questo record)."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from canonical_utils import ROOT, load_json, save_json, wrap_with_provenance, rel_path, file_sha256  # noqa: E402

PHASE65_DIR = os.path.join(ROOT, "server", "research_scripts", "phase6_5")
PHASE66_DIR = os.path.dirname(os.path.abspath(__file__))


def build():
    dirb_file = os.path.join(PHASE65_DIR, "h006_directional_baseline_v3.json")
    dirb = load_json(dirb_file)
    policy_file = os.path.join(PHASE65_DIR, "directional_diagnostics_policy.json")
    policy = load_json(policy_file)

    buy = dirb["buy_directional"]
    sell = dirb["sell_directional"]

    observation = {
        "observation_id": "SELL_SWEEP_RECLAIM_ASYMMETRY",
        "status": "POST_HOC_OBSERVATION",
        "derived_from_hypothesis_id": "H006_LIQUIDITY_SWEEP_RECLAIM_TRUE_HOLDOUT",
        "source_phase": "Phase6.5",
        "buy": {
            "event_probability": buy["event_probability"]["observed_p"],
            "baseline_probability": buy["baseline_probability"]["observed_p"],
            "delta_p": buy["delta_p_directional"],
            "n_events": buy["n_events"],
        },
        "sell": {
            "event_probability": sell["event_probability"]["observed_p"],
            "baseline_probability": sell["baseline_probability"]["observed_p"],
            "delta_p": sell["delta_p_directional"],
            "n_events": sell["n_events"],
        },
        "is_edge": False,
        "is_validated": False,
        "requires_new_hypothesis": True,
        "requires_new_holdout": True,
        "explicit_non_actions": policy["explicit_non_actions_this_phase"],
        "policy_reference": rel_path(policy_file),
        "what_would_be_required": policy["observation_registered"]["what_would_be_required_to_test_this_as_its_own_hypothesis"],
    }

    registry = {
        "schema_version": 1,
        "description": "Osservazioni notate durante analisi/audit ma MAI promosse a ipotesi o edge senza un freeze + holdout indipendente dedicato.",
        "observations": [observation],
    }
    return registry, [dirb_file, policy_file]


if __name__ == "__main__":
    registry, sources = build()
    wrapped = wrap_with_provenance(registry, script="server/research_scripts/phase6_6/build_post_hoc_observations.py")
    wrapped["source_hashes"] = {rel_path(p): file_sha256(p) for p in sources}
    out_path = os.path.join(PHASE66_DIR, "post_hoc_observations_v1.json")
    save_json(out_path, wrapped)
    print(f"canonical_sha256: {wrapped['canonical_sha256']}")
    print(f"written: {out_path}")
