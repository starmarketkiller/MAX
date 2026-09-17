#!/usr/bin/env python3
"""Phase 5.5 sec.6 - Market Regime Layer.

Rappresentazione di regime DESCRITTIVA, separata da qualunque strategia
- non e' un segnale di trading, e' un'etichetta di stato osservabile
usata per stratificare/interpretare i risultati (es. nei breakdown
"regime_breakdown" del Probability Engine, sec.G di Phase 5, mai
popolati concretamente finora - questa e' la prima implementazione
reale).

5 stati minimi richiesti: TRENDING, RANGING, HIGH_VOL, LOW_VOL,
TRANSITION. Sono trattati come UN'UNICA variabile categorica (non due
assi ortogonali) con una PRIORITA' DICHIARATA esplicitamente qui,
PRIMA di calcolare qualunque distribuzione:

  1. HIGH_VOL  se atr_percentile > soglia_alta (estremo di volatilita'
     - quando la barra e' in un contesto di volatilita' estrema, questo
     domina la descrizione qualitativa indipendentemente dal trend)
  2. LOW_VOL   se atr_percentile < soglia_bassa
  3. TRANSITION se il trend e' "fresco" (trend_persistence_bars <=
     soglia_transizione) - il regime di trend non e' ancora stabilito
  4. TRENDING  se directional_efficiency > soglia_alta E la
     persistenza di trend supera la soglia di transizione
  5. RANGING   altrimenti (bassa efficienza direzionale, vol normale,
     trend non fresco)

Soglie derivate da QUANTILI (33/66 percentile) calcolati SOLO sulla
finestra di discovery (no leakage dalla validation), stesse soglie
gia' usate nel resto di Phase 5 per coerenza (vol_terc/trend_terc di
edge_discovery.py) piu' una soglia di "freschezza" per TRANSITION
dichiarata qui: trend_persistence_bars <= 2 (una svolta di
direzione avvenuta nelle ultime 1-2 barre - non arbitraria in senso
di "scelta a caso", ma dichiarata qui una volta per tutte, PRIMA di
calcolare la distribuzione dei regimi, e non piu' toccata).

Observation point: chiusura barra corrente (stesse feature causali di
market_state_dataset_v1.csv - nessuna feature futura usata qui).
"""
import json
import os
from datetime import datetime, timezone

import numpy as np
import pandas as pd

ROOT = r"C:\Users\User\ClaudeWork\MAX"
DATA_DIR = os.path.join(ROOT, "server", "research_scripts", "phase5", "data")
STATE_PATH = os.path.join(DATA_DIR, "market_state_dataset_v1.csv")
OUT_CSV = os.path.join(ROOT, "server", "research_scripts", "phase5_5", "regime_layer_v1.csv")
OUT_META = os.path.join(ROOT, "server", "research_scripts", "phase5_5", "regime_schema_v1.json")

SPLIT_IDX = 3366
TRANSITION_FRESHNESS_BARS = 2  # dichiarata qui, non dopo


def main():
    state = pd.read_csv(STATE_PATH, parse_dates=["bar_time_utc"]).sort_values("bar_time_utc").reset_index(drop=True)
    disc = state.iloc[:SPLIT_IDX]

    vol_terc = np.nanpercentile(disc["atr_percentile"].dropna(), [33.33, 66.67])
    eff_terc = np.nanpercentile(disc["directional_efficiency"].dropna(), [33.33, 66.67])

    def classify(row):
        v = row["atr_percentile"]
        e = row["directional_efficiency"]
        p = row["trend_persistence_bars"]
        if pd.isna(v) or pd.isna(e) or pd.isna(p):
            return None
        if v > vol_terc[1]:
            return "HIGH_VOL"
        if v < vol_terc[0]:
            return "LOW_VOL"
        if p <= TRANSITION_FRESHNESS_BARS:
            return "TRANSITION"
        if e > eff_terc[1]:
            return "TRENDING"
        return "RANGING"

    state["regime_v1"] = state.apply(classify, axis=1)

    out = state[["bar_time_utc", "bar_epoch", "regime_v1"]].copy()
    out.to_csv(OUT_CSV, index=False)

    dist_all = state["regime_v1"].value_counts(dropna=False).to_dict()
    dist_disc = state.iloc[:SPLIT_IDX]["regime_v1"].value_counts(dropna=False).to_dict()
    dist_val = state.iloc[SPLIT_IDX:]["regime_v1"].value_counts(dropna=False).to_dict()

    schema = {
        "schema_version": 1,
        "regime_definition": {
            "states": ["HIGH_VOL", "LOW_VOL", "TRANSITION", "TRENDING", "RANGING"],
            "priority_order": ["HIGH_VOL", "LOW_VOL", "TRANSITION", "TRENDING", "RANGING"],
            "priority_rationale": "vol estrema domina la descrizione qualitativa; poi la freschezza del trend (TRANSITION) prima di dichiarare un trend stabilito; infine TRENDING vs RANGING per esclusione",
        },
        "feature_inputs": ["atr_percentile", "directional_efficiency", "trend_persistence_bars"],
        "thresholds": {
            "vol_tercile_33_67": vol_terc.tolist(),
            "directional_efficiency_tercile_33_67": eff_terc.tolist(),
            "transition_freshness_bars_leq": TRANSITION_FRESHNESS_BARS,
            "thresholds_calibration_window": "discovery only, righe [0,{})".format(SPLIT_IDX),
        },
        "observation_point": "bar_close (stesse garanzie causali di market_state_dataset_v1)",
        "is_a_trading_signal": False,
        "intended_use": "stratificazione descrittiva per regime_breakdown nel Probability Engine e per audit di stabilita' di un edge component - MAI come trigger di entrata",
        "distribution_all": dist_all,
        "distribution_discovery": dist_disc,
        "distribution_validation": dist_val,
        "built_at": datetime.now(timezone.utc).isoformat(),
        "script": "server/research_scripts/phase5_5/build_regime_layer.py",
    }
    json.dump(schema, open(OUT_META, "w", encoding="utf-8"), indent=2, default=str)
    print(json.dumps({k: v for k, v in schema.items() if "distribution" in k or k == "thresholds"}, indent=2, default=str))
    print(f"\nwritten: {OUT_CSV}\nwritten: {OUT_META}")


if __name__ == "__main__":
    main()
