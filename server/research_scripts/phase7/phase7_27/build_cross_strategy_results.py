#!/usr/bin/env python3
"""Phase 7.27 punto 6 - risultati cross-strategy, SOLO DOPO i risultati
individuali (letti da per_strategy_results_v1.json / regime_controlled_
analysis_v1.json, non ricalcolati). Non trasforma automaticamente la
concordanza in edge (nessun EDGE_VALIDATED prodotto qui)."""
import os
import sys

PHASE727_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(PHASE727_DIR, "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase6_6"))
from canonical_utils import wrap_with_provenance, save_json, load_json  # noqa: E402

sys.path.insert(0, PHASE727_DIR)
import nxs_prereg_constants as C  # noqa: E402


def build():
    regime = load_json(os.path.join(PHASE727_DIR, "regime_controlled_analysis_v1.json"))["payload"]
    per_strat = load_json(os.path.join(PHASE727_DIR, "per_strategy_results_v1.json"))["payload"]

    primary_directions = {s: per_strat[s]["primary_analysis_summary"]["direction_of_effect"]
                          for s in C.STRATEGIES_INCLUDED}
    primary_significant = {s: bool(per_strat[s]["primary_analysis_summary"]["result"] and
                                   per_strat[s]["primary_analysis_summary"]["result"]["excludes_zero"])
                          for s in C.STRATEGIES_INCLUDED}
    n_favorable = sum(1 for d in primary_directions.values() if d == "REAL_BETTER")
    n_significant_favorable = sum(1 for s in C.STRATEGIES_INCLUDED
                                  if primary_significant[s] and primary_directions[s] == "REAL_BETTER")

    if n_significant_favorable == len(C.STRATEGIES_INCLUDED):
        pattern = "ALL_SELECT_BETTER_MOMENTS_THAN_BENCHMARK"
    elif n_significant_favorable == 0:
        pattern = "NONE_BEATS_REGIME_MATCHED_BENCHMARK_SIGNIFICANTLY"
    elif n_significant_favorable >= 1:
        pattern = "ONLY_SOME_SHOW_SELECTION"
    else:
        pattern = "MIXED_INCONCLUSIVE_EVIDENCE"

    payload = {
        "primary_metric_direction_per_strategy": primary_directions,
        "primary_metric_significant_per_strategy": primary_significant,
        "n_strategies_favorable_direction": n_favorable,
        "n_strategies_out_of": len(C.STRATEGIES_INCLUDED),
        "n_strategies_statistically_significant_and_favorable": n_significant_favorable,
        "cross_strategy_pattern": pattern,
        "pattern_options_declared": ["ALL_SELECT_BETTER_MOMENTS_THAN_BENCHMARK",
                                    "ONLY_SOME_SHOW_SELECTION",
                                    "NONE_BEATS_REGIME_MATCHED_BENCHMARK_SIGNIFICANTLY",
                                    "MIXED_INCONCLUSIVE_EVIDENCE"],
        "concordance_not_automatically_edge": True,
        "per_strategy_conclusions": {s: regime[s]["conclusion_this_strategy"] for s in C.STRATEGIES_INCLUDED},
        "note": "2/3 strategie mostrano direzione favorevole (paired mean > 0) all'orizzonte "
               "primario (h10) contro il benchmark regime-matched, ma NESSUNA delle 3 in modo "
               "statisticamente significativo su quell'orizzonte specifico - ORDER_BLOCK mostra "
               "un singolo orizzonte (h1, il piu' corto) significativo su un campione minuscolo "
               "(n=12) che si INVERTE di segno entro h40/h60 - pattern coerente con rumore "
               "campionario piuttosto che un segnale robusto, non con un fenomeno trasversale forte.",
    }
    return payload


def main():
    payload = build()
    doc = wrap_with_provenance(payload, script=os.path.abspath(__file__))
    out_path = os.path.join(PHASE727_DIR, "cross_strategy_results_v1.json")
    save_json(out_path, doc)
    print(f"Scritto {out_path} (sha256={doc['canonical_sha256'][:16]}...)")
    print(f"  pattern: {payload['cross_strategy_pattern']}")


if __name__ == "__main__":
    main()
