#!/usr/bin/env python3
"""Phase 7.27 punto 4 - analisi regime-controlled esplicita: dopo aver
controllato trend/volatilita' (REGIME_MATCHED_RANDOM_LONG, appaiato per
bucket), i BUY delle strategie restano migliori del benchmark? Riporta
TUTTI gli orizzonti (non solo il primario) + una rottura per bucket di
regime (trend x vol_tercile) quando il campione lo permette (>=5
eventi nel bucket - altrimenti NOT_AVAILABLE, campione troppo piccolo
per un numero specifico)."""
import os
import sys
from collections import defaultdict

PHASE727_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(PHASE727_DIR, "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase6_6"))
from canonical_utils import wrap_with_provenance, save_json, load_json  # noqa: E402

sys.path.insert(0, PHASE727_DIR)
import nxs_prereg_constants as C  # noqa: E402

MIN_BUCKET_SIZE = 5


def _analyze_strategy(strat, samples_data, results_data):
    real_events = samples_data["real_events"]
    rm_samples = samples_data["benchmarks"]["REGIME_MATCHED_RANDOM_LONG"]["samples"]
    all_horizons = results_data["per_benchmark_results"]["REGIME_MATCHED_RANDOM_LONG"]["by_horizon"]

    still_better_count = sum(1 for h, r in all_horizons.items() if r and r["mean"] > 0)
    still_better_significant = sum(1 for h, r in all_horizons.items() if r and r["excludes_zero"] and r["mean"] > 0)

    buckets = defaultdict(list)
    for e, s in zip(real_events, rm_samples):
        rm = e["metrics_close_relative"]
        if not rm.get("data_available") or not s.get("data_available"):
            continue
        h10 = f"h{C.PRIMARY_HORIZON_D1_BARS}"
        rv = rm["horizons"][h10]["forward_return_price_units"]
        sv = s["horizons"][h10]["forward_return_price_units"]
        if rv is None or sv is None:
            continue
        key = f"{e['regime']['trend']}_{e['regime']['vol_tercile']}"
        buckets[key].append(rv - sv)

    bucket_results = {}
    for key, diffs in buckets.items():
        if len(diffs) < MIN_BUCKET_SIZE:
            bucket_results[key] = {"n": len(diffs), "status": "SAMPLE_TOO_SMALL_NOT_AVAILABLE"}
        else:
            bucket_results[key] = {"n": len(diffs), "mean_paired_diff": sum(diffs) / len(diffs)}

    return {
        "all_horizons_vs_regime_matched_benchmark": all_horizons,
        "n_horizons_where_real_mean_higher": still_better_count,
        "n_horizons_out_of": len(all_horizons),
        "n_horizons_statistically_significant_and_favorable": still_better_significant,
        "per_regime_bucket_breakdown_h_primary": bucket_results,
        "conclusion_this_strategy": (
            "I BUY reali restano in media migliori del benchmark regime-matched in "
            f"{still_better_count}/{len(all_horizons)} orizzonti, ma NESSUNO statisticamente "
            "significativo" if still_better_significant == 0 else
            f"I BUY reali sono significativamente migliori del benchmark regime-matched in "
            f"{still_better_significant}/{len(all_horizons)} orizzonti."),
    }


def build():
    samples = load_json(os.path.join(PHASE727_DIR, "benchmark_samples_v1.json"))["payload"]
    results = load_json(os.path.join(PHASE727_DIR, "per_strategy_results_v1.json"))["payload"]
    return {strat: _analyze_strategy(strat, samples[strat], results[strat])
           for strat in C.STRATEGIES_INCLUDED}


def main():
    payload = build()
    doc = wrap_with_provenance(payload, script=os.path.abspath(__file__))
    out_path = os.path.join(PHASE727_DIR, "regime_controlled_analysis_v1.json")
    save_json(out_path, doc)
    print(f"Scritto {out_path} (sha256={doc['canonical_sha256'][:16]}...)")
    for strat, d in payload.items():
        print(f"  {strat}: {d['conclusion_this_strategy']}")


if __name__ == "__main__":
    main()
