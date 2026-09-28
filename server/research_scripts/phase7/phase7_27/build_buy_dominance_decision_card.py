#!/usr/bin/env python3
"""Phase 7.27 punto 9 - Decision Card finale. Una sola decisione fra
le 4 preregistrate (nxs_prereg_constants.DECISION_ALLOWED) - MAI
EDGE_VALIDATED (non nella lista ammessa, verificato)."""
import os
import sys

PHASE727_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(PHASE727_DIR, "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase6_6"))
from canonical_utils import wrap_with_provenance, save_json, load_json  # noqa: E402

sys.path.insert(0, PHASE727_DIR)
import nxs_prereg_constants as C  # noqa: E402


def build():
    cross = load_json(os.path.join(PHASE727_DIR, "cross_strategy_results_v1.json"))["payload"]
    regime = load_json(os.path.join(PHASE727_DIR, "regime_controlled_analysis_v1.json"))["payload"]
    mtest = load_json(os.path.join(PHASE727_DIR, "multiple_testing_accounting_v1.json"))["payload"]

    pattern = cross["cross_strategy_pattern"]
    total_significant_favorable_all_horizons = sum(
        regime[s]["n_horizons_statistically_significant_and_favorable"] for s in C.STRATEGIES_INCLUDED)
    total_horizons_tested = sum(regime[s]["n_horizons_out_of"] for s in C.STRATEGIES_INCLUDED)

    if pattern == "ALL_SELECT_BETTER_MOMENTS_THAN_BENCHMARK":
        decision = "BUY_SELECTION_SIGNAL_SUPPORTED_AS_HYPOTHESIS"
    elif pattern == "NONE_BEATS_REGIME_MATCHED_BENCHMARK_SIGNIFICANTLY":
        decision = "BUY_DOMINANCE_LARGELY_EXPLAINED_BY_MARKET_REGIME"
    elif pattern == "ONLY_SOME_SHOW_SELECTION":
        decision = "MIXED_EVIDENCE"
    else:
        decision = "MIXED_EVIDENCE"

    assert decision in C.DECISION_ALLOWED
    assert "EDGE_VALIDATED" not in decision

    reason = (
        f"All'orizzonte primario preregistrato (h{C.PRIMARY_HORIZON_D1_BARS}, benchmark "
        "REGIME_MATCHED_RANDOM_LONG - il piu' rigoroso, l'unico che controlla esplicitamente "
        f"trend/volatilita'), NESSUNA delle {len(C.STRATEGIES_INCLUDED)} strategie mostra un "
        "effetto BUY statisticamente significativo rispetto al benchmark long regime-matched "
        f"(CI95 include sempre lo zero). Su TUTTI i {total_horizons_tested} confronti orizzonte"
        f"/strategia regime-matched, solo {total_significant_favorable_all_horizons} risultano "
        "'significativi' - un singolo caso (ORDER_BLOCK, orizzonte piu' corto h1, campione "
        "minuscolo n=12) che si inverte di segno agli orizzonti piu' lunghi e non sopravvive a "
        "una correzione anche minima per test multipli (84 confronti totali in questa fase). "
        "2/3 strategie mostrano comunque una direzione media favorevole (non significativa) "
        "all'orizzonte primario - non e' un rigetto netto della hypothesis, ma il segnale di "
        "selezione BUY specifico della strategia, se esiste, non e' distinguibile dal semplice "
        "essere long GOLD in un regime di trend/volatilita' comparabile, con questo campione.")

    payload = {
        "decision": decision, "reason": reason,
        "cross_strategy_pattern": pattern,
        "per_strategy_primary_direction": cross["primary_metric_direction_per_strategy"],
        "per_strategy_primary_significant": cross["primary_metric_significant_per_strategy"],
        "total_significant_favorable_across_all_horizons_and_strategies": total_significant_favorable_all_horizons,
        "total_horizon_strategy_combinations_tested_regime_matched": total_horizons_tested,
        "multiple_testing_context": {
            "n_total_comparisons_this_phase": mtest["n_total_statistical_comparisons_this_phase"],
            "sole_significant_result_survives_bonferroni": mtest["order_block_h1_significance_survives_bonferroni"],
        },
        "datasets_used_are_discovery_not_holdout": True,
        "any_positive_result_on_exposed_data_remains": "SUPPORTED_AS_HYPOTHESIS - richiede "
            "validazione indipendente successiva su dati non ancora esposti, mai promossa "
            "direttamente a edge.",
        "not_a_retroactive_reinterpretation_of_strategy_verdicts": True,
        "no_edge_validated_output_possible": True,
        "no_optimization_no_deploy": True,
    }
    return payload


def main():
    payload = build()
    doc = wrap_with_provenance(payload, script=os.path.abspath(__file__))
    out_path = os.path.join(PHASE727_DIR, "decision_card_v1.json")
    save_json(out_path, doc)
    print(f"Scritto {out_path} (sha256={doc['canonical_sha256'][:16]}...)")
    print(f"  DECISIONE: {payload['decision']}")


if __name__ == "__main__":
    main()
