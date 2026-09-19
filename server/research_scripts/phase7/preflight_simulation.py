#!/usr/bin/env python3
"""Phase 7 sec.26 - Preflight simulation. Dry-run END-TO-END su dati
SINTETICI (synthetic_fixtures.py) per dimostrare che ogni gate del motore
funziona MECCANICAMENTE, non solo sulla carta. Ogni gruppo di controlli
ha un caso valido E, dove ha senso, un caso deliberatamente rotto.

Questo script NON e' una discovery run (nessun dato di mercato reale,
nessun H007, nessun nuovo edge). Produce 4 artifact di output, tutti
etichettati SYNTHETIC_FIXTURE_ONLY, dentro preflight_output/.

Integrity Patch (post-review, 2026-09-18): aggiunti i controlli 9-13
(normalizzazione numerica/casing della signature, coerenza terminale di
COST_SENSITIVE, assenza di path assoluti machine-specific sotto
phase7/, classificazione epistemica del gate di uncertainty) - vedi
vault/01-Trading/NEXUS - Phase 7.0 Integrity Patch.md per il dettaglio
dei bug corretti.

Phase 7.0B (Operational Readiness, 2026-09-19): aggiunti i controlli
14-27 (Baseline Engine v4 reale, event firing rate guard, validation/
holdout access ledger, dataset version guard/drift, sigillo holdout,
serializzazione end-to-end del candidato) - vedi
vault/01-Trading/NEXUS - Phase 7.0B Operational Readiness.md.
"""
import json
import os
import re
import sys

PHASE7_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(PHASE7_DIR, "engine"))
sys.path.insert(0, os.path.join(PHASE7_DIR, "..", "phase6_6"))

from canonical_utils import wrap_with_provenance, save_json  # noqa: E402
from candidate_lifecycle import Candidate, InvalidTransitionError, TERMINAL_STATES  # noqa: E402
from candidate_signature import canonical_signature, signature_hash, is_duplicate  # noqa: E402
from dependence_diagnostics_v2 import compare_event_vs_episode_view  # noqa: E402
from multiple_testing_v2 import run_family  # noqa: E402
from post_hoc_quarantine import register_post_hoc_observation, attempt_promotion, PostHocPromotionBlocked  # noqa: E402
from cross_split_safety import assign_split, validate_baseline_matches, CrossSplitViolation  # noqa: E402
from synthetic_fixtures import generate_fixture, fake_baseline_p  # noqa: E402
from baseline_engine_v4 import BaselineEngineV4, FitIsolationViolation, build_quality_report  # noqa: E402
from event_firing_rate_guard import classify_firing_rate  # noqa: E402
from validation_access_ledger import ValidationAccessLedger, ValidationAccessViolation, load_policy as load_access_policy  # noqa: E402
from dataset_version_guard import DatasetVersionRegistry, assert_no_drift, DatasetVersionDriftError  # noqa: E402

OUT_DIR = os.path.join(PHASE7_DIR, "preflight_output")
os.makedirs(OUT_DIR, exist_ok=True)

RESULTS = []


def check(name, condition, detail=""):
    status = "PASS" if condition else "FAIL"
    RESULTS.append({"check": name, "status": status, "detail": detail})
    print(f"[{status}] {name} {('- ' + detail) if detail else ''}")
    return condition


def assert_feature_allowed_for_discovery(feature_entry: dict):
    """Gate minimo di leakage per il preflight: nessuna feature con
    leakage_risk != LOW puo' essere usata come state_condition. Riflette
    la regola gia' dichiarata in feature_registry_v2.json / FAIL-008."""
    if feature_entry.get("leakage_risk") != "LOW":
        raise ValueError(
            f"Feature '{feature_entry['feature_id']}' rifiutata: "
            f"leakage_risk={feature_entry.get('leakage_risk')} (richiesto LOW/CAUSAL_SAFE)."
        )


def main():
    fx = generate_fixture(seed=42)
    boundaries = fx["split_boundaries"]

    print("=== Phase 7 Preflight Simulation - SYNTHETIC_FIXTURE_ONLY ===\n")

    # ------------------------------------------------------------------
    # Check 1: split isolation - assign_split + rifiuto di un match
    # cross-split esplicito (API-level).
    # ------------------------------------------------------------------
    ok_result = validate_baseline_matches(event_row=1500, control_rows=[1410, 1420, 1650], split_boundaries=boundaries)
    check("split_isolation_valid_case_passes", len(ok_result["violations"]) == 0)
    try:
        validate_baseline_matches(event_row=1500, control_rows=[1410, 500, 1650], split_boundaries=boundaries)
        check("split_isolation_negative_case_blocked", False, "violazione NON rilevata!")
    except CrossSplitViolation:
        check("split_isolation_negative_case_blocked", True, "CrossSplitViolation sollevata correttamente")

    # ------------------------------------------------------------------
    # Check 2: leakage guard blocca una feature non causal-safe.
    # ------------------------------------------------------------------
    try:
        assert_feature_allowed_for_discovery({"feature_id": "atr_14", "leakage_risk": "LOW"})
        check("leakage_guard_allows_safe_feature", True)
    except ValueError:
        check("leakage_guard_allows_safe_feature", False, "feature sicura rifiutata per errore")

    try:
        assert_feature_allowed_for_discovery(fx["fake_leaky_feature"])
        check("leakage_guard_blocks_unsafe_feature", False, "feature leaky NON bloccata!")
    except ValueError as e:
        check("leakage_guard_blocks_unsafe_feature", True, str(e))

    # ------------------------------------------------------------------
    # Check 3: duplicate signature detection.
    # ------------------------------------------------------------------
    sig_a = canonical_signature("SYNTH_SWEEP", "BUY",
                                 [{"feature_id": "volatility_state", "operator": "==", "threshold": "HIGH"},
                                  {"feature_id": "trend_state", "operator": "==", "threshold": "UP"}],
                                 "P(+1R before -1R)")
    sig_b = canonical_signature("SYNTH_SWEEP", "BUY",
                                 [{"feature_id": "trend_state", "operator": "==", "threshold": "UP"},
                                  {"feature_id": "volatility_state", "operator": "==", "threshold": "HIGH"}],
                                 "P(+1R before -1R)")
    sig_c = canonical_signature("SYNTH_SWEEP", "SELL",
                                 [{"feature_id": "volatility_state", "operator": "==", "threshold": "HIGH"},
                                  {"feature_id": "trend_state", "operator": "==", "threshold": "UP"}],
                                 "P(+1R before -1R)")
    check("duplicate_signature_detected_regardless_of_order", is_duplicate(sig_a, sig_b))
    check("distinct_direction_not_flagged_as_duplicate", not is_duplicate(sig_a, sig_c))

    # ------------------------------------------------------------------
    # Check 4: post-hoc quarantine.
    # ------------------------------------------------------------------
    obs = register_post_hoc_observation("SYNTH-POSTHOC-001", "SYNTH-CAND-001", "direction_split", "PREFLIGHT-RUN-001")
    try:
        attempt_promotion(obs, target_state="SUPPORTED", same_run=True)
        check("post_hoc_promotion_blocked_same_run", False, "promozione NON bloccata!")
    except PostHocPromotionBlocked:
        check("post_hoc_promotion_blocked_same_run", True)

    # ------------------------------------------------------------------
    # Check 5: FDR family count corretto.
    # ------------------------------------------------------------------
    comparisons = [
        {"id": "SYNTH-CAND-001", "wins_event": 62, "n_event": 100, "wins_baseline": 250, "n_baseline": 500},
        {"id": "SYNTH-CAND-002", "wins_event": 55, "n_event": 100, "wins_baseline": 250, "n_baseline": 500},
        {"id": "SYNTH-CAND-003", "wins_event": 48, "n_event": 100, "wins_baseline": 250, "n_baseline": 500},
    ]
    mt_report = run_family("SYNTH_FAMILY_1", comparisons, q=0.10)
    check("fdr_family_size_matches_comparisons", mt_report["family_size"] == len(comparisons))
    check("fdr_results_cover_all_ids", set(mt_report["results"].keys()) == {c["id"] for c in comparisons})

    # ------------------------------------------------------------------
    # Check 6: baseline mai cross-split, su un pass completo (non solo
    # un singolo caso API-level come il Check 1).
    # ------------------------------------------------------------------
    n_checked, n_violations_caught = 0, 0
    for ev_row in fx["event_rows"][:30]:
        ev_split = assign_split(ev_row, boundaries)
        same_split_controls = [c for c in fx["control_pool"] if assign_split(c, boundaries) == ev_split][:5]
        res = validate_baseline_matches(ev_row, same_split_controls, boundaries)
        n_checked += 1
        assert len(res["violations"]) == 0
    # ora un caso deliberatamente corrotto: forziamo controlli da un altro split
    corrupted_controls = [c for c in fx["control_pool"] if assign_split(c, boundaries) == "discovery"][:3]
    try:
        validate_baseline_matches(1850, corrupted_controls, boundaries)  # 1850 e' in final_holdout
        n_violations_caught = 0
    except CrossSplitViolation:
        n_violations_caught = 1
    check("baseline_full_pass_no_violations_when_correct", n_checked == 30)
    check("baseline_corrupted_case_detected", n_violations_caught == 1)

    # ------------------------------------------------------------------
    # Check 7: dependence metrics prodotte (EVENT vs EPISODE view).
    # ------------------------------------------------------------------
    dep_result = compare_event_vs_episode_view(
        fx["event_rows"], fx["direction_by_row"], fx["outcome_by_row"],
        materiality_threshold_delta_p=0.10, baseline_p_func=fake_baseline_p,
    )
    check("dependence_metrics_produced", all(k in dep_result for k in ("event_view", "episode_view", "dependence_sensitive")))

    # ------------------------------------------------------------------
    # Check 8: lifecycle non puo' saltare stati.
    # ------------------------------------------------------------------
    c = Candidate("SYNTH-CAND-LIFECYCLE-001")
    c.transition("DISCOVERY_SIGNAL", "generato in discovery")
    c.transition("INTERNAL_VALIDATION", "supera internal validation")
    check("lifecycle_valid_path_succeeds", c.state == "INTERNAL_VALIDATION")
    try:
        c.transition("SUPPORTED", "tentativo di salto illegale")
        check("lifecycle_illegal_skip_blocked", False, "salto NON bloccato!")
    except InvalidTransitionError:
        check("lifecycle_illegal_skip_blocked", True)

    # ------------------------------------------------------------------
    # Check 9 (Integrity Patch): normalizzazione NUMERICA della signature
    # - 1 / 1.0 / "1.000" / " 1 " devono produrre la stessa firma.
    # ------------------------------------------------------------------
    sig_num_variants = [
        canonical_signature("SYNTH_SWEEP", "BUY", [{"feature_id": "trend", "operator": "=", "threshold": t}], "OUT")
        for t in (1, 1.0, "1.000", " 1 ")
    ]
    check("signature_numeric_threshold_normalization", len(set(sig_num_variants)) == 1,
          "1 / 1.0 / '1.000' / ' 1 ' devono collassare alla stessa firma")
    sig_num_diff = canonical_signature("SYNTH_SWEEP", "BUY", [{"feature_id": "trend", "operator": "=", "threshold": 1.5}], "OUT")
    check("signature_distinct_numeric_thresholds_not_collapsed", sig_num_diff not in set(sig_num_variants))

    # ------------------------------------------------------------------
    # Check 10 (Integrity Patch): normalizzazione CASING/ORDINE della
    # signature - feature_id/operator/threshold categorico con casing e
    # whitespace diversi devono comunque collassare alla stessa firma.
    # ------------------------------------------------------------------
    sig_case_1 = canonical_signature("sweep", "sell",
                                      [{"feature_id": "Volatility", "operator": "==", "threshold": " high "},
                                       {"feature_id": "TREND", "operator": "eq", "threshold": "down"}],
                                      "OUT")
    sig_case_2 = canonical_signature("SWEEP", "SELL",
                                      [{"feature_id": "trend", "operator": "=", "threshold": "DOWN"},
                                       {"feature_id": "volatility", "operator": "=", "threshold": "HIGH"}],
                                      "OUT")
    check("signature_casing_and_order_normalization", sig_case_1 == sig_case_2)

    # ------------------------------------------------------------------
    # Check 11 (Integrity Patch): COST_SENSITIVE non ha transizioni in
    # uscita -> deve essere strutturalmente terminale.
    # ------------------------------------------------------------------
    c_cost = Candidate("SYNTH-CAND-COST-001", initial_state="COST_SENSITIVE")
    check("cost_sensitive_is_terminal", c_cost.is_terminal() is True)
    check("terminal_states_invariant_holds_for_all_states",
          all(Candidate(f"INV-{s}", initial_state=s).is_terminal() == (s in TERMINAL_STATES)
              for s in ("COST_SENSITIVE", "SUPPORTED", "BORDERLINE", "GENERATED")))

    # ------------------------------------------------------------------
    # Check 12 (Integrity Patch): nessun path assoluto machine-specific
    # sotto phase7/ (source tree, esclusi output generati/pycache).
    # ------------------------------------------------------------------
    absolute_path_pattern = re.compile(r"[A-Za-z]:\\Users\\[^\"'\s]+|/Users/[^\"'\s]+|/home/[^/\"'\s]+/[^\"'\s]*")
    self_file = os.path.abspath(__file__)
    offenders = []
    for dirpath, dirnames, filenames in os.walk(PHASE7_DIR):
        dirnames[:] = [d for d in dirnames if d not in ("__pycache__", "preflight_output")]
        for fname in filenames:
            if not fname.endswith((".py", ".json")):
                continue
            fpath = os.path.join(dirpath, fname)
            if os.path.abspath(fpath) == self_file:
                # Questo stesso file contiene, come stringa letterale, il
                # pattern usato per RILEVARE path assoluti - non e' un path
                # assoluto reale, e' il detector - escluso per costruzione,
                # non per nascondere un problema.
                continue
            with open(fpath, encoding="utf-8") as fh:
                for lineno, line in enumerate(fh, start=1):
                    if absolute_path_pattern.search(line):
                        offenders.append(f"{os.path.relpath(fpath, PHASE7_DIR)}:{lineno}")
    check("no_machine_specific_absolute_paths_under_phase7", len(offenders) == 0,
          f"offenders={offenders}" if offenders else "")
    # Caso deliberatamente rotto (senza scrivere file reali su disco): il
    # pattern deve individuare stringhe di path assoluti sintetiche e non
    # segnalare falsi positivi su path relativi legittimi.
    check("absolute_path_pattern_detects_synthetic_bad_paths",
          bool(absolute_path_pattern.search(r'ROOT = "C:\Users\SomeOtherUser\ClaudeWork\MAX"'))
          and bool(absolute_path_pattern.search('path = "/Users/someone/repo/file.py"'))
          and bool(absolute_path_pattern.search('path = "/home/someone/repo/file.py"')))
    check("absolute_path_pattern_no_false_positive_on_relative_paths",
          not absolute_path_pattern.search('PHASE55_DIR = os.path.join(ROOT, "server", "research_scripts", "phase5_5")'))

    # ------------------------------------------------------------------
    # Check 13 (Integrity Patch): il gate di uncertainty resta
    # classificato POLICY_THRESHOLD_WITH_STATISTICAL_RATIONALE, non
    # STATISTICALLY_JUSTIFIED - invariante anti-regressione.
    # ------------------------------------------------------------------
    with open(os.path.join(PHASE7_DIR, "policies", "minimum_evidence_gates.json"), encoding="utf-8") as fh:
        gates_policy = json.load(fh)
    uncertainty_status = gates_policy["gates"]["uncertainty_requirement"]["status"]
    check("uncertainty_gate_correctly_classified",
          uncertainty_status == "POLICY_THRESHOLD_WITH_STATISTICAL_RATIONALE",
          f"status attuale={uncertainty_status}")

    # ------------------------------------------------------------------
    # Check 14: Baseline Engine v4 - matching valido su una cella con
    # pool sufficiente e direzione corretta.
    # ------------------------------------------------------------------
    engine_v4 = BaselineEngineV4(match_dimensions=["volatility_state"], k=5, split_boundaries=boundaries)
    discovery_rows_v4 = [r for r in fx["control_pool"] if assign_split(r, boundaries) == "discovery"]
    discovery_feats_v4 = {r: fx["feature_by_row"][r] for r in discovery_rows_v4 if r in fx["feature_by_row"]}
    engine_v4.fit_normalization(discovery_feats_v4)

    ev_row_v4 = fx["event_rows"][0]
    ev_dir_v4 = fx["direction_by_row"][ev_row_v4]
    ev_split_v4 = assign_split(ev_row_v4, boundaries)
    ev_feat_v4 = fx["feature_by_row"].get(ev_row_v4, {"volatility_state": "HIGH"})
    pool_v4 = [c for c in fx["control_pool"] if assign_split(c, boundaries) == ev_split_v4]
    ctrl_row_v4 = {c: c for c in pool_v4}
    ctrl_dir_v4 = {c: fx["direction_by_row"].get(c, ev_dir_v4) for c in pool_v4}
    ctrl_feat_v4 = {c: fx["feature_by_row"].get(c, {"volatility_state": "HIGH"}) for c in pool_v4}
    match_v4 = engine_v4.match(ev_row_v4, ev_row_v4, ev_dir_v4, ev_feat_v4, pool_v4, ctrl_row_v4, ctrl_dir_v4, ctrl_feat_v4)
    check("baseline_v4_valid_matching", match_v4["status"] in ("MATCHED", "MATCHED_K_SHORTFALL"))

    # ------------------------------------------------------------------
    # Check 15: direction mismatch - nessun match deve MAI includere un
    # controllo di direzione diversa dall'evento.
    # ------------------------------------------------------------------
    ctrl_dir_mixed = {c: (ctrl_dir_v4[c] if i % 2 == 0 else -ctrl_dir_v4[c]) for i, c in enumerate(pool_v4)}
    match_mixed = engine_v4.match(ev_row_v4, ev_row_v4, ev_dir_v4, ev_feat_v4, pool_v4, ctrl_row_v4, ctrl_dir_mixed, ctrl_feat_v4)
    check("baseline_v4_direction_mismatch_blocked",
          all(m["control_direction"] == ev_dir_v4 for m in match_mixed["matches"]))

    # ------------------------------------------------------------------
    # Check 16: cross-split - il pool passato a match() puo' contenere
    # righe di altri split, ma NESSUN match risultante deve attraversarli.
    # ------------------------------------------------------------------
    other_split_rows = [r for r in fx["control_pool"] if assign_split(r, boundaries) != ev_split_v4][:10]
    pool_with_foreign = pool_v4 + other_split_rows
    ctrl_row_foreign = {**ctrl_row_v4, **{r: r for r in other_split_rows}}
    ctrl_dir_foreign = {**ctrl_dir_v4, **{r: ev_dir_v4 for r in other_split_rows}}
    ctrl_feat_foreign = {**ctrl_feat_v4, **{r: ev_feat_v4 for r in other_split_rows}}
    match_foreign = engine_v4.match(ev_row_v4, ev_row_v4, ev_dir_v4, ev_feat_v4, pool_with_foreign,
                                     ctrl_row_foreign, ctrl_dir_foreign, ctrl_feat_foreign)
    check("baseline_v4_cross_split_blocked",
          all(assign_split(ctrl_row_foreign[m["control_id"]], boundaries) == ev_split_v4 for m in match_foreign["matches"]))

    # ------------------------------------------------------------------
    # Check 17: pool insufficiente -> REJECTED_INSUFFICIENT_POOL, mai un
    # match forzato su meno controlli del minimo dichiarato.
    # ------------------------------------------------------------------
    tiny_pool = pool_v4[:5]  # sotto minimum_control_count=20
    match_tiny = engine_v4.match(ev_row_v4, ev_row_v4, ev_dir_v4, ev_feat_v4, tiny_pool,
                                  {c: ctrl_row_v4[c] for c in tiny_pool}, {c: ctrl_dir_v4[c] for c in tiny_pool},
                                  {c: ctrl_feat_v4[c] for c in tiny_pool})
    check("baseline_v4_insufficient_controls_blocked", match_tiny["status"] == "REJECTED_INSUFFICIENT_POOL")

    # ------------------------------------------------------------------
    # Check 18: overload di match POOR - dimensione numerica dispersa
    # deliberatamente per forzare distanze standardizzate alte.
    # ------------------------------------------------------------------
    engine_poor = BaselineEngineV4(match_dimensions=["dispersed_numeric"], k=5, split_boundaries=boundaries)
    poor_discovery_feats = {r: {"dispersed_numeric": float(i)} for i, r in enumerate(discovery_rows_v4)}
    engine_poor.fit_normalization(poor_discovery_feats)
    poor_pool = pool_v4[:40]
    ctrl_feat_poor = {c: {"dispersed_numeric": float(i * 1000)} for i, c in enumerate(poor_pool)}  # outlier estremi
    ev_feat_poor = {"dispersed_numeric": 0.0}
    match_poor = engine_poor.match(ev_row_v4, ev_row_v4, ev_dir_v4, ev_feat_poor, poor_pool,
                                    {c: ctrl_row_v4[c] for c in poor_pool}, {c: ctrl_dir_v4[c] for c in poor_pool},
                                    ctrl_feat_poor)
    poor_report = build_quality_report([match_poor])
    check("baseline_v4_poor_match_overload_flagged", poor_report["excessive_poor_matches_flag"] is True,
          f"poor_share={poor_report['poor_match_share']:.2f}")

    # ------------------------------------------------------------------
    # Check 19: fit isolation - fit su una riga fuori da discovery deve
    # sollevare FitIsolationViolation (ripete a livello preflight quanto
    # gia' dimostrato nel modulo, per garantirne l'integrazione qui).
    # ------------------------------------------------------------------
    try:
        non_discovery_row = next(r for r in fx["control_pool"] if assign_split(r, boundaries) != "discovery")
        engine_v4.fit_normalization({non_discovery_row: {"volatility_state": "HIGH"}})
        check("fit_on_validation_blocked", False, "fit su non-discovery NON bloccato!")
    except FitIsolationViolation:
        check("fit_on_validation_blocked", True)

    # ------------------------------------------------------------------
    # Check 20-21: Event Firing Rate Guard - detector patologico
    # bloccato, detector normale ammesso, sui detector REALI di Phase 5
    # (letti da event_detector_health_v1.json, gia' prodotto - solo
    # conteggi strutturali, nessun outcome).
    # ------------------------------------------------------------------
    health_path = os.path.join(PHASE7_DIR, "event_detector_health_v1.json")
    if os.path.exists(health_path):
        with open(health_path, encoding="utf-8") as fh:
            health = json.load(fh)["payload"]
        by_family = {f["event_family"]: f for f in health["families"]}
        pullback = by_family.get("PULLBACK")
        sweep = by_family.get("SWEEP")
        check("event_firing_rate_pathological_detector_blocked",
              pullback is not None and pullback["status"] == "PATHOLOGICAL" and pullback["allowed_for_discovery"] is False)
        check("event_firing_rate_normal_detector_allowed",
              sweep is not None and sweep["allowed_for_discovery"] is True)
    else:
        check("event_firing_rate_pathological_detector_blocked", False, "event_detector_health_v1.json non trovato")
        check("event_firing_rate_normal_detector_allowed", False, "event_detector_health_v1.json non trovato")
    check("firing_rate_classifier_consistent", classify_firing_rate(0.85) == "PATHOLOGICAL" and classify_firing_rate(0.10) == "NORMAL")

    # ------------------------------------------------------------------
    # Check 22-23: Validation/Holdout Access Ledger - secondo accesso a
    # locked_validation/final_holdout bloccato meccanicamente.
    # ------------------------------------------------------------------
    access_policy = load_access_policy()
    ledger = ValidationAccessLedger(access_policy)
    ledger.record_access("PREFLIGHT-CAND-001", "locked_validation", "PREFLIGHT-RUN-001", "DSHASH-PREFLIGHT",
                          purpose="preflight demo", caller="preflight_simulation.py")
    try:
        ledger.record_access("PREFLIGHT-CAND-001", "locked_validation", "PREFLIGHT-RUN-001", "DSHASH-PREFLIGHT",
                              purpose="secondo tentativo", caller="preflight_simulation.py")
        check("second_locked_validation_access_blocked", False, "secondo accesso NON bloccato!")
    except ValidationAccessViolation:
        check("second_locked_validation_access_blocked", True)

    ledger.record_access("PREFLIGHT-CAND-002", "final_holdout", "PREFLIGHT-RUN-001", "DSHASH-PREFLIGHT",
                          purpose="preflight demo", caller="preflight_simulation.py")
    try:
        ledger.record_access("PREFLIGHT-CAND-002", "final_holdout", "PREFLIGHT-RUN-001", "DSHASH-PREFLIGHT",
                              purpose="secondo tentativo", caller="preflight_simulation.py")
        check("second_final_holdout_access_blocked", False, "secondo accesso NON bloccato!")
    except ValidationAccessViolation:
        check("second_final_holdout_access_blocked", True)

    # ------------------------------------------------------------------
    # Check 24-25: Dataset Version Guard - drift rilevato su componenti
    # cambiati, rebuild identico produce lo stesso hash.
    # ------------------------------------------------------------------
    ds_registry_path = os.path.join(PHASE7_DIR, "preflight_output", "_dataset_version_registry_preflight_demo.json")
    if os.path.exists(ds_registry_path):
        os.remove(ds_registry_path)
    ds_registry = DatasetVersionRegistry(ds_registry_path)
    base_components = {"source_manifest_hash": "demo123", "date_range": ["2023-02-04", "2026-09-16"],
                        "instrument": "XAUUSD", "timeframe": "TICK", "transform_version": "v1"}
    r_first = ds_registry.register_or_check("PREFLIGHT_DS_DEMO", base_components)
    r_identical = ds_registry.register_or_check("PREFLIGHT_DS_DEMO", dict(base_components))
    check("dataset_identical_rebuild_same_hash", r_identical["status"] == "MATCH" and r_identical["hash"] == r_first["hash"])
    try:
        assert_no_drift(ds_registry, "PREFLIGHT_DS_DEMO", dict(base_components, transform_version="v2_DRIFTED"))
        check("dataset_drift_detected", False, "drift NON rilevato!")
    except DatasetVersionDriftError:
        check("dataset_drift_detected", True)
    if os.path.exists(ds_registry_path):
        os.remove(ds_registry_path)

    # ------------------------------------------------------------------
    # Check 26: holdout sealed - se materialize_partitions.py e' gia'
    # stato eseguito sul dataset reale, il sigillo deve esistere ed
    # essere SEALED (letto, non ricalcolato qui).
    # ------------------------------------------------------------------
    seal_path = os.path.join(PHASE7_DIR, "final_holdout_seal_v1.json")
    if os.path.exists(seal_path):
        with open(seal_path, encoding="utf-8") as fh:
            seal = json.load(fh)["payload"]
        check("holdout_sealed", seal.get("sealed_status") == "SEALED")
    else:
        check("holdout_sealed", False, "final_holdout_seal_v1.json non ancora prodotto")

    # ------------------------------------------------------------------
    # Check 27: serializzazione end-to-end del candidato - Setup Candidate
    # -> Signature -> Registry -> Baseline Contract -> Split Contract ->
    # Access Ledger -> Outcome Surface -> Dependence Diagnostics ->
    # Candidate Result v2, senza interpretazione manuale fra i pezzi.
    # ------------------------------------------------------------------
    e2e_signature = canonical_signature("SYNTH_SWEEP", "BUY",
                                         [{"feature_id": "volatility_state", "operator": "==", "threshold": "HIGH"}],
                                         "P(+1R before -1R)")
    e2e_candidate_id = "E2E-CAND-001"
    e2e_registry_entry = {"candidate_id": e2e_candidate_id, "signature": signature_hash(e2e_signature),
                           "lifecycle_state": "GENERATED", "baseline_contract_version": "BASELINE_ENGINE_V4_CONTRACT/schema_version=4"}
    e2e_lifecycle = Candidate(e2e_candidate_id)
    e2e_lifecycle.transition("DISCOVERY_SIGNAL")
    e2e_access = ledger.record_access(e2e_candidate_id, "internal_validation", "PREFLIGHT-RUN-001", "DSHASH-PREFLIGHT",
                                       purpose="e2e demo", caller="preflight_simulation.py")
    e2e_dep = compare_event_vs_episode_view(fx["event_rows"][:20],
                                             {r: fx["direction_by_row"][r] for r in fx["event_rows"][:20]},
                                             {r: fx["outcome_by_row"][r] for r in fx["event_rows"][:20]},
                                             materiality_threshold_delta_p=0.10, baseline_p_func=fake_baseline_p)
    e2e_candidate_result = {
        "identity": {"candidate_id": e2e_candidate_id, "signature": e2e_registry_entry["signature"]},
        "lifecycle_state": e2e_lifecycle.state,
        "access_ledger_ref": e2e_access["access_id"],
        "dependence_diagnostics_ref": e2e_dep["dependence_sensitive"],
        "baseline_contract_version": e2e_registry_entry["baseline_contract_version"],
    }
    e2e_chain_ok = all([
        e2e_registry_entry["signature"] == signature_hash(e2e_signature),
        e2e_lifecycle.state == "DISCOVERY_SIGNAL",
        e2e_access["candidate_id"] == e2e_candidate_id,
        "dependence_sensitive" in e2e_dep,
        e2e_candidate_result["identity"]["candidate_id"] == e2e_candidate_id,
    ])
    check("candidate_end_to_end_serialization", e2e_chain_ok)

    n_pass = sum(1 for r in RESULTS if r["status"] == "PASS")
    n_fail = sum(1 for r in RESULTS if r["status"] == "FAIL")
    print(f"\n=== Risultato preflight: {n_pass} PASS, {n_fail} FAIL su {len(RESULTS)} check ===")

    # ==================================================================
    # Output artifacts (sec.22) - istanze REALI ma su dati sintetici,
    # tutte etichettate SYNTHETIC_FIXTURE_ONLY.
    # ==================================================================
    run_manifest = {
        "SYNTHETIC_FIXTURE_ONLY": True,
        "run_id": "PREFLIGHT-RUN-001",
        "phase": "phase7_preflight",
        "purpose": "Dry-run di verifica gate - NON una discovery run reale (nessun dato di mercato).",
        "dataset_id": "SYNTHETIC_FIXTURE_V1 (synthetic_fixtures.py, seed=42)",
        "split_boundaries": boundaries,
        "n_synthetic_events": len(fx["event_rows"]),
        "n_synthetic_controls_pool": len(fx["control_pool"]),
        "checks_summary": {"n_pass": n_pass, "n_fail": n_fail, "n_total": len(RESULTS)},
        "checks_detail": RESULTS,
    }
    save_json(os.path.join(OUT_DIR, "discovery_run_manifest_v2.json"),
              wrap_with_provenance(run_manifest, "phase7/preflight_simulation.py"))

    candidate_registry = {
        "SYNTHETIC_FIXTURE_ONLY": True,
        "run_id": "PREFLIGHT-RUN-001",
        "candidates": [
            {"candidate_id": "SYNTH-CAND-001", "signature": signature_hash(sig_a), "lifecycle_state": "GENERATED",
             "complexity_level": 2, "note": "Candidato valido di riferimento (BUY, HIGH vol, UP trend)."},
            {"candidate_id": "SYNTH-CAND-001-DUP", "signature": signature_hash(sig_b), "lifecycle_state": "REJECTED_DUPLICATE",
             "duplicate_of": "SYNTH-CAND-001",
             "note": "Stesse condizioni di SYNTH-CAND-001 in ordine diverso - rifiutato come duplicato (Check 3)."},
            {"candidate_id": "SYNTH-CAND-002", "signature": signature_hash(sig_c), "lifecycle_state": "GENERATED",
             "complexity_level": 2, "note": "Stesse condizioni ma direzione SELL - NON un duplicato (Check 3)."},
            {"candidate_id": "SYNTH-CAND-REJECTED-LEAKY", "signature": None, "lifecycle_state": "REJECTED_LEAKAGE",
             "rejected_feature": fx["fake_leaky_feature"]["feature_id"],
             "note": "Generazione rifiutata: feature con leakage_risk=HIGH (Check 2)."},
            {"candidate_id": "SYNTH-CAND-LIFECYCLE-001", "signature": None, "lifecycle_state": c.state,
             "note": "Usato per dimostrare il blocco di transizione illegale (Check 8)."},
        ],
    }
    save_json(os.path.join(OUT_DIR, "candidate_registry_v2.json"),
              wrap_with_provenance(candidate_registry, "phase7/preflight_simulation.py"))

    mt_report_out = dict(mt_report)
    mt_report_out["SYNTHETIC_FIXTURE_ONLY"] = True
    save_json(os.path.join(OUT_DIR, "multiple_testing_report_v2.json"),
              wrap_with_provenance(mt_report_out, "phase7/preflight_simulation.py"))

    dep_out = dict(dep_result)
    dep_out["SYNTHETIC_FIXTURE_ONLY"] = True
    dep_out["note"] = "Prodotto da dependence_diagnostics_v2.compare_event_vs_episode_view su synthetic_fixtures.py - nessun dato di mercato."
    save_json(os.path.join(OUT_DIR, "dependence_diagnostics_v2.json"),
              wrap_with_provenance(dep_out, "phase7/preflight_simulation.py"))

    print(f"\nArtifact scritti in: {os.path.relpath(OUT_DIR, os.path.join(PHASE7_DIR, '..', '..', '..'))}")
    return n_fail == 0


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
