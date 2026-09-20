#!/usr/bin/env python3
"""Phase 7.3 sec.4 - Episode-first architecture. Phase 7.1 ha mostrato
il rischio di contare eventi correlati come osservazioni indipendenti
(RECLAIM: 179 eventi nominali -> 72 episodi, con un cambio di segno fra
EVENT VIEW ed EPISODE VIEW). Il Sequence Engine produce NATIVAMENTE
EVENT_VIEW ed EPISODE_VIEW per ogni batch di sequence_event - non
un'aggiunta finale opzionale.

Riusa dependence_diagnostics_v2.py (Phase 7.0) per la meccanica di
clustering - non reimplementata qui."""
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase7", "engine"))
from dependence_diagnostics_v2 import assign_clusters, episode_view as _episode_view_rows  # noqa: E402


class EpisodeRuleNotDeclaredError(Exception):
    pass


def build_outcome_independent_view(episode_view_events: list, outcome_overlap_embargo_bars: int) -> dict:
    """Phase 7.4A Integrity Patch sec.1 - event_cluster_rule (episode_gap_rule)
    e outcome_overlap_rule sono DUE concetti distinti, non lo stesso:

    - event_cluster_rule risponde 'e' la stessa espansione fisica locale?'
      (usato per costruire EPISODE_VIEW).
    - outcome_overlap_rule risponde 'le finestre di misura dell'outcome si
      sovrappongono, anche se le espansioni fisiche sono diverse?' - due
      episodi a gap>event_cluster_rule ma con outcome_window sovrapposte
      NON sono osservazioni indipendenti solo perche' superano il gap
      dell'episode clustering.

    Seconda passata di clustering (stesso meccanismo assign_clusters, MAI
    reimplementato) APPLICATA ai rappresentanti di EPISODE_VIEW (non ai
    raw event), con soglia = outcome_overlap_embargo_bars. Per una
    outcome window di larghezza natural_horizon barre che inizia a t+1,
    due eventi a t e t+d hanno finestre sovrapposte se e solo se d <
    natural_horizon, quindi l'embargo corretto e' natural_horizon-1 (MAI
    lo stesso valore numerico di event_cluster_rule - dichiararli uguali
    per errore vanificherebbe la distinzione concettuale).

    Ritorna INDEPENDENT_VIEW: il conteggio realmente usato per Wilson
    CI/two-proportion-test/bootstrap - MAI EPISODE_VIEW direttamente
    quando outcome_overlap_embargo_bars > event_cluster_rule (il caso
    normale, perche' natural_horizon >> event_cluster_rule per
    costruzione in ogni family finora formalizzata)."""
    if outcome_overlap_embargo_bars is None:
        raise EpisodeRuleNotDeclaredError(
            "outcome_overlap_embargo_bars deve essere dichiarato ex-ante (Phase 7.4A Integrity Patch sec.1) - "
            "nessun default silenzioso."
        )
    rows = sorted(e["event_a_index"] for e in episode_view_events)
    event_by_row = {e["event_a_index"]: e for e in episode_view_events}
    clusters, gaps = assign_clusters(rows, outcome_overlap_embargo_bars)
    representative_rows = [c[0] for c in clusters]  # COLLAPSE_TO_FIRST, stessa regola anti-cherry-pick
    independent_events = [event_by_row[r] for r in representative_rows]
    return {
        "n": len(representative_rows), "n_independent_observations": len(clusters),
        "events": independent_events,
        "representative_rule": "primo evento del cluster (embargo outcome-overlap, anti-cherry-pick, mai il migliore)",
        "outcome_overlap_embargo_bars": outcome_overlap_embargo_bars,
        "source_view": "EPISODE_VIEW (gia' collassata per event_cluster_rule) - seconda passata, non sui raw event",
    }


def build_event_and_episode_views(sequence_events: list, episode_gap_rule: int, natural_horizon: int,
                                   overlap_policy: str):
    """sequence_events: lista di dict conformi a sequence_detector_contract_v1.json
    (con almeno event_a_index, direction, e un outcome_by_event placeholder
    fornito dal chiamante - qui NON si calcola alcun outcome, solo la
    segmentazione episodica).

    episode_gap_rule/natural_horizon/overlap_policy DEVONO essere dichiarati
    ex-ante dal detector/frozen spec - la funzione rifiuta di procedere se
    mancano (sec.4: 'Ogni detector deve dichiarare ex-ante')."""
    if episode_gap_rule is None or natural_horizon is None or overlap_policy is None:
        raise EpisodeRuleNotDeclaredError(
            "episode_gap_rule, natural_horizon e overlap_policy devono essere dichiarati ex-ante dal "
            "detector/frozen spec - nessun default silenzioso e' ammesso."
        )
    if overlap_policy not in ("COLLAPSE_TO_FIRST", "COLLAPSE_TO_LAST", "NO_COLLAPSE_INDEPENDENT_HORIZON"):
        raise ValueError(f"overlap_policy sconosciuta: {overlap_policy}")

    rows = [e["event_a_index"] for e in sequence_events]
    direction_by_row = {e["event_a_index"]: e["direction"] for e in sequence_events}
    event_by_row = {e["event_a_index"]: e for e in sequence_events}

    event_view = {
        "n": len(rows),
        "events": sequence_events,
    }

    if overlap_policy == "NO_COLLAPSE_INDEPENDENT_HORIZON":
        # Gli eventi sono dichiarati sufficientemente distanti/indipendenti
        # per definizione della sequence (es. orizzonte naturale >> gap
        # osservato tipico) - EPISODE VIEW coincide con EVENT VIEW, ma la
        # dichiarazione resta esplicita e verificabile, non assunta.
        episode_view = {"n": len(rows), "n_episodes": len(rows), "events": sequence_events,
                        "representative_rule": "nessun collasso - overlap_policy=NO_COLLAPSE_INDEPENDENT_HORIZON dichiarata ex-ante"}
        return event_view, episode_view

    clusters, gaps = assign_clusters(sorted(rows), episode_gap_rule)
    if overlap_policy == "COLLAPSE_TO_FIRST":
        representative_rows = [c[0] for c in clusters]
        rule_desc = "primo evento del cluster (temporale, mai il migliore - anti-cherry-pick)"
    else:  # COLLAPSE_TO_LAST
        representative_rows = [c[-1] for c in clusters]
        rule_desc = "ultimo evento del cluster (dichiarato ex-ante per questa sequence)"

    episode_events = [event_by_row[r] for r in representative_rows]
    episode_view = {
        "n": len(representative_rows), "n_episodes": len(clusters),
        "events": episode_events, "representative_rule": rule_desc,
        "episode_gap_rule": episode_gap_rule, "natural_horizon": natural_horizon,
    }
    return event_view, episode_view


if __name__ == "__main__":
    # Dati sintetici (nessun dato NEXUS) - eventi clusterizzati a bassa distanza + eventi isolati.
    synthetic_events = []
    for i, row in enumerate([100, 102, 103, 150, 200, 202, 250]):
        synthetic_events.append({
            "sequence_event_id": f"DEMO-{i:03d}", "sequence_id": "SEQ-DEMO", "direction": "BUY",
            "event_a_index": row, "transition_complete_index": row, "prediction_start_index": row,
        })

    # Caso 1 (negativo): parametri non dichiarati -> rifiutato.
    try:
        build_event_and_episode_views(synthetic_events, episode_gap_rule=None, natural_horizon=None, overlap_policy=None)
        print("ERRORE: episode rule mancante avrebbe dovuto essere rifiutata!")
    except EpisodeRuleNotDeclaredError as e:
        print(f"Caso 1 (regole non dichiarate) correttamente rifiutato: {type(e).__name__}")

    # Caso 2 (positivo): COLLAPSE_TO_FIRST con gap=5 -> attesi 3 cluster (100-103, 150, 200-202, 250 -> in realta' 4).
    ev, ep = build_event_and_episode_views(synthetic_events, episode_gap_rule=5, natural_horizon=40, overlap_policy="COLLAPSE_TO_FIRST")
    print(f"Caso 2 (COLLAPSE_TO_FIRST, gap=5): EVENT_VIEW n={ev['n']}, EPISODE_VIEW n_episodes={ep['n_episodes']} rows={[e['event_a_index'] for e in ep['events']]}")
    assert ev["n"] == 7
    assert ep["n_episodes"] == 4  # {100,102,103}, {150}, {200,202}, {250}
    assert [e["event_a_index"] for e in ep["events"]] == [100, 150, 200, 250]

    # Caso 3 (positivo): NO_COLLAPSE_INDEPENDENT_HORIZON -> EPISODE VIEW == EVENT VIEW.
    ev2, ep2 = build_event_and_episode_views(synthetic_events, episode_gap_rule=5, natural_horizon=40, overlap_policy="NO_COLLAPSE_INDEPENDENT_HORIZON")
    assert ep2["n_episodes"] == ev2["n"] == 7
    print(f"Caso 3 (NO_COLLAPSE_INDEPENDENT_HORIZON): EPISODE_VIEW n_episodes={ep2['n_episodes']} == EVENT_VIEW n={ev2['n']}")

    # ---- Phase 7.4A Integrity Patch sec.1: event_cluster_rule vs outcome_overlap_rule ----
    # natural_horizon=40 -> outcome_overlap_embargo_bars = natural_horizon-1 = 39
    # (due eventi a distanza d hanno outcome window sovrapposte se e solo se d<40).

    # Caso 4: t=100, t=102 -> STESSO episodio locale (event_cluster_rule=3, |102-100|=2<=3).
    ev4, ep4 = build_event_and_episode_views(
        [{"sequence_event_id": "A", "sequence_id": "SEQ-DEMO", "direction": "BUY", "event_a_index": 100,
          "transition_complete_index": 100, "prediction_start_index": 100},
         {"sequence_event_id": "B", "sequence_id": "SEQ-DEMO", "direction": "BUY", "event_a_index": 102,
          "transition_complete_index": 102, "prediction_start_index": 102}],
        episode_gap_rule=3, natural_horizon=40, overlap_policy="COLLAPSE_TO_FIRST")
    assert ep4["n_episodes"] == 1, "t=100,t=102 devono collassare nello stesso episodio locale (gap=3)"
    print(f"Caso 4 (t=100,t=102 - stesso episodio locale): EPISODE_VIEW n_episodes={ep4['n_episodes']}")

    # Caso 5: t=100, t=105 -> episodio locale DIVERSO (gap=3, |105-100|=5>3) MA outcome fortemente
    # overlap (5<39) -> devono ricongiungersi in INDEPENDENT_VIEW (embargo=39).
    ev5, ep5 = build_event_and_episode_views(
        [{"sequence_event_id": "A", "sequence_id": "SEQ-DEMO", "direction": "BUY", "event_a_index": 100,
          "transition_complete_index": 100, "prediction_start_index": 100},
         {"sequence_event_id": "B", "sequence_id": "SEQ-DEMO", "direction": "BUY", "event_a_index": 105,
          "transition_complete_index": 105, "prediction_start_index": 105}],
        episode_gap_rule=3, natural_horizon=40, overlap_policy="COLLAPSE_TO_FIRST")
    assert ep5["n_episodes"] == 2, "t=100,t=105 devono essere 2 episodi locali DIVERSI (gap=3)"
    indep5 = build_outcome_independent_view(ep5["events"], outcome_overlap_embargo_bars=39)
    assert indep5["n_independent_observations"] == 1, (
        "t=100,t=105 sono 2 episodi locali ma outcome window sovrapposte (d=5<39) - "
        "devono contare come 1 SOLA osservazione indipendente, mai 2 solo perche' superano gap=3"
    )
    print(f"Caso 5 (t=100,t=105 - episodi locali diversi ma outcome overlap): "
          f"EPISODE_VIEW n_episodes={ep5['n_episodes']} -> INDEPENDENT_VIEW n={indep5['n_independent_observations']}")

    # Caso 6: t=100, t=141 -> episodio locale diverso E outcome NON overlap (d=41>=40) ->
    # restano 2 osservazioni indipendenti anche dopo l'embargo.
    ev6, ep6 = build_event_and_episode_views(
        [{"sequence_event_id": "A", "sequence_id": "SEQ-DEMO", "direction": "BUY", "event_a_index": 100,
          "transition_complete_index": 100, "prediction_start_index": 100},
         {"sequence_event_id": "B", "sequence_id": "SEQ-DEMO", "direction": "BUY", "event_a_index": 141,
          "transition_complete_index": 141, "prediction_start_index": 141}],
        episode_gap_rule=3, natural_horizon=40, overlap_policy="COLLAPSE_TO_FIRST")
    indep6 = build_outcome_independent_view(ep6["events"], outcome_overlap_embargo_bars=39)
    assert indep6["n_independent_observations"] == 2, "t=100,t=141 hanno outcome window NON sovrapposte (d=41) - devono restare 2 osservazioni indipendenti"
    print(f"Caso 6 (t=100,t=141 - outcome non overlap): INDEPENDENT_VIEW n={indep6['n_independent_observations']} (nessun collasso indebito)")

    # Caso 7 (negativo): embargo non dichiarato -> rifiutato, nessun default silenzioso.
    try:
        build_outcome_independent_view(ep5["events"], outcome_overlap_embargo_bars=None)
        print("ERRORE: embargo mancante avrebbe dovuto essere rifiutato!")
    except EpisodeRuleNotDeclaredError as e:
        print(f"Caso 7 (embargo non dichiarato) correttamente rifiutato: {type(e).__name__}")

    print("\nTutti i casi dell'episode engine verificati (incl. Phase 7.4A Integrity Patch: event_cluster_rule vs outcome_overlap_rule).")
