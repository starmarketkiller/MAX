#!/usr/bin/env python3
"""Phase 7.26 punto H - selezione riusabile di matched non-event e near
-miss (generalizza la logica ad hoc di Phase 7.25). REGOLA STRUTTURALE:
la selezione usa ESCLUSIVAMENTE timestamp di entry/exit (informazione
pre-evento/temporale) - MAI P&L, MFE, MAE, o qualunque campo di esito.
Il verificatore di questa fase (verify_leakage.py) ispeziona staticamente
il codice di questo modulo per confermare che nessuna delle funzioni
sotto accede a un campo di esito - vedi verify_no_outcome_fields_used."""
from datetime import datetime

FORBIDDEN_OUTCOME_KEYS = {"actual_pnl", "net_pnl", "exit_price", "exit_reason", "mfe", "mae",
                         "r_multiple", "win", "loss", "pnl"}


def _dt(s):
    return datetime.strptime(s, "%Y.%m.%d %H:%M:%S") if isinstance(s, str) else s


def select_matched_non_event(events, rule="longest_gap_midpoint"):
    """events: lista di dict con SOLO 'entry_time'/'exit_time' (stringhe)
    - qualunque altro campo presente nel dict e' ignorato per costruzione
    (non letto da questa funzione). Ritorna (control_datetime, rule_note,
    evidence) - evidence e' solo timing, mai esito."""
    if rule != "longest_gap_midpoint":
        raise ValueError(f"regola non supportata: {rule} (solo 'longest_gap_midpoint' implementata "
                        "in questa fase - qualunque nuova regola va dichiarata PRIMA di guardare i "
                        "risultati, non aggiunta per adattarsi a un caso specifico)")

    timed = sorted(({"entry": _dt(e["entry_time"]), "exit": _dt(e["exit_time"])}
                    for e in events if e.get("exit_time") is not None),
                   key=lambda x: x["entry"])
    if len(timed) < 2:
        return None, "campione insufficiente per calcolare un gap (servono >=2 eventi chiusi)", None

    gaps = []
    for i in range(1, len(timed)):
        gap_days = (timed[i]["entry"] - timed[i - 1]["exit"]).days
        gaps.append((gap_days, timed[i - 1]["exit"], timed[i]["entry"]))
    gap_days, prev_exit, next_entry = sorted(gaps, key=lambda x: -x[0])[0]
    control_dt = prev_exit + (next_entry - prev_exit) / 2

    rule_note = (f"punto medio del gap piu' lungo ({gap_days} giorni) fra l'exit di un evento "
               f"chiuso e l'entry del successivo - regola dichiarata PRIMA di guardare il prezzo "
               f"in quella finestra, usa solo timestamp entry/exit.")
    evidence = {"gap_days": gap_days, "prev_exit": prev_exit.strftime("%Y.%m.%d %H:%M:%S"),
               "next_entry": next_entry.strftime("%Y.%m.%d %H:%M:%S")}
    return control_dt, rule_note, evidence


def select_near_miss(blocked_signal_events):
    """blocked_signal_events: lista di segnali bloccati con telemetria
    PER-EVENTO (timestamp, reason) - se vuota/non disponibile, ritorna
    esplicitamente GAP_DICHIARATO_NON_FABBRICATO invece di inventare un
    proxy (stessa decisione presa in Phase 7.25 per LIQ_SWEEP: MQL5 non
    logga telemetria per-evento dei segnali bloccati, solo conteggi
    aggregati nel certificato)."""
    if not blocked_signal_events:
        return {"status": "GAP_DICHIARATO_NON_FABBRICATO",
               "reason": "nessuna telemetria per-evento disponibile per i segnali bloccati - solo "
                        "conteggi aggregati nel certificato MQL5 (limite del logging, non della "
                        "strategia)."}
    first = sorted(blocked_signal_events, key=lambda e: e.get("entry_time") or e.get("time"))[0]
    return {"status": "SELECTED", "event": {"entry_time": first.get("entry_time") or first.get("time")}}


def verify_no_outcome_fields_used():
    """Controllo statico: ispeziona il sorgente di questo stesso modulo
    per confermare che nessuna FORBIDDEN_OUTCOME_KEYS venga referenziata
    come accesso a campo (['key'] o .get('key')) nel corpo delle
    funzioni di selezione. Usato dal verificatore indipendente di
    Phase 7.26, non solo da questo modulo."""
    import inspect
    src = inspect.getsource(select_matched_non_event) + inspect.getsource(select_near_miss)
    violations = [k for k in FORBIDDEN_OUTCOME_KEYS if f"'{k}'" in src or f'"{k}"' in src]
    return violations
