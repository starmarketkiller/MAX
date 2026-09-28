#!/usr/bin/env python3
"""Phase 7.25 punto 6 - execution realism. Riusa il funnel GIA'
riconciliato aritmeticamente in Phase 7.24 (nessuna anomalia irrisolta,
a differenza di ORDER_BLOCK Phase 7.22) - qui aggiunge la separazione
esplicita signal-level opportunity / executable trade / realized trade
richiesta dal task. Blocked/reject/opened/closed/still-open TUTTI
preservati, nessuno scartato dal funnel."""
import os
import sys

PHASE725_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(PHASE725_DIR, "..", "..", "..", ".."))
PHASE724_DIR = os.path.join(ROOT, "server", "research_scripts", "phase7", "phase7_24")
sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase6_6"))
from canonical_utils import wrap_with_provenance, save_json, load_json  # noqa: E402


def build():
    funnel = load_json(os.path.join(PHASE724_DIR, "funnel_accounting_v1.json"))["payload"]
    fc = funnel["final_counts"]
    generated = fc["generated"]

    levels = {
        "signal_level_opportunity": {
            "definition": "Ogni barra D1 chiusa in cui detector di sweep + delivery-candle filter "
                         "+ direzione producono un segnale valido (PRIMA di qualunque gate "
                         "applicativo/single-position-at-a-time).",
            "count": generated,
        },
        "executable_trade": {
            "definition": "Segnale che supera i gate applicativi (nessuna posizione LIQ_SWEEP gia' "
                         "aperta, TF gate) ed e' effettivamente inviato come tentativo d'ordine.",
            "count": None,  # assegnato subito sotto da funnel_stages (open_attempt)
        },
        "realized_trade": {
            "definition": "Posizione realmente aperta E chiusa entro la fine della finestra "
                         "testata - fonte del dataset economico.",
            "count": fc["closed_within_window"],
        },
    }

    open_attempt = None
    broker_reject = None
    for stage in funnel["funnel_stages"]:
        if stage["stage"] == "3_open_attempt":
            open_attempt = stage["count"]
        if stage["stage"] == "4_broker_reject":
            broker_reject = stage["count"]
    levels["executable_trade"]["count"] = open_attempt

    funnel_preserved = {
        "generated": generated,
        "blocked": fc.get("generated") - open_attempt if generated is not None and open_attempt is not None else None,
        "open_attempt": open_attempt,
        "broker_reject": broker_reject,
        "opened": fc["opened"],
        "closed_within_window": fc["closed_within_window"],
        "still_open_at_period_end": fc["still_open_at_period_end"],
    }

    rates = {
        "pct_generated_that_get_blocked": (funnel_preserved["blocked"] / generated * 100)
                                          if generated else None,
        "pct_generated_that_get_rejected": (broker_reject / generated * 100) if generated else None,
        "pct_generated_that_open": (fc["opened"] / generated * 100) if generated else None,
        "pct_opened_that_close_within_window": (fc["closed_within_window"] / fc["opened"] * 100)
                                               if fc["opened"] else None,
        "pct_open_attempt_rejected_by_broker": (broker_reject / open_attempt * 100)
                                               if open_attempt else None,
    }

    payload = {
        "source": "funnel_accounting_v1.json (Phase 7.24) - riconciliato aritmeticamente, zero "
                 "residuo UNKNOWN/DATA_LOSS. Nessun nuovo run in questa fase per l'execution "
                 "realism (dati gia' sufficienti e riconciliati).",
        "granularity": "AGGREGATO (conteggi per stadio del funnel) per signal/blocked/reject - "
                      "PER-EVENTO per opened/closed/still-open (dataset canonico completo).",
        "three_level_separation": levels,
        "funnel_all_stages_preserved_none_dropped": funnel_preserved,
        "funnel_rates": rates,
        "blocked_and_rejected_not_dropped": True,
        "known_limitation": "Impossibile in questa fase distinguere se i segnali BLOCKED (quasi "
            "tutti per gate OPEN_POSITION - una posizione LIQ_SWEEP era gia' aperta) avessero, in "
            "media, una qualita' di segnale migliore o peggiore di quelli aperti - nessun proxy di "
            "movimento forward per-evento disponibile per i segnali bloccati (stesso gap gia' "
            "dichiarato per ORDER_BLOCK in Phase 7.22). Per questo motivo il visual audit di questa "
            "fase NON include un campione reale 'blocked/near-miss' con dati price-action - vedi "
            "visual_audit_sample_v1.json.",
        "execution_does_not_collapse_to_zero": fc["opened"] > 0,
    }
    return payload


def main():
    payload = build()
    doc = wrap_with_provenance(payload, script=os.path.abspath(__file__))
    out_path = os.path.join(PHASE725_DIR, "execution_realism_v1.json")
    save_json(out_path, doc)
    print(f"Scritto {out_path} (sha256={doc['canonical_sha256'][:16]}...)")
    print(f"  funnel: {payload['funnel_all_stages_preserved_none_dropped']}")


if __name__ == "__main__":
    main()
