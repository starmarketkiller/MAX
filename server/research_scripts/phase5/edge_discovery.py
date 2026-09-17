#!/usr/bin/env python3
"""Phase 5.E-J - Baseline matching + Conditional Edge Tests + Probability
Engine + Edge Quality classification.

METODOLOGIA DICHIARATA EX-ANTE (prima di calcolare qualunque risultato):

E. Baseline matching: per ogni evento si costruisce una popolazione di
   controllo formata da barre NON-evento (stessa famiglia) che condividono
   la stessa cella (vol_tercile, trend_tercile, anno) dell'evento, valutata
   nella STESSA direzione dell'evento (un'ipotetica entrata in quella
   direzione su quella barra). I terzili di vol/trend sono calcolati UNA
   VOLTA sull'intero dataset (non per-evento), cosi' la definizione di
   "stesso stato" e' fissa e non si adatta ai risultati.

F. Le 5 interazioni sono PREDEFINITE (elencate sotto in INTERACTIONS),
   nessuna e' stata scelta guardando i risultati.

H. Split discovery/validation: 70% CRONOLOGICO iniziale = discovery, 30%
   finale = validation. Il punto di split e' calcolato UNA VOLTA dalla
   lunghezza del dataset, PRIMA di calcolare qualunque outcome per
   evento/interazione - stampato a schermo prima di ogni risultato.

I/J. Per ogni candidato: DeltaP = P(target|evento[+condizione]) -
   P(target|baseline matched); DeltaE = E[outcome] - E[outcome baseline];
   stabilita' su discovery/validation/BUY/SELL/anno. Soglia di target
   primaria per la classificazione: +1 ATR-multiplo prima di -1
   ATR-multiplo (outcome_basis ATR_NORMALIZED, la valuta comune usata per
   TUTTI i confronti evento-vs-baseline in questo file, anche per le
   famiglie R-based, perche' una barra di baseline non ha un "livello"
   naturale di rischio - vedi outcomes_v1 per gli R-outcome nativi delle
   4 famiglie R-based, riportati a parte, non qui).

Classificazione (soglie dichiarate qui, non dopo):
- SUPPORTED_EDGE: stesso segno dell'effetto discovery/validation; DeltaP>0
  E DeltaE>0 in validation; n_validation>=30; CI95/posteriore non
  compatibile con effetto nullo in modo materiale (Wilson CI95 low > 0 su
  DeltaP stimato via due proporzioni indipendenti, approssimato come
  CI(evento) e CI(baseline) non sovrapposte); rimuovendo il 10% di eventi
  con il miglior outcome singolo l'effetto resta positivo (check
  no-outlier-dependence).
- WEAK_EDGE: stesso segno discovery/validation, DeltaP>0 in validation ma
  CI sovrapposte o n_validation<30.
- NO_EDGE: DeltaP/DeltaE non consistentemente positivi, o CI ampiamente
  compatibili con zero.
- OPPOSITE_EDGE: segno dell'effetto INVERTITO tra discovery e validation,
  o baseline sistematicamente migliore dell'evento.
- INSUFFICIENT_SAMPLE: n_discovery<15 o n_validation<15.
"""
import json
import os
from datetime import datetime, timezone

import numpy as np
import pandas as pd

from stats_utils import probability_record, wilson_ci95

ROOT = r"C:\Users\User\ClaudeWork\MAX"
DATA_DIR = os.path.join(ROOT, "server", "research_scripts", "phase5", "data")
BARS_PATH = os.path.join(DATA_DIR, "xauusd_h4_bars.csv")
STATE_PATH = os.path.join(DATA_DIR, "market_state_dataset_v1.csv")
EVENTS_PATH = os.path.join(DATA_DIR, "events_v1.csv")
OUT_RESULTS = os.path.join(DATA_DIR, "edge_results_v1.json")

HORIZON = 40
PRIMARY_THRESHOLD = 1.0  # ATR-multipli, usato per la classificazione principale
ALL_THRESHOLDS = [0.25, 0.5, 1.0, 1.5, 2.0, 3.0]

EVENT_FAMILIES = ["BREAKOUT", "FAILED_BREAKOUT", "SWEEP", "RECLAIM", "RETEST",
                  "DISPLACEMENT", "COMPRESSION_RELEASE", "VOLATILITY_EXPANSION", "PULLBACK"]

# --- F: le 5 interazioni predefinite ---
INTERACTIONS = [
    {
        "name": "BREAKOUT_x_VOLATILITY_EXPANSION",
        "base_family": "BREAKOUT",
        "condition": lambda ev_row, state_row: ev_row["_is_also_vol_expansion"],
        "condition_desc": "la barra di breakout e' anche una barra di VOLATILITY_EXPANSION (true range > 1.0xATR)",
    },
    {
        "name": "BREAKOUT_x_TREND_PERSISTENCE",
        "base_family": "BREAKOUT",
        "condition": lambda ev_row, state_row: (
            np.sign(state_row["ema_slope_atr_norm"]) == ev_row["direction"]
            and state_row["trend_persistence_bars"] >= TREND_PERSISTENCE_MEDIAN
        ),
        "condition_desc": "trend EMA gia' allineato alla direzione del breakout E persistenza di trend >= mediana del dataset",
    },
    {
        "name": "SWEEP_RECLAIM_x_LOCATION",
        "base_family": "SWEEP",
        "condition": lambda ev_row, state_row: (
            (ev_row["direction"] == -1 and state_row["position_in_rolling_range"] >= 0.8)
            or (ev_row["direction"] == 1 and state_row["position_in_rolling_range"] <= 0.2)
        ),
        "condition_desc": "lo sweep avviene a un estremo di location del range rolling (>=0.8 per sweep di high, <=0.2 per sweep di low)",
    },
    {
        "name": "COMPRESSION_RELEASE_x_DIRECTIONAL_EFFICIENCY",
        "base_family": "COMPRESSION_RELEASE",
        "condition": lambda ev_row, state_row: state_row["directional_efficiency"] >= EFFICIENCY_TOP_TERCILE,
        "condition_desc": "directional_efficiency alla barra di release nel terzile piu' alto del dataset",
    },
    {
        "name": "DISPLACEMENT_x_VOLATILITY_STATE",
        "base_family": "DISPLACEMENT",
        "condition": lambda ev_row, state_row: state_row["atr_percentile"] <= VOL_BOTTOM_TERCILE,
        "condition_desc": "displacement mentre atr_percentile e' nel terzile piu' basso (sorpresa di volatilita' in contesto quieto)",
    },
]

# popolati a runtime dai terzili globali (dichiarati qui come nomi, calcolati in main())
TREND_PERSISTENCE_MEDIAN = None
EFFICIENCY_TOP_TERCILE = None
VOL_BOTTOM_TERCILE = None


def atr_outcome_for_bar(row_idx, direction, df, atr_col, horizon=HORIZON):
    n = len(df)
    end = min(row_idx + horizon, n - 1)
    if end <= row_idx:
        return None
    entry_price = df["close"].values[row_idx]
    atr_entry = atr_col[row_idx]
    if np.isnan(atr_entry) or atr_entry <= 0:
        return None
    highs = df["high"].values[row_idx + 1:end + 1]
    lows = df["low"].values[row_idx + 1:end + 1]
    if len(highs) == 0:
        return None
    if direction >= 0:
        fav = (highs - entry_price) / atr_entry
        adv = (entry_price - lows) / atr_entry
    else:
        fav = (entry_price - lows) / atr_entry
        adv = (highs - entry_price) / atr_entry
    mfe, mae = float(np.max(fav)), float(np.max(adv))
    res = {"mfe_ATR": mfe, "mae_ATR": mae}
    for th in ALL_THRESHOLDS:
        hit_t = fav >= th
        hit_s = adv >= 1.0
        ti = np.argmax(hit_t) if np.any(hit_t) else None
        si = np.argmax(hit_s) if np.any(hit_s) else None
        if ti is None and si is None:
            res[f"outcome_{th}"] = "CENSORED"
        elif ti is not None and (si is None or ti <= si):
            res[f"outcome_{th}"] = "TARGET_FIRST"
        else:
            res[f"outcome_{th}"] = "STOP_FIRST"
    return res


def build_baseline_pool(df, state, exclude_rows_set, cell_of_row, direction, cells_needed, atr_col):
    """Pool di barre NON-evento (per la famiglia data) che condividono
    almeno una delle celle (vol_tercile,trend_tercile,anno) richieste,
    valutate nella direzione data."""
    outcomes = []
    n = len(df)
    for row_idx in range(n):
        if row_idx in exclude_rows_set:
            continue
        if cell_of_row[row_idx] not in cells_needed:
            continue
        o = atr_outcome_for_bar(row_idx, direction, df, atr_col)
        if o is not None:
            outcomes.append(o)
    return outcomes


def wl_censored(outcomes, key):
    wins = sum(1 for o in outcomes if o[key] == "TARGET_FIRST")
    losses = sum(1 for o in outcomes if o[key] == "STOP_FIRST")
    censored = sum(1 for o in outcomes if o[key] == "CENSORED")
    return wins, losses, censored


def mean_mfe(outcomes):
    return float(np.mean([o["mfe_ATR"] for o in outcomes])) if outcomes else None


def delta_metrics(event_outcomes, baseline_outcomes, threshold_key):
    ew, el, ec = wl_censored(event_outcomes, threshold_key)
    bw, bl, bc = wl_censored(baseline_outcomes, threshold_key)
    ep_rec = probability_record(ew, el, ec)
    bp_rec = probability_record(bw, bl, bc)
    delta_p = (ep_rec["observed_p"] - bp_rec["observed_p"]) if (ep_rec["observed_p"] is not None and bp_rec["observed_p"] is not None) else None
    delta_e = (mean_mfe(event_outcomes) - mean_mfe(baseline_outcomes)) if (event_outcomes and baseline_outcomes) else None
    # CI non sovrapposte come proxy di "non compatibile con effetto nullo"
    ci_non_overlap = None
    if ep_rec["wilson_ci95_low"] is not None and bp_rec["wilson_ci95_high"] is not None:
        ci_non_overlap = ep_rec["wilson_ci95_low"] > bp_rec["wilson_ci95_high"]
    return {
        "event": ep_rec, "baseline": bp_rec,
        "delta_p": delta_p, "delta_e_mfe_atr": delta_e,
        "ci95_non_overlapping": ci_non_overlap,
    }


def outlier_robustness_check(event_outcomes, threshold_key, drop_frac=0.10):
    """Rimuove il drop_frac di eventi con il miglior mfe_ATR singolo e
    ricontrolla se la proporzione TARGET_FIRST resta positiva/simile."""
    if len(event_outcomes) < 10:
        return None
    sorted_ev = sorted(event_outcomes, key=lambda o: o["mfe_ATR"], reverse=True)
    n_drop = max(1, int(len(sorted_ev) * drop_frac))
    trimmed = sorted_ev[n_drop:]
    w, l, c = wl_censored(trimmed, threshold_key)
    n = w + l
    return {"n_after_trim": n, "p_after_trim": (w / n if n else None)}


def classify(disc, val, robustness):
    n_disc = disc["event"]["n"]
    n_val = val["event"]["n"]
    if n_disc < 15 or n_val < 15:
        return "INSUFFICIENT_SAMPLE"
    dp_disc, dp_val = disc["delta_p"], val["delta_p"]
    de_disc, de_val = disc["delta_e_mfe_atr"], val["delta_e_mfe_atr"]
    if dp_disc is None or dp_val is None:
        return "INSUFFICIENT_SAMPLE"
    same_sign = (dp_disc > 0) == (dp_val > 0)
    if not same_sign and (dp_disc > 0) != (dp_val > 0):
        # segno invertito tra discovery e validation
        if (dp_disc > 0 and dp_val < -0.05) or (dp_disc < 0 and dp_val > 0.05):
            return "OPPOSITE_EDGE"
    if dp_val <= 0 or (de_val is not None and de_val <= 0):
        return "NO_EDGE"
    if not same_sign:
        return "NO_EDGE"
    strong = (
        val.get("ci95_non_overlapping") is True
        and n_val >= 30
        and (robustness is None or robustness["p_after_trim"] is not None and robustness["p_after_trim"] > val["baseline"]["observed_p"])
    )
    return "SUPPORTED_EDGE" if strong else "WEAK_EDGE"


def main():
    global TREND_PERSISTENCE_MEDIAN, EFFICIENCY_TOP_TERCILE, VOL_BOTTOM_TERCILE

    df = pd.read_csv(BARS_PATH, parse_dates=["bar_time_utc"]).sort_values("bar_time_utc").reset_index(drop=True)
    state = pd.read_csv(STATE_PATH, parse_dates=["bar_time_utc"]).sort_values("bar_time_utc").reset_index(drop=True)
    events = pd.read_csv(EVENTS_PATH)
    atr_col = state["atr"].values
    n = len(df)

    # --- H: split 70/30 dichiarato PRIMA di ogni risultato ---
    split_idx = int(n * 0.70)
    split_time = df["bar_time_utc"].iloc[split_idx]
    print(f"[H] discovery=[0,{split_idx}) validation=[{split_idx},{n}) split_time={split_time}")

    # --- terzili globali (calcolati una volta, sull'intero dataset) ---
    vol_valid = state["atr_percentile"].dropna()
    trend_valid = state["ema_slope_atr_norm"].dropna()
    eff_valid = state["directional_efficiency"].dropna()
    vol_terc = np.nanpercentile(vol_valid, [33.33, 66.67])
    trend_terc = np.nanpercentile(trend_valid, [33.33, 66.67])
    TREND_PERSISTENCE_MEDIAN = float(state["trend_persistence_bars"].median())
    EFFICIENCY_TOP_TERCILE = float(np.nanpercentile(eff_valid, 66.67))
    VOL_BOTTOM_TERCILE = float(np.nanpercentile(vol_valid, 33.33))

    def vol_bucket(v):
        if np.isnan(v):
            return None
        return "LOW" if v <= vol_terc[0] else ("HIGH" if v > vol_terc[1] else "MED")

    def trend_bucket(v):
        if np.isnan(v):
            return None
        return "DOWN" if v <= trend_terc[0] else ("UP" if v > trend_terc[1] else "FLAT")

    year_arr = df["bar_time_utc"].dt.year.values
    vol_bucket_arr = state["atr_percentile"].apply(vol_bucket).values
    trend_bucket_arr = state["ema_slope_atr_norm"].apply(trend_bucket).values
    cell_of_row = [
        (vol_bucket_arr[i], trend_bucket_arr[i], int(year_arr[i])) if vol_bucket_arr[i] and trend_bucket_arr[i] else None
        for i in range(n)
    ]

    events_by_family_rows = {fam: set(events.loc[events["event_family"] == fam, "row_index"].astype(int)) for fam in EVENT_FAMILIES}
    vol_expansion_rows = events_by_family_rows.get("VOLATILITY_EXPANSION", set())

    results = {"meta": {
        "split_idx": split_idx, "split_time": str(split_time), "n_total_bars": n,
        "vol_terciles": vol_terc.tolist(), "trend_terciles": trend_terc.tolist(),
        "trend_persistence_median": TREND_PERSISTENCE_MEDIAN,
        "efficiency_top_tercile": EFFICIENCY_TOP_TERCILE, "vol_bottom_tercile": VOL_BOTTOM_TERCILE,
        "primary_threshold_ATR": PRIMARY_THRESHOLD,
    }, "event_alone": {}, "interactions": {}}

    def split_label(row_idx):
        return "discovery" if row_idx < split_idx else "validation"

    def run_population(rows_with_direction, exclude_rows_set, family_for_baseline_exclusion, label):
        """rows_with_direction: list of (row_idx, direction). Ritorna dict
        con outcome per-split, BUY/SELL, anno, e confronto vs baseline."""
        out = {"label": label, "n_events": len(rows_with_direction)}
        if not rows_with_direction:
            out["insufficient"] = True
            return out

        event_outcomes_all = []
        cells_needed = set()
        for row_idx, direction in rows_with_direction:
            o = atr_outcome_for_bar(row_idx, direction, df, atr_col)
            if o is None:
                continue
            o["_row"] = row_idx
            o["_direction"] = direction
            o["_split"] = split_label(row_idx)
            o["_year"] = int(year_arr[row_idx])
            event_outcomes_all.append(o)
            c = cell_of_row[row_idx]
            if c:
                cells_needed.add(c)

        # baseline pool per direzione (BUY e SELL separati, poi combinati per split)
        baseline_by_dir = {}
        for d in set(x["_direction"] for x in event_outcomes_all):
            baseline_by_dir[d] = build_baseline_pool(
                df, state, exclude_rows_set, cell_of_row, d, cells_needed, atr_col)

        def subset(pred):
            return [o for o in event_outcomes_all if pred(o)]

        def baseline_subset(pred_row_idx_list):
            pool = []
            for d, bl in baseline_by_dir.items():
                pool.extend(bl)
            return pool

        threshold_key = f"outcome_{PRIMARY_THRESHOLD}"

        disc_events = subset(lambda o: o["_split"] == "discovery")
        val_events = subset(lambda o: o["_split"] == "validation")
        # Nota: il baseline pool e' matched per cella (vol,trend,anno), quindi
        # e' gia' implicitamente confinato agli stessi anni degli eventi che
        # matcha - non serve un filtro di split separato sul baseline: la
        # cella-anno e' il controllo di comparabilita' temporale richiesto
        # dalla metodologia (sezione E), non lo split discovery/validation
        # (che e' un controllo di tenuta fuori-campione sugli EVENTI, non
        # sul baseline stesso).

        buy_events = subset(lambda o: o["_direction"] == 1)
        sell_events = subset(lambda o: o["_direction"] == -1)

        baseline_all = [o for bl in baseline_by_dir.values() for o in bl]

        out["discovery"] = delta_metrics(disc_events, baseline_all, threshold_key)
        out["validation"] = delta_metrics(val_events, baseline_all, threshold_key)
        out["buy"] = delta_metrics(buy_events, baseline_by_dir.get(1, []), threshold_key) if buy_events else None
        out["sell"] = delta_metrics(sell_events, baseline_by_dir.get(-1, []), threshold_key) if sell_events else None

        by_year = {}
        for yr in sorted(set(o["_year"] for o in event_outcomes_all)):
            yr_events = subset(lambda o, yr=yr: o["_year"] == yr)
            by_year[yr] = delta_metrics(yr_events, baseline_all, threshold_key) if len(yr_events) >= 5 else {"n": len(yr_events), "note": "n<5, non riportato"}
        out["by_year"] = by_year

        robustness = outlier_robustness_check(val_events, threshold_key)
        out["robustness_trim10pct"] = robustness
        out["classification"] = classify(out["discovery"], out["validation"], robustness)
        out["n_baseline_pool"] = len(baseline_all)
        return out

    # --- event alone, per tutte e 9 le famiglie (risponde Q1) ---
    for fam in EVENT_FAMILIES:
        fam_rows = events.loc[events["event_family"] == fam, ["row_index", "direction"]].dropna()
        rows_with_direction = [(int(r), int(d)) for r, d in zip(fam_rows["row_index"], fam_rows["direction"]) if d != 0]
        exclude = events_by_family_rows.get(fam, set())
        print(f"[event_alone] {fam}: n={len(rows_with_direction)}")
        results["event_alone"][fam] = run_population(rows_with_direction, exclude, fam, fam)

    # --- 5 interazioni predefinite ---
    events_idx = events.set_index("row_index", drop=False)
    for inter in INTERACTIONS:
        fam = inter["base_family"]
        fam_events = events[events["event_family"] == fam].copy()
        fam_events["_is_also_vol_expansion"] = fam_events["row_index"].isin(vol_expansion_rows)
        selected_rows = []
        for _, ev_row in fam_events.iterrows():
            row_idx = int(ev_row["row_index"])
            if row_idx >= len(state):
                continue
            st_row = state.iloc[row_idx]
            try:
                cond = inter["condition"](ev_row, st_row)
            except Exception:
                cond = False
            if cond and not pd.isna(ev_row["direction"]) and ev_row["direction"] != 0:
                selected_rows.append((row_idx, int(ev_row["direction"])))
        exclude = events_by_family_rows.get(fam, set())
        print(f"[interaction] {inter['name']}: n={len(selected_rows)} (condition: {inter['condition_desc']})")
        res = run_population(selected_rows, exclude, fam, inter["name"])
        res["condition_desc"] = inter["condition_desc"]
        res["base_family"] = fam
        res["base_family_alone_classification"] = results["event_alone"].get(fam, {}).get("classification")
        results["interactions"][inter["name"]] = res

    def _clean(o):
        if isinstance(o, dict):
            return {str(k): _clean(v) for k, v in o.items() if not (isinstance(k, str) and k.startswith("_"))}
        if isinstance(o, list):
            return [_clean(x) for x in o]
        if isinstance(o, (np.floating, np.integer)):
            return o.item()
        if isinstance(o, np.bool_):
            return bool(o)
        return o

    results = _clean(results)
    json.dump(results, open(OUT_RESULTS, "w", encoding="utf-8"), indent=2, default=str)
    print(f"\nwritten: {OUT_RESULTS}")


if __name__ == "__main__":
    main()
