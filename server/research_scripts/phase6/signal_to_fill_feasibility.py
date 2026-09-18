#!/usr/bin/env python3
"""Phase 6 sec.10 - Signal-to-Fill feasibility study. Eseguito SOLO se
H006 e' risultato PASS (E3). Studio NON-trading: nessuna strategia,
nessun ordine simulato/eseguito - solo misurazione di gap reali usando
i tick veri del periodo di holdout, per decidere se ha senso investire
in una futura E5 (validazione di esecuzione).

Per ogni evento RECLAIM: signal_timestamp (chiusura barra di conferma),
earliest_executable_timestamp (primo tick REALE disponibile dopo quella
chiusura), reference_price (chiusura idealizzata usata nel test),
next tradable bid/ask, gap di tempo, gap di prezzo, distorsione di R
stimata (gap di prezzo / 1 ATR).
"""
import gzip
import csv
import json
import os
from datetime import datetime, timedelta, timezone

import numpy as np
import pandas as pd

ROOT = r"C:\Users\User\ClaudeWork\MAX"
PHASE6_DIR = os.path.join(ROOT, "server", "research_scripts", "phase6")
DATA_DIR = os.path.join(PHASE6_DIR, "data")
DECODED_DIR = os.path.join(PHASE6_DIR, "data_cache_holdout", "decoded")
OUT_JSON = os.path.join(PHASE6_DIR, "signal_to_fill_feasibility_v1.json")

_day_tick_cache = {}


def load_day_ticks(day: datetime):
    key = day.strftime("%Y-%m-%d")
    if key in _day_tick_cache:
        return _day_tick_cache[key]
    path = os.path.join(DECODED_DIR, f"{day.year:04d}", f"{key}.csv.gz")
    if not os.path.exists(path):
        _day_tick_cache[key] = []
        return []
    rows = []
    with gzip.open(path, "rt", newline="", encoding="utf-8") as f:
        r = csv.reader(f)
        next(r, None)
        for row in r:
            if not row:
                continue
            rows.append((int(row[0]), float(row[1]), float(row[2])))
    rows.sort(key=lambda x: x[0])
    _day_tick_cache[key] = rows
    return rows


def next_tick_after(ts_ms: int):
    """Cerca il primo tick con epoch_ms > ts_ms, spazzolando in avanti fino
    a 2 giorni (sufficiente: mai piu' di poche ore di buco atteso su GOLD)."""
    day = datetime.fromtimestamp(ts_ms / 1000, tz=timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    for _ in range(3):
        ticks = load_day_ticks(day)
        for t in ticks:
            if t[0] > ts_ms:
                return t
        day += timedelta(days=1)
    return None


def main():
    primary = json.load(open(os.path.join(PHASE6_DIR, "h006_primary_result.json"), encoding="utf-8"))
    if primary["primary_result"]["VERDICT"] != "PASS":
        print(f"VERDICT={primary['primary_result']['VERDICT']} != PASS - signal-to-fill feasibility NON eseguito (per disegno di questa fase).")
        return None

    df = pd.read_csv(os.path.join(DATA_DIR, "xauusd_h4_bars_holdout.csv"), parse_dates=["bar_time_utc"]).sort_values("bar_time_utc").reset_index(drop=True)
    state = pd.read_csv(os.path.join(DATA_DIR, "market_state_dataset_holdout.csv"))
    atr_col = state["atr"].values

    rows = []
    for ev in primary["event_outcomes_summary"]:
        row_idx = ev["_row"]
        bar_close_dt = df["bar_time_utc"].iloc[row_idx] + pd.Timedelta(hours=4)  # fine barra H4
        reference_price = df["close"].iloc[row_idx]
        atr_at_signal = atr_col[row_idx]
        ts_ms = int(bar_close_dt.timestamp() * 1000)
        nxt = next_tick_after(ts_ms)
        if nxt is None:
            continue
        next_ts_ms, next_bid, next_ask = nxt
        next_mid = (next_bid + next_ask) / 2
        time_gap_s = (next_ts_ms - ts_ms) / 1000.0
        price_gap = next_mid - reference_price
        r_distortion_atr = price_gap / atr_at_signal if atr_at_signal else None
        rows.append({
            "event_row": row_idx,
            "signal_timestamp": bar_close_dt.isoformat(),
            "earliest_executable_timestamp": datetime.fromtimestamp(next_ts_ms / 1000, tz=timezone.utc).isoformat(),
            "reference_price": reference_price,
            "next_tradable_bid": next_bid, "next_tradable_ask": next_ask,
            "time_gap_seconds": time_gap_s,
            "price_gap": price_gap,
            "r_distortion_atr_units": r_distortion_atr,
        })

    if not rows:
        summary = {"n": 0, "note": "nessun tick successivo trovato per nessun evento"}
    else:
        tg = np.array([r["time_gap_seconds"] for r in rows])
        pg = np.array([abs(r["price_gap"]) for r in rows])
        rd = np.array([abs(r["r_distortion_atr_units"]) for r in rows if r["r_distortion_atr_units"] is not None])
        summary = {
            "n": len(rows),
            "time_gap_seconds": {"median": float(np.median(tg)), "p90": float(np.percentile(tg, 90)), "max": float(tg.max())},
            "abs_price_gap": {"median": float(np.median(pg)), "p90": float(np.percentile(pg, 90)), "max": float(pg.max())},
            "abs_r_distortion_atr_units": {"median": float(np.median(rd)), "p90": float(np.percentile(rd, 90)), "max": float(rd.max())} if len(rd) else None,
        }

    out = {
        "schema_version": 1,
        "scope_note": "Studio NON-trading: nessun ordine simulato o eseguito, nessuna strategia. Serve solo a stimare se una futura validazione di esecuzione (E5) e' plausibile.",
        "n_events_analyzed": len(rows),
        "summary": summary,
        "per_event": rows,
        "interpretation_guardrail": (
            "Un time_gap/price_gap PICCOLO qui NON implica che il fenomeno sia eseguibile - "
            "misura solo la distanza fisica minima fra 'segnale confermato' e 'primo tick disponibile', "
            "non tiene conto di spread reale al momento dell'invio, latenza dell'infrastruttura di "
            "esecuzione, o del comportamento di un vero motore MT5/broker. E' un pre-requisito "
            "necessario ma non sufficiente per E5."
        ),
    }
    json.dump(out, open(OUT_JSON, "w", encoding="utf-8"), indent=2, default=str)
    print(json.dumps(summary, indent=2, default=str))
    print(f"\nwritten: {OUT_JSON}")
    return out


if __name__ == "__main__":
    main()
