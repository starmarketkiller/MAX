#!/usr/bin/env python3
"""NEXUS TASK #0005 - 5 OPPORTUNITY_V1 di esempio, per validare il Funding
Priority & Opportunity Framework V1 con dati realistici (radicati nel
contesto REALE di questo progetto - infrastruttura NEXUS gia' costruita in
questa sessione), NON decisioni di business gia' prese - servono a
dimostrare che il framework discrimina correttamente fra TECHNICAL_PRIORITY
e FUNDING_PRIORITY, non a raccomandare quale perseguire.

Ogni dimensione e' una stima DICHIARATA da Claude (provenance.
dimension_estimation_method=ESTIMATED_BY_CLAUDE_NO_MARKET_DATA) - NESSUN
dato di mercato reale e' stato raccolto, NESSUNA di queste e' presentata
come un fatto verificato."""
import os
import sys

FUNDING_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(FUNDING_DIR, "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase6_6"))
from canonical_utils import wrap_with_provenance, save_json  # noqa: E402

sys.path.insert(0, FUNDING_DIR)
from opportunity_scoring import score_funding_priority, score_technical_priority  # noqa: E402


def _build(opportunity_id, title, description, category, dimensions, technical_criteria,
          technical_rationale, funding_rationale):
    funding_score, funding_breakdown = score_funding_priority(dimensions)
    technical_score, technical_breakdown = score_technical_priority(technical_criteria)
    return {
        "opportunity_id": opportunity_id, "title": title, "description": description,
        "category": category, "status": "IDEA", "dimensions": dimensions,
        "technical_priority": {"score": technical_score, "criteria": technical_criteria,
                              "rationale": technical_rationale},
        "funding_priority": {"score": funding_score, "weighted_breakdown": funding_breakdown,
                            "rationale": funding_rationale},
        "created_by": "nexus_task_0005", "created_at": "2026-09-29T00:00:00Z",
        "provenance": {"dimension_estimation_method": "ESTIMATED_BY_CLAUDE_NO_MARKET_DATA",
                     "reviewed": False},
    }


def build():
    opportunities = [
        _build(
            "OPP_DATA_PROVENANCE_COMPLIANCE_TOOL",
            "Tool di provenance/audit per fondi quant regolamentati",
            "Prodotto leggero basato sulla disciplina gia' costruita in questo progetto "
            "(canonical_sha256 + wrapper di provenance + verificatori indipendenti "
            "fail-closed) - venduto come tool di compliance/audit a piccoli fondi quant "
            "che devono dimostrare tracciabilita' dei propri artifact di ricerca.",
            "DATA_PRODUCT",
            {"time_to_cash": "MEDIUM_1_3M", "capital_required": "LOW", "sales_difficulty": "MEDIUM",
            "margin": "HIGH", "recurrence": "SUBSCRIPTION", "automation_level": "FULLY_AUTOMATED",
            "skills_available": "FULLY_AVAILABLE", "premium_tool_dependency": "NONE",
            "strategic_reuse": "CORE_REUSE", "risk": "LOW", "human_time_required": "PART_TIME"},
            {"novelty": "LOW", "infrastructure_leverage": "PARTIAL", "complexity_interest": "LOW",
            "long_term_strategic_value": "MEDIUM"},
            "Novita' tecnica bassa (e' un packaging di disciplina gia' esistente), ma "
            "infrastructure_leverage solo parziale - non fa avanzare il core NEXUS, lo "
            "esporta.",
            "Nicchia di mercato piu' facile da vendere (compliance e' un bisogno chiaro), "
            "riuso quasi totale di codice gia' scritto, rischio basso, poco tempo umano "
            "ricorrente."),
        _build(
            "OPP_BACKTEST_AS_SERVICE",
            "Backtest-as-a-Service per piccoli team quant",
            "Offrire il pipeline di backtest deterministico + Safety Net (provenance, "
            "backfill classification, escalation) come servizio a pagamento per team "
            "quant piccoli senza questa infrastruttura.",
            "SERVICE",
            {"time_to_cash": "LONG_3_6M", "capital_required": "LOW", "sales_difficulty": "HIGH",
            "margin": "MEDIUM", "recurrence": "RECURRING", "automation_level": "PARTIALLY_AUTOMATED",
            "skills_available": "FULLY_AVAILABLE", "premium_tool_dependency": "NONE",
            "strategic_reuse": "CORE_REUSE", "risk": "MEDIUM", "human_time_required": "SIGNIFICANT"},
            {"novelty": "MEDIUM", "infrastructure_leverage": "PARTIAL", "complexity_interest": "MEDIUM",
            "long_term_strategic_value": "MEDIUM"},
            "Riuso alto ma richiede adattamento per clienti esterni (non fa avanzare il "
            "core NEXUS stesso, lo confeziona per terzi).",
            "Vendita a team esterni e' intrinsecamente lenta/difficile senza rete di "
            "contatti gia' esistente - time_to_cash lungo, tempo umano significativo per "
            "onboarding/supporto clienti."),
        _build(
            "OPP_LOCAL_MODEL_ORCHESTRATOR_PRODUCT",
            "Prodotto SaaS: Orchestrator locale-first con escalation premium",
            "Productizzare il pattern Task Queue + Router + worker locale (Ministral) + "
            "escalation selettiva a premium gia' costruito e validato in questa sessione "
            "(NEXUS TASK #0001-#0004) come strumento generico per team che vogliono "
            "ridurre il costo di agenti AI premium.",
            "SAAS",
            {"time_to_cash": "VERY_LONG_GT_6M", "capital_required": "MEDIUM",
            "sales_difficulty": "HIGH", "margin": "HIGH", "recurrence": "SUBSCRIPTION",
            "automation_level": "PARTIALLY_AUTOMATED", "skills_available": "PARTIAL",
            "premium_tool_dependency": "LOW_COST", "strategic_reuse": "HIGH", "risk": "HIGH",
            "human_time_required": "FULL_TIME"},
            {"novelty": "HIGH", "infrastructure_leverage": "HIGH", "complexity_interest": "HIGH",
            "long_term_strategic_value": "HIGH"},
            "Il piu' alto in infrastructure_leverage: costruirlo bene fa avanzare "
            "DIRETTAMENTE le capacita' core di NEXUS stesso, non solo un derivato.",
            "Time-to-cash molto lungo (serve generalizzare da 'funziona per noi' a "
            "'prodotto vendibile'), capitale/tempo pieno richiesti, rischio alto - "
            "l'opposto esatto del profilo 'genera cassa presto'."),
        _build(
            "OPP_SAFETY_NET_METHODOLOGY_CONSULTING",
            "Consulenza/workshop sulla metodologia Research Safety Net",
            "Vendere come consulenza/workshop la disciplina scientifica Phase 7 (outcome-"
            "blind preflight, preregistrazione, backfill classification, escalation "
            "strutturata) a team di ricerca quant che vogliono irrobustire il proprio "
            "processo.",
            "CONSULTING",
            {"time_to_cash": "LONG_3_6M", "capital_required": "NONE", "sales_difficulty": "HIGH",
            "margin": "VERY_HIGH", "recurrence": "OCCASIONAL", "automation_level": "MANUAL",
            "skills_available": "FULLY_AVAILABLE", "premium_tool_dependency": "NONE",
            "strategic_reuse": "PARTIAL", "risk": "MEDIUM", "human_time_required": "SIGNIFICANT"},
            {"novelty": "LOW", "infrastructure_leverage": "NONE", "complexity_interest": "LOW",
            "long_term_strategic_value": "LOW"},
            "Non fa avanzare l'infrastruttura NEXUS in alcun modo - e' puro trasferimento "
            "di conoscenza gia' maturata, valore strategico basso per NEXUS stesso.",
            "Margine altissimo (consulenza pura) ma non scalabile/non ricorrente in modo "
            "affidabile, richiede tempo umano diretto significativo per ogni engagement."),
        _build(
            "OPP_MT5_STRATEGY_SIGNAL_SUBSCRIPTION",
            "Abbonamento segnali di trading dalle strategie NEXUS validate",
            "Vendere un abbonamento a segnali generati dalle strategie gia' sviluppate in "
            "questo progetto (LIQ_SWEEP, BREAKOUT_ACC, ORDER_BLOCK). ATTENZIONE ESPLICITA: "
            "NESSUNA di queste strategie ha oggi lo stato EDGE_CONFIRMED - Phase 7.27 ha "
            "gia' trovato che la dominanza BUY osservata e' largamente spiegata dal regime "
            "di mercato, non da un edge specifico (BUY_DOMINANCE_LARGELY_EXPLAINED_BY_"
            "MARKET_REGIME). Questa opportunity NON E' AZIONABILE oggi - inclusa solo per "
            "dimostrare che il framework la classifica correttamente come rischiosa "
            "nonostante punteggi di automazione/ricorrenza attraenti.",
            "PRODUCT",
            {"time_to_cash": "SHORT_LT_1M", "capital_required": "NONE", "sales_difficulty": "HIGH",
            "margin": "HIGH", "recurrence": "SUBSCRIPTION", "automation_level": "FULLY_AUTOMATED",
            "skills_available": "FULLY_AVAILABLE", "premium_tool_dependency": "NONE",
            "strategic_reuse": "PARTIAL", "risk": "VERY_HIGH", "human_time_required": "MINIMAL"},
            {"novelty": "LOW", "infrastructure_leverage": "NONE", "complexity_interest": "LOW",
            "long_term_strategic_value": "LOW"},
            "Non fa avanzare l'infrastruttura di ricerca/orchestrazione - e' puro "
            "sfruttamento commerciale di un risultato che oggi NON esiste ancora "
            "(nessun edge confermato).",
            "Punteggio funding ALTO per automazione/ricorrenza/tempo umano minimo, MA "
            "risk=VERY_HIGH abbassa il punteggio e la descrizione dichiara esplicitamente "
            "che nessuna strategia sottostante ha oggi un edge confermato - illustra "
            "perche' il framework non deve MAI essere letto senza il campo risk e la "
            "descrizione completa."),
    ]
    return {"schema_version": 1, "opportunities": opportunities}


def main():
    payload = build()
    doc = wrap_with_provenance(payload, script=os.path.abspath(__file__))
    out_path = os.path.join(FUNDING_DIR, "example_instances", "opportunities_v1.json")
    save_json(out_path, doc)
    print(f"Scritto {out_path} ({len(payload['opportunities'])} opportunities)")


if __name__ == "__main__":
    main()
