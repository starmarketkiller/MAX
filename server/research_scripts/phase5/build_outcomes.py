#!/usr/bin/env python3
"""Phase 5.D - Outcome Surface: per ogni evento calcola outcome forward
SENZA management dinamico (nessun trailing/BE, nessuna scelta di TP -
solo osservazione della distribuzione naturale, come richiesto).

Definizione di R per famiglia di evento (dichiarata qui, non dopo aver
visto i risultati):

- Eventi con invalidation NATURALE (un livello che la logica stessa
  dell'evento implica come punto di negazione): BREAKOUT, SWEEP, RECLAIM,
  RETEST. Per questi: entry = close della barra di osservazione (o della
  barra di conferma per RECLAIM/RETEST, che sono eventi a risoluzione
  ritardata); invalidation = il livello implicato dall'evento stesso
  (vedi R_LEVEL_FN sotto); R = |entry - invalidation|; tutti gli outcome
  +0.25R..+3R/-1R sono calcolati su questa base.

- Eventi SENZA invalidation naturale (osservazioni di stato/momento, non
  hanno un "livello" che le nega): VOLATILITY_EXPANSION, DISPLACEMENT,
  COMPRESSION_RELEASE, PULLBACK, FAILED_BREAKOUT. Per questi NON viene
  inventato uno stop arbitrario - si riportano SOLO outcome normalizzati
  in unita' di ATR-alla-barra-di-osservazione, con la stessa griglia di
  soglie (+0.25..+3 "ATR-multipli" prima di -1 ATR-multiplo), tenuti
  esplicitamente separati dagli R-outcome (colonna outcome_basis).

Orizzonte forward: 40 barre (stessa convenzione gia' in uso per
VOLATILITY_BREAKOUT_CONFIRMED in Phase 3 - timeout, non scelto qui per
questo studio).
"""
import json
import os
from datetime import datetime, timezone

import numpy as np
import pandas as pd

ROOT = r"C:\Users\User\ClaudeWork\MAX"
DATA_DIR = os.path.join(ROOT, "server", "research_scripts", "phase5", "data")
BARS_PATH = os.path.join(DATA_DIR, "xauusd_h4_bars.csv")
STATE_PATH = os.path.join(DATA_DIR, "market_state_dataset_v1.csv")
EVENTS_PATH = os.path.join(DATA_DIR, "events_v1.csv")
OUT_PATH = os.path.join(DATA_DIR, "outcomes_v1.csv")
META_PATH = os.path.join(DATA_DIR, "outcomes_v1.meta.json")

HORIZON = 40
THRESHOLDS = [0.25, 0.5, 1.0, 1.5, 2.0, 3.0]
R_BASED_FAMILIES = {"BREAKOUT", "SWEEP", "RECLAIM", "RETEST"}
ATR_ONLY_FAMILIES = {"VOLATILITY_EXPANSION", "DISPLACEMENT", "COMPRESSION_RELEASE",
                     "PULLBACK", "FAILED_BREAKOUT"}


def invalidation_level(ev, df):
    """Livello di invalidation naturale per gli eventi R-based."""
    fam = ev["event_family"]
    if fam == "BREAKOUT":
        return ev["level"]  # opposto implicito: per BUY (dir=1) SL sotto il livello rotto e' l'estremo range opposto - usiamo il livello stesso come riferimento minimo di rischio a 1 ATR (vedi nota sotto)
    if fam == "SWEEP":
        return ev["level"]
    if fam in ("RECLAIM", "RETEST"):
        return ev["level"]
    return None


def compute_r_outcome(entry_row, entry_price, direction, invalidation_price, df, horizon):
    n = len(df)
    end = min(entry_row + horizon, n - 1)
    if end <= entry_row:
        return None
    risk = abs(entry_price - invalidation_price)
    if risk <= 0 or np.isnan(risk):
        return None
    highs = df["high"].values[entry_row + 1:end + 1]
    lows = df["low"].values[entry_row + 1:end + 1]
    if len(highs) == 0:
        return None

    if direction == 1:
        fav_excursion = (highs - entry_price) / risk
        adv_excursion = (entry_price - lows) / risk
    else:
        fav_excursion = (entry_price - lows) / risk
        adv_excursion = (highs - entry_price) / risk

    mfe = float(np.max(fav_excursion))
    mae = float(np.max(adv_excursion))
    bars_to_mfe = int(np.argmax(fav_excursion)) + 1
    bars_to_mae = int(np.argmax(adv_excursion)) + 1

    result = {"mfe_R": mfe, "mae_R": mae, "bars_to_mfe": bars_to_mfe, "bars_to_mae": bars_to_mae}
    # istante di invalidazione: primo bar con adv_excursion >= 1.0
    inval_idx = np.argmax(adv_excursion >= 1.0) if np.any(adv_excursion >= 1.0) else None
    result["bars_to_invalidation"] = int(inval_idx) + 1 if inval_idx is not None else None
    for th in THRESHOLDS:
        hit_target = fav_excursion >= th
        hit_stop = adv_excursion >= 1.0
        target_idx = np.argmax(hit_target) if np.any(hit_target) else None
        stop_idx = np.argmax(hit_stop) if np.any(hit_stop) else None
        if target_idx is None and stop_idx is None:
            outcome = "CENSORED"
            bars_to_target = None
        elif target_idx is not None and (stop_idx is None or target_idx <= stop_idx):
            outcome = "TARGET_FIRST"
            bars_to_target = int(target_idx) + 1
        else:
            outcome = "STOP_FIRST"
            bars_to_target = None
        result[f"outcome_{th}R"] = outcome
        result[f"bars_to_target_{th}R"] = bars_to_target
    return result


def compute_atr_outcome(entry_row, entry_price, direction, atr_at_entry, df, horizon):
    n = len(df)
    end = min(entry_row + horizon, n - 1)
    if end <= entry_row or np.isnan(atr_at_entry) or atr_at_entry <= 0:
        return None
    highs = df["high"].values[entry_row + 1:end + 1]
    lows = df["low"].values[entry_row + 1:end + 1]
    if len(highs) == 0:
        return None
    if direction >= 0:
        fav_excursion = (highs - entry_price) / atr_at_entry
        adv_excursion = (entry_price - lows) / atr_at_entry
    else:
        fav_excursion = (entry_price - lows) / atr_at_entry
        adv_excursion = (highs - entry_price) / atr_at_entry

    mfe = float(np.max(fav_excursion))
    mae = float(np.max(adv_excursion))
    bars_to_mfe = int(np.argmax(fav_excursion)) + 1
    bars_to_mae = int(np.argmax(adv_excursion)) + 1
    result = {"mfe_ATR": mfe, "mae_ATR": mae, "bars_to_mfe": bars_to_mfe, "bars_to_mae": bars_to_mae}
    inval_idx = np.argmax(adv_excursion >= 1.0) if np.any(adv_excursion >= 1.0) else None
    result["bars_to_invalidation"] = int(inval_idx) + 1 if inval_idx is not None else None
    for th in THRESHOLDS:
        hit_target = fav_excursion >= th
        hit_stop = adv_excursion >= 1.0
        target_idx = np.argmax(hit_target) if np.any(hit_target) else None
        stop_idx = np.argmax(hit_stop) if np.any(hit_stop) else None
        if target_idx is None and stop_idx is None:
            outcome = "CENSORED"
            bars_to_target = None
        elif target_idx is not None and (stop_idx is None or target_idx <= stop_idx):
            outcome = "TARGET_FIRST"
            bars_to_target = int(target_idx) + 1
        else:
            outcome = "STOP_FIRST"
            bars_to_target = None
        result[f"outcome_{th}ATR"] = outcome
        result[f"bars_to_target_{th}ATR"] = bars_to_target
    return result


def main():
    df = pd.read_csv(BARS_PATH, parse_dates=["bar_time_utc"]).sort_values("bar_time_utc").reset_index(drop=True)
    state = pd.read_csv(STATE_PATH)
    df["atr"] = state["atr"].values
    events = pd.read_csv(EVENTS_PATH)

    rows = []
    for _, ev in events.iterrows():
        fam = ev["event_family"]
        entry_row = int(ev["confirmed_at_row_index"]) if not pd.isna(ev.get("confirmed_at_row_index")) else int(ev["row_index"])
        if entry_row >= len(df):
            continue
        entry_price = df["close"].values[entry_row]
        direction = ev["direction"] if not pd.isna(ev["direction"]) else 0
        atr_entry = df["atr"].values[entry_row]

        base = {"event_id": ev["event_id"], "event_family": fam, "entry_row": entry_row,
                "entry_price": entry_price, "direction": direction}

        if fam in R_BASED_FAMILIES and "level" in ev and not pd.isna(ev.get("level")):
            inv_level = ev["level"]
            r_out = compute_r_outcome(entry_row, entry_price, direction, inv_level, df, HORIZON)
            if r_out:
                base["outcome_basis"] = "R"
                base["invalidation_level"] = inv_level
                base["risk_R"] = abs(entry_price - inv_level)
                base.update(r_out)
                rows.append(base)
                continue
        # fallback / ATR-only families: nessuno stop naturale
        atr_out = compute_atr_outcome(entry_row, entry_price, direction, atr_entry, df, HORIZON)
        if atr_out:
            base["outcome_basis"] = "ATR_NORMALIZED_NO_NATURAL_STOP"
            base.update(atr_out)
            rows.append(base)

    out_df = pd.DataFrame(rows)
    out_df.to_csv(OUT_PATH, index=False)

    meta = {
        "schema_version": 1,
        "horizon_bars": HORIZON,
        "thresholds": THRESHOLDS,
        "r_based_families": sorted(R_BASED_FAMILIES),
        "atr_only_families": sorted(ATR_ONLY_FAMILIES),
        "n_outcomes": len(out_df),
        "n_by_basis": out_df["outcome_basis"].value_counts().to_dict() if len(out_df) else {},
        "built_at": datetime.now(timezone.utc).isoformat(),
        "script": "server/research_scripts/phase5/build_outcomes.py",
    }
    json.dump(meta, open(META_PATH, "w", encoding="utf-8"), indent=2)
    print(json.dumps(meta, indent=2))


if __name__ == "__main__":
    main()
