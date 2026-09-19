#!/usr/bin/env python3
"""Phase 7.3 sec.17 - Red-team del Sequence Discovery Engine: 10 attacchi
nominati, ciascuno eseguito contro i moduli REALI. Bloccato = l'eccezione
specifica del guard competente viene sollevata; qualunque altro esito e'
un blocker residuo, mai silenziato."""
import json
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", ".."))
PHASE73_DIR = os.path.dirname(os.path.abspath(__file__))
PHASE7_ENGINE_DIR = os.path.join(ROOT, "server", "research_scripts", "phase7", "engine")
sys.path.insert(0, os.path.join(PHASE73_DIR, "engine"))
sys.path.insert(0, PHASE73_DIR)
sys.path.insert(0, PHASE7_ENGINE_DIR)

from sequence_causality_guard import (enforce_temporal_causality, SequenceCausalityViolation,  # noqa: E402
                                       assert_detector_version_unchanged, DetectorVersionMismatchError)
from sequence_episode_engine import build_event_and_episode_views  # noqa: E402
from sequence_baseline_adapter_v1 import SequenceBaselineAdapter  # noqa: E402
from outcome_surface_v3 import OutcomeSurfaceV3, OutcomeShoppingBlocked  # noqa: E402
from sequence_engine_governance import enforce_failure_memory_gate, DirectRepeatBlockedError  # noqa: E402
from cross_split_safety import validate_baseline_matches, CrossSplitViolation, assign_split  # noqa: E402
from validation_access_ledger import ValidationAccessLedger, ValidationAccessViolation, load_policy  # noqa: E402
from preregistration_provenance_guard import assert_frozen_spec_committed_before_run, PreRegistrationProvenanceError  # noqa: E402

ATTACKS = []


def attack(name, fn, expected_exception):
    try:
        fn()
        ATTACKS.append({"attack": name, "result": "NOT_BLOCKED", "note": "azione pericolosa non intercettata - blocker residuo."})
        print(f"[RESIDUAL BLOCKER] {name}")
    except expected_exception as e:
        ATTACKS.append({"attack": name, "result": "BLOCKED", "note": f"{type(e).__name__}: {e}"})
        print(f"[BLOCKED] {name}: {type(e).__name__}")


def main():
    boundaries = {"discovery": (0, 100), "internal_validation": (100, 150),
                  "locked_validation": (150, 200), "final_holdout": (200, 250)}

    # 1. sequence usa barra futura
    attack("sequence_uses_future_bar",
           lambda: enforce_temporal_causality(observation_cutoff_index=5, max_feature_timestamp_index=9,
                                               transition_complete_index=5, prediction_start_index=5,
                                               outcome_window_start_index=6, sequence_event_id="RT-1"),
           SequenceCausalityViolation)

    # 2. outcome usato come trigger (circolarita')
    sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase7", "phase7_2"))
    from sequence_semantic_leakage_guard import check_sequence_leakage, FAIL  # noqa: E402
    verdict, reason = check_sequence_leakage(0, 0, 1, outcome_measures_same_event_as_trigger=True)
    if verdict == FAIL:
        ATTACKS.append({"attack": "outcome_used_as_trigger", "result": "BLOCKED",
                        "note": f"sequence_semantic_leakage_guard.check_sequence_leakage ha classificato FAIL: {reason}"})
        print("[BLOCKED] outcome_used_as_trigger: FAIL (semantic_leakage_guard)")
    else:
        ATTACKS.append({"attack": "outcome_used_as_trigger", "result": "NOT_BLOCKED",
                        "note": f"atteso verdetto FAIL, ottenuto {verdict} - la circolarita' non e' stata rilevata."})
        print("[RESIDUAL BLOCKER] outcome_used_as_trigger")

    # 3. eventi duplicati dello stesso episodio (nessun doppio conteggio nell'EPISODE VIEW)
    def a3():
        dup_events = [
            {"sequence_event_id": "C-1", "sequence_id": "SEQ-TOY", "direction": "BUY", "event_a_index": 10,
             "transition_complete_index": 10, "prediction_start_index": 10},
            {"sequence_event_id": "C-1-DUP", "sequence_id": "SEQ-TOY", "direction": "BUY", "event_a_index": 10,
             "transition_complete_index": 10, "prediction_start_index": 10},
            {"sequence_event_id": "C-2", "sequence_id": "SEQ-TOY", "direction": "BUY", "event_a_index": 11,
             "transition_complete_index": 11, "prediction_start_index": 11},
        ]
        _, ep = build_event_and_episode_views(dup_events, episode_gap_rule=5, natural_horizon=40, overlap_policy="COLLAPSE_TO_FIRST")
        if ep["n_episodes"] != 1:
            raise RuntimeError(f"atteso 1 episodio (eventi allo stesso indice/ravvicinati collassati), ottenuti {ep['n_episodes']}")
    try:
        a3()
        ATTACKS.append({"attack": "duplicate_events_same_episode_double_counted", "result": "BLOCKED",
                        "note": "l'EPISODE VIEW collassa correttamente eventi duplicati/ravvicinati in un solo episodio."})
        print("[BLOCKED] duplicate_events_same_episode_double_counted")
    except RuntimeError as e:
        ATTACKS.append({"attack": "duplicate_events_same_episode_double_counted", "result": "NOT_BLOCKED", "note": str(e)})
        print(f"[RESIDUAL BLOCKER] duplicate_events_same_episode_double_counted: {e}")

    # 4. baseline pesca dallo split successivo (exception path diretto, non solo filtro)
    attack("baseline_fishes_from_next_split",
           lambda: validate_baseline_matches(event_row=10, control_rows=[12, 120], split_boundaries=boundaries),
           CrossSplitViolation)

    # 5. direction mismatch - un controllo di direzione diversa non deve mai comparire nei match
    def a5():
        adapter = SequenceBaselineAdapter(match_dimensions=["toy_state"], k=5, split_boundaries=boundaries)
        adapter.fit_on_discovery_only({i: {"toy_state": 1.0} for i in range(0, 100, 2)})
        pool = list(range(0, 40, 2))
        result = adapter.engine.match(
            event_id="RT-5", event_row=10, event_direction="BUY", event_features={"toy_state": 1.0},
            control_pool=pool, control_row_by_id={c: c for c in pool},
            control_direction_by_id={c: ("BUY" if c % 4 == 0 else "SELL") for c in pool},  # meta' direzione sbagliata
            control_features_by_id={c: {"toy_state": 1.0} for c in pool},
        )
        mismatched = [m for m in result["matches"] if m["control_direction"] != "BUY"]
        if mismatched:
            raise RuntimeError(f"{len(mismatched)} match con direzione sbagliata sono passati!")
    try:
        a5()
        ATTACKS.append({"attack": "direction_mismatch_control_used", "result": "BLOCKED",
                        "note": "nessun controllo di direzione diversa e' comparso nei match finali (filtro direction-aware)."})
        print("[BLOCKED] direction_mismatch_control_used")
    except RuntimeError as e:
        ATTACKS.append({"attack": "direction_mismatch_control_used", "result": "NOT_BLOCKED", "note": str(e)})
        print(f"[RESIDUAL BLOCKER] direction_mismatch_control_used: {e}")

    # 6. detector cambia dopo outcome (versione diversa a meta' run)
    attack("detector_changed_after_outcome",
           lambda: assert_detector_version_unchanged("toy-v1", "toy-v2-hotfix", sequence_event_id="RT-6"),
           DetectorVersionMismatchError)

    # 7. outcome shopping
    def a7():
        surface = OutcomeSurfaceV3(primary_outcome="P_PLUS_1ATR_BEFORE_MINUS_1ATR", secondary_outcomes=["MFE"], diagnostic_outcomes=["MAE"])
        surface.assert_no_post_hoc_outcome_addition("CONTINUATION_PROBABILITY", already_saw_results=True)
    attack("outcome_shopping", a7, OutcomeShoppingBlocked)

    # 8. repeated validation access
    def a8():
        policy = load_policy()
        ledger = ValidationAccessLedger(policy)
        ledger.record_access("RT-SEQFAM-1", "locked_validation", "RT-RUN", "HASH", purpose="rt", caller="phase7_3_red_team.py")
        ledger.record_access("RT-SEQFAM-1", "locked_validation", "RT-RUN", "HASH", purpose="rt-secondo-tentativo", caller="phase7_3_red_team.py")
    attack("repeated_validation_access", a8, ValidationAccessViolation)

    # 9. post-hoc parameter change (frozen spec modificata senza commit)
    def a9():
        target = os.path.join(PHASE73_DIR, "schemas", "sequence_family_frozen_spec_v1.schema.json")
        rel = os.path.relpath(target, ROOT).replace("\\", "/")
        with open(target, "a", encoding="utf-8") as f:
            f.write("\n")  # modifica minima non committata
        try:
            assert_frozen_spec_committed_before_run(ROOT, rel)
        finally:
            # ripristino immediato - nessuna modifica lasciata sul repo
            with open(target, encoding="utf-8") as f:
                content = f.read()
            with open(target, "w", encoding="utf-8") as f:
                f.write(content[:-1] if content.endswith("\n\n") else content)
    attack("post_hoc_parameter_change_uncommitted_spec", a9, PreRegistrationProvenanceError)

    # 10. failed idea renamed (DIRECT_REPEAT senza override, anche con un family_id nuovo)
    def a10():
        renamed_links = {"failure_memory_relation": "DIRECT_REPEAT_OF_FAILED_IDEA", "prior_failure_ids": ["SEQ-0010"],
                          "direct_repeat_flag": True, "related_failure_flag": False,
                          "novelty_note": "rinominato SEQFAM-BRAND-NEW-NAME, stessa logica di SEQ-0010"}
        enforce_failure_memory_gate(renamed_links)
    attack("failed_idea_renamed", a10, DirectRepeatBlockedError)

    n_blocked = sum(1 for a in ATTACKS if a["result"] == "BLOCKED")
    n_residual = len(ATTACKS) - n_blocked
    print(f"\n=== Red-team Phase 7.3: {n_blocked}/{len(ATTACKS)} attacchi BLOCKED, {n_residual} blocker residui ===")

    payload = {
        "_provenance": {"generated_by": "phase7/phase7_3/phase7_3_red_team.py",
                        "note": "10 attacchi sec.17 eseguiti contro i moduli REALI del Sequence Discovery Engine v1, "
                                "nessun dato NEXUS coinvolto."},
        "attacks": ATTACKS, "n_attacks": len(ATTACKS), "n_blocked": n_blocked, "n_residual_blockers": n_residual,
    }
    out_path = os.path.join(PHASE73_DIR, "phase7_3_red_team_v1.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)
    return n_residual == 0


if __name__ == "__main__":
    ok = main()
    sys.exit(0 if ok else 1)
