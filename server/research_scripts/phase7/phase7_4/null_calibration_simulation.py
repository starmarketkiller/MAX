#!/usr/bin/env python3
"""Phase 7.4A Final Statistical Integrity Patch sec.1-4 - Null
Calibration Simulation. INTERAMENTE SINTETICA - nessun dato NEXUS.

Misura l'empirical rejection rate a alpha=.01/.05/.10 sotto H0 VERA per:
  (A) il metodo precedente (two_sample_block_bootstrap_percentile_p,
      pooling di due campioni "indipendenti" evento/baseline)
  (B) il nuovo metodo (block_sign_flip_permutation_p su differenze
      accoppiate d_i = evento_i - media(controlli matched_i))

su 4 scenari sotto H0 per ciascun metodo (Gaussian iid, skewed,
autocorrelato, sbilanciato/rumoroso) + 1 scenario dimostrativo
("shared_regime") che confronta ESPLICITAMENTE i due metodi sugli
STESSI dati generati con una struttura a shock di regime condiviso
fra evento e i propri controlli matched (il caso concreto in cui
appiattire la struttura matched e' scorretto)."""
import json
import os
import sys
import time

import numpy as np

PHASE74_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(PHASE74_DIR, "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase7", "engine"))
from two_sample_bootstrap_test import two_sample_block_bootstrap_percentile_p  # noqa: E402
from matched_pair_permutation_test import block_sign_flip_permutation_p  # noqa: E402

ALPHAS = [0.01, 0.05, 0.10]
N_REPS = 1000
N_BOOT = 1000


def rejection_rates(p_values):
    p = np.asarray(p_values, dtype=float)
    return {str(a): float(np.mean(p <= a)) for a in ALPHAS}


# ---------------- OLD METHOD (pooled, two-sample) scenarios under H0 ----------------

def gen_old_gaussian_iid(rng):
    return rng.normal(0.0, 1.0, 30), rng.normal(0.0, 1.0, 100)


def gen_old_skewed(rng):
    # Esponenziale ricentrata (skew reale, stessa distribuzione per evento e baseline sotto H0).
    return rng.exponential(1.0, 30) - 1.0, rng.exponential(1.0, 100) - 1.0


def gen_old_autocorrelated_event(rng, phi=0.7, n=30):
    eps = rng.normal(0.0, 1.0, n)
    x = np.empty(n)
    x[0] = eps[0]
    for t in range(1, n):
        x[t] = phi * x[t - 1] + eps[t] * np.sqrt(1 - phi ** 2)  # varianza marginale ~1
    return x, rng.normal(0.0, 1.0, 100)


def gen_old_unequal_n(rng):
    return rng.normal(0.0, 1.0, 30), rng.normal(0.0, 1.0, 300)


OLD_SCENARIOS = {
    "gaussian_iid": gen_old_gaussian_iid,
    "skewed": gen_old_skewed,
    "autocorrelated_event": gen_old_autocorrelated_event,
    "unequal_n_30_vs_300": gen_old_unequal_n,
}


def run_old_method_calibration():
    results = {}
    for name, gen in OLD_SCENARIOS.items():
        rng = np.random.default_rng(hash(name) % (2**32))
        pvals = []
        t0 = time.time()
        for i in range(N_REPS):
            ev, bl = gen(rng)
            r = two_sample_block_bootstrap_percentile_p(ev, bl, n_boot=N_BOOT, seed=i)
            pvals.append(r["p_value"])
        elapsed = time.time() - t0
        results[name] = {"n_reps": N_REPS, "n_boot": N_BOOT, "elapsed_sec": round(elapsed, 1),
                          "empirical_rejection_rate": rejection_rates(pvals)}
        print(f"[OLD/{name}] {N_REPS} reps in {elapsed:.1f}s -> rejection rates: {results[name]['empirical_rejection_rate']}")
    return results


# ---------------- NEW METHOD (matched-pair d_i) scenarios under H0 ----------------

def gen_new_gaussian_iid(rng):
    return rng.normal(0.0, 1.0, 30)


def gen_new_skewed(rng):
    return rng.exponential(1.0, 30) - 1.0


def gen_new_autocorrelated_d(rng, phi=0.7, n=30):
    eps = rng.normal(0.0, 1.0, n)
    x = np.empty(n)
    x[0] = eps[0]
    for t in range(1, n):
        x[t] = phi * x[t - 1] + eps[t] * np.sqrt(1 - phi ** 2)
    return x


def gen_new_few_controls_high_noise(rng, n=30, n_controls=2):
    # d_i = 1 draw evento - media di soli 2 controlli (invece di 5) -> d_i piu' rumoroso/asimmetrico a n piccolo.
    event_draws = rng.normal(0.0, 1.0, n)
    control_draws = rng.normal(0.0, 1.0, (n, n_controls))
    return event_draws - control_draws.mean(axis=1)


NEW_SCENARIOS = {
    "gaussian_iid": gen_new_gaussian_iid,
    "skewed": gen_new_skewed,
    "autocorrelated_d": gen_new_autocorrelated_d,
    "few_controls_high_noise_n_controls_2": gen_new_few_controls_high_noise,
}


def run_new_method_calibration():
    results = {}
    for name, gen in NEW_SCENARIOS.items():
        rng = np.random.default_rng(hash("new_" + name) % (2**32))
        pvals = []
        t0 = time.time()
        for i in range(N_REPS):
            d = gen(rng)
            r = block_sign_flip_permutation_p(d, n_boot=N_BOOT, seed=i)
            pvals.append(r["p_value"])
        elapsed = time.time() - t0
        results[name] = {"n_reps": N_REPS, "n_boot": N_BOOT, "elapsed_sec": round(elapsed, 1),
                          "empirical_rejection_rate": rejection_rates(pvals)}
        print(f"[NEW/{name}] {N_REPS} reps in {elapsed:.1f}s -> rejection rates: {results[name]['empirical_rejection_rate']}")
    return results


# ---------------- Scenario dimostrativo: shared regime shock (sec.4) ----------------

def gen_shared_regime_episode(rng, n_events=30, k_controls=5, tau=1.0, sigma=0.3):
    """Sotto H0 ESATTA: outcome_event_i = r_i + eps_event_i, outcome_control_ij = r_i + eps_control_ij
    (stesso regime shock r_i condiviso da evento e dai suoi k controlli matched - esattamente cio' che
    accade con un buon matching: i controlli sono scelti perche' nello stesso stato di mercato). Nessuna
    vera differenza sistematica evento/controllo (E[d_i]=0 per costruzione)."""
    r = rng.normal(0.0, tau, n_events)
    event_outcomes = r + rng.normal(0.0, sigma, n_events)
    control_outcomes = r[:, None] + rng.normal(0.0, sigma, (n_events, k_controls))
    return event_outcomes, control_outcomes


def run_shared_regime_demo():
    rng_old = np.random.default_rng(999)
    rng_new = np.random.default_rng(999)  # stesso seed pattern per generare dati comparabili
    pvals_old, pvals_new = [], []
    t0 = time.time()
    for i in range(N_REPS):
        ev, ctrl = gen_shared_regime_episode(rng_old)
        pooled_baseline = ctrl.flatten()  # OLD: appiattisce tutti i 150 controlli in un pool unico
        r_old = two_sample_block_bootstrap_percentile_p(ev, pooled_baseline, n_boot=N_BOOT, seed=i)
        pvals_old.append(r_old["p_value"])

        ev2, ctrl2 = gen_shared_regime_episode(rng_new)  # dati indipendenti ma STESSA struttura generativa
        d = ev2 - ctrl2.mean(axis=1)  # NEW: differenza per-evento, il regime r_i si cancella esattamente
        r_new = block_sign_flip_permutation_p(d, n_boot=N_BOOT, seed=i)
        pvals_new.append(r_new["p_value"])
    elapsed = time.time() - t0
    return {
        "description": (
            "H0 esatta: outcome_event_i = r_i + eps_event_i, outcome_control_ij = r_i + eps_control_ij "
            "(shock di regime r_i~N(0,tau=1.0) condiviso da evento e i suoi 5 controlli matched, rumore "
            "idiosincratico eps~N(0,sigma=0.3)). Nessuna vera differenza (E[d_i]=0 per costruzione)."
        ),
        "n_reps": N_REPS, "n_boot": N_BOOT, "elapsed_sec": round(elapsed, 1),
        "OLD_pooled_flattened_controls": {"empirical_rejection_rate": rejection_rates(pvals_old)},
        "NEW_matched_pair_per_event": {"empirical_rejection_rate": rejection_rates(pvals_new)},
        "interpretation": (
            "CORREZIONE (Phase 7.4A Dependence Validity Gate, sec.8 - l'interpretazione precedente era "
            "ERRATA): il risultato empirico e' rejection_rate=0% per OLD a TUTTI gli alpha - questo e' "
            "FORTEMENTE CONSERVATIVO/POWERLESS (troppo poco potente, non rigetta praticamente mai, nemmeno "
            "quando dovrebbe), NON anti-conservativo. Il meccanismo corretto: sullo STESSO replicato, evento "
            "e i suoi 5 controlli condividono ESATTAMENTE lo stesso r_i, quindi nel delta OSSERVATO r_i si "
            "cancella quasi del tutto (la vera variabilita' di delta_e_observed e' piccola, dominata solo "
            "dal rumore idiosincratico eps, non da tau). OLD pero' ricampiona evento e baseline "
            "SEPARATAMENTE E INDIPENDENTEMENTE (block bootstrap sull'evento, iid bootstrap sul pool di "
            "baseline): il bootstrap dell'evento (30 valori con varianza dominata da tau=1.0, alta) tratta "
            "quella variabilita' come se riflettesse vera incertezza campionaria del delta, quando invece "
            "quella stessa componente di varianza e' CONDIVISA con la baseline sullo stesso replicato e "
            "dovrebbe cancellarsi - il bootstrap, non sapendolo, produce un intervallo di confidenza molto "
            "PIU' AMPIO del necessario, da cui 0% di rigetto. NEW invece calcola d_i = eps_event_i - "
            "mean(eps_control_i) DIRETTAMENTE sui dati reali (non nel bootstrap): r_i si cancella gia' "
            "nell'osservazione stessa, non solo nella sua attesa, quindi la distribuzione di permutazione "
            "riflette correttamente la vera (piccola) variabilita' residua - risultato correttamente "
            "calibrato (vedi tabella sopra). La conclusione valida, in ENTRAMBE le direzioni di errore "
            "possibili (anti-conservativo nei 4 scenari base, fortemente conservativo/powerless qui): "
            "appiattire la struttura matched (flattening) distrugge l'informazione di accoppiamento e "
            "produce un'inferenza mal calibrata - a volte nella direzione pericolosa (falsi positivi), a "
            "volte in quella che nasconde un effetto vero (falsi negativi) - non e' prevedibile a priori in "
            "quale direzione sbagliera', il che la rende inaffidabile in entrambi i casi."
        ),
    }


def main():
    print("=== Calibrazione OLD method (two_sample_block_bootstrap_percentile_p, pooled) ===")
    old_results = run_old_method_calibration()
    print("\n=== Calibrazione NEW method (block_sign_flip_permutation_p, matched-pair) ===")
    new_results = run_new_method_calibration()
    print("\n=== Scenario dimostrativo: shared regime shock (struttura matched) ===")
    shared_regime = run_shared_regime_demo()
    print(json.dumps(shared_regime, indent=2, ensure_ascii=False))

    payload = {
        "principle": "Simulazione interamente sintetica sotto H0 VERA - nessun dato NEXUS. Un metodo ben calibrato deve avere empirical_rejection_rate ~= alpha (o piu' conservativo, mai marcatamente superiore).",
        "alphas_tested": ALPHAS, "n_reps_per_scenario": N_REPS, "n_boot_per_replicate": N_BOOT,
        "old_method_two_sample_block_bootstrap_percentile_p": old_results,
        "new_method_block_sign_flip_permutation": new_results,
        "shared_regime_demo_old_vs_new": shared_regime,
    }
    out_path = os.path.join(PHASE74_DIR, "phase7_4_null_calibration_v1.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)
    print(f"\nScritto: {out_path}")
    return payload


if __name__ == "__main__":
    main()
