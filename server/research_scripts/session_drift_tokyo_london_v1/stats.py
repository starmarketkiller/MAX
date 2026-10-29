"""Descriptive statistics for session-drift rows. No p-value hunting."""
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


def _mean(values):
    return sum(values) / len(values) if values else None


def summarize(rows, params):
    closed = [r for r in rows if r.get("status") == "CLOSED"]
    n = len(closed)
    out = {"n_closed": n}
    if n == 0:
        return out
    nets = [r["net_return_usd"] for r in closed]
    mids = [r["mid_return_usd"] for r in closed]
    deltas = [r["delta_vs_generic_gold_usd"] for r in closed
              if r.get("delta_vs_generic_gold_usd") is not None]
    out.update({
        "mean_net_return_usd": _mean(nets),
        "mean_mid_return_usd": _mean(mids),
        "mean_delta_vs_generic_gold_usd": _mean(deltas),
        "n_with_generic_comparator": len(deltas),
        "std_net_return_usd": (
            math.sqrt(sum((x - _mean(nets)) ** 2 for x in nets) / (n - 1)) if n > 1 else None
        ),
    })
    out["mean_net_return_usd_ci95_month_blocks"] = block_bootstrap_mean(
        closed,
        lambda r: r["net_return_usd"],
        n_boot=int(params["bootstrap_n"]),
        seed=int(params["bootstrap_seed"]),
    )
    if deltas:
        out["mean_delta_vs_generic_gold_usd_ci95_month_blocks"] = block_bootstrap_mean(
            [r for r in closed if r.get("delta_vs_generic_gold_usd") is not None],
            lambda r: r["delta_vs_generic_gold_usd"],
            n_boot=int(params["bootstrap_n"]),
            seed=int(params["bootstrap_seed"]) + 1,
        )
    else:
        out["mean_delta_vs_generic_gold_usd_ci95_month_blocks"] = None
    return out


def yearly_breakdown(rows):
    groups = {}
    for row in rows:
        if row.get("status") == "CLOSED":
            groups.setdefault(row["year"], []).append(row)
    out = {}
    for year, items in sorted(groups.items()):
        nets = [r["net_return_usd"] for r in items]
        out[year] = {"n": len(items), "mean_net_return_usd": _mean(nets)}
    return out


def year_concentration_share(yearly, min_n=20):
    """Share of sum(max(mean,0)) attributable to the single richest year."""
    usable = {y: v for y, v in yearly.items() if v["n"] >= min_n}
    positives = {y: max(v["mean_net_return_usd"] or 0.0, 0.0) for y, v in usable.items()}
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
