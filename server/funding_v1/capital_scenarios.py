#!/usr/bin/env python3
"""NEXUS TASK #0006 - Capital Scenarios V1: la STESSA opportunity ottiene
una funding_priority diversa a seconda del capitale disponibile - nessun
capitale personale dell'utente e' hardcoded, sono 4 scenari GENERICI.

Regola deterministica: se dimensions.capital_required eccede il tetto
dello scenario, lo scenario e' INFEASIBLE per quella opportunity
(adjusted_funding_priority=0). Se e' alla portata, il contributo della
dimensione capital_required al punteggio pesato viene portato al massimo
(100 punti) per quello scenario - rappresenta il fatto che, a quel livello
di capitale, il capitale NON e' piu' un fattore limitante per QUELLA
opportunity - le altre 10 dimensioni restano invariate."""
import sys
import os

FUNDING_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, FUNDING_DIR)
from opportunity_scoring import FUNDING_DIMENSION_WEIGHTS  # noqa: E402

CAPITAL_LEVELS_ORDER = ["NONE", "LOW", "MEDIUM", "HIGH"]
SCENARIO_CEILING = {
    "BOOTSTRAP_0_100": "NONE",
    "BOOTSTRAP_100_500": "LOW",
    "BOOTSTRAP_500_2000": "MEDIUM",
    "GROWTH_2000_PLUS": "HIGH",
}


def compute_capital_scenarios(dimensions, base_funding_breakdown):
    """dimensions: OPPORTUNITY_V1.dimensions. base_funding_breakdown: il
    weighted_breakdown GIA' calcolato da score_funding_priority (riusato,
    non ricalcolato da zero, per garantire coerenza con lo score base)."""
    capital_required = dimensions["capital_required"]
    capital_index = CAPITAL_LEVELS_ORDER.index(capital_required)
    capital_weight = FUNDING_DIMENSION_WEIGHTS["capital_required"]

    results = {}
    for scenario, ceiling in SCENARIO_CEILING.items():
        ceiling_index = CAPITAL_LEVELS_ORDER.index(ceiling)
        feasible = capital_index <= ceiling_index
        if not feasible:
            results[scenario] = {
                "feasible": False, "adjusted_funding_priority": 0.0,
                "note": f"capital_required='{capital_required}' eccede il tetto di questo "
                       f"scenario ('{ceiling}') - BLOCKED_BY_CAPITAL",
            }
            continue
        # Il capitale non e' piu' un fattore limitante a questo scenario - il contributo
        # della dimensione capital_required viene portato al massimo, le altre 10 restano
        # come nello score base.
        adjusted_breakdown = dict(base_funding_breakdown)
        adjusted_breakdown["capital_required"] = round(100 * capital_weight, 4)
        adjusted_score = round(sum(adjusted_breakdown.values()), 2)
        results[scenario] = {
            "feasible": True, "adjusted_funding_priority": adjusted_score,
            "note": f"capitale sufficiente a questo scenario - capital_required non e' piu' "
                   "un fattore limitante, altre 10 dimensioni invariate",
        }
    return results
