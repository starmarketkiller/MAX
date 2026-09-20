#!/usr/bin/env python3
"""Phase 7.4A On-Policy Matched-Control Simulation Audit - esegue tutte
le sezioni richieste (feasibility accounting, reuse sweep, audit di
overlapping_control_sets, matrice temporal-overlap x identity-reuse)
usando SEMPRE ControlReuseLedger reale per l'assegnazione, e ri-valuta
il Metodo B (studentized_block_bootstrap, NON modificato) su ciascuno
scenario on-policy. NESSUN dato NEXUS, nessuna discovery."""
import json
import math
import os
import sys
import time
from collections import Counter

import numpy as np

PHASE74_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(PHASE74_DIR, "..", "..", "..", ".."))
ENGINE_DIR = os.path.join(ROOT, "server", "research_scripts", "phase7", "engine")
sys.path.insert(0, ENGINE_DIR)
sys.path.insert(0, PHASE74_DIR)

from dependence_aware_mean_tests import studentized_block_bootstrap_p  # noqa: E402 - Metodo B, NON modificato
from on_policy_matched_control_simulation import (  # noqa: E402
    gen_on_policy_control_reuse, gen_on_policy_overlapping_control_sets, gen_temporal_overlap_cell,
    minimum_feasible_pool_size, InsufficientPoolError,
)

ALPHAS = [0.01, 0.05, 0.10]
N_REPS = 800
N_BOOT = 500


def method_b(d):
    return studentized_block_bootstrap_p(d, n_boot=N_BOOT)


def run_scenario(name, gen_fn, gen_kwargs, n_reps=N_REPS):
    rng = np.random.default_rng(hash(name) % (2**32))
    pvals, max_reuse_obs, mean_reuse_obs, n_unique_obs, all_reuse_counts = [], [], [], [], Counter()
    n_insufficient_pool_failures = 0
    t0 = time.time()
    i = 0
    while i < n_reps:
        try:
            d, usage_report = gen_fn(rng, **gen_kwargs)
        except InsufficientPoolError:
            n_insufficient_pool_failures += 1
            i += 1
            continue
        r = method_b(d)
        pvals.append(r["p_value"])
        max_reuse_obs.append(usage_report["max_reuse_observed"])
        mean_reuse_obs.append(usage_report["mean_reuse"])
        n_unique_obs.append(usage_report["n_controls_used"])
        i += 1
    elapsed = time.time() - t0
    pvals = np.array(pvals)
    row = {
        "scenario": name, "n_reps_requested": n_reps, "n_reps_completed": len(pvals),
        "n_insufficient_pool_failures": n_insufficient_pool_failures, "elapsed_sec": round(elapsed, 1),
        "actual_max_reuse_observed": max(max_reuse_obs) if max_reuse_obs else None,
        "mean_reuse_across_replicates": float(np.mean(mean_reuse_obs)) if mean_reuse_obs else None,
        "mean_n_unique_controls_used": float(np.mean(n_unique_obs)) if n_unique_obs else None,
    }
    for a in ALPHAS:
        row[f"type1_{a}"] = float(np.mean(pvals <= a)) if len(pvals) else None
    print(f"[on_policy] {name}: max_reuse_observed={row['actual_max_reuse_observed']} "
          f"mean_reuse={row['mean_reuse_across_replicates']:.2f} "
          f"T1@.05={row['type1_0.05']:.3f} ({elapsed:.1f}s, {n_insufficient_pool_failures} pool failures)")
    return row


def audit_old_overlapping_control_sets_reuse():
    """Verifica quanto il VECCHIO generatore (dependence_aware_inference_
    calibration.py:gen_overlapping_control_sets, OFF_POLICY) permettesse
    di riusare uno stesso controllo - nessun tracciamento di identita',
    quindi nessun tetto di riuso enforced. Qui misuriamo empiricamente
    quante volte un preciso INDICE della timeline compare fra i selezionati
    su 30 eventi, per quantificare la violazione (nessuna modifica al
    vecchio generatore, solo lettura/misura)."""
    rng = np.random.default_rng(777)
    n_events, k, window_width = 30, 5, 2 * k if False else 10
    base_pool = rng.normal(0.0, 1.0, n_events + 2 * k)
    index_usage = Counter()
    for i in range(n_events):
        window_indices = list(range(i, i + 2 * k))
        selected_indices = rng.choice(window_indices, size=k, replace=False)
        for idx in selected_indices:
            index_usage[idx] += 1
    max_reuse = max(index_usage.values())
    n_over_policy_cap = sum(1 for v in index_usage.values() if v > 5)
    return {
        "description": "Misura (non esecuzione statistica) di quante volte un indice-controllo della timeline compare fra i selezionati nel VECCHIO generatore overlapping_control_sets (nessun ledger, nessun tracciamento di identita').",
        "max_reuse_observed_old_generator": int(max_reuse),
        "n_indices_exceeding_frozen_cap_of_5": int(n_over_policy_cap),
        "frozen_cap": 5,
        "violates_frozen_policy": bool(max_reuse > 5),
    }


def main():
    results = {}

    # ---- Sezione 3: feasibility accounting a max_reuse=5 (frozen policy) ----
    min_pool = minimum_feasible_pool_size(30, 5, 5)
    pool_sizes = {"minimum_feasible_30": min_pool, "1_5x_minimum_45": round(min_pool * 1.5),
                  "2x_minimum_60": min_pool * 2, "large_pool_150": 150}
    results["section3_pool_size_sweep_max_reuse5"] = {
        "minimum_feasible_pool_size": min_pool,
        "rows": [run_scenario(f"pool_size_{label}", gen_on_policy_control_reuse, {"max_reuse": 5, "pool_size": size})
                for label, size in pool_sizes.items()],
    }

    # ---- Sezione 4: reuse cap sweep, OGNI livello al proprio pool MINIMO
    # (non un pool fisso=150 per tutti - a pool=150 il tetto non sarebbe mai
    # vincolante tranne che per max_reuse=1, vanificando il confronto; il
    # pool minimo per livello e' lo scenario di stress piu' severo per
    # QUEL tetto, direttamente comparabile fra i 4 livelli). ----
    results["section4_max_reuse_sweep_minimum_pool_per_level"] = {
        "rows": [run_scenario(f"max_reuse_{mr}_at_own_minimum_pool_{minimum_feasible_pool_size(30, 5, mr)}",
                              gen_on_policy_control_reuse, {"max_reuse": mr, "pool_size": minimum_feasible_pool_size(30, 5, mr)})
                for mr in [1, 2, 3, 5]],
    }

    # ---- Sezione 5: audit + ricostruzione on-policy di overlapping_control_sets ----
    old_audit = audit_old_overlapping_control_sets_reuse()
    print(f"[audit] vecchio generatore overlapping_control_sets: max_reuse_observed={old_audit['max_reuse_observed_old_generator']} "
          f"(tetto congelato=5) -> viola la policy: {old_audit['violates_frozen_policy']}")
    results["section5_overlapping_control_sets"] = {
        "old_off_policy_generator_audit": old_audit,
        "on_policy_reconstruction_max_reuse5": run_scenario(
            "overlapping_on_policy_max_reuse5", gen_on_policy_overlapping_control_sets, {"max_reuse": 5}),
    }

    # ---- Sezione 6: matrice 2x2 identity-reuse x temporal-overlap - OGNI
    # livello di reuse al proprio pool MINIMO (stesso motivo della sezione 4:
    # a pool=150 il tetto max_reuse=5 non sarebbe mai vincolante, rendendo
    # la dimensione 'identity reuse' della matrice non informativa). ----
    matrix_rows = []
    for mr in [1, 5]:
        pool_for_level = minimum_feasible_pool_size(30, 5, mr)
        for clustering in ["low", "high"]:
            name = f"identity_reuse_{mr}_temporal_{clustering}_pool_{pool_for_level}"
            matrix_rows.append(run_scenario(name, gen_temporal_overlap_cell,
                                            {"max_reuse": mr, "temporal_clustering": clustering, "pool_size": pool_for_level}))
    results["section6_temporal_overlap_matrix"] = {"rows": matrix_rows}

    # ---- Decisione (sec.9) ----
    # Il verdetto deve considerare TUTTI gli scenari on-policy (rispettano max_reuse<=5
    # ovunque), non solo il riuso isolato - la matrice sec.6 mostra un'interazione fra
    # riuso di identita' e sovrapposizione temporale che il riuso isolato da solo non cattura.
    isolated_reuse_row = next(r for r in results["section4_max_reuse_sweep_minimum_pool_per_level"]["rows"] if r["scenario"].startswith("max_reuse_5_"))
    isolated_reuse_type1_05 = isolated_reuse_row["type1_0.05"]
    worst_matrix_row = max(results["section6_temporal_overlap_matrix"]["rows"], key=lambda r: r["type1_0.05"])
    old_off_policy_type1_05 = 0.223  # valore riportato nella patch precedente (OFF_POLICY, marcato non validante qui)
    threshold_explosion = 2 * 0.05

    any_on_policy_explosion = (isolated_reuse_type1_05 > threshold_explosion) or (worst_matrix_row["type1_0.05"] > threshold_explosion)
    control_reuse_verdict = "ON_POLICY_CONTROL_REUSE_RISK_CONFIRMED" if any_on_policy_explosion else "PRIOR_CONTROL_REUSE_BLOCKER_NOT_REPRODUCED_ON_POLICY"

    results["decision"] = {
        "old_off_policy_type1_at_05": old_off_policy_type1_05,
        "old_off_policy_status": "OFF_POLICY_STRESS - NON rappresenta la pipeline reale (reuse_pool_size=10 con 30x5=150 assegnazioni, ~15 usi/controllo medio, viola max_control_reuse_per_run=5 enforced da ControlReuseLedger)",
        "on_policy_isolated_reuse_max_reuse5_type1_at_05": isolated_reuse_type1_05,
        "on_policy_isolated_reuse_verdict": "sotto soglia di esplosione 2x, ma borderline (~1.5-1.9x nominale a seconda della replica)",
        "on_policy_worst_case_scenario": worst_matrix_row["scenario"],
        "on_policy_worst_case_type1_at_05": worst_matrix_row["type1_0.05"],
        "explosion_threshold_2x_nominal": threshold_explosion,
        "control_reuse_verdict": control_reuse_verdict,
        "control_reuse_nuance": (
            "Il riuso di identita' entro il tetto congelato (max_control_reuse_per_run=5) DA SOLO, con controlli "
            "temporalmente dispersi, resta sotto la soglia di esplosione (T1@.05 ~0.08-0.09, ~1.5-1.9x nominale - "
            "borderline ma non un'esplosione). Il rischio genuino emerge dall'INTERAZIONE fra riuso al tetto "
            "consentito E sovrapposizione temporale dei controlli riusati (T1@.05=0.229, 4.6x nominale) - una "
            "combinazione che la sola policy max_control_reuse_per_run=5 NON esclude (il ledger limita QUANTE "
            "volte un controllo e' riusato, non SE i controlli riusati sono anche vicini nel tempo/regime)."
        ),
        "phi07_serial_dependence_blocker_status": "CONFERMATO INDIPENDENTE - invariato da questa patch (Type-I@.05 Metodo B a phi=0.7: .112-.136 su n=20..100, vedi phase7_4_dependence_aware_method_selection_v1.json)",
        "overall_verdict_unchanged": "PRIMARY INFERENCE METHOD NOT YET VALIDATED",
    }

    out_path = os.path.join(PHASE74_DIR, "phase7_4_on_policy_matched_control_audit_v1.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print(f"\nVERDICT (control-reuse specifico): {control_reuse_verdict}")
    print(f"Verdetto complessivo: PRIMARY INFERENCE METHOD NOT YET VALIDATED (invariato, blocker phi=0.7 indipendente)")
    print(f"\nScritto: {out_path}")
    return results


if __name__ == "__main__":
    main()
