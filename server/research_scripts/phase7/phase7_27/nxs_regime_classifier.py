#!/usr/bin/env python3
"""Phase 7.27 - classificazione di regime CAUSALE (usa solo prezzi
FINO alla barra corrente, mai barre future) per il regime matching
richiesto dal task. Trend: pendenza SMA50 trailing. Volatilita': ATR14
trailing, poi bucket in terzili - i BORDI dei terzili sono calcolati
sull'intera distribuzione del dataset (limite dichiarato: i bordi non
sono causali punto-per-punto, ma il VALORE di ATR14 usato per
classificare ogni barra lo e' - stessa convenzione di uno z-score
globale, non leakage sul prezzo futuro). Anno = regime calendario
banale. Sessione: NON_APPLICABILE (serie D1, nessun concetto di
sessione infra-day)."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from nxs_gold_d1_loader import load_d1  # noqa: E402

SMA_WINDOW = 50
ATR_WINDOW = 14
HTF_SMA_WINDOW = 200


def _true_range(df):
    prev_close = df["close"].shift(1)
    tr = (df[["high", "low"]].assign(pc=prev_close)
         .apply(lambda r: max(r["high"] - r["low"], abs(r["high"] - r["pc"]), abs(r["low"] - r["pc"]))
                if r["pc"] == r["pc"] else r["high"] - r["low"], axis=1))
    return tr


_REGIME_DF = None


def build_regime_table():
    """Ritorna un DataFrame indicizzato come load_d1() con colonne
    aggiuntive: sma50, sma50_slope (UP/DOWN/FLAT), atr14,
    vol_tercile (LOW/MED/HIGH), year, price_above_htf_sma200 (bool)."""
    global _REGIME_DF
    if _REGIME_DF is not None:
        return _REGIME_DF
    df = load_d1().copy()
    df["sma50"] = df["close"].rolling(SMA_WINDOW).mean()
    df["sma50_prev"] = df["sma50"].shift(5)
    df["sma50_slope"] = "UNKNOWN"
    df.loc[df["sma50"] > df["sma50_prev"] * 1.001, "sma50_slope"] = "UP"
    df.loc[df["sma50"] < df["sma50_prev"] * 0.999, "sma50_slope"] = "DOWN"
    df.loc[(df["sma50_slope"] == "UNKNOWN") & df["sma50_prev"].notna(), "sma50_slope"] = "FLAT"

    tr = _true_range(df)
    df["atr14"] = tr.rolling(ATR_WINDOW).mean()
    valid_atr = df["atr14"].dropna()
    q1, q2 = valid_atr.quantile([1 / 3, 2 / 3])
    df["vol_tercile"] = "UNKNOWN"
    df.loc[df["atr14"] <= q1, "vol_tercile"] = "LOW"
    df.loc[(df["atr14"] > q1) & (df["atr14"] <= q2), "vol_tercile"] = "MED"
    df.loc[df["atr14"] > q2, "vol_tercile"] = "HIGH"

    df["year"] = df["time"].dt.year
    df["htf_sma200"] = df["close"].rolling(HTF_SMA_WINDOW).mean()
    df["price_above_htf_sma200"] = df["close"] > df["htf_sma200"]

    _REGIME_DF = df
    return df


def regime_for_index(idx):
    df = build_regime_table()
    row = df.iloc[idx]
    return {
        "trend": row["sma50_slope"] if row["sma50_slope"] != "UNKNOWN" else None,
        "vol_tercile": row["vol_tercile"] if row["vol_tercile"] != "UNKNOWN" else None,
        "year": int(row["year"]),
        "price_above_htf_sma200": bool(row["price_above_htf_sma200"]) if row["price_above_htf_sma200"] == row["price_above_htf_sma200"] else None,
        "session": "NOT_APPLICABLE_D1_SERIES",
    }


def regime_bucket_key(regime):
    """Chiave di stratificazione per il regime matching - trend + vol_tercile
    (year escluso dalla chiave di matching stretto: troppo pochi bar per
    anno in alcune combinazioni - riportato separatamente come covariata
    descrittiva, non come vincolo di matching)."""
    return (regime["trend"], regime["vol_tercile"])
