#!/usr/bin/env python3
"""Phase 7.27 punto 5 - risultati PER STRATEGIA (tenute separate, MAI
aggregate in questo artifact). Per ogni benchmark preregistrato,
confronta i BUY reali contro il benchmark sulla metrica primaria
(forward_return_price_units) ad ogni orizzonte preregistrato:
- REGIME_MATCHED_RANDOM_LONG: confronto APPAIATO (1 match per evento
  reale, stesso regime) - bootstrap sulla differenza appaiata.
- RANDOM_TIMESTAMPS_MATCHED / PERIODIC_ENTRY_LONG: campioni
  INDIPENDENTI stessa numerosita' - bootstrap a due campioni.
- UNCONDITIONAL_LONG_EXPOSURE: popolazione intera (nessuna incertezza
  campionaria propria) - bootstrap a un campione contro la media fissa
  della popolazione.
- BUY_AND_HOLD: SOLO contesto macro, mai incluso nel confronto
  statistico (istruzione esplicita del task)."""
import os
import random
import statistics
import sys

PHASE727_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(PHASE727_DIR, "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase6_6"))
from canonical_utils import wrap_with_provenance, save_json, load_json  # noqa: E402

sys.path.insert(0, PHASE727_DIR)
import nxs_prereg_constants as C  # noqa: E402


def _real_returns_at_h(real_events, h):
    out = []
    for e in real_events:
        m = e["metrics_close_relative"]
        if not m.get("data_available"):
            continue
        v = m["horizons"][f"h{h}"]["forward_return_price_units"]
        if v is not None:
            out.append(v)
    return out


def _sample_returns_at_h(samples, h):
    out = []
    for s in samples:
        if not s.get("data_available"):
            continue
        v = s["horizons"][f"h{h}"]["forward_return_price_units"]
        if v is not None:
            out.append(v)
    return out


def _paired_returns_at_h(real_events, matched_samples, h):
    pairs = []
    for e, s in zip(real_events, matched_samples):
        rm = e["metrics_close_relative"]
        if not rm.get("data_available") or not s.get("data_available"):
            continue
        rv = rm["horizons"][f"h{h}"]["forward_return_price_units"]
        sv = s["horizons"][f"h{h}"]["forward_return_price_units"]
        if rv is not None and sv is not None:
            pairs.append(rv - sv)
    return pairs


def _bootstrap_mean_ci(values, seed, n_boot=C.N_BOOTSTRAP):
    if not values:
        return None
    rng = random.Random(seed)
    n = len(values)
    means = []
    for _ in range(n_boot):
        sample = [values[rng.randrange(n)] for _ in range(n)]
        means.append(sum(sample) / n)
    means.sort()
    lo, hi = means[int(0.025 * n_boot)], means[int(0.975 * n_boot) - 1]
    return {"n": n, "mean": sum(values) / n, "ci95_low": lo, "ci95_high": hi,
           "excludes_zero": not (lo <= 0 <= hi)}


def _two_sample_bootstrap_diff(real_vals, bench_vals, seed, n_boot=C.N_BOOTSTRAP):
    if not real_vals or not bench_vals:
        return None
    rng = random.Random(seed)
    nr, nb = len(real_vals), len(bench_vals)
    diffs = []
    for _ in range(n_boot):
        rmean = sum(real_vals[rng.randrange(nr)] for _ in range(nr)) / nr
        bmean = sum(bench_vals[rng.randrange(nb)] for _ in range(nb)) / nb
        diffs.append(rmean - bmean)
    diffs.sort()
    lo, hi = diffs[int(0.025 * n_boot)], diffs[int(0.975 * n_boot) - 1]
    return {"n_real": nr, "n_bench": nb, "real_mean": statistics.mean(real_vals),
           "bench_mean": statistics.mean(bench_vals), "diff_mean": statistics.mean(real_vals) - statistics.mean(bench_vals),
           "ci95_low": lo, "ci95_high": hi, "excludes_zero": not (lo <= 0 <= hi)}


def _analyze_strategy(strat, data):
    real_events = data["real_events"]
    benches = data["benchmarks"]
    seed_base = C.RANDOM_SEED_BASE + 1

    per_benchmark = {}

    # paired: regime-matched
    rm_samples = benches["REGIME_MATCHED_RANDOM_LONG"]["samples"]
    rm_by_h = {}
    for h in C.HORIZONS_D1_BARS:
        pairs = _paired_returns_at_h(real_events, rm_samples, h)
        rm_by_h[f"h{h}"] = _bootstrap_mean_ci(pairs, seed_base + h, C.N_BOOTSTRAP)
    per_benchmark["REGIME_MATCHED_RANDOM_LONG"] = {"design": "PAIRED", "by_horizon": rm_by_h}

    # independent two-sample: random, periodic
    for bench_name in ("RANDOM_TIMESTAMPS_MATCHED", "PERIODIC_ENTRY_LONG"):
        samples = benches[bench_name]["samples"]
        by_h = {}
        for h in C.HORIZONS_D1_BARS:
            real_vals = _real_returns_at_h(real_events, h)
            bench_vals = _sample_returns_at_h(samples, h)
            by_h[f"h{h}"] = _two_sample_bootstrap_diff(real_vals, bench_vals, seed_base + h,
                                                       C.N_BOOTSTRAP)
        per_benchmark[bench_name] = {"design": "INDEPENDENT_TWO_SAMPLE", "by_horizon": by_h}

    # one-sample vs fixed population mean: unconditional
    unc = benches["UNCONDITIONAL_LONG_EXPOSURE"]["summary"]
    by_h = {}
    for h in C.HORIZONS_D1_BARS:
        real_vals = _real_returns_at_h(real_events, h)
        pop_mean = unc[f"h{h}"]["mean_forward_return"]
        if not real_vals or pop_mean is None:
            by_h[f"h{h}"] = None
            continue
        centered = [v - pop_mean for v in real_vals]
        ci = _bootstrap_mean_ci(centered, seed_base + h, C.N_BOOTSTRAP)
        if ci:
            ci["real_mean"] = statistics.mean(real_vals)
            ci["population_mean"] = pop_mean
        by_h[f"h{h}"] = ci
    per_benchmark["UNCONDITIONAL_LONG_EXPOSURE"] = {"design": "ONE_SAMPLE_VS_FIXED_POPULATION",
                                                    "by_horizon": by_h}

    per_benchmark["BUY_AND_HOLD_MACRO_CONTEXT"] = {
        "design": "MACRO_CONTEXT_ONLY_NOT_A_STATISTICAL_COMPARISON",
        "value": benches["BUY_AND_HOLD_MACRO_CONTEXT"]}

    primary_h_key = f"h{C.PRIMARY_HORIZON_D1_BARS}"
    primary_result = rm_by_h.get(primary_h_key)
    direction = None
    if primary_result:
        direction = "REAL_BETTER" if primary_result["mean"] > 0 else (
            "REAL_WORSE" if primary_result["mean"] < 0 else "NEUTRAL")

    return {
        "n_real_buy_events": len(real_events), "period": data["period"],
        "per_benchmark_results": per_benchmark,
        "primary_analysis_summary": {
            "benchmark": "REGIME_MATCHED_RANDOM_LONG", "horizon": primary_h_key,
            "result": primary_result, "direction_of_effect": direction,
        },
        "sample_size_limitation": (C.MIN_SAMPLE_SIZE_CAVEAT if strat == "ORDER_BLOCK" else None),
    }


def build():
    samples = load_json(os.path.join(PHASE727_DIR, "benchmark_samples_v1.json"))["payload"]
    return {strat: _analyze_strategy(strat, data) for strat, data in samples.items()}


def main():
    payload = build()
    doc = wrap_with_provenance(payload, script=os.path.abspath(__file__))
    out_path = os.path.join(PHASE727_DIR, "per_strategy_results_v1.json")
    save_json(out_path, doc)
    print(f"Scritto {out_path} (sha256={doc['canonical_sha256'][:16]}...)")
    for strat, d in payload.items():
        p = d["primary_analysis_summary"]
        print(f"  {strat}: primary({p['benchmark']}@{p['horizon']}) direction={p['direction_of_effect']} "
             f"result={p['result']}")


if __name__ == "__main__":
    main()
