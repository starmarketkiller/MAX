"""
NEXUS Causal Research Thread 2 - Structural Causal Experiment 2: Confirmatory
Test of the 3 frozen WEAK_HINT patterns from Experiment 1.

NON discovery: nessuna nuova feature, nessuna combinazione, nessuna soglia
ricalcolata. Le tre soglie sono CONGELATE dai dati di Experiment 1 (TRAIN,
w1+w2+parte w3) e riapplicate identiche su un periodo indipendente MAI
usato in w1-w4.

Puro standard library, riusa assign_episodes()/build_episode_lifecycle_index()
da build_structural_dataset_v1.py (stessa logica di popolazione/linkage).
"""
import csv
import json
import math
import os
from datetime import datetime
from collections import defaultdict

import build_structural_dataset_v1 as bds

HARVEST_DIR = r"C:\Users\User\.claude\jobs\703d44b4\tmp\structural_dataset_v1\harvest"
OUT_DIR = r"C:\Users\User\ClaudeWork\MAX\results\structural_causal_experiment_2"
os.makedirs(OUT_DIR, exist_ok=True)

W0 = {"id": "w0", "from": "2025.09.01", "to": "2026.01.01"}

# --- Soglie CONGELATE da Experiment 1 (TRAIN, w1+w2+parte w3) - MAI ricalcolate qui ---
PEN_ATR_Q4_THRESHOLD = 0.058713928652578955  # Q3/Q4 boundary esatto, ricomputato dal TRAIN di Exp1
AGE_THRESHOLD_SECONDS = 3600.0               # <1h, fisso per istruzione
SOURCE_TF_TARGET = "PERIOD_D1"               # fisso per istruzione

MIN_EFFECT = 0.10          # stessa soglia di Experiment 1, per coerenza
MIN_N_GROUP = 20
MIN_N_HALF = 8             # minimo per considerare interpretabile una meta' temporale
MIN_N_SIDE = 15            # minimo per side (BUY/SELL) robustness


def wilson_ci(k, n, z=1.96):
    if n == 0:
        return (0.0, 0.0)
    p = k / n
    denom = 1 + z * z / n
    center = p + z * z / (2 * n)
    margin = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return ((center - margin) / denom, (center + margin) / denom)


def two_proportion_z(k1, n1, k2, n2):
    """z-test per differenza di proporzioni (gruppo vs resto). Ritorna (diff, z, p_two_sided)."""
    if n1 == 0 or n2 == 0:
        return (float("nan"), float("nan"), float("nan"))
    p1, p2 = k1 / n1, k2 / n2
    p_pool = (k1 + k2) / (n1 + n2)
    se = math.sqrt(p_pool * (1 - p_pool) * (1 / n1 + 1 / n2))
    if se == 0:
        return (p1 - p2, float("nan"), float("nan"))
    z = (p1 - p2) / se
    # approssimazione normale standard per il p-value a due code (senza scipy)
    p_value = 2 * (1 - _norm_cdf(abs(z)))
    return (p1 - p2, z, p_value)


def _norm_cdf(x):
    return 0.5 * (1 + math.erf(x / math.sqrt(2)))


def load_w0_events():
    rows = bds.read_structural_csv(os.path.join(HARVEST_DIR, f"structural_events_{W0['id']}.csv"))
    for r in rows:
        r["window_id"] = W0["id"]
    return rows


def build_valid_population(all_events):
    lifecycle_link, episodes, true_orphans, redundant_after_close, true_break_after_close = bds.assign_episodes(all_events)
    episode_lifecycle = bds.build_episode_lifecycle_index(all_events, lifecycle_link)
    redundant_ids = set(e["event_id"] for e in redundant_after_close)
    tbac_ids = set(e["event_id"] for e in true_break_after_close)
    sweeps_by_episode = {e["structural_episode_id"]: e for e in all_events if e["event_type"] == "SWEEP"}

    n_no_lifecycle = 0
    n_excluded_redundant = 0
    n_orphan = len(true_orphans)
    valid = []
    for ep_id in episodes:
        peers = episode_lifecycle.get(ep_id, [])
        tb = sorted([p for p in peers if p["event_type"] == "TRUE_BREAK"], key=lambda x: int(x["event_id"]))
        inv_swept = sorted([p for p in peers if p["event_type"] == "INVALIDATE" and p["state_before"] == "SWEPT"],
                            key=lambda x: int(x["event_id"]))
        if not tb and not inv_swept:
            n_no_lifecycle += 1
            continue
        determinant = tb[0] if tb else inv_swept[0]
        outcome = "TRUE_BREAK_OBSERVED" if tb else "INVALIDATED_NO_BREAK"
        if determinant["event_id"] in redundant_ids or determinant["event_id"] in tbac_ids:
            n_excluded_redundant += 1
            continue
        sweep_row = sweeps_by_episode.get(ep_id)
        if sweep_row is None:
            continue
        atr = float(sweep_row["atr_at_event"]) if sweep_row["atr_at_event"] not in (None, "") else None
        pen_pips = float(sweep_row["penetration_pips"])
        pen_price = pen_pips * bds.PIP_SIZE
        pen_per_atr = (pen_price / atr) if (atr and atr > 0) else None
        age = float(sweep_row["age_seconds"]) if sweep_row["age_seconds"] not in (None, "") else -1
        valid.append({
            "episode_id": ep_id, "outcome": outcome, "timestamp": sweep_row["timestamp"],
            "source_tf": sweep_row["source_tf"], "direction": sweep_row["direction"],
            "penetration_per_atr": pen_per_atr, "age_seconds": age if age >= 0 else None,
        })
    return valid, {
        "total_episodes": len(episodes), "no_lifecycle_observed": n_no_lifecycle,
        "excluded_redundant_outcome": n_excluded_redundant, "orphan_events": n_orphan,
        "valid_population": len(valid),
    }


def rate_of(subset):
    n = len(subset)
    k = sum(1 for r in subset if r["outcome"] == "TRUE_BREAK_OBSERVED")
    return k, n, (k / n if n else float("nan"))


def test_hint(name, population, group_fn, exp1_uplift_sign=+1):
    base_k, base_n, base_rate = rate_of(population)
    group = [r for r in population if group_fn(r)]
    rest = [r for r in population if not group_fn(r)]
    gk, gn, grate = rate_of(group)
    lo, hi = wilson_ci(gk, gn)
    uplift_abs = (grate - base_rate) if gn else float("nan")
    uplift_rel = (uplift_abs / base_rate) if (gn and base_rate > 0) else float("nan")
    diff_rest, z, pval = two_proportion_z(gk, gn, *rate_of(rest)[:2])

    # meta' temporale (split sulla mediana del timestamp dell'INTERA population, non del gruppo)
    ts_sorted = sorted(r["timestamp"] for r in population)
    median_ts = ts_sorted[len(ts_sorted) // 2] if ts_sorted else None
    first_half = [r for r in group if r["timestamp"] < median_ts] if median_ts else []
    second_half = [r for r in group if r["timestamp"] >= median_ts] if median_ts else []
    base_first = rate_of([r for r in population if r["timestamp"] < median_ts])[2] if median_ts else float("nan")
    base_second = rate_of([r for r in population if r["timestamp"] >= median_ts])[2] if median_ts else float("nan")
    k_fh, n_fh, rate_fh = rate_of(first_half)
    k_sh, n_sh, rate_sh = rate_of(second_half)
    uplift_fh = (rate_fh - base_first) if n_fh else float("nan")
    uplift_sh = (rate_sh - base_second) if n_sh else float("nan")

    # BUY/SELL robustness
    buy_group = [r for r in group if r["direction"] == "BUY"]
    sell_group = [r for r in group if r["direction"] == "SELL"]
    base_buy = rate_of([r for r in population if r["direction"] == "BUY"])[2]
    base_sell = rate_of([r for r in population if r["direction"] == "SELL"])[2]
    k_buy, n_buy, rate_buy = rate_of(buy_group)
    k_sell, n_sell, rate_sell = rate_of(sell_group)
    uplift_buy = (rate_buy - base_buy) if n_buy else float("nan")
    uplift_sell = (rate_sell - base_sell) if n_sell else float("nan")

    result = {
        "hint": name, "n_total": base_n, "n_group": gn, "base_rate": base_rate, "group_rate": grate,
        "ci95_group": [lo, hi], "uplift_absolute": uplift_abs, "uplift_relative": uplift_rel,
        "diff_vs_rest": diff_rest, "z": z, "p_value": pval,
        "first_half": {"n": n_fh, "rate": rate_fh, "base": base_first, "uplift": uplift_fh},
        "second_half": {"n": n_sh, "rate": rate_sh, "base": base_second, "uplift": uplift_sh},
        "buy": {"n": n_buy, "rate": rate_buy, "base": base_buy, "uplift": uplift_buy},
        "sell": {"n": n_sell, "rate": rate_sell, "base": base_sell, "uplift": uplift_sell},
    }

    # --- gate di classificazione ---
    reasons = []
    same_dir_exp1 = (not math.isnan(uplift_abs)) and ((uplift_abs > 0) == (exp1_uplift_sign > 0))
    if not same_dir_exp1:
        result["classification"] = "REFUTED"
        result["reason"] = "uplift non nella stessa direzione di Experiment 1 (o non misurabile)"
        return result
    if gn < MIN_N_GROUP:
        result["classification"] = "INCONCLUSIVE_FINAL"
        result["reason"] = f"campione insufficiente nel gruppo (n={gn} < {MIN_N_GROUP})"
        return result
    if abs(uplift_abs) < MIN_EFFECT:
        result["classification"] = "REFUTED"
        result["reason"] = f"effetto sotto soglia materiale ({uplift_abs:+.3f} < {MIN_EFFECT})"
        return result
    # coerenza fra le due meta' temporali (stesso segno dell'uplift complessivo, se misurabili)
    half_ok = True
    if n_fh >= MIN_N_HALF and n_sh >= MIN_N_HALF and not math.isnan(uplift_fh) and not math.isnan(uplift_sh):
        half_ok = (uplift_fh > 0) == (uplift_sh > 0) == (uplift_abs > 0)
    else:
        reasons.append("almeno una meta' temporale con campione insufficiente per un giudizio pieno")
    if not half_ok:
        result["classification"] = "INCONCLUSIVE_FINAL"
        result["reason"] = "direzione non coerente fra prima e seconda meta' temporale"
        return result
    # inversione distruttiva BUY/SELL: un lato fortemente NEGATIVO che nasconde l'altro fortemente positivo
    destructive = False
    if n_buy >= MIN_N_SIDE and n_sell >= MIN_N_SIDE:
        if (uplift_buy < -MIN_EFFECT and uplift_sell > 0) or (uplift_sell < -MIN_EFFECT and uplift_buy > 0):
            destructive = True
    else:
        reasons.append("BUY/SELL non entrambi con campione sufficiente per un giudizio pieno robustezza")
    if destructive:
        result["classification"] = "INCONCLUSIVE_FINAL"
        result["reason"] = "inversione distruttiva fra BUY e SELL"
        return result

    result["classification"] = "CONFIRMED"
    result["reason"] = "uplift materiale, stessa direzione di Experiment 1, coerente fra meta' temporali, " \
                        "nessuna inversione distruttiva BUY/SELL, campione adeguato" + \
                        (f" (note: {'; '.join(reasons)})" if reasons else "")
    return result


def main():
    all_events = load_w0_events()
    valid_population, pop_stats = build_valid_population(all_events)

    print("=== PERIODO INDIPENDENTE ===")
    print(f"w0: {W0['from']} -> {W0['to']} (nessun overlap con w1-w4, 2026-01-01 -> 2026-08-25)")
    print("\n=== POPULATION ===")
    print(json.dumps(pop_stats, indent=2))

    base_k, base_n, base_rate = rate_of(valid_population)
    lo_b, hi_b = wilson_ci(base_k, base_n)
    print(f"\n=== BASE RATE (TRUE_BREAK_OBSERVED, w0) ===")
    print(f"{base_k}/{base_n} = {base_rate:.3f}  CI95=[{lo_b:.3f},{hi_b:.3f}]")

    print(f"\n=== SOGLIE CONGELATE (da Experiment 1, non ricalcolate) ===")
    print(f"penetration_per_atr > {PEN_ATR_Q4_THRESHOLD}")
    print(f"age_seconds < {AGE_THRESHOLD_SECONDS}")
    print(f"source_tf == '{SOURCE_TF_TARGET}'")

    results = []
    results.append(test_hint(
        "penetration_per_atr_Q4", valid_population,
        lambda r: r["penetration_per_atr"] is not None and r["penetration_per_atr"] > PEN_ATR_Q4_THRESHOLD,
        exp1_uplift_sign=+1))
    results.append(test_hint(
        "age_seconds_lt_1h", valid_population,
        lambda r: r["age_seconds"] is not None and r["age_seconds"] < AGE_THRESHOLD_SECONDS,
        exp1_uplift_sign=+1))
    results.append(test_hint(
        "source_tf_D1", valid_population,
        lambda r: r["source_tf"] == SOURCE_TF_TARGET,
        exp1_uplift_sign=+1))

    print("\n=== RISULTATI PER HINT ===")
    for r in results:
        print(f"\n--- {r['hint']} ---")
        print(f"n_group={r['n_group']}  base_rate={r['base_rate']:.3f}  group_rate={r['group_rate']:.3f}  "
              f"CI95={[round(x,3) for x in r['ci95_group']]}")
        print(f"uplift_assoluto={r['uplift_absolute']:+.3f}  uplift_relativo={r['uplift_relative']:+.1%}  "
              f"diff_vs_rest={r['diff_vs_rest']:+.3f}  z={r['z']:.2f}  p={r['p_value']:.4f}")
        print(f"prima meta': n={r['first_half']['n']} rate={r['first_half']['rate']:.3f} uplift={r['first_half']['uplift']:+.3f}   "
              f"seconda meta': n={r['second_half']['n']} rate={r['second_half']['rate']:.3f} uplift={r['second_half']['uplift']:+.3f}")
        print(f"BUY: n={r['buy']['n']} rate={r['buy']['rate']:.3f} uplift={r['buy']['uplift']:+.3f}   "
              f"SELL: n={r['sell']['n']} rate={r['sell']['rate']:.3f} uplift={r['sell']['uplift']:+.3f}")
        print(f"CLASSIFICAZIONE: {r['classification']}  ({r['reason']})")

    n_confirmed = sum(1 for r in results if r["classification"] == "CONFIRMED")
    verdict = "STRUCTURAL_HYPOTHESIS_CONFIRMED" if n_confirmed > 0 else "STRUCTURAL_THREAD_2_NO_CONFIRMED_EDGE"

    output = {
        "generated_at": datetime.now().isoformat(),
        "independent_period": W0,
        "population": pop_stats,
        "base_rate": {"k": base_k, "n": base_n, "rate": base_rate, "ci95": [lo_b, hi_b]},
        "frozen_thresholds": {
            "penetration_per_atr_q4": PEN_ATR_Q4_THRESHOLD,
            "age_seconds": AGE_THRESHOLD_SECONDS,
            "source_tf": SOURCE_TF_TARGET,
        },
        "results": results,
        "n_confirmed": n_confirmed,
        "verdict": verdict,
    }

    def _default(o):
        return str(o)

    with open(os.path.join(OUT_DIR, "experiment_2_results.json"), "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, default=_default)

    pop_fields = ["episode_id", "timestamp", "outcome", "source_tf", "direction", "penetration_per_atr", "age_seconds"]
    with open(os.path.join(OUT_DIR, "experiment_2_population.csv"), "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=pop_fields)
        writer.writeheader()
        for r in valid_population:
            writer.writerow({k: r[k] for k in pop_fields})

    print(f"\n=== VERDICT: {verdict} ({n_confirmed}/3 confermati) ===")
    print(f"Output salvato in {OUT_DIR}")


if __name__ == "__main__":
    main()
