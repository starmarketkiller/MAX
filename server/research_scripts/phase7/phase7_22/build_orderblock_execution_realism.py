#!/usr/bin/env python3
"""Phase 7.22 punto 8 - execution realism. Usa il certificato BASE
(nxs_orderblock_discovery_certificate_base.txt, run_id senza suffisso
_rXXX, period_end=2026.08.24 - combacia con l'ultimo trade reale nel
dataset) come fonte del funnel AGGREGATO - non un certificato prodotto
da questa fase (i certificati _r001/_r002 generati oggi mostravano
conteggi palesemente incompleti, GENERATED=2, incoerenti con i 13
trade reali gia' nel log - anomalia dichiarata in
orderblock_data_exposure_map_v1.json, non nascosta).

Granularita' AGGREGATA (conteggi per stadio), NON per-evento - a
differenza di BREAKOUT_ACC (Phase 7.21). Blocked/reject riportati come
conteggio, non persi."""
import os
import re
import sys

PHASE722_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(PHASE722_DIR, "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase6_6"))
from canonical_utils import wrap_with_provenance, save_json  # noqa: E402

CERT_PATH = os.path.join(PHASE722_DIR, "nxs_orderblock_discovery_certificate_base.txt")


def _parse_certificate(path):
    if not os.path.exists(path):
        return None
    with open(path, encoding="utf-8") as f:
        text = f.read()
    m = re.search(r"GENERATED=(\d+) BLOCKED=(\d+) OPEN_ATTEMPT=(\d+) OPENED=(\d+) BROKER_REJECT=(\d+)", text)
    if not m:
        return {"raw_text": text, "parse_error": "pattern funnel non trovato"}
    keys = ["GENERATED", "BLOCKED", "OPEN_ATTEMPT", "OPENED", "BROKER_REJECT"]
    return {"counts": {k: int(v) for k, v in zip(keys, m.groups())}, "raw_text": text}


def build():
    cert = _parse_certificate(CERT_PATH)
    if cert is None:
        return {"status": "CERTIFICATE_NOT_YET_CAPTURED"}

    counts = cert.get("counts", {})
    generated = counts.get("GENERATED", 0)
    opened_cert = counts.get("OPENED", 0)
    blocked = counts.get("BLOCKED", 0)
    rejected = counts.get("BROKER_REJECT", 0)

    payload = {
        "source": "Certificato BASE (run_id GOLD_2023.10.02 00:00:00_sel15, senza suffisso, "
                 "period_end=2026.08.24, prodotto in una sessione precedente a questa fase, "
                 "trovato in Common/Files/NEXUS/certificates/) - NON un certificato di questa fase.",
        "reconciliation_note_declared": "Il certificato riporta OPENED=12, ma il dataset economico "
            "canonico di questa fase (canonical_economic_dataset_v1.json, costruito direttamente "
            "da NEXUS_trades.csv riga per riga) conta 13 trade OPEN->CLOSE distinti nella stessa "
            "finestra. Discrepanza di 1 trade NON risolta in questa fase (possibile edge-case al "
            "confine esatto del period_end, o un trade proveniente da un run leggermente diverso) - "
            "dichiarata esplicitamente, non nascosta. Il dataset economico (CSV riga per riga, "
            "verificabile) resta la fonte primaria per la baseline - il certificato e' usato SOLO "
            "per il contesto aggregato del funnel (blocked/reject), non per il conteggio dei trade.",
        "granularity": "AGGREGATO (conteggi per stadio del funnel), NON per-evento - a differenza "
            "di BREAKOUT_ACC (Phase 7.21).",
        "funnel_counts": counts,
        "funnel_counts_opened_vs_dataset_n13_discrepancy": opened_cert - 13,
        "funnel_rates": {
            "pct_generated_that_get_blocked": (blocked / generated * 100) if generated else None,
            "pct_generated_that_get_rejected": (rejected / generated * 100) if generated else None,
            "pct_generated_that_open_per_certificate": (opened_cert / generated * 100) if generated else None,
        },
        "blocked_and_rejected_not_dropped": True,
        "known_limitation": "Impossibile in questa fase distinguere se i segnali BLOCKED avessero, "
            "in media, una qualita' di segnale migliore o peggiore di quelli aperti (nessun proxy "
            "di movimento forward per-evento disponibile per questa strategia in questa fase, a "
            "differenza di BREAKOUT_ACC) - dichiarato come gap, non nascosto.",
    }
    return payload


def main():
    payload = build()
    doc = wrap_with_provenance(payload, script=os.path.abspath(__file__))
    out_path = os.path.join(PHASE722_DIR, "orderblock_execution_realism_v1.json")
    save_json(out_path, doc)
    print(f"Scritto {out_path} (sha256={doc['canonical_sha256'][:16]}...)")
    if payload.get("status") != "CERTIFICATE_NOT_YET_CAPTURED":
        print(f"  funnel: {payload['funnel_counts']}")


if __name__ == "__main__":
    main()
