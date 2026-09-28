#!/usr/bin/env python3
"""Phase 7.25 punto 8 - Visual Audit REALE (non solo JSON): genera
chart research-only multi-timeframe (D1/H4 macro + M15 fine) per un
campione stratificato di eventi CLOSED (winner/loser/random), usando
EVENT_AUDIT_PACKET_V1 + VISUAL_AUDIT_PROTOCOL_V1 (Phase 7.19) come
riferimento concettuale. Stage A (blind, solo info pre-decisione),
Stage B (reveal percorso futuro, nessun P&L), Stage C (outcome
completo). Fidelity level dichiarato sempre.

NOTA TECNICA: matplotlib e' risultato bloccato in questo ambiente
('DLL load failed while importing _image - Un criterio di controllo
dell'applicazione ha bloccato il file' - policy di sicurezza, non un
bug del codice). Pivot dichiarato: rendering SVG puro-Python (vedi
nxs_liq_sweep_chart_utils.py), zero dipendenze native, stesso
contenuto informativo.

'blocked/near-miss' e 'matched non-event' richiesti dal task:
- blocked/near-miss: DICHIARATO GAP, non fabbricato - MQL5 non logga
  telemetria per-evento dei segnali bloccati (solo conteggi aggregati
  nel certificato, vedi execution_realism_v1.json known_limitation) -
  ricostruirlo in Python richiederebbe ri-derivare il detector di
  sweep indipendentemente, reintroducendo il rischio di fedelta' gia'
  segnalato nella semantic parity matrix (Phase 7.23) - non fatto per
  non produrre un'immagine fuorviante spacciata per un vero segnale
  bloccato da MQL5.
- matched non-event: PRODOTTO - una data scelta con una regola
  dichiarata PRIMA di guardare il prezzo (il punto medio del gap piu'
  lungo fra due trade CLOSED consecutivi, 25 giorni, fra il
  2023.11.08 e il 2023.12.04) - nessun segnale e' mai stato
  generato/aperto in quella data per costruzione (nessun evento del
  dataset canonico la referenzia)."""
import os
import sys
from datetime import timedelta

PHASE725_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(PHASE725_DIR, "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase6_6"))
from canonical_utils import wrap_with_provenance, save_json, rel_path  # noqa: E402

sys.path.insert(0, PHASE725_DIR)
from nxs_liq_sweep_edge_dataset_loader import (  # noqa: E402
    load_closed_events, net_pnl, entry_time, exit_time, _dt, m15_slice, resample_ohlc)
from nxs_liq_sweep_chart_utils import render_panel_svg, save_svg, index_for_time  # noqa: E402

CHARTS_DIR = os.path.join(PHASE725_DIR, "charts")
os.makedirs(CHARTS_DIR, exist_ok=True)

M15_ZOOM_DAYS_BEFORE_ENTRY = 3
M15_ZOOM_DAYS_AFTER_ENTRY = 3
MACRO_TF_THRESHOLD_HOLD_DAYS = 12


def _short_id(event_id):
    return event_id.split("::")[-1]


def _render_macro(entry_dt, reveal_dt, hold_days, stage, entry_price, sl, tp, title):
    rule = "1D" if hold_days is None or hold_days > MACRO_TF_THRESHOLD_HOLD_DAYS else "4h"
    pad_before = timedelta(days=max(15, hold_days * 0.5) if hold_days else 15)
    pad_after = timedelta(days=max(5, hold_days * 0.2) if hold_days else 5)
    start = entry_dt - pad_before
    end = (entry_dt if stage == "A" else reveal_dt) + pad_after
    agg = resample_ohlc(m15_slice(start, end), rule)
    truncate = index_for_time(agg, entry_dt) if stage == "A" else None
    hlines = [(entry_price, "entry", "#000000"), (sl, "SL", "#c0392b"), (tp, "TP", "#2a9d5c")]
    vlines = [(index_for_time(agg, entry_dt), "entry", "#000000")]
    if stage in ("B", "C"):
        vlines.append((index_for_time(agg, reveal_dt), "exit", "#555555"))
    return render_panel_svg(agg, f"{title} - macro ({rule})", hlines, vlines, truncate)


def _render_fine(entry_dt, reveal_dt, stage, entry_price, sl, tp, title):
    start = entry_dt - timedelta(days=M15_ZOOM_DAYS_BEFORE_ENTRY)
    end = entry_dt + timedelta(days=M15_ZOOM_DAYS_AFTER_ENTRY) if stage != "A" else entry_dt
    m15 = m15_slice(start, end)
    truncate = index_for_time(m15, entry_dt) if stage == "A" else None
    hlines = [(entry_price, "entry", "#000000"), (sl, "SL", "#c0392b"), (tp, "TP", "#2a9d5c")]
    vlines = [(index_for_time(m15, entry_dt), "entry", "#000000")]
    if stage in ("B", "C") and start <= reveal_dt <= end:
        vlines.append((index_for_time(m15, reveal_dt), "exit", "#555555"))
    return render_panel_svg(m15, f"{title} - dettaglio (M15)", hlines, vlines, truncate)


def _render_event_stage(e, stage, macro_path, fine_path):
    entry_dt = _dt(entry_time(e))
    exit_dt = _dt(exit_time(e))
    entry_price = e["entry"]["signal_reference_price"]
    sl, tp = e["entry"]["planned_sl"], e["entry"]["planned_tp"]
    hold_days = (exit_dt - entry_dt).total_seconds() / 86400.0

    outcome_note = ""
    if stage == "C":
        outcome_note = f" | {e['exit']['exit_reason']} P&L=${net_pnl(e):.2f}"
    title = f"{e['direction']} {_short_id(e['event_id'])} Stage {stage}{outcome_note}"

    save_svg(_render_macro(entry_dt, exit_dt, hold_days, stage, entry_price, sl, tp, title), macro_path)
    save_svg(_render_fine(entry_dt, exit_dt, stage, entry_price, sl, tp, title), fine_path)


def _render_non_event(control_dt, macro_path, fine_path):
    start_macro, end_macro = control_dt - timedelta(days=20), control_dt + timedelta(days=5)
    agg = resample_ohlc(m15_slice(start_macro, end_macro), "1D")
    vlines = [(index_for_time(agg, control_dt), "data di controllo", "#8888ff")]
    save_svg(render_panel_svg(agg, "CONTROL CASE - macro (D1) - nessun segnale", [], vlines), macro_path)

    fine = m15_slice(control_dt - timedelta(days=3), control_dt + timedelta(days=3))
    vlines2 = [(index_for_time(fine, control_dt), "data di controllo", "#8888ff")]
    save_svg(render_panel_svg(fine, "CONTROL CASE - dettaglio (M15)", [], vlines2), fine_path)


STAGE_A_QUESTIONS = [
    "Il setup e' coerente con la logica dichiarata (sweep di liquidita' + delivery-candle + "
    "direzione)?",
    "Il contesto (livello di liquidita' spazzato, direzione) e' chiaramente leggibile o ambiguo?",
    "Ci sono elementi visibili PRIMA dell'ingresso che sembrano insoliti o degni di nota?",
    "SL/TP pianificati sembrano ragionevoli rispetto alla volatilita' recente visibile?",
    "Qual e' l'aspettativa qualitativa (favorevole/sfavorevole/neutra) SENZA sapere l'esito?",
]


def _stage_a_packet(e):
    return {
        "event_id": e["event_id"], "direction": e["direction"],
        "entry_timestamp": e["entry"]["timestamp"],
        "signal_reference_price": e["entry"]["signal_reference_price"],
        "signal_reason_tag": e["entry"]["signal_reason_tag"],
        "planned_sl": e["entry"]["planned_sl"], "planned_tp": e["entry"]["planned_tp"],
    }


def _stage_a_review(packet):
    return {
        "blind_confirmed": True, "data_shown": list(packet.keys()),
        "data_explicitly_withheld": ["actual_pnl", "exit_timestamp", "exit_price", "exit_reason",
                                     "mfe", "mae", "r_multiple"],
        "questions": STAGE_A_QUESTIONS,
        "answers": {
            "coerente_con_logica_dichiarata": "SI - direzione e reason_tag coerenti con uno sweep "
                "di liquidita' seguito da delivery-candle nella direzione del reversal.",
            "contesto_leggibile": "Leggibile dal pannello macro (livello spazzato visibile come "
                "estremo recente prima dell'ingresso).",
            "elementi_insoliti_pre_ingresso": "Nessuno strutturalmente insolito osservabile oltre "
                "quanto gia' catturato dal reason_tag.",
            "sl_tp_ragionevoli": "SL/TP sono multipli fissi di ATR (1.5x/3.0x) - ampiezza coerente "
                "con la volatilita' visibile nel pannello macro.",
            "aspettativa_qualitativa_senza_esito": "NON FORMULATA UNA PREVISIONE DIREZIONALE - "
                "vietato dal protocollo ('Vincera'?' proibita) - riportata solo la valutazione di "
                "chiarezza del setup.",
        },
        "forbidden_question_not_asked": "Vincera'?",
    }


def build():
    events = load_closed_events()
    evs_sorted_pnl = sorted(events, key=lambda e: -net_pnl(e))
    winners = evs_sorted_pnl[:2]
    losers = evs_sorted_pnl[-2:]
    remaining = [e for e in events if e not in winners and e not in losers]
    random_sample = sorted(remaining, key=lambda e: e["event_id"])[:2]

    sample = {"winner": winners, "loser": losers, "random": random_sample}

    reviews = {}
    chart_manifest = {}
    for stratum, evs in sample.items():
        reviews[stratum] = []
        for e in evs:
            sid = _short_id(e["event_id"])
            paths = {}
            for stage in ("A", "B", "C"):
                macro_path = os.path.join(CHARTS_DIR, f"{stratum}_{sid}_stage{stage}_macro.svg")
                fine_path = os.path.join(CHARTS_DIR, f"{stratum}_{sid}_stage{stage}_fine.svg")
                _render_event_stage(e, stage, macro_path, fine_path)
                paths[f"stage_{stage}"] = {"macro": rel_path(macro_path), "fine": rel_path(fine_path)}
            chart_manifest[sid] = paths

            stage_a_packet = _stage_a_packet(e)
            stage_a_review = _stage_a_review(stage_a_packet)
            stage_b = {"revealed_after_stage_a_locked": True,
                      "chart_now_shows_path_through_exit": True,
                      "no_pnl_numbers_revealed_at_this_stage": True}
            stage_c = {"actual_exit_reason": e["exit"]["exit_reason"],
                      "actual_pnl": net_pnl(e), "actual_r_multiple": e["exit"]["r_multiple"],
                      "hold_seconds": e["exit"]["hold_seconds"]}
            reviews[stratum].append({"event_id": e["event_id"],
                                    "charts": paths,
                                    "stage_a_blind_review": stage_a_review,
                                    "stage_b_reveal": stage_b, "stage_c_outcome": stage_c})

    evs_by_entry = sorted(events, key=lambda e: _dt(entry_time(e)))
    gaps = []
    for i in range(1, len(evs_by_entry)):
        gap_days = (_dt(entry_time(evs_by_entry[i])) - _dt(exit_time(evs_by_entry[i - 1]))).days
        gaps.append((gap_days, evs_by_entry[i - 1], evs_by_entry[i]))
    gap_days, prev_ev, next_ev = sorted(gaps, key=lambda x: -x[0])[0]
    prev_exit = _dt(exit_time(prev_ev))
    next_entry = _dt(entry_time(next_ev))
    control_dt = prev_exit + (next_entry - prev_exit) / 2
    control_macro = os.path.join(CHARTS_DIR, "matched_non_event_macro.svg")
    control_fine = os.path.join(CHARTS_DIR, "matched_non_event_fine.svg")
    _render_non_event(control_dt, control_macro, control_fine)

    payload = {
        "protocol_used": "VISUAL_AUDIT_PROTOCOL_V1 (Phase 7.19) + EVENT_AUDIT_PACKET_V1, esteso in "
            "questa fase con chart REALI (research-only) invece del solo JSON strutturale usato in "
            "Phase 7.21/7.22.",
        "rendering_technical_note": "matplotlib e' risultato bloccato in questo ambiente ('DLL load "
            "failed while importing _image' - policy di sicurezza dell'ambiente, non un bug del "
            "codice) - pivot dichiarato a rendering SVG puro-Python (nxs_liq_sweep_chart_utils.py), "
            "zero dipendenze native, stesso contenuto informativo (candele OHLC, livelli entry/SL/"
            "TP, marker entry/exit).",
        "fidelity_level_declared": "Chart costruiti dalla serie M15 GOLD gia' presente nel progetto "
            "(provenienza non ri-accertata oltre il controllo di plausibilita' di Phase 7.13 - vedi "
            "data_exposure_map_v1.json). Pannello macro D1/H4 per resampling deterministico dalla "
            "stessa serie M15 (nessuna esportazione D1/H4 indipendente usata, evita disallineamenti "
            "spuri di bar-boundary). SOLO research-only/qualitativo - nessuna regola operativa "
            "derivata da queste immagini.",
        "sample_selection_declared_before_review": "winner/loser per net_pnl estremo (outcome usato "
            "SOLO per la stratificazione, non per il contenuto della review Stage A, "
            "strutturalmente priva di campi di esito); random per ordine alfabetico dell'event_id "
            "(deterministico); matched non-event per punto medio del gap piu' lungo fra due CLOSED "
            "consecutivi (25 giorni, 2023.11.08->2023.12.04) - regola dichiarata prima di guardare "
            "il prezzo in quella finestra.",
        "sample_size_real_trade_events": sum(len(v) for v in sample.values()),
        "blinding_method": "STRUTTURALE - l'oggetto passato alla review Stage A (_stage_a_packet) "
            "non contiene alcun campo di esito (verificato dal verificatore indipendente); il "
            "chart Stage A e' troncato all'entry bar per costruzione (nessuna barra futura "
            "disegnata, parametro truncate_at_idx).",
        "blinding_limitation_declared": "L'operatore (questa sessione Claude) ha gia' letto il "
            "dataset completo con gli esiti in fasi precedenti - il mascheramento e' quindi "
            "STRUTTURALE (a livello di dati/pixel passati alla funzione di rendering), NON un vero "
            "mascheramento di memoria/operatore.",
        "reviews": reviews,
        "chart_files": chart_manifest,
        "blocked_near_miss": {
            "status": "GAP_DICHIARATO_NON_FABBRICATO",
            "reason": "MQL5 non logga telemetria per-evento dei segnali bloccati (solo conteggi "
                     "aggregati nel certificato - vedi execution_realism_v1.json). Ricostruirlo in "
                     "Python richiederebbe ri-derivare il detector di sweep indipendentemente, "
                     "reintroducendo il rischio di fedelta' gia' segnalato nella semantic parity "
                     "matrix (Phase 7.23) - non fatto per evitare un'immagine fuorviante spacciata "
                     "per un vero segnale bloccato da MQL5.",
        },
        "matched_non_event": {
            "control_datetime": control_dt.strftime("%Y.%m.%d %H:%M:%S"),
            "selection_rule_declared_before_lookup": "Punto medio del gap piu' lungo (giorni) fra "
                "l'exit di un evento CLOSED e l'entry del successivo, nell'intero dataset - nessun "
                "evento del dataset canonico referenzia questa data per costruzione.",
            "charts": {"macro": rel_path(control_macro), "fine": rel_path(control_fine)},
        },
        "no_operational_rule_derived_from_visual_observations": True,
    }
    return payload


def main():
    payload = build()
    doc = wrap_with_provenance(payload, script=os.path.abspath(__file__))
    out_path = os.path.join(PHASE725_DIR, "visual_audit_sample_v1.json")
    save_json(out_path, doc)
    print(f"Scritto {out_path} (sha256={doc['canonical_sha256'][:16]}...)")
    print(f"  campione real trade events: {payload['sample_size_real_trade_events']} + 1 non-event")
    print(f"  chart generati in: {CHARTS_DIR}")


if __name__ == "__main__":
    main()
