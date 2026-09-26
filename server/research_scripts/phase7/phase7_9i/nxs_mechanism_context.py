#!/usr/bin/env python3
"""Phase 7.9I - modulo condiviso di caricamento/arricchimento (SOLA
LETTURA del dataset canonico Phase 7.9H, congelato - nessuna modifica).

Ogni feature derivata qui e' calcolata CAUSALMENTE (solo da barre D1
strettamente precedenti o uguali alla barra del segnale) e salvata in
artifact SEPARATI da questo modulo - il dataset canonico
breakout_acc_intended_d1_v1_dataset.json non viene mai toccato.
"""
import csv
import os
import sys
from datetime import datetime

PHASE79I_DIR = os.path.dirname(os.path.abspath(__file__))
PHASE79G_DIR = os.path.abspath(os.path.join(PHASE79I_DIR, "..", "phase7_9g"))
PHASE79H_DIR = os.path.abspath(os.path.join(PHASE79I_DIR, "..", "phase7_9h"))
ROOT = os.path.abspath(os.path.join(PHASE79I_DIR, "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase6_6"))
from canonical_utils import load_json  # noqa: E402

CANONICAL_DATASET_PATH = os.path.join(PHASE79H_DIR, "breakout_acc_intended_d1_v1_dataset.json")
ISOLATED_D1_CSV = os.path.join(PHASE79G_DIR, "raw_data",
                               "nxs_breakoutacc_cadence_diag_prefix_isolated.csv")
D1_BARS_CSV = os.path.join(PHASE79H_DIR, "raw_data", "nxs_d1_gold_phase79h.csv")

PREREGISTERED_HORIZONS_D1 = [1, 3, 5, 10, 20, 40, 60]


def load_canonical_events():
    """Carica il dataset canonico 7.9H COSI' COM'E' - nessuna scrittura."""
    doc = load_json(CANONICAL_DATASET_PATH)
    return doc["payload"], doc["canonical_sha256"]


def load_isolated_d1_rows():
    with open(ISOLATED_D1_CSV, encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))
    for r in rows:
        r["_dt"] = datetime.strptime(r["d1_bar_time"], "%Y.%m.%d")
    rows.sort(key=lambda r: r["_dt"])
    return rows


def load_d1_bars():
    with open(D1_BARS_CSV, encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))
    bars = []
    for r in rows:
        bars.append({
            "time": datetime.strptime(r["time"], "%Y.%m.%d %H:%M"),
            "open": float(r["open"]), "high": float(r["high"]),
            "low": float(r["low"]), "close": float(r["close"]),
        })
    bars.sort(key=lambda b: b["time"])
    return bars


def causal_atr(d1_bars, as_of_date, period=20):
    """ATR-like (media del true range) sulle PERIOD barre D1 strettamente
    precedenti as_of_date - nessun leakage dal futuro."""
    prior = [b for b in d1_bars if b["time"].date() < as_of_date.date()]
    if len(prior) < period + 1:
        return None
    window = prior[-(period + 1):]
    trs = []
    for i in range(1, len(window)):
        h, l, pc = window[i]["high"], window[i]["low"], window[i - 1]["close"]
        tr = max(h - l, abs(h - pc), abs(l - pc))
        trs.append(tr)
    return sum(trs) / len(trs)


def causal_ema(d1_bars, as_of_date, period=100):
    """EMA(period) calcolata SOLO su barre <= as_of_date (inclusa la barra
    del segnale stesso, che e' gia' chiusa quando la strategia valuta -
    iClose(tf,1) legge la barra precedente, non quella corrente)."""
    prior = [b for b in d1_bars if b["time"].date() <= as_of_date.date()]
    if len(prior) < period:
        return None
    closes = [b["close"] for b in prior]
    k = 2.0 / (period + 1)
    ema = sum(closes[:period]) / period
    for c in closes[period:]:
        ema = c * k + ema * (1 - k)
    return ema


def build_feature_table():
    """Costruisce, per ciascuno dei 75 eventi canonici, una riga di
    contesto arricchito - SOLO LETTURA del dataset canonico + dei raw data
    gia' congelati, nessuna nuova esecuzione EA, nessuna modifica al
    dataset canonico."""
    payload, canonical_sha = load_canonical_events()
    events = payload["events"]
    isolated_rows = load_isolated_d1_rows()
    isolated_by_date = {r["d1_bar_time"]: r for r in isolated_rows}
    d1_bars = load_d1_bars()

    # sequenza ordinata di TUTTI i raw-accept (per direzione) sull'intera storia D1
    # isolata - serve per "distanza dal precedente breakout" nella STESSA direzione,
    # indipendentemente dal fatto che quel precedente abbia poi generato un
    # segnale finale o sia stato bloccato da cooldown/htf.
    raw_accepts_by_dir = {1: [], -1: []}
    for r in isolated_rows:
        if r["raw_dir"] == "1":
            raw_accepts_by_dir[1].append(r["_dt"])
        elif r["raw_dir"] == "-1":
            raw_accepts_by_dir[-1].append(r["_dt"])

    def days_since_previous_raw_accept(direction, this_dt):
        seq = raw_accepts_by_dir[direction]
        prior = [d for d in seq if d < this_dt]
        if not prior:
            return None
        return (this_dt - max(prior)).days

    rows = []
    for e in events:
        date_str = e["d1_bar_date"]
        dt = datetime.strptime(date_str, "%Y.%m.%d")
        iso = isolated_by_date.get(date_str)

        row = {
            "event_id": e["event_id"], "d1_bar_date": date_str, "year": dt.year,
            "direction": e["direction"],
            "direction_label": "BUY" if e["direction"] == 1 else "SELL",
            "population_source": e["population_source"],
            "funnel_terminal_stage": e["funnel_terminal_stage"],
        }

        if iso is not None:
            c1 = float(iso["c1"])
            range_hi = float(iso["range_hi"])
            range_lo = float(iso["range_lo"])
            range_width = range_hi - range_lo
            if e["direction"] == 1:
                breakout_magnitude_price = c1 - range_hi
            else:
                breakout_magnitude_price = range_lo - c1
            row["breakout_close_c1"] = c1
            row["range_hi"] = range_hi
            row["range_lo"] = range_lo
            row["range_width"] = range_width
            row["breakout_magnitude_price_units"] = breakout_magnitude_price
            row["breakout_magnitude_pct_of_range"] = (
                breakout_magnitude_price / range_width if range_width > 0 else None)
        else:
            row["breakout_close_c1"] = None
            row["range_hi"] = None
            row["range_lo"] = None
            row["range_width"] = None
            row["breakout_magnitude_price_units"] = None
            row["breakout_magnitude_pct_of_range"] = None
            row["_upstream_row_missing"] = True

        atr20 = causal_atr(d1_bars, dt, period=20)
        row["causal_atr20_d1_price_units"] = atr20
        if atr20 and row["breakout_magnitude_price_units"] is not None:
            row["breakout_magnitude_in_atr_units"] = row["breakout_magnitude_price_units"] / atr20
        else:
            row["breakout_magnitude_in_atr_units"] = None

        ema100 = causal_ema(d1_bars, dt, period=100)
        row["causal_ema100_d1"] = ema100
        if ema100 is not None and row["breakout_close_c1"] is not None:
            close_vs_ema = row["breakout_close_c1"] - ema100
            row["htf_proxy_close_minus_ema100"] = close_vs_ema
            row["htf_proxy_trend_aligned"] = (
                (close_vs_ema > 0) == (e["direction"] == 1))
        else:
            row["htf_proxy_close_minus_ema100"] = None
            row["htf_proxy_trend_aligned"] = None

        row["days_since_previous_raw_accept_same_direction"] = days_since_previous_raw_accept(
            e["direction"], dt)

        row["cooldown_stage"] = e.get("cooldown_stage")
        row["htf_filter_stage_vestigial_upstream"] = e.get("htf_filter_stage")

        if e["funnel_terminal_stage"] == "OPENED":
            row["entry_fill_price"] = e["entry_fill_price"]
            row["entry_fill_time"] = e["entry_fill_time"]
            row["realized_pnl"] = e["realized_pnl"]
            row["exit_reason_comment"] = e["exit_reason_comment"]
            row["post_entry_path_anatomy"] = e["post_entry_path_anatomy"]
        else:
            row["entry_fill_price"] = None
            row["entry_fill_time"] = None
            row["realized_pnl"] = None
            row["exit_reason_comment"] = None
            row["post_entry_path_anatomy"] = None

        rows.append(row)

    rows.sort(key=lambda r: r["d1_bar_date"])
    return {
        "source_canonical_dataset_sha256": canonical_sha,
        "source_canonical_dataset_path": "server/research_scripts/phase7/phase7_9h/"
            "breakout_acc_intended_d1_v1_dataset.json",
        "no_canonical_dataset_modification": True,
        "feature_provenance": {
            "breakout_magnitude_*": "da nxs_breakoutacc_cadence_diag_prefix_isolated.csv "
                "(c1/range_hi/range_lo), disponibile per TUTTI i 75 eventi in modo uniforme "
                "(anche BLOCKED/BROKER_REJECT/B-only, che non hanno un fill reale)",
            "causal_atr20_d1_price_units": "media del true range sulle 20 barre D1 "
                "STRETTAMENTE precedenti alla data del segnale - nessun leakage dal futuro",
            "causal_ema100_d1 / htf_proxy_*": "EMA(100) causale (barre <= data segnale) - "
                "proxy NUOVO di contesto HTF, DISTINTO dalla colonna 'htf_ok' vestigiale "
                "dell'upstream (che non corrisponde a codice reale in NXS_Strat_BreakoutAcc, "
                "vedi Phase 7.9H) - qui esplicitamente etichettato come proxy, non come gate "
                "reale della strategia",
            "days_since_previous_raw_accept_same_direction": "distanza in giorni dal "
                "precedente raw-accept (stesso raw_dir) nell'intera serie D1 isolata, "
                "indipendentemente dal fatto che quel precedente abbia poi generato un "
                "segnale finale",
        },
        "rows": rows,
    }


MAX_PATH_WINDOW_D1 = 60


def full_path_curve(d1_bars, entry_time, entry_price, direction, max_h=MAX_PATH_WINDOW_D1):
    """Percorso completo barra-per-barra (favorable/adverse excursion e
    close-to-close return, in unita' di prezzo) per un singolo evento -
    usato sia da Path Anatomy sia da Natural Horizon, cosi' le due analisi
    condividono ESATTAMENTE la stessa fonte/metodo (nessuna doppia
    implementazione che potrebbe divergere)."""
    idx = None
    for i, b in enumerate(d1_bars):
        if b["time"] >= entry_time:
            idx = i
            break
    if idx is None:
        return None
    window = d1_bars[idx:idx + max_h + 1]
    if len(window) < 2:
        return None

    curve = []
    running_favorable = 0.0
    running_adverse = 0.0
    for j, b in enumerate(window[1:], start=1):
        if direction == 1:
            fav = b["high"] - entry_price
            adv = entry_price - b["low"]
            ret = b["close"] - entry_price
        else:
            fav = entry_price - b["low"]
            adv = b["high"] - entry_price
            ret = entry_price - b["close"]
        running_favorable = max(running_favorable, fav)
        running_adverse = max(running_adverse, adv)
        curve.append({
            "bar": j, "favorable_excursion_running_max": round(running_favorable, 5),
            "adverse_excursion_running_max": round(running_adverse, 5),
            "close_to_close_return": round(ret, 5),
        })
    return curve


def counterfactual_path_anatomy(d1_bars, d1_bar_date_str, proxy_entry_price, direction,
                                horizons=PREREGISTERED_HORIZONS_D1, max_h=MAX_PATH_WINDOW_D1):
    """Path anatomy CONTROFATTUALE per eventi mai eseguiti (BLOCKED,
    BROKER_REJECT, B-only) - usa il prezzo di chiusura della barra di
    breakout (c1, gia' disponibile per costruzione per ogni evento) come
    proxy di ingresso, e come timestamp il mezzogiorno dello stesso
    giorno solare per allinearsi ESATTAMENTE alla convenzione usata per
    gli eventi OPENED reali (dove l'ingresso intraday successivo alla
    chiusura fa scattare la ricerca della barra D1 SUCCESSIVA come
    prima barra della finestra) - stessa metodologia, comparabile 1:1,
    MAI trattato come un trade realmente accaduto."""
    from datetime import datetime as _dt
    y, m, d = (int(x) for x in d1_bar_date_str.split("."))
    entry_time = _dt(y, m, d, 12, 0)
    path = compute_path_anatomy_from_curve(d1_bars, entry_time, proxy_entry_price, direction,
                                           horizons=horizons, max_h=max_h)
    return path


def compute_path_anatomy_from_curve(d1_bars, entry_time, entry_price, direction,
                                    horizons=PREREGISTERED_HORIZONS_D1, max_h=MAX_PATH_WINDOW_D1):
    curve = full_path_curve(d1_bars, entry_time, entry_price, direction, max_h=max_h)
    if curve is None:
        return {"status": "UNKNOWN_INSUFFICIENT_FORWARD_BARS"}
    mfe = max((p["favorable_excursion_running_max"] for p in curve), default=0.0)
    mae = max((p["adverse_excursion_running_max"] for p in curve), default=0.0)
    bars_to_mfe = next((p["bar"] for p in curve
                        if p["favorable_excursion_running_max"] == mfe), None)
    bars_to_mae = next((p["bar"] for p in curve
                        if p["adverse_excursion_running_max"] == mae), None)
    horizons_out = {}
    for h in horizons:
        point = next((p for p in curve if p["bar"] == h), None)
        horizons_out[f"fwd_return_{h}d1_price_units"] = (
            point["close_to_close_return"] if point else None)
    return {"status": "OK", "mfe_price_units": round(mfe, 5), "mae_price_units": round(mae, 5),
           "bars_to_mfe_d1": bars_to_mfe, "bars_to_mae_d1": bars_to_mae,
           "horizons": horizons_out}


POPULATIONS = {
    "A_live_observed": lambda r: r["population_source"] == "LIVE_TRACE_GENERATED",
    "B_opened": lambda r: r["funnel_terminal_stage"] == "OPENED",
    "C_b_only_residual": lambda r: r["population_source"] == "OFFLINE_ISOLATED_RECONSTRUCTION_ONLY",
}


def split_populations(rows):
    return {name: [r for r in rows if pred(r)] for name, pred in POPULATIONS.items()}
