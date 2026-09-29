#!/usr/bin/env python3
"""NEXUS TASK #0006 - Opportunity Brief V1 builder. La parte deterministica
(tutti i campi tranne short_voice_summary) e' un assemblaggio puro dei
campi gia' presenti nell'OPPORTUNITY_V1 sorgente - MAI un'interpretazione
nuova. short_voice_summary e' l'UNICO campo generativo (richiede
trasformazione da dati strutturati a frase naturale) - responsabilita' di
ministral-3:3b, verificato (vedi run_nexus_task_0006*.py)."""
from datetime import datetime, timezone


def build_brief_skeleton(opportunity, source_artifact, canonical_sha256):
    """Ritorna il brief COMPLETO tranne short_voice_summary (assente qui,
    aggiunto dal chiamante dopo la generazione via Ministral)."""
    why_now_parts = []
    fp = opportunity["funding_priority"]["score"]
    tp = opportunity["technical_priority"]["score"]
    if fp >= tp:
        why_now_parts.append(f"funding_priority ({fp}) supera technical_priority ({tp})")
    else:
        why_now_parts.append(f"technical_priority ({tp}) supera funding_priority ({fp})")
    why_now_parts.append(f"hard_gate={opportunity['hard_gate']}")
    why_now = " - ".join(why_now_parts)

    gate = opportunity["hard_gate"]
    main_blocker = None
    if gate.startswith("BLOCKED_BY_"):
        blockers = opportunity["capability_coverage"].get("blockers", [])
        main_blocker = blockers[0] if blockers else gate

    # capital_requirement: il piu' economico fra gli scenari FEASIBLE - se nessuno e'
    # feasible (non dovrebbe succedere dato che GROWTH_2000_PLUS ha sempre ceiling=HIGH),
    # ricade su GROWTH_2000_PLUS.
    scenario_order = ["BOOTSTRAP_0_100", "BOOTSTRAP_100_500", "BOOTSTRAP_500_2000",
                     "GROWTH_2000_PLUS"]
    capital_requirement = next(
        (s for s in scenario_order if opportunity["capital_scenario_priorities"][s]["feasible"]),
        "GROWTH_2000_PLUS")

    return {
        "opportunity_id": opportunity["opportunity_id"], "title": opportunity["title"],
        "why_now": why_now, "funding_priority": fp, "technical_priority": tp,
        "evidence_confidence": opportunity["evidence_confidence"],
        "priority_status": opportunity["priority_status"],
        "capital_requirement": capital_requirement,
        "capability_coverage_pct": opportunity["capability_coverage"][
            "existing_capability_coverage_pct"],
        "main_blocker": main_blocker,
        "next_cheapest_test": opportunity["next_cheapest_validation_step"]["description"],
        "approval_required": True,  # sempre True per costruzione - un brief non autorizza
                                    # mai da solo un'azione commerciale reale
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_opportunity_provenance": {"source_artifact": source_artifact,
                                         "canonical_sha256": canonical_sha256},
    }
