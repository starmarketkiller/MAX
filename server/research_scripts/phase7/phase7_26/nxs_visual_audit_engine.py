#!/usr/bin/env python3
"""Phase 7.26 punto I - Visual Audit Engine riusabile. NON riscrive il
rendering SVG (gia' generico, prende in input DataFrame OHLC qualunque)
scritto in Phase 7.25 - lo IMPORTA da li' (read-only, nessuna modifica
a phase7_25) e generalizza solo la parte che in Phase 7.25 era
specifica di LIQ_SWEEP (nomi di campo, scelta della TF macro). Stage A
(blind, troncato all'entry), Stage B (percorso rivelato, nessun P&L),
Stage C (outcome completo) - fidelity grade sempre dichiarato, NOT_
AVAILABLE esplicito se i dati non permettono un rendering affidabile."""
import os
import sys
from datetime import timedelta

PHASE726_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(PHASE726_DIR, "..", "..", "..", ".."))
PHASE725_DIR = os.path.join(ROOT, "server", "research_scripts", "phase7", "phase7_25")
sys.path.insert(0, PHASE725_DIR)
from nxs_liq_sweep_chart_utils import render_panel_svg, save_svg, index_for_time  # noqa: E402

MACRO_TF_THRESHOLD_HOLD_DAYS = 12
M15_ZOOM_DAYS = 3


def render_event_stages(event, price_series_fn, resample_fn, out_dir, fidelity_note):
    """event: dict generico {event_id, direction, entry_time (datetime),
    exit_time (datetime o None), signal_reference_price, planned_sl,
    planned_tp}. price_series_fn(start,end)->DataFrame M15-o-equivalente
    grezzo. resample_fn(df, rule)->DataFrame OHLC risampionato (stessa
    interfaccia di resample_ohlc, Phase 7.23/25). Ritorna il manifest dei
    file scritti + un fidelity_grade dichiarato.

    Se il prezzo di riferimento manca, o non esiste alcuna barra nella
    finestra richiesta, ritorna data_available=False e NON scrive alcun
    file (mai un chart fuorviante costruito su dati assenti)."""
    os.makedirs(out_dir, exist_ok=True)
    entry_dt, exit_dt = event["entry_time"], event.get("exit_time")
    price = event.get("signal_reference_price")
    if price is None:
        return {"data_available": False, "reason": "signal_reference_price mancante"}

    censored = exit_dt is None
    reveal_dt = exit_dt if not censored else entry_dt
    hold_days = (reveal_dt - entry_dt).total_seconds() / 86400.0 if not censored else None
    sl, tp = event.get("planned_sl"), event.get("planned_tp")

    manifest = {}
    stages = ("A",) if censored else ("A", "B", "C")
    for stage in stages:
        macro_path = os.path.join(out_dir, f"{event['event_id']}_stage{stage}_macro.svg")
        fine_path = os.path.join(out_dir, f"{event['event_id']}_stage{stage}_fine.svg")

        rule = "1D" if hold_days is None or hold_days > MACRO_TF_THRESHOLD_HOLD_DAYS else "4h"
        pad_before = timedelta(days=max(15, (hold_days or 15) * 0.5))
        pad_after = timedelta(days=max(5, (hold_days or 5) * 0.2))
        macro_end = (entry_dt if stage == "A" else reveal_dt) + pad_after
        macro_raw = price_series_fn(entry_dt - pad_before, macro_end)
        if macro_raw.empty:
            return {"data_available": False, "reason": "nessuna barra nella finestra macro richiesta"}
        macro_agg = resample_fn(macro_raw, rule)
        truncate = index_for_time(macro_agg, entry_dt) if stage == "A" else None
        hlines = [(price, "entry", "#000000")]
        if sl is not None:
            hlines.append((sl, "SL", "#c0392b"))
        if tp is not None:
            hlines.append((tp, "TP", "#2a9d5c"))
        vlines = [(index_for_time(macro_agg, entry_dt), "entry", "#000000")]
        if stage in ("B", "C"):
            vlines.append((index_for_time(macro_agg, reveal_dt), "exit", "#555555"))
        outcome_note = f" | {event.get('exit_reason', '')} P&L={event.get('actual_pnl')}" if stage == "C" else ""
        title = f"{event['direction']} {event['event_id']} Stage {stage}{outcome_note} - macro ({rule})"
        save_svg(render_panel_svg(macro_agg, title, hlines, vlines, truncate), macro_path)

        fine_start = entry_dt - timedelta(days=M15_ZOOM_DAYS)
        fine_end = entry_dt + timedelta(days=M15_ZOOM_DAYS) if stage != "A" else entry_dt
        fine_raw = price_series_fn(fine_start, fine_end)
        fine_truncate = index_for_time(fine_raw, entry_dt) if stage == "A" else None
        fine_vlines = [(index_for_time(fine_raw, entry_dt), "entry", "#000000")]
        if stage in ("B", "C") and not censored and fine_start <= reveal_dt <= fine_end:
            fine_vlines.append((index_for_time(fine_raw, reveal_dt), "exit", "#555555"))
        save_svg(render_panel_svg(fine_raw, f"{title} - dettaglio (M15)", hlines, fine_vlines,
                                  fine_truncate), fine_path)

        manifest[f"stage_{stage}"] = {"macro": macro_path, "fine": fine_path}

    return {"data_available": True, "censored": censored, "fidelity_grade": fidelity_note,
           "files": manifest}
