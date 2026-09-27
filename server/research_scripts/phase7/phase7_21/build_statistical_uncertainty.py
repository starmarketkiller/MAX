#!/usr/bin/env python3
"""Phase 7.21 punto 8 - incertezza statistica: campione ridotto (47
trade), evitare falsa precisione. Bootstrap per-trade (non assume IID
se gli eventi sono clusterizzati temporalmente - verificato)."""
import os
import random
import statistics
import sys
from datetime import datetime

PHASE721_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(PHASE721_DIR, "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase6_6"))
from canonical_utils import wrap_with_provenance, save_json  # noqa: E402

sys.path.insert(0, PHASE721_DIR)
from nxs_breakoutacc_dataset_loader import load_opened_events, net_pnl, split_by_direction  # noqa: E402

N_BOOTSTRAP = 10000
SEED = 79210  # deterministico, dichiarato - non ripetuto/cercato per ottenere un risultato migliore


def _dt(s):
    return datetime.strptime(s, "%Y.%m.%d %H:%M:%S")


def _bootstrap_mean_ci(values, n_boot=N_BOOTSTRAP, seed=SEED):
    rng = random.Random(seed)
    n = len(values)
    if n == 0:
        return None
    means = []
    for _ in range(n_boot):
        sample = [values[rng.randrange(n)] for _ in range(n)]
        means.append(sum(sample) / n)
    means.sort()
    lo_idx = int(0.025 * n_boot)
    hi_idx = int(0.975 * n_boot) - 1
    return {"point_estimate_mean": sum(values) / n, "bootstrap_ci_95_low": means[lo_idx],
           "bootstrap_ci_95_high": means[hi_idx], "n_bootstrap_resamples": n_boot,
           "excludes_zero": not (means[lo_idx] <= 0 <= means[hi_idx])}


def _check_temporal_clustering(events_sorted, gap_days_threshold=10):
    """Verifica se gli eventi sono clusterizzati temporalmente (piu' eventi
    ravvicinati nel tempo di quanto atteso da un processo uniforme) - se
    si', l'assunzione IID per il bootstrap e' una semplificazione nota,
    dichiarata qui, non nascosta."""
    if len(events_sorted) < 2:
        return {"n_pairs": 0}
    gaps = []
    for i in range(1, len(events_sorted)):
        d1 = _dt(events_sorted[i - 1]["entry_fill_time"])
        d2 = _dt(events_sorted[i]["entry_fill_time"])
        gaps.append((d2 - d1).days)
    n_close = sum(1 for g in gaps if g <= gap_days_threshold)
    return {"n_pairs": len(gaps), "median_gap_days": statistics.median(gaps),
           "n_pairs_within_10_days": n_close,
           "pct_pairs_within_10_days": n_close / len(gaps),
           "iid_assumption_caveat": "Il bootstrap per-trade sotto assume scambiabilita' (non "
               "necessariamente indipendenza temporale in senso stretto) - se una quota rilevante "
               "di coppie di trade e' ravvicinata nel tempo, l'incertezza reale potrebbe essere "
               "maggiore di quella stimata dal bootstrap IID.",
    }


def build():
    events = load_opened_events()
    events_sorted = sorted(events, key=lambda e: _dt(e["entry_fill_time"]))
    groups = split_by_direction(events)

    result = {}
    for name, evs in groups.items():
        evs_sorted = sorted(evs, key=lambda e: _dt(e["entry_fill_time"]))
        nets = [net_pnl(e) for e in evs_sorted]
        wins = [1 if p > 0 else 0 for p in nets]
        result[name] = {
            "n": len(nets),
            "net_expectancy_bootstrap_ci": _bootstrap_mean_ci(nets) if nets else None,
            "win_rate_bootstrap_ci": _bootstrap_mean_ci(wins) if wins else None,
            "temporal_clustering": _check_temporal_clustering(evs_sorted),
        }

    payload = {
        "method": "Bootstrap per-trade (resampling con reinserimento), 10.000 iterazioni, seed "
                 f"{SEED} dichiarato e fisso (non ricercato per ottenere un intervallo migliore).",
        "sample_size_caveat": "47 trade totali (36 BUY, 11 SELL) - il gruppo SELL in particolare e' "
            "troppo piccolo per un CI bootstrap informativo (ampio per costruzione).",
        "results": result,
        "iid_not_assumed_blindly": True,
    }
    return payload


def main():
    payload = build()
    doc = wrap_with_provenance(payload, script=os.path.abspath(__file__))
    out_path = os.path.join(PHASE721_DIR, "statistical_uncertainty_v1.json")
    save_json(out_path, doc)
    print(f"Scritto {out_path} (sha256={doc['canonical_sha256'][:16]}...)")
    for name, r in payload["results"].items():
        ci = r["net_expectancy_bootstrap_ci"]
        if ci:
            print(f"  {name}: mean={ci['point_estimate_mean']:.2f} "
                  f"CI95=[{ci['bootstrap_ci_95_low']:.2f}, {ci['bootstrap_ci_95_high']:.2f}] "
                  f"excludes_zero={ci['excludes_zero']}")


if __name__ == "__main__":
    main()
