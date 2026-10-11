"""Power and feasibility for barrier-outcome experiments (Behavior Lab family).

Deterministic, stdlib only, synthetic: no market data is read.

Outcome model for one closed trade with target T (in R) and stop -1R:
  with probability t the trade times out, R ~ Normal(m_t, s_t) clipped to [-1, T];
  otherwise it ends at the target with probability p, at the stop with 1 - p.
  Net R = gross R - c (round-trip cost in R).
  For a driftless price the barrier probability is p0 = 1 / (1 + T)
  (gambler's ruin for continuous paths), so "no edge" means p = p0, gross mean 0.

Two things are computed and must not be confused:
- `replicate_loop_v1`: the one-sample z-test the RI-02 loop used as a planning
  proxy (p_target_first vs p0, one-sided, alpha corrected over 6 hypotheses);
- `simulate_bl01_rule`: the BL-01 preregistered decision rule
  (BL01_DECISION_RULES_V1): STOP below 30 trades, STOP if the month-block CI95
  is below 0, GO only with n >= 60, mean > 0, CI95 low > 0, mean - 0.10R > 0,
  >= 60% positive quarters (n >= 5) and the event beating the control; else INVESTIGATE.
  The month-block bootstrap is approximated by a month-clustered standard
  error; direction, hour and stratified-cell checks are not modelled, so the
  simulated GO rate is an upper bound.
"""
from __future__ import annotations

import math
import random
import statistics

ND = statistics.NormalDist()


def null_rate(target_r=2.0):
    return 1.0 / (1.0 + target_r)


def moments(p, *, target_r=2.0, timeout_share=0.0, timeout_mean=0.0, timeout_sd=0.7, cost_r=0.0):
    """Mean and SD of net R per trade (timeouts treated as unclipped normal for the moments)."""
    t = timeout_share
    m_hit = p * target_r - (1 - p)
    e2_hit = p * target_r ** 2 + (1 - p)
    mean_gross = (1 - t) * m_hit + t * timeout_mean
    e2 = (1 - t) * e2_hit + t * (timeout_sd ** 2 + timeout_mean ** 2)
    return mean_gross - cost_r, math.sqrt(max(e2 - mean_gross ** 2, 0.0))


def power_ci_low_positive(mu, sigma, n, deff=1.0, z=1.959964):
    """P(mean - z * SE > 0) with SE = sigma * sqrt(deff / n): the CI-low criterion alone."""
    if n <= 0:
        return 0.0
    return ND.cdf(mu * math.sqrt(n / deff) / sigma - z)


def n_required(mu, sigma, *, deff=1.0, alpha_two_sided=0.05, power=0.8):
    if mu <= 0:
        return math.inf
    za, zb = ND.inv_cdf(1 - alpha_two_sided / 2), ND.inv_cdf(power)
    return math.ceil(((za + zb) * sigma / mu) ** 2 * deff)


def mde(n, sigma, *, deff=1.0, alpha_two_sided=0.05, power=0.8):
    """Smallest net mean (R) detected with the given power by the CI-low criterion."""
    za, zb = ND.inv_cdf(1 - alpha_two_sided / 2), ND.inv_cdf(power)
    return (za + zb) * sigma * math.sqrt(deff / n)


def design_effect(trades_per_cluster, icc):
    return 1 + max(trades_per_cluster - 1, 0) * icc


def replicate_loop_v1(n=80, alpha=0.05 / 6, p0=1 / 3, effect=0.08, power=0.8, reps=400, seed=0x166CC23E):
    """What the RI-02 SYNTHETIC_DRY_RUN computed (one-sample, one-sided, binomial outcome only)."""
    p1 = p0 + effect
    za, zb = ND.inv_cdf(1 - alpha), ND.inv_cdf(power)
    n_needed = math.ceil(((za * math.sqrt(p0 * (1 - p0)) + zb * math.sqrt(p1 * (1 - p1))) / effect) ** 2)
    crit = p0 + za * math.sqrt(p0 * (1 - p0) / n)
    analytic = 1 - ND.cdf((crit - p1) / math.sqrt(p1 * (1 - p1) / n))
    rng = random.Random(seed)
    hits = sum(1 for _ in range(reps) if sum(rng.random() < p1 for _ in range(n)) / n > crit)
    return {"test": "one-sample one-sided z on p_target_first vs p0", "n": n, "alpha": alpha, "p0": p0,
            "p1": p1, "analytic_power": analytic, "simulated_power": hits / reps, "n_for_80pct": n_needed,
            "z_alpha": za, "z_beta": zb}


def _draw_r(rng, p, target_r, t, m_t, s_t):
    if rng.random() < t:
        return min(target_r, max(-1.0, rng.gauss(m_t, s_t)))
    return target_r if rng.random() < p else -1.0


def _poisson(rng, lam):
    if lam > 50:  # normal approximation keeps this O(1)
        return max(0, int(round(rng.gauss(lam, math.sqrt(lam)))))
    k, prod, limit = 0, rng.random(), math.exp(-lam)
    while prod > limit:
        k += 1
        prod *= rng.random()
    return k


def simulate_bl01_rule(*, delta_p, pullbacks_expected=83.3, conversion=0.6, months=18, target_r=2.0,
                       timeout_share=0.15, timeout_sd=0.7, cost_r=0.05, month_sd=0.0, reps=2000,
                       seed=20261011, extra_cost_r=0.10):
    """Decision distribution of BL01_DECISION_RULES_V1 under a synthetic world.

    delta_p: true P(target first) minus the driftless rate 1/(1+T) (0 = no edge).
    conversion: share of pullbacks that become closed trades (confirmation, risk
    filter, entry gap, censoring). month_sd: SD of a month-level shift of p, the
    source of within-month dependence.
    """
    rng = random.Random(seed)
    p_base = null_rate(target_r) + delta_p
    counts = {"GO": 0, "INVESTIGATE": 0, "STOP_SAMPLE": 0, "STOP_NEGATIVE": 0, "STOP_NO_ADVANTAGE": 0}
    n_trades = []
    for _ in range(reps):
        n = sum(1 for _ in range(_poisson(rng, pullbacks_expected)) if rng.random() < conversion)
        n_trades.append(n)
        if n < 30:
            counts["STOP_SAMPLE"] += 1
            continue
        shifts = [rng.gauss(0, month_sd) for _ in range(months)]
        by_month = {}
        for _ in range(n):
            m = rng.randrange(months)
            p = min(0.99, max(0.01, p_base + shifts[m]))
            by_month.setdefault(m, []).append(_draw_r(rng, p, target_r, timeout_share, 0.0, timeout_sd) - cost_r)
        values = [v for vs in by_month.values() for v in vs]
        mean = sum(values) / n
        g = len(by_month)
        # month-clustered (CR1) standard error, the analytic counterpart of the month-block bootstrap
        se = math.sqrt(sum(sum(v - mean for v in vs) ** 2 for vs in by_month.values()) / n ** 2 * g / max(g - 1, 1))
        low, high = mean - 1.959964 * se, mean + 1.959964 * se
        control_mean = -cost_r  # driftless control, same costs, large n: estimated without noise
        if high < 0:
            counts["STOP_NEGATIVE"] += 1
            continue
        if mean <= 0 and mean - control_mean <= 0:
            counts["STOP_NO_ADVANTAGE"] += 1
            continue
        quarters = {}
        for m, vs in by_month.items():
            quarters.setdefault(m // 3, []).extend(vs)
        usable = [vs for vs in quarters.values() if len(vs) >= 5]
        q_ok = bool(usable) and sum(1 for vs in usable if sum(vs) > 0) / len(usable) >= 0.6
        go = n >= 60 and mean > 0 and low > 0 and mean - extra_cost_r > 0 and q_ok and mean - control_mean > 0
        counts["GO" if go else "INVESTIGATE"] += 1
    mu, sigma = moments(p_base, target_r=target_r, timeout_share=timeout_share, timeout_sd=timeout_sd,
                        cost_r=cost_r)
    n_trades.sort()
    return {"delta_p": delta_p, "conversion": conversion, "month_sd": month_sd, "cost_r": cost_r,
            "timeout_share": timeout_share, "true_net_mean_r": mu, "sd_r": sigma,
            "trades_median": n_trades[len(n_trades) // 2],
            "trades_p10_p90": [n_trades[int(0.1 * reps)], n_trades[int(0.9 * reps)]],
            "decision_rates": {k: v / reps for k, v in counts.items()}, "reps": reps, "seed": seed,
            "upper_bound_note": "direction, hour and stratified-cell checks not simulated: GO rate is an upper bound"}
