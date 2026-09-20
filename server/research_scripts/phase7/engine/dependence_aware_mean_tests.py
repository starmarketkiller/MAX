#!/usr/bin/env python3
"""Phase 7.4A Dependence-Aware Inference Redesign - 3 metodi candidati
per testare H0: E[d]=0 su d_i = outcome(event_i) - mean(matched_controls_i),
INCORPORANDO la dipendenza seriale NEL TEST STESSO - nessuna diagnostica
seleziona post-hoc se il campione e' 'abbastanza indipendente' (il
Dependence Validity Gate della patch precedente e' stato dimostrato
soggetto a selection bias avverso, vedi phase7_4_dependence_gated_
inference_validation_v1.json - ARCHITETTURA ABBANDONATA, non riusata qui).

Metodo A - null-centered moving block bootstrap:
    observed_delta = mean(d)
    centered_i = d_i - observed_delta          # media ESATTAMENTE 0 per costruzione
    resample blocchi contigui da centered       # preserva dipendenza seriale
    T*_b = mean(resampled_centered)
    p = P(|T*_b| >= |observed_delta|)
Diverso da two_sample_block_bootstrap_percentile_p (REFUTATO, Phase 7.4A
Final Statistical Integrity Patch): quello ricampionava DUE campioni
osservati (evento/baseline) senza mai centrare esplicitamente su H0;
qui si centra UN campione (le differenze accoppiate d_i) esattamente
su H0 PRIMA di ricampionare - la distribuzione nulla e' vera per
costruzione, non un'inversione di CI sui dati osservati.

Metodo B - studentized block bootstrap:
    T_obs = mean(d) / SE_block(d)
    per ogni replica: ricampiona blocchi da centered, ricalcola SE_block
    sulla replica stessa, T*_b = mean(resampled)/SE_block(resampled)
    p = P(|T*_b| >= |T_obs|)

Metodo C - HAC/Newey-West (benchmark trasparente, forma chiusa):
    T = mean(d) / HAC_SE(d), bandwidth = ceil(n^(1/3)) (STESSA formula
    strutturale gia' usata da block_length_default in tutto il progetto -
    non scelta guardando i dati), kernel di Bartlett, p-value da t(n-1)."""
import math
import os
import sys

import numpy as np
from scipy import stats

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase6_5"))
from block_bootstrap import block_length_default  # noqa: E402 - riuso della stessa formula L=ceil(n^(1/3))


def _clean(d_values):
    return np.asarray([v for v in d_values if v is not None and not (isinstance(v, float) and np.isnan(v))], dtype=float)


def _block_resample(x, L, n_blocks, rng):
    n = len(x)
    max_start = n - L
    starts = rng.integers(0, max_start + 1, size=n_blocks)
    return np.concatenate([x[s:s + L] for s in starts])[:n]


# ---------------- Metodo A ----------------

def null_centered_block_bootstrap_p(d_values, n_boot=1000, block_length=None, seed=42):
    d = _clean(d_values)
    n = len(d)
    if n < 5:
        return {"n": n, "note": "campione troppo piccolo", "method": "null_centered_block_bootstrap"}
    L = block_length or block_length_default(n)
    n_blocks = math.ceil(n / L)
    rng = np.random.default_rng(seed)

    observed_delta = float(d.mean())
    centered = d - observed_delta  # media ESATTAMENTE 0

    t_boot = np.empty(n_boot)
    for b in range(n_boot):
        resampled = _block_resample(centered, L, n_blocks, rng)
        t_boot[b] = resampled.mean()

    p_value = float((1 + np.sum(np.abs(t_boot) >= abs(observed_delta))) / (n_boot + 1))
    return {"n": n, "block_length": L, "n_blocks": n_blocks, "n_boot": n_boot,
            "observed_delta": observed_delta, "null_std": float(t_boot.std()),
            "p_value": p_value, "method": "null_centered_block_bootstrap"}


# ---------------- Metodo B ----------------

def block_se(x, L, n_blocks_needed=None):
    """SE della media stimato dalla varianza fra medie di blocco (jackknife-
    di-blocco semplice, MAI ottimizzato sui dati - solo L=ceil(n^(1/3))."""
    n = len(x)
    n_full_blocks = n // L
    if n_full_blocks < 2:
        return float(x.std(ddof=1) / math.sqrt(n)) if n > 1 else 1e-9
    block_means = np.array([x[i * L:(i + 1) * L].mean() for i in range(n_full_blocks)])
    var_of_block_means = block_means.var(ddof=1) if n_full_blocks > 1 else 0.0
    se = math.sqrt(var_of_block_means * L / n) if var_of_block_means > 0 else float(x.std(ddof=1) / math.sqrt(n))
    return max(se, 1e-9)


def studentized_block_bootstrap_p(d_values, n_boot=1000, block_length=None, seed=42):
    d = _clean(d_values)
    n = len(d)
    if n < 5:
        return {"n": n, "note": "campione troppo piccolo", "method": "studentized_block_bootstrap"}
    L = block_length or block_length_default(n)
    n_blocks = math.ceil(n / L)
    rng = np.random.default_rng(seed)

    observed_delta = float(d.mean())
    se_obs = block_se(d, L)
    t_obs = observed_delta / se_obs
    centered = d - observed_delta

    t_boot = np.empty(n_boot)
    for b in range(n_boot):
        resampled = _block_resample(centered, L, n_blocks, rng)
        se_b = block_se(resampled, L)
        t_boot[b] = resampled.mean() / se_b

    p_value = float((1 + np.sum(np.abs(t_boot) >= abs(t_obs))) / (n_boot + 1))
    return {"n": n, "block_length": L, "n_blocks": n_blocks, "n_boot": n_boot,
            "observed_delta": observed_delta, "t_observed": t_obs,
            "p_value": p_value, "method": "studentized_block_bootstrap"}


# ---------------- Metodo C ----------------

def hac_bandwidth_default(n):
    """Bandwidth STRUTTURALE, MAI scelta guardando i dati - stessa formula
    di block_length_default (L=ceil(n^(1/3))) per coerenza di progetto."""
    return block_length_default(n)


def hac_newey_west_p(d_values, bandwidth=None):
    d = _clean(d_values)
    n = len(d)
    if n < 5:
        return {"n": n, "note": "campione troppo piccolo", "method": "hac_newey_west"}
    bw = bandwidth or hac_bandwidth_default(n)
    mean_d = float(d.mean())
    x = d - mean_d
    gamma0 = float(np.dot(x, x) / n)
    hac_var = gamma0
    for k in range(1, bw + 1):
        if k >= n:
            break
        gamma_k = float(np.dot(x[:-k], x[k:]) / n)
        w_k = 1.0 - k / (bw + 1)  # kernel di Bartlett
        hac_var += 2 * w_k * gamma_k
    hac_var = max(hac_var, 1e-12) / n
    hac_se = math.sqrt(hac_var)
    t_stat = mean_d / hac_se if hac_se > 0 else 0.0
    p_value = float(2 * stats.t.sf(abs(t_stat), df=max(1, n - 1)))
    return {"n": n, "bandwidth": bw, "observed_delta": mean_d, "hac_se": hac_se,
            "t_statistic": t_stat, "p_value": min(1.0, p_value), "method": "hac_newey_west"}


if __name__ == "__main__":
    rng = np.random.default_rng(21)

    def gen_ar1(rng, phi, n=30, mean_shift=0.0):
        eps = rng.normal(0.0, 1.0, n)
        x = np.empty(n)
        x[0] = eps[0] + mean_shift
        for t in range(1, n):
            x[t] = phi * x[t - 1] + eps[t] * np.sqrt(1 - phi ** 2) + mean_shift * (1 - phi)
        return x

    print("=== Self-test dei 3 metodi su dati SINTETICI ===")
    for label, fn in [("A (null-centered block bootstrap)", null_centered_block_bootstrap_p),
                      ("B (studentized block bootstrap)", studentized_block_bootstrap_p),
                      ("C (HAC/Newey-West)", hac_newey_west_p)]:
        print(f"\n--- Metodo {label} ---")
        d_h0 = gen_ar1(rng, 0.0, n=30, mean_shift=0.0)
        r = fn(d_h0) if fn is not hac_newey_west_p else fn(d_h0)
        print(f"Caso 1 (H0 vera, iid): p={r['p_value']:.4f}")
        assert r["p_value"] > 0.01, f"{label}: p-value sospettosamente basso sotto H0 vera in questo seed"

        d_effect = gen_ar1(rng, 0.0, n=30, mean_shift=1.0)
        r2 = fn(d_effect)
        print(f"Caso 2 (effetto ampio e reale): p={r2['p_value']:.4f}")
        assert r2["p_value"] < 0.05, f"{label}: un effetto ampio dovrebbe risultare significativo"

        r3 = fn([0.1, 0.2, -0.1])
        assert "p_value" not in r3 and "note" in r3
        print(f"Caso 3 (campione insufficiente): {r3['note']}")

    print("\nSelf-test dependence_aware_mean_tests completato su dati SINTETICI.")
