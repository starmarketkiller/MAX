"""Descriptive statistics for macro-event-gate rows. No p-value hunting beyond prereg CI."""
from __future__ import annotations

import math
import random
from datetime import datetime, timezone


def month_key(epoch):
    return datetime.fromtimestamp(epoch, tz=timezone.utc).strftime("%Y-%m")


def block_bootstrap_mean(rows, value, block=month_key, n_boot=2000, seed=20261030):
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
    out = {
        "n_closed": n,
        "n_skip_sparse_event": sum(1 for r in rows if r.get("status") == "SKIP_SPARSE_EVENT"),
        "n_skip_sparse_control": sum(1 for r in rows if r.get("status") == "SKIP_SPARSE_CONTROL"),
    }
    if n == 0:
        return out
    spreads = [r["spread_delta"] for r in closed]
    ranges = [r["range_delta"] for r in closed]
    out.update({
        "mean_spread_delta": _mean(spreads),
        "mean_range_delta": _mean(ranges),
        "std_spread_delta": (
            math.sqrt(sum((x - _mean(spreads)) ** 2 for x in spreads) / (n - 1)) if n > 1 else None
        ),
        "std_range_delta": (
            math.sqrt(sum((x - _mean(ranges)) ** 2 for x in ranges) / (n - 1)) if n > 1 else None
        ),
    })
    out["mean_spread_delta_ci95_month_blocks"] = block_bootstrap_mean(
        closed,
        lambda r: r["spread_delta"],
        n_boot=int(params["bootstrap_n"]),
        seed=int(params["bootstrap_seed"]),
    )
    out["mean_range_delta_ci95_month_blocks"] = block_bootstrap_mean(
        closed,
        lambda r: r["range_delta"],
        n_boot=int(params["bootstrap_n"]),
        seed=int(params["bootstrap_seed"]) + 1,
    )
    return out


def yearly_breakdown(rows, metric="spread_delta"):
    groups = {}
    for row in rows:
        if row.get("status") == "CLOSED":
            groups.setdefault(row["year"], []).append(row)
    out = {}
    for year, items in sorted(groups.items()):
        vals = [r[metric] for r in items]
        out[year] = {"n": len(items), f"mean_{metric}": _mean(vals)}
    return out


def year_concentration_share(yearly, metric_key="mean_spread_delta", min_n=8):
    usable = {y: v for y, v in yearly.items() if v["n"] >= min_n}
    positives = {y: max(v.get(metric_key) or 0.0, 0.0) for y, v in usable.items()}
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


def metric_elevated(summary, metric):
    """True if month-block CI low > 0 for the named delta metric."""
    ci = summary.get(f"mean_{metric}_ci95_month_blocks")
    mean_v = summary.get(f"mean_{metric}")
    if ci is not None and ci.get("low") is not None:
        return ci["low"] > 0, ci, mean_v
    if mean_v is not None and mean_v > 0 and ci is None:
        # Weak: positive mean without CI — not enough to claim elevation.
        return False, None, mean_v
    return False, ci, mean_v
