#!/usr/bin/env python3
"""NEXUS TASK #0005/#0006 - 5 OPPORTUNITY_V1 di esempio (dalla fase #0005,
MIGRATE per includere tutti i nuovi campi di #0006 - hardening, non
riprogettazione: gli score/dimensioni ORIGINALI restano identici, solo
arricchiti con evidence_confidence/hard_gate/capital_scenarios/capability_
coverage/lifecycle/next_cheapest_validation_step/learning_record).

Radicati nel contesto REALE di questo progetto - NON decisioni di business
gia' prese, marcati ESPLICITAMENTE PROVISIONAL/HYPOTHESIS_BASED (mai
VALIDATED)."""
import json
import os
import sys

FUNDING_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(FUNDING_DIR, "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase6_6"))
from canonical_utils import wrap_with_provenance, save_json  # noqa: E402

sys.path.insert(0, FUNDING_DIR)
from opportunity_assembly import assemble_opportunity  # noqa: E402
from initial_hypothesis_inputs import INITIAL_HYPOTHESES  # noqa: E402

_NARRATIVES_PATH = os.path.join(ROOT, "server", "orchestrator_v1",
                               "nexus_task_0006_narratives_v1.json")
_HYPOTHESIS_COMMON = {"created_by": "nexus_task_0006", "created_at": "2026-09-29T00:00:00Z",
                     "dimension_estimation_method": "ESTIMATED_BY_CLAUDE_NO_MARKET_DATA",
                     "input_type": "ASSUMPTION", "evidence_confidence": "LOW"}


def _build_initial_hypothesis_opportunities():
    """NEXUS TASK #0006 punto 11 - assembla le 13 INITIAL_HYPOTHESIS usando i
    campi strutturati dichiarati da Claude (initial_hypothesis_inputs.py) +
    la narrativa gia' generata e verificata da ministral-3:3b attraverso
    l'Orchestrator (nexus_task_0006_narratives_v1.json) - MAI rigenerata
    qui: legge l'output gia' congelato per restare riproducibile
    (builder->artifact deterministico, la generazione stocastica resta un
    passo separato e a monte, stesso pattern di NEXUS TASK #0002)."""
    with open(_NARRATIVES_PATH, encoding="utf-8") as f:
        narratives = json.load(f)["results"]

    opportunities = []
    for spec in INITIAL_HYPOTHESES:
        narrative = narratives.get(spec["id"])
        if narrative is None:
            raise AssertionError(
                f"narrativa mancante per {spec['id']} - rieseguire "
                "run_nexus_task_0006_generate_dataset.py prima di costruire il dataset")
        opportunities.append(assemble_opportunity(
            opportunity_id=spec["id"], title=spec["title"], category=spec["category"],
            status="IDEA", dimensions=spec["dimensions"],
            technical_criteria=spec["technical_criteria"],
            description=narrative["description"],
            technical_rationale=narrative["technical_rationale"],
            funding_rationale=narrative["funding_rationale"],
            required_capabilities=spec["required_capabilities"],
            next_cheapest_validation_step=spec["next_cheapest_validation_step"],
            **_HYPOTHESIS_COMMON))
    return opportunities

_COMMON = {"created_by": "nexus_task_0005", "created_at": "2026-09-29T00:00:00Z",
          "dimension_estimation_method": "ESTIMATED_BY_CLAUDE_NO_MARKET_DATA",
          "input_type": "ASSUMPTION"}


def build():
    opportunities = [
        assemble_opportunity(
            opportunity_id="OPP_DATA_PROVENANCE_COMPLIANCE_TOOL",
            title="Tool di provenance/audit per fondi quant regolamentati",
            description="Prodotto leggero basato sulla disciplina gia' costruita in questo "
                       "progetto (canonical_sha256 + wrapper di provenance + verificatori "
                       "indipendenti fail-closed) - venduto come tool di compliance/audit a "
                       "piccoli fondi quant che devono dimostrare tracciabilita' dei propri "
                       "artifact di ricerca.",
            category="DATA_PRODUCT", status="IDEA",
            dimensions={"time_to_cash": "MEDIUM_1_3M", "capital_required": "LOW",
                      "sales_difficulty": "MEDIUM", "margin": "HIGH", "recurrence": "SUBSCRIPTION",
                      "automation_level": "FULLY_AUTOMATED", "skills_available": "FULLY_AVAILABLE",
                      "premium_tool_dependency": "NONE", "strategic_reuse": "CORE_REUSE",
                      "risk": "LOW", "human_time_required": "PART_TIME"},
            technical_criteria={"novelty": "LOW", "infrastructure_leverage": "PARTIAL",
                              "complexity_interest": "LOW", "long_term_strategic_value": "MEDIUM"},
            technical_rationale="Novita' tecnica bassa (packaging di disciplina gia' "
                               "esistente), infrastructure_leverage solo parziale - non fa "
                               "avanzare il core NEXUS, lo esporta.",
            funding_rationale="Nicchia piu' facile da vendere (compliance e' un bisogno "
                             "chiaro), riuso quasi totale di codice gia' scritto, rischio "
                             "basso, poco tempo umano ricorrente.",
            required_capabilities=["orchestrator", "deterministic_workers", "website_generation"],
            evidence_confidence="LOW",
            next_cheapest_validation_step={
                "description": "Cercare 20 piccoli fondi quant/prop desk su LinkedIn e "
                              "verificare se menzionano requisiti di compliance/audit nei "
                              "loro annunci di lavoro o siti - nessun contatto diretto.",
                "estimated_cost": "NONE", "reversibility": "FULLY_REVERSIBLE", "speed": "DAYS",
                "informational_value": "MEDIUM"},
            **_COMMON),
        assemble_opportunity(
            opportunity_id="OPP_BACKTEST_AS_SERVICE",
            title="Backtest-as-a-Service per piccoli team quant",
            description="Offrire il pipeline di backtest deterministico + Safety Net "
                       "(provenance, backfill classification, escalation) come servizio a "
                       "pagamento per team quant piccoli senza questa infrastruttura.",
            category="SERVICE", status="IDEA",
            dimensions={"time_to_cash": "LONG_3_6M", "capital_required": "LOW",
                      "sales_difficulty": "HIGH", "margin": "MEDIUM", "recurrence": "RECURRING",
                      "automation_level": "PARTIALLY_AUTOMATED", "skills_available": "FULLY_AVAILABLE",
                      "premium_tool_dependency": "NONE", "strategic_reuse": "CORE_REUSE",
                      "risk": "MEDIUM", "human_time_required": "SIGNIFICANT"},
            technical_criteria={"novelty": "MEDIUM", "infrastructure_leverage": "PARTIAL",
                              "complexity_interest": "MEDIUM", "long_term_strategic_value": "MEDIUM"},
            technical_rationale="Riuso alto ma richiede adattamento per clienti esterni (non "
                               "fa avanzare il core NEXUS stesso, lo confeziona per terzi).",
            funding_rationale="Vendita a team esterni e' intrinsecamente lenta/difficile "
                             "senza rete di contatti gia' esistente - time_to_cash lungo, "
                             "tempo umano significativo per onboarding/supporto clienti.",
            required_capabilities=["orchestrator", "deterministic_workers", "local_llm",
                                  "research", "crm", "customer_support"],
            evidence_confidence="LOW",
            next_cheapest_validation_step={
                "description": "Postare in 3 forum/community quant online una domanda aperta "
                              "su come i piccoli team gestiscono oggi provenance/audit dei "
                              "backtest - misurare interesse dalle risposte.",
                "estimated_cost": "NONE", "reversibility": "FULLY_REVERSIBLE", "speed": "WEEKS",
                "informational_value": "HIGH"},
            **_COMMON),
        assemble_opportunity(
            opportunity_id="OPP_LOCAL_MODEL_ORCHESTRATOR_PRODUCT",
            title="Prodotto SaaS: Orchestrator locale-first con escalation premium",
            description="Productizzare il pattern Task Queue + Router + worker locale "
                       "(Ministral) + escalation selettiva a premium gia' costruito e "
                       "validato in questa sessione (NEXUS TASK #0001-#0004) come strumento "
                       "generico per team che vogliono ridurre il costo di agenti AI premium.",
            category="SAAS", status="IDEA",
            dimensions={"time_to_cash": "VERY_LONG_GT_6M", "capital_required": "MEDIUM",
                      "sales_difficulty": "HIGH", "margin": "HIGH", "recurrence": "SUBSCRIPTION",
                      "automation_level": "PARTIALLY_AUTOMATED", "skills_available": "PARTIAL",
                      "premium_tool_dependency": "LOW_COST", "strategic_reuse": "HIGH",
                      "risk": "HIGH", "human_time_required": "FULL_TIME"},
            technical_criteria={"novelty": "HIGH", "infrastructure_leverage": "HIGH",
                              "complexity_interest": "HIGH", "long_term_strategic_value": "HIGH"},
            technical_rationale="Il piu' alto in infrastructure_leverage: costruirlo bene fa "
                               "avanzare DIRETTAMENTE le capacita' core di NEXUS stesso, non "
                               "solo un derivato.",
            funding_rationale="Time-to-cash molto lungo (serve generalizzare da 'funziona "
                             "per noi' a 'prodotto vendibile'), capitale/tempo pieno "
                             "richiesti, rischio alto - l'opposto esatto del profilo 'genera "
                             "cassa presto'.",
            required_capabilities=["orchestrator", "deterministic_workers", "local_llm",
                                  "coding", "crm", "payments", "customer_support"],
            evidence_confidence="LOW",
            next_cheapest_validation_step={
                "description": "Scrivere un post tecnico (blog/forum) che descrive "
                              "l'architettura gia' costruita (Task Queue+Router+escalation) "
                              "e misurare l'interesse (commenti/richieste di dettagli) prima "
                              "di scrivere una sola riga di codice di produttizzazione.",
                "estimated_cost": "NONE", "reversibility": "FULLY_REVERSIBLE", "speed": "DAYS",
                "informational_value": "MEDIUM"},
            **_COMMON),
        assemble_opportunity(
            opportunity_id="OPP_SAFETY_NET_METHODOLOGY_CONSULTING",
            title="Consulenza/workshop sulla metodologia Research Safety Net",
            description="Vendere come consulenza/workshop la disciplina scientifica Phase 7 "
                       "(outcome-blind preflight, preregistrazione, backfill classification, "
                       "escalation strutturata) a team di ricerca quant che vogliono "
                       "irrobustire il proprio processo.",
            category="CONSULTING", status="IDEA",
            dimensions={"time_to_cash": "LONG_3_6M", "capital_required": "NONE",
                      "sales_difficulty": "HIGH", "margin": "VERY_HIGH", "recurrence": "OCCASIONAL",
                      "automation_level": "MANUAL", "skills_available": "FULLY_AVAILABLE",
                      "premium_tool_dependency": "NONE", "strategic_reuse": "PARTIAL",
                      "risk": "MEDIUM", "human_time_required": "SIGNIFICANT"},
            technical_criteria={"novelty": "LOW", "infrastructure_leverage": "NONE",
                              "complexity_interest": "LOW", "long_term_strategic_value": "LOW"},
            technical_rationale="Non fa avanzare l'infrastruttura NEXUS in alcun modo - e' "
                               "puro trasferimento di conoscenza gia' maturata, valore "
                               "strategico basso per NEXUS stesso.",
            funding_rationale="Margine altissimo (consulenza pura) ma non scalabile/non "
                             "ricorrente in modo affidabile, richiede tempo umano diretto "
                             "significativo per ogni engagement.",
            required_capabilities=["research", "content"],
            evidence_confidence="LOW",
            next_cheapest_validation_step={
                "description": "Scrivere 1 articolo pubblico che riassume la metodologia e "
                              "vedere se genera richieste di consulenza organiche, prima di "
                              "investire tempo a costruire un'offerta formale.",
                "estimated_cost": "NONE", "reversibility": "FULLY_REVERSIBLE", "speed": "WEEKS",
                "informational_value": "HIGH"},
            **_COMMON),
        assemble_opportunity(
            opportunity_id="OPP_MT5_STRATEGY_SIGNAL_SUBSCRIPTION",
            title="Abbonamento segnali di trading dalle strategie NEXUS validate",
            description="Vendere un abbonamento a segnali generati dalle strategie gia' "
                       "sviluppate in questo progetto (LIQ_SWEEP, BREAKOUT_ACC, ORDER_BLOCK). "
                       "ATTENZIONE ESPLICITA: NESSUNA di queste strategie ha oggi lo stato "
                       "EDGE_CONFIRMED - Phase 7.27 ha gia' trovato che la dominanza BUY "
                       "osservata e' largamente spiegata dal regime di mercato "
                       "(BUY_DOMINANCE_LARGELY_EXPLAINED_BY_MARKET_REGIME). Questa "
                       "opportunity NON E' AZIONABILE oggi - inclusa solo per dimostrare che "
                       "il framework la classifica correttamente come rischiosa nonostante "
                       "punteggi di automazione/ricorrenza attraenti.",
            category="PRODUCT", status="IDEA",
            dimensions={"time_to_cash": "SHORT_LT_1M", "capital_required": "NONE",
                      "sales_difficulty": "HIGH", "margin": "HIGH", "recurrence": "SUBSCRIPTION",
                      "automation_level": "FULLY_AUTOMATED", "skills_available": "FULLY_AVAILABLE",
                      "premium_tool_dependency": "NONE", "strategic_reuse": "PARTIAL",
                      "risk": "VERY_HIGH", "human_time_required": "MINIMAL"},
            technical_criteria={"novelty": "LOW", "infrastructure_leverage": "NONE",
                              "complexity_interest": "LOW", "long_term_strategic_value": "LOW"},
            technical_rationale="Non fa avanzare l'infrastruttura di ricerca/orchestrazione - "
                               "e' puro sfruttamento commerciale di un risultato che oggi "
                               "NON esiste ancora (nessun edge confermato).",
            funding_rationale="Punteggio funding ALTO per automazione/ricorrenza/tempo umano "
                             "minimo, MA risk=VERY_HIGH abbassa il punteggio e la "
                             "descrizione dichiara esplicitamente che nessuna strategia "
                             "sottostante ha oggi un edge confermato.",
            required_capabilities=["orchestrator", "research", "payments", "messaging"],
            evidence_confidence="LOW", legal_or_policy_risk_flag=True,
            # ^ vendere segnali di trading e' un'attivita' regolamentata in molte giurisdizioni
            # (consulenza finanziaria) - flag esplicito, coerente con l'assenza di edge
            # confermato: BLOCKED_BY_LEGAL_OR_POLICY_RISK ha precedenza su qualunque score.
            next_cheapest_validation_step={
                "description": "NON PROCEDERE fino a quando almeno una strategia raggiunge "
                              "EDGE_CONFIRMED nella pipeline Phase 7 - il prossimo passo reale "
                              "e' quello, non un test di mercato.",
                "estimated_cost": "NONE", "reversibility": "FULLY_REVERSIBLE", "speed": "MONTHS",
                "informational_value": "HIGH"},
            **_COMMON),
    ]
    opportunities = opportunities + _build_initial_hypothesis_opportunities()
    return {"schema_version": 1,
           "dataset_label": "PROVISIONAL_COMBINED_SET_NEXUS_TASK_0005_AND_0006",
           "opportunities": opportunities}


def main():
    payload = build()
    doc = wrap_with_provenance(payload, script=os.path.abspath(__file__))
    out_path = os.path.join(FUNDING_DIR, "example_instances", "opportunities_v1.json")
    save_json(out_path, doc)
    print(f"Scritto {out_path} ({len(payload['opportunities'])} opportunities)")


if __name__ == "__main__":
    main()
