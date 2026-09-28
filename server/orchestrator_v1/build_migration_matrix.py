#!/usr/bin/env python3
"""Orchestrator V1 punto 38 - classifica esempi REALI di task gia'
svolti nelle Phase 7 (non ipotetici) secondo i tier definiti in Parte A."""
import os
import sys

ORCH_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(ORCH_DIR, "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase6_6"))
from canonical_utils import wrap_with_provenance, save_json  # noqa: E402


def build():
    examples = [
        {"task": "Ricostruire e verificare i registry di Phase 7.26 (hash canonico, riferimenti "
               "orfani)", "tier": "DETERMINISTIC",
        "reason": "Puro Python/pytest - nessun ragionamento linguistico necessario."},
        {"task": "Lanciare/monitorare un run MT5 via harness di isolamento, raccogliere risultati",
        "tier": "DETERMINISTIC",
        "reason": "Orchestrazione di processi + parsing file - gia' fatto senza LLM in Phase "
                 "7.23-7.25."},
        {"task": "Riassumere un log di test fallito in una frase per il vault report",
        "tier": "LOCAL_FAST",
        "reason": "Riassunto di testo strutturato, basso rischio, nessun giudizio scientifico."},
        {"task": "Backfill temporal_concentration + exit_efficiency per BREAKOUT_ACC e ORDER_BLOCK",
        "tier": "LOCAL_STRONG",
        "reason": "Richiede scrivere un builder Python nuovo (pattern gia' visto in LIQ_SWEEP, "
                 "Phase 7.25) che legge dataset esistenti e calcola statistiche - generazione di "
                 "codice moderata, dati e schema gia' noti, verificabile con hash canonico - "
                 "CANDIDATO ESPLICITO al primo pilota locale (vedi build_first_pilot_spec.py). "
                 "Rischio scientifico BASSO (nessuna nuova decisione di edge), rischio di codice "
                 "MEDIO (un builder nuovo, ma con un pattern quasi identico gia' esistente da "
                 "copiare/adattare)."},
        {"task": "Decidere se la dominanza BUY riflette il regime di mercato o un edge specifico "
               "(Phase 7.27, preregistrazione + benchmark + decisione)", "tier": "CLAUDE_REQUIRED",
        "reason": "Causal reasoning, disegno sperimentale, adjudication - rischio scientifico "
                 "ALTO, richiede giudizio metodologico (preregistrazione, evitare cherry-picking, "
                 "interpretare risultati misti)."},
        {"task": "Trovare e correggere il bug di collisione di nomi modulo Python fra fasi "
               "diverse (Phase 7.25/7.26)", "tier": "CLAUDE_REQUIRED",
        "reason": "Debugging non banale che ha richiesto capire un comportamento di Python "
                 "(sys.modules) non ovvio dal solo messaggio di errore - rischio di codice "
                 "MEDIO-ALTO in un sistema con molte fasi interdipendenti."},
        {"task": "Integrare i registry Phase 7.26 nel Control Plane frontend "
               "(ResearchControlPlanePage.jsx + server/research_control_plane.py)",
        "tier": "CODEX_REQUIRED",
        "reason": "Refactor multi-file backend/frontend, integrazione con Product Platform - "
                 "esattamente il pattern gia' osservato in pratica in questa sessione (l'autore "
                 "'Codex' ha fatto proprio questo dopo ogni fase Claude)."},
        {"task": "Generare 38 chart SVG research-only per il Visual Audit (Phase 7.25)",
        "tier": "LOCAL_STRONG",
        "reason": "Codice di rendering ripetitivo/parametrico una volta definito il pattern - "
                 "avrebbe potuto essere delegato dopo che Claude ha stabilito la libreria SVG "
                 "puro-Python (il PRIMO caso, la scoperta del blocco matplotlib e il pivot, "
                 "restava CLAUDE_REQUIRED per il giudizio tecnico)."},
    ]
    payload = {
        "examples": examples,
        "pilot_candidate": "Backfill temporal_concentration + exit_efficiency per BREAKOUT_ACC e "
                          "ORDER_BLOCK",
        "pilot_candidate_tier": "LOCAL_STRONG",
        "pilot_rationale": "E' l'esempio esplicitamente richiesto dal task E il candidato gia' in "
            "cima alla Research Priority Queue (Phase 7.26/7.27, punteggio 29, status PENDING) - "
            "pattern di codice quasi identico gia' scritto (build_liq_sweep_temporal_robustness.py "
            "/ build_liq_sweep_path_anatomy.py da Phase 7.25/7.26 possono essere adattati) e "
            "verificabile automaticamente via hash canonico - basso rischio se il worker locale "
            "fallisce (nessun impatto scientifico, solo un builder da rifare).",
    }
    return payload


def main():
    payload = build()
    doc = wrap_with_provenance(payload, script=os.path.abspath(__file__))
    out_path = os.path.join(ORCH_DIR, "migration_matrix_v1.json")
    save_json(out_path, doc)
    print(f"Scritto {out_path} (sha256={doc['canonical_sha256'][:16]}...)")


if __name__ == "__main__":
    main()
