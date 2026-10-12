"""Descriptive statistics for one event family. No p-value hunting here:
the screening and multiple-testing gates of phase7/engine apply later."""
from __future__ import annotations

import math
import os
import random
import sys
from datetime import datetime, timezone

_ENGINE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "phase7", "engine")
if _ENGINE not in sys.path:
    sys.path.insert(0, _ENGINE)
from event_firing_rate_guard import build_detector_health  # noqa: E402  (reused, not copied)


def wilson(wins, n, z=1.96):
    if n == 0:
        return None
    p = wins / n
    denom = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / denom
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return {"p": p, "low": centre - half, "high": centre + half}


def _quantiles(values, qs=(0.1, 0.25, 0.5, 0.75, 0.9)):
    if not values:
        return None
    ordered = sorted(values)
    out = {}
    for q in qs:
        pos = q * (len(ordered) - 1)
        lo, hi = math.floor(pos), math.ceil(pos)
        out[f"q{int(q * 100)}"] = ordered[lo] + (ordered[hi] - ordered[lo]) * (pos - lo)
    return out


def month_key(epoch):
    return datetime.fromtimestamp(epoch, tz=timezone.utc).strftime("%Y-%m")


def quarter_key(epoch):
    dt = datetime.fromtimestamp(epoch, tz=timezone.utc)
    return f"{dt.year}Q{(dt.month - 1) // 3 + 1}"


def block_bootstrap_mean(rows, value, block=month_key, n_boot=2000, seed=20261011):
    """Resample whole calendar months: events in the same month are not independent."""
    groups = {}
    for r in rows:
        groups.setdefault(block(r["entry_time"]), []).append(value(r))
    keys = sorted(groups)
    if len(keys) < 2:
        return None
    rng = random.Random(seed)
    means = []
    for _ in range(n_boot):
        sample = [v for _ in keys for v in groups[rng.choice(keys)]]
        means.append(sum(sample) / len(sample))
    means.sort()
    return {"low": means[int(0.025 * n_boot)], "high": means[int(0.975 * n_boot) - 1],
            "n_blocks": len(keys), "n_boot": n_boot, "seed": seed}


def summarize(rows, bootstrap=True):
    closed = [r for r in rows if r.get("status") == "CLOSED"]
    n = len(closed)
    out = {"n_closed": n,
           "n_censored": sum(1 for r in rows if r.get("status") == "CENSORED")}
    if n == 0:
        return out
    wins = sum(1 for r in closed if r["exit_reason"] == "TARGET")
    gross = [r["realized_r"] + r["spread_cost_r"] for r in closed]
    net = [r["realized_r_net"] for r in closed]
    out.update({
        "p_target_first": wilson(wins, n),
        "exit_reasons": {k: sum(1 for r in closed if r["exit_reason"] == k)
                         for k in ("TARGET", "STOP", "TIMEOUT")},
        "expectancy_r_net": sum(net) / n,
        "expectancy_r_before_spread": sum(gross) / n,
        "mean_spread_cost_r": sum(r["spread_cost_r"] for r in closed) / n,
        "mfe_r": _quantiles([r["mfe_r"] for r in closed]),
        "mae_r": _quantiles([r["mae_r"] for r in closed]),
        "risk_atr": _quantiles([r["risk_atr"] for r in closed if r.get("risk_atr") is not None]),
    })
    if bootstrap:
        out["expectancy_r_net_ci95_month_blocks"] = block_bootstrap_mean(
            closed, lambda r: r["realized_r_net"])
    return out


def breakdown(rows, key):
    groups = {}
    for r in rows:
        if r.get("status") == "CLOSED":
            groups.setdefault(key(r), []).append(r)
    return {k: summarize(v, bootstrap=False) for k, v in sorted(groups.items())}


def stability(rows):
    """Same sign of net expectancy across quarters is a minimum, not a proof."""
    by_q = breakdown(rows, lambda r: quarter_key(r["entry_time"]))
    signs = [v["expectancy_r_net"] > 0 for v in by_q.values() if v.get("n_closed", 0) >= 5]
    return {"by_quarter": by_q, "quarters_with_n_ge_5": len(signs),
            "quarters_positive": sum(signs)}


def funnel(rows):
    counts = {}
    for r in rows:
        status = r.get("status") or r["confirmation"]
        counts[status] = counts.get(status, 0) + 1
    return counts


def detector_health(result):
    n = result["n_h4_bars_in_split"]
    return {
        "IMPULSE": build_detector_health("H4_IMPULSE", n, [e["i"] for e in result["impulses_in_split"]]),
        "PULLBACK": build_detector_health("H4_PULLBACK_AFTER_IMPULSE", n,
                                          [p["pullback_j"] for p in result["pullbacks_in_split"]]),
    }
