#!/usr/bin/env python3
"""Phase 7.9K - Forward Path Correction. Libreria condivisa che
implementa il CONTRATTO TEMPORALE corretto per il percorso post-evento,
sostituendo full_path_curve()/compute_path_anatomy() di Phase 7.9H/
7.9I (che avevano un offset di +1 barra confermato in Phase 7.9J).

CONTRATTO TEMPORALE (vedi anche breakout_acc_temporal_contract_v1.json):

- reference_time = il timestamp usato come ancora (segnale O fill, MAI
  confusi - vedi le due misurazioni separate in questo modulo).
- "barra parziale d'ingresso" = la barra D1 il cui orario di apertura
  precede reference_time. Il suo High/Low puo' contenere prezzo
  ANTECEDENTE a reference_time (se reference_time cade a meta' della
  barra, es. fill intraday) - questa barra NON VIENE MAI USATA per
  calcolare MFE/MAE/forward return: non abbiamo dati intraday
  verificati per l'intero periodo 2019-2026 per isolare la sola
  porzione successiva a reference_time entro quella barra.
- "bar 1" = la PRIMA barra D1 COMPLETA con orario di apertura >=
  reference_time. Per costruzione, l'intero OHLC di questa barra e'
  temporalmente successivo (o coincidente, se reference_time == bar
  open esatto) a reference_time - non puo' MAI contenere un estremo
  precedente al fill/segnale.
- "bar N" = N-esima barra D1 completa a partire da bar 1 (N barre DI
  MERCATO, non N giorni di calendario - la sequenza salta nativamente
  weekend/festivita', perche' d1_bars contiene solo barre realmente
  presenti nel feed).
- Copertura: se al momento del calcolo sono disponibili meno di N
  barre future (evento troppo vicino alla fine dello storico
  disponibile, 2026.08.19), l'orizzonte N e' CENSURATO
  (status=CENSORED_INSUFFICIENT_BARS) - MAI trattato come FAILURE o
  con un valore inventato.

LIMITE DICHIARATO: la porzione della barra d'ingresso successiva al
fill/segnale (se l'ingresso e' intraday) NON e' misurata - il primo
movimento di prezzo catturato da questo modulo e' quello dalla PRIMA
barra D1 completa in poi. Per i 47 eventi OPENED reali, tutti i fill
sono intraday (nessuno esattamente a mezzanotte) - quindi la copertura
comincia sempre dal giorno di calendario SUCCESSIVO al fill/segnale,
mai dal giorno stesso.
"""
import os
import sys
from datetime import datetime

PHASE79K_DIR = os.path.dirname(os.path.abspath(__file__))
PHASE79I_DIR = os.path.abspath(os.path.join(PHASE79K_DIR, "..", "phase7_9i"))
sys.path.insert(0, PHASE79I_DIR)
import nxs_mechanism_context as ctx_v1  # noqa: E402 - riuso load_d1_bars/causal_ema/causal_atr, INVARIATI

load_d1_bars = ctx_v1.load_d1_bars
causal_ema = ctx_v1.causal_ema
causal_atr = ctx_v1.causal_atr
load_canonical_events = ctx_v1.load_canonical_events

PREREGISTERED_HORIZONS_D1 = ctx_v1.PREREGISTERED_HORIZONS_D1  # [1,3,5,10,20,40,60] - INVARIATI
MAX_H = max(PREREGISTERED_HORIZONS_D1)


def find_first_full_bar_index(d1_bars, reference_time):
    """Indice della prima barra D1 con apertura >= reference_time - MAI
    la barra parziale d'ingresso. Ritorna None se reference_time e'
    dopo l'ultima barra disponibile."""
    for i, b in enumerate(d1_bars):
        if b["time"] >= reference_time:
            return i
    return None


def build_forward_curve_v2(d1_bars, reference_time, reference_price, direction, max_h=MAX_H):
    """Percorso forward CORRETTO: bar 1 = window[0] (prima barra D1
    completa), non window[1] come nella versione Phase 7.9H/7.9I
    (offset confermato in Phase 7.9J). Copertura esplicita -
    CENSURATO se meno di max_h barre sono disponibili."""
    idx = find_first_full_bar_index(d1_bars, reference_time)
    if idx is None:
        return {"status": "NO_BARS_AVAILABLE", "coverage_bars": 0, "curve": []}
    window = d1_bars[idx:idx + max_h]
    n = len(window)
    if n == 0:
        return {"status": "NO_BARS_AVAILABLE", "coverage_bars": 0, "curve": []}

    curve = []
    running_favorable = 0.0
    running_adverse = 0.0
    for j, b in enumerate(window, start=1):
        if direction == 1:
            fav = b["high"] - reference_price
            adv = reference_price - b["low"]
            ret = b["close"] - reference_price
        else:
            fav = reference_price - b["low"]
            adv = b["high"] - reference_price
            ret = reference_price - b["close"]
        running_favorable = max(running_favorable, fav)
        running_adverse = max(running_adverse, adv)
        curve.append({
            "bar": j, "favorable_excursion_running_max": round(running_favorable, 5),
            "adverse_excursion_running_max": round(running_adverse, 5),
            "close_to_close_return": round(ret, 5),
        })
    status = "FULL_COVERAGE" if n >= max_h else "CENSORED_INSUFFICIENT_BARS"
    return {"status": status, "coverage_bars": n, "curve": curve}


def path_anatomy_v2(d1_bars, reference_time, reference_price, direction,
                    horizons=PREREGISTERED_HORIZONS_D1, max_h=MAX_H):
    """MFE/MAE/bars_to_mfe/bars_to_mae/forward return, con censura
    esplicita. MFE/MAE sono calcolati sulla copertura EFFETTIVAMENTE
    disponibile (mai finta come se fosse completa) - il campo
    'mfe_mae_coverage_bars' dichiara sempre su quante barre sono stati
    calcolati."""
    fc = build_forward_curve_v2(d1_bars, reference_time, reference_price, direction, max_h=max_h)
    if fc["status"] == "NO_BARS_AVAILABLE":
        return {"status": "NO_BARS_AVAILABLE", "coverage_bars": 0}

    curve = fc["curve"]
    mfe = max((p["favorable_excursion_running_max"] for p in curve), default=0.0)
    mae = max((p["adverse_excursion_running_max"] for p in curve), default=0.0)
    bars_to_mfe = next((p["bar"] for p in curve if p["favorable_excursion_running_max"] == mfe), None)
    bars_to_mae = next((p["bar"] for p in curve if p["adverse_excursion_running_max"] == mae), None)

    horizons_out = {}
    for h in horizons:
        point = next((p for p in curve if p["bar"] == h), None)
        if point is not None:
            horizons_out[f"fwd_return_{h}d1_price_units"] = point["close_to_close_return"]
        else:
            horizons_out[f"fwd_return_{h}d1_price_units"] = None  # CENSURATO, non un valore reale

    return {
        "status": fc["status"], "coverage_bars": fc["coverage_bars"],
        "mfe_mae_coverage_bars": fc["coverage_bars"],
        "mfe_price_units": round(mfe, 5), "mae_price_units": round(mae, 5),
        "bars_to_mfe_d1": bars_to_mfe, "bars_to_mae_d1": bars_to_mae,
        "horizons": horizons_out,
        "horizons_censored": [h for h in horizons if fc["coverage_bars"] < h],
    }


def classify_continuation_failure_v2(path, horizon=60):
    """Continuation/Failure SOLO se l'orizzonte e' pienamente coperto -
    altrimenti UNKNOWN_CENSORED esplicito, mai FAILURE per default."""
    if path["status"] == "NO_BARS_AVAILABLE" or path["coverage_bars"] < horizon:
        return "UNKNOWN_CENSORED"
    fwd = path["horizons"].get(f"fwd_return_{horizon}d1_price_units")
    if fwd is None:
        return "UNKNOWN_CENSORED"
    return "CONTINUATION" if fwd > 0 else "FAILURE"


# ---------------------------------------------------------------------------
# Misurazione A (post-segnale): ancorata al timestamp REALE del segnale (dal
# trace live per i 67 live-observed; timestamp SINTETICO esplicitamente
# etichettato per gli 8 B-only, mai osservato). Prezzo = c1 (chiusura della
# barra precedente, causalmente pulita - vedi Phase 7.9J), UNIFORME per
# tutti i 67+8 - MAI il fill reale, anche per i 47 OPENED (quella e' la
# misurazione B, separata).
# ---------------------------------------------------------------------------

def load_real_signal_timestamps():
    """Timestamp REALE del segnale (stage GENERATED del trace live) per
    tutti i 67 eventi live-observed - MAI un'approssimazione. Fonte:
    postfix_live_ea_trace_events.csv (Phase 7.9G/7.9H, invariato)."""
    import csv
    path = os.path.join(os.path.dirname(PHASE79I_DIR), "phase7_9g", "raw_data",
                        "postfix_live_ea_trace_events.csv")
    with open(path, encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))
    by_date = {}
    for r in rows:
        date_str = r["timestamp"].split(" ")[0]
        by_date[date_str] = r["timestamp"]  # es. "2019.06.05 17:30:00" - REALE
    return by_date


def measurement_a_reference(row, real_signal_timestamps):
    """Ritorna (reference_time, reference_price, timestamp_source) per la
    misurazione A di un evento (qualunque popolazione)."""
    date_str = row["d1_bar_date"]
    real_ts = real_signal_timestamps.get(date_str)
    if real_ts is not None:
        reference_time = datetime.strptime(real_ts, "%Y.%m.%d %H:%M:%S")
        ts_source = "REAL_SIGNAL_TIMESTAMP_FROM_LIVE_TRACE"
    else:
        # SOLO per gli 8 B-only, mai osservati nel trace live - timestamp
        # SINTETICO, MAI da confondere con un tempo di esecuzione osservato.
        y, m, d = (int(x) for x in date_str.split("."))
        reference_time = datetime(y, m, d, 12, 0)
        ts_source = "SYNTHETIC_NOT_OBSERVED_NOON_PLACEHOLDER"
    reference_price = row["breakout_close_c1"]
    return reference_time, reference_price, ts_source


def measurement_b_reference(row):
    """Ritorna (reference_time, reference_price) per la misurazione B
    (post-fill) - SOLO eventi OPENED, con fill reale verificato."""
    if row["funnel_terminal_stage"] != "OPENED":
        return None, None
    reference_time = datetime.strptime(row["entry_fill_time"], "%Y.%m.%d %H:%M:%S")
    reference_price = row["entry_fill_price"]
    return reference_time, reference_price
