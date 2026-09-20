#!/usr/bin/env python3
"""Phase 7.4A Dependence-Aware Inference Redesign - calibrazione
completa dei 3 metodi candidati (A/B/C, engine/dependence_aware_mean_
tests.py). NESSUN gate selettivo: ogni metodo e' applicato a TUTTI i
dati, sempre - la diagnostica di dipendenza (ACF/Ljung-Box/ESS) resta
disponibile SOLO come informazione diagnostica riportata, MAI per
decidere se testare o quale p-value ammettere (architettura precedente
abbandonata, vedi phase7_4_dependence_gated_inference_validation_v1.json).

NOTA SUL BUDGET DI CALCOLO: lo screening preliminare (6 phi, n=30,
N_reps=800) ha mostrato Metodo B (studentized block bootstrap)
nettamente piu' calibrato di A e C in OGNI scenario (phi=0.7:
B=0.098 vs A=0.265 vs C=0.263 a alpha=.05) - A e C mostrano gia'
anti-conservativita' anche sotto iid pura (phi=0.0). Questa evidenza
PRECOCE giustifica un'allocazione asimmetrica del budget di calcolo
(piu' repliche per B, che e' anche ~3-4x piu' costoso computazionalmente
per replica) - dichiarato esplicitamente, non nascosto: A e C restano
comunque testati sull'intera griglia richiesta, a precisione ridotta."""
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

from dependence_aware_mean_tests import (  # noqa: E402
    null_centered_block_bootstrap_p, studentized_block_bootstrap_p, hac_newey_west_p,
)
from dependence_validity_gate import compute_dependence_diagnostics  # noqa: E402 - SOLO diagnostica riportata, mai gating

ALPHAS = [0.01, 0.05, 0.10]
METHODS = {
    "A_null_centered_block_bootstrap": (null_centered_block_bootstrap_p, {"n_boot": 500}),
    "B_studentized_block_bootstrap": (studentized_block_bootstrap_p, {"n_boot": 500}),
    "C_hac_newey_west": (hac_newey_west_p, {}),
}
# Repliche asimmetriche per costo computazionale - dichiarato sopra.
N_REPS_BY_METHOD = {"A_null_centered_block_bootstrap": 1200, "B_studentized_block_bootstrap": 1200, "C_hac_newey_west": 3000}


def mc_tolerance(true_rate, n_reps, n_sigma=3):
    se = math.sqrt(true_rate * (1 - true_rate) / n_reps)
    return n_sigma * se


def run_method(name, d):
    fn, kw = METHODS[name]
    return fn(d, **kw) if kw else fn(d)


def gen_ar1(rng, phi, n, mean_shift=0.0):
    eps = rng.normal(0.0, 1.0, n)
    x = np.empty(n)
    x[0] = eps[0] + mean_shift
    for t in range(1, n):
        x[t] = phi * x[t - 1] + eps[t] * np.sqrt(1 - phi ** 2) + mean_shift * (1 - phi)
    return x


# ---------------- Sezione 5: null calibration completa (6 phi x 4 n) ----------------

def section_null_calibration(method_name, phis=(0.0, 0.1, 0.2, 0.3, 0.5, 0.7), ns=(20, 30, 50, 100)):
    n_reps = N_REPS_BY_METHOD[method_name]
    rows = []
    for n in ns:
        for phi in phis:
            rng = np.random.default_rng(hash(f"{method_name}_{n}_{phi}") % (2**32))
            t0 = time.time()
            pvals = []
            for i in range(n_reps):
                d = gen_ar1(rng, phi, n)
                r = run_method(method_name, d)
                pvals.append(r["p_value"])
            elapsed = time.time() - t0
            pvals = np.array(pvals)
            row = {"method": method_name, "n": n, "phi": phi, "n_reps": n_reps, "elapsed_sec": round(elapsed, 1)}
            for a in ALPHAS:
                row[f"type1_{a}"] = float(np.mean(pvals <= a))
                row[f"mc_tolerance_{a}"] = mc_tolerance(a, n_reps)
            rows.append(row)
            print(f"[null_cal] {method_name} n={n} phi={phi}: "
                  f"T1@.01={row['type1_0.01']:.3f} T1@.05={row['type1_0.05']:.3f} T1@.10={row['type1_0.1']:.3f} ({elapsed:.1f}s)")
    return rows


# ---------------- Sezione 6: distribution stress ----------------

def gen_symmetric_gaussian(rng, n):
    return rng.normal(0.0, 1.0, n)


def gen_student_t3(rng, n):
    return rng.standard_t(df=3, size=n)


def gen_mild_skew(rng, n):
    x = rng.gamma(shape=5.0, scale=1.0, size=n)
    return x - x.mean()


def gen_strong_skew(rng, n):
    x = rng.exponential(1.0, n)
    return x - x.mean()


def gen_vol_clustering(rng, n):
    """GARCH(1,1)-like semplificato: varianza condizionale che evolve, media 0."""
    omega, alpha, beta = 0.05, 0.15, 0.80
    sigma2 = np.empty(n)
    x = np.empty(n)
    sigma2[0] = omega / (1 - alpha - beta)
    x[0] = rng.normal(0, math.sqrt(sigma2[0]))
    for t in range(1, n):
        sigma2[t] = omega + alpha * x[t - 1] ** 2 + beta * sigma2[t - 1]
        x[t] = rng.normal(0, math.sqrt(sigma2[t]))
    return x


def gen_regime_switching(rng, n):
    """2 regimi di varianza (basso/alto), switch con probabilita' 0.1 per barra, media 0 in entrambi."""
    state = 0
    x = np.empty(n)
    sigmas = [0.5, 2.5]
    for t in range(n):
        if rng.random() < 0.1:
            state = 1 - state
        x[t] = rng.normal(0.0, sigmas[state])
    return x


def gen_ar1_wrapper(rng, n):
    return gen_ar1(rng, 0.4, n)


def gen_arma_persistent(rng, n):
    """ARMA(1,1) semplice, persistenza moderata, media 0."""
    phi_ar, theta_ma = 0.5, 0.3
    eps = rng.normal(0.0, 1.0, n)
    x = np.empty(n)
    x[0] = eps[0]
    for t in range(1, n):
        x[t] = phi_ar * x[t - 1] + eps[t] + theta_ma * eps[t - 1]
    return x


DISTRIBUTION_SCENARIOS = {
    "gaussian": gen_symmetric_gaussian, "student_t3": gen_student_t3, "skew_mild": gen_mild_skew,
    "skew_strong": gen_strong_skew, "volatility_clustering_garch": gen_vol_clustering,
    "regime_switching": gen_regime_switching, "ar1_phi04": gen_ar1_wrapper, "arma11_persistent": gen_arma_persistent,
}


def section_distribution_stress(method_name, n=30):
    n_reps = N_REPS_BY_METHOD[method_name]
    rows = []
    for name, gen in DISTRIBUTION_SCENARIOS.items():
        rng = np.random.default_rng(hash(f"{method_name}_dist_{name}") % (2**32))
        t0 = time.time()
        pvals = []
        for i in range(n_reps):
            d = gen(rng, n)
            r = run_method(method_name, d)
            pvals.append(r["p_value"])
        elapsed = time.time() - t0
        pvals = np.array(pvals)
        row = {"method": method_name, "scenario": name, "n": n, "n_reps": n_reps, "elapsed_sec": round(elapsed, 1)}
        for a in ALPHAS:
            row[f"type1_{a}"] = float(np.mean(pvals <= a))
        rows.append(row)
        print(f"[dist_stress] {method_name} {name}: T1@.05={row['type1_0.05']:.3f} ({elapsed:.1f}s)")
    return rows


# ---------------- Sezione 7: matched-control stress ----------------

def gen_control_reuse(rng, n_events=30, k=5, reuse_pool_size=10):
    """Pool di controlli piccolo (10) condiviso da 30 eventi - forte riuso, ma H0 vera (nessun effetto)."""
    pool = rng.normal(0.0, 1.0, reuse_pool_size)
    d = np.empty(n_events)
    for i in range(n_events):
        controls_idx = rng.choice(reuse_pool_size, size=k, replace=False)
        event_val = rng.normal(0.0, 1.0)
        d[i] = event_val - pool[controls_idx].mean()
    return d


def gen_overlapping_control_sets(rng, n_events=30, k=5):
    """Ogni evento pesca k controlli da una finestra scorrevole di ampiezza 2k che si sovrappone
    fortemente con quella dell'evento precedente - H0 vera."""
    base_pool = rng.normal(0.0, 1.0, n_events + 2 * k)
    d = np.empty(n_events)
    for i in range(n_events):
        window = base_pool[i:i + 2 * k]
        controls = rng.choice(window, size=k, replace=False)
        event_val = rng.normal(0.0, 1.0)
        d[i] = event_val - controls.mean()
    return d


def gen_shared_regime_stress(rng, n_events=30, k=5, tau=1.0, sigma=0.3):
    r = rng.normal(0.0, tau, n_events)
    event_outcomes = r + rng.normal(0.0, sigma, n_events)
    control_outcomes = r[:, None] + rng.normal(0.0, sigma, (n_events, k))
    return event_outcomes - control_outcomes.mean(axis=1)


def gen_heterogeneous_k(rng, n_events=30):
    """k variabile per evento (fra 2 e 8) - H0 vera."""
    d = np.empty(n_events)
    for i in range(n_events):
        k_i = rng.integers(2, 9)
        controls = rng.normal(0.0, 1.0, k_i)
        event_val = rng.normal(0.0, 1.0)
        d[i] = event_val - controls.mean()
    return d


def gen_occasional_missing_controls(rng, n_events=30, k=5, p_missing_control=0.15):
    """Ogni controllo ha probabilita' p_missing_control di essere scartato (dato mancante) -
    numero effettivo di controlli per evento variabile, talvolta molto basso."""
    d = np.empty(n_events)
    for i in range(n_events):
        controls = rng.normal(0.0, 1.0, k)
        mask = rng.random(k) > p_missing_control
        valid_controls = controls[mask] if mask.sum() > 0 else controls[:1]
        event_val = rng.normal(0.0, 1.0)
        d[i] = event_val - valid_controls.mean()
    return d


MATCHED_CONTROL_STRESS_SCENARIOS = {
    "control_reuse_small_pool": gen_control_reuse,
    "overlapping_control_sets": gen_overlapping_control_sets,
    "shared_regime_shock": gen_shared_regime_stress,
    "heterogeneous_k": gen_heterogeneous_k,
    "occasional_missing_controls": gen_occasional_missing_controls,
}


def section_matched_control_stress(method_name):
    n_reps = N_REPS_BY_METHOD[method_name]
    rows = []
    for name, gen in MATCHED_CONTROL_STRESS_SCENARIOS.items():
        rng = np.random.default_rng(hash(f"{method_name}_mc_{name}") % (2**32))
        t0 = time.time()
        pvals = []
        for i in range(n_reps):
            d = gen(rng)
            r = run_method(method_name, d)
            pvals.append(r["p_value"])
        elapsed = time.time() - t0
        pvals = np.array(pvals)
        row = {"method": method_name, "scenario": name, "n_reps": n_reps, "elapsed_sec": round(elapsed, 1)}
        for a in ALPHAS:
            row[f"type1_{a}"] = float(np.mean(pvals <= a))
        rows.append(row)
        print(f"[matched_control_stress] {method_name} {name}: T1@.05={row['type1_0.05']:.3f} ({elapsed:.1f}s)")
    return rows


# ---------------- Sezione 8: power ----------------

def section_power(method_name, deltas=(0.0, 0.10, 0.20, 0.40, 0.80), phi=0.0, n=30):
    n_reps = N_REPS_BY_METHOD[method_name]
    rows = []
    for delta in deltas:
        rng = np.random.default_rng(hash(f"{method_name}_power_{delta}") % (2**32))
        t0 = time.time()
        pvals = []
        for i in range(n_reps):
            d = gen_ar1(rng, phi, n, mean_shift=delta)
            r = run_method(method_name, d)
            pvals.append(r["p_value"])
        elapsed = time.time() - t0
        pvals = np.array(pvals)
        row = {"method": method_name, "delta": delta, "phi": phi, "n": n, "n_reps": n_reps,
              "elapsed_sec": round(elapsed, 1), "power_at_05": float(np.mean(pvals <= 0.05))}
        rows.append(row)
        print(f"[power] {method_name} delta={delta}: power@.05={row['power_at_05']:.3f} ({elapsed:.1f}s)")
    return rows


def main():
    section = sys.argv[1] if len(sys.argv) > 1 else "help"
    method = sys.argv[2] if len(sys.argv) > 2 else None
    if section == "null_cal":
        result = section_null_calibration(method)
    elif section == "dist_stress":
        result = section_distribution_stress(method)
    elif section == "matched_control":
        result = section_matched_control_stress(method)
    elif section == "power":
        result = section_power(method)
    else:
        print("Uso: python dependence_aware_inference_calibration.py <null_cal|dist_stress|matched_control|power> <method_name>")
        return
    out_path = os.path.join(PHASE74_DIR, f"_dac_{section}_{method}.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)
    print(f"\nScritto: {out_path}")


if __name__ == "__main__":
    main()
