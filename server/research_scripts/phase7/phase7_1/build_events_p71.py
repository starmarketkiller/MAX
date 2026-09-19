#!/usr/bin/env python3
"""Phase 7.1 - COPIA VERBATIM (zero semantic drift) di
server/research_scripts/phase5/build_events.py, applicata al nuovo
periodo. Stesso identico CFG dict, stesse funzioni di detection - solo i
path di I/O sono cambiati (stesso pattern di phase6/build_events_holdout.py).

Tutte e 9 le famiglie vengono rilevate (detector non modificato), ma
questa fase analizza SOLO RECLAIM (event_family_FROZEN in
phase7_1_frozen_spec_v1.json) - le altre famiglie restano nel file di
output ma non vengono usate per calcolare alcun effetto in questa run.
"""
import json
import os
from datetime import datetime, timezone

import numpy as np
import pandas as pd

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", ".."))
DATA_DIR = os.path.join(ROOT, "server", "research_scripts", "phase7", "phase7_1", "data")
BARS_PATH = os.path.join(DATA_DIR, "xauusd_h4_bars_p71.csv")
STATE_PATH = os.path.join(DATA_DIR, "market_state_dataset_p71.csv")
OUT_PATH = os.path.join(DATA_DIR, "events_p71.csv")
META_PATH = os.path.join(DATA_DIR, "events_p71.meta.json")

CFG = {
    "range_n": 20,
    "range_offset_start": 21, "range_offset_end": 2,
    "vol_expansion_atr_mult": 1.0,
    "displacement_atr_mult": 1.5,
    "failed_breakout_horizon": 5,
    "sweep_lookback_n": 20,
    "reclaim_horizon": 10,
    "retest_horizon": 10,
    "retest_tolerance_atr": 0.15,
    "compression_percentile_threshold": 20.0,
    "compression_min_bars": 5,
    "pullback_trend_lookback": 20,
    "pullback_retrace_atr_mult": 0.5,
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
    off_start, off_end = cfg["range_offset_start"], cfg["range_offset_end"]

    breakout_events_by_row = {}

    for i in range(n):
        if i < off_start + 1 or np.isnan(atr[i]):
            continue
        tr = max(high[i] - low[i], abs(high[i] - close[i - 1]), abs(low[i] - close[i - 1]))

        if tr > cfg["vol_expansion_atr_mult"] * atr[i]:
            d = 1 if close[i] > open_[i] else (-1 if close[i] < open_[i] else 0)
            emit(events, "VOLATILITY_EXPANSION", i, ts[i], d, tr / atr[i], "bar_close", "vol_expansion_v1")

        body = close[i] - open_[i]
        if abs(body) > cfg["displacement_atr_mult"] * atr[i]:
            d = 1 if body > 0 else -1
            emit(events, "DISPLACEMENT", i, ts[i], d, abs(body) / atr[i], "bar_close", "displacement_v1")

        w_hi = high[i - off_start:i - off_end + 1]
        w_lo = low[i - off_start:i - off_end + 1]
        if len(w_hi) == 0:
            continue
        hh, ll = w_hi.max(), w_lo.min()
        if close[i] > hh:
            emit(events, "BREAKOUT", i, ts[i], 1, (close[i] - hh) / atr[i], "bar_close", "breakout_v1_range20", extra={"level": float(hh)})
            breakout_events_by_row[i] = (1, hh)
        elif close[i] < ll:
            emit(events, "BREAKOUT", i, ts[i], -1, (ll - close[i]) / atr[i], "bar_close", "breakout_v1_range20", extra={"level": float(ll)})
            breakout_events_by_row[i] = (-1, ll)

        sw_hi = high[i - cfg["sweep_lookback_n"]:i].max() if i >= cfg["sweep_lookback_n"] else np.nan
        sw_lo = low[i - cfg["sweep_lookback_n"]:i].min() if i >= cfg["sweep_lookback_n"] else np.nan
        if not np.isnan(sw_hi) and high[i] > sw_hi and close[i] < sw_hi:
            emit(events, "SWEEP", i, ts[i], -1, (high[i] - sw_hi) / atr[i], "bar_close", "sweep_v1_range20", extra={"level": float(sw_hi), "swept_side": "HIGH"})
        if not np.isnan(sw_lo) and low[i] < sw_lo and close[i] > sw_lo:
            emit(events, "SWEEP", i, ts[i], 1, (sw_lo - low[i]) / atr[i], "bar_close", "sweep_v1_range20", extra={"level": float(sw_lo), "swept_side": "LOW"})

        if i >= cfg["compression_min_bars"]:
            window = comp_pct[i - cfg["compression_min_bars"]:i]
            if not np.any(np.isnan(window)) and np.all(window < cfg["compression_percentile_threshold"]):
                if tr > cfg["vol_expansion_atr_mult"] * atr[i]:
                    d = 1 if close[i] > open_[i] else (-1 if close[i] < open_[i] else 0)
                    emit(events, "COMPRESSION_RELEASE", i, ts[i], d, tr / atr[i], "bar_close", "compression_release_v1")

        if i >= cfg["pullback_trend_lookback"] and not np.isnan(ema_slope[i]):
            trend_window = ema_slope[i - cfg["pullback_trend_lookback"]:i]
            if not np.any(np.isnan(trend_window)):
                trend_sign = 1 if np.mean(trend_window) > 0 else (-1 if np.mean(trend_window) < 0 else 0)
                if trend_sign != 0:
                    extreme = high[i - cfg["pullback_trend_lookback"]:i].max() if trend_sign == 1 \
                        else low[i - cfg["pullback_trend_lookback"]:i].min()
                    retrace = (extreme - close[i]) if trend_sign == 1 else (close[i] - extreme)
                    if retrace > cfg["pullback_retrace_atr_mult"] * atr[i]:
                        emit(events, "PULLBACK", i, ts[i], trend_sign, retrace / atr[i], "bar_close", "pullback_v1", extra={"trend_context": trend_sign})

    for i, (d, level) in breakout_events_by_row.items():
        horizon = min(i + cfg["failed_breakout_horizon"], n - 1)
        for j in range(i + 1, horizon + 1):
            if d == 1 and close[j] < level:
                emit(events, "FAILED_BREAKOUT", i, ts[i], d, None, "bar_close_delayed", "failed_breakout_v1", confirmed_at=j)
                break
            if d == -1 and close[j] > level:
                emit(events, "FAILED_BREAKOUT", i, ts[i], d, None, "bar_close_delayed", "failed_breakout_v1", confirmed_at=j)
                break

    for i, (d, level) in breakout_events_by_row.items():
        horizon = min(i + cfg["retest_horizon"], n - 1)
        tol = cfg["retest_tolerance_atr"]
        for j in range(i + 1, horizon + 1):
            touched = (low[j] <= level + tol * atr[j] and high[j] >= level - tol * atr[j])
            held = (close[j] > level) if d == 1 else (close[j] < level)
            if touched and held:
                emit(events, "RETEST", i, ts[j], d, None, "bar_close_delayed", "retest_v1", extra={"level": float(level), "breakout_row": i}, confirmed_at=j)
                break
            if not held:
                break

    sweep_events = [e for e in events if e["event_family"] == "SWEEP"]
    for e in sweep_events:
        i = e["row_index"]
        level = e["level"]
        side = e["swept_side"]
        horizon = min(i + cfg["reclaim_horizon"], n - 1)
        for j in range(i + 1, horizon + 1):
            if side == "HIGH" and close[j] > level:
                emit(events, "RECLAIM", i, ts[j], 1, None, "bar_close_delayed", "reclaim_v1", extra={"level": float(level), "sweep_row": i}, confirmed_at=j)
                break
            if side == "LOW" and close[j] < level:
                emit(events, "RECLAIM", i, ts[j], -1, None, "bar_close_delayed", "reclaim_v1", extra={"level": float(level), "sweep_row": i}, confirmed_at=j)
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
        "source_state": "server/research_scripts/phase7/phase7_1/data/market_state_dataset_p71.csv",
        "detectors_declared_ex_ante": True,
        "built_at": datetime.now(timezone.utc).isoformat(),
        "script": "server/research_scripts/phase7/phase7_1/build_events_p71.py (copia verbatim di server/research_scripts/phase5/build_events.py, solo path I/O diversi, stesso CFG dict)",
    }
    json.dump(meta, open(META_PATH, "w", encoding="utf-8"), indent=2)
    print(json.dumps(meta, indent=2))


if __name__ == "__main__":
    main()
