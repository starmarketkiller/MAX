#!/usr/bin/env python3
"""NEXUS TASK #0005 - costruisce OPPORTUNITY_PRIORITY_QUEUE_V1: due
classifiche SEPARATE (technical/funding) + una vista affiancata - MAI un
unico punteggio fuso. 'funding_can_finance_technical' e' popolato SOLO
tramite dichiarazioni esplicite qui sotto (mai inferito automaticamente da
una correlazione statistica fra punteggi - sarebbe un'interpretazione non
richiesta dai dati)."""
import os
import sys
from datetime import datetime, timezone

FUNDING_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(FUNDING_DIR, "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase6_6"))
from canonical_utils import wrap_with_provenance, save_json, load_json  # noqa: E402

# Dichiarazione ESPLICITA (non calcolata) di quali opportunity ad alta funding_priority
# potrebbero finanziare quali opportunity ad alta technical_priority - questo e' un
# giudizio di design, non un'inferenza automatica dai punteggi.
FUNDING_CAN_FINANCE_TECHNICAL = {
    "OPP_DATA_PROVENANCE_COMPLIANCE_TOOL": ["OPP_LOCAL_MODEL_ORCHESTRATOR_PRODUCT"],
    "OPP_MT5_STRATEGY_SIGNAL_SUBSCRIPTION": None,  # esplicitamente NESSUNA finanziabilita'
                                                   # dichiarata - l'opportunity stessa non e'
                                                   # azionabile oggi (nessun edge confermato)
}


def build():
    opportunities_doc = load_json(os.path.join(FUNDING_DIR, "example_instances",
                                              "opportunities_v1.json"))
    opportunities = opportunities_doc["payload"]["opportunities"]

    ranked_technical = sorted(
        [{"opportunity_id": o["opportunity_id"], "title": o["title"],
         "technical_priority_score": o["technical_priority"]["score"]} for o in opportunities],
        key=lambda x: -x["technical_priority_score"])
    ranked_funding = sorted(
        [{"opportunity_id": o["opportunity_id"], "title": o["title"],
         "funding_priority_score": o["funding_priority"]["score"]} for o in opportunities],
        key=lambda x: -x["funding_priority_score"])

    technical_rank_by_id = {o["opportunity_id"]: i + 1 for i, o in enumerate(ranked_technical)}
    funding_rank_by_id = {o["opportunity_id"]: i + 1 for i, o in enumerate(ranked_funding)}

    combined = []
    for o in opportunities:
        oid = o["opportunity_id"]
        combined.append({
            "opportunity_id": oid, "title": o["title"],
            "technical_priority_score": o["technical_priority"]["score"],
            "funding_priority_score": o["funding_priority"]["score"],
            "technical_rank": technical_rank_by_id[oid], "funding_rank": funding_rank_by_id[oid],
            "funding_can_finance_technical": FUNDING_CAN_FINANCE_TECHNICAL.get(oid),
        })
    combined.sort(key=lambda x: x["funding_rank"])

    payload = {
        "schema_version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "scoring_methodology_note": "TECHNICAL_PRIORITY e FUNDING_PRIORITY sono assi "
                                   "SEPARATI per costruzione (server/funding_v1/"
                                   "opportunity_scoring.py, pesi e punti espliciti, "
                                   "nessuna black-box) - NON un unico punteggio fuso. "
                                   "'funding_can_finance_technical' e' dichiarato "
                                   "esplicitamente, mai inferito da una correlazione fra "
                                   "punteggi.",
        "ranked_by_technical_priority": ranked_technical,
        "ranked_by_funding_priority": ranked_funding,
        "combined_view": combined,
        "opportunities_evaluated": len(opportunities),
    }
    return payload


def main():
    payload = build()
    doc = wrap_with_provenance(payload, script=os.path.abspath(__file__))
    out_path = os.path.join(FUNDING_DIR, "opportunity_priority_queue_v1.json")
    save_json(out_path, doc)
    print(f"Scritto {out_path}")
    print("Top 3 per FUNDING_PRIORITY:")
    for o in payload["ranked_by_funding_priority"][:3]:
        print(f"  {o['funding_priority_score']:.1f} - {o['title']}")
    print("Top 3 per TECHNICAL_PRIORITY:")
    for o in payload["ranked_by_technical_priority"][:3]:
        print(f"  {o['technical_priority_score']:.1f} - {o['title']}")


if __name__ == "__main__":
    main()
