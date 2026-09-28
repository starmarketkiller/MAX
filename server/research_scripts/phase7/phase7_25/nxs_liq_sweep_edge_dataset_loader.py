#!/usr/bin/env python3
"""Phase 7.25 - loader condiviso per l'edge validation LIQ_SWEEP. Legge
DIRETTAMENTE liq_sweep_canonical_dataset_v1.json (Phase 7.24, MT5 =
ground truth) - nessuna dipendenza da Python per P&L/exit. Fornisce
anche accesso alla serie M15 GOLD gia' presente nel progetto (usata da
Phase 7.13/7.16 in precedenza) per il visual audit e la path anatomy."""
import json
import os
from datetime import datetime

PHASE725_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(PHASE725_DIR, "..", "..", "..", ".."))
PHASE724_DIR = os.path.join(ROOT, "server", "research_scripts", "phase7", "phase7_24")
CANONICAL_DATASET_PATH = os.path.join(PHASE724_DIR, "liq_sweep_canonical_dataset_v1.json")
M15_CSV_PATH = os.path.join(ROOT, "server", "research_scripts", "nxs_m15_gold_extended.csv")


def _dt(s):
    return datetime.strptime(s, "%Y.%m.%d %H:%M:%S")


def load_all_events():
    with open(CANONICAL_DATASET_PATH, encoding="utf-8") as f:
        doc = json.load(f)
    return doc["payload"]["events"], doc["payload"]


def load_closed_events():
    """I 42 eventi con lifecycle CLOSED - dataset economico primario."""
    events, _ = load_all_events()
    return [e for e in events if e["lifecycle"] == "CLOSED"]


def net_pnl(e):
    return e["actual_pnl"]


def risk_r(e):
    """Distanza SL pianificata in price units (= $ a lotto fisso 0.01 su GOLD)."""
    return abs(e["entry"]["signal_reference_price"] - e["entry"]["planned_sl"])


def net_pnl_in_r(e):
    r = risk_r(e)
    if r <= 0:
        return None
    return net_pnl(e) / r


def entry_time(e):
    return e["entry"]["timestamp"]


def exit_time(e):
    return e["exit"]["timestamp"]


def split_by_direction(events):
    return {"ALL": events, "BUY": [e for e in events if e["direction"] == "BUY"],
           "SELL": [e for e in events if e["direction"] == "SELL"]}


_M15_DF = None


def load_m15_gold():
    """Serie M15 GOLD gia' presente nel progetto (2023-10-02 -> 2026-08-25),
    riusata da Phase 7.13/7.16 in precedenza per analisi diverse - qui
    per visual audit e path anatomy (MFE/MAE). Provenienza non
    ri-accertata in questa fase oltre il controllo di plausibilita' gia'
    fatto in Phase 7.13 (dichiarato, non nascosto)."""
    global _M15_DF
    if _M15_DF is None:
        import pandas as pd
        df = pd.read_csv(M15_CSV_PATH)
        df["time"] = pd.to_datetime(df["time"], format="%Y.%m.%d %H:%M")
        df = df.sort_values("time").reset_index(drop=True)
        _M15_DF = df
    return _M15_DF


def m15_slice(start_dt, end_dt):
    df = load_m15_gold()
    mask = (df["time"] >= start_dt) & (df["time"] <= end_dt)
    return df.loc[mask].reset_index(drop=True)


def m15_coverage_bounds():
    df = load_m15_gold()
    return df["time"].min(), df["time"].max()


def resample_ohlc(df, rule):
    """Resample deterministico M15->TF piu' larga, offset di 1 ora sul
    confine giorno (convenzione empirica gia' stabilita in Phase 7.13:
    685/748=91.6% dei giorni M15 iniziano alle 01:00). '1D' e' tradotto
    in '24h' - una frequenza 'Tick-like' e' richiesta da pandas perche'
    il parametro offset abbia effetto (con '1D' l'offset viene
    silenziosamente ignorato)."""
    if df.empty:
        return df
    if rule == "1D":
        rule = "24h"
    d = df.set_index("time")
    agg = d.resample(rule, offset="1h").agg({"open": "first", "high": "max",
                                             "low": "min", "close": "last"}).dropna()
    return agg.reset_index()
