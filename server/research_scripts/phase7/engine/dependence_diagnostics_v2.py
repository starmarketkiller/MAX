#!/usr/bin/env python3
"""Phase 7 sec.10-11 - Dependence-aware discovery, nativo (non piu' un
audit retroattivo). Estende il modulo generico gia' costruito in
Phase 6.5 (server/research_scripts/phase6_5/dependence_diagnostics.py,
riusato qui via import, non riscritto) aggiungendo il confronto
EVENT VIEW vs EPISODE VIEW richiesto da sec.11.

EVENT VIEW: ogni evento osservato singolarmente (n_nominal pieno).
EPISODE VIEW: eventi vicini (stesso cluster, soglia dichiarata in
dependence_diagnostics.assign_clusters) collassati in UN solo episodio
rappresentativo (il PRIMO evento del cluster, temporalmente - scelta
dichiarata qui, non "quello con l'outcome migliore", che sarebbe
cherry-picking).

Se l'effetto (P(target) - baseline) esiste nella EVENT VIEW ma collassa
(scende sotto la soglia di materialita' o cambia segno) nella EPISODE
VIEW, il candidato viene marcato DEPENDENCE_SENSITIVE - nessuna
promozione e' ammessa basandosi solo sulla EVENT VIEW quando questo
accade.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "phase6_5"))
from dependence_diagnostics import (  # noqa: E402
    compute_gaps, clustering_rate, assign_clusters, outcome_autocorrelation,
    ess_autocorrelation, overlap_classification, full_dependence_report,
)


def episode_view(rows, direction_by_row, outcome_by_row, cluster_gap_threshold=10):
    """Collassa gli eventi in episodi: un episodio = un cluster di eventi
    vicini (gap <= cluster_gap_threshold), rappresentato dal PRIMO evento
    del cluster (temporalmente) - scelta dichiarata, non selezionata per
    massimizzare l'effetto."""
    clusters, _ = assign_clusters(rows, cluster_gap_threshold)
    episode_rows = [c[0] for c in clusters]  # primo evento di ogni cluster
    episode_directions = {r: direction_by_row[r] for r in episode_rows}
    episode_outcomes = {r: outcome_by_row[r] for r in episode_rows}
    return episode_rows, episode_directions, episode_outcomes


def compare_event_vs_episode_view(rows, direction_by_row, outcome_by_row,
                                   materiality_threshold_delta_p, baseline_p_func,
                                   cluster_gap_threshold=10):
    """baseline_p_func(rows, direction_by_row) -> baseline_probability
    dichiarato come funzione esterna, perche' il baseline dipende dal
    contesto del candidato (vedi Baseline Engine v4) - questo modulo non
    lo ricalcola da solo, riceve la logica di baseline gia' pronta."""
    def observed_p(rws):
        outs = [outcome_by_row[r] for r in rws if outcome_by_row.get(r) is not None]
        if not outs:
            return None, 0
        wins = sum(1 for o in outs if o == 1.0)
        return wins / len(outs), len(outs)

    ev_p, ev_n = observed_p(rows)
    ev_baseline_p = baseline_p_func(rows, direction_by_row)
    ev_delta_p = (ev_p - ev_baseline_p) if (ev_p is not None and ev_baseline_p is not None) else None

    ep_rows, ep_dir, ep_out = episode_view(rows, direction_by_row, outcome_by_row, cluster_gap_threshold)
    ep_p, ep_n = observed_p(ep_rows)
    ep_baseline_p = baseline_p_func(ep_rows, ep_dir)
    ep_delta_p = (ep_p - ep_baseline_p) if (ep_p is not None and ep_baseline_p is not None) else None

    collapsed = False
    if ev_delta_p is not None and ep_delta_p is not None:
        sign_flip = (ev_delta_p > 0) != (ep_delta_p > 0)
        below_materiality = abs(ep_delta_p) < materiality_threshold_delta_p
        collapsed = sign_flip or below_materiality

    return {
        "event_view": {"n": ev_n, "observed_p": ev_p, "baseline_p": ev_baseline_p, "delta_p": ev_delta_p},
        "episode_view": {"n": ep_n, "observed_p": ep_p, "baseline_p": ep_baseline_p, "delta_p": ep_delta_p,
                          "n_episodes": len(ep_rows), "representative_rule": "first event in cluster (temporal), not best-outcome"},
        "dependence_sensitive": collapsed,
        "materiality_threshold_used": materiality_threshold_delta_p,
    }


if __name__ == "__main__":
    # Dimostrazione con dati sintetici (nessun dato di mercato reale) - vedi
    # preflight_simulation.py per il dry-run completo su fixture strutturata.
    import random
    random.seed(7)
    # 50 eventi "veri" (episodi indipendenti), ciascuno ripetuto 1-4 volte
    # ravvicinato (simula clustering) - l'effetto e' reale MA piccolo per
    # dimostrare che l'EPISODE VIEW lo mantiene comunque visibile (non e'
    # un esempio di falso positivo, e' solo una demo di meccanica).
    rows, direction_by_row, outcome_by_row = [], {}, {}
    r = 0
    for episode in range(50):
        r += random.randint(15, 30)
        n_repeats = random.choice([1, 1, 2, 3, 4])
        outcome = 1.0 if random.random() < 0.60 else 0.0
        for _ in range(n_repeats):
            rows.append(r)
            direction_by_row[r] = 1
            outcome_by_row[r] = outcome
            r += random.randint(1, 3)

    def fake_baseline(rws, dir_by_row):
        return 0.50  # baseline fissa di comodo per la demo

    result = compare_event_vs_episode_view(rows, direction_by_row, outcome_by_row,
                                            materiality_threshold_delta_p=0.10,
                                            baseline_p_func=fake_baseline)
    import json
    print(json.dumps(result, indent=2, default=str))
