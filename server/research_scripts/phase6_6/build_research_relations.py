#!/usr/bin/env python3
"""Phase 6.6 sec.7 - Evidence Relation Model: formalizza le relazioni fra
entita' di ricerca come archi tipizzati, utile per un futuro Explain
Path / knowledge graph.

Tipi di relazione: TESTS, SUPPORTS, LIMITS, REFUTES, AUDITS,
DERIVED_FROM, SUPERSEDES.

Vincolo esplicito (sec.7 della richiesta): Phase 6.5 deve AUDITARE
Phase 6, MAI sostituirla - per questo l'arco fra i due esperimenti e'
tipizzato AUDITS, non SUPERSEDES (che non compare mai in questo file
riferito a H006, deliberatamente)."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from canonical_utils import wrap_with_provenance, save_json  # noqa: E402

PHASE66_DIR = os.path.dirname(os.path.abspath(__file__))

RELATION_TYPES = ["TESTS", "SUPPORTS", "LIMITS", "REFUTES", "AUDITS", "DERIVED_FROM", "SUPERSEDES"]

EDGES = [
    {"from": "EXP-P6-001-H006-TRUE-HOLDOUT", "relation": "TESTS", "to": "H006_LIQUIDITY_SWEEP_RECLAIM_TRUE_HOLDOUT"},
    {"from": "H006_LIQUIDITY_SWEEP_RECLAIM_TRUE_HOLDOUT", "relation": "DERIVED_FROM", "to": "H004_EVENT_RECLAIM"},
    {"from": "EVD-H006-PRIMARY-001", "relation": "TESTS", "to": "H006_LIQUIDITY_SWEEP_RECLAIM_TRUE_HOLDOUT"},
    {"from": "EVD-H006-AUDIT-001", "relation": "AUDITS", "to": "EVD-H006-PRIMARY-001"},
    {"from": "EXP-P6.5-001-H006-DEPENDENCE-AUDIT", "relation": "AUDITS", "to": "EXP-P6-001-H006-TRUE-HOLDOUT"},
    {"from": "EVD-H006-AUDIT-001", "relation": "LIMITS", "to": "EVD-H006-PRIMARY-001", "note": "l'audit non refuta ne' sostituisce il risultato primario - ne segnala i limiti di dipendenza/campionamento"},
    {"from": "SELL_SWEEP_RECLAIM_ASYMMETRY", "relation": "DERIVED_FROM", "to": "EVD-H006-PRIMARY-001"},
    {"from": "SELL_SWEEP_RECLAIM_ASYMMETRY", "relation": "DERIVED_FROM", "to": "EVD-H006-AUDIT-001"},
    {"from": "H006_LIQUIDITY_SWEEP_RECLAIM_TRUE_HOLDOUT", "relation": "LIMITS", "to": "H004_EVENT_RECLAIM", "note": "il true holdout ridimensiona (non refuta del tutto) l'evidenza originale H004: DeltaP crolla da +0.24/+0.30 a +0.057"},
    {"from": "DEPENDENCE_AUDIT_PASS_GATE", "relation": "TESTS", "to": "EVD-H006-AUDIT-001"},
    {"from": "DEPENDENCE_AUDIT_PASS_GATE", "relation": "REFUTES", "to": "H006_PRE_PHASE6.5_RECORD", "note": "il record originale di Phase 6 (senza campi di dipendenza) fallisce il gate se ri-valutato con lo schema v2 - non e' un giudizio sul merito del risultato, solo sulla completezza della strumentazione"},
]


def build():
    return {
        "schema_version": 1,
        "relation_types": RELATION_TYPES,
        "invariants": [
            "Phase6.5 AUDITS Phase6 - MAI SUPERSEDES, per costruzione di questo file (nessun arco SUPERSEDES verso EVD-H006-PRIMARY-001 esiste qui)",
            "Nessun arco SUPPORTS punta a H006 con peso di conferma - il verdetto e' BORDERLINE, non un supporto pieno",
            "SELL_SWEEP_RECLAIM_ASYMMETRY e' sempre DERIVED_FROM, mai TESTS o SUPPORTS un'ipotesi propria (non ne ha una)",
        ],
        "edges": EDGES,
    }


if __name__ == "__main__":
    relations = build()
    wrapped = wrap_with_provenance(relations, script="server/research_scripts/phase6_6/build_research_relations.py")
    out_path = os.path.join(PHASE66_DIR, "research_relations_v1.json")
    save_json(out_path, wrapped)
    print(f"canonical_sha256: {wrapped['canonical_sha256']}")
    print(f"written: {out_path}")
