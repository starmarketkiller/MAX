#!/usr/bin/env python3
"""Phase 7.25 punto 9 - outcome/path anatomy (MFE/MAE/time-to-X),
DESCRITTIVO, nessuna nuova regola operativa derivata. Ricostruito dalla
serie M15 GOLD (stessa granularita' di entry_tf=PERIOD_M15 dichiarata
nel certificato Phase 7.23) fra entry e exit di ogni evento CLOSED.

LIMITE DI FEDELTA' DICHIARATO: le barre OHLC M15 approssimano il
percorso intrabar - il MFE/MAE esatto a livello di tick del Tester puo'
differire leggermente da quanto ricostruito qui (slippage/modello
tick del Tester non replicato). Descrittivo, non usato per derivare
regole operative."""
import os
import sys

PHASE725_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(PHASE725_DIR, "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase6_6"))
from canonical_utils import wrap_with_provenance, save_json  # noqa: E402

sys.path.insert(0, PHASE725_DIR)
from nxs_liq_sweep_edge_dataset_loader import load_closed_events, net_pnl, m15_slice, _dt  # noqa: E402

import pandas as pd  # noqa: E402


def _path_metrics_for_event(e):
    entry_dt = _dt(e["entry"]["timestamp"])
    exit_dt = _dt(e["exit"]["timestamp"])
    entry_price = e["entry"]["signal_reference_price"]
    direction = e["direction"]

    bars = m15_slice(entry_dt, exit_dt)
    if bars.empty:
        return {"data_available": False, "reason": "nessuna barra M15 nella finestra "
               "entry->exit (fuori copertura della serie M15 disponibile)."}

    fav_excursions, adv_excursions = [], []
    running_max_fav, running_max_adv = 0.0, 0.0
    t_mfe, t_mae, t_profit = None, None, None
    for _, row in bars.iterrows():
        if direction == "BUY":
            fav = row["high"] - entry_price
            adv = entry_price - row["low"]
        else:
            fav = entry_price - row["low"]
            adv = row["high"] - entry_price
        if fav > running_max_fav:
            running_max_fav = fav
            t_mfe = row["time"]
        if adv > running_max_adv:
            running_max_adv = adv
            t_mae = row["time"]
        if t_profit is None and fav > 0:
            t_profit = row["time"]
        fav_excursions.append(fav)
        adv_excursions.append(adv)

    mfe = max(fav_excursions) if fav_excursions else None
    mae = max(adv_excursions) if adv_excursions else None
    exit_reason = e["exit"]["exit_reason"]
    time_to_stop_seconds = e["exit"]["hold_seconds"] if exit_reason == "sl" else None

    is_winner = net_pnl(e) > 0
    result = {
        "data_available": True,
        "n_m15_bars_in_window": len(bars),
        "mfe_price_units": mfe, "mae_price_units": mae,
        "time_to_mfe": t_mfe.strftime("%Y.%m.%d %H:%M:%S") if t_mfe is not None else None,
        "time_to_mae": t_mae.strftime("%Y.%m.%d %H:%M:%S") if t_mae is not None else None,
        "time_to_mfe_seconds_from_entry": (t_mfe - entry_dt).total_seconds() if t_mfe is not None else None,
        "time_to_mae_seconds_from_entry": (t_mae - entry_dt).total_seconds() if t_mae is not None else None,
        "time_to_first_profit": t_profit.strftime("%Y.%m.%d %H:%M:%S") if t_profit is not None else None,
        "time_to_first_profit_seconds_from_entry": (t_profit - entry_dt).total_seconds()
                                                   if t_profit is not None else None,
        "time_to_stop_seconds": time_to_stop_seconds,
        "exit_reason": exit_reason, "is_winner": is_winner,
    }
    if is_winner:
        result["adverse_excursion_before_winner_price_units"] = mae
        result["adverse_excursion_before_winner_pct_of_planned_r"] = (
            mae / abs(entry_price - e["entry"]["planned_sl"])
            if abs(entry_price - e["entry"]["planned_sl"]) > 0 else None)
    else:
        result["favorable_excursion_before_loser_price_units"] = mfe
        result["reversal_after_favorable_excursion_price_units"] = mfe
        result["favorable_excursion_before_loser_pct_of_planned_r"] = (
            mfe / abs(entry_price - e["entry"]["planned_sl"])
            if abs(entry_price - e["entry"]["planned_sl"]) > 0 else None)
    return result


def build():
    events = load_closed_events()
    per_event = []
    for e in events:
        metrics = _path_metrics_for_event(e)
        per_event.append({"event_id": e["event_id"], "direction": e["direction"],
                         "actual_pnl": net_pnl(e), **metrics})

    available = [p for p in per_event if p["data_available"]]
    winners = [p for p in available if p["is_winner"]]
    losers = [p for p in available if not p["is_winner"]]

    def _avg(key, subset):
        vals = [p[key] for p in subset if p.get(key) is not None]
        return sum(vals) / len(vals) if vals else None

    summary = {
        "n_events_total": len(per_event), "n_events_with_path_data": len(available),
        "n_events_missing_path_data": len(per_event) - len(available),
        "avg_mfe_all": _avg("mfe_price_units", available),
        "avg_mae_all": _avg("mae_price_units", available),
        "avg_time_to_mfe_hours": (_avg("time_to_mfe_seconds_from_entry", available) or 0) / 3600
                                if available else None,
        "avg_time_to_mae_hours": (_avg("time_to_mae_seconds_from_entry", available) or 0) / 3600
                                if available else None,
        "avg_adverse_excursion_before_winner": _avg("adverse_excursion_before_winner_price_units", winners),
        "avg_favorable_excursion_before_loser": _avg("favorable_excursion_before_loser_price_units", losers),
        "n_winners_with_data": len(winners), "n_losers_with_data": len(losers),
    }

    payload = {
        "method": "MFE/MAE ricostruiti dalla serie M15 GOLD (entry_tf dichiarato nel certificato) "
                 "fra entry e exit di ogni evento CLOSED - running max dell'escursione favorevole/"
                 "sfavorevole in price units, direzione-consapevole (BUY: favorevole=high-entry, "
                 "sfavorevole=entry-low; SELL: invertito).",
        "fidelity_limitation_declared": "Le barre OHLC M15 approssimano il percorso intrabar - il "
            "MFE/MAE esatto a livello di tick del Tester puo' differire leggermente (slippage/"
            "modello tick non replicato). Descrittivo, NESSUNA nuova regola operativa derivata da "
            "queste misure in questa fase.",
        "per_event": per_event,
        "summary": summary,
        "descriptive_only_no_new_rule_derived": True,
    }
    return payload


def main():
    payload = build()
    doc = wrap_with_provenance(payload, script=os.path.abspath(__file__))
    out_path = os.path.join(PHASE725_DIR, "path_anatomy_v1.json")
    save_json(out_path, doc)
    print(f"Scritto {out_path} (sha256={doc['canonical_sha256'][:16]}...)")
    print(f"  {payload['summary']}")


if __name__ == "__main__":
    main()
