#!/usr/bin/env python3
"""Phase 7.2 sec.21-22/28 - Applica research_priority_scoring_rule_v1.json
(congelata PRIMA di leggere questo output) a ogni sequence di
market_sequence_registry_v1.json. OGNI componente e' derivata
MECCANICAMENTE da campi GIA' registrati nei file precedenti (nessun
punteggio scelto a mano guardando quanto una sequenza 'sembra
promettente') - questo e' precisamente il vincolo anti-selection (sec.22)."""
import json
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", ".."))
PHASE72_DIR = os.path.join(ROOT, "server", "research_scripts", "phase7", "phase7_2")
sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase6_6"))
from canonical_utils import wrap_with_provenance, save_json  # noqa: E402

EXISTING_DETECTOR_MECHANISMS = {"MECH-06", "MECH-07", "MECH-08", "MECH-18", "MECH-19", "MECH-20"}
QUALITY_ORDER = {"Q0": 0, "Q1": 1, "Q2": 2, "Q3": 3, "Q4": 4}
RISK_ORDER = {"LOW": 0, "MEDIUM": 1, "HIGH": 2, "UNKNOWN": 2}


def load(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def score_sequence(seq, claim_by_id, diversity_by_mech):
    falsifiability = 2 if seq.get("falsification_definition") else 0

    obs = seq["causal_observability_status"]
    impl = seq["implementation_status"]
    if obs == "OBSERVABLE_AT_DECISION_TIME" and impl == "READY_FOR_FORMALIZATION":
        causal_measurability = 2
    elif obs == "OBSERVABLE_AT_DECISION_TIME" and impl == "NEEDS_ADDITIONAL_SPECIFICATION":
        causal_measurability = 1
    else:
        causal_measurability = 0

    implementation_clarity = {"READY_FOR_FORMALIZATION": 2, "NEEDS_ADDITIONAL_SPECIFICATION": 1,
                               "NOT_IMPLEMENTABLE_AS_DESCRIBED": 0}[impl]

    if seq["mechanism_id"] in EXISTING_DETECTOR_MECHANISMS:
        sample_availability = 2  # firing rate NORMAL noto da event_detector_health_v1.json (Phase 7.0B)
    elif impl == "READY_FOR_FORMALIZATION":
        sample_availability = 1
    else:
        sample_availability = 0

    distinctiveness = {"NOVEL": 2, "RELATED_TO_PREVIOUS_FAILURE": 1, "DIRECT_REPEAT_OF_FAILED_IDEA": 0}[seq["failure_memory_relation"]]

    n_cat = diversity_by_mech.get(seq["mechanism_id"], 0)
    source_diversity = 2 if n_cat >= 3 else (1 if n_cat == 2 else 0)

    qualities = [QUALITY_ORDER.get(claim_by_id[cid]["evidence_quality"], 0) for cid in seq["source_claim_ids"] if cid in claim_by_id]
    best_quality = max(qualities) if qualities else 0
    evidence_transparency = 2 if best_quality >= 3 else (1 if best_quality == 2 else 0)

    risks = [RISK_ORDER.get(claim_by_id[cid]["parameter_overfit_risk"], 2) for cid in seq["source_claim_ids"] if cid in claim_by_id]
    best_risk = min(risks) if risks else 2
    parameter_count_penalty = 2 if best_risk == 0 else (1 if best_risk == 1 else 0)

    if impl == "NOT_IMPLEMENTABLE_AS_DESCRIBED":
        execution_feasibility = 0
    elif "note_gap" in seq:
        execution_feasibility = 1
    else:
        execution_feasibility = 2

    components = {
        "falsifiability": falsifiability, "causal_measurability": causal_measurability,
        "implementation_clarity": implementation_clarity, "sample_availability_estimate": sample_availability,
        "distinctiveness_from_failed_mechanisms": distinctiveness, "source_diversity": source_diversity,
        "external_evidence_transparency": evidence_transparency, "parameter_count_penalty": parameter_count_penalty,
        "execution_feasibility": execution_feasibility,
    }
    total = sum(components.values())
    tier = "HIGH_RESEARCH_PRIORITY" if total >= 13 else ("MEDIUM_RESEARCH_PRIORITY" if total >= 8 else "LOW_RESEARCH_PRIORITY")
    return components, total, tier


def main():
    corpus = load(os.path.join(PHASE72_DIR, "external_hypothesis_corpus_v1.json"))["payload"]
    sequences = load(os.path.join(PHASE72_DIR, "market_sequence_registry_v1.json"))["sequences"]
    diversity = load(os.path.join(PHASE72_DIR, "source_diversity_matrix_v1.json"))["payload"]

    claim_by_id = {c["claim_id"]: c for c in corpus["claims"]}
    diversity_by_mech = {r["mechanism_id"]: r["n_categories_with_support"] for r in diversity["rows"]}

    scored = []
    for seq in sequences:
        components, total, tier = score_sequence(seq, claim_by_id, diversity_by_mech)
        scored.append({
            "sequence_id": seq["sequence_id"], "mechanism_id": seq["mechanism_id"],
            "components": components, "total_score": total, "tier": tier,
            "failure_memory_relation": seq["failure_memory_relation"],
            "n_source_claims": len(seq["source_claim_ids"]),
        })

    # tie-break deterministico: source_diversity desc, poi distinctiveness desc, poi sequence_id asc
    scored.sort(key=lambda r: (-r["total_score"], -r["components"]["source_diversity"],
                                -r["components"]["distinctiveness_from_failed_mechanisms"], r["sequence_id"]))

    for r in scored:
        seq = next(s for s in sequences if s["sequence_id"] == r["sequence_id"])
        r["mechanism_name"] = seq_name = next(m for m in load(os.path.join(PHASE72_DIR, "market_mechanism_registry_v1.json"))["payload"]["mechanisms"] if m["mechanism_id"] == seq["mechanism_id"])["name"]
        r["description"] = f"{seq['event_a']} -> {seq.get('event_b_optional') or '(esito diretto)'}"
        r["source_support_count"] = r["n_source_claims"]
        r["source_diversity_categories"] = diversity_by_mech.get(seq["mechanism_id"], 0)
        r["complexity"] = len(seq["initial_state_conditions"]) + len(seq["transition_conditions"])
        r["estimated_event_frequency"] = "NORMAL (detector Phase 5 esistente)" if seq["mechanism_id"] in EXISTING_DETECTOR_MECHANISMS else "DA STIMARE"
        r["causal_safety"] = seq["causal_observability_status"]
        r["implementation_difficulty"] = seq["implementation_status"]
        r["priority_reason"] = f"Punteggio totale {r['total_score']}/18 ({r['tier']}) - componenti: {r['components']}"

    high = [r for r in scored if r["tier"] == "HIGH_RESEARCH_PRIORITY"]
    shortlist = scored[:20]  # comunque limitato a 20 per costruzione (sec.28), anche se meno di 20 fossero HIGH

    payload = {
        "scoring_rule_ref": "research_priority_scoring_rule_v1.json (congelata prima di questo output)",
        "n_sequences_scored": len(scored),
        "n_high_priority": len(high),
        "all_scores": scored,
        "shortlist_phase7_3": shortlist,
        "explicit_ceiling_reminder": "Nessuna voce qui e' un PROMISING_EDGE - HIGH_RESEARCH_PRIORITY significa solo 'proprieta' ex-ante favorevoli alla ricerca', nessun numero calcolato su dati NEXUS in questa fase.",
    }
    save_json(os.path.join(PHASE72_DIR, "research_priority_queue_v1.json"), wrap_with_provenance(payload, "phase7/phase7_2/build_priority_queue.py"))

    print(f"n_sequences_scored={len(scored)} n_high_priority={len(high)}")
    for r in scored:
        print(f"  {r['sequence_id']:10s} {r['mechanism_name']:40s} score={r['total_score']:2d} tier={r['tier']}")


if __name__ == "__main__":
    main()
