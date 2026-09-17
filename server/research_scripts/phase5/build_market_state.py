#!/usr/bin/env python3
"""Phase 5.B - Market State Dataset v1: feature causali barra-per-barra su
XAUUSD H4 (fonte: server/research_scripts/phase5/data/xauusd_h4_bars.csv,
costruito da tick Dukascopy validati in Phase 4).

REGOLA CAUSALE: ogni feature alla barra i usa SOLO informazione fino alla
chiusura della barra i inclusa. pandas .rolling(N) di default e' trailing
(allineato a destra) - MAI usato con center=True in questo script. Le
feature "prev day/week" usano il giorno/settimana COMPLETI precedenti,
mai il giorno/settimana corrente (che sarebbe non-causale finche' non e'
chiuso). Nessuna feature qui guarda outcome futuri.

Ogni colonna riporta provenance/versione in market_state_dataset.meta.json
(definizione + finestra + data di build), cosi' un futuro cambio di
definizione non si confonde silenziosamente con la v1 usata per l'edge
discovery di questa fase.
"""
import json
import os
from datetime import datetime, timezone

import numpy as np
import pandas as pd

ROOT = r"C:\Users\User\ClaudeWork\MAX"
DATA_DIR = os.path.join(ROOT, "server", "research_scripts", "phase5", "data")
BARS_PATH = os.path.join(DATA_DIR, "xauusd_h4_bars.csv")
OUT_PATH = os.path.join(DATA_DIR, "market_state_dataset_v1.csv")
META_PATH = os.path.join(DATA_DIR, "market_state_dataset_v1.meta.json")

# ---- parametri (dichiarati qui, versione 1, congelati per questa fase) ----
P = {
    "ema_n": 20,
    "efficiency_n": 20,
    "persistence_lookback": 20,
    "atr_n": 14,
    "atr_percentile_window": 252,
    "realized_vol_n": 20,
    "vol_accel_lag": 5,
    "compression_short_n": 10,
    "compression_window": 120,
    "range_n": 20,
    "roc_n": 10,
    "momentum_persistence_lookback": 20,
    "autocorr_window": 60,
    "variance_ratio_k": 4,
    "variance_ratio_window": 60,
}

SESSION_MAP = {
    0: "ASIA", 4: "ASIA_LATE_LONDON_PRE", 8: "LONDON",
    12: "LONDON_NY_OVERLAP", 16: "NY", 20: "NY_LATE",
}


def wilder_atr(high, low, close, n):
    prev_close = close.shift(1)
    tr = pd.concat([
        (high - low).abs(),
        (high - prev_close).abs(),
        (low - prev_close).abs(),
    ], axis=1).max(axis=1)
    # Wilder smoothing == EMA with alpha=1/n (causale, trailing)
    return tr.ewm(alpha=1 / n, adjust=False, min_periods=n).mean()


def rolling_percentile_rank(s: pd.Series, window: int) -> pd.Series:
    """Percentile (0-100) del valore corrente dentro la propria finestra
    trailing di 'window' barre (valore corrente incluso) - causale."""
    def _rank(x):
        return (x <= x[-1]).sum() / len(x) * 100.0
    return s.rolling(window, min_periods=max(10, window // 4)).apply(_rank, raw=True)


def rolling_autocorr_lag1(returns: pd.Series, window: int) -> pd.Series:
    def _ac(x):
        a, b = x[:-1], x[1:]
        if np.std(a) == 0 or np.std(b) == 0:
            return np.nan
        return np.corrcoef(a, b)[0, 1]
    return returns.rolling(window, min_periods=max(20, window // 2)).apply(_ac, raw=True)


def build():
    df = pd.read_csv(BARS_PATH, parse_dates=["bar_time_utc"])
    df = df.sort_values("bar_time_utc").reset_index(drop=True)
    df["date"] = df["bar_time_utc"].dt.date
    df["iso_year"] = df["bar_time_utc"].dt.isocalendar().year
    df["iso_week"] = df["bar_time_utc"].dt.isocalendar().week

    close, high, low, open_ = df["close"], df["high"], df["low"], df["open"]
    ret1 = close.pct_change()
    log_ret1 = np.log(close / close.shift(1))

    out = pd.DataFrame(index=df.index)
    out["bar_time_utc"] = df["bar_time_utc"]
    out["bar_epoch"] = df["bar_epoch"]
    out["close"] = close

    # --- ATR (serve come normalizzatore per molte altre feature) ---
    atr = wilder_atr(high, low, close, P["atr_n"])
    out["atr"] = atr

    # --- Trend ---
    out["return_direction"] = np.sign(ret1)
    ema = close.ewm(span=P["ema_n"], adjust=False, min_periods=P["ema_n"]).mean()
    out["ema_slope_raw"] = ema.diff()
    out["ema_slope_atr_norm"] = out["ema_slope_raw"] / atr
    n_eff = P["efficiency_n"]
    net_change = (close - close.shift(n_eff)).abs()
    path_sum = close.diff().abs().rolling(n_eff, min_periods=n_eff).sum()
    out["directional_efficiency"] = (net_change / path_sum).replace([np.inf, -np.inf], np.nan)

    def _persist(x):
        # numero di barre consecutive (fino all'ultima) con lo stesso segno di ritorno
        s = np.sign(x)
        if s[-1] == 0 or np.isnan(s[-1]):
            return 0
        cnt = 0
        for v in s[::-1]:
            if v == s[-1]:
                cnt += 1
            else:
                break
        return cnt
    out["trend_persistence_bars"] = ret1.rolling(
        P["persistence_lookback"], min_periods=2).apply(_persist, raw=True)

    # --- Volatility ---
    out["atr_percentile"] = rolling_percentile_rank(atr, P["atr_percentile_window"])
    out["realized_vol"] = log_ret1.rolling(P["realized_vol_n"], min_periods=P["realized_vol_n"]).std()
    out["vol_acceleration"] = atr - atr.shift(P["vol_accel_lag"])
    compression_base = atr.rolling(P["compression_short_n"], min_periods=P["compression_short_n"]).mean()
    out["compression_percentile"] = rolling_percentile_rank(compression_base, P["compression_window"])

    # --- Structure / location ---
    roll_high = high.rolling(P["range_n"], min_periods=P["range_n"]).max()
    roll_low = low.rolling(P["range_n"], min_periods=P["range_n"]).min()
    out["dist_from_rolling_high_atr"] = (close - roll_high) / atr
    out["dist_from_rolling_low_atr"] = (close - roll_low) / atr
    rng = (roll_high - roll_low).replace(0, np.nan)
    out["position_in_rolling_range"] = (close - roll_low) / rng

    daily = df.groupby("date").agg(day_high=("high", "max"), day_low=("low", "min")).reset_index()
    daily["prev_day_high"] = daily["day_high"].shift(1)
    daily["prev_day_low"] = daily["day_low"].shift(1)
    df2 = df.merge(daily[["date", "prev_day_high", "prev_day_low"]], on="date", how="left")
    out["dist_from_prev_day_high_atr"] = (close - df2["prev_day_high"]) / atr
    out["dist_from_prev_day_low_atr"] = (close - df2["prev_day_low"]) / atr

    weekly = df.groupby(["iso_year", "iso_week"]).agg(
        week_high=("high", "max"), week_low=("low", "min")).reset_index()
    weekly["prev_week_high"] = weekly["week_high"].shift(1)
    weekly["prev_week_low"] = weekly["week_low"].shift(1)
    df3 = df.merge(weekly[["iso_year", "iso_week", "prev_week_high", "prev_week_low"]],
                    on=["iso_year", "iso_week"], how="left")
    out["dist_from_prev_week_high_atr"] = (close - df3["prev_week_high"]) / atr
    out["dist_from_prev_week_low_atr"] = (close - df3["prev_week_low"]) / atr

    # --- Momentum ---
    roc = close.pct_change(P["roc_n"])
    out["roc"] = roc
    out["momentum_acceleration"] = roc.diff()

    def _mom_persist(x):
        s = np.sign(x)
        if s[-1] == 0 or np.isnan(s[-1]):
            return 0
        cnt = 0
        for v in s[::-1]:
            if v == s[-1]:
                cnt += 1
            else:
                break
        return cnt
    out["momentum_persistence_bars"] = roc.diff().rolling(
        P["momentum_persistence_lookback"], min_periods=2).apply(_mom_persist, raw=True)

    # --- Statistical behavior ---
    out["lag1_autocorr_rolling"] = rolling_autocorr_lag1(ret1.fillna(0), P["autocorr_window"])

    k = P["variance_ratio_k"]
    ret_k = close.pct_change(k)
    var_1 = ret1.rolling(P["variance_ratio_window"], min_periods=P["variance_ratio_window"]).var()
    var_k = ret_k.rolling(P["variance_ratio_window"], min_periods=P["variance_ratio_window"]).var()
    out["variance_ratio_proxy"] = var_k / (k * var_1)
    out["mean_reversion_score"] = -out["lag1_autocorr_rolling"]

    # --- Time ---
    out["hour_utc"] = df["bar_time_utc"].dt.hour
    out["session"] = out["hour_utc"].map(SESSION_MAP)
    out["day_of_week"] = df["bar_time_utc"].dt.dayofweek  # 0=Mon .. 6=Sun

    out.to_csv(OUT_PATH, index=False)

    meta = {
        "schema_version": 1,
        "source_bars": "server/research_scripts/phase5/data/xauusd_h4_bars.csv",
        "n_rows": len(out),
        "first_bar": str(out["bar_time_utc"].iloc[0]),
        "last_bar": str(out["bar_time_utc"].iloc[-1]),
        "parameters": P,
        "session_map": SESSION_MAP,
        "causal_guarantees": [
            "all pandas .rolling() calls are trailing (right-aligned), never center=True",
            "prev_day/prev_week high-low use the fully-completed PRIOR day/week only (explicit .shift(1) on the daily/weekly aggregation before merge)",
            "no feature computed from bars after the observation bar",
        ],
        "built_at": datetime.now(timezone.utc).isoformat(),
        "script": "server/research_scripts/phase5/build_market_state.py",
    }
    json.dump(meta, open(META_PATH, "w", encoding="utf-8"), indent=2)
    print(f"rows={len(out)} cols={len(out.columns)}")
    print(f"written: {OUT_PATH}")
    print(f"written: {META_PATH}")
    print("NaN warmup counts (top 10):")
    print(out.isna().sum().sort_values(ascending=False).head(10))


if __name__ == "__main__":
    build()
