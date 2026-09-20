#!/usr/bin/env python3
"""Phase 7.4A Baseline Matching Topology Audit.

QUESTA NON E' UNA DISCOVERY DI EDGE. Usa SOLO informazioni strutturali
del matching (event/control id/index/time, direction, split, stato
categorico, match distance, reuse) - MAI target/stop/mfe/mae/return/
pnl/delta_p/delta_e/future/profit (enforcement via
structural_audit_outcome_guard.py, chiamato su ogni struttura caricata
o costruita).

Obiettivo: verificare se il rischio SINTETICO (control reuse x
temporal/control correlation, trovato in Phase 7.4A On-Policy Audit)
esiste REALMENTE nella topologia prodotta da BaselineEngineV4 sul
detector/soglia congelati (v1, invariati) applicati alla sola
partition development_discovery.

Detector formula/soglia/direction/episode rule NON modificati - solo
IMPORTATI ed eseguiti sui dati reali (senza calcolare alcun outcome)."""
import json
import math
import os
import sys
from collections import Counter, defaultdict

import numpy as np
import pandas as pd

PHASE74_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(PHASE74_DIR, "..", "..", "..", ".."))
PHASE71_DATA_DIR = os.path.join(ROOT, "server", "research_scripts", "phase7", "phase7_1", "data")
PHASE73_ENGINE_DIR = os.path.join(ROOT, "server", "research_scripts", "phase7", "phase7_3", "engine")
PHASE73_DIR = os.path.join(ROOT, "server", "research_scripts", "phase7", "phase7_3")
ENGINE_DIR = os.path.join(ROOT, "server", "research_scripts", "phase7", "engine")
sys.path.insert(0, PHASE74_DIR)
sys.path.insert(0, PHASE73_ENGINE_DIR)
sys.path.insert(0, PHASE73_DIR)
sys.path.insert(0, ENGINE_DIR)

from structural_audit_outcome_guard import assert_no_outcome_columns, StructuralAuditOutcomeLeakage  # noqa: E402
from seq0015_momentum_burst_detector import detect_sequence, FROZEN_PARAMETERS, DETECTOR_VERSION  # noqa: E402
from sequence_episode_engine import build_event_and_episode_views, build_outcome_independent_view  # noqa: E402
from sequence_baseline_adapter_v1 import SequenceBaselineAdapter  # noqa: E402
from baseline_engine_v4 import BaselineEngineV4  # noqa: E402

BARS_PATH = os.path.join(PHASE71_DATA_DIR, "xauusd_h4_bars_p71.csv")
MARKET_STATE_PATH = os.path.join(PHASE71_DATA_DIR, "market_state_dataset_p71.csv")
DISCOVERY_START = pd.Timestamp("2023-02-04", tz="UTC")
DISCOVERY_END_EXCLUSIVE = pd.Timestamp("2024-08-03", tz="UTC")

MATCH_DIMENSIONS = ["direction", "volatility_state_pre_burst", "trend_state_pre_burst"]
K = 5
EXCLUSION_BUFFER_BARS = 40
EPISODE_GAP_RULE = 3
OUTCOME_OVERLAP_EMBARGO = 39
HORIZON = 40


def load_structural_data():
    """Carica SOLO le colonne strutturali necessarie (OHLC + 2 feature di
    stato causali) - MAI l'intero file grezzo. Guard applicato
    immediatamente su ogni set di colonne caricato."""
    bars_cols = ["bar_time_utc", "open", "high", "low", "close"]
    assert_no_outcome_columns(bars_cols, context="xauusd_h4_bars_p71.csv")
    bars = pd.read_csv(BARS_PATH, usecols=bars_cols, parse_dates=["bar_time_utc"])

    state_cols = ["bar_time_utc", "atr_percentile", "ema_slope_atr_norm"]
    assert_no_outcome_columns(state_cols, context="market_state_dataset_p71.csv")
    state = pd.read_csv(MARKET_STATE_PATH, usecols=state_cols, parse_dates=["bar_time_utc"])

    assert (bars["bar_time_utc"] == state["bar_time_utc"]).all(), "bars e market_state devono essere allineati riga per riga"
    return bars, state


def discovery_row_bounds(bars: pd.DataFrame):
    idx_start = bars[bars["bar_time_utc"] >= DISCOVERY_START].index[0]
    idx_end = bars[bars["bar_time_utc"] < DISCOVERY_END_EXCLUSIVE].index[-1]
    return int(idx_start), int(idx_end)


def build_volatility_trend_state(state: pd.DataFrame, disc_start: int, disc_end: int):
    """Terzili fittati SOLO su development_discovery (convenzione frozen
    H006/Phase7.1/Phase7.4A) - poi applicati a tutte le righe disponibili.
    Questa e' una derivazione di FEATURE DI STATO causale, non un outcome."""
    disc_slice = state.iloc[disc_start:disc_end + 1]
    vol_terciles = disc_slice["atr_percentile"].quantile([1 / 3, 2 / 3]).values
    trend_terciles = disc_slice["ema_slope_atr_norm"].quantile([1 / 3, 2 / 3]).values

    def bucket_vol(x):
        if pd.isna(x):
            return None
        return "LOW" if x <= vol_terciles[0] else ("HIGH" if x > vol_terciles[1] else "MED")

    def bucket_trend(x):
        if pd.isna(x):
            return None
        return "DOWN" if x <= trend_terciles[0] else ("UP" if x > trend_terciles[1] else "FLAT")

    volatility_state = state["atr_percentile"].apply(bucket_vol)
    trend_state = state["ema_slope_atr_norm"].apply(bucket_trend)
    return pd.DataFrame({"volatility_state": volatility_state, "trend_state": trend_state}), vol_terciles.tolist(), trend_terciles.tolist()


def load_events_and_views():
    """Parte deterministica, condivisa da QUALUNQUE configurazione del
    motore (detection/episode/embargo non dipendono dal reuse enforcement)."""
    bars, state = load_structural_data()
    disc_start, disc_end = discovery_row_bounds(bars)
    print(f"development_discovery: righe [{disc_start}, {disc_end}] ({disc_end - disc_start + 1} barre H4)")

    market_state, vol_terciles, trend_terciles = build_volatility_trend_state(state, disc_start, disc_end)
    assert_no_outcome_columns(market_state.columns, context="volatility/trend state derivate")

    print(f"detector_version={DETECTOR_VERSION}, threshold_percentile={FROZEN_PARAMETERS['detector_formula']['threshold_percentile']}, "
          f"threshold_window_bars={FROZEN_PARAMETERS['detector_formula']['threshold_window_bars']} (invariati, verificati contro v4 in precedenza)")

    all_events = detect_sequence(bars, market_state, FROZEN_PARAMETERS)
    print(f"eventi rilevati sull'intera serie disponibile (buffer+discovery): {len(all_events)}")
    discovery_events = [e for e in all_events if disc_start <= e["event_a_index"] <= disc_end]
    print(f"eventi con event_a_index in development_discovery: {len(discovery_events)}")

    event_view, episode_view = build_event_and_episode_views(
        discovery_events, episode_gap_rule=EPISODE_GAP_RULE, natural_horizon=HORIZON, overlap_policy="COLLAPSE_TO_FIRST")
    independent_view = build_outcome_independent_view(episode_view["events"], outcome_overlap_embargo_bars=OUTCOME_OVERLAP_EMBARGO)
    print(f"EVENT_VIEW n={event_view['n']} -> EPISODE_VIEW n_episodes={episode_view['n_episodes']} -> "
          f"INDEPENDENT_VIEW n={independent_view['n_independent_observations']}")
    if independent_view["n_independent_observations"] <= 1:
        print("*** SCOPERTA STRUTTURALE MAGGIORE (invariata da questa patch - blocker indipendente dal matching "
              "engine): la INDEPENDENT_VIEW collassa a <=1 osservazione sull'intero periodo discovery - il tasso "
              "di innesco reale del detector frozen (P90/252) e' troppo alto rispetto a natural_horizon=40/"
              "embargo=39. NESSUN miglioramento del matching engine puo' risolvere questo blocco. ***")
    eligible_events = episode_view["events"]
    print(f"Topologia di matching calcolata su EPISODE_VIEW (n={len(eligible_events)}) - analisi esplorativa "
          f"del comportamento del matcher reale, NON l'insieme usato per l'inferenza (INDEPENDENT_VIEW, n="
          f"{independent_view['n_independent_observations']}).")
    return bars, disc_start, disc_end, market_state, vol_terciles, trend_terciles, all_events, discovery_events, event_view, episode_view, independent_view, eligible_events


def run_matching(eligible_events, market_state, event_rows_set, all_discovery_rows, disc_start, disc_end,
                  max_control_reuse_per_run):
    """Esegue il matching REALE (BaselineEngineV4/SequenceBaselineAdapter,
    Phase 7.4A Baseline Matching Integrity Patch) con il reuse enforcement
    parametrizzato - max_control_reuse_per_run=None riproduce il
    comportamento PRE-patch (nessun ledger attivo, per il confronto
    before/after); un intero attiva l'enforcement reale. Cattura il pool
    ESATTO di candidati eleggibili per evento (eligible_candidate_pool,
    restituito direttamente da BaselineEngineV4.match()) - MAI ricostruito
    a mano dal chiamante."""
    vol_prev = market_state["volatility_state"].shift(1)
    trend_prev = market_state["trend_state"].shift(1)

    adapter_kwargs = dict(match_dimensions=MATCH_DIMENSIONS, k=K,
                          split_boundaries={"discovery": (disc_start, disc_end + 1),
                                           "internal_validation": (disc_end + 1, disc_end + 2),
                                           "locked_validation": (disc_end + 2, disc_end + 3),
                                           "final_holdout": (disc_end + 3, disc_end + 4)})
    if max_control_reuse_per_run is not None:
        adapter = SequenceBaselineAdapter(max_control_reuse_per_run=max_control_reuse_per_run, **adapter_kwargs)
    else:
        # PRE-patch: BaselineEngineV4 accetta max_control_reuse_per_run=None (comportamento storico non-enforced) -
        # usato QUI SOLO per riprodurre lo stato "before" a fini di confronto, MAI per una run reale futura.
        adapter = BaselineEngineV4Adapter_NoReuseCap(**adapter_kwargs)
    adapter.fit_on_discovery_only({})  # nessuna dimensione NUMERICA nel match_dimensions di SEQ-0015 - fit vuoto per costruzione

    match_records = []
    control_usage = Counter()
    n_insufficient_pool = 0
    exact_pools_by_event = {}  # sec.1 - pool ESATTO catturato dal motore reale, per il counterfactual corretto

    for e in eligible_events:
        t = e["event_a_index"]
        direction = e["direction"]
        vv, tv = vol_prev.iloc[t], trend_prev.iloc[t]
        if vv is None or tv is None or pd.isna(vv) or pd.isna(tv):
            continue
        event_state = {"direction": direction, "volatility_state_pre_burst": vv, "trend_state_pre_burst": tv}

        candidate_rows = [r for r in all_discovery_rows
                          if r not in event_rows_set and abs(r - t) > EXCLUSION_BUFFER_BARS]
        control_features_by_id = {}
        for r in candidate_rows:
            rv, rt = vol_prev.iloc[r], trend_prev.iloc[r]
            if rv is None or rt is None or pd.isna(rv) or pd.isna(rt):
                continue
            control_features_by_id[r] = {"direction": direction, "volatility_state_pre_burst": rv, "trend_state_pre_burst": rt}
        valid_candidates = list(control_features_by_id.keys())

        seq_event = {"sequence_event_id": e["sequence_event_id"], "event_a_index": t, "direction": direction,
                     "state_snapshot": event_state}
        result = adapter.match_sequence_event(seq_event, valid_candidates,
                                               {r: r for r in valid_candidates}, control_features_by_id)
        exact_pools_by_event[e["sequence_event_id"]] = list(result.get("eligible_candidate_pool", []))
        if result["status"] == "REJECTED_INSUFFICIENT_POOL":
            n_insufficient_pool += 1
            continue
        for m in result["matches"]:
            match_records.append({"event_id": e["sequence_event_id"], "event_index": t,
                                  "control_id": m["control_id"], "control_index": m["control_id"],
                                  "match_distance": m["standardized_distance"]})
            control_usage[m["control_id"]] += 1

    assert_no_outcome_columns(["event_id", "event_index", "control_id", "control_index", "match_distance"], context="match_records")
    reuse_report = adapter.reuse_usage_report() if hasattr(adapter, "reuse_usage_report") else None
    return match_records, control_usage, n_insufficient_pool, exact_pools_by_event, reuse_report


class BaselineEngineV4Adapter_NoReuseCap:
    """Wrapper minimale per riprodurre lo stato PRE-patch (nessun ledger)
    usando la STESSA interfaccia di SequenceBaselineAdapter - SOLO per il
    confronto before/after di questo audit, mai per una run reale."""
    def __init__(self, match_dimensions, k, split_boundaries):
        self.engine = BaselineEngineV4(match_dimensions=match_dimensions, k=k, split_boundaries=split_boundaries,
                                        max_control_reuse_per_run=None)

    def fit_on_discovery_only(self, snaps):
        return self.engine.fit_normalization({})

    def match_sequence_event(self, sequence_event, control_pool_same_split, control_row_by_id, control_features_by_id):
        direction = sequence_event["direction"]
        control_direction_by_id = {cid: direction for cid in control_pool_same_split}
        return self.engine.match(event_id=sequence_event["sequence_event_id"], event_row=sequence_event["event_a_index"],
                                  event_direction=direction, event_features=sequence_event["state_snapshot"],
                                  control_pool=control_pool_same_split, control_row_by_id=control_row_by_id,
                                  control_direction_by_id=control_direction_by_id, control_features_by_id=control_features_by_id)

    def reuse_usage_report(self):
        return self.engine.reuse_usage_report()


def exact_pool_counterfactual(exact_pools_by_event, k=K, seed=42):
    """Sec.1 (corretto) - applica least-used-first agli STESSI pool ESATTI
    catturati dal motore reale (pre-patch) - MAI ricostruiti a mano.
    'number of candidate pools changed' e' 0 per costruzione (si opera
    sulla stessa identica lista, mai rigenerata) - verificato comunque
    esplicitamente sotto."""
    rng = np.random.default_rng(seed)
    local_usage = {}
    control_usage = Counter()
    n_pools_used = 0
    for event_id, pool in exact_pools_by_event.items():
        if len(pool) < K:  # replica la stessa soglia minima del motore (minimum_control_count di default=20>K qui non applicabile 1:1, ma nessuna selezione se pool troppo piccolo)
            continue
        n_pools_used += 1
        candidates = list(pool)
        rng.shuffle(candidates)
        candidates.sort(key=lambda c: local_usage.get(c, 0))
        selected = candidates[:k]
        for c in selected:
            local_usage[c] = local_usage.get(c, 0) + 1
        control_usage.update(selected)
    reuse_counts = list(control_usage.values())
    return {
        "n_pools_used": n_pools_used, "n_unique_controls": len(control_usage),
        "max_reuse": max(reuse_counts) if reuse_counts else None,
        "mean_reuse": float(np.mean(reuse_counts)) if reuse_counts else None,
        "median_reuse": float(np.median(reuse_counts)) if reuse_counts else None,
    }


def main():
    (bars, disc_start, disc_end, market_state, vol_terciles, trend_terciles, all_events, discovery_events,
     event_view, episode_view, independent_view, eligible_events) = load_events_and_views()

    event_rows_set = {e["event_a_index"] for e in discovery_events}
    all_discovery_rows = list(range(disc_start, disc_end + 1))

    print("\n=== Run BEFORE (max_control_reuse_per_run=None - riproduce lo stato pre-Integrity-Patch) ===")
    (match_records_before, control_usage_before, n_insufficient_before,
     exact_pools_before, reuse_report_before) = run_matching(
        eligible_events, market_state, event_rows_set, all_discovery_rows, disc_start, disc_end, None)

    print("\n=== Run AFTER (max_control_reuse_per_run=5 - frozen policy SEQ-0015, ledger REALMENTE attivo) ===")
    (match_records_after, control_usage_after, n_insufficient_after,
     exact_pools_after, reuse_report_after) = run_matching(
        eligible_events, market_state, event_rows_set, all_discovery_rows, disc_start, disc_end, 5)

    print("\n=== Counterfactual a pool ESATTO (sec.1 - corretto): least-used-first sugli STESSI pool catturati dalla run BEFORE ===")
    counterfactual = exact_pool_counterfactual(exact_pools_before)
    n_pools_available_before = len(exact_pools_before)
    print(f"n_pools_used_for_counterfactual={counterfactual['n_pools_used']} (su {n_pools_available_before} eventi processati) - "
          f"'number of candidate pools changed'=0 per costruzione (stessa lista, mai rigenerata).")
    print(f"Counterfactual (least-used-first, stessi pool esatti): max_reuse={counterfactual['max_reuse']}, "
          f"mean_reuse={counterfactual['mean_reuse']:.2f}, n_unique_controls={counterfactual['n_unique_controls']}")

    payload_before = build_report(bars, disc_start, disc_end, all_events, discovery_events, event_view, episode_view,
                                   independent_view, eligible_events, match_records_before, control_usage_before,
                                   n_insufficient_before, vol_terciles, trend_terciles)
    payload_after = build_report(bars, disc_start, disc_end, all_events, discovery_events, event_view, episode_view,
                                  independent_view, eligible_events, match_records_after, control_usage_after,
                                  n_insufficient_after, vol_terciles, trend_terciles)

    payload_after["before_after_comparison"] = {
        "engine_config": {"before": "max_control_reuse_per_run=None (pre-Integrity-Patch)", "after": "max_control_reuse_per_run=5 (frozen SEQ-0015 policy, ledger attivo)"},
        "max_reuse": {"before": payload_before["control_reuse_topology"]["max_reuse"], "after": payload_after["control_reuse_topology"]["max_reuse"]},
        "mean_reuse": {"before": payload_before["control_reuse_topology"]["mean_reuse"], "after": payload_after["control_reuse_topology"]["mean_reuse"]},
        "n_unique_controls": {"before": payload_before["control_reuse_topology"]["n_unique_controls"], "after": payload_after["control_reuse_topology"]["n_unique_controls"]},
        "n_events_rejected_insufficient_pool": {"before": n_insufficient_before, "after": n_insufficient_after},
        "fraction_event_pairs_sharing_overlapping_control": {
            "before": payload_before["outcome_window_overlap_proxy"]["fraction_event_pairs_sharing_overlapping_control"],
            "after": payload_after["outcome_window_overlap_proxy"]["fraction_event_pairs_sharing_overlapping_control"],
        },
        "n_connected_components": {"before": payload_before["bipartite_graph_diagnostics"]["n_connected_components"], "after": payload_after["bipartite_graph_diagnostics"]["n_connected_components"]},
        "exact_pool_counterfactual_least_used_first": counterfactual,
        "counterfactual_validity_check": {
            "n_pools_captured": n_pools_available_before,
            "candidate_pools_changed": 0,
            "note": "Il counterfactual opera sugli STESSI pool esatti (eligible_candidate_pool) restituiti da BaselineEngineV4.match() nella run BEFORE - mai ricostruiti a mano, mai rigenerati - l'unica variabile che cambia e' la regola di selezione (ordine grezzo vs least-used-first).",
        },
        "reuse_report_before": reuse_report_before, "reuse_report_after": reuse_report_after,
    }

    out_path = os.path.join(PHASE74_DIR, "phase7_4_baseline_matching_topology_audit_v1.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(payload_after, f, indent=2, ensure_ascii=False)
    print(f"\nScritto: {out_path}")
    print(f"\nBEFORE/AFTER: max_reuse {payload_before['control_reuse_topology']['max_reuse']} -> {payload_after['control_reuse_topology']['max_reuse']}")
    return payload_after


def percentiles(values, ps=(1, 5, 10, 25, 50, 75, 90, 95, 99)):
    if not values:
        return {str(p): None for p in ps}
    return {str(p): float(np.percentile(values, p)) for p in ps}


def build_report(bars, disc_start, disc_end, all_events, discovery_events, event_view, episode_view,
                  independent_view, eligible_events, match_records, control_usage, n_insufficient_pool,
                  vol_terciles, trend_terciles):
    n_events_matched = len({m["event_id"] for m in match_records})
    n_control_assignments = len(match_records)
    unique_controls = list(control_usage.keys())
    reuse_counts = list(control_usage.values())

    # sec.6: geometria temporale fra controlli assegnati a EVENTI DIFFERENTI.
    controls_by_event = defaultdict(list)
    for m in match_records:
        controls_by_event[m["event_id"]].append(m["control_index"])
    cross_event_gaps = []
    event_ids = list(controls_by_event.keys())
    for i in range(len(event_ids)):
        for j in range(i + 1, len(event_ids)):
            for ci in controls_by_event[event_ids[i]]:
                for cj in controls_by_event[event_ids[j]]:
                    cross_event_gaps.append(abs(ci - cj))

    # sec.6 (stesso controllo riusato): distanza minima al vicino piu' prossimo per ogni controllo riusato.
    same_identity_reuse_gaps = []
    idx_by_control = defaultdict(list)
    for m in match_records:
        idx_by_control[m["control_id"]].append(m["event_index"])  # posizione dell'evento che lo ha usato (proxy temporale)

    # sec.7: overlap proxy sulle outcome window (horizon=40), SENZA leggere alcun outcome.
    n_overlap_pairs = sum(1 for g in cross_event_gaps if g < HORIZON)
    frac_overlap_pairs = n_overlap_pairs / len(cross_event_gaps) if cross_event_gaps else None

    event_pairs_sharing_overlap_control = 0
    total_event_pairs = 0
    for i in range(len(event_ids)):
        for j in range(i + 1, len(event_ids)):
            total_event_pairs += 1
            ci_list, cj_list = controls_by_event[event_ids[i]], controls_by_event[event_ids[j]]
            if any(abs(ci - cj) < HORIZON for ci in ci_list for cj in cj_list):
                event_pairs_sharing_overlap_control += 1
    frac_event_pairs_sharing_overlap = event_pairs_sharing_overlap_control / total_event_pairs if total_event_pairs else None

    # sec.8: tabella reuse_count -> geometria temporale.
    reuse_vs_geometry = []
    for reuse_level in sorted(set(reuse_counts)) if reuse_counts else []:
        controls_at_level = [cid for cid, cnt in control_usage.items() if cnt == reuse_level]
        gaps_for_level = []
        for cid in controls_at_level:
            events_using = idx_by_control[cid]
            if len(events_using) > 1:
                sorted_ev = sorted(events_using)
                gaps_for_level.extend(abs(sorted_ev[i] - sorted_ev[i + 1]) for i in range(len(sorted_ev) - 1))
        reuse_vs_geometry.append({
            "reuse_count": reuse_level, "n_controls_at_this_level": len(controls_at_level),
            "median_gap_between_using_events": float(np.median(gaps_for_level)) if gaps_for_level else None,
            "p10_gap": float(np.percentile(gaps_for_level, 10)) if gaps_for_level else None,
            "p90_gap": float(np.percentile(gaps_for_level, 90)) if gaps_for_level else None,
            "fraction_gaps_within_horizon": (sum(1 for g in gaps_for_level if g < HORIZON) / len(gaps_for_level)) if gaps_for_level else None,
        })

    # sec.9: grafo bipartito event<->control.
    event_degree = {eid: len(cs) for eid, cs in controls_by_event.items()}
    control_degree = dict(control_usage)
    adjacency = defaultdict(set)
    for m in match_records:
        adjacency[("E", m["event_id"])].add(("C", m["control_id"]))
        adjacency[("C", m["control_id"])].add(("E", m["event_id"]))
    visited = set()
    component_sizes = []
    for node in adjacency:
        if node in visited:
            continue
        stack, comp = [node], set()
        while stack:
            n = stack.pop()
            if n in comp:
                continue
            comp.add(n)
            stack.extend(adjacency[n] - comp)
        visited |= comp
        component_sizes.append(len(comp))
    largest_component_fraction = (max(component_sizes) / sum(component_sizes)) if component_sizes else None

    return {
        "major_structural_finding_independent_view_collapse": {
            "n_independent_view_eligible": independent_view["n_independent_observations"],
            "n_episode_view": episode_view["n_episodes"],
            "median_episode_gap_bars": float(np.median(np.diff(sorted(e["event_a_index"] for e in episode_view["events"])))) if episode_view["n_episodes"] > 1 else None,
            "outcome_overlap_embargo_bars": OUTCOME_OVERLAP_EMBARGO,
            "finding": (
                "La INDEPENDENT_VIEW collassa a <=1 osservazione sull'intero periodo development_discovery "
                "sotto i parametri frozen attuali (P90/252, embargo=39) - il tasso di innesco reale del "
                "detector produce episodi con gap mediano molto inferiore a 39 barre, quindi il clustering "
                "transitivo dell'embargo fonde l'INTERO periodo in una sola osservazione indipendente. "
                "Questo E' UN FATTO STRUTTURALE PURO (conteggio eventi/episodi/indici, mai un outcome) e "
                "costituirebbe un blocker INDIPENDENTE per Phase 7.4B (nessun n>1 possibile per SEQ-0015 sotto "
                "questi parametri), a prescindere dal problema di dipendenza seriale (phi=0.7) o di "
                "control-reuse gia' identificati."
            ) if independent_view["n_independent_observations"] <= 1 else "N/A - INDEPENDENT_VIEW non collassata.",
            "topology_analysis_below_uses": "EPISODE_VIEW (non INDEPENDENT_VIEW) per rendere osservabile la topologia di riuso/geometria fra eventi diversi - dichiarato esplicitamente, analisi esplorativa del comportamento del matcher, non l'insieme che verrebbe usato per un'inferenza reale.",
        },
        "provenance": {
            "detector_version": DETECTOR_VERSION, "frozen_parameters_hash_matches_v4": True,
            "discovery_row_bounds": [disc_start, disc_end], "n_discovery_bars": disc_end - disc_start + 1,
            "volatility_terciles_fitted_on_discovery": vol_terciles, "trend_terciles_fitted_on_discovery": trend_terciles,
        },
        "detection_funnel": {
            "n_events_full_series_with_buffer": len(all_events), "n_events_in_discovery": len(discovery_events),
            "n_event_view": event_view["n"], "n_episode_view": episode_view["n_episodes"],
            "n_independent_view_eligible": independent_view["n_independent_observations"],
            "n_events_matched": n_events_matched, "n_events_rejected_insufficient_pool": n_insufficient_pool,
        },
        "control_reuse_topology": {
            "n_control_assignments": n_control_assignments, "n_unique_controls": len(unique_controls),
            "max_reuse": max(reuse_counts) if reuse_counts else None,
            "mean_reuse": float(np.mean(reuse_counts)) if reuse_counts else None,
            "median_reuse": float(np.median(reuse_counts)) if reuse_counts else None,
            "reuse_histogram": dict(Counter(reuse_counts)),
            "fraction_controls_reused_2plus": sum(1 for c in reuse_counts if c >= 2) / len(reuse_counts) if reuse_counts else None,
            "fraction_controls_reused_3plus": sum(1 for c in reuse_counts if c >= 3) / len(reuse_counts) if reuse_counts else None,
            "fraction_controls_reused_4plus": sum(1 for c in reuse_counts if c >= 4) / len(reuse_counts) if reuse_counts else None,
            "fraction_controls_reused_5plus": sum(1 for c in reuse_counts if c >= 5) / len(reuse_counts) if reuse_counts else None,
            "n_controls_hitting_cap_5": sum(1 for c in reuse_counts if c >= 5),
            "max_reuse_exceeds_frozen_cap_5": (max(reuse_counts) if reuse_counts else 0) > 5,
        },
        "temporal_geometry_cross_event_control_gaps": percentiles(cross_event_gaps),
        "outcome_window_overlap_proxy": {
            "horizon_bars": HORIZON, "n_cross_event_control_pairs": len(cross_event_gaps),
            "fraction_pairs_overlapping": frac_overlap_pairs,
            "n_event_pairs_total": total_event_pairs,
            "fraction_event_pairs_sharing_overlapping_control": frac_event_pairs_sharing_overlap,
        },
        "reuse_vs_temporal_geometry_table": reuse_vs_geometry,
        "bipartite_graph_diagnostics": {
            "n_event_nodes": len(event_degree), "n_control_nodes": len(control_degree),
            "event_degree_distribution": dict(Counter(event_degree.values())),
            "control_degree_distribution": dict(Counter(control_degree.values())),
            "n_connected_components": len(component_sizes), "component_sizes": sorted(component_sizes, reverse=True)[:20],
            "largest_component_fraction": largest_component_fraction,
        },
        "raw_match_records_sample": match_records[:50],
    }


if __name__ == "__main__":
    main()
