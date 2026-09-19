#!/usr/bin/env python3
"""Phase 7.2 sec.4/26/27 - Assembla i batch grezzi prodotti dagli agenti
di ricerca in external_hypothesis_corpus_v1.json (claim canonici,
claim_id assegnato qui) e source_registry_v1.json (fonti deduplicate per
source_url - gli agenti assegnavano un source_id per CLAIM, non per
fonte reale; questo script corregge la deduplicazione usando l'URL come
identita' canonica di una fonte, come richiesto dal principio 'nessuna
fonte >10% dei claim' che ha senso solo se le fonti sono deduplicate
correttamente)."""
import glob
import json
import os
import sys
from collections import defaultdict

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", ".."))
PHASE72_DIR = os.path.join(ROOT, "server", "research_scripts", "phase7", "phase7_2")
RAW_DIR = os.path.join(PHASE72_DIR, "raw")
sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase6_6"))
from canonical_utils import wrap_with_provenance, save_json  # noqa: E402


def main():
    batch_files = sorted(glob.glob(os.path.join(RAW_DIR, "batch_*.json")))
    all_raw_claims = []
    for f in batch_files:
        with open(f, encoding="utf-8") as fh:
            batch = json.load(fh)
        for c in batch:
            c["_origin_batch"] = os.path.basename(f)
            all_raw_claims.append(c)

    print(f"Batch trovati: {[os.path.basename(f) for f in batch_files]}")
    print(f"Claim grezzi totali: {len(all_raw_claims)}")

    # --- deduplica fonti per source_url (identita' canonica di una fonte) ---
    source_by_url = {}
    source_order = []
    for c in all_raw_claims:
        url = c["source_url"]
        if url not in source_by_url:
            sid = f"SRC-{len(source_order) + 1:04d}"
            source_order.append(url)
            source_by_url[url] = {
                "source_id": sid,
                "source_type": c["source_type"],
                "source_url": url,
                "source_title": c["source_title"],
                "author_if_known": c.get("author_if_known"),
                "publication_date_if_known": c.get("publication_date_if_known"),
                "n_claims_from_source": 0,
            }
        source_by_url[url]["n_claims_from_source"] += 1

    n_total_claims = len(all_raw_claims)
    max_share = max(s["n_claims_from_source"] for s in source_by_url.values()) / n_total_claims if n_total_claims else 0
    dominant_sources = [s for s in source_by_url.values() if s["n_claims_from_source"] / n_total_claims > 0.10]

    # --- assegna claim_id canonico e source_id canonico ---
    claims = []
    for i, c in enumerate(all_raw_claims, start=1):
        claim_id = f"CLAIM-{i:04d}"
        canonical_source_id = source_by_url[c["source_url"]]["source_id"]
        claim = dict(c)
        claim["claim_id"] = claim_id
        claim["source_id"] = canonical_source_id
        claim.pop("_origin_batch", None)
        # campi da compilare in fasi successive (normalizzazione/contraddizioni) - dichiarati ma vuoti ora
        claim.setdefault("candidate_mechanism_ids", [])
        claim.setdefault("contradiction_group_id", None)
        claim.setdefault("exclusion_reason", None)
        claims.append(claim)

    # --- statistiche di copertura (sec.2-3, sec.26) ---
    source_type_counts = defaultdict(int)
    market_counts = defaultdict(int)
    quality_counts = defaultdict(int)
    commercial_conflict_count = 0
    reproducible_count = 0
    for c in claims:
        source_type_counts[c["source_type"]] += 1
        market_counts[c["market"]] += 1
        quality_counts[c["evidence_quality"]] += 1
        if c["commercial_conflict_risk"] and c["commercial_conflict_risk"] != ["NONE_DETECTED"]:
            commercial_conflict_count += 1
        if c["reproducibility"] == "FULLY_SPECIFIED":
            reproducible_count += 1

    # 5 categorie di fonte = raggruppamento dei source_type in famiglie (sec.1-2)
    category_map = {
        "ACADEMIC_PAPER": "ACADEMIC", "PREPRINT_SSRN_ARXIV": "ACADEMIC", "QUANT_BLOG": "ACADEMIC",
        "MQL5": "MQL5_EA", "EA_PUBLIC": "MQL5_EA",
        "REDDIT": "COMMUNITY", "FOREXFACTORY": "COMMUNITY", "OTHER_FORUM": "COMMUNITY",
        "TRADINGVIEW": "OPEN_SOURCE_SCRIPTS", "GITHUB_OPENSOURCE": "OPEN_SOURCE_SCRIPTS",
        "BROKER_EXCHANGE_DOC": "MARKET_STRUCTURE_DOC",
    }
    category_counts = defaultdict(int)
    for c in claims:
        category_counts[category_map.get(c["source_type"], "OTHER")] += 1

    n_sources = len(source_by_url)
    n_categories = len(category_counts)

    coverage_report = {
        "n_raw_claims": n_total_claims,
        "n_distinct_sources": n_sources,
        "n_source_categories": n_categories,
        "source_category_counts": dict(category_counts),
        "source_type_counts": dict(source_type_counts),
        "market_counts": dict(market_counts),
        "evidence_quality_distribution": dict(quality_counts),
        "commercial_conflict_flagged_count": commercial_conflict_count,
        "fully_reproducible_count": reproducible_count,
        "max_single_source_share": max_share,
        "sources_exceeding_10_percent": [s["source_id"] for s in dominant_sources],
        "targets_met": {
            "n_raw_claims_geq_100": n_total_claims >= 100,
            "n_distinct_sources_geq_30": n_sources >= 30,
            "n_source_categories_geq_5": n_categories >= 5,
            "no_source_over_10_percent": len(dominant_sources) == 0,
        },
    }

    corpus_payload = {"claims": claims, "coverage_report": coverage_report}
    save_json(os.path.join(PHASE72_DIR, "external_hypothesis_corpus_v1.json"),
              wrap_with_provenance(corpus_payload, "phase7/phase7_2/build_corpus_and_source_registry.py"))

    sources_payload = {"sources": list(source_by_url.values())}
    save_json(os.path.join(PHASE72_DIR, "source_registry_v1.json"),
              wrap_with_provenance(sources_payload, "phase7/phase7_2/build_corpus_and_source_registry.py"))

    print(json.dumps(coverage_report, indent=2, ensure_ascii=False))
    print(f"\nwritten: external_hypothesis_corpus_v1.json ({len(claims)} claims)")
    print(f"written: source_registry_v1.json ({n_sources} sources)")
    return coverage_report


if __name__ == "__main__":
    main()
