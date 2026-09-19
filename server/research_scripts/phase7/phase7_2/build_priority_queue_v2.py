#!/usr/bin/env python3
"""Phase 7.2B sec.5 - Rigenera DETERMINISTICAMENTE la priority queue con
research_priority_scoring_rule_v2.json (gia' congelata). Ogni componente
derivata meccanicamente da campi gia' registrati - nessun punteggio
scelto a mano. Confronta v1 vs v2 per ogni sequence."""
import json
import os
import sys
from collections import defaultdict

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


def build_source_to_cluster(evidence_clusters, all_source_ids):
    source_to_cluster = {sid: sid for sid in all_source_ids}  # default: singleton cluster = se stesso
    for cl in evidence_clusters["merged_clusters"]:
        canonical = cl["member_source_ids"][0]
        for sid in cl["member_source_ids"]:
            source_to_cluster[sid] = canonical
    return source_to_cluster


def score_sequence_v2(seq, claim_by_id, diversity_by_mech, source_to_cluster):
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
        sample_availability = 2
    elif impl == "READY_FOR_FORMALIZATION":
        sample_availability = 1
    else:
        sample_availability = 0

    distinctiveness = {"NOVEL": 2, "RELATED_TO_PREVIOUS_FAILURE": 1, "DIRECT_REPEAT_OF_FAILED_IDEA": 0}[seq["failure_memory_relation"]]

    n_cat = diversity_by_mech.get(seq["mechanism_id"], 0)
    source_diversity = 2 if n_cat >= 3 else (1 if n_cat == 2 else 0)

    # --- external_evidence_transparency v2: conta CLUSTER indipendenti a Q3/Q4 ---
    relevant_claims = [claim_by_id[cid] for cid in seq["source_claim_ids"] if cid in claim_by_id]
    q3plus_clusters = set()
    for c in relevant_claims:
        if QUALITY_ORDER.get(c["evidence_quality"], 0) >= 3:
            q3plus_clusters.add(source_to_cluster.get(c["source_id"], c["source_id"]))
    n_independent_q3plus = len(q3plus_clusters)
    evidence_transparency_v2 = 2 if n_independent_q3plus >= 2 else (1 if n_independent_q3plus == 1 else 0)

    risks = [RISK_ORDER.get(c["parameter_overfit_risk"], 2) for c in relevant_claims]
    best_risk = min(risks) if risks else 2
    parameter_count_penalty = 2 if best_risk == 0 else (1 if best_risk == 1 else 0)

    if impl == "NOT_IMPLEMENTABLE_AS_DESCRIBED":
        execution_feasibility = 0
    elif "note_gap" in seq:
        execution_feasibility = 1
    else:
        execution_feasibility = 2

    # --- nuovo componente: hindsight_awareness ---
    n_high_hindsight = sum(1 for c in relevant_claims if c["hindsight_risk"] == "HIGH")
    frac_high = (n_high_hindsight / len(relevant_claims)) if relevant_claims else 0.0
    hindsight_awareness = 2 if frac_high == 0 else (1 if frac_high < 0.5 else 0)

    components = {
        "falsifiability": falsifiability, "causal_measurability": causal_measurability,
        "implementation_clarity": implementation_clarity, "sample_availability_estimate": sample_availability,
        "distinctiveness_from_failed_mechanisms": distinctiveness, "source_diversity": source_diversity,
        "external_evidence_transparency_v2": evidence_transparency_v2,
        "parameter_count_penalty": parameter_count_penalty, "execution_feasibility": execution_feasibility,
        "hindsight_awareness": hindsight_awareness,
    }
    total = sum(components.values())
    tier = "HIGH_RESEARCH_PRIORITY" if total >= 15 else ("MEDIUM_RESEARCH_PRIORITY" if total >= 9 else "LOW_RESEARCH_PRIORITY")
    return components, total, tier, n_independent_q3plus, frac_high


def main():
    corpus = load(os.path.join(PHASE72_DIR, "external_hypothesis_corpus_v1.json"))["payload"]
    seq_doc = load(os.path.join(PHASE72_DIR, "market_sequence_registry_v1.json"))
    sequences = seq_doc["sequences"]
    diversity = load(os.path.join(PHASE72_DIR, "source_diversity_matrix_v1.json"))["payload"]
    evidence_clusters = load(os.path.join(PHASE72_DIR, "evidence_cluster_registry_v1.json"))
    mechanisms = load(os.path.join(PHASE72_DIR, "market_mechanism_registry_v1.json"))["payload"]["mechanisms"]
    v1_queue = load(os.path.join(PHASE72_DIR, "research_priority_queue_v1.json"))["payload"]

    claim_by_id = {c["claim_id"]: c for c in corpus["claims"]}
    diversity_by_mech = {r["mechanism_id"]: r["n_categories_with_support"] for r in diversity["rows"]}
    all_source_ids = {c["source_id"] for c in corpus["claims"]}
    source_to_cluster = build_source_to_cluster(evidence_clusters, all_source_ids)
    v1_by_id = {r["sequence_id"]: r for r in v1_queue["all_scores"]}
    mech_name_by_id = {m["mechanism_id"]: m["name"] for m in mechanisms}

    scored = []
    for seq in sequences:
        components, total, tier, n_clusters, frac_hindsight = score_sequence_v2(seq, claim_by_id, diversity_by_mech, source_to_cluster)
        v1_entry = v1_by_id[seq["sequence_id"]]
        old_score, old_tier = v1_entry["total_score"], v1_entry["tier"]

        reasons = []
        if components["external_evidence_transparency_v2"] != (2 if v1_entry["components"]["external_evidence_transparency"] == 2 else v1_entry["components"]["external_evidence_transparency"]):
            pass  # confronto diretto sotto
        old_transp = v1_entry["components"]["external_evidence_transparency"]
        new_transp = components["external_evidence_transparency_v2"]
        if new_transp != old_transp:
            reasons.append(f"external_evidence_transparency {old_transp}->{new_transp} ({n_clusters} cluster indipendenti Q3/Q4, non piu' conteggio grezzo di fonti)")
        if components["hindsight_awareness"] < 2:
            reasons.append(f"nuovo componente hindsight_awareness={components['hindsight_awareness']} ({frac_hindsight:.0%} dei claim di supporto ad alto hindsight_risk)")
        if seq["implementation_status"] != "READY_FOR_FORMALIZATION" and v1_entry["components"]["implementation_clarity"] == 2:
            reasons.append(f"implementation_status degradato a {seq['implementation_status']} post semantic-leakage-guard (Integrity Patch sec.2)")
        if not reasons:
            reasons.append("nessun cambiamento sostanziale nei componenti rilevanti")

        scored.append({
            "sequence_id": seq["sequence_id"], "mechanism_id": seq["mechanism_id"],
            "mechanism_name": mech_name_by_id[seq["mechanism_id"]],
            "components": components, "total_score": total, "tier": tier,
            "n_independent_q3plus_clusters": n_clusters, "frac_high_hindsight": round(frac_hindsight, 3),
            "old_score": old_score, "old_tier": old_tier,
            "score_delta": total - old_score, "tier_changed": tier != old_tier,
            "reason_for_change": "; ".join(reasons),
        })

    scored.sort(key=lambda r: (-r["total_score"], -r["components"]["source_diversity"],
                                -r["components"]["distinctiveness_from_failed_mechanisms"], r["sequence_id"]))

    high = [r for r in scored if r["tier"] == "HIGH_RESEARCH_PRIORITY"]
    old_high_ids = {r["sequence_id"] for r in v1_queue["all_scores"] if r["tier"] == "HIGH_RESEARCH_PRIORITY"}
    new_high_ids = {r["sequence_id"] for r in high}

    payload = {
        "scoring_rule_ref": "research_priority_scoring_rule_v2.json",
        "n_sequences_scored": len(scored), "n_high_priority": len(high),
        "all_scores": scored,
        "shortlist_phase7_3": scored,
        "high_priority_added_vs_v1": sorted(new_high_ids - old_high_ids),
        "high_priority_removed_vs_v1": sorted(old_high_ids - new_high_ids),
        "high_priority_unchanged": sorted(new_high_ids & old_high_ids),
        "explicit_ceiling_reminder": "Nessuna voce qui e' un PROMISING_EDGE.",
    }
    save_json(os.path.join(PHASE72_DIR, "research_priority_queue_v2.json"), wrap_with_provenance(payload, "phase7/phase7_2/build_priority_queue_v2.py"))

    print(f"n_high_priority_v2={len(high)} (v1 era {len(old_high_ids)})")
    print(f"Aggiunte a HIGH: {sorted(new_high_ids - old_high_ids)}")
    print(f"Rimosse da HIGH: {sorted(old_high_ids - new_high_ids)}")
    print(f"Invariate in HIGH: {sorted(new_high_ids & old_high_ids)}")
    print()
    for r in scored:
        marker = " <-- CAMBIO TIER" if r["tier_changed"] else ""
        print(f"  {r['sequence_id']:10s} {r['mechanism_name']:40s} v1={r['old_score']:2d}({r['old_tier'][:4]}) -> v2={r['total_score']:2d}({r['tier'][:4]}){marker}")


if __name__ == "__main__":
    main()
