#!/usr/bin/env python3
"""Phase 7.22 punto 6 - incertezza statistica: bootstrap per-trade,
sensitivity al clustering temporale. Non assume IID ciecamente. Se il
CI include zero, non si dichiara edge dimostrato."""
import os
import random
import statistics
import sys
from datetime import datetime

PHASE722_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(PHASE722_DIR, "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase6_6"))
from canonical_utils import wrap_with_provenance, save_json  # noqa: E402

sys.path.insert(0, PHASE722_DIR)
from nxs_orderblock_dataset_loader import load_events, net_pnl, split_by_direction  # noqa: E402

N_BOOTSTRAP = 10000
SEED = 79220  # deterministico, dichiarato - stesso principio di Phase 7.21 (seed diverso per fase)


def _dt(s):
    return datetime.strptime(s, "%Y.%m.%d %H:%M:%S")


def _bootstrap_mean_ci(values, n_boot=N_BOOTSTRAP, seed=SEED):
    if not values:
        return None
    rng = random.Random(seed)
    n = len(values)
    means = []
    for _ in range(n_boot):
        sample = [values[rng.randrange(n)] for _ in range(n)]
        means.append(sum(sample) / n)
    means.sort()
    lo_idx, hi_idx = int(0.025 * n_boot), int(0.975 * n_boot) - 1
    return {"point_estimate_mean": sum(values) / n, "bootstrap_ci_95_low": means[lo_idx],
           "bootstrap_ci_95_high": means[hi_idx], "n_bootstrap_resamples": n_boot,
           "excludes_zero": not (means[lo_idx] <= 0 <= means[hi_idx])}


def _check_temporal_clustering(events_sorted, gap_days_threshold=10):
    if len(events_sorted) < 2:
        return {"n_pairs": 0}
    gaps = [(_dt(events_sorted[i]["entry_time"]) - _dt(events_sorted[i - 1]["entry_time"])).days
           for i in range(1, len(events_sorted))]
    n_close = sum(1 for g in gaps if g <= gap_days_threshold)
    return {"n_pairs": len(gaps), "median_gap_days": statistics.median(gaps),
           "n_pairs_within_10_days": n_close, "pct_pairs_within_10_days": n_close / len(gaps)}


def build():
    events = load_events()
    if not events:
        return {"status": "NO_EVENTS_YET"}

    groups = split_by_direction(events)
    result = {}
    for name, evs in groups.items():
        evs_sorted = sorted(evs, key=lambda e: _dt(e["entry_time"]))
        nets = [net_pnl(e) for e in evs_sorted]
        wins = [1 if p > 0 else 0 for p in nets]
        result[name] = {"n": len(nets), "net_expectancy_bootstrap_ci": _bootstrap_mean_ci(nets),
                       "win_rate_bootstrap_ci": _bootstrap_mean_ci(wins),
                       "temporal_clustering": _check_temporal_clustering(evs_sorted)}

    payload = {
        "method": f"Bootstrap per-trade, {N_BOOTSTRAP} iterazioni, seed {SEED} dichiarato e fisso.",
        "iid_assumption_caveat": "Il bootstrap per-trade assume scambiabilita', non necessariamente "
            "indipendenza temporale stretta - vedi temporal_clustering per ogni gruppo.",
        "results": result, "iid_not_assumed_blindly": True,
        "ci_includes_zero_means_no_edge_declared": True,
    }
    return payload


def main():
    payload = build()
    doc = wrap_with_provenance(payload, script=os.path.abspath(__file__))
    out_path = os.path.join(PHASE722_DIR, "orderblock_statistical_uncertainty_v1.json")
    save_json(out_path, doc)
    print(f"Scritto {out_path} (sha256={doc['canonical_sha256'][:16]}...)")
    if payload.get("status") != "NO_EVENTS_YET":
        for name, r in payload["results"].items():
            ci = r["net_expectancy_bootstrap_ci"]
            if ci:
                print(f"  {name}: mean={ci['point_estimate_mean']:.2f} "
                      f"CI95=[{ci['bootstrap_ci_95_low']:.2f}, {ci['bootstrap_ci_95_high']:.2f}] "
                      f"excludes_zero={ci['excludes_zero']}")


if __name__ == "__main__":
    main()
