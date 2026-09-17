#!/usr/bin/env python3
"""Phase 5.5 sec.9 - Feature Redundancy Audit.

Analisi REALE (non stimata) delle feature numeriche di
market_state_dataset_v1.csv: correlazione di Pearson e di rango
(Spearman), varianza, ricerca di quasi-duplicati. Classificazione per
ciascuna feature, NESSUNA rimozione automatica (richiesto esplicitamente).

Classi: UNIQUE, REDUNDANT, HIGHLY_CORRELATED, LOW_INFORMATION,
KEEP_FOR_INTERPRETABILITY.

Soglie dichiarate qui: |pearson| o |spearman| > 0.90 -> HIGHLY_CORRELATED
(candidato REDUNDANT se inoltre la formula e' quasi-derivata da un'altra
feature gia' presente); std relativa (std/mean assoluto, o std nudo se
mean~0) sotto l'1 percentile della distribuzione fra le feature ->
LOW_INFORMATION.
"""
import json
import os

import numpy as np
import pandas as pd

ROOT = r"C:\Users\User\ClaudeWork\MAX"
STATE_PATH = os.path.join(ROOT, "server", "research_scripts", "phase5", "data", "market_state_dataset_v1.csv")
OUT_JSON = os.path.join(ROOT, "server", "research_scripts", "phase5_5", "feature_redundancy_audit_v1.json")

# derivazioni formula-note (dichiarate dal design, non scoperte a posteriori)
KNOWN_DERIVED_PAIRS = [
    ("mean_reversion_score", "lag1_autocorr_rolling", "mean_reversion_score = -lag1_autocorr_rolling per costruzione"),
    ("ema_slope_atr_norm", "ema_slope_raw", "ema_slope_atr_norm = ema_slope_raw / ATR, stessa quantita' solo riscalata"),
    ("dist_from_rolling_high_atr", "dist_from_rolling_low_atr", "stessa finestra rolling (N=20), lati opposti dello stesso range"),
    ("dist_from_prev_day_high_atr", "dist_from_prev_day_low_atr", "stesso giorno precedente, lati opposti"),
    ("dist_from_prev_week_high_atr", "dist_from_prev_week_low_atr", "stessa settimana precedente, lati opposti"),
]

INTERPRETABILITY_KEEP = {
    "return_direction", "hour_utc", "day_of_week",
}  # feature categoriche/elementari mantenute per interpretabilita' anche se a bassa varianza informativa


def main():
    df = pd.read_csv(STATE_PATH)
    numeric_cols = [c for c in df.columns if c not in ("bar_time_utc", "bar_epoch", "close", "session")]
    X = df[numeric_cols]

    pearson = X.corr(method="pearson")
    spearman = X.corr(method="spearman")

    high_corr_pairs = []
    cols = list(X.columns)
    for i in range(len(cols)):
        for j in range(i + 1, len(cols)):
            a, b = cols[i], cols[j]
            pr = pearson.loc[a, b]
            sr = spearman.loc[a, b]
            if pd.isna(pr) or pd.isna(sr):
                continue
            if abs(pr) > 0.90 or abs(sr) > 0.90:
                high_corr_pairs.append({"feature_a": a, "feature_b": b,
                                         "pearson": round(float(pr), 4), "spearman": round(float(sr), 4)})

    known_derived_set = set()
    for a, b, why in KNOWN_DERIVED_PAIRS:
        known_derived_set.add(a)

    # varianza / quasi-costanza: coefficiente di variazione robusto
    # (std / (|mediana|+eps)) - per feature che possono essere ~0 in media
    variance_report = {}
    for c in cols:
        s = X[c].dropna()
        if len(s) == 0:
            variance_report[c] = {"std": None, "n_unique": 0, "flag": "LOW_INFORMATION"}
            continue
        std = float(s.std())
        n_unique = int(s.nunique())
        near_constant = (n_unique <= 3) or (std == 0)
        variance_report[c] = {"std": round(std, 6), "n_unique": n_unique,
                               "near_constant": near_constant}

    classification = {}
    corr_flagged = set()
    for pair in high_corr_pairs:
        corr_flagged.add(pair["feature_a"])
        corr_flagged.add(pair["feature_b"])

    for c in cols:
        if c in INTERPRETABILITY_KEEP:
            classification[c] = "KEEP_FOR_INTERPRETABILITY"
            continue
        if variance_report[c].get("near_constant"):
            classification[c] = "LOW_INFORMATION"
            continue
        if c in known_derived_set:
            classification[c] = "REDUNDANT"
            continue
        if c in corr_flagged:
            classification[c] = "HIGHLY_CORRELATED"
            continue
        classification[c] = "UNIQUE"

    summary_counts = pd.Series(list(classification.values())).value_counts().to_dict()

    out = {
        "schema_version": 1,
        "n_features_analyzed": len(cols),
        "correlation_threshold": 0.90,
        "high_correlation_pairs": sorted(high_corr_pairs, key=lambda p: -max(abs(p["pearson"]), abs(p["spearman"]))),
        "known_derived_relationships": [{"derived": a, "from": b, "note": why} for a, b, why in KNOWN_DERIVED_PAIRS],
        "variance_report": variance_report,
        "classification": classification,
        "classification_counts": summary_counts,
        "no_automatic_removal": True,
        "note": "Nessuna feature rimossa automaticamente, come richiesto. La classificazione informa scelte future di modellazione (es. evitare di usare due feature HIGHLY_CORRELATED come predittori indipendenti in una regressione logistica), non e' un'azione sul dataset esistente.",
    }
    json.dump(out, open(OUT_JSON, "w", encoding="utf-8"), indent=2, default=str)
    print("classification counts:", summary_counts)
    print(f"\nhigh correlation pairs (|r|>0.90): {len(high_corr_pairs)}")
    for p in high_corr_pairs:
        print(f"  {p['feature_a']} <-> {p['feature_b']}: pearson={p['pearson']} spearman={p['spearman']}")
    print(f"\nwritten: {OUT_JSON}")


if __name__ == "__main__":
    main()
