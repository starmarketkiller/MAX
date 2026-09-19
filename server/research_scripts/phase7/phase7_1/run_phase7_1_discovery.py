#!/usr/bin/env python3
"""Phase 7.1 - Orchestratore della prima vera discovery run. Esegue,
IN ORDINE STRETTO e senza tornare indietro, la sequenza congelata in
phase7_1_frozen_spec_v1.json: discovery screening -> internal_validation
(via ValidationAccessLedger) -> locked_validation (ONE-SHOT via ledger)
-> final_holdout (ONE-SHOT, SOLO se un candidato raggiunge PASS su
locked_validation).

Il log dell'access ledger e' PERSISTITO su disco
(validation_access_log_p71.json) e ricaricato ad ogni esecuzione - se
questo script venisse rieseguito DOPO aver gia' letto locked_validation/
final_holdout per un candidato, un secondo tentativo verrebbe bloccato
meccanicamente da ValidationAccessViolation, non silenziosamente
ripetuto.

Integrity & Provenance Patch (post-review, 2026-09-19): la classificazione
del motivo di fallimento ad ogni fase ora usa SEMPRE
engine/discovery_gate_precedence.classify_discovery_outcome (precedenza
esplicita: pool insufficiente > n basso > DeltaP<=0 > dependence-sensitive
> CI sovrapposte) invece di if/elif ad hoc per fase - la Fase 1 di questa
prima run etichettava erroneamente su INSUFFICIENT_SAMPLE candidati con
campione adeguato che fallivano per DeltaP<=0 (corretto retroattivamente
sugli evidence record esistenti da apply_lifecycle_correction_p71.py,
senza ricalcolare alcun numero). Questo file e' stato corretto per le
run FUTURE - non e' stato ri-eseguito su dati reali per produrre questa
patch.
"""
import json
import os
import sys
from datetime import datetime, timezone

import pandas as pd

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", ".."))
DATA_DIR = os.path.join(ROOT, "server", "research_scripts", "phase7", "phase7_1", "data")
PHASE7_DIR = os.path.join(ROOT, "server", "research_scripts", "phase7")
sys.path.insert(0, os.path.join(PHASE7_DIR, "engine"))
sys.path.insert(0, os.path.join(PHASE7_DIR, "phase7_1"))

from candidate_lifecycle import Candidate, InvalidTransitionError  # noqa: E402
from candidate_signature import canonical_signature, signature_hash  # noqa: E402
from multiple_testing_v2 import run_family  # noqa: E402
from validation_access_ledger import ValidationAccessLedger, ValidationAccessViolation, load_policy  # noqa: E402
from cross_split_safety import assign_split  # noqa: E402
from candidate_stats_p71 import compute_candidate_stats  # noqa: E402
from splits_p71 import assign_split_p71, SPLIT_BOUNDARIES_DATES  # noqa: E402
from discovery_gate_precedence import classify_discovery_outcome  # noqa: E402

FROZEN_SPEC_PATH = os.path.join(PHASE7_DIR, "phase7_1", "phase7_1_frozen_spec_v1.json")
FROZEN_PARAMS_PATH = os.path.join(DATA_DIR, "frozen_baseline_parameters_p71.json")
ACCESS_LOG_PATH = os.path.join(DATA_DIR, "validation_access_log_p71.json")
RUN_ID = "PHASE7_1-FIRST-REAL-DISCOVERY-001"

DIRECTIONS = {
    "CAND-P71-RECLAIM-BOTH": "BOTH",
    "CAND-P71-RECLAIM-BUY": "BUY",
    "CAND-P71-RECLAIM-SELL": "SELL",
}
FAMILY_ID = "RECLAIM_FAMILY_P71"
MIN_MATERIAL_DELTA_P = 0.15
MIN_N = 30


def load_ledger():
    policy = load_policy()
    ledger = ValidationAccessLedger(policy)
    if os.path.exists(ACCESS_LOG_PATH):
        with open(ACCESS_LOG_PATH, encoding="utf-8") as f:
            log = json.load(f)
        for rec in log:
            ledger.log.append(rec)
            ledger._counts[(rec["candidate_id"], rec["split"])] = rec["access_count_for_candidate_split"]
    return ledger


def save_ledger(ledger):
    with open(ACCESS_LOG_PATH, "w", encoding="utf-8") as f:
        json.dump(ledger.export_log(), f, indent=2, default=str)


def build_index_boundaries(state: pd.DataFrame) -> dict:
    bounds = {}
    for name, (start, end) in SPLIT_BOUNDARIES_DATES.items():
        mask = (state["bar_time_utc"] >= start) & (state["bar_time_utc"] <= end)
        idx = state.index[mask]
        if len(idx) == 0:
            continue
        bounds[name] = (int(idx.min()), int(idx.max()) + 1)
    return bounds


def gates_check(stats, family_direction):
    """Ritorna (ok, reasons, dep_sensitive) - 'reasons' resta una lista
    DESCRITTIVA completa di tutte le gate fallite (per il log/print), ma
    la decisione di QUALE stato lifecycle assegnare in caso di fallimento
    e' demandata a discovery_gate_precedence.classify_discovery_outcome
    (unica fonte di verita' sulla precedenza - vedi Integrity &
    Provenance Patch, 2026-09-19)."""
    reasons = []
    ok = True
    if stats["n_events"] < MIN_N:
        ok = False
        reasons.append(f"n_events={stats['n_events']}<{MIN_N}")
    if stats["n_rejected_insufficient_pool"] > 0:
        ok = False
        reasons.append(f"{stats['n_rejected_insufficient_pool']} eventi con pool di controllo insufficiente")
    if stats["delta_p"] is None or stats["delta_p"] <= 0:
        ok = False
        reasons.append(f"delta_p={stats['delta_p']}<=0 o non calcolabile")
    elif stats["delta_p"] < MIN_MATERIAL_DELTA_P:
        ok = False
        reasons.append(f"delta_p={stats['delta_p']:.4f}<{MIN_MATERIAL_DELTA_P} (materialita' minima)")
    if not stats["ci95_non_overlapping"]:
        ok = False
        reasons.append("CI95 Wilson sovrapposte")
    dep_sensitive = stats["dependence"]["dependence_sensitive"] if stats["dependence"] else None
    if dep_sensitive:
        ok = False
        reasons.append("DEPENDENCE_SENSITIVE=true (effetto non stabile fra EVENT e EPISODE view)")
    return ok, reasons, dep_sensitive


def failure_state_for(stats, dep_sensitive):
    """Wrapper che chiama classify_discovery_outcome con i campi di
    'stats' gia' calcolati - unico punto in cui questo script decide lo
    stato lifecycle di un fallimento, per ogni fase (discovery/internal_
    validation/locked_validation)."""
    return classify_discovery_outcome(
        n_nominal=stats["n_events"], min_n=MIN_N, delta_p=stats["delta_p"],
        ci_non_overlapping=stats["ci95_non_overlapping"], dependence_sensitive=bool(dep_sensitive),
        n_rejected_insufficient_pool=stats["n_rejected_insufficient_pool"],
        materiality_threshold=MIN_MATERIAL_DELTA_P,
    )


def run_phase_for_candidate(candidate_id, direction, split_name, events_df, state_df, df, atr_col,
                             frozen_params, split_boundaries_idx, excluded_from_baseline):
    stats = compute_candidate_stats(split_name, direction, events_df, state_df, df, atr_col,
                                     frozen_params, split_boundaries_idx, excluded_from_baseline,
                                     materiality_threshold=MIN_MATERIAL_DELTA_P)
    ok, reasons, dep_sensitive = gates_check(stats, direction)
    return stats, ok, reasons, dep_sensitive


def main():
    with open(FROZEN_SPEC_PATH, encoding="utf-8") as f:
        spec = json.load(f)
    with open(FROZEN_PARAMS_PATH, encoding="utf-8") as f:
        frozen_params = json.load(f)

    df = pd.read_csv(os.path.join(DATA_DIR, "xauusd_h4_bars_p71.csv"), parse_dates=["bar_time_utc"]).sort_values("bar_time_utc").reset_index(drop=True)
    state = pd.read_csv(os.path.join(DATA_DIR, "market_state_dataset_p71.csv"), parse_dates=["bar_time_utc"]).sort_values("bar_time_utc").reset_index(drop=True)
    events = pd.read_csv(os.path.join(DATA_DIR, "events_p71.csv"))
    atr_col = state["atr"].values

    split_boundaries_idx = build_index_boundaries(state)
    n_by_split = {name: (end - start) for name, (start, end) in split_boundaries_idx.items()}
    print(f"split boundaries (row_index): {split_boundaries_idx}")
    print(f"n bars per split: {n_by_split}")

    sweep_rows = set(events.loc[events.event_family == "SWEEP", "row_index"].astype(int))
    reclaim_all_rows = set(events.loc[events.event_family == "RECLAIM", "row_index"].astype(int)) | \
        set(events.loc[events.event_family == "RECLAIM", "confirmed_at_row_index"].dropna().astype(int))
    excluded_from_baseline = sweep_rows | reclaim_all_rows

    ledger = load_ledger()
    lifecycles = {cid: Candidate(cid) for cid in DIRECTIONS}
    all_results = {}

    # ================= FASE 1: DISCOVERY SCREENING =================
    print("\n" + "=" * 70 + "\nFASE 1: DISCOVERY SCREENING (development.discovery)\n" + "=" * 70)
    discovery_comparisons = []
    for cid, direction in DIRECTIONS.items():
        stats, ok, reasons, dep_sensitive = run_phase_for_candidate(
            cid, direction, "discovery", events, state, df, atr_col, frozen_params, split_boundaries_idx, excluded_from_baseline)
        all_results.setdefault(cid, {})["discovery"] = stats
        lifecycles[cid].transition("DISCOVERY_SIGNAL", f"discovery screening completato: ok={ok}")
        print(f"[{cid}] n={stats['n_events']} delta_p={stats['delta_p']} ci_non_overlap={stats['ci95_non_overlapping']} "
              f"dependence_sensitive={dep_sensitive} gates_ok={ok} reasons={reasons}")
        ep = stats["event_probability"]
        bp = stats["baseline_probability"]
        discovery_comparisons.append({"id": cid, "wins_event": ep["wins"], "n_event": ep["n"],
                                       "wins_baseline": bp["wins"], "n_baseline": bp["n"]})
        if ok:
            lifecycles[cid].transition("INTERNAL_VALIDATION", "gate di discovery superate")
        else:
            # Integrity & Provenance Patch (2026-09-19): DISCOVERY_SIGNAL
            # ora ammette direttamente REFUTED/DEPENDENCE_SENSITIVE/BORDERLINE
            # oltre a INSUFFICIENT_SAMPLE/CONTAMINATED - la scelta fra questi
            # segue SEMPRE la precedenza di discovery_gate_precedence.py,
            # mai un default unico su INSUFFICIENT_SAMPLE.
            target_state, reason_code, human_reason = failure_state_for(stats, dep_sensitive)
            lifecycles[cid].transition(target_state, f"[{reason_code}] {human_reason}")

    mt_report_discovery = run_family(FAMILY_ID, discovery_comparisons, q=0.10)
    print(f"\nMultiple testing (discovery, famiglia={FAMILY_ID}): {json.dumps(mt_report_discovery['results'], indent=2, default=str)}")

    survivors = [cid for cid in DIRECTIONS if lifecycles[cid].state == "INTERNAL_VALIDATION"]
    print(f"\nCandidati che procedono a internal_validation: {survivors}")

    # ================= FASE 2: INTERNAL VALIDATION =================
    if survivors:
        print("\n" + "=" * 70 + "\nFASE 2: INTERNAL VALIDATION (development.internal_validation)\n" + "=" * 70)
    for cid in survivors:
        direction = DIRECTIONS[cid]
        access = ledger.record_access(cid, "internal_validation", RUN_ID, frozen_params.get("dataset_version_hash", "SEE_PHASE7_0B"),
                                       purpose="Phase 7.1 internal validation", caller="run_phase7_1_discovery.py")
        stats, ok, reasons, dep_sensitive = run_phase_for_candidate(
            cid, direction, "internal_validation", events, state, df, atr_col, frozen_params, split_boundaries_idx, excluded_from_baseline)
        all_results[cid]["internal_validation"] = stats
        print(f"[{cid}] access={access['access_id']} n={stats['n_events']} delta_p={stats['delta_p']} "
              f"ci_non_overlap={stats['ci95_non_overlapping']} dependence_sensitive={dep_sensitive} gates_ok={ok} reasons={reasons}")
        if ok:
            lifecycles[cid].transition("PRE_REGISTERED_CANDIDATE", "gate di internal_validation superate")
        else:
            target_state, reason_code, human_reason = failure_state_for(stats, dep_sensitive)
            lifecycles[cid].transition(target_state, f"[{reason_code}] {human_reason}")
    save_ledger(ledger)

    pre_registered = [cid for cid in DIRECTIONS if lifecycles[cid].state == "PRE_REGISTERED_CANDIDATE"]
    print(f"\nCandidati pre-registrati che procedono a locked_validation: {pre_registered}")

    # ================= FASE 3: LOCKED VALIDATION (ONE-SHOT) =================
    locked_results = {}
    if pre_registered:
        print("\n" + "=" * 70 + "\nFASE 3: LOCKED VALIDATION - ONE SHOT (locked_validation)\n" + "=" * 70)
    for cid in pre_registered:
        direction = DIRECTIONS[cid]
        access = ledger.record_access(cid, "locked_validation", RUN_ID, frozen_params.get("dataset_version_hash", "SEE_PHASE7_0B"),
                                       purpose="Phase 7.1 locked validation (one-shot)", caller="run_phase7_1_discovery.py")
        stats, ok, reasons, dep_sensitive = run_phase_for_candidate(
            cid, direction, "locked_validation", events, state, df, atr_col, frozen_params, split_boundaries_idx, excluded_from_baseline)
        all_results[cid]["locked_validation"] = stats
        locked_results[cid] = (stats, ok, reasons, dep_sensitive)
        print(f"[{cid}] access={access['access_id']} n={stats['n_events']} delta_p={stats['delta_p']} "
              f"ci_non_overlap={stats['ci95_non_overlapping']} dependence_sensitive={dep_sensitive} gates_ok={ok} reasons={reasons}")
        if ok:
            lifecycles[cid].transition("SUPPORTED", "gate di locked_validation (PASS) superate - tutte le gate soddisfatte")
        else:
            # INDEPENDENT_VALIDATION ammette gia' tutti gli stati che
            # classify_discovery_outcome puo' restituire (REFUTED,
            # DEPENDENCE_SENSITIVE, INSUFFICIENT_SAMPLE, BORDERLINE) -
            # nessuna eccezione di grafo qui, a differenza di discovery/
            # internal_validation.
            target_state, reason_code, human_reason = failure_state_for(stats, dep_sensitive)
            lifecycles[cid].transition(target_state, f"[{reason_code}] {human_reason}")
    save_ledger(ledger)

    supported = [cid for cid in DIRECTIONS if lifecycles[cid].state == "SUPPORTED"]

    # ================= FASE 4: FINAL HOLDOUT (CONDIZIONALE, ONE-SHOT) =================
    if supported:
        print("\n" + "=" * 70 + f"\nFASE 4: FINAL HOLDOUT - ONE SHOT ({len(supported)} candidato/i SUPPORTED su locked_validation)\n" + "=" * 70)
        for cid in supported:
            direction = DIRECTIONS[cid]
            access = ledger.record_access(cid, "final_holdout", RUN_ID, frozen_params.get("dataset_version_hash", "SEE_PHASE7_0B"),
                                           purpose="Phase 7.1 final holdout - conferma ultima (E3-equivalente)", caller="run_phase7_1_discovery.py")
            stats, ok, reasons, dep_sensitive = run_phase_for_candidate(
                cid, direction, "final_holdout", events, state, df, atr_col, frozen_params, split_boundaries_idx, excluded_from_baseline)
            all_results[cid]["final_holdout"] = stats
            print(f"[{cid}] access={access['access_id']} n={stats['n_events']} delta_p={stats['delta_p']} "
                  f"ci_non_overlap={stats['ci95_non_overlapping']} dependence_sensitive={dep_sensitive} gates_ok={ok} reasons={reasons}")
        save_ledger(ledger)
    else:
        print("\n" + "=" * 70 + "\nFASE 4: FINAL HOLDOUT - NON TOCCATO\n" + "=" * 70)
        print("Nessun candidato ha raggiunto SUPPORTED su locked_validation - final_holdout NON acceduto, per regola congelata.")

    final_states = {cid: lifecycles[cid].state for cid in DIRECTIONS}
    final_history = {cid: lifecycles[cid].history for cid in DIRECTIONS}
    print("\n" + "=" * 70 + "\nSTATI FINALI\n" + "=" * 70)
    for cid, st in final_states.items():
        print(f"  {cid}: {st}  (storia: {' -> '.join(final_history[cid])})")

    overall_verdict = "NO_SUPPORTED_CANDIDATE" if not supported else "SUPPORTED_CANDIDATE_FOUND"
    print(f"\n*** VERDETTO COMPLESSIVO Phase 7.1: {overall_verdict} ***")

    def strip_outcomes(d):
        out = {}
        for k, v in d.items():
            out[k] = {kk: (vv if kk != "event_outcomes" else len(vv)) for kk, vv in v.items()}
        return out

    output = {
        "run_id": RUN_ID,
        "family_id": FAMILY_ID,
        "final_lifecycle_states": final_states,
        "lifecycle_history": final_history,
        "multiple_testing_discovery": mt_report_discovery,
        "results_by_candidate": {cid: strip_outcomes({k: v for k, v in res.items()}) for cid, res in all_results.items()},
        "final_holdout_accessed_for": supported,
        "overall_verdict": overall_verdict,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
    out_path = os.path.join(DATA_DIR, "phase7_1_run_results.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, default=str)
    print(f"\nwritten: {out_path}")
    return output


if __name__ == "__main__":
    main()
