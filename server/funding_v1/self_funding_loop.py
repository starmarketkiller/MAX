#!/usr/bin/env python3
"""NEXUS TASK #0006 - Self-Funding Loop V1: struttura di ALLOCAZIONE
concettuale, MAI un forecast di revenue - nessun numero di previsione e'
permesso qui, solo categorie e una regola qualitativa di allocazione."""


def build_self_funding_loop():
    return {
        "schema_version": 1,
        "stages": ["OPPORTUNITY", "VALIDATION", "MVP", "FIRST_REVENUE", "RESERVE",
                 "REINVESTMENT", "INFRASTRUCTURE_UPGRADE", "NEW_CAPABILITY",
                 "HIGHER_VALUE_OPPORTUNITIES"],
        "allocation_rule_note": "Quando un'opportunity raggiunge FIRST_REVENUE, la cassa "
                               "generata si divide concettualmente in RESERVE (buffer di "
                               "sicurezza, priorita' finche' non e' costituito) e "
                               "REINVESTMENT (finanzia INFRASTRUCTURE_UPGRADE o direttamente "
                               "una NEW_CAPABILITY che sblocca HIGHER_VALUE_OPPORTUNITIES gia' "
                               "identificate nella priority queue con alto TECHNICAL_PRIORITY "
                               "ma basso FUNDING_PRIORITY) - la proporzione esatta NON e' "
                               "definita qui (sarebbe un numero inventato), va decisa "
                               "esplicitamente quando FIRST_REVENUE e' osservato per davvero.",
        "no_forecast_declaration": "Questo schema non contiene alcuna previsione di revenue, "
                                  "timeline o importo - e' una struttura di allocazione "
                                  "concettuale, popolata con numeri reali SOLO dopo che "
                                  "FIRST_REVENUE e' stato osservato per una specifica "
                                  "opportunity.",
    }
