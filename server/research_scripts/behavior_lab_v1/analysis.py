"""Secondary analyses for BL-01, declared before any real data was read.

Profit factor, cost sensitivity, and a control comparison that holds
direction, session and volatility fixed, so an apparent edge that is only
"more NY-session trades" or "more high-volatility trades" shows up as such.
"""
from __future__ import annotations

from datetime import datetime, timezone

EXTRA_COST_R = (0.0, 0.05, 0.10, 0.20)


def closed(rows):
    return [r for r in rows if r.get("status") == "CLOSED"]


def profit_factor(rows):
    net = [r["realized_r_net"] for r in closed(rows)]
    gains = sum(v for v in net if v > 0)
    losses = -sum(v for v in net if v < 0)
    if not net:
        return None
    return None if losses == 0 else gains / losses


def cost_sensitivity(rows, target_r):
    """Expectancy after extra per-trade costs (R) and with the spread paid twice."""
    c = closed(rows)
    if not c:
        return None
    base = sum(r["realized_r_net"] for r in c) / len(c)
    out = {f"extra_{x:.2f}R": base - x for x in EXTRA_COST_R}
    out["double_spread"] = base - sum(r["spread_cost_r"] for r in c) / len(c)
    # +target_r on a win, -1 on a loss: breakeven p = 1 / (1 + target_r), before costs
    out["breakeven_win_rate_gross"] = 1 / (1 + target_r)
    return out


def volatility_terciles(control_rows):
    """ATR cut points from the CONTROL population, so events cannot shape their own bins."""
    atrs = sorted(r["atr_h4"] for r in closed(control_rows) if r.get("atr_h4"))
    if len(atrs) < 3:
        return None
    return atrs[len(atrs) // 3], atrs[2 * len(atrs) // 3]


def _vol_bin(atr, cuts):
    if atr is None or cuts is None:
        return "NA"
    return "LOW" if atr < cuts[0] else ("MID" if atr < cuts[1] else "HIGH")


def stratum(row, cuts):
    return ("BUY" if row["direction"] == 1 else "SELL", row.get("session") or "NA",
            _vol_bin(row.get("atr_h4"), cuts))


def _cell(rows):
    c = closed(rows)
    if not c:
        return None
    return {"n": len(c), "p": sum(1 for r in c if r["exit_reason"] == "TARGET") / len(c),
            "exp": sum(r["realized_r_net"] for r in c) / len(c)}


def stratified_vs_control(events, controls, min_control=20):
    """Direct standardisation: compare events with controls inside the same
    (direction, session, volatility) cell, then weight by event counts."""
    cuts = volatility_terciles(controls)
    ev_cells, ct_cells = {}, {}
    for r in closed(events):
        ev_cells.setdefault(stratum(r, cuts), []).append(r)
    for r in closed(controls):
        ct_cells.setdefault(stratum(r, cuts), []).append(r)
    cells, w_sum, dp_sum, de_sum, uncovered = [], 0, 0.0, 0.0, 0
    for key, ev_rows in sorted(ev_cells.items()):
        e, c = _cell(ev_rows), _cell(ct_cells.get(key, []))
        usable = c is not None and c["n"] >= min_control
        cells.append({"stratum": list(key), "events": e, "controls": c, "used": usable})
        if not usable:
            uncovered += e["n"]
            continue
        w_sum += e["n"]
        dp_sum += e["n"] * (e["p"] - c["p"])
        de_sum += e["n"] * (e["exp"] - c["exp"])
    return {"volatility_cuts_atr": cuts, "min_control_per_cell": min_control, "cells": cells,
            "events_in_covered_cells": w_sum, "events_without_comparable_control": uncovered,
            "adjusted_delta_p": (dp_sum / w_sum) if w_sum else None,
            "adjusted_delta_expectancy_r": (de_sum / w_sum) if w_sum else None,
            "cells_event_better": sum(1 for x in cells if x["used"] and x["events"]["exp"] > x["controls"]["exp"]),
            "cells_used": sum(1 for x in cells if x["used"])}


def hour_profile(rows):
    """Entries per UTC hour: a strong concentration means the result is a clock effect."""
    hours = {}
    for r in closed(rows):
        h = datetime.fromtimestamp(r["entry_time"], tz=timezone.utc).hour
        hours[h] = hours.get(h, 0) + 1
    total = sum(hours.values())
    top = max(hours.values()) / total if total else None
    return {"by_hour_utc": dict(sorted(hours.items())), "max_hour_share": top}


def selection_profile(events, controls):
    """How much the H4 context changes who reaches a trade at all."""
    def rate(rows):
        n = len(rows)
        return (len(closed(rows)) / n) if n else None
    return {"events_seen": len(events), "events_closed_share": rate(events),
            "controls_seen": len(controls), "controls_closed_share": rate(controls)}
