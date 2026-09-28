#!/usr/bin/env python3
"""Phase 7.25 punto 4 - incertezza statistica: bootstrap per-trade (IID
assunto) + BLOCK bootstrap (finestre mobili di eventi consecutivi, NON
assume indipendenza) come sensitivity alla serial dependence - i gap
fra entry consecutive vanno da 1 a 109 giorni (mediana 14gg), quindi
l'IID non e' assunto ciecamente. Se il CI include zero, nessun edge
dichiarato."""
import os
import random
import statistics
import sys

PHASE725_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(PHASE725_DIR, "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase6_6"))
from canonical_utils import wrap_with_provenance, save_json  # noqa: E402

sys.path.insert(0, PHASE725_DIR)
from nxs_liq_sweep_edge_dataset_loader import (  # noqa: E402
    load_closed_events, net_pnl, split_by_direction, entry_time, _dt)

N_BOOTSTRAP = 10000
SEED = 72500  # deterministico, dichiarato - seed specifico di questa fase
BLOCK_SIZE = 5  # ~1/8 del campione (42 eventi) - dichiarato prima del calcolo
GAP_CLUSTER_THRESHOLD_DAYS = 10


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


def _block_bootstrap_mean_ci(values_in_temporal_order, block_size=BLOCK_SIZE,
                             n_boot=N_BOOTSTRAP, seed=SEED + 1):
    """Moving-block bootstrap: preserva la dipendenza seriale locale
    ricampionando BLOCCHI di eventi consecutivi (non singoli eventi) -
    se il CI resta simile al bootstrap IID, la serial dependence non
    sta gonfiando artificialmente la significativita'."""
    n = len(values_in_temporal_order)
    if n < block_size:
        return None
    rng = random.Random(seed)
    n_blocks_needed = -(-n // block_size)  # ceil
    max_start = n - block_size
    means = []
    for _ in range(n_boot):
        sample = []
        for _ in range(n_blocks_needed):
            start = rng.randint(0, max_start)
            sample.extend(values_in_temporal_order[start:start + block_size])
        sample = sample[:n]
        means.append(sum(sample) / len(sample))
    means.sort()
    lo_idx, hi_idx = int(0.025 * n_boot), int(0.975 * n_boot) - 1
    return {"point_estimate_mean": sum(values_in_temporal_order) / n,
           "block_size": block_size, "bootstrap_ci_95_low": means[lo_idx],
           "bootstrap_ci_95_high": means[hi_idx], "n_bootstrap_resamples": n_boot,
           "excludes_zero": not (means[lo_idx] <= 0 <= means[hi_idx])}


def _check_temporal_clustering(events_sorted, gap_days_threshold=GAP_CLUSTER_THRESHOLD_DAYS):
    if len(events_sorted) < 2:
        return {"n_pairs": 0}
    gaps = [(_dt(entry_time(events_sorted[i])) - _dt(entry_time(events_sorted[i - 1]))).days
           for i in range(1, len(events_sorted))]
    n_close = sum(1 for g in gaps if g <= gap_days_threshold)
    return {"n_pairs": len(gaps), "min_gap_days": min(gaps), "median_gap_days": statistics.median(gaps),
           "max_gap_days": max(gaps),
           "n_pairs_within_threshold": n_close, "pct_pairs_within_threshold": n_close / len(gaps)}


def build():
    events = load_closed_events()
    if not events:
        return {"status": "NO_EVENTS_YET"}

    groups = split_by_direction(events)
    result = {}
    for name, evs in groups.items():
        evs_sorted = sorted(evs, key=lambda e: _dt(entry_time(e)))
        nets = [net_pnl(e) for e in evs_sorted]
        wins = [1 if p > 0 else 0 for p in nets]
        clustering = _check_temporal_clustering(evs_sorted)
        result[name] = {
            "n": len(nets),
            "net_expectancy_bootstrap_ci_iid": _bootstrap_mean_ci(nets),
            "win_rate_bootstrap_ci_iid": _bootstrap_mean_ci(wins),
            "net_expectancy_block_bootstrap_ci": _block_bootstrap_mean_ci(nets),
            "temporal_clustering": clustering,
        }

    ci_all_iid = result["ALL"]["net_expectancy_bootstrap_ci_iid"]
    ci_all_block = result["ALL"]["net_expectancy_block_bootstrap_ci"]
    agreement = None
    if ci_all_iid and ci_all_block:
        agreement = ci_all_iid["excludes_zero"] == ci_all_block["excludes_zero"]

    agreement_per_group = {}
    for name, r in result.items():
        i, b = r["net_expectancy_bootstrap_ci_iid"], r["net_expectancy_block_bootstrap_ci"]
        agreement_per_group[name] = (i["excludes_zero"] == b["excludes_zero"]) if (i and b) else None

    payload = {
        "method_iid": f"Bootstrap per-trade, {N_BOOTSTRAP} iterazioni, seed {SEED} - assume "
            "scambiabilita' (non necessariamente indipendenza temporale stretta).",
        "method_block": f"Moving-block bootstrap, blocco={BLOCK_SIZE} eventi consecutivi "
            f"({N_BOOTSTRAP} iterazioni, seed {SEED + 1}) - preserva la dipendenza seriale locale "
            "(holding time, clustering di regime) invece di ricampionare singoli trade "
            "indipendentemente. Sensitivity esplicita alla serial dependence, non un'alternativa "
            "sostitutiva.",
        "iid_assumption_not_blindly_assumed": True,
        "results": result,
        "iid_vs_block_ci_conclusion_agree_on_excludes_zero_ALL": agreement,
        "iid_vs_block_ci_agreement_per_group": agreement_per_group,
        "disagreement_note": "Se IID e BLOCK bootstrap NON concordano sull'escludere lo zero per "
            "un gruppo, il risultato e' sensibile all'assunzione di indipendenza - dichiarato "
            "esplicitamente, non usato per scegliere il metodo che conferma l'edge (entrambi i "
            "risultati sono riportati, nessuno dei due scartato).",
        "ci_includes_zero_means_no_edge_declared": True,
    }
    return payload


def main():
    payload = build()
    doc = wrap_with_provenance(payload, script=os.path.abspath(__file__))
    out_path = os.path.join(PHASE725_DIR, "statistical_uncertainty_v1.json")
    save_json(out_path, doc)
    print(f"Scritto {out_path} (sha256={doc['canonical_sha256'][:16]}...)")
    for name, r in payload["results"].items():
        ci = r["net_expectancy_bootstrap_ci_iid"]
        cib = r["net_expectancy_block_bootstrap_ci"]
        if ci:
            print(f"  {name}: IID mean={ci['point_estimate_mean']:.2f} "
                 f"CI95=[{ci['bootstrap_ci_95_low']:.2f}, {ci['bootstrap_ci_95_high']:.2f}] "
                 f"excl0={ci['excludes_zero']}"
                 + (f" | BLOCK CI95=[{cib['bootstrap_ci_95_low']:.2f}, "
                    f"{cib['bootstrap_ci_95_high']:.2f}] excl0={cib['excludes_zero']}" if cib else ""))


if __name__ == "__main__":
    main()
