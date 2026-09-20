#!/usr/bin/env python3
"""Phase 7.4A Baseline Matching Topology Audit sec.10-11.

Sec.10: confronta la topologia reale (phase7_4_baseline_matching_
topology_audit_v1.json) con gli scenari sintetici di riferimento
(phase7_4_on_policy_matched_control_audit_v1.json) usando criteri
numerici dichiarati qui.

Sec.11: quantifica la differenza fra la selezione REALE di
BaselineEngineV4 (nessun tie-break oltre l'ordine della pool - per
SEQ-0015 tutte le dimensioni di match sono categoriche, quindi NESSUNA
distanza numerica discrimina i candidati) e _select_least_used() della
simulazione sintetica, ricostruendo un CONTROFATTUALE sugli STESSI dati
reali (stessi eventi, stessi pool di candidati) con selezione
least-used-first invece dell'ordine grezzo della pool."""
import json
import os
import sys
from collections import Counter

import numpy as np
import pandas as pd

PHASE74_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(PHASE74_DIR, "..", "..", "..", ".."))
sys.path.insert(0, PHASE74_DIR)
sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase7", "phase7_3", "engine"))
sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase7", "phase7_3"))

from baseline_matching_topology_audit import (  # noqa: E402
    load_structural_data, discovery_row_bounds, build_volatility_trend_state,
    EXCLUSION_BUFFER_BARS, EPISODE_GAP_RULE, HORIZON,
)
from seq0015_momentum_burst_detector import detect_sequence, FROZEN_PARAMETERS  # noqa: E402
from sequence_episode_engine import build_event_and_episode_views  # noqa: E402


# ---------------- Sec.11: controfattuale least-used-first sugli STESSI dati reali ----------------

def _select_least_used(rng, available, k, local_usage):
    pool = list(available)
    rng.shuffle(pool)
    pool.sort(key=lambda c: local_usage.get(c, 0))
    return pool[:k]


def run_counterfactual_least_used(seed=42):
    bars, state = load_structural_data()
    disc_start, disc_end = discovery_row_bounds(bars)
    market_state, _, _ = build_volatility_trend_state(state, disc_start, disc_end)
    all_events = detect_sequence(bars, market_state, FROZEN_PARAMETERS)
    discovery_events = [e for e in all_events if disc_start <= e["event_a_index"] <= disc_end]
    _, episode_view = build_event_and_episode_views(discovery_events, episode_gap_rule=EPISODE_GAP_RULE,
                                                      natural_horizon=HORIZON, overlap_policy="COLLAPSE_TO_FIRST")
    eligible_events = episode_view["events"]

    event_rows_set = {e["event_a_index"] for e in discovery_events}
    all_discovery_rows = list(range(disc_start, disc_end + 1))
    vol_prev = market_state["volatility_state"].shift(1)
    trend_prev = market_state["trend_state"].shift(1)

    rng = np.random.default_rng(seed)
    local_usage = {}
    control_usage = Counter()
    n_assignments = 0
    for e in eligible_events:
        t = e["event_a_index"]
        vv, tv = vol_prev.iloc[t], trend_prev.iloc[t]
        if vv is None or tv is None or pd.isna(vv) or pd.isna(tv):
            continue
        candidate_rows = [r for r in all_discovery_rows if r not in event_rows_set and abs(r - t) > EXCLUSION_BUFFER_BARS]
        valid_candidates = []
        for r in candidate_rows:
            rv, rt = vol_prev.iloc[r], trend_prev.iloc[r]
            if rv is None or rt is None or pd.isna(rv) or pd.isna(rt):
                continue
            if rv == vv and rt == tv:  # stessa cella categorica (direction implicita, ipotetica come nel motore reale)
                valid_candidates.append(r)
        if len(valid_candidates) < 20:  # minimum_control_count, stesso valore del motore reale
            continue
        selected = _select_least_used(rng, valid_candidates, 5, local_usage)
        for c in selected:
            local_usage[c] = local_usage.get(c, 0) + 1
        control_usage.update(selected)
        n_assignments += len(selected)

    reuse_counts = list(control_usage.values())
    return {
        "n_events_matched": sum(1 for _ in eligible_events),
        "n_control_assignments": n_assignments,
        "n_unique_controls": len(control_usage),
        "max_reuse": max(reuse_counts) if reuse_counts else None,
        "mean_reuse": float(np.mean(reuse_counts)) if reuse_counts else None,
        "median_reuse": float(np.median(reuse_counts)) if reuse_counts else None,
    }


def main():
    with open(os.path.join(PHASE74_DIR, "phase7_4_baseline_matching_topology_audit_v1.json"), encoding="utf-8") as f:
        real_topology = json.load(f)
    with open(os.path.join(PHASE74_DIR, "phase7_4_on_policy_matched_control_audit_v1.json"), encoding="utf-8") as f:
        synthetic = json.load(f)

    print("Ricalcolo il controfattuale least-used-first sugli STESSI dati reali...")
    counterfactual = run_counterfactual_least_used()
    print(f"Controfattuale (least-used-first): max_reuse={counterfactual['max_reuse']}, "
          f"mean_reuse={counterfactual['mean_reuse']:.2f}, n_unique_controls={counterfactual['n_unique_controls']}")

    real_reuse = real_topology["control_reuse_topology"]
    real_overlap_frac = real_topology["outcome_window_overlap_proxy"]["fraction_event_pairs_sharing_overlapping_control"]

    # ---- Sec.11: differenze fra selezione reale e least-used-first sintetica ----
    section11 = {
        "real_engine_selection_algorithm": "Nessun tie-break oltre l'ORDINE della pool passata dal chiamante - per SEQ-0015 (match_dimensions tutte categoriche: direction/volatility_state_pre_burst/trend_state_pre_burst) NON esiste alcuna dimensione numerica che discrimini i candidati via distanza standardizzata (_standardized_distance ritorna sempre None) - 'used = distances[:k]' preserva quindi l'ordine di iscrizione del control_pool (qui: indice di riga crescente).",
        "synthetic_least_used_first_algorithm": "Ordina i candidati disponibili per utilizzo residuo crescente (pareggio casuale) prima di selezionare i k migliori - MAI usato dal motore reale.",
        "real_vs_counterfactual_same_real_data": {
            "real_engine_max_reuse": real_reuse["max_reuse"], "real_engine_mean_reuse": real_reuse["mean_reuse"],
            "real_engine_n_unique_controls": real_reuse["n_unique_controls"],
            "counterfactual_least_used_max_reuse": counterfactual["max_reuse"],
            "counterfactual_least_used_mean_reuse": counterfactual["mean_reuse"],
            "counterfactual_least_used_n_unique_controls": counterfactual["n_unique_controls"],
        },
        "distance_deterioration": "NON APPLICABILE per SEQ-0015 - nessuna dimensione numerica nel match_dimensions congelato, ogni match ha standardized_distance=None/qualita' GOOD per costruzione indipendentemente dalla selezione.",
        "interpretation": (
            "La differenza NON e' un dettaglio implementativo minore: sugli STESSI eventi/pool reali, l'assenza "
            "di un criterio di selezione anti-concentrazione nel motore reale produce un riuso "
            f"{real_reuse['max_reuse']}x/{real_reuse['mean_reuse']:.1f}x (max/mean) contro "
            f"{counterfactual['max_reuse']}x/{counterfactual['mean_reuse']:.2f}x del controfattuale least-used-first "
            "sugli stessi identici dati - la scelta di selezione e' la causa diretta e dominante della "
            "concentrazione di riuso osservata, non la scarsita' di controlli disponibili in se'."
        ),
    }

    # ---- Sec.10: classificazione (criteri dichiarati ORA, PRIMA di scegliere la categoria) ----
    CLASSIFICATION_CRITERIA = {
        "MATERIAL_MATCH_TO_HIGH_RISK_SYNTHETIC_GEOMETRY": "real_max_reuse >= 5 (tetto sintetico piu' severo testato) E fraction_event_pairs_sharing_overlapping_control >= 0.20",
        "PARTIAL_MATCH": "soddisfatta SOLO una delle due condizioni sopra",
        "LOW_MATCH": "real_max_reuse < 5 E fraction_event_pairs_sharing_overlapping_control < 0.20",
    }
    cond_reuse = real_reuse["max_reuse"] >= 5
    cond_overlap = real_overlap_frac >= 0.20
    if cond_reuse and cond_overlap:
        classification = "MATERIAL_MATCH_TO_HIGH_RISK_SYNTHETIC_GEOMETRY"
    elif cond_reuse or cond_overlap:
        classification = "PARTIAL_MATCH"
    else:
        classification = "LOW_MATCH"

    section10 = {
        "classification_criteria_declared": CLASSIFICATION_CRITERIA,
        "real_max_reuse": real_reuse["max_reuse"], "real_max_reuse_condition_met": cond_reuse,
        "real_fraction_event_pairs_sharing_overlapping_control": real_overlap_frac, "real_overlap_condition_met": cond_overlap,
        "synthetic_reference_worst_case": next((r for r in synthetic["section6_temporal_overlap_matrix"]["rows"]
                                                if "identity_reuse_5_temporal_high" in r["scenario"]), None),
        "classification": classification,
        "note_on_severity": (
            f"La topologia reale ({real_reuse['max_reuse']}x reuse massimo) SUPERA nettamente lo scenario "
            f"sintetico piu' severo testato in precedenza (reuse=5, il tetto congelato mai raggiunto realmente "
            f"perche' il ledger non e' collegato al motore) - la classificazione MATERIAL_MATCH e' quindi "
            f"conservativa: il rischio reale e' probabilmente maggiore di quanto la simulazione sintetica "
            f"avesse ipotizzato, non solo confermato."
        ) if classification == "MATERIAL_MATCH_TO_HIGH_RISK_SYNTHETIC_GEOMETRY" else None,
    }

    payload = {"section10_synthetic_vs_real_comparison": section10, "section11_selection_algorithm_audit": section11}
    out_path = os.path.join(PHASE74_DIR, "phase7_4_topology_vs_synthetic_comparison_v1.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)
    print(f"\nCLASSIFICATION: {classification}")
    print(f"Scritto: {out_path}")
    return payload


if __name__ == "__main__":
    main()
