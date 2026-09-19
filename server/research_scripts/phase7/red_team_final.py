#!/usr/bin/env python3
"""Phase 7.0B sec.23 - Red-team finale: prova esplicitamente a rompere
il sistema con gli 8 attacchi nominati dall'utente, contro i moduli
REALI. Ogni attacco esegue l'azione pericolosa; e' BLOCKED solo se
l'ECCEZIONE SPECIFICA del guard competente viene sollevata - qualunque
altra eccezione e' un bug dello script stesso e non viene silenziata
come 'bloccato' (anti-pattern gia' evitato qui deliberatamente).
"""
import json
import os
import sys

PHASE7_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(PHASE7_DIR, "engine"))
sys.path.insert(0, os.path.join(PHASE7_DIR, "..", "phase6_6"))

from baseline_engine_v4 import BaselineEngineV4, FitIsolationViolation  # noqa: E402
from cross_split_safety import assign_split, validate_baseline_matches, CrossSplitViolation  # noqa: E402
from validation_access_ledger import ValidationAccessLedger, ValidationAccessViolation, load_policy  # noqa: E402
from dataset_version_guard import DatasetVersionRegistry, assert_no_drift, DatasetVersionDriftError  # noqa: E402
from candidate_signature import canonical_signature, assert_not_duplicate, DuplicateCandidateSignature  # noqa: E402
from event_firing_rate_guard import assert_allowed_for_discovery, DetectorNotAllowedForDiscovery  # noqa: E402
from synthetic_fixtures import generate_fixture  # noqa: E402
from canonical_utils import wrap_with_provenance, save_json  # noqa: E402

ATTACKS = []


def attack(name: str, fn, expected_exception: type):
    """fn() esegue l'azione pericolosa. Se solleva expected_exception ->
    BLOCKED. Se ritorna senza sollevare -> NOT_BLOCKED (blocker residuo).
    Qualunque ALTRA eccezione si propaga (bug dello script, non un
    risultato da registrare come bloccato o non bloccato)."""
    try:
        fn()
        ATTACKS.append({"attack": name, "result": "NOT_BLOCKED",
                        "note": "L'azione pericolosa e' andata a buon fine senza essere intercettata - blocker residuo."})
        print(f"[RESIDUAL BLOCKER] {name}: NON bloccato!")
    except expected_exception as e:
        ATTACKS.append({"attack": name, "result": "BLOCKED", "note": f"{type(e).__name__}: {e}"})
        print(f"[BLOCKED] {name}: {type(e).__name__}")


def main():
    fx = generate_fixture(seed=99)
    boundaries = fx["split_boundaries"]

    # 1. cross-split baseline match
    attack("cross_split_baseline_match",
           lambda: validate_baseline_matches(event_row=1500, control_rows=[500], split_boundaries=boundaries),
           CrossSplitViolation)

    # 2. holdout second read
    def a2():
        policy = load_policy()
        ledger = ValidationAccessLedger(policy)
        ledger.record_access("RT-CAND-001", "final_holdout", "RT-RUN", "HASH", purpose="primo", caller="red_team")
        ledger.record_access("RT-CAND-001", "final_holdout", "RT-RUN", "HASH", purpose="secondo (attacco)", caller="red_team")
    attack("holdout_second_read", a2, ValidationAccessViolation)

    # 3. validation reuse (oltre il limite di internal_validation=3)
    def a3():
        policy = load_policy()
        ledger = ValidationAccessLedger(policy)
        for i in range(4):
            ledger.record_access("RT-CAND-002", "internal_validation", "RT-RUN", "HASH", purpose=f"iter{i}", caller="red_team")
    attack("validation_reuse_beyond_limit", a3, ValidationAccessViolation)

    # 4. dataset file modification (simulata come drift di componenti non dichiarato)
    rt_ds_path = os.path.join(PHASE7_DIR, "preflight_output", "_rt_dataset_registry.json")

    def a4():
        registry = DatasetVersionRegistry(rt_ds_path)
        base = {"source_manifest_hash": "rt1", "date_range": ["2023-02-04", "2026-09-16"],
                "instrument": "XAUUSD", "timeframe": "TICK", "transform_version": "v1"}
        registry.register_or_check("RT_DATASET", base)
        modified = dict(base, source_manifest_hash="rt2_MODIFIED")  # simula un file sorgente alterato
        assert_no_drift(registry, "RT_DATASET", modified)
    attack("dataset_file_modification_undetected", a4, DatasetVersionDriftError)
    if os.path.exists(rt_ds_path):
        os.remove(rt_ds_path)

    # 5. scaler fit su validation
    def a5():
        engine = BaselineEngineV4(match_dimensions=["volatility_state"], k=5, split_boundaries=boundaries)
        non_discovery_row = next(r for r in fx["control_pool"] if assign_split(r, boundaries) != "discovery")
        engine.fit_normalization({non_discovery_row: {"volatility_state": "HIGH"}})
    attack("scaler_fit_on_validation", a5, FitIsolationViolation)

    # 6. detector che spara su quasi tutte le barre (PULLBACK reale) - il
    # tentativo di usarlo comunque per discovery deve essere bloccato da
    # assert_allowed_for_discovery(), non solo segnalato in un JSON.
    def a6():
        health_path = os.path.join(PHASE7_DIR, "event_detector_health_v1.json")
        with open(health_path, encoding="utf-8") as f:
            health = json.load(f)["payload"]
        pullback = next(fam for fam in health["families"] if fam["event_family"] == "PULLBACK")
        assert_allowed_for_discovery(pullback)  # deve sollevare per PULLBACK
    attack("pathological_detector_used_for_discovery", a6, DetectorNotAllowedForDiscovery)

    # 7. candidate duplicate con rappresentazione diversa (casing/ordine/numerico)
    def a7():
        sig1 = canonical_signature("SWEEP", "SELL", [{"feature_id": "trend", "operator": "=", "threshold": 1}], "OUT")
        sig2 = canonical_signature("sweep", "sell", [{"feature_id": "TREND", "operator": "==", "threshold": "1.0"}], "OUT")
        assert_not_duplicate([sig1], sig2)  # deve sollevare: sig2 e' un duplicato di sig1
    attack("duplicate_candidate_different_representation", a7, DuplicateCandidateSignature)

    # 8. baseline con pool insufficiente - deve risultare REJECTED, mai un match forzato
    def a8():
        engine = BaselineEngineV4(match_dimensions=["volatility_state"], k=5, split_boundaries=boundaries)
        discovery_rows = [r for r in fx["control_pool"] if assign_split(r, boundaries) == "discovery"]
        engine.fit_normalization({r: fx["feature_by_row"][r] for r in discovery_rows if r in fx["feature_by_row"]})
        ev_row = fx["event_rows"][0]
        tiny_pool = discovery_rows[:3]  # sotto minimum_control_count=20
        result = engine.match(ev_row, ev_row, fx["direction_by_row"][ev_row],
                               fx["feature_by_row"].get(ev_row, {"volatility_state": "HIGH"}),
                               tiny_pool, {c: c for c in tiny_pool}, {c: fx["direction_by_row"].get(c, 1) for c in tiny_pool},
                               {c: fx["feature_by_row"].get(c, {"volatility_state": "HIGH"}) for c in tiny_pool})
        if result["status"] != "REJECTED_INSUFFICIENT_POOL" or result["matches"]:
            raise RuntimeError(f"pool insufficiente NON rifiutato correttamente: status={result['status']}, n_matches={len(result['matches'])}")
    # Qui il "blocco" e' l'ASSENZA di un'eccezione (match() rifiuta per stato, non per eccezione) -
    # quindi il modello e' invertito: successo di a8() = attacco bloccato.
    try:
        a8()
        ATTACKS.append({"attack": "baseline_insufficient_pool_forced_match", "result": "BLOCKED",
                        "note": "match() ha correttamente restituito REJECTED_INSUFFICIENT_POOL con zero match, mai un match forzato."})
        print("[BLOCKED] baseline_insufficient_pool_forced_match: REJECTED_INSUFFICIENT_POOL confermato")
    except RuntimeError as e:
        ATTACKS.append({"attack": "baseline_insufficient_pool_forced_match", "result": "NOT_BLOCKED", "note": str(e)})
        print(f"[RESIDUAL BLOCKER] baseline_insufficient_pool_forced_match: {e}")

    n_blocked = sum(1 for a in ATTACKS if a["result"] == "BLOCKED")
    n_residual = len(ATTACKS) - n_blocked
    print(f"\n=== Red-team finale: {n_blocked}/{len(ATTACKS)} attacchi BLOCKED, {n_residual} blocker residui ===")

    payload = {"attacks": ATTACKS, "n_attacks": len(ATTACKS), "n_blocked": n_blocked, "n_residual_blockers": n_residual}
    save_json(os.path.join(PHASE7_DIR, "red_team_final_v1.json"), wrap_with_provenance(payload, "phase7/red_team_final.py"))
    return n_residual == 0


if __name__ == "__main__":
    ok = main()
    sys.exit(0 if ok else 1)
