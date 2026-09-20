#!/usr/bin/env python3
"""Phase 7.4A Dependence Validity Gate sec.3 - calibra il gate su
simulazioni AR(1) SINTETICHE (phi=0.0/0.1/0.2/0.3/0.5/0.7). Per ogni
phi: empirical Type-I error del block_sign_flip_permutation_p (gia'
noto da null_calibration_simulation.py, ricalcolato qui per accoppiarlo
direttamente alla diagnostica), i valori medi della diagnostica di
dipendenza (ACF lag1, Ljung-Box, ESS ratio) e il verdetto del gate con
le soglie congelate in dependence_validity_gate.py - MAI scelte dopo
aver visto SEQ-0015."""
import json
import os
import sys
import time

import numpy as np

PHASE74_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(PHASE74_DIR, "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase7", "engine"))
from matched_pair_permutation_test import block_sign_flip_permutation_p  # noqa: E402
from dependence_validity_gate import compute_dependence_diagnostics, classify_dependence_validity, THRESHOLDS_FROZEN  # noqa: E402

ALPHAS = [0.01, 0.05, 0.10]
N_REPS = 1000
N_BOOT = 1000
N = 30
PHIS = [0.0, 0.1, 0.2, 0.3, 0.5, 0.7]


def gen_ar1(rng, phi, n=N):
    eps = rng.normal(0.0, 1.0, n)
    x = np.empty(n)
    x[0] = eps[0]
    for t in range(1, n):
        x[t] = phi * x[t - 1] + eps[t] * np.sqrt(1 - phi ** 2)
    return x


def run_phi(phi):
    rng = np.random.default_rng(hash(f"gatecal_{phi}") % (2**32))
    pvals, acf1s, lb_ps, ess_rs = [], [], [], []
    verdict_counts = {"INFERENCE_VALID": 0, "DEPENDENCE_SENSITIVE": 0, "INFERENCE_INVALID_DEPENDENCE": 0}
    t0 = time.time()
    for i in range(N_REPS):
        d = gen_ar1(rng, phi)
        r = block_sign_flip_permutation_p(d, n_boot=N_BOOT, seed=i)
        pvals.append(r["p_value"])
        diag = compute_dependence_diagnostics(d, n_boot=200, seed=i)  # n_boot ridotto qui: solo per la diagnostica ESS, non per il p-value
        acf1s.append(diag["acf_lag1"])
        lb_ps.append(diag["ljung_box_p_h3"])
        ess_rs.append(diag["ess_ratio"])
        cls = classify_dependence_validity(diag)
        verdict_counts[cls["state"]] += 1
    elapsed = time.time() - t0
    pvals = np.array(pvals)
    n_reps = len(pvals)
    majority_verdict = max(verdict_counts, key=verdict_counts.get)
    return {
        "phi": phi, "n_reps": n_reps, "elapsed_sec": round(elapsed, 1),
        "empirical_type1_error": {str(a): float(np.mean(pvals <= a)) for a in ALPHAS},
        "mean_acf_lag1": float(np.mean(acf1s)), "mean_abs_acf_lag1": float(np.mean(np.abs(acf1s))),
        "mean_ljung_box_p": float(np.mean(lb_ps)), "frac_ljung_box_flags_at_05": float(np.mean(np.array(lb_ps) < 0.05)),
        "mean_ess_ratio": float(np.mean(ess_rs)),
        "gate_verdict_distribution": verdict_counts,
        "gate_majority_verdict": majority_verdict,
    }


def main():
    rows = []
    for phi in PHIS:
        row = run_phi(phi)
        rows.append(row)
        print(f"phi={phi}: Type-I@.05={row['empirical_type1_error']['0.05']:.3f}  "
              f"mean|ACF1|={row['mean_abs_acf_lag1']:.3f}  mean_LB_p={row['mean_ljung_box_p']:.3f}  "
              f"mean_ESS/n={row['mean_ess_ratio']:.3f}  gate={row['gate_majority_verdict']} {row['gate_verdict_distribution']}")

    payload = {
        "principle": "Calibrazione ex-ante del Dependence Validity Gate su simulazioni AR(1) sintetiche - nessun dato NEXUS. Il gate deve iniziare a segnalare DEPENDENCE_SENSITIVE/INFERENCE_INVALID_DEPENDENCE proprio dove l'empirical Type-I error diventa materialmente anti-conservativo.",
        "n_reps_per_phi": N_REPS, "n_boot_per_replicate": N_BOOT, "n_independent_view": N,
        "frozen_thresholds": THRESHOLDS_FROZEN,
        "calibration_curve": rows,
    }
    out_path = os.path.join(PHASE74_DIR, "phase7_4_dependence_gate_calibration_v1.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)
    print(f"\nScritto: {out_path}")
    return payload


if __name__ == "__main__":
    main()
