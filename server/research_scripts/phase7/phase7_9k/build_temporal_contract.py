#!/usr/bin/env python3
"""Phase 7.9K - Contratto temporale (punto 1 della task). Documento
formale, in forma di artifact dati, delle convenzioni usate per
correggere il difetto di indicizzazione forward confermato in Phase
7.9J. Nessun calcolo qui - solo definizione del contratto, verificata
con numeri reali del dataset."""
import os
import sys
from datetime import datetime

PHASE79K_DIR = os.path.dirname(os.path.abspath(__file__))
PHASE79I_DIR = os.path.abspath(os.path.join(PHASE79K_DIR, "..", "phase7_9i"))
ROOT = os.path.abspath(os.path.join(PHASE79K_DIR, "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase6_6"))
from canonical_utils import save_json, wrap_with_provenance  # noqa: E402

sys.path.insert(0, PHASE79K_DIR)
sys.path.insert(0, PHASE79I_DIR)
import nxs_forward_path_v2 as fp  # noqa: E402
import nxs_mechanism_context as ctx  # noqa: E402


def build():
    d1_bars = fp.load_d1_bars()

    definitions = {
        "signal_timestamp": (
            "Timestamp REALE al quale NXS_Trace_Generated() e' stato emesso nel run "
            "diagnostico live (Phase 7.9G/7.9H) - disponibile per tutti i 67 eventi "
            "live-observed (fonte: postfix_live_ea_trace_events.csv, colonna "
            "'timestamp'). NON disponibile per gli 8 eventi B-only (mai osservati nel "
            "trace live)."
        ),
        "fill_timestamp": (
            "Timestamp REALE del deal di apertura (DEAL_ENTRY_IN), verificato via "
            "HistoryDealGetDouble nel run diagnostico Phase 7.9H "
            "(nxs_diag_deals_export_r003.csv) - disponibile SOLO per i 47 eventi "
            "OPENED. Per tutti i 47 OPENED, signal_timestamp == fill_timestamp "
            "esattamente (verificato) - la strategia invia l'ordine a mercato "
            "immediatamente dopo la generazione del segnale, senza ritardo misurabile "
            "in questo run diagnostico."
        ),
        "bar_open_close_convention": (
            "Le barre D1 (nxs_d1_gold_phase79h.csv, Phase 7.9H, CopyRates dalla cache "
            "storica del terminale - stessa fonte usata dal backtest) sono "
            "timestampate al loro ORARIO DI APERTURA. Una barra 'copre' l'intervallo "
            "[apertura, apertura+24h) approssimativamente - la serie e' quella del "
            "feed REALE del broker (XMGlobal-MT5), quindi salta nativamente i periodi "
            "di chiusura del mercato (weekend, festivita') - non esistono barre "
            "sintetiche per i giorni non tradati."
        ),
        "partial_entry_bar": (
            "La barra D1 la cui apertura PRECEDE il reference_time (segnale o fill). "
            "Per un ingresso INTRADAY (es. 17:30), questa barra copre l'intera "
            "giornata (00:00-24:00) e il suo High/Low PUO' contenere prezzo "
            "ANTECEDENTE alle 17:30 - non e' possibile isolare, con i soli dati OHLC "
            "D1, la porzione della barra successiva al reference_time. QUESTA BARRA "
            "NON VIENE MAI USATA per calcolare MFE/MAE/forward return in Phase 7.9K."
        ),
        "first_full_d1_bar": (
            "La PRIMA barra D1 con orario di apertura >= reference_time. Per "
            "costruzione, l'intero OHLC di questa barra e' temporalmente successivo "
            "(o esattamente coincidente, se reference_time == apertura della barra) al "
            "reference_time - non puo' MAI contenere un estremo precedente al "
            "fill/segnale. Questa e' 'bar 1' nel contratto Phase 7.9K."
        ),
        "market_bars_vs_calendar_days": (
            "'bar N' = N-esima barra D1 REALMENTE PRESENTE nel feed a partire da bar 1 "
            "- N barre DI MERCATO, non N giorni di calendario. La sequenza salta "
            "nativamente i weekend (nessuna barra sabato/domenica nel feed GOLD) - "
            "'bar 60' corrisponde quindi a circa 84-86 giorni di calendario, non 60."
        ),
    }

    # --- Copertura effettiva: verifica quantitativa che nessun fill sia esattamente a
    # mezzanotte (quindi la porzione "stesso giorno" e' SEMPRE esclusa per i 47 OPENED). ---
    events, _ = ctx.load_canonical_events()
    opened = [e for e in events["events"] if e["funnel_terminal_stage"] == "OPENED"]
    intraday_fills = [e for e in opened if not e["entry_fill_time"].endswith("00:00:00")]
    exact_midnight_fills = [e for e in opened if e["entry_fill_time"].endswith("00:00:00")]

    coverage_statement = {
        "all_47_opened_fills_are_intraday": len(intraday_fills) == 47,
        "n_intraday_fills": len(intraday_fills),
        "n_exact_midnight_fills": len(exact_midnight_fills),
        "conclusion": (
            "Tutti i 47 fill reali sono intraday (nessuno a mezzanotte esatta) - la "
            "copertura del percorso post-evento (sia misurazione A che B) comincia "
            "SEMPRE dal primo giorno di calendario SUCCESSIVO al giorno di ingresso, "
            "mai dal giorno stesso. La porzione del giorno di ingresso successiva al "
            "fill (poche ore, nella maggior parte dei casi) NON e' misurata - "
            "dichiarato come limite, non colmato con dati intraday ricostruiti (nessuna "
            "serie M15 verificata copre l'intero 2019-2026, solo un campione "
            "2023.10-2026.08 esiste come scratch non congelato)."
        ),
    }

    # --- Verifica quantitativa della censura a fine storico. ---
    last_bar_time = d1_bars[-1]["time"]
    censored_events = []
    for e in opened:
        entry_dt = datetime.strptime(e["entry_fill_time"], "%Y.%m.%d %H:%M:%S")
        idx = fp.find_first_full_bar_index(d1_bars, entry_dt)
        n_avail = len(d1_bars) - idx if idx is not None else 0
        if n_avail < 60:
            censored_events.append({"event_id": e["event_id"], "d1_bar_date": e["d1_bar_date"],
                                    "bars_available": n_avail})

    return {
        "phase": "7.9K",
        "scope": "Contratto temporale formale - risolve il difetto di indicizzazione "
            "forward confermato in Phase 7.9J (offset di +1 barra). Nessuna modifica a "
            "Phase 7.9H (dataset V1) o ai raw data - solo un nuovo contratto per gli "
            "artifact derivati V2.",
        "definitions": definitions,
        "coverage_statement": coverage_statement,
        "no_extremes_before_fill_guarantee": (
            "Per costruzione (bar 1 = prima barra con apertura >= reference_time), "
            "NESSUN valore di High/Low/Close usato nel calcolo di MFE/MAE/forward "
            "return puo' essere temporalmente antecedente al reference_time - "
            "verificato anche con test dedicati (vedi test_phase_7_9k.py::"
            "TestHandComputableSeries)."
        ),
        "last_d1_bar_available": str(last_bar_time),
        "censored_events_horizon_60_all_opened": censored_events,
        "n_censored_events": len(censored_events),
        "market_bar_to_calendar_day_example": {
            "60_market_bars_from": "2019.06.06", "corresponds_to_calendar_date": "~2019.08.30",
            "note": "approssimazione illustrativa - 60 barre di mercato saltando i weekend "
                "corrispondono a circa 84-86 giorni di calendario, non 60.",
        },
    }


def main():
    payload = build()
    doc = wrap_with_provenance(payload, os.path.basename(__file__))
    save_json(os.path.join(PHASE79K_DIR, "breakout_acc_temporal_contract_v1.json"), doc)
    print(f"canonical_sha256={doc['canonical_sha256']}")
    print(f"censored events (60-bar horizon): {payload['n_censored_events']}")
    return doc


if __name__ == "__main__":
    main()
