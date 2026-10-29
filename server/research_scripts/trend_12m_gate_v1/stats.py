"""Descriptive statistics for trend-gate rows. No p-value hunting beyond prereg CI."""
from __future__ import annotations

import math
import random
from datetime import datetime, timezone


def month_key(epoch):
    return datetime.fromtimestamp(epoch, tz=timezone.utc).strftime("%Y-%m")


def block_bootstrap_mean(rows, value, block=month_key, n_boot=2000, seed=20261029):
    groups = {}
    for row in rows:
        groups.setdefault(block(row["entry_time"]), []).append(value(row))
    keys = sorted(groups)
    if len(keys) < 2:
        return None
    rng = random.Random(seed)
    means = []
    for _ in range(n_boot):
        sample = [v for _ in keys for v in groups[rng.choice(keys)]]
        means.append(sum(sample) / len(sample))
    means.sort()
    return {
        "low": means[int(0.025 * n_boot)],
        "high": means[int(0.975 * n_boot) - 1],
        "n_blocks": len(keys),
        "n_boot": n_boot,
        "seed": seed,
    }


def block_bootstrap_mean_at_level(rows, value, level, block=month_key, n_boot=2000, seed=20261029):
    """Two-sided CI at arbitrary level (e.g. 1 - alpha/K for Bonferroni)."""
    groups = {}
    for row in rows:
        groups.setdefault(block(row["entry_time"]), []).append(value(row))
    keys = sorted(groups)
    if len(keys) < 2:
        return None
    rng = random.Random(seed)
    means = []
    for _ in range(n_boot):
        sample = [v for _ in keys for v in groups[rng.choice(keys)]]
        means.append(sum(sample) / len(sample))
    means.sort()
    alpha = 1.0 - float(level)
    lo_i = int((alpha / 2.0) * n_boot)
    hi_i = int((1.0 - alpha / 2.0) * n_boot) - 1
    hi_i = max(0, min(n_boot - 1, hi_i))
    return {
        "low": means[lo_i],
        "high": means[hi_i],
        "level": level,
        "n_blocks": len(keys),
        "n_boot": n_boot,
        "seed": seed,
    }


def _mean(values):
    return sum(values) / len(values) if values else None


def summarize(rows, params, ci_level=0.95):
    closed = [r for r in rows if r.get("status") == "CLOSED"]
    n = len(closed)
    out = {"n_days": n, "n_closed": n}
    if n == 0:
        return out
    excess = [r["excess_log_return"] for r in closed]
    strat = [r["strategy_log_return"] for r in closed]
    bh = [r["bh_log_return"] for r in closed]
    out.update({
        "mean_excess_log_return": _mean(excess),
        "mean_strategy_log_return": _mean(strat),
        "mean_bh_log_return": _mean(bh),
        "std_excess_log_return": (
            math.sqrt(sum((x - _mean(excess)) ** 2 for x in excess) / (n - 1)) if n > 1 else None
        ),
    })
    out["mean_excess_log_return_ci_month_blocks"] = block_bootstrap_mean_at_level(
        closed,
        lambda r: r["excess_log_return"],
        level=ci_level,
        n_boot=int(params["bootstrap_n"]),
        seed=int(params["bootstrap_seed"]),
    )
    # Keep 95% alias for confirmation path.
    out["mean_excess_log_return_ci95_month_blocks"] = block_bootstrap_mean(
        closed,
        lambda r: r["excess_log_return"],
        n_boot=int(params["bootstrap_n"]),
        seed=int(params["bootstrap_seed"]),
    )
    return out


def yearly_breakdown(rows):
    groups = {}
    for row in rows:
        if row.get("status") == "CLOSED":
            groups.setdefault(row["year"], []).append(row)
    out = {}
    for year, items in sorted(groups.items()):
        excess = [r["excess_log_return"] for r in items]
        out[year] = {"n": len(items), "mean_excess_log_return": _mean(excess)}
    return out


def year_concentration_share(yearly, min_n=20):
    usable = {y: v for y, v in yearly.items() if v["n"] >= min_n}
    positives = {y: max(v["mean_excess_log_return"] or 0.0, 0.0) for y, v in usable.items()}
    total = sum(positives.values())
    if total <= 0 or not positives:
        return {"share": None, "dominant_year": None, "usable_years": list(usable)}
    dominant = max(positives, key=positives.get)
    return {
        "share": positives[dominant] / total,
        "dominant_year": dominant,
        "usable_years": list(usable),
        "positives": positives,
    }


def sign_of(mean_value):
    if mean_value is None:
        return None
    if mean_value > 0:
        return 1
    if mean_value < 0:
        return -1
    return 0
