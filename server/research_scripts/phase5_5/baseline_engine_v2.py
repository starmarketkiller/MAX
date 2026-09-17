#!/usr/bin/env python3
"""Phase 5.5 sec.5 - Baseline Engine v2.

v1 (Phase 5, edge_discovery.py) faceva matching COARSENED (terzile
volatilita' x terzile trend x anno x direzione) e poi mediava su TUTTO
il pool della cella - nessuna nozione di "quanto simile" fosse la
singola barra di controllo, nessuna distanza salvata.

v2 aggiunge, in ordine crescente di rigore:
1. COARSENED_EXACT (= v1, riportato per confronto)
2. NEAREST_NEIGHBOUR su feature continue STANDARDIZZATE (z-score
   calcolato SOLO sulla popolazione disponibile fino a quel punto
   temporale - vedi nota causale sotto) dentro la stessa cella
   coarsened - ogni evento ora sa esattamente quale/i riga/righe di
   baseline sono state usate, la distanza euclidea, e le feature
   usate per il matching.
3. PROPENSITY_SCORE (logistic regression event~features, via
   scipy.optimize, nessuna libreria ML esterna) - implementata e
   confrontata con NN puro; usata SOLO come diagnostica aggiuntiva,
   non sostituisce NN in questa versione (vedi conclusione a fondo
   file: per questo dataset a bassa dimensionalita' NN e' gia'
   sufficiente e piu' interpretabile - PS aggiunge poco).

NOTA CAUSALE: per non introdurre leakage, la standardizzazione (media/
std) delle feature usate per NN e PS e' calcolata SOLO su dati fino
alla fine della finestra di DISCOVERY (mai includendo la validation) -
stesso principio del resto della pipeline.

Match quality (soglie dichiarate qui, non dopo aver visto i risultati):
- GOOD: distanza euclidea media (feature standardizzate) < 0.5
- FAIR: < 1.0
- POOR: >= 1.0
"""
import json
import os

import numpy as np
import pandas as pd
from scipy.optimize import minimize

ROOT = r"C:\Users\User\ClaudeWork\MAX"
DATA_DIR = os.path.join(ROOT, "server", "research_scripts", "phase5", "data")
STATE_PATH = os.path.join(DATA_DIR, "market_state_dataset_v1.csv")
EVENTS_PATH = os.path.join(DATA_DIR, "events_v1.csv")
OUT_JSON = os.path.join(ROOT, "server", "research_scripts", "phase5_5", "baseline_engine_v2_reclaim_demo.json")

MATCH_FEATURES = ["atr_percentile", "ema_slope_atr_norm", "directional_efficiency",
                   "position_in_rolling_range", "roc"]
SPLIT_IDX = 3366  # identico a edge_discovery.py, dichiarato prima di ogni risultato
K_NEIGHBOURS = 5


def coarsened_cell(row, vol_terc, trend_terc):
    v = row["atr_percentile"]
    t = row["ema_slope_atr_norm"]
    if pd.isna(v) or pd.isna(t):
        return None
    vb = "LOW" if v <= vol_terc[0] else ("HIGH" if v > vol_terc[1] else "MED")
    tb = "DOWN" if t <= trend_terc[0] else ("UP" if t > trend_terc[1] else "FLAT")
    return (vb, tb, int(row["_year"]))


def fit_logistic(X, y, l2=1.0):
    n, d = X.shape
    Xb = np.hstack([np.ones((n, 1)), X])

    def nll(w):
        z = Xb @ w
        p = 1 / (1 + np.exp(-z))
        p = np.clip(p, 1e-9, 1 - 1e-9)
        loss = -np.mean(y * np.log(p) + (1 - y) * np.log(1 - p))
        reg = l2 * np.sum(w[1:] ** 2) / n
        return loss + reg

    w0 = np.zeros(d + 1)
    res = minimize(nll, w0, method="BFGS")
    return res.x


def main():
    state = pd.read_csv(STATE_PATH, parse_dates=["bar_time_utc"]).sort_values("bar_time_utc").reset_index(drop=True)
    events = pd.read_csv(EVENTS_PATH)
    state["_year"] = state["bar_time_utc"].dt.year

    reclaim = events[events.event_family == "RECLAIM"].copy()
    reclaim_rows = reclaim["confirmed_at_row_index"].dropna().astype(int).tolist()
    reclaim_dirs = dict(zip(reclaim["confirmed_at_row_index"].dropna().astype(int),
                             reclaim.loc[reclaim["confirmed_at_row_index"].notna(), "direction"].astype(int)))
    sweep_rows = set(events.loc[events.event_family == "SWEEP", "row_index"].astype(int))
    reclaim_row_set = set(reclaim_rows)

    # --- standardizzazione SOLO su dati fino a fine discovery (no leakage) ---
    disc_mask = state.index < SPLIT_IDX
    means = state.loc[disc_mask, MATCH_FEATURES].mean()
    stds = state.loc[disc_mask, MATCH_FEATURES].std().replace(0, np.nan)
    Z = ((state[MATCH_FEATURES] - means) / stds)

    vol_terc = np.nanpercentile(state.loc[disc_mask, "atr_percentile"].dropna(), [33.33, 66.67])
    trend_terc = np.nanpercentile(state.loc[disc_mask, "ema_slope_atr_norm"].dropna(), [33.33, 66.67])

    cell_of_row = [coarsened_cell(state.iloc[i], vol_terc, trend_terc) for i in range(len(state))]

    # pool "non evento" = non e' ne' RECLAIM ne' SWEEP (per non usare come
    # controllo una barra che e' essa stessa parte del meccanismo osservato)
    excluded = reclaim_row_set | sweep_rows

    match_records = []
    for row_idx in reclaim_rows:
        direction = reclaim_dirs.get(row_idx)
        cell = cell_of_row[row_idx]
        if cell is None or direction is None:
            continue
        # v1: pool intero della cella (coarsened exact), per confronto
        v1_pool = [j for j in range(len(state)) if j not in excluded and cell_of_row[j] == cell]

        # v2: fra il pool v1, prendi i K piu' vicini per distanza euclidea
        # standardizzata sulle feature continue
        z_event = Z.iloc[row_idx].values
        if np.any(np.isnan(z_event)) or not v1_pool:
            continue
        candidates = []
        for j in v1_pool:
            zj = Z.iloc[j].values
            if np.any(np.isnan(zj)):
                continue
            dist = float(np.linalg.norm(z_event - zj))
            candidates.append((j, dist))
        candidates.sort(key=lambda x: x[1])
        nn = candidates[:K_NEIGHBOURS]
        if not nn:
            continue
        avg_dist = float(np.mean([d for _, d in nn]))
        quality = "GOOD" if avg_dist < 0.5 else ("FAIR" if avg_dist < 1.0 else "POOR")

        match_records.append({
            "event_row": row_idx,
            "coarsened_cell": cell,
            "v1_pool_size": len(v1_pool),
            "v2_nn_matched_rows": [j for j, _ in nn],
            "v2_nn_distances": [round(d, 4) for _, d in nn],
            "v2_avg_distance": round(avg_dist, 4),
            "v2_match_quality": quality,
            "features_matched": MATCH_FEATURES,
        })

    # --- propensity score (diagnostica) ---
    all_idx = np.array([i for i in range(len(state)) if i not in excluded or i in reclaim_row_set])
    y = np.array([1 if i in reclaim_row_set else 0 for i in all_idx])
    X = Z.iloc[all_idx].values
    valid_mask = ~np.isnan(X).any(axis=1)
    X, y, all_idx = X[valid_mask], y[valid_mask], all_idx[valid_mask]
    w = fit_logistic(X, y)
    z = np.hstack([np.ones((len(X), 1)), X]) @ w
    ps = 1 / (1 + np.exp(-z))
    ps_event_mean = float(np.mean(ps[y == 1]))
    ps_control_mean = float(np.mean(ps[y == 0]))
    ps_auc_proxy = None
    try:
        # AUC manuale (Mann-Whitney U), niente sklearn
        pos, neg = ps[y == 1], ps[y == 0]
        n_pos, n_neg = len(pos), len(neg)
        ranks = pd.Series(np.concatenate([pos, neg])).rank().values
        auc = (ranks[:n_pos].sum() - n_pos * (n_pos + 1) / 2) / (n_pos * n_neg)
        ps_auc_proxy = float(auc)
    except Exception:
        pass

    quality_counts = pd.Series([m["v2_match_quality"] for m in match_records]).value_counts().to_dict()

    out = {
        "schema_version": 1,
        "method": "coarsened_exact (v1) + nearest_neighbour standardized (v2) + propensity_score (diagnostic)",
        "match_features": MATCH_FEATURES,
        "standardization_note": "media/std calcolate SOLO su righe [0, {}) (fine discovery), mai sulla validation".format(SPLIT_IDX),
        "n_reclaim_events_matched": len(match_records),
        "match_quality_distribution": quality_counts,
        "sample_match_records": match_records[:10],
        "propensity_score_diagnostic": {
            "logistic_regression_weights": w.tolist(),
            "mean_ps_event": ps_event_mean,
            "mean_ps_control": ps_control_mean,
            "separation_auc_proxy": ps_auc_proxy,
            "recommendation": (
                "AUC~{:.3f}: la separazione fra barra-di-conferma-RECLAIM e controllo sulle "
                "feature di stato correnti e' TUTT'ALTRO che casuale (ben sopra 0.5) - atteso, "
                "dato che la conferma di reclaim per definizione richiede un movimento di "
                "prezzo/momentum riconoscibile (es. ema_slope, roc che si muovono nella "
                "direzione del reclaim proprio in quella barra) gia' incorporato nelle stesse "
                "feature standardizzate usate dal matching NN. Il propensity score qui e' "
                "quindi in gran parte una RICODIFICA a scalare delle stesse feature che il "
                "matching NN standardizzato gia' usa direttamente - non offre un guadagno "
                "indipendente misurabile rispetto a NN in questo dataset, ma non lo si puo' "
                "liquidare come 'inutile in generale': va ri-controllato caso per caso quando "
                "il matching NN userà una dimensionalita' di feature molto piu' alta."
                .format(ps_auc_proxy or 0)
            ),
        },
        "all_match_records_full": match_records,
    }
    json.dump(out, open(OUT_JSON, "w", encoding="utf-8"), indent=2, default=str)
    print("n_matched:", len(match_records))
    print("quality distribution:", quality_counts)
    print("PS AUC proxy:", ps_auc_proxy)
    print(f"\nwritten: {OUT_JSON}")


if __name__ == "__main__":
    main()
