#!/usr/bin/env python3
"""Phase 7.4A Dependence Validity Gate - classifica OGNI serie d_i
(INDEPENDENT_VIEW, per candidate x outcome) in uno di 3 stati PRIMA di
ammettere il suo p-value a BH-FDR:

  INFERENCE_VALID             - il p-value entra normalmente in BH-FDR.
  DEPENDENCE_SENSITIVE         - il p-value resta calcolato ma e'
                                 DIAGNOSTIC_ONLY: non puo' produrre da
                                 solo un verdetto di discovery.
  INFERENCE_INVALID_DEPENDENCE - il candidato/outcome si ferma: nessuna
                                 classificazione BH-FDR per quella cella.

Diagnostica congelata EX-ANTE (Phase 7.4A Dependence Validity Gate,
2026-09-20, PRIMA di guardare qualunque dato NEXUS/SEQ-0015):
  - ACF lag 1 della serie d_i (ordinata per tempo).
  - Ljung-Box su h=3 lag (formula chiusa, nessuna libreria esterna -
    ispezionabile a mano, vedi statistical_methods_policy.json).
  - Effective Sample Size via inflation ratio block-vs-iid
    (moving_block_bootstrap_ci/iid_bootstrap_ci, phase6_5/block_bootstrap.py,
    riusati senza modifiche).

Soglie fissate dalla calibration curve sintetica (phi=0.0..0.7, vedi
dependence_validity_gate_calibration.py) - MAI scelte guardando SEQ-0015."""
import math
import os
import sys

import numpy as np
from scipy import stats

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase6_5"))
from block_bootstrap import moving_block_bootstrap_ci, iid_bootstrap_ci  # noqa: E402

INFERENCE_VALID = "INFERENCE_VALID"
DEPENDENCE_SENSITIVE = "DEPENDENCE_SENSITIVE"
INFERENCE_INVALID_DEPENDENCE = "INFERENCE_INVALID_DEPENDENCE"

# Soglie congelate (sec.2-3) - vedi calibration curve per la derivazione.
THRESHOLDS_FROZEN = {
    "acf_lag1_sensitive": 0.20,
    "acf_lag1_invalid": 0.45,
    "ljung_box_p_sensitive": 0.10,   # p < 0.10 -> dipendenza rilevata (soglia permissiva, cattura anche dipendenza debole)
    "ljung_box_p_invalid": 0.01,     # p < 0.01 -> dipendenza forte
    "ess_ratio_sensitive": 0.70,     # ESS/n < 0.70 -> perdita di informazione moderata
    "ess_ratio_invalid": 0.40,       # ESS/n < 0.40 -> perdita di informazione severa
}

# Diagnostico di skew/asimmetria (sec.7) - flag separato, non un terzo stato pieno.
ASYMMETRY_SENSITIVE_SKEW_THRESHOLD = 0.75


def acf_lag_k(x: np.ndarray, k: int) -> float:
    n = len(x)
    if n <= k:
        return 0.0
    x_c = x - x.mean()
    num = np.sum(x_c[:-k] * x_c[k:])
    den = np.sum(x_c ** 2)
    return float(num / den) if den > 0 else 0.0


def ljung_box_p(x: np.ndarray, h: int = 3) -> float:
    """Formula chiusa standard (nessuna libreria di serie storiche esterna,
    solo scipy.stats.chi2 per il p-value finale - ispezionabile a mano):
    Q = n(n+2) * sum_{k=1}^{h} rho_k^2/(n-k) ~ chi2(h) sotto H0 di assenza
    di autocorrelazione fino al lag h."""
    n = len(x)
    if n <= h + 2:
        return 1.0
    q = 0.0
    for k in range(1, h + 1):
        rho_k = acf_lag_k(x, k)
        q += (rho_k ** 2) / (n - k)
    q *= n * (n + 2)
    return float(1.0 - stats.chi2.cdf(q, df=h))


def ess_ratio(x: np.ndarray, n_boot: int = 1000, seed: int = 42) -> float:
    """ESS/n stimato dal rapporto fra varianza iid-bootstrap e varianza
    block-bootstrap della media (entrambe riusate da block_bootstrap.py
    senza modifiche) - un rapporto <1 indica che la dipendenza seriale
    infla l'incertezza reale oltre quella naive iid."""
    x = np.asarray(x, dtype=float)
    n = len(x)
    if n < 10:
        return 1.0
    iid = iid_bootstrap_ci(x, n_boot=n_boot, seed=seed)
    block = moving_block_bootstrap_ci(x, n_boot=n_boot, seed=seed)
    if "std" not in iid or "std" not in block or block["std"] <= 0:
        return 1.0
    inflation = (block["std"] / iid["std"]) ** 2 if iid["std"] > 0 else 1.0
    return float(1.0 / inflation) if inflation > 0 else 1.0


def sample_skewness(x: np.ndarray) -> float:
    x = np.asarray(x, dtype=float)
    n = len(x)
    if n < 5:
        return 0.0
    m = x.mean()
    s = x.std(ddof=1)
    if s == 0:
        return 0.0
    return float(np.mean(((x - m) / s) ** 3))


def compute_dependence_diagnostics(d_values, n_boot: int = 1000, seed: int = 42) -> dict:
    x = np.asarray([v for v in d_values if v is not None and not (isinstance(v, float) and np.isnan(v))], dtype=float)
    n = len(x)
    if n < 10:
        return {"n": n, "note": "campione troppo piccolo per la diagnostica di dipendenza"}
    return {
        "n": n,
        "acf_lag1": acf_lag_k(x, 1),
        "ljung_box_p_h3": ljung_box_p(x, h=3),
        "ess_ratio": ess_ratio(x, n_boot=n_boot, seed=seed),
        "sample_skewness": sample_skewness(x),
    }


def classify_dependence_validity(diagnostics: dict, thresholds: dict = None) -> dict:
    """Fail-closed (sec.4): basta UNA condizione di livello piu' severo per
    classificare la cella a quel livello - nessuna media pesata fra i 3
    indicatori."""
    th = thresholds or THRESHOLDS_FROZEN
    if "note" in diagnostics:
        return {"state": INFERENCE_INVALID_DEPENDENCE, "reason": diagnostics["note"], "asymmetry_sensitive": False}

    acf1 = abs(diagnostics["acf_lag1"])
    lb_p = diagnostics["ljung_box_p_h3"]
    ess_r = diagnostics["ess_ratio"]

    invalid_reasons = []
    if acf1 >= th["acf_lag1_invalid"]:
        invalid_reasons.append(f"|ACF(1)|={acf1:.3f} >= {th['acf_lag1_invalid']}")
    if lb_p < th["ljung_box_p_invalid"]:
        invalid_reasons.append(f"Ljung-Box p={lb_p:.4f} < {th['ljung_box_p_invalid']}")
    if ess_r < th["ess_ratio_invalid"]:
        invalid_reasons.append(f"ESS/n={ess_r:.3f} < {th['ess_ratio_invalid']}")
    if invalid_reasons:
        return {"state": INFERENCE_INVALID_DEPENDENCE, "reason": "; ".join(invalid_reasons),
                "asymmetry_sensitive": abs(diagnostics["sample_skewness"]) >= ASYMMETRY_SENSITIVE_SKEW_THRESHOLD}

    sensitive_reasons = []
    if acf1 >= th["acf_lag1_sensitive"]:
        sensitive_reasons.append(f"|ACF(1)|={acf1:.3f} >= {th['acf_lag1_sensitive']}")
    if lb_p < th["ljung_box_p_sensitive"]:
        sensitive_reasons.append(f"Ljung-Box p={lb_p:.4f} < {th['ljung_box_p_sensitive']}")
    if ess_r < th["ess_ratio_sensitive"]:
        sensitive_reasons.append(f"ESS/n={ess_r:.3f} < {th['ess_ratio_sensitive']}")
    if sensitive_reasons:
        return {"state": DEPENDENCE_SENSITIVE, "reason": "; ".join(sensitive_reasons),
                "asymmetry_sensitive": abs(diagnostics["sample_skewness"]) >= ASYMMETRY_SENSITIVE_SKEW_THRESHOLD}

    return {"state": INFERENCE_VALID, "reason": "nessun indicatore di dipendenza sopra soglia",
            "asymmetry_sensitive": abs(diagnostics["sample_skewness"]) >= ASYMMETRY_SENSITIVE_SKEW_THRESHOLD}


def p_value_for_bh(raw_p_value: float, validity_state: str) -> float:
    """sec.6 - FDR denominator policy: family_size resta SEMPRE fisso
    (mai ridotto opportunisticamente); le celle non INFERENCE_VALID
    ricevono p=1.0 (non-reject garantito) invece di essere rimosse dalla
    famiglia."""
    return raw_p_value if validity_state == INFERENCE_VALID else 1.0


if __name__ == "__main__":
    rng = np.random.default_rng(3)

    # Caso 1: rumore bianco -> INFERENCE_VALID.
    white = rng.normal(0, 1, 60)
    diag1 = compute_dependence_diagnostics(white)
    cls1 = classify_dependence_validity(diag1)
    print(f"Caso 1 (rumore bianco): acf1={diag1['acf_lag1']:.3f}, lb_p={diag1['ljung_box_p_h3']:.3f}, ess_ratio={diag1['ess_ratio']:.3f} -> {cls1['state']}")
    assert cls1["state"] == INFERENCE_VALID

    # Caso 2: AR(1) forte (phi=0.8) -> deve degradare almeno a DEPENDENCE_SENSITIVE.
    def gen_ar1(rng, phi, n=60):
        eps = rng.normal(0, 1, n)
        x = np.empty(n)
        x[0] = eps[0]
        for t in range(1, n):
            x[t] = phi * x[t - 1] + eps[t] * np.sqrt(1 - phi ** 2)
        return x

    strong_ar1 = gen_ar1(rng, 0.8)
    diag2 = compute_dependence_diagnostics(strong_ar1)
    cls2 = classify_dependence_validity(diag2)
    print(f"Caso 2 (AR(1) phi=0.8): acf1={diag2['acf_lag1']:.3f}, lb_p={diag2['ljung_box_p_h3']:.3f}, ess_ratio={diag2['ess_ratio']:.3f} -> {cls2['state']}")
    assert cls2["state"] in (DEPENDENCE_SENSITIVE, INFERENCE_INVALID_DEPENDENCE)

    # Caso 3: p_value_for_bh - INFERENCE_VALID passa il p reale, altri stati -> 1.0.
    assert p_value_for_bh(0.002, INFERENCE_VALID) == 0.002
    assert p_value_for_bh(0.002, DEPENDENCE_SENSITIVE) == 1.0
    assert p_value_for_bh(0.002, INFERENCE_INVALID_DEPENDENCE) == 1.0
    print("Caso 3 OK: p_value_for_bh sostituisce con 1.0 qualunque stato diverso da INFERENCE_VALID.")

    # Caso 4: campione troppo piccolo -> INFERENCE_INVALID_DEPENDENCE (fail-closed).
    diag4 = compute_dependence_diagnostics([0.1, 0.2, -0.1])
    cls4 = classify_dependence_validity(diag4)
    assert cls4["state"] == INFERENCE_INVALID_DEPENDENCE
    print(f"Caso 4 OK: campione insufficiente -> {cls4['state']} (fail-closed, non un default permissivo).")

    print("\nSelf-test dependence_validity_gate completato su dati SINTETICI.")
