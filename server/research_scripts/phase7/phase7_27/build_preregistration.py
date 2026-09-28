#!/usr/bin/env python3
"""Phase 7.27 punto 1 - preregistrazione. Congela in un artifact
firmato (hash canonico) tutti i parametri di nxs_prereg_constants.py
PRIMA che qualunque benchmark/metrica venga calcolato - il verificatore
ricontrolla che gli artifact successivi (benchmark, metriche, decisione)
usino ESATTAMENTE questi valori, non valori ridefiniti altrove."""
import os
import sys

PHASE727_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(PHASE727_DIR, "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase6_6"))
from canonical_utils import wrap_with_provenance, save_json  # noqa: E402

sys.path.insert(0, PHASE727_DIR)
import nxs_prereg_constants as C  # noqa: E402
from nxs_real_buy_events_loader import load_all_buy_events  # noqa: E402


def build():
    events = load_all_buy_events()
    n_events = {k: len(v) for k, v in events.items()}
    payload = {
        "strategies_included": C.STRATEGIES_INCLUDED,
        "n_buy_events_per_strategy": n_events,
        "datasets_used": C.DATASETS_USED,
        "datasets_are_discovery_not_holdout": True,
        "price_source": C.PRICE_SOURCE, "price_source_note": C.PRICE_SOURCE_NOTE,
        "horizons_d1_bars": C.HORIZONS_D1_BARS,
        "primary_horizon_d1_bars": C.PRIMARY_HORIZON_D1_BARS,
        "metrics": C.METRICS,
        "benchmarks": C.BENCHMARKS,
        "matching_rules": C.MATCHING_RULES,
        "exclusion_rules": C.EXCLUSION_RULES,
        "sample_size_caveats": C.MIN_SAMPLE_SIZE_CAVEAT,
        "random_seed_base": C.RANDOM_SEED_BASE, "n_bootstrap": C.N_BOOTSTRAP,
        "primary_analysis_declared": C.PRIMARY_ANALYSIS,
        "decision_allowed_values": C.DECISION_ALLOWED,
        "frozen_before_any_result_examined": True,
        "no_benchmark_change_after_seeing_results": True,
    }
    return payload


def main():
    payload = build()
    doc = wrap_with_provenance(payload, script=os.path.abspath(__file__))
    out_path = os.path.join(PHASE727_DIR, "preregistration_v1.json")
    save_json(out_path, doc)
    print(f"Scritto {out_path} (sha256={doc['canonical_sha256'][:16]}...)")
    print(f"  n_buy_events: {payload['n_buy_events_per_strategy']}")


if __name__ == "__main__":
    main()
