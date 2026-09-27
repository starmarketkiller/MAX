#!/usr/bin/env python3
"""Phase 7.20 punto 7 - quale UNA strategia consigliare come prima da
validare con EDGE_VALIDATION_V1."""
import os
import sys

PHASE720_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(PHASE720_DIR, "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase6_6"))
from canonical_utils import wrap_with_provenance, save_json  # noqa: E402


def build():
    payload = {
        "recommended_first": "BREAKOUT_ACC",
        "not_order_block_because": "ORDER_BLOCK ha integrita' altrettanto pulita ma RICHIEDE un nuovo "
            "run MT5 reale (nessun dato economico esiste oggi per l'implementazione V2) prima di poter "
            "anche solo iniziare lo Stadio 1 (baseline edge) del protocollo - un costo/tempo che "
            "BREAKOUT_ACC non richiede.",
        "why_breakout_acc": [
            "E' l'UNICA strategia del corpus con un canonical event dataset GIA' ESISTENTE, a fill "
            "reali, con costi (swap/commissione/slippage) gia' catturati per evento - gli Stadi 1 "
            "(baseline edge) e 2 (costi) di EDGE_VALIDATION_V1 possono iniziare SUBITO, senza attendere "
            "nessun nuovo run MT5.",
            "L'unico gap strutturale per completare il protocollo e' lo Stadio 3 (OOS) - richiede "
            "raccogliere un periodo temporalmente successivo, un lavoro delimitato e piu' piccolo di "
            "costruire un intero dataset da zero.",
            "Il pattern (BUY side) e' sopravvissuto a una correzione metodologica sostanziale sugli "
            "stessi dati - un indizio di robustezza al netto della bassa confidence dichiarata, non una "
            "prova di edge.",
        ],
        "explicit_caveat": "Il lato SELL (15 eventi) NON deve essere incluso nel primo passaggio del "
            "protocollo - campione troppo piccolo per essere informativo da solo; consigliato testare "
            "SOLO BUY nel primo giro, poi eventualmente SELL separatamente con l'accumulo di piu' dati.",
        "not_a_promotion": "Questa raccomandazione riguarda SOLO l'ordine di lavoro (quale strategia "
            "validare per prima), non e' un'affermazione che BREAKOUT_ACC abbia gia' un edge - "
            "esattamente cio' che lo Stadio 1 del protocollo dovra' stabilire.",
    }
    return payload


def main():
    payload = build()
    doc = wrap_with_provenance(payload, script=os.path.abspath(__file__))
    out_path = os.path.join(PHASE720_DIR, "recommended_first_v1.json")
    save_json(out_path, doc)
    print(f"Scritto {out_path} (sha256={doc['canonical_sha256'][:16]}...)")
    print(f"  RACCOMANDATA: {payload['recommended_first']}")


if __name__ == "__main__":
    main()
