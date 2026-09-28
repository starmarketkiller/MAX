#!/usr/bin/env python3
"""Phase 7.26.F - Path Anatomy Engine standardizzato, generalizzato
dalla logica gia' scritta e usata in Phase 7.25
(build_liq_sweep_path_anatomy.py) per essere riutilizzabile da
QUALUNQUE strategia. Sempre separati: SIGNAL-RELATIVE (rispetto al
prezzo di segnale/riferimento) e FILL-RELATIVE (rispetto al prezzo di
fill reale, quando disponibile e diverso dal segnale). Gestisce il
censoring (posizione ancora aperta/orizzonte non raggiunto)."""
from datetime import datetime


class PathAnatomyEvent:
    """Schema normalizzato di input - il chiamante (per-strategia)
    mappa il proprio schema su questo, l'engine non conosce i dettagli
    di nessuna strategia specifica."""

    def __init__(self, event_id, direction, entry_time, exit_time, signal_price,
                fill_price=None, planned_sl=None, planned_tp=None, censored=False,
                censor_reason=None):
        self.event_id = event_id
        self.direction = direction  # "BUY" o "SELL"
        self.entry_time = entry_time  # datetime
        self.exit_time = exit_time  # datetime o None se censored
        self.signal_price = signal_price
        self.fill_price = fill_price if fill_price is not None else signal_price
        self.planned_sl = planned_sl
        self.planned_tp = planned_tp
        self.censored = censored
        self.censor_reason = censor_reason


def _excursions(bars, direction, ref_price):
    """bars: iterabile di dict/Series con 'time','high','low'. Ritorna
    liste parallele (times, favorable, adverse) - running max NON
    ancora applicato qui (fatto dal chiamante per poter fermarsi al
    picco esatto)."""
    times, fav, adv = [], [], []
    for row in bars:
        if direction == "BUY":
            f = row["high"] - ref_price
            a = ref_price - row["low"]
        else:
            f = ref_price - row["low"]
            a = row["high"] - ref_price
        times.append(row["time"])
        fav.append(f)
        adv.append(a)
    return times, fav, adv


def _running_peak(times, values):
    """Ritorna (max_value, time_of_max, time_of_first_positive)."""
    running_max = 0.0
    t_max = None
    t_first_positive = None
    for t, v in zip(times, values):
        if v > running_max:
            running_max = v
            t_max = t
        if t_first_positive is None and v > 0:
            t_first_positive = t
    return running_max, t_max, t_first_positive


def compute_path_metrics(event: PathAnatomyEvent, bars_between_entry_and_horizon, ref_mode):
    """ref_mode: 'signal' o 'fill' - sceglie signal_price o fill_price
    come riferimento. bars_between_entry_and_horizon: lista di dict
    con 'time','high','low', gia' filtrata dal chiamante (entry->exit,
    o entry->orizzonte fisso se censored)."""
    ref_price = event.signal_price if ref_mode == "signal" else event.fill_price
    if not bars_between_entry_and_horizon:
        return {"data_available": False, "reason": "nessuna barra nella finestra"}

    times, fav, adv = _excursions(bars_between_entry_and_horizon, event.direction, ref_price)
    mfe, t_mfe, t_first_profit = _running_peak(times, fav)
    mae, t_mae, _ = _running_peak(times, adv)

    last_fav = fav[-1]
    result = {
        "data_available": True, "ref_mode": ref_mode, "ref_price": ref_price,
        "n_bars": len(bars_between_entry_and_horizon),
        "mfe_price_units": mfe, "mae_price_units": mae,
        "time_to_mfe": t_mfe, "time_to_mae": t_mae,
        "time_to_first_profit": t_first_profit,
        "recovery_after_mae": (last_fav > 0) if adv and max(adv) > 0 else None,
        "reversal_after_mfe": (mfe - last_fav) if mfe > 0 else None,
    }
    return result


def excursion_before_outcome(event: PathAnatomyEvent, metrics_signal, actual_pnl):
    """Separa esplicitamente 'escursione avversa prima di un winner' e
    'escursione favorevole prima di un loser' - stesso principio gia'
    usato in Phase 7.25, qui generico."""
    if not metrics_signal.get("data_available"):
        return {"applicable": False}
    is_winner = actual_pnl is not None and actual_pnl > 0
    risk_r = abs(event.signal_price - event.planned_sl) if event.planned_sl is not None else None
    if is_winner:
        return {"applicable": True, "role": "adverse_excursion_before_winner",
               "value_price_units": metrics_signal["mae_price_units"],
               "pct_of_planned_r": (metrics_signal["mae_price_units"] / risk_r)
                                  if risk_r else None}
    return {"applicable": True, "role": "favorable_excursion_before_loser",
           "value_price_units": metrics_signal["mfe_price_units"],
           "pct_of_planned_r": (metrics_signal["mfe_price_units"] / risk_r) if risk_r else None}


def fixed_horizon_outcome(event: PathAnatomyEvent, bars_from_entry, horizon_bars):
    """Outcome a orizzonte fisso (N barre dopo l'entry), indipendente
    da SL/TP - utile per confrontare strategie con exit logic diverse
    sullo stesso piano. Ritorna None se censored E l'orizzonte supera
    i dati disponibili."""
    if len(bars_from_entry) < horizon_bars:
        return {"available": False, "reason": "orizzonte oltre i dati disponibili (censored)",
               "censored": True}
    bar = bars_from_entry[horizon_bars - 1]
    ref = event.signal_price
    move = (bar["close"] - ref) if event.direction == "BUY" else (ref - bar["close"])
    return {"available": True, "censored": False, "horizon_bars": horizon_bars,
           "price_units_move": move, "favorable": move > 0}


def build_event_report(event: PathAnatomyEvent, bars_signal_horizon, bars_fill_horizon,
                       actual_pnl, fixed_horizons_bars=()):
    signal_metrics = compute_path_metrics(event, bars_signal_horizon, "signal")
    fill_metrics = (compute_path_metrics(event, bars_fill_horizon, "fill")
                   if event.fill_price != event.signal_price else None)
    report = {
        "event_id": event.event_id, "direction": event.direction, "censored": event.censored,
        "censor_reason": event.censor_reason,
        "signal_relative": signal_metrics,
        "fill_relative": fill_metrics if fill_metrics is not None else
            {"data_available": False, "reason": "fill_price == signal_price per questa strategia "
                                                 "(nessun prezzo di fill separato disponibile)"},
        "excursion_before_outcome": excursion_before_outcome(event, signal_metrics, actual_pnl),
        "fixed_horizon_outcomes": {
            f"h{h}": fixed_horizon_outcome(event, bars_signal_horizon, h)
            for h in fixed_horizons_bars
        },
    }
    return report
