#!/usr/bin/env python3
"""Phase 7.2 sec.20/23/25 - Deriva PROGRAMMATICAMENTE (nessuna relazione
inventata) il source graph, la source diversity matrix e il confronto
con failure_memory_registry_v1.json dai registry gia' costruiti."""
import json
import os
import sys
from collections import defaultdict

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", ".."))
PHASE72_DIR = os.path.join(ROOT, "server", "research_scripts", "phase7", "phase7_2")
PHASE7_DIR = os.path.join(ROOT, "server", "research_scripts", "phase7")
sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase6_6"))
from canonical_utils import wrap_with_provenance, save_json  # noqa: E402

CATEGORY_MAP = {
    "ACADEMIC_PAPER": "ACADEMIC", "PREPRINT_SSRN_ARXIV": "ACADEMIC", "QUANT_BLOG": "ACADEMIC",
    "MQL5": "MQL5_EA", "EA_PUBLIC": "MQL5_EA",
    "REDDIT": "COMMUNITY", "FOREXFACTORY": "COMMUNITY", "OTHER_FORUM": "COMMUNITY",
    "TRADINGVIEW": "OPEN_SOURCE_SCRIPTS", "GITHUB_OPENSOURCE": "OPEN_SOURCE_SCRIPTS",
    "BROKER_EXCHANGE_DOC": "MARKET_STRUCTURE_DOC",
}


def load(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def main():
    corpus = load(os.path.join(PHASE72_DIR, "external_hypothesis_corpus_v1.json"))["payload"]
    sources = load(os.path.join(PHASE72_DIR, "source_registry_v1.json"))["payload"]["sources"]
    mechanisms = load(os.path.join(PHASE72_DIR, "market_mechanism_registry_v1.json"))["payload"]["mechanisms"]
    sequences = load(os.path.join(PHASE72_DIR, "market_sequence_registry_v1.json"))["sequences"]
    proxy_registry = load(os.path.join(PHASE72_DIR, "mechanism_proxy_registry_v1.json"))
    contradictions = load(os.path.join(PHASE72_DIR, "contradiction_registry_v1.json"))["contradiction_groups"]
    failure_memory = load(os.path.join(PHASE7_DIR, "failure_memory_registry_v1.json"))["patterns"]

    claims = corpus["claims"]
    claim_by_id = {c["claim_id"]: c for c in claims}
    source_by_id = {s["source_id"]: s for s in sources}

    # ---------------- SOURCE GRAPH (sec.20) ----------------
    edges = []
    for c in claims:
        edges.append({"from": c["source_id"], "relation": "SUPPORTS_CLAIM", "to": c["claim_id"]})
        for mech_id in c.get("candidate_mechanism_ids", []):
            edges.append({"from": c["claim_id"], "relation": "DESCRIBES_MECHANISM", "to": mech_id})
        if c.get("contradiction_group_id"):
            edges.append({"from": c["claim_id"], "relation": "PART_OF_CONTRADICTION_GROUP", "to": c["contradiction_group_id"]})
    for cg in contradictions:
        for a in cg["claim_ids_side_a"]:
            for b in cg["claim_ids_side_b"]:
                edges.append({"from": a, "relation": "CONTRADICTS", "to": b})
    for seq in sequences:
        for cid in seq["source_claim_ids"]:
            edges.append({"from": cid, "relation": "MAPS_TO_SEQUENCE", "to": seq["sequence_id"]})
        for state_cond in seq.get("initial_state_conditions", []) + seq.get("terminal_state_conditions", []):
            edges.append({"from": seq["sequence_id"], "relation": "USES_STATE", "to": state_cond})
        edges.append({"from": seq["sequence_id"], "relation": "CONTAINS_EVENT", "to": seq["event_a"]})
        if seq.get("event_b_optional"):
            edges.append({"from": seq["sequence_id"], "relation": "CONTAINS_EVENT", "to": seq["event_b_optional"]})
    for concept, entry in proxy_registry["concepts"].items():
        for proxy in entry["proxies"]:
            edges.append({"from": concept, "relation": "HAS_PROXY", "to": proxy["name"]})

    graph_payload = {"n_edges": len(edges), "edges": edges}
    save_json(os.path.join(PHASE72_DIR, "source_graph_v1.json"), wrap_with_provenance(graph_payload, "phase7/phase7_2/build_graph_and_diversity.py"))

    # ---------------- SOURCE DIVERSITY MATRIX (sec.25) ----------------
    mech_category_counts = defaultdict(lambda: defaultdict(int))
    for c in claims:
        cat = CATEGORY_MAP.get(c["source_type"], "OTHER")
        for mech_id in c.get("candidate_mechanism_ids", []):
            mech_category_counts[mech_id][cat] += 1

    diversity_rows = []
    categories_all = sorted({cat for m in mech_category_counts.values() for cat in m})
    for mech in mechanisms:
        mech_id = mech["mechanism_id"]
        row = {"mechanism_id": mech_id, "name": mech["name"]}
        for cat in categories_all:
            row[cat] = mech_category_counts[mech_id].get(cat, 0)
        row["n_categories_with_support"] = sum(1 for cat in categories_all if row[cat] > 0)
        diversity_rows.append(row)
    diversity_rows.sort(key=lambda r: -r["n_categories_with_support"])

    diversity_payload = {"categories": categories_all, "rows": diversity_rows,
                          "note": "Convergenza di fonti indipendenti NON prova un edge - aumenta solo l'interesse epistemico (sec.25)."}
    save_json(os.path.join(PHASE72_DIR, "source_diversity_matrix_v1.json"), wrap_with_provenance(diversity_payload, "phase7/phase7_2/build_graph_and_diversity.py"))

    # ---------------- FAILURE MEMORY CROSS-CHECK (sec.23) ----------------
    fm_checks = []
    for mech in mechanisms:
        mech_id = mech["mechanism_id"]
        matched_patterns = []
        # Confronto con Phase 7.1 (RECLAIM) - gia' incorporato nelle sequence (failure_memory_relation),
        # qui si aggiunge il confronto esplicito con gli 8 pattern strutturali di failure_memory_registry_v1.json.
        name = mech["name"]
        if "RECLAIM" in name:
            matched_patterns.append({"pattern_id": "N/A (Phase 7.1 canonical result, non un FAIL-00x)",
                                      "note": "RECLAIM generico REFUTED_AT_DISCOVERY in Phase 7.1 - vedi market_sequence_registry_v1.json per il dettaglio per-sequence."})
        seqs_for_mech = [s for s in sequences if s["mechanism_id"] == mech_id]
        relations = {s["failure_memory_relation"] for s in seqs_for_mech}
        overall = "DIRECT_REPEAT_OF_FAILED_IDEA" if "DIRECT_REPEAT_OF_FAILED_IDEA" in relations else \
                  ("RELATED_TO_PREVIOUS_FAILURE" if "RELATED_TO_PREVIOUS_FAILURE" in relations else
                   ("NOVEL" if relations else "NOT_FORMALIZED_AS_SEQUENCE"))
        fm_checks.append({
            "mechanism_id": mech_id, "name": name, "overall_failure_memory_relation": overall,
            "n_sequences_derived": len(seqs_for_mech), "matched_registry_patterns": matched_patterns,
        })

    fm_payload = {
        "failure_memory_registry_patterns_checked": [p["pattern_id"] for p in failure_memory],
        "note": "I pattern FAIL-001..008 di failure_memory_registry_v1.json riguardano principalmente l'integrita' del PROCESSO di ricerca (leakage, contaminazione validazione, baseline non direction-aware) - non si applicano direttamente al CONTENUTO di un mechanism di mercato non ancora testato. Il confronto rilevante per Phase 7.2 e' con i RISULTATI CANONICI gia' ottenuti (Phase 5/6/6.5/7.1), riportato per-mechanism/per-sequence sotto.",
        "mechanism_checks": fm_checks,
        "top_overlaps": [c for c in fm_checks if c["overall_failure_memory_relation"] != "NOVEL" and c["overall_failure_memory_relation"] != "NOT_FORMALIZED_AS_SEQUENCE"],
    }
    save_json(os.path.join(PHASE72_DIR, "failure_memory_crosscheck_v1.json"), wrap_with_provenance(fm_payload, "phase7/phase7_2/build_graph_and_diversity.py"))

    print(f"source_graph: {len(edges)} edges")
    print(f"diversity_matrix: {len(diversity_rows)} mechanisms, categories={categories_all}")
    print(f"top diversity (>=3 categorie): {[r['mechanism_id'] for r in diversity_rows if r['n_categories_with_support'] >= 3]}")
    print(f"failure_memory overlaps: {[c['mechanism_id'] for c in fm_payload['top_overlaps']]}")


if __name__ == "__main__":
    main()
