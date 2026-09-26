#!/usr/bin/env python3
"""Phase 7.13 punto 4 (preparazione dati) - costruisce una serie
multi-TF (M15/M30/H1/H4/D1) AUTO-CONSISTENTE derivando OGNI timeframe
per resampling deterministico dalla STESSA serie M15 di base, invece di
usare esportazioni D1/H4 indipendenti del broker (che avrebbero
convenzioni di bar-boundary potenzialmente diverse, introducendo
disallineamenti spuri NON legati al meccanismo sotto diagnosi).

FONTE: server/research_scripts/nxs_m15_gold_extended.csv - file GIA'
presente nel working tree PRIMA di questa fase (non generato qui, non
ri-verificato con un secondo export indipendente in questa sessione).
Formato e range di prezzo coerenti con le altre esportazioni MT5
XAUUSD del progetto (es. nxs_h4_gold_29-08.csv, stesso ordine di
grandezza di prezzo nello stesso periodo). Provenienza NON accertata
oltre questo controllo di plausibilita' - dichiarato come limite.

SCOPO E LIMITE DI PERIODO: copre 2023-10-02 -> 2026-08-25 (~2.9 anni).
Questo NON e' la storia completa 2019-2026 usata altrove nel progetto
per BREAKOUT_ACC - e' un periodo piu' corto ma REALE e internamente
consistente, sufficiente per (a) quantificare la frequenza del
meccanismo di contaminazione nel periodo studiato e (b) dimostrare
casi reali end-to-end nella timeline di stato. Non e' una campagna di
backtest e non e' usato per alcuna stima di redditivita'.

CONVENZIONE DI CONFINE GIORNO/BARRA: dedotta empiricamente dalla
cadenza della serie M15 (685/748 = 91.6% dei giorni iniziano alle
01:00) - D1 e H4 sono allineati a un confine spostato di 1 ora
(01:00, 05:00, 09:00, ...) rispetto alla mezzanotte. M30/H1 non
richiedono lo spostamento (i confini orari non dipendono da un offset
di un'ora esatta) ma lo applichiamo comunque per uniformita' - risultato
identico.
"""
import os
import sys

import pandas as pd

PHASE713_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(PHASE713_DIR, "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase6_6"))
from canonical_utils import wrap_with_provenance, save_json, file_sha256  # noqa: E402

M15_SOURCE_PATH = os.path.join(ROOT, "server", "research_scripts", "nxs_m15_gold_extended.csv")
DAY_BOUNDARY_OFFSET_HOURS = 1
ATR_PERIOD = 14

TF_RULES = {"M15": "15min", "M30": "30min", "H1": "1h", "H4": "4h", "D1": "1D"}


def _load_m15():
    df = pd.read_csv(M15_SOURCE_PATH, encoding="utf-8-sig")
    df["time"] = pd.to_datetime(df["time"], format="%Y.%m.%d %H:%M")
    df = df.set_index("time").sort_index()
    df = df[["open", "high", "low", "close"]].astype(float)
    return df


def _resample(df, rule):
    shifted = df.copy()
    shifted.index = shifted.index - pd.Timedelta(hours=DAY_BOUNDARY_OFFSET_HOURS)
    o = shifted["open"].resample(rule).first()
    h = shifted["high"].resample(rule).max()
    l = shifted["low"].resample(rule).min()
    c = shifted["close"].resample(rule).last()
    out = pd.concat([o, h, l, c], axis=1)
    out.columns = ["open", "high", "low", "close"]
    out = out.dropna()
    out.index = out.index + pd.Timedelta(hours=DAY_BOUNDARY_OFFSET_HOURS)
    return out


def _wilder_atr(bars, period=ATR_PERIOD):
    """ATR di Wilder (stessa formula di iATR MT5), causale: atr[i] e'
    calcolato usando le barre fino a bars[i] INCLUSA (shift 1 al
    momento della chiusura di bars[i], coerente con g_atr letto subito
    dopo NXS_ActivateTF/NXS_UpdateIndicators sul TF attivo)."""
    n = len(bars)
    atr = [None] * n
    trs = [None] * n
    for i in range(1, n):
        h, l, pc = bars[i]["high"], bars[i]["low"], bars[i - 1]["close"]
        trs[i] = max(h - l, abs(h - pc), abs(l - pc))
    if n <= period:
        return atr
    first = sum(trs[1:period + 1]) / period
    atr[period] = first
    for i in range(period + 1, n):
        atr[i] = (atr[i - 1] * (period - 1) + trs[i]) / period
    return atr


def build():
    df = _load_m15()
    source_hash = file_sha256(M15_SOURCE_PATH)
    tf_bars = {}
    tf_atr = {}
    for tf, rule in TF_RULES.items():
        resampled = _resample(df, rule)
        bars = []
        idx = resampled.index
        for pos in range(len(resampled)):
            row = resampled.iloc[pos]
            open_time = idx[pos]
            close_time = idx[pos + 1] if pos + 1 < len(resampled) else None
            bars.append({
                "open_time": open_time.strftime("%Y-%m-%dT%H:%M:%S"),
                "close_time": close_time.strftime("%Y-%m-%dT%H:%M:%S") if close_time is not None else None,
                "open": float(row["open"]), "high": float(row["high"]),
                "low": float(row["low"]), "close": float(row["close"]),
            })
        if bars and bars[-1]["close_time"] is None:
            bars = bars[:-1]  # scarta l'ultima barra incompleta (nessuna barra successiva nota)
        tf_bars[tf] = bars
        tf_atr[tf] = _wilder_atr(bars)

    payload = {
        "source_csv": os.path.relpath(M15_SOURCE_PATH, ROOT).replace(os.sep, "/"),
        "source_sha256": source_hash,
        "source_row_count": int(len(df)),
        "source_date_range": [df.index.min().strftime("%Y-%m-%dT%H:%M:%S"),
                              df.index.max().strftime("%Y-%m-%dT%H:%M:%S")],
        "source_provenance_note": "file gia' presente nel working tree, non generato in questa "
                                  "fase, non ri-verificato con un secondo export indipendente - "
                                  "plausibile per formato/range di prezzo confrontato con altre "
                                  "esportazioni MT5 XAUUSD del progetto",
        "day_boundary_offset_hours": DAY_BOUNDARY_OFFSET_HOURS,
        "day_boundary_empirical_basis": "685/748 (91.6%) delle giornate della serie M15 iniziano "
                                        "alle 01:00 - confine dedotto empiricamente, non e' "
                                        "necessariamente la convenzione D1/H4 nativa del broker",
        "atr_period": ATR_PERIOD,
        "atr_method": "Wilder (identica formula di iATR MT5), causale (nessun leakage dal futuro)",
        "tf_bar_counts": {tf: len(bars) for tf, bars in tf_bars.items()},
        "tf_bars": tf_bars,
        "tf_atr": tf_atr,
        "not_a_backtest_campaign": True,
        "not_used_for_profitability": True,
    }
    return payload


def main():
    payload = build()
    doc = wrap_with_provenance(payload, script=os.path.abspath(__file__))
    out_path = os.path.join(PHASE713_DIR, "multi_tf_dataset_v1.json")
    save_json(out_path, doc)
    print(f"Scritto {out_path} (sha256={doc['canonical_sha256'][:16]}...)")
    for tf, n in payload["tf_bar_counts"].items():
        print(f"  {tf}: {n} barre")


if __name__ == "__main__":
    main()
