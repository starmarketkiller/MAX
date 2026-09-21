#!/usr/bin/env python3
"""Phase 7.6C - SEQ-0014B Structural Feasibility Preflight: RESULT COMMIT.

Esegue i count REALI congelati nello SPEC COMMIT (`6c0d3f6`,
`seq0014b_structural_preflight_spec_v1.json`) - nessun parametro nuovo
viene deciso qui, solo applicato ai dati reali (`events_p71.csv`,
`market_state_dataset_p71.csv`), ristretti a `development_discovery`
([396,2789), Phase 7.5C/7.5B/7.6A/7.6B, invariato).

Pipeline (STRUTTURALE, nessun outcome letto):
1. Tabella di setup reale (6 famiglie, direction!=0, regime_at_t_minus_1
   != MED escluso separatamente e riportato).
2. Audit di overlap same-bar/cross-family (concern del reviewer dopo
   `fb52168`).
3. Geometria WITHIN-FAMILY (EVENT/EPISODE/INDEPENDENT_VIEW) per famiglia
   x regime (CHOPPY/TRENDING), episode_gap_rule per-famiglia (dallo
   spec), natural_horizon/embargo condivisi (40/39).
4. Geometria CROSS-FAMILY pooled: un secondo passaggio di declustering
   sull'unione delle righe rappresentative within-family indipendenti,
   soglia = embargo condiviso (39) - MAI una somma ingenua.
5. Bilancio CHOPPY/TRENDING per famiglia e pooled (dato descrittivo,
   nessun gate pass/fail - NEEDS_ARM_SIZE_POLICY, vedi spec).
6. Matching feasibility per famiglia (CHOPPY vs TRENDING, STESSA
   famiglia, mai cross-family).
7. Verdetto strutturale composito finale.

Nessun outcome NEXUS letto. Nessuna discovery. Nessuna scelta di primary
outcome."""
import os
import sys

import numpy as np
import pandas as pd

PHASE76C_DIR = os.path.dirname(os.path.abspath(__file__))
PHASE7_DIR = os.path.abspath(os.path.join(PHASE76C_DIR, ".."))
ROOT = os.path.abspath(os.path.join(PHASE76C_DIR, "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase6_5"))
sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase6_6"))
sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase7", "phase7_3", "engine"))
sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase7", "engine"))
from canonical_utils import load_json, save_json, wrap_with_provenance  # noqa: E402
from dependence_diagnostics import assign_clusters  # noqa: E402
from sequence_structural_feasibility_gate import compute_detection_funnel  # noqa: E402
from baseline_engine_v4 import BaselineEngineV4, build_quality_report  # noqa: E402

DATA_DIR = os.path.join(PHASE7_DIR, "phase7_1", "data")
EVENTS_PATH = os.path.join(DATA_DIR, "events_p71.csv")
STATE_PATH = os.path.join(DATA_DIR, "market_state_dataset_p71.csv")
SPEC_PATH = os.path.join(PHASE76C_DIR, "seq0014b_structural_preflight_spec_v1.json")
SETUP_POP_PATH = os.path.join(PHASE7_DIR, "phase7_6b", "seq0014b_setup_population_spec_v1.json")

DIR_LABEL = {1: "BUY", -1: "SELL"}


def load_spec():
    return load_json(SPEC_PATH)["payload"]


def load_setup_population():
    return load_json(SETUP_POP_PATH)["payload"]


def build_eligible_setup_table(spec, setup_pop):
    """Tabella REALE di setup (6 famiglie), ristretta a development_discovery,
    direction!=0. regime_at_t_minus_1 calcolato su directional_efficiency
    letta a row_index-1, con i cutpoint GIA' CONGELATI (Phase 7.5C, riusati
    identici via il setup population spec - fb52168). Nessun outcome letto."""
    ev = pd.read_csv(EVENTS_PATH)
    state = pd.read_csv(STATE_PATH)
    de = state["directional_efficiency"].values

    disc_start, disc_end = spec["matching_spec"]["split_boundaries"]["discovery"]
    families = setup_pop["eligible_setup_families"]
    reg = setup_pop["regime_contract"]
    q1 = reg["tercile_cutpoints_reused_unchanged"]["q1_low_med"]
    q2 = reg["tercile_cutpoints_reused_unchanged"]["q2_med_high"]

    ev_scope = ev[(ev["event_family"].isin(families)) &
                  (ev["row_index"] >= disc_start) & (ev["row_index"] < disc_end) &
                  (ev["direction"] != 0)].copy()

    records = []
    med_excluded = []
    for _, row in ev_scope.iterrows():
        r = int(row["row_index"])
        t_minus_1 = r - 1
        de_tm1 = de[t_minus_1] if 0 <= t_minus_1 < len(de) else np.nan
        if np.isnan(de_tm1):
            regime = "UNDEFINED_MISSING_FEATURE"
        elif de_tm1 <= q1:
            regime = "CHOPPY"
        elif de_tm1 > q2:
            regime = "TRENDING"
        else:
            regime = "MED"
        rec = {
            "setup_family_id": row["event_family"],
            "row_index": r,
            "direction": int(row["direction"]),
            "directional_efficiency_t_minus_1": None if np.isnan(de_tm1) else float(de_tm1),
            "regime_at_t_minus_1": regime,
        }
        if regime in ("MED", "UNDEFINED_MISSING_FEATURE"):
            med_excluded.append(rec)
        else:
            records.append(rec)

    # setup_id univoco - gestisce esplicitamente il caso raro (verificato sui dati, non assunto)
    # in cui lo STESSO detector di famiglia spara 2 volte sulla stessa riga (es. SWEEP puo'
    # emettere sia HIGH sia LOW sweep su una singola barra outside-bar).
    seen = {}
    for rec in records + med_excluded:
        key = (rec["setup_family_id"], rec["row_index"])
        seen[key] = seen.get(key, 0) + 1
        idx = seen[key] - 1
        rec["setup_id"] = f"{rec['setup_family_id']}-{rec['row_index']}" + (f"-{idx}" if idx > 0 else "")
    same_family_same_row_duplicates = {f"{k[0]}-{k[1]}": v for k, v in seen.items() if v > 1}

    return records, med_excluded, same_family_same_row_duplicates, (disc_start, disc_end), state


def compute_base_counts(records, med_excluded, families):
    def block(recs):
        return {
            "n_total": len(recs),
            "n_CHOPPY": sum(1 for r in recs if r["regime_at_t_minus_1"] == "CHOPPY"),
            "n_TRENDING": sum(1 for r in recs if r["regime_at_t_minus_1"] == "TRENDING"),
        }
    overall = block(records)
    overall["n_MED_excluded"] = len(med_excluded)
    per_family = {}
    for fam in families:
        fam_records = [r for r in records if r["setup_family_id"] == fam]
        fam_med = [r for r in med_excluded if r["setup_family_id"] == fam]
        b = block(fam_records)
        b["n_MED_excluded"] = len(fam_med)
        per_family[fam] = b
    return {"overall": overall, "per_family": per_family}


def compute_overlap_audit(records, med_excluded_for_secondary):
    """Audit obbligatorio sec.5 della richiesta - calcolato sulla popolazione
    ELEGGIBILE PER L'ANALISI (direction!=0, regime!=MED, quella che entra
    davvero nella geometria/matching sotto). Le righe escluse per MED sono
    riportate separatamente come diagnostica secondaria (sec. secondary)."""
    by_row = {}
    for r in records:
        by_row.setdefault(r["row_index"], set()).add(r["setup_family_id"])

    n_rows_1_family = sum(1 for fams in by_row.values() if len(fams) == 1)
    n_rows_2plus_families = sum(1 for fams in by_row.values() if len(fams) >= 2)
    max_families_on_single_row = max((len(fams) for fams in by_row.values()), default=0)

    from collections import Counter
    combo_counts = Counter(tuple(sorted(fams)) for fams in by_row.values() if len(fams) >= 2)
    family_combination_distribution = {
        " + ".join(combo): count for combo, count in sorted(combo_counts.items(), key=lambda kv: -kv[1])
    }

    n_setup_records_sharing_row = sum(len(fams) for fams in by_row.values() if len(fams) >= 2)
    fraction_setup_records_sharing_row = (n_setup_records_sharing_row / len(records)) if records else None

    by_row_med = {}
    for r in med_excluded_for_secondary:
        by_row_med.setdefault(r["row_index"], set()).add(r["setup_family_id"])
    n_med_rows_that_also_have_a_non_med_family_on_same_row = sum(
        1 for row, fams in by_row_med.items() if row in by_row
    )

    return {
        "scope": "Calcolato sulla popolazione eleggibile per l'analisi (direction!=0 AND regime!=MED) - "
                 "quella che entra realmente nella geometria/matching sotto.",
        "n_unique_rows_with_exactly_1_family": n_rows_1_family,
        "n_unique_rows_with_2_or_more_families": n_rows_2plus_families,
        "max_families_on_a_single_row": max_families_on_single_row,
        "family_combination_distribution_on_shared_rows": family_combination_distribution,
        "n_setup_records_sharing_a_row_with_another_family": n_setup_records_sharing_row,
        "fraction_setup_records_sharing_a_row_with_another_family": fraction_setup_records_sharing_row,
        "secondary_diagnostic_med_excluded_rows_also_colocated_with_a_non_med_family": (
            n_med_rows_that_also_have_a_non_med_family_on_same_row
        ),
        "secondary_diagnostic_note": "Atteso strutturalmente 0: regime_at_t_minus_1 dipende SOLO da "
                                      "directional_efficiency[row_index-1], una proprieta' DELLA RIGA, non "
                                      "della famiglia - tutte le famiglie che sparano sulla stessa riga "
                                      "condividono per costruzione lo stesso regime (MED o non-MED). Non e' "
                                      "possibile che una riga sia 'MED per la famiglia A' e 'CHOPPY per la "
                                      "famiglia B' - un valore diverso da 0 qui avrebbe indicato un bug nel "
                                      "calcolo del regime.",
    }


def _empty_funnel(n_bars, episode_gap_rule, natural_horizon, overlap_policy, embargo):
    return {
        "n_bars": n_bars, "n_raw_events": 0, "firing_rate": 0.0,
        "gap_stats": {"median_gap_bars": None, "p10": None, "p25": None, "p50": None, "p75": None, "p90": None},
        "EVENT_VIEW": {"n": 0}, "EPISODE_VIEW": {"n": 0, "n_episodes": 0, "representative_rows": []},
        "INDEPENDENT_VIEW": {"n": 0, "n_independent_observations": 0, "representative_rows": [],
                              "direction_by_row": {}},
        "episode_gap_rule": episode_gap_rule, "natural_horizon": natural_horizon,
        "overlap_policy": overlap_policy, "outcome_overlap_embargo_bars": embargo,
    }


def compute_within_family_geometry(records, spec, n_bars_discovery):
    wfg = spec["within_family_geometry_rule"]
    shared = wfg["shared_across_all_6_families"]
    gap_rules = wfg["family_specific_episode_gap_rule"]
    families = sorted(set(r["setup_family_id"] for r in records))

    result = {}
    for fam in families:
        result[fam] = {}
        for regime in ("CHOPPY", "TRENDING"):
            rows = [r for r in records if r["setup_family_id"] == fam and r["regime_at_t_minus_1"] == regime]
            row_indices = [r["row_index"] for r in rows]
            direction_by_row = {r["row_index"]: DIR_LABEL[r["direction"]] for r in rows}
            gap_rule = gap_rules[fam]["value"]
            if not row_indices:
                funnel = _empty_funnel(n_bars_discovery, gap_rule, shared["natural_horizon"],
                                        shared["overlap_policy"], shared["outcome_overlap_embargo_bars"])
            else:
                funnel = compute_detection_funnel(
                    event_row_indices=row_indices, n_bars=n_bars_discovery, episode_gap_rule=gap_rule,
                    natural_horizon=shared["natural_horizon"], overlap_policy=shared["overlap_policy"],
                    outcome_overlap_embargo_bars=shared["outcome_overlap_embargo_bars"],
                    direction_by_row=direction_by_row,
                )
            result[fam][regime] = funnel
    return result


def compute_cross_family_pooled_geometry(records, within_family_geometry, spec):
    cfd = spec["cross_family_dependence_clustering"]
    threshold = cfd["threshold_bars"]

    pooled_nominal_setup_records = len(records)
    unique_setup_rows = sorted(set(r["row_index"] for r in records))
    n_unique_setup_rows = len(unique_setup_rows)

    # DIAGNOSTICA (mai l'autorita'): declustering diretto delle righe nominali pooled grezze,
    # stessa filosofia di raw_event_embargo_geometry nel gate esistente.
    if unique_setup_rows:
        raw_clusters, _ = assign_clusters(unique_setup_rows, threshold)
        cross_family_raw_episode_clusters = len(raw_clusters)
    else:
        cross_family_raw_episode_clusters = 0

    def _pool_reps(regime_filter):
        reps = set()
        for fam, by_regime in within_family_geometry.items():
            for regime, funnel in by_regime.items():
                if regime_filter is not None and regime != regime_filter:
                    continue
                reps.update(funnel["INDEPENDENT_VIEW"]["representative_rows"])
        return sorted(reps)

    def _cluster_count(rows):
        if not rows:
            return 0
        clusters, _ = assign_clusters(rows, threshold)
        return len(clusters)

    all_reps = _pool_reps(None)
    choppy_reps = _pool_reps("CHOPPY")
    trending_reps = _pool_reps("TRENDING")

    pooled_independent_units = _cluster_count(all_reps)
    choppy_independent_units_pooled = _cluster_count(choppy_reps)
    trending_independent_units_pooled = _cluster_count(trending_reps)

    sum_family_independent_units = sum(
        funnel["INDEPENDENT_VIEW"]["n"] for by_regime in within_family_geometry.values() for funnel in by_regime.values()
    )
    sum_family_choppy_independent_units = sum(
        by_regime["CHOPPY"]["INDEPENDENT_VIEW"]["n"] for by_regime in within_family_geometry.values()
    )
    sum_family_trending_independent_units = sum(
        by_regime["TRENDING"]["INDEPENDENT_VIEW"]["n"] for by_regime in within_family_geometry.values()
    )

    no_double_counting_check = {
        "pooled_independent_units": pooled_independent_units,
        "sum_family_independent_units_naive": sum_family_independent_units,
        "invariant_holds": pooled_independent_units <= sum_family_independent_units,
        "cross_family_collapse_detected": pooled_independent_units < sum_family_independent_units,
        "CHOPPY_pooled_independent_units": choppy_independent_units_pooled,
        "CHOPPY_sum_family_independent_units_naive": sum_family_choppy_independent_units,
        "CHOPPY_invariant_holds": choppy_independent_units_pooled <= sum_family_choppy_independent_units,
        "TRENDING_pooled_independent_units": trending_independent_units_pooled,
        "TRENDING_sum_family_independent_units_naive": sum_family_trending_independent_units,
        "TRENDING_invariant_holds": trending_independent_units_pooled <= sum_family_trending_independent_units,
    }

    return {
        "pooled_nominal_setup_records": pooled_nominal_setup_records,
        "unique_setup_rows": n_unique_setup_rows,
        "cross_family_raw_episode_clusters_diagnostic_only": cross_family_raw_episode_clusters,
        "pooled_independent_units": pooled_independent_units,
        "CHOPPY_independent_units_pooled": choppy_independent_units_pooled,
        "TRENDING_independent_units_pooled": trending_independent_units_pooled,
        "no_double_counting_check": no_double_counting_check,
    }


def compute_choppy_trending_balance(records, within_family_geometry):
    def ratio(a, b):
        return (a / b) if b else None

    per_family = {}
    for fam, by_regime in within_family_geometry.items():
        n_choppy_nominal = sum(1 for r in records if r["setup_family_id"] == fam and r["regime_at_t_minus_1"] == "CHOPPY")
        n_trending_nominal = sum(1 for r in records if r["setup_family_id"] == fam and r["regime_at_t_minus_1"] == "TRENDING")
        n_choppy_indep = by_regime["CHOPPY"]["INDEPENDENT_VIEW"]["n"]
        n_trending_indep = by_regime["TRENDING"]["INDEPENDENT_VIEW"]["n"]
        per_family[fam] = {
            "n_choppy_nominal": n_choppy_nominal, "n_trending_nominal": n_trending_nominal,
            "ratio_nominal_choppy_over_trending": ratio(n_choppy_nominal, n_trending_nominal),
            "n_choppy_independent": n_choppy_indep, "n_trending_independent": n_trending_indep,
            "ratio_independent_choppy_over_trending": ratio(n_choppy_indep, n_trending_indep),
            "minimum_arm_size_independent": min(n_choppy_indep, n_trending_indep),
        }

    pooled_n_choppy_nominal = sum(v["n_choppy_nominal"] for v in per_family.values())
    pooled_n_trending_nominal = sum(v["n_trending_nominal"] for v in per_family.values())
    pooled_n_choppy_indep = sum(v["n_choppy_independent"] for v in per_family.values())
    pooled_n_trending_indep = sum(v["n_trending_independent"] for v in per_family.values())
    pooled = {
        "n_choppy_nominal": pooled_n_choppy_nominal, "n_trending_nominal": pooled_n_trending_nominal,
        "ratio_nominal_choppy_over_trending": ratio(pooled_n_choppy_nominal, pooled_n_trending_nominal),
        "n_choppy_independent_naive_sum": pooled_n_choppy_indep,
        "n_trending_independent_naive_sum": pooled_n_trending_indep,
        "ratio_independent_naive_choppy_over_trending": ratio(pooled_n_choppy_indep, pooled_n_trending_indep),
        "minimum_arm_size_independent_naive": min(pooled_n_choppy_indep, pooled_n_trending_indep),
        "note": "I valori 'independent' pooled qui sono la SOMMA per-famiglia (naive) - per il conteggio "
                "pooled CORRETTO (dopo declustering cross-family) vedi cross_family_pooled_geometry."
                " Riportato qui solo a fini di bilancio regime/regime, non come sostituto del conteggio "
                "pooled autorevole.",
    }
    return {"per_family": per_family, "pooled": pooled}


class _SimpleReuseLedger:
    """Ledger di riuso minimale per il matching stesso-famiglia - stessa
    interfaccia di ControlReuseLedger (filter_available_pool/usage_count/
    register_controls_used/usage_report), riusato per costruzione (import
    diretto), MAI reimplementato qui."""
    pass


def run_same_family_matching(fam, within_family_geometry, state_df, spec):
    """Matching CHOPPY-vs-TRENDING, SEMPRE stessa famiglia (mai cross-family),
    riusando BaselineEngineV4/ControlReuseLedger direttamente (non
    run_matching_preflight del gate: quella funzione forza
    control_direction_by_id = direzione dell'EVENTO per ogni controllo,
    corretto per un baseline controfattuale generico ma SBAGLIATO qui - i
    controlli TRENDING hanno una loro direzione REALE che deve essere
    confrontata con quella dell'evento CHOPPY, mai sovrascritta)."""
    ms = spec["matching_spec"]
    atr_pct = state_df["atr_percentile"].values

    choppy_funnel = within_family_geometry[fam]["CHOPPY"]
    trending_funnel = within_family_geometry[fam]["TRENDING"]
    choppy_rows = choppy_funnel["INDEPENDENT_VIEW"]["representative_rows"]
    trending_rows = trending_funnel["INDEPENDENT_VIEW"]["representative_rows"]
    choppy_dir = choppy_funnel["INDEPENDENT_VIEW"]["direction_by_row"]
    trending_dir = trending_funnel["INDEPENDENT_VIEW"]["direction_by_row"]

    if not choppy_rows or not trending_rows:
        return {
            "status": "MATCHING_STRUCTURALLY_INFEASIBLE",
            "fail_reasons": ["NO_SAME_FAMILY_COMPARATOR_ARM"],
            "n_choppy_independent": len(choppy_rows), "n_trending_independent": len(trending_rows),
            "n_matched": 0, "n_unmatched": len(choppy_rows), "match_quality_counts": None, "reuse_report": None,
        }

    def feat(row):
        v = atr_pct[row - 1] if 0 <= row - 1 < len(atr_pct) else np.nan
        return {"volatility_state_pre_setup": None if np.isnan(v) else float(v)}

    discovery_start, discovery_end = ms["split_boundaries"]["discovery"]
    discovery_features_by_row = {
        r: feat(r) for r in range(discovery_start, discovery_end)
        if not np.isnan(atr_pct[r - 1] if 0 <= r - 1 < len(atr_pct) else np.nan)
    }

    control_row_by_id = {f"CTRL-{r}": r for r in trending_rows}
    control_features_by_id = {f"CTRL-{r}": feat(r) for r in trending_rows}
    control_direction_by_id = {f"CTRL-{r}": trending_dir[r] for r in trending_rows}
    control_pool = list(control_row_by_id.keys())

    events = [{"event_id": f"INDEP-{r}", "event_row": r, "direction": choppy_dir[r], "features": feat(r)}
              for r in choppy_rows]

    def _run(engine):
        return [engine.match(event_id=ev["event_id"], event_row=ev["event_row"], event_direction=ev["direction"],
                              event_features=ev["features"], control_pool=control_pool,
                              control_row_by_id=control_row_by_id, control_direction_by_id=control_direction_by_id,
                              control_features_by_id=control_features_by_id)
                for ev in events]

    engine = BaselineEngineV4(match_dimensions=ms["match_dimensions"], k=ms["k"],
                               split_boundaries=ms["split_boundaries"], minimum_control_count=ms["minimum_control_count"],
                               max_control_reuse_per_run=ms["max_control_reuse_per_run"])
    engine.fit_normalization(discovery_features_by_row)
    results = _run(engine)

    engine_repeat = BaselineEngineV4(match_dimensions=ms["match_dimensions"], k=ms["k"],
                                      split_boundaries=ms["split_boundaries"], minimum_control_count=ms["minimum_control_count"],
                                      max_control_reuse_per_run=ms["max_control_reuse_per_run"])
    engine_repeat.fit_normalization(discovery_features_by_row)
    repeat_results = _run(engine_repeat)
    tie_break_deterministic = (
        [sorted(m["control_id"] for m in r["matches"]) for r in results] ==
        [sorted(m["control_id"] for m in r["matches"]) for r in repeat_results]
    )

    quality_report = build_quality_report(results)
    reuse_report = engine.reuse_usage_report()
    max_reuse_within_cap = True
    if reuse_report and ms["max_control_reuse_per_run"]:
        max_reuse_within_cap = reuse_report["max_reuse_observed"] <= ms["max_control_reuse_per_run"]

    fail_reasons = []
    if not tie_break_deterministic:
        fail_reasons.append("TIE_BREAK_NOT_DETERMINISTIC")
    if not max_reuse_within_cap:
        fail_reasons.append("MAX_CONTROL_REUSE_EXCEEDS_DECLARED_CAP")

    all_events_rejected_insufficient_pool = (
        quality_report["n_matched"] == 0 and quality_report["n_rejected_insufficient_pool"] == len(events)
    )
    if all_events_rejected_insufficient_pool:
        fail_reasons.append("CONTROL_POOL_BELOW_MINIMUM_CONTROL_COUNT_AFTER_DIRECTION_CONDITIONING")

    status = "MATCHING_STRUCTURALLY_INFEASIBLE" if fail_reasons else "EXECUTED_FEASIBLE"
    return {
        "status": status,
        "fail_reasons": fail_reasons,
        "all_events_rejected_insufficient_pool": all_events_rejected_insufficient_pool,
        "n_choppy_independent": len(choppy_rows),
        "n_trending_independent": len(trending_rows),
        "n_matched": quality_report["n_matched"],
        "n_unmatched": quality_report["n_rejected_insufficient_pool"],
        "match_quality_counts": quality_report["match_quality_counts"],
        "poor_match_share": quality_report["poor_match_share"],
        "tie_break_deterministic": tie_break_deterministic,
        "max_reuse_within_declared_cap": max_reuse_within_cap,
        "reuse_report": reuse_report,
    }


def compute_matching_feasibility(within_family_geometry, state_df, spec):
    families = sorted(within_family_geometry.keys())
    per_family = {}
    families_with_matching_failures = []
    for fam in families:
        res = run_same_family_matching(fam, within_family_geometry, state_df, spec)
        per_family[fam] = res
        if res["status"] != "EXECUTED_FEASIBLE":
            families_with_matching_failures.append(fam)
    return {"per_family": per_family, "families_with_matching_failures": families_with_matching_failures}


def classify_family_verdict(fam, within_family_geometry, matching_result, min_ev_gates):
    """NESSUNA soglia 'per braccio di regime' e' applicata qui (vedi
    arm_size_policy/NEEDS_ARM_SIZE_POLICY - nessun canone esiste nel
    progetto per questo). L'UNICA soglia numerica riusata e'
    n_nominal_minimum (gia' canonica, minimum_evidence_gates.json,
    STESSO gate gia' usato in evaluate_matching_feasibility del gate
    Phase 7.5A per 'independent_units_with_valid_match'), applicata qui
    al numero di unita' EFFETTIVAMENTE matchate (n_matched) - il
    campione realmente analizzabile per il contrasto CHOPPY-vs-TRENDING
    di questa famiglia, non un conteggio grezzo per braccio."""
    minimum_required_n = min_ev_gates["gates"]["n_nominal_minimum"]["value"]
    choppy_n = within_family_geometry[fam]["CHOPPY"]["INDEPENDENT_VIEW"]["n"]
    trending_n = within_family_geometry[fam]["TRENDING"]["INDEPENDENT_VIEW"]["n"]
    m = matching_result["per_family"][fam]
    if choppy_n == 0 or trending_n == 0:
        return "MATCHING_STRUCTURALLY_INFEASIBLE"
    if m["status"] == "MATCHING_STRUCTURALLY_INFEASIBLE":
        return "MATCHING_STRUCTURALLY_INFEASIBLE"
    if m.get("n_matched", 0) < minimum_required_n:
        return "FAMILY_LEVEL_INSUFFICIENT"
    return "FAMILY_LEVEL_FEASIBLE"


def compute_overall_verdict(per_family_verdicts, cross_family_pooled_geometry, choppy_trending_balance,
                             arm_size_policy, min_ev_gates):
    minimum_required_n = min_ev_gates["gates"]["n_nominal_minimum"]["value"]
    any_family_feasible = any(v == "FAMILY_LEVEL_FEASIBLE" for v in per_family_verdicts.values())
    any_matching_infeasible = any(v == "MATCHING_STRUCTURALLY_INFEASIBLE" for v in per_family_verdicts.values())
    any_family_insufficient = any(v == "FAMILY_LEVEL_INSUFFICIENT" for v in per_family_verdicts.values())

    ndc = cross_family_pooled_geometry["no_double_counting_check"]
    pooled_choppy = ndc["CHOPPY_pooled_independent_units"]
    pooled_trending = ndc["TRENDING_pooled_independent_units"]
    pooled_all = cross_family_pooled_geometry["pooled_independent_units"]

    # invariant_holds=False sarebbe un BUG di programma (pooled>naive), mai un finding scientifico -
    # fail-closed esplicito, mai un flag "soft" mescolato con gli stati di verdetto sostanziali.
    assert ndc["invariant_holds"] and ndc["CHOPPY_invariant_holds"] and ndc["TRENDING_invariant_holds"], (
        "BUG: pooled_independent_units supera la somma naive per-famiglia - violazione del no-double-"
        "counting invariant congelato nello spec, non un risultato scientifico valido."
    )

    pooled_feasible = (pooled_all >= minimum_required_n) and any_family_feasible
    pooled_dependence_collapse = ndc["cross_family_collapse_detected"] and (pooled_all < minimum_required_n)

    # ARM_IMBALANCE (descrittivo, mai un gate): una famiglia FEASIBLE il cui braccio piu' piccolo e'
    # comunque marcatamente sotto la meta' del braccio piu' grande - segnalato per trasparenza, MAI
    # usato per bocciare la famiglia (nessuna soglia per-braccio esiste - NEEDS_ARM_SIZE_POLICY).
    arm_imbalance_families = []
    for fam, verdict in per_family_verdicts.items():
        if verdict != "FAMILY_LEVEL_FEASIBLE":
            continue
        bal = choppy_trending_balance["per_family"][fam]
        c, t = bal["n_choppy_independent"], bal["n_trending_independent"]
        if max(c, t) and min(c, t) < 0.5 * max(c, t):
            arm_imbalance_families.append(fam)

    statuses = []
    if any_family_feasible:
        statuses.append("FAMILY_LEVEL_FEASIBLE")
    if any_family_insufficient:
        statuses.append("FAMILY_LEVEL_INSUFFICIENT")
    if any_matching_infeasible:
        statuses.append("MATCHING_STRUCTURALLY_INFEASIBLE")
    if pooled_feasible:
        statuses.append("POOLED_FEASIBLE")
    if pooled_dependence_collapse:
        statuses.append("POOLED_DEPENDENCE_COLLAPSE")
    if arm_imbalance_families:
        statuses.append("ARM_IMBALANCE")
    statuses.append(arm_size_policy["flag"])  # NEEDS_ARM_SIZE_POLICY - sempre presente, mai un gate applicato

    return {
        "per_family_verdicts": per_family_verdicts,
        "pooled_choppy_independent_units": pooled_choppy,
        "pooled_trending_independent_units": pooled_trending,
        "pooled_all_regimes_independent_units": pooled_all,
        "pooled_feasible_by_n_nominal_minimum": pooled_feasible,
        "pooled_dependence_collapse_detected": pooled_dependence_collapse,
        "arm_imbalance_families_diagnostic_only": arm_imbalance_families,
        "composite_verdict_states": statuses,
        "note": "Gli stati family-level (FAMILY_LEVEL_FEASIBLE/FAMILY_LEVEL_INSUFFICIENT/"
                "MATCHING_STRUCTURALLY_INFEASIBLE) NON sono collassati in un singolo verdetto pooled 'verde' - "
                "un fallimento a livello di famiglia resta visibile anche se il pooled cross-family risulta "
                "FEASIBLE. NEEDS_ARM_SIZE_POLICY e' sempre incluso perche' nessun gate pass/fail per-braccio "
                "e' stato applicato (nessuna soglia inventata - vedi arm_size_policy nello spec). "
                "ARM_IMBALANCE e' puramente descrittivo (mai un gate) - vedi arm_imbalance_families_"
                "diagnostic_only.",
    }


def main():
    spec = load_spec()
    setup_pop = load_setup_population()
    min_ev_gates = load_json(os.path.join(PHASE7_DIR, "policies", "minimum_evidence_gates.json"))

    records, med_excluded, duplicates, (disc_start, disc_end), state_df = build_eligible_setup_table(spec, setup_pop)
    n_bars_discovery = disc_end - disc_start
    families = setup_pop["eligible_setup_families"]

    base_counts = compute_base_counts(records, med_excluded, families)
    overlap_audit = compute_overlap_audit(records, med_excluded)
    within_family_geometry = compute_within_family_geometry(records, spec, n_bars_discovery)
    cross_family_pooled_geometry = compute_cross_family_pooled_geometry(records, within_family_geometry, spec)
    choppy_trending_balance = compute_choppy_trending_balance(records, within_family_geometry)
    matching_feasibility = compute_matching_feasibility(within_family_geometry, state_df, spec)

    per_family_verdicts = {
        fam: classify_family_verdict(fam, within_family_geometry, matching_feasibility, min_ev_gates)
        for fam in families
    }
    overall_verdict = compute_overall_verdict(per_family_verdicts, cross_family_pooled_geometry,
                                               choppy_trending_balance, spec["arm_size_policy"], min_ev_gates)

    def _strip_funnel_for_json(funnel):
        f = dict(funnel)
        f["INDEPENDENT_VIEW"] = dict(f["INDEPENDENT_VIEW"])
        f["INDEPENDENT_VIEW"]["direction_by_row"] = {str(k): v for k, v in f["INDEPENDENT_VIEW"]["direction_by_row"].items()}
        return f

    within_family_geometry_json = {
        fam: {regime: _strip_funnel_for_json(funnel) for regime, funnel in by_regime.items()}
        for fam, by_regime in within_family_geometry.items()
    }

    payload = {
        "phase": "7.6C",
        "artifact_role": "PREFLIGHT_RESULT_COMMIT",
        "spec_commit_reference": "6c0d3f6 (server/research_scripts/phase7/phase7_6c/seq0014b_structural_preflight_spec_v1.json)",
        "development_discovery_row_range": [disc_start, disc_end],
        "n_bars_discovery": n_bars_discovery,
        "same_family_same_row_duplicate_detector_firings": duplicates,
        "base_counts": base_counts,
        "overlap_audit": overlap_audit,
        "within_family_geometry": within_family_geometry_json,
        "cross_family_pooled_geometry": cross_family_pooled_geometry,
        "choppy_trending_balance": choppy_trending_balance,
        "matching_feasibility": matching_feasibility,
        "overall_structural_verdict": overall_verdict,
        "seq0014b_status": None,
        "arm_size_policy_reused_from_spec": spec["arm_size_policy"],
        "no_nexus_outcome_data_accessed": True,
        "no_edge_discovery_performed": True,
        "no_primary_outcome_selected": True,
        "seq0015_status_unchanged": "CLOSED_NOT_REEXAMINED_AS_CANDIDATE",
        "seq0009_status_unchanged": "CLOSED_NOT_REEXAMINED_AS_CANDIDATE",
    }

    hard_stop = not any(v == "FAMILY_LEVEL_FEASIBLE" for v in per_family_verdicts.values()) and \
        not overall_verdict["pooled_feasible_by_n_nominal_minimum"]
    payload["seq0014b_status"] = (
        "NOT_TESTABLE_WITH_FROZEN_SETUP_POPULATION" if hard_stop else
        "STRUCTURALLY_FEASIBLE_AWAITING_STATISTICAL_PREREGISTRATION"
    )
    payload["hard_stop_triggered"] = hard_stop

    doc = wrap_with_provenance(payload, script="server/research_scripts/phase7/phase7_6c/build_seq0014b_structural_preflight_result.py")
    out_path = os.path.join(PHASE76C_DIR, "seq0014b_structural_preflight_result_v1.json")
    save_json(out_path, doc)
    print(f"Written {out_path}")
    print(f"canonical_sha256={doc['canonical_sha256']}")
    print(f"SEQ0014B_STATUS = {payload['seq0014b_status']}")
    return payload


if __name__ == "__main__":
    main()
