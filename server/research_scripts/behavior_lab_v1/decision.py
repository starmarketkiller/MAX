"""BL-01 decision rules, declared before any real data was read (2026-10-11).

Discovery is exploratory. GO never means "edge proven": it only authorises
ONE internal_validation read with the same frozen parameters. STOP closes
the hypothesis. INVESTIGATE means the data does not allow either call and a
new, separately pre-registered question is needed before touching validation.
"""
from __future__ import annotations

RULES_VERSION = "BL01_DECISION_RULES_V1"
MIN_EVENTS_STOP = 30
MIN_EVENTS_GO = 60
MIN_QUARTER_POSITIVE_SHARE = 0.6
MIN_CELL_BETTER_SHARE = 0.6
MAX_HOUR_SHARE = 0.35
DIRECTION_FLOOR_R = -0.10
DIRECTION_MIN_N = 20


def _data_failures(summary):
    checks = summary["data_checks"]
    out = []
    if checks["tick_audit"]["verdict"] == "FAIL":
        out.append("tick_audit FAIL")
    if checks["alignment_mismatches"]:
        out.append(f"{len(checks['alignment_mismatches'])} H4/M15 alignment mismatches")
    ref = checks.get("reference_h4_mismatches")
    if isinstance(ref, list) and ref:
        out.append(f"{len(ref)} mismatches against phase7_1 H4 bars")
    if not summary.get("smoke") and checks["manifest"]["verdict"] != "MATCH":
        out.append(f"tick manifest {checks['manifest']['verdict']}")
    for name, health in summary["detector_health"].items():
        if health["status"] == "PATHOLOGICAL":
            out.append(f"{name} detector PATHOLOGICAL")
    return out


def decide(summary):
    reasons = _data_failures(summary)
    if reasons:
        return {"rules": RULES_VERSION, "decision": "STOP", "kind": "DATA_OR_DETECTOR", "reasons": reasons}
    if summary.get("smoke"):
        return {"rules": RULES_VERSION, "decision": "SMOKE_PASSED", "reasons": []}

    ev = summary["events"]
    n = ev.get("n_closed", 0)
    exp = ev.get("expectancy_r_net")
    ci = ev.get("expectancy_r_net_ci95_month_blocks") or {}
    strat = summary["vs_control_stratified"]
    stab = summary["stability"]
    costs = summary["cost_sensitivity"] or {}

    if n < MIN_EVENTS_STOP:
        return {"rules": RULES_VERSION, "decision": "STOP", "kind": "SAMPLE",
                "reasons": [f"only {n} closed events (< {MIN_EVENTS_STOP})"]}
    if ci.get("high") is not None and ci["high"] < 0:
        return {"rules": RULES_VERSION, "decision": "STOP", "kind": "NEGATIVE",
                "reasons": [f"net expectancy CI95 entirely below zero ({ci['low']:.3f}..{ci['high']:.3f} R)"]}
    adj = strat.get("adjusted_delta_expectancy_r")
    if exp is not None and exp <= 0 and (adj is None or adj <= 0):
        return {"rules": RULES_VERSION, "decision": "STOP", "kind": "NO_ADVANTAGE",
                "reasons": [f"net expectancy {exp:.3f} R and no advantage over the control ({adj})"]}

    checks = {
        f"n_closed >= {MIN_EVENTS_GO}": n >= MIN_EVENTS_GO,
        "net expectancy > 0": exp is not None and exp > 0,
        "month-block CI95 low > 0": ci.get("low") is not None and ci["low"] > 0,
        "adjusted delta vs control > 0": adj is not None and adj > 0,
        f"event better than control in >= {MIN_CELL_BETTER_SHARE:.0%} of usable cells":
            strat["cells_used"] > 0 and strat["cells_event_better"] / strat["cells_used"] >= MIN_CELL_BETTER_SHARE,
        f"positive in >= {MIN_QUARTER_POSITIVE_SHARE:.0%} of quarters with n>=5":
            stab["quarters_with_n_ge_5"] > 0
            and stab["quarters_positive"] / stab["quarters_with_n_ge_5"] >= MIN_QUARTER_POSITIVE_SHARE,
        "still > 0 with +0.10R extra cost": costs.get("extra_0.10R", -1) > 0,
        f"no direction below {DIRECTION_FLOOR_R}R with n>={DIRECTION_MIN_N}": all(
            v.get("expectancy_r_net", 0) >= DIRECTION_FLOOR_R
            for v in summary["by_direction"].values() if v.get("n_closed", 0) >= DIRECTION_MIN_N),
        f"no single UTC hour above {MAX_HOUR_SHARE:.0%} of entries":
            (summary["hour_profile"]["max_hour_share"] or 1) <= MAX_HOUR_SHARE,
    }
    failed = [k for k, ok in checks.items() if not ok]
    decision = "GO" if not failed else "INVESTIGATE"
    return {"rules": RULES_VERSION, "decision": decision, "checks": checks, "reasons": failed,
            "meaning": ("one internal_validation read with frozen parameters is allowed; this is NOT a proven edge"
                        if decision == "GO" else
                        "neither GO nor STOP: do not read internal_validation; a new pre-registered question is needed")}
