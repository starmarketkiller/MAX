#!/usr/bin/env python3
"""Phase 5.G - Probability & Uncertainty Engine: Wilson score interval
(frequentista) + Beta-Binomial (Bayesiano, interpretabile). Nessun
win-rate nudo: ogni chiamata restituisce n/wins/losses/censored/CI95/
posteriore, mai un singolo numero isolato - vedi
vault/01-Trading/_phase4_artifacts/probability_schema.md per lo schema
concettuale; qui l'implementazione numerica v1.
"""
import math

from scipy import stats


def wilson_ci95(wins: int, n: int):
    if n == 0:
        return (None, None)
    z = 1.959963984540054  # 97.5th percentile standard normal
    p = wins / n
    denom = 1 + z ** 2 / n
    center = (p + z ** 2 / (2 * n)) / denom
    half = (z * math.sqrt((p * (1 - p) / n) + (z ** 2 / (4 * n ** 2)))) / denom
    return (max(0.0, center - half), min(1.0, center + half))


def beta_binomial(wins: int, n: int, prior_alpha: float = 1.0, prior_beta: float = 1.0):
    """Posteriore Beta(prior_alpha+wins, prior_beta+losses). Ritorna media
    posteriore e intervallo credibile 95% (ppf esatto via scipy.stats.beta)."""
    losses = n - wins
    a = prior_alpha + wins
    b = prior_beta + losses
    mean = a / (a + b)
    lo = stats.beta.ppf(0.025, a, b)
    hi = stats.beta.ppf(0.975, a, b)
    return {
        "prior_alpha": prior_alpha, "prior_beta": prior_beta,
        "posterior_alpha": a, "posterior_beta": b,
        "posterior_mean": float(mean),
        "posterior_ci95_low": float(lo), "posterior_ci95_high": float(hi),
    }


def probability_record(wins: int, losses: int, censored: int = 0,
                        prior_alpha: float = 1.0, prior_beta: float = 1.0):
    """Record completo per un outcome binario TARGET_FIRST/STOP_FIRST,
    CENSORED escluso da wins/losses/n ma riportato esplicitamente."""
    n = wins + losses
    observed_p = wins / n if n > 0 else None
    ci_lo, ci_hi = wilson_ci95(wins, n) if n > 0 else (None, None)
    bb = beta_binomial(wins, n, prior_alpha, prior_beta) if n > 0 else None
    return {
        "n": n, "wins": wins, "losses": losses, "censored": censored,
        "observed_p": observed_p,
        "wilson_ci95_low": ci_lo, "wilson_ci95_high": ci_hi,
        "beta_binomial": bb,
    }


def series_to_wl(outcomes, target_col_prefix="TARGET_FIRST"):
    """outcomes: iterable di stringhe 'TARGET_FIRST'/'STOP_FIRST'/'CENSORED'."""
    wins = sum(1 for o in outcomes if o == "TARGET_FIRST")
    losses = sum(1 for o in outcomes if o == "STOP_FIRST")
    censored = sum(1 for o in outcomes if o == "CENSORED")
    return wins, losses, censored
