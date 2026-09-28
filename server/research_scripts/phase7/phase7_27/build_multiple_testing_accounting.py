#!/usr/bin/env python3
"""Phase 7.27 punto 8 - conteggio multiple-testing di QUESTA fase
(distinto dal registro globale di Phase 7.26, che viene aggiornato a
parte). Distingue esplicitamente analisi PRIMARIA da EXPLORATORY -
nessun cherry-picking del confronto piu' favorevole nella decisione
finale (la decisione usa SOLO la primaria, dichiarata prima dei
risultati)."""
import os
import sys

PHASE727_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(PHASE727_DIR, "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase6_6"))
from canonical_utils import wrap_with_provenance, save_json  # noqa: E402

sys.path.insert(0, PHASE727_DIR)
import nxs_prereg_constants as C  # noqa: E402

N_STATISTICAL_BENCHMARKS = 4  # esclude BUY_AND_HOLD (contesto macro, non un confronto statistico)


def build():
    n_strategies = len(C.STRATEGIES_INCLUDED)
    n_horizons = len(C.HORIZONS_D1_BARS)
    n_benchmarks = N_STATISTICAL_BENCHMARKS
    n_comparisons_total = n_strategies * n_horizons * n_benchmarks
    n_primary_comparisons = n_strategies  # 1 per strategia: REGIME_MATCHED_RANDOM_LONG @ h_primary

    payload = {
        "n_strategies_tested": n_strategies,
        "n_horizons_tested": n_horizons,
        "n_statistical_benchmarks_tested": n_benchmarks,
        "n_benchmarks_total_incl_macro_context": len(C.BENCHMARKS),
        "n_total_statistical_comparisons_this_phase": n_comparisons_total,
        "n_primary_comparisons_used_for_decision": n_primary_comparisons,
        "n_exploratory_comparisons": n_comparisons_total - n_primary_comparisons,
        "primary_vs_exploratory_declared_before_results": True,
        "no_cherry_picking_most_favorable_comparison_for_decision": True,
        "bonferroni_note": f"Se si applicasse una correzione Bonferroni ai soli confronti "
            f"ESPLORATIVI ({n_comparisons_total - n_primary_comparisons}), la soglia alpha "
            f"effettiva scenderebbe da 0.05 a ~{0.05 / max(1, n_comparisons_total - n_primary_comparisons):.5f} "
            "- NON applicata in questa fase (dichiarato, non nascosto) - l'unico caso "
            "'significativo' trovato (ORDER_BLOCK, h1, esplorativo) non sopravviverebbe a questa "
            "soglia.",
        "order_block_h1_significance_survives_bonferroni": False,
    }
    return payload


def main():
    payload = build()
    doc = wrap_with_provenance(payload, script=os.path.abspath(__file__))
    out_path = os.path.join(PHASE727_DIR, "multiple_testing_accounting_v1.json")
    save_json(out_path, doc)
    print(f"Scritto {out_path} (sha256={doc['canonical_sha256'][:16]}...)")
    print(f"  totale confronti: {payload['n_total_statistical_comparisons_this_phase']} "
         f"(primari: {payload['n_primary_comparisons_used_for_decision']})")


if __name__ == "__main__":
    main()
