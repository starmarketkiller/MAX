#!/usr/bin/env python3
"""Phase 6.5 sec.1/2/6 - Event Dependence Model, Effective Sample Size,
Overlapping Outcome Windows.

Modulo GENERICO e riutilizzabile - non specifico a RECLAIM. Prende in
input una lista di "eventi" con almeno {row, direction, outcome_binary}
e un orizzonte di outcome (in barre), e produce le diagnostiche di
dipendenza richieste. In questo file viene anche applicato a H006 come
CASO DI TEST (Phase 6.5 sec.8) - i numeri prodotti per H006 sono un
AUDIT RETROATTIVO, non una nuova validazione (vedi report principale).

Nessuna formula qui e' "la" formula giusta di sample size effettivo -
ne vengono riportate tre, con assunzioni/limiti dichiarati, mai una
sola presentata come definitiva (vedi ESS_METHODS_NOTES sotto).
"""
import json
import os

import numpy as np

HORIZON_BARS = 40  # stesso orizzonte di outcome usato in Phase 5/6

ESS_METHODS_NOTES = {
    "cluster_count": (
        "n_effective = numero di cluster (non di eventi). Assunzione: eventi "
        "nello stesso cluster sono trattati come UNA sola osservazione "
        "indipendente, il caso piu' conservativo possibile - sottostima "
        "l'informazione se gli eventi in cluster non sono perfettamente "
        "ridondanti, ma non la sovrastima mai."
    ),
    "autocorrelation_based": (
        "n_effective = n / (1 + 2*sum_{k=1}^{K} rho_k), rho_k = autocorrelazione "
        "lag-k della serie binaria di outcome ORDINATA per tempo. K troncato al "
        "primo lag k per cui |rho_k| scende sotto 1.96/sqrt(n) (non piu' "
        "distinguibile da rumore) o a un tetto di 10 lag, quale che venga prima. "
        "Assunzione: la dipendenza e' descritta adeguatamente da un processo "
        "stazionario a corto raggio - puo' sottostimare la dipendenza se ci sono "
        "correlazioni a lungo raggio non catturate entro il tetto di 10 lag."
    ),
    "block_bootstrap_variance": (
        "n_effective = p(1-p) / Var_block_bootstrap(p_hat). Assunzione: il block "
        "bootstrap cattura correttamente la struttura di dipendenza locale (vedi "
        "block_bootstrap.py per il criterio di lunghezza blocco) - la stima e' "
        "sensibile alla scelta della lunghezza blocco, per questo il criterio di "
        "scelta e' dichiarato separatamente e non ottimizzato per nessun risultato."
    ),
}


def compute_gaps(rows_sorted):
    return [rows_sorted[i + 1] - rows_sorted[i] for i in range(len(rows_sorted) - 1)]


def clustering_rate(rows_sorted, k):
    """Frazione di eventi che hanno ALMENO un altro evento entro k barre
    (prima o dopo)."""
    rows = np.array(sorted(rows_sorted))
    n = len(rows)
    if n < 2:
        return 0.0
    has_neighbor = np.zeros(n, dtype=bool)
    for i in range(n):
        for j in range(n):
            if i != j and abs(rows[i] - rows[j]) <= k:
                has_neighbor[i] = True
                break
    return float(has_neighbor.mean())


def assign_clusters(rows_sorted, cluster_gap_threshold):
    """Cluster = componenti connesse di una catena di eventi consecutivi con
    gap <= cluster_gap_threshold. Soglia dichiarata qui = 10 barre (lo stesso
    valore piu' ampio richiesto esplicitamente fra le finestre 1/2/3/5/10 -
    non scelta guardando quale soglia avrebbe dato il conteggio di cluster
    "piu' bello")."""
    rows = sorted(rows_sorted)
    clusters = []
    current = [rows[0]] if rows else []
    for i in range(1, len(rows)):
        if rows[i] - rows[i - 1] <= cluster_gap_threshold:
            current.append(rows[i])
        else:
            clusters.append(current)
            current = [rows[i]]
    if current:
        clusters.append(current)
    cluster_of_row = {}
    for cid, members in enumerate(clusters):
        for r in members:
            cluster_of_row[r] = cid
    return clusters, cluster_of_row


def outcome_autocorrelation(rows_sorted, outcome_by_row, max_lag=10):
    """Autocorrelazione della serie binaria di outcome (1=TARGET_FIRST,
    0=STOP_FIRST, NaN=CENSORED escluso), ordinata per riga/tempo."""
    rows = sorted(rows_sorted)
    series = np.array([outcome_by_row[r] for r in rows if outcome_by_row[r] is not None], dtype=float)
    n = len(series)
    if n < 5:
        return {"n": n, "note": "campione troppo piccolo per autocorrelazione", "lags": {}}
    mean = series.mean()
    var = series.var()
    lags = {}
    if var == 0:
        return {"n": n, "note": "varianza nulla (tutti gli outcome identici)", "lags": {}}
    for k in range(1, min(max_lag, n - 1) + 1):
        cov = np.mean((series[:-k] - mean) * (series[k:] - mean))
        lags[k] = float(cov / var)
    return {"n": n, "lags": lags}


def ess_autocorrelation(n, lags: dict):
    threshold = 1.96 / np.sqrt(n) if n > 0 else 0
    s = 0.0
    for k in sorted(lags.keys()):
        rho = lags[k]
        if abs(rho) < threshold:
            break
        s += rho
    denom = 1 + 2 * s
    if denom <= 0:
        return None
    return n / denom


def overlap_classification(rows_sorted, horizon=HORIZON_BARS):
    """Per ogni evento, calcola la massima frazione di sovrapposizione della
    propria finestra di outcome [row+1, row+horizon] con quella di QUALUNQUE
    altro evento, e classifica: independent (0), partially_overlapping
    (0,0.5), heavily_overlapping (>=0.5)."""
    rows = sorted(rows_sorted)
    windows = {r: (r + 1, r + horizon) for r in rows}
    result = {}
    for r in rows:
        s1, e1 = windows[r]
        max_frac = 0.0
        for r2 in rows:
            if r2 == r:
                continue
            s2, e2 = windows[r2]
            overlap = max(0, min(e1, e2) - max(s1, s2) + 1)
            frac = overlap / horizon
            max_frac = max(max_frac, frac)
        if max_frac == 0:
            cls = "independent"
        elif max_frac < 0.5:
            cls = "partially_overlapping"
        else:
            cls = "heavily_overlapping"
        result[r] = {"max_overlap_fraction": round(max_frac, 4), "classification": cls}
    return result


def full_dependence_report(rows, direction_by_row, outcome_by_row, label="H006_RECLAIM_HOLDOUT_AUDIT"):
    rows_sorted = sorted(rows)
    n_nominal = len(rows_sorted)
    gaps = compute_gaps(rows_sorted)

    clustering = {k: clustering_rate(rows_sorted, k) for k in (1, 2, 3, 5, 10)}
    clusters, cluster_of_row = assign_clusters(rows_sorted, cluster_gap_threshold=10)
    cluster_sizes = [len(c) for c in clusters]

    autocorr = outcome_autocorrelation(rows_sorted, outcome_by_row)
    ess_ac = ess_autocorrelation(autocorr["n"], autocorr.get("lags", {})) if autocorr.get("lags") else None

    overlap = overlap_classification(rows_sorted)
    overlap_counts = {}
    for r, v in overlap.items():
        overlap_counts[v["classification"]] = overlap_counts.get(v["classification"], 0) + 1
    overlap_rate = 1.0 - (overlap_counts.get("independent", 0) / n_nominal) if n_nominal else None

    dependence_flag = "HIGH" if (overlap_rate is not None and overlap_rate > 0.5) or \
        (clustering[3] > 0.5) else ("MODERATE" if clustering[10] > 0.3 else "LOW")

    report = {
        "label": label,
        "n_nominal": n_nominal,
        "gaps_bars": {"median": float(np.median(gaps)) if gaps else None,
                      "min": int(min(gaps)) if gaps else None,
                      "max": int(max(gaps)) if gaps else None},
        "clustering_rate_within_k_bars": clustering,
        "n_clusters": len(clusters),
        "largest_cluster": max(cluster_sizes) if cluster_sizes else 0,
        "cluster_size_distribution": sorted(cluster_sizes, reverse=True)[:20],
        "cluster_gap_threshold_bars": 10,
        "outcome_autocorrelation": autocorr,
        "overlap_classification_counts": overlap_counts,
        "overlap_rate": overlap_rate,
        "dependence_flag": dependence_flag,
        "n_effective": {
            "cluster_count_approximation": len(clusters),
            "autocorrelation_based": ess_ac,
            "note": ESS_METHODS_NOTES,
        },
        "per_event_overlap": overlap,
        "per_event_cluster": cluster_of_row,
    }
    return report


if __name__ == "__main__":
    ROOT = r"C:\Users\User\ClaudeWork\MAX"
    PHASE6_DIR = os.path.join(ROOT, "server", "research_scripts", "phase6")
    primary = json.load(open(os.path.join(PHASE6_DIR, "h006_primary_result.json"), encoding="utf-8"))
    events = primary["event_outcomes_summary"]

    rows = [e["_row"] for e in events]
    direction_by_row = {e["_row"]: e["_direction"] for e in events}
    outcome_by_row = {}
    for e in events:
        v = e.get("outcome_1.0")
        if v == "TARGET_FIRST":
            outcome_by_row[e["_row"]] = 1.0
        elif v == "STOP_FIRST":
            outcome_by_row[e["_row"]] = 0.0
        else:
            outcome_by_row[e["_row"]] = None

    report = full_dependence_report(rows, direction_by_row, outcome_by_row)
    out_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "h006_dependence_audit.json")
    json.dump(report, open(out_path, "w", encoding="utf-8"), indent=2, default=str)
    print(json.dumps({k: v for k, v in report.items() if k not in ("per_event_overlap", "per_event_cluster")}, indent=2, default=str))
    print(f"\nwritten: {out_path}")
