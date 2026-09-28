#!/usr/bin/env python3
"""NEXUS TASK #0005 - Funding Priority & Opportunity Framework V1.

Motore di scoring DETERMINISTICO (nessun LLM, nessuna stima di mercato reale
- ogni punteggio e' derivato da un dizionario di punti PER LIVELLO ENUM,
esplicitamente dichiarato qui, mai una black-box). Separa per costruzione:

- FUNDING_PRIORITY: quanto un'opportunity puo' generare cassa PRESTO per
  autofinanziare il resto (le 11 dimensioni dichiarate dall'utente).
- TECHNICAL_PRIORITY: quanto e' interessante/strategicamente rilevante dal
  punto di vista tecnico/infrastrutturale NEXUS - un asse VOLUTAMENTE
  separato, mai fuso in un unico numero (obiettivo esplicito: Jarvis deve
  poter dire 'X e' interessante ma Y genera cassa prima e finanzia X', non
  appiattire le due cose).

Risk/premium boundary: nessuna di queste dimensioni e' derivata da dati di
mercato reali automaticamente raccolti - sono stime DICHIARATE (vedi
provenance.dimension_estimation_method in ogni OPPORTUNITY_V1), mai
inventate come se fossero fatti di mercato verificati."""

# --- FUNDING_PRIORITY: punti per livello enum (0-100) + peso per dimensione ---
# Pesi sommano a 1.0 - documentati esplicitamente, non un tuning arbitrario:
# time_to_cash pesa piu' di tutte le altre (0.15) perche' l'obiettivo dichiarato
# e' generare cassa PRESTO per autofinanziare il resto - le altre 10 dimensioni
# pesano in modo piu' uniforme (0.05-0.10) a seconda di quanto direttamente
# incidono sulla VELOCITA'/SOSTENIBILITA' della cassa generata.
FUNDING_DIMENSION_POINTS = {
    "time_to_cash": {"IMMEDIATE_LT_1W": 100, "SHORT_LT_1M": 75, "MEDIUM_1_3M": 50,
                    "LONG_3_6M": 25, "VERY_LONG_GT_6M": 0},
    "capital_required": {"NONE": 100, "LOW": 70, "MEDIUM": 35, "HIGH": 0},
    "sales_difficulty": {"LOW": 100, "MEDIUM": 65, "HIGH": 30, "VERY_HIGH": 0},
    "margin": {"VERY_HIGH": 100, "HIGH": 70, "MEDIUM": 40, "LOW": 10},
    "recurrence": {"SUBSCRIPTION": 100, "RECURRING": 75, "OCCASIONAL": 40, "ONE_OFF": 15},
    "automation_level": {"FULLY_AUTOMATED": 100, "PARTIALLY_AUTOMATED": 55, "MANUAL": 15},
    "skills_available": {"FULLY_AVAILABLE": 100, "PARTIAL": 65, "NEEDS_LEARNING": 30,
                        "NEEDS_HIRING": 0},
    "premium_tool_dependency": {"NONE": 100, "LOW_COST": 70, "MODERATE_COST": 35, "HIGH_COST": 0},
    "strategic_reuse": {"CORE_REUSE": 100, "HIGH": 75, "PARTIAL": 40, "NONE": 10},
    "risk": {"LOW": 100, "MEDIUM": 60, "HIGH": 25, "VERY_HIGH": 0},
    "human_time_required": {"MINIMAL": 100, "PART_TIME": 65, "SIGNIFICANT": 30, "FULL_TIME": 0},
}
FUNDING_DIMENSION_WEIGHTS = {
    "time_to_cash": 0.15, "capital_required": 0.10, "sales_difficulty": 0.10, "margin": 0.10,
    "recurrence": 0.10, "automation_level": 0.10, "skills_available": 0.10,
    "premium_tool_dependency": 0.05, "strategic_reuse": 0.10, "risk": 0.05,
    "human_time_required": 0.05,
}
assert abs(sum(FUNDING_DIMENSION_WEIGHTS.values()) - 1.0) < 1e-9, "pesi funding devono sommare a 1.0"

# --- TECHNICAL_PRIORITY: 4 criteri, pesi documentati - infrastructure_leverage pesa di
# piu' (0.35) perche' e' il criterio piu' direttamente legato all'obiettivo dichiarato
# (far avanzare le capacita' core di NEXUS, non solo essere "interessante").
TECHNICAL_CRITERIA_POINTS = {
    "novelty": {"LOW": 20, "MEDIUM": 60, "HIGH": 100},
    "infrastructure_leverage": {"NONE": 10, "PARTIAL": 55, "HIGH": 100},
    "complexity_interest": {"LOW": 30, "MEDIUM": 65, "HIGH": 100},
    "long_term_strategic_value": {"LOW": 20, "MEDIUM": 60, "HIGH": 100},
}
TECHNICAL_CRITERIA_WEIGHTS = {
    "novelty": 0.25, "infrastructure_leverage": 0.35, "complexity_interest": 0.15,
    "long_term_strategic_value": 0.25,
}
assert abs(sum(TECHNICAL_CRITERIA_WEIGHTS.values()) - 1.0) < 1e-9, "pesi technical devono sommare a 1.0"


def score_funding_priority(dimensions):
    """dimensions: dict con le 11 chiavi di OPPORTUNITY_V1.dimensions.
    Ritorna (score 0-100, weighted_breakdown dict) - MAI un numero opaco."""
    breakdown = {}
    for dim, value in dimensions.items():
        points = FUNDING_DIMENSION_POINTS[dim][value]
        weight = FUNDING_DIMENSION_WEIGHTS[dim]
        breakdown[dim] = round(points * weight, 4)
    score = round(sum(breakdown.values()), 2)
    return score, breakdown


def score_technical_priority(criteria):
    """criteria: dict con le 4 chiavi di OPPORTUNITY_V1.technical_priority.criteria."""
    breakdown = {}
    for crit, value in criteria.items():
        points = TECHNICAL_CRITERIA_POINTS[crit][value]
        weight = TECHNICAL_CRITERIA_WEIGHTS[crit]
        breakdown[crit] = round(points * weight, 4)
    score = round(sum(breakdown.values()), 2)
    return score, breakdown
