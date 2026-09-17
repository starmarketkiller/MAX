#!/usr/bin/env python3
"""Phase 5.C - Event layer: 9 famiglie di eventi rilevate sullo stesso
dataset H4/Market State, indipendentemente da qualunque strategia
nominata. Regole dichiarate EX-ANTE (prima di guardare qualunque outcome)
in questo file - vedi vault/01-Trading/_phase4_artifacts/event_registry_schema.md
per le definizioni concettuali; qui la loro operazionalizzazione concreta
v1, congelata per questa fase.

Ogni evento porta: event_id, event_family, timestamp (observation point),
direction, magnitude, detector_provenance (nome+versione), e l'indice di
riga nel Market State Dataset (per il join allo snapshot di stato).

Nessuna feature/soglia e' stata scelta guardando i risultati - sono le
stesse soglie gia' usate/validate altrove nel progetto (es. la finestra
N=20 range e la soglia 1.0xATR di VOLATILITY_BREAKOUT_CONFIRMED, gia'
frozen in Phase 3) o valori tondi dichiarati qui una volta per tutte.
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
OUT_PATH = os.path.join(DATA_DIR, "events_v1.csv")
META_PATH = os.path.join(DATA_DIR, "events_v1.meta.json")

# ---- soglie EX-ANTE, congelate v1 ----
CFG = {
    "range_n": 20,                    # stessa finestra di VOLATILITY_BREAKOUT_CONFIRMED (FROZEN_SIGNAL_SPEC_V1)
    "range_offset_start": 21, "range_offset_end": 2,  # [i-21, i-2], esclude barra corrente e la precedente immediata
    "vol_expansion_atr_mult": 1.0,     # stessa soglia di VOLATILITY_BREAKOUT_CONFIRMED
    "displacement_atr_mult": 1.5,      # piu' stringente della vol-expansion: corpo direzionale, non solo true range
    "failed_breakout_horizon": 5,      # barre entro cui verificare il fallimento
    "sweep_lookback_n": 20,            # barre precedenti per l'estremo "swept" (esclude barra corrente)
    "reclaim_horizon": 10,
    "retest_horizon": 10,
    "retest_tolerance_atr": 0.15,      # quanto vicino al livello rotto conta come "tocco" di retest
    "compression_percentile_threshold": 20.0,   # sotto il 20esimo percentile = compresso
    "compression_min_bars": 5,         # barre consecutive di compressione richieste prima della release
    "pullback_trend_lookback": 20,     # barre per definire il contesto di trend
    "pullback_retrace_atr_mult": 0.5,  # ritracciamento minimo per contare come pullback
}


def load():
    bars = pd.read_csv(BARS_PATH, parse_dates=["bar_time_utc"]).sort_values("bar_time_utc").reset_index(drop=True)
    state = pd.read_csv(STATE_PATH, parse_dates=["bar_time_utc"]).sort_values("bar_time_utc").reset_index(drop=True)
    assert len(bars) == len(state), "bars/state length mismatch"
    df = bars.merge(state.drop(columns=["close"]), on=["bar_time_utc", "bar_epoch"], how="inner")
    return df.reset_index(drop=True)


def emit(events, family, i, ts, direction, magnitude, obs_point, detector, extra=None, confirmed_at=None):
    rec = {
        "event_id": f"EVT-{family}-{i:07d}",
        "event_family": family,
        "row_index": i,
        "timestamp": ts,
        "direction": direction,
        "magnitude": round(float(magnitude), 6) if magnitude is not None and not (isinstance(magnitude, float) and np.isnan(magnitude)) else None,
        "observation_point": obs_point,
        "detector_provenance": detector,
        "confirmed_at_row_index": confirmed_at,
    }
    if extra:
        rec.update(extra)
    events.append(rec)


def detect(df: pd.DataFrame):
    events = []
    n = len(df)
    close = df["close"].values
    high = df["high"].values
    low = df["low"].values
    open_ = df["open"].values
    atr = df["atr"].values
    comp_pct = df["compression_percentile"].values
    ema_slope = df["ema_slope_atr_norm"].values
    ts = df["bar_time_utc"].astype(str).values

    cfg = CFG
    n_range = cfg["range_n"]
    off_start, off_end = cfg["range_offset_start"], cfg["range_offset_end"]

    breakout_events_by_row = {}  # row -> (direction, level)

    for i in range(n):
        if i < off_start + 1 or np.isnan(atr[i]):
            continue
        tr = max(high[i] - low[i], abs(high[i] - close[i - 1]), abs(low[i] - close[i - 1]))

        # --- VOLATILITY_EXPANSION ---
        if tr > cfg["vol_expansion_atr_mult"] * atr[i]:
            d = 1 if close[i] > open_[i] else (-1 if close[i] < open_[i] else 0)
            emit(events, "VOLATILITY_EXPANSION", i, ts[i], d, tr / atr[i],
                 "bar_close", "vol_expansion_v1")

        # --- DISPLACEMENT ---
        body = close[i] - open_[i]
        if abs(body) > cfg["displacement_atr_mult"] * atr[i]:
            d = 1 if body > 0 else -1
            emit(events, "DISPLACEMENT", i, ts[i], d, abs(body) / atr[i],
                 "bar_close", "displacement_v1")

        # --- BREAKOUT (stessa finestra/soglia di FROZEN_SIGNAL_SPEC_V1) ---
        w_hi = high[i - off_start:i - off_end + 1]
        w_lo = low[i - off_start:i - off_end + 1]
        if len(w_hi) == 0:
            continue
        hh, ll = w_hi.max(), w_lo.min()
        if close[i] > hh:
            emit(events, "BREAKOUT", i, ts[i], 1, (close[i] - hh) / atr[i],
                 "bar_close", "breakout_v1_range20", extra={"level": float(hh)})
            breakout_events_by_row[i] = (1, hh)
        elif close[i] < ll:
            emit(events, "BREAKOUT", i, ts[i], -1, (ll - close[i]) / atr[i],
                 "bar_close", "breakout_v1_range20", extra={"level": float(ll)})
            breakout_events_by_row[i] = (-1, ll)

        # --- SWEEP (mecha su estremo N=20 precedente, esclusa barra corrente) ---
        sw_hi = high[i - cfg["sweep_lookback_n"]:i].max() if i >= cfg["sweep_lookback_n"] else np.nan
        sw_lo = low[i - cfg["sweep_lookback_n"]:i].min() if i >= cfg["sweep_lookback_n"] else np.nan
        if not np.isnan(sw_hi) and high[i] > sw_hi and close[i] < sw_hi:
            emit(events, "SWEEP", i, ts[i], -1, (high[i] - sw_hi) / atr[i],
                 "bar_close", "sweep_v1_range20", extra={"level": float(sw_hi), "swept_side": "HIGH"})
        if not np.isnan(sw_lo) and low[i] < sw_lo and close[i] > sw_lo:
            emit(events, "SWEEP", i, ts[i], 1, (sw_lo - low[i]) / atr[i],
                 "bar_close", "sweep_v1_range20", extra={"level": float(sw_lo), "swept_side": "LOW"})

        # --- COMPRESSION_RELEASE: compressione sostenuta poi vol-expansion ---
        if i >= cfg["compression_min_bars"]:
            window = comp_pct[i - cfg["compression_min_bars"]:i]
            if not np.any(np.isnan(window)) and np.all(window < cfg["compression_percentile_threshold"]):
                if tr > cfg["vol_expansion_atr_mult"] * atr[i]:
                    d = 1 if close[i] > open_[i] else (-1 if close[i] < open_[i] else 0)
                    emit(events, "COMPRESSION_RELEASE", i, ts[i], d, tr / atr[i],
                         "bar_close", "compression_release_v1")

        # --- PULLBACK: trend stabilito + ritracciamento minimo contro trend ---
        if i >= cfg["pullback_trend_lookback"] and not np.isnan(ema_slope[i]):
            trend_window = ema_slope[i - cfg["pullback_trend_lookback"]:i]
            if not np.any(np.isnan(trend_window)):
                trend_sign = 1 if np.mean(trend_window) > 0 else (-1 if np.mean(trend_window) < 0 else 0)
                if trend_sign != 0:
                    extreme = high[i - cfg["pullback_trend_lookback"]:i].max() if trend_sign == 1 \
                        else low[i - cfg["pullback_trend_lookback"]:i].min()
                    retrace = (extreme - close[i]) if trend_sign == 1 else (close[i] - extreme)
                    if retrace > cfg["pullback_retrace_atr_mult"] * atr[i]:
                        emit(events, "PULLBACK", i, ts[i], trend_sign, retrace / atr[i],
                             "bar_close", "pullback_v1", extra={"trend_context": trend_sign})

    # --- FAILED_BREAKOUT: risoluzione ritardata di un BREAKOUT ---
    for i, (d, level) in breakout_events_by_row.items():
        horizon = min(i + cfg["failed_breakout_horizon"], n - 1)
        for j in range(i + 1, horizon + 1):
            if d == 1 and close[j] < level:
                emit(events, "FAILED_BREAKOUT", i, ts[i], d, None,
                     "bar_close_delayed", "failed_breakout_v1", confirmed_at=j)
                break
            if d == -1 and close[j] > level:
                emit(events, "FAILED_BREAKOUT", i, ts[i], d, None,
                     "bar_close_delayed", "failed_breakout_v1", confirmed_at=j)
                break

    # --- RETEST: dopo un BREAKOUT, il prezzo ritocca il livello senza richiuderci sotto/sopra ---
    for i, (d, level) in breakout_events_by_row.items():
        horizon = min(i + cfg["retest_horizon"], n - 1)
        tol = cfg["retest_tolerance_atr"]
        for j in range(i + 1, horizon + 1):
            touched = (low[j] <= level + tol * atr[j] and high[j] >= level - tol * atr[j])
            held = (close[j] > level) if d == 1 else (close[j] < level)
            if touched and held:
                emit(events, "RETEST", i, ts[j], d, None,
                     "bar_close_delayed", "retest_v1", extra={"level": float(level), "breakout_row": i},
                     confirmed_at=j)
                break
            if not held:
                break  # gia' fallito (failed breakout), non e' piu' un retest valido

    # --- RECLAIM: dopo un SWEEP, il prezzo torna a chiudere oltre il livello swept nella direzione opposta allo sweep ---
    sweep_events = [e for e in events if e["event_family"] == "SWEEP"]
    for e in sweep_events:
        i = e["row_index"]
        level = e["level"]
        side = e["swept_side"]
        horizon = min(i + cfg["reclaim_horizon"], n - 1)
        for j in range(i + 1, horizon + 1):
            if side == "HIGH" and close[j] > level:
                emit(events, "RECLAIM", i, ts[j], 1, None,
                     "bar_close_delayed", "reclaim_v1", extra={"level": float(level), "sweep_row": i},
                     confirmed_at=j)
                break
            if side == "LOW" and close[j] < level:
                emit(events, "RECLAIM", i, ts[j], -1, None,
                     "bar_close_delayed", "reclaim_v1", extra={"level": float(level), "sweep_row": i},
                     confirmed_at=j)
                break

    return events


def main():
    df = load()
    events = detect(df)
    ev_df = pd.DataFrame(events)
    ev_df.to_csv(OUT_PATH, index=False)

    counts = ev_df["event_family"].value_counts().to_dict()
    meta = {
        "schema_version": 1,
        "config": CFG,
        "n_events_total": len(ev_df),
        "counts_by_family": counts,
        "source_state": "server/research_scripts/phase5/data/market_state_dataset_v1.csv",
        "detectors_declared_ex_ante": True,
        "built_at": datetime.now(timezone.utc).isoformat(),
        "script": "server/research_scripts/phase5/build_events.py",
    }
    json.dump(meta, open(META_PATH, "w", encoding="utf-8"), indent=2)
    print(json.dumps(meta, indent=2))


if __name__ == "__main__":
    main()
