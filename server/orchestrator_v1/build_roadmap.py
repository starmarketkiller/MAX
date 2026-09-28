#!/usr/bin/env python3
"""Orchestrator V1 punto 40 - roadmap di implementazione V0-V8. Nessun
codice di produzione scritto in questa fase - solo la sequenza."""
import os
import sys

ORCH_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(ORCH_DIR, "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase6_6"))
from canonical_utils import wrap_with_provenance, save_json  # noqa: E402


def build():
    stages = [
        {"stage": "V0", "name": "Schemas + Activity Ledger",
        "content": "I 6 schemi contracts/*.schema.json (gia' consegnati in questa fase) + "
                  "l'implementazione dell'Activity Ledger append-only (SQLite locale o file "
                  "JSONL - non ancora deciso, dettaglio implementativo per V0 stesso).",
        "delivered_in_this_phase": True},
        {"stage": "V1", "name": "Deterministic worker + code",
        "content": "Un piccolo runner Python che sa eseguire i task TIER 0 (rebuild registry, "
                  "pytest, git checks) leggendo un TASK_MANIFEST e scrivendo un RESULT_PACKET - "
                  "ZERO LLM coinvolto.",
        "delivered_in_this_phase": False},
        {"stage": "V2", "name": "Local agent runtime",
        "content": "Installazione Ollama + modello raccomandato (vedi install_plan_v1.json), "
                  "esecuzione del primo pilota (first_pilot_spec_v1.json).",
        "delivered_in_this_phase": False},
        {"stage": "V3", "name": "Router + escalation premium",
        "content": "Implementazione di ROUTING_POLICY_V1 come codice reale (non solo pseudocodice) "
                  "- capability matching, risk gates, retry/escalation.",
        "delivered_in_this_phase": False},
        {"stage": "V4", "name": "Control Plane integration",
        "content": "Collegare l'Activity Ledger e i RESULT_PACKET al Control Plane gia' esistente "
                  "(server/research_control_plane.py + ResearchControlPlanePage.jsx) - "
                  "probabilmente lavoro TIER 4 (Codex), coerente col pattern gia' osservato in "
                  "questa sessione.",
        "delivered_in_this_phase": False},
        {"stage": "V5", "name": "Jarvis text",
        "content": "Interfaccia testuale di query/notifica/approvazione (item 19) - legge SOLO "
                  "dall'Activity Ledger, non e' mai source of truth.",
        "delivered_in_this_phase": False},
        {"stage": "V6", "name": "Jarvis voice",
        "content": "Strato vocale sopra V5 - stesso contratto, nessuna nuova autorita' decisionale.",
        "delivered_in_this_phase": False},
        {"stage": "V7", "name": "MT5 read-only",
        "content": "Jarvis/worker locale possono LEGGERE stato/log MT5 (gia' dimostrato tecnicamente "
                  "possibile in Phase 7.23-7.25) - nessuna scrittura/esecuzione ordini.",
        "delivered_in_this_phase": False},
        {"stage": "V8", "name": "Approval/trading actions",
        "content": "L'UNICO stadio che tocca esecuzione reale - richiede EXPLICIT_USER_APPROVAL "
                  "per costruzione (item 17/18) - ultimo della sequenza per disegno, non per "
                  "convenienza implementativa.",
        "delivered_in_this_phase": False},
    ]
    payload = {
        "stages": stages,
        "sequence_rationale": "L'ordine e' deliberatamente PRUDENTE: infrastruttura di "
            "osservabilita' (V0-V1) prima di qualunque agente reale, agente locale (V2-V3) prima "
            "dell'integrazione UI (V4), interfaccia utente (V5-V6) prima di QUALUNQUE accesso a "
            "MT5 (V7), e accesso MT5 in sola lettura prima di qualunque azione (V8) - coerente "
            "con la gerarchia di autorita' gia' stabilita in docs/NEXUS_MASTER_PROJECT.md "
            "Blocco A3.8 e con l'invariante 'l'AI non puo' bypassare il Risk Engine'.",
        "sequence_not_forced_can_be_revised": True,
    }
    return payload


def main():
    payload = build()
    doc = wrap_with_provenance(payload, script=os.path.abspath(__file__))
    out_path = os.path.join(ORCH_DIR, "roadmap_v1.json")
    save_json(out_path, doc)
    print(f"Scritto {out_path} (sha256={doc['canonical_sha256'][:16]}...)")


if __name__ == "__main__":
    main()
