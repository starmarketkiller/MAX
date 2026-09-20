#!/usr/bin/env python3
"""Phase 7.4A Final Gate Calibration / End-to-End Inference Validation.

Valida SINTETICAMENTE la pipeline COMPLETA gia' congelata in b825012:
  diagnostics -> classify_dependence_validity() -> p_value_for_bh()
  -> multiple_testing_v2.benjamini_hochberg (via dependence_gated_bh_family)

NON modifica detector/soglia/episode rule/matched baseline/gate
thresholds/BH policy - li IMPORTA cosi' come sono congelati e li
esercita su dati sintetici. Nessun dato NEXUS. Eseguito a sezioni
(CLI arg) per stare dentro i limiti di tempo di ogni chiamata."""
import json
import math
import os
import sys
import time

import numpy as np

PHASE74_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(PHASE74_DIR, "..", "..", "..", ".."))
ENGINE_DIR = os.path.join(ROOT, "server", "research_scripts", "phase7", "engine")
sys.path.insert(0, ENGINE_DIR)

from matched_pair_permutation_test import block_sign_flip_permutation_p  # noqa: E402
from dependence_validity_gate import (  # noqa: E402
    compute_dependence_diagnostics, classify_dependence_validity, p_value_for_bh,
    INFERENCE_VALID, DEPENDENCE_SENSITIVE, INFERENCE_INVALID_DEPENDENCE,
)
from dependence_gated_bh_family import build_gated_bh_family  # noqa: E402

ALPHAS = [0.01, 0.05, 0.10]
N_BOOT_TEST = 500       # ridotto da 1000 per lo studio di validazione su larga scala (gia' verificato non
N_BOOT_DIAG = 300       # cambiare le conclusioni qualitative nella patch precedente) - dichiarato, non nascosto.
Q_FDR = 0.10


def mc_tolerance(true_rate, n_reps, n_sigma=3):
    """Tolleranza Monte Carlo esplicita (sec.8): n_sigma deviazioni standard
    binomiali attorno al tasso nominale, motivata dal numero di repliche -
    congelata PRIMA di guardare i risultati."""
    se = math.sqrt(true_rate * (1 - true_rate) / n_reps)
    return n_sigma * se


def gen_ar1(rng, phi, n, mean_shift=0.0):
    eps = rng.normal(0.0, 1.0, n)
    x = np.empty(n)
    x[0] = eps[0] + mean_shift
    for t in range(1, n):
        x[t] = phi * x[t - 1] + eps[t] * np.sqrt(1 - phi ** 2) + mean_shift * (1 - phi)
    return x


def run_cell(d, seed):
    """Pipeline ESATTA congelata (sec.2) - nessuna scorciatoia parallela."""
    r = block_sign_flip_permutation_p(d, n_boot=N_BOOT_TEST, seed=seed)
    diag = compute_dependence_diagnostics(d, n_boot=N_BOOT_DIAG, seed=seed)
    cls = classify_dependence_validity(diag)
    bh_p = p_value_for_bh(r["raw_p_value"] if "raw_p_value" in r else r["p_value"], cls["state"])
    return {"raw_p": r["p_value"], "state": cls["state"], "bh_p": bh_p,
            "asymmetry_sensitive": cls["asymmetry_sensitive"]}


# ---------------- Sezione 1 + 7: conditional calibration / gate-selection bias ----------------

def section1_conditional_calibration(phis=(0.0, 0.1, 0.2, 0.3, 0.5, 0.7), n=30, n_reps=2000):
    rows = []
    for phi in phis:
        rng = np.random.default_rng(hash(f"s1_{phi}_{n}") % (2**32))
        t0 = time.time()
        states, raw_ps, bh_ps = [], [], []
        for i in range(n_reps):
            d = gen_ar1(rng, phi, n)
            res = run_cell(d, seed=i)
            states.append(res["state"])
            raw_ps.append(res["raw_p"])
        elapsed = time.time() - t0
        raw_ps = np.array(raw_ps)
        states = np.array(states)
        n_valid = int(np.sum(states == INFERENCE_VALID))
        n_sensitive = int(np.sum(states == DEPENDENCE_SENSITIVE))
        n_invalid = int(np.sum(states == INFERENCE_INVALID_DEPENDENCE))

        row = {"phi": phi, "n": n, "n_reps": n_reps, "elapsed_sec": round(elapsed, 1),
               "n_total": n_reps, "n_INFERENCE_VALID": n_valid, "n_DEPENDENCE_SENSITIVE": n_sensitive,
               "n_INVALID": n_invalid}
        for a in ALPHAS:
            raw_rej = float(np.mean(raw_ps <= a))
            if n_valid > 0:
                cond_rej = float(np.mean(raw_ps[states == INFERENCE_VALID] <= a))
            else:
                cond_rej = None
            gated_rej_overall = float(np.mean((states == INFERENCE_VALID) & (raw_ps <= a)))
            row[f"raw_rejection_rate_{a}"] = raw_rej
            row[f"rejection_rate_among_INFERENCE_VALID_{a}"] = cond_rej
            row[f"false_positive_rate_after_gate_over_all_replicates_{a}"] = gated_rej_overall
            row[f"mc_tolerance_{a}"] = mc_tolerance(a, n_valid if n_valid > 30 else n_reps)
        rows.append(row)
        print(f"[sec1] phi={phi} n={n}: n_valid={n_valid}/{n_reps} ({100*n_valid/n_reps:.1f}%) "
              f"cond_rej@.05={row['rejection_rate_among_INFERENCE_VALID_0.05']} "
              f"gated_overall@.05={row['false_positive_rate_after_gate_over_all_replicates_0.05']:.4f} "
              f"({elapsed:.1f}s)")
    return rows


# ---------------- Sezione 3: full BH-FDR family simulation ----------------

def build_family_cells(rng, spec, seed_base):
    """spec: lista di (n_cells, phi, mean_shift) - genera esattamente
    sum(n_cells) celle nell'ordine dichiarato."""
    cells = []
    idx = 0
    for n_cells, phi, mean_shift in spec:
        for _ in range(n_cells):
            d = gen_ar1(rng, phi, n=30, mean_shift=mean_shift)
            cells.append({"cell_id": f"CELL-{idx}", "candidate_id": f"CAND-{idx % 3}", "outcome_id": f"OUT-{idx % 7}",
                         "d_values": list(d), "raw_p_value": block_sign_flip_permutation_p(d, n_boot=N_BOOT_TEST, seed=seed_base + idx)["p_value"],
                         "_true_effect": mean_shift != 0.0})
            idx += 1
    return cells


def run_family_scenario(name, spec, n_true_effects, n_family_reps, q=Q_FDR):
    rng = np.random.default_rng(hash(f"fam_{name}") % (2**32))
    t0 = time.time()
    any_rejection = []
    fdps = []
    powers = []
    n_gated_list = []
    for rep in range(n_family_reps):
        cells = build_family_cells(rng, spec, seed_base=rep * 1000)
        result = build_gated_bh_family(cells, q=q, n_boot_diagnostics=N_BOOT_DIAG)
        sig_cells = [c for c in result["cells"] if c["bh_result"]["significant_at_q"]]
        n_sig = len(sig_cells)
        n_false_disc = sum(1 for c in sig_cells if not c["_true_effect"])
        fdp = n_false_disc / n_sig if n_sig > 0 else 0.0
        any_rejection.append(n_sig > 0)
        fdps.append(fdp)
        if n_true_effects > 0:
            n_true_positive = sum(1 for c in sig_cells if c["_true_effect"])
            powers.append(n_true_positive / n_true_effects)
        n_gated = result["n_by_dependence_state"][DEPENDENCE_SENSITIVE] + result["n_by_dependence_state"][INFERENCE_INVALID_DEPENDENCE]
        n_gated_list.append(n_gated)
    elapsed = time.time() - t0
    row = {
        "scenario": name, "n_family_reps": n_family_reps, "family_size": sum(s[0] for s in spec),
        "n_true_effects": n_true_effects, "elapsed_sec": round(elapsed, 1),
        "probability_any_rejection": float(np.mean(any_rejection)),
        "empirical_fdr": float(np.mean(fdps)),
        "mean_n_gated_to_p1": float(np.mean(n_gated_list)),
        "mc_tolerance_fdr": mc_tolerance(q, n_family_reps),
    }
    if n_true_effects > 0:
        row["power"] = float(np.mean(powers))
    print(f"[sec3] {name}: P(any_rej)={row['probability_any_rejection']:.4f} "
          f"empirical_FDR={row['empirical_fdr']:.4f} "
          f"{'power='+format(row.get('power', 0), '.4f') if n_true_effects else ''} "
          f"mean_n_gated={row['mean_n_gated_to_p1']:.2f} ({elapsed:.1f}s)")
    return row


def section3_bh_family_simulation(n_family_reps=300):
    rows = []
    # Global null, 21 celle iid.
    rows.append(run_family_scenario("global_null_iid_21_cells", [(21, 0.0, 0.0)], 0, n_family_reps))
    # sec.4 - dependence mixtures sotto H0 (nessun effetto vero, dipendenza eterogenea).
    rows.append(run_family_scenario("global_null_mixed_dependence_21_cells",
                                     [(6, 0.0, 0.0), (5, 0.2, 0.0), (5, 0.5, 0.0), (5, 0.7, 0.0)], 0, n_family_reps))
    # Mixed family: 14 null (iid) + 7 effetti veri (iid, mean_shift=0.8).
    rows.append(run_family_scenario("mixed_14null_7effect_iid", [(14, 0.0, 0.0), (7, 0.0, 0.8)], 7, n_family_reps))
    return rows


# ---------------- Sezione 5: sample-size sensitivity ----------------

def section5_sample_size_sensitivity(ns=(20, 30, 50, 100), phis=(0.0, 0.5), n_reps=1000):
    rows = []
    for n in ns:
        for phi in phis:
            rng = np.random.default_rng(hash(f"s5_{n}_{phi}") % (2**32))
            t0 = time.time()
            states, raw_ps = [], []
            for i in range(n_reps):
                d = gen_ar1(rng, phi, n)
                res = run_cell(d, seed=i)
                states.append(res["state"])
                raw_ps.append(res["raw_p"])
            elapsed = time.time() - t0
            raw_ps = np.array(raw_ps)
            states = np.array(states)
            n_valid = int(np.sum(states == INFERENCE_VALID))
            cond_rej_05 = float(np.mean(raw_ps[states == INFERENCE_VALID] <= 0.05)) if n_valid > 0 else None
            row = {"n": n, "phi": phi, "n_reps": n_reps, "elapsed_sec": round(elapsed, 1),
                   "pct_INFERENCE_VALID": n_valid / n_reps,
                   "raw_rejection_rate_0.05": float(np.mean(raw_ps <= 0.05)),
                   "rejection_rate_among_INFERENCE_VALID_0.05": cond_rej_05}
            rows.append(row)
            print(f"[sec5] n={n} phi={phi}: pct_valid={row['pct_INFERENCE_VALID']:.3f} "
                  f"cond_rej@.05={cond_rej_05} ({elapsed:.1f}s)")
    return rows


# ---------------- Sezione 6: asymmetry / sign-flip assumption ----------------

def gen_symmetric_gaussian(rng, n):
    return rng.normal(0.0, 1.0, n)


def gen_mild_skew(rng, n):
    x = rng.gamma(shape=5.0, scale=1.0, size=n)
    return x - x.mean()  # ricentrato a media 0, skew moderato


def gen_strong_skew(rng, n):
    x = rng.exponential(1.0, n)
    return x - x.mean()  # skew forte (esponenziale)


def gen_heavy_tail_symmetric(rng, n):
    return rng.standard_t(df=3, size=n)  # code pesanti, simmetrica


def gen_heavy_tail_skewed(rng, n):
    x = rng.standard_t(df=3, size=n)
    x = np.where(x > 0, x * 1.8, x)  # asimmetrizza artificialmente una t di Student
    return x - x.mean()


SKEW_SCENARIOS = {
    "symmetric_gaussian": gen_symmetric_gaussian,
    "mild_skew_gamma": gen_mild_skew,
    "strong_skew_exponential": gen_strong_skew,
    "heavy_tail_symmetric_t3": gen_heavy_tail_symmetric,
    "heavy_tail_skewed_t3": gen_heavy_tail_skewed,
}


def section6_asymmetry_sensitivity(n=30, n_reps=1500):
    rows = []
    for name, gen in SKEW_SCENARIOS.items():
        rng = np.random.default_rng(hash(f"s6_{name}") % (2**32))
        t0 = time.time()
        states, raw_ps, asym_flags = [], [], []
        for i in range(n_reps):
            d = gen(rng, n)
            res = run_cell(d, seed=i)
            states.append(res["state"])
            raw_ps.append(res["raw_p"])
            asym_flags.append(res["asymmetry_sensitive"])
        elapsed = time.time() - t0
        raw_ps = np.array(raw_ps)
        states = np.array(states)
        asym_flags = np.array(asym_flags)
        n_valid = int(np.sum(states == INFERENCE_VALID))
        cond_rej = {str(a): (float(np.mean(raw_ps[states == INFERENCE_VALID] <= a)) if n_valid > 0 else None) for a in ALPHAS}
        gated_overall = {str(a): float(np.mean((states == INFERENCE_VALID) & (raw_ps <= a))) for a in ALPHAS}
        row = {"scenario": name, "n": n, "n_reps": n_reps, "elapsed_sec": round(elapsed, 1),
               "asymmetry_sensitive_rate": float(np.mean(asym_flags)),
               "pct_INFERENCE_VALID": n_valid / n_reps,
               "conditional_type1_among_INFERENCE_VALID": cond_rej,
               "gated_type1_overall": gated_overall}
        rows.append(row)
        print(f"[sec6] {name}: asym_rate={row['asymmetry_sensitive_rate']:.3f} "
              f"pct_valid={row['pct_INFERENCE_VALID']:.3f} cond_rej@.05={cond_rej['0.05']} ({elapsed:.1f}s)")
    return rows


def main():
    section = sys.argv[1] if len(sys.argv) > 1 else "all"
    out = {}
    if section in ("1", "all"):
        out["section1_conditional_calibration"] = section1_conditional_calibration()
        with open(os.path.join(PHASE74_DIR, "_val_section1.json"), "w", encoding="utf-8") as f:
            json.dump(out["section1_conditional_calibration"], f, indent=2)
    if section in ("3", "all"):
        out["section3_bh_family_simulation"] = section3_bh_family_simulation()
        with open(os.path.join(PHASE74_DIR, "_val_section3.json"), "w", encoding="utf-8") as f:
            json.dump(out["section3_bh_family_simulation"], f, indent=2)
    if section in ("5", "all"):
        out["section5_sample_size_sensitivity"] = section5_sample_size_sensitivity()
        with open(os.path.join(PHASE74_DIR, "_val_section5.json"), "w", encoding="utf-8") as f:
            json.dump(out["section5_sample_size_sensitivity"], f, indent=2)
    if section in ("6", "all"):
        out["section6_asymmetry_sensitivity"] = section6_asymmetry_sensitivity()
        with open(os.path.join(PHASE74_DIR, "_val_section6.json"), "w", encoding="utf-8") as f:
            json.dump(out["section6_asymmetry_sensitivity"], f, indent=2)
    print("\nDONE:", section)


if __name__ == "__main__":
    main()
