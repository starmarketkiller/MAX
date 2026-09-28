#!/usr/bin/env python3
"""Phase 7.27 - loader D1 GOLD condiviso. Fonte:
server/research_scripts/phase7/phase7_9h/raw_data/nxs_d1_gold_phase79h.csv
- gia' usata dal progetto (Phase 7.9H) per costruire il dataset
canonico BREAKOUT_ACC, copre 2019.01.02-2026.08.19 (l'UNICA serie D1
gia' presente nel progetto che copre l'intera finestra di discovery di
tutte e 3 le strategie di questo test, incluso BREAKOUT_ACC che parte
dal 2019). Usata UNIFORMEMENTE per tutte e 3 le strategie e per i
benchmark, cosi' il confronto non dipende da fonti/granularita' diverse
fra strategie."""
import os

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
D1_CSV_PATH = os.path.join(ROOT, "server", "research_scripts", "phase7", "phase7_9h", "raw_data",
                          "nxs_d1_gold_phase79h.csv")

_DF = None


def load_d1():
    global _DF
    if _DF is None:
        import pandas as pd
        df = pd.read_csv(D1_CSV_PATH)
        df["time"] = pd.to_datetime(df["time"], format="%Y.%m.%d %H:%M")
        df = df.sort_values("time").reset_index(drop=True)
        _DF = df
    return _DF


def coverage_bounds():
    df = load_d1()
    return df["time"].min(), df["time"].max()


def bar_index_for_date(dt):
    """Indice della barra D1 il cui 'time' e' il piu' vicino <= dt
    (barra dell'evento) - None se dt e' fuori copertura."""
    df = load_d1()
    if dt < df["time"].iloc[0] or dt > df["time"].iloc[-1]:
        return None
    idx = df[df["time"] <= dt].index
    return int(idx[-1]) if len(idx) else None


def bars_forward(entry_idx, n_bars):
    """Le n_bars barre D1 SUCCESSIVE alla barra di entry (esclusa),
    come lista di dict {time,open,high,low,close} - lista piu' corta se
    i dati finiscono prima (censoring, mai esteso/inventato)."""
    df = load_d1()
    sl = df.iloc[entry_idx + 1: entry_idx + 1 + n_bars]
    return sl.to_dict("records")


def rows_between(start_idx, end_idx):
    df = load_d1()
    return df.iloc[start_idx:end_idx + 1].to_dict("records")
