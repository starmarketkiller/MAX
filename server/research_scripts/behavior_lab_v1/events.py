"""H4 impulse -> H4 pullback -> M15 confirmation -> outcome.

Causality contract (enforced by construction and by tests):
- an H4 bar is used only once it is closed (time >= bar end);
- ATR thresholds use ATR of the previous closed bar, never the bar being judged;
- the pullback event is known at the close of the H4 bar that completes it (T);
- the M15 confirmation only looks at M15 bars starting at or after T;
- the entry is the open of the M15 bar after the confirming one;
- stops come from lows/highs already printed before the entry;
- outcomes never read bars at or after the split end (censored instead).

Prices: levels on BID. A long buys on ASK and exits on BID; a short sells on
BID and exits on ASK, so the spread is paid where it would be.
"""
from __future__ import annotations

from bisect import bisect_left

from .sessions import session_label


def wilder_atr(bars, period):
    """ATR[i] uses bars up to and including i. Callers read ATR[i-1]."""
    atr = [None] * len(bars)
    trs = []
    for i, bar in enumerate(bars):
        if i == 0:
            tr = bar["high"] - bar["low"]
        else:
            prev = bars[i - 1]["close"]
            tr = max(bar["high"] - bar["low"], abs(bar["high"] - prev), abs(bar["low"] - prev))
        trs.append(tr)
        if i + 1 == period:
            atr[i] = sum(trs) / period
        elif i + 1 > period:
            atr[i] = (atr[i - 1] * (period - 1) + tr) / period
    return atr


def detect_impulses(h4, atr, params):
    """Single H4 bar with a directional body >= k * ATR(previous bar)."""
    out = []
    for i in range(1, len(h4)):
        prev_atr = atr[i - 1]
        if prev_atr is None or prev_atr <= 0:
            continue
        bar = h4[i]
        body = bar["close"] - bar["open"]
        rng = bar["high"] - bar["low"]
        if rng <= 0 or abs(body) < params["impulse_body_atr_mult"] * prev_atr:
            continue
        if abs(body) / rng < params["impulse_body_to_range_min"]:
            continue
        out.append({"i": i, "direction": 1 if body > 0 else -1, "atr_prev": prev_atr,
                    "body_atr": abs(body) / prev_atr})
    return out


def detect_pullbacks(h4, impulses, params):
    """First H4 close after the impulse that retraces >= r_min of the impulse leg.

    Long: anchor = impulse bar low, leg extreme = highest high since the impulse
    bar. Retracement at bar j = (extreme_j - low_j) / (extreme_j - anchor).
    A low at or below the anchor invalidates the setup. Mirror for shorts."""
    events = []
    for imp in impulses:
        i, d = imp["i"], imp["direction"]
        anchor = h4[i]["low"] if d == 1 else h4[i]["high"]
        extreme = h4[i]["high"] if d == 1 else h4[i]["low"]
        last = min(len(h4) - 1, i + params["pullback_max_h4_bars"])
        for j in range(i + 1, last + 1):
            bar = h4[j]
            if (d == 1 and bar["low"] <= anchor) or (d == -1 and bar["high"] >= anchor):
                break
            extreme = max(extreme, bar["high"]) if d == 1 else min(extreme, bar["low"])
            leg = (extreme - anchor) if d == 1 else (anchor - extreme)
            if leg <= 0:
                continue
            depth = ((extreme - bar["low"]) if d == 1 else (bar["high"] - extreme)) / leg
            if depth >= params["pullback_retrace_min"]:
                lows = [h4[k]["low"] for k in range(i + 1, j + 1)]
                highs = [h4[k]["high"] for k in range(i + 1, j + 1)]
                events.append({
                    "impulse_i": i, "pullback_j": j, "direction": d,
                    "known_at": bar["end"], "anchor": anchor, "leg_extreme": extreme,
                    "retrace": depth, "atr_prev_impulse": imp["atr_prev"],
                    "impulse_body_atr": imp["body_atr"],
                    "pullback_extreme": min(lows) if d == 1 else max(highs),
                })
                break
    return events


def _starts(bars):
    return [b["start"] for b in bars]


def confirm_m15(m15, known_at, direction, anchor, params, start_index=None):
    """Micro break on M15 after `known_at`.

    Window: M15 bars starting in [known_at, known_at + window). Long confirms at
    the first bar k (with at least `confirm_min_prior_bars` window bars before
    it) whose close is above every high of the earlier window bars. A window low
    at or below the anchor cancels. Returns the confirming index or a reason."""
    window_end = known_at + params["confirm_window_m15_bars"] * 900
    k = start_index
    if k is None:
        k = bisect_left(_starts(m15), known_at)
        k = k if k < len(m15) else None
    if k is None:
        return {"status": "NO_M15_DATA"}
    window = []
    while k < len(m15) and m15[k]["start"] < window_end:
        bar = m15[k]
        if bar["start"] < known_at:          # defensive: never read before the H4 close
            raise AssertionError("M15 bar before the H4 signal was available")
        if (direction == 1 and bar["low"] <= anchor) or (direction == -1 and bar["high"] >= anchor):
            return {"status": "CANCELLED_ANCHOR_BROKEN", "index": k}
        if len(window) >= params["confirm_min_prior_bars"]:
            ref = max(b["high"] for b in window) if direction == 1 else min(b["low"] for b in window)
            if (direction == 1 and bar["close"] > ref) or (direction == -1 and bar["close"] < ref):
                return {"status": "CONFIRMED", "index": k, "window": window + [bar]}
        window.append(bar)
        k += 1
    return {"status": "UNCONFIRMED"}


def simulate_outcome(m15, entry_index, direction, stop, params, split_end):
    """First touch of +target_r R or the stop, within the horizon, on fill-side prices."""
    entry_bar = m15[entry_index]
    entry = entry_bar["ask_open"] if direction == 1 else entry_bar["open"]
    risk = (entry - stop) if direction == 1 else (stop - entry)
    if risk <= 0:
        return {"status": "INVALID_RISK"}
    target = entry + direction * params["target_r"] * risk
    spread_entry = entry_bar["ask_open"] - entry_bar["open"]
    mfe = mae = 0.0
    exit_reason, exit_price, bars_held = None, None, 0
    horizon_end = min(len(m15), entry_index + params["horizon_m15_bars"])
    complete = True
    for k in range(entry_index, horizon_end):
        bar = m15[k]
        if bar["end"] > split_end:
            complete = False
            break
        bars_held += 1
        hi = bar["high"] if direction == 1 else bar["ask_high"]
        lo = bar["low"] if direction == 1 else bar["ask_low"]
        fav = (hi - entry) if direction == 1 else (entry - lo)
        adv = (entry - lo) if direction == 1 else (hi - entry)
        mfe, mae = max(mfe, fav / risk), max(mae, adv / risk)
        stop_hit = lo <= stop if direction == 1 else hi >= stop
        target_hit = hi >= target if direction == 1 else lo <= target
        if stop_hit:                           # both in one bar: the stop counts first
            exit_reason, exit_price = "STOP", stop
            break
        if target_hit:
            exit_reason, exit_price = "TARGET", target
            break
    else:
        if horizon_end - entry_index < params["horizon_m15_bars"]:
            complete = False
    if exit_reason is None:
        if not complete:
            return {"status": "CENSORED", "bars_held": bars_held, "mfe_r": mfe, "mae_r": mae}
        last = m15[horizon_end - 1]
        exit_reason = "TIMEOUT"
        exit_price = last["close"] if direction == 1 else last["ask_close"]
    realized = ((exit_price - entry) if direction == 1 else (entry - exit_price)) / risk
    return {"status": "CLOSED", "exit_reason": exit_reason, "entry": entry, "stop": stop,
            "target": target, "risk": risk, "realized_r": realized,
            "realized_r_net": realized - params["commission_r"],
            "spread_cost_r": spread_entry / risk, "mfe_r": mfe, "mae_r": mae,
            "bars_held": bars_held}


def run_family(h4, m15, params, split_start, split_end, controls=True):
    """Full pipeline on one split. Events are kept only if known inside the split."""
    atr = wilder_atr(h4, params["atr_period"])
    impulses = detect_impulses(h4, atr, params)
    pullbacks = detect_pullbacks(h4, impulses, params)
    starts = _starts(m15)
    rows = []
    for ev in pullbacks:
        if not (split_start <= ev["known_at"] < split_end):
            continue
        rows.append(_trade(m15, starts, h4, atr, ev, params, split_end, kind="EVENT"))
    control_rows = []
    if controls:
        event_times = {r["known_at"] for r in rows}
        for j in range(1, len(h4)):
            t = h4[j]["end"]
            if not (split_start <= t < split_end) or t in event_times or atr[j - 1] is None:
                continue
            for d in (1, -1):
                lows = [h4[j]["low"]]
                highs = [h4[j]["high"]]
                ctrl = {"impulse_i": None, "pullback_j": j, "direction": d, "known_at": t,
                        "anchor": min(lows) if d == 1 else max(highs),
                        "leg_extreme": None, "retrace": None, "atr_prev_impulse": atr[j - 1],
                        "impulse_body_atr": None,
                        "pullback_extreme": min(lows) if d == 1 else max(highs)}
                control_rows.append(_trade(m15, starts, h4, atr, ctrl, params, split_end,
                                           kind="CONTROL"))
    return {"n_h4_bars_in_split": sum(1 for b in h4 if split_start <= b["end"] <= split_end),
            "impulses": impulses, "pullbacks": pullbacks, "events": rows, "controls": control_rows}


def _trade(m15, starts, h4, atr, ev, params, split_end, kind):
    row = {"kind": kind, "direction": ev["direction"], "known_at": ev["known_at"],
           "impulse_i": ev["impulse_i"], "pullback_j": ev["pullback_j"], "retrace": ev["retrace"],
           "impulse_body_atr": ev["impulse_body_atr"]}
    first = bisect_left(starts, ev["known_at"])
    first = first if first < len(m15) else None
    conf = confirm_m15(m15, ev["known_at"], ev["direction"], ev["anchor"], params, first)
    row["confirmation"] = conf["status"]
    if conf["status"] != "CONFIRMED":
        return row
    k = conf["index"]
    entry_index = k + 1
    if entry_index >= len(m15) or m15[entry_index]["start"] - m15[k]["end"] > params["max_entry_gap_seconds"]:
        row["confirmation"] = "NO_ENTRY_BAR"
        return row
    d = ev["direction"]
    window_lows = [b["low"] for b in conf["window"]]
    window_highs = [b["high"] for b in conf["window"]]
    stop = min([ev["pullback_extreme"]] + window_lows) if d == 1 else \
        max([ev["pullback_extreme"]] + window_highs)
    atr_ref = atr[ev["pullback_j"]]
    entry_bar = m15[entry_index]
    entry = entry_bar["ask_open"] if d == 1 else entry_bar["open"]
    risk = (entry - stop) if d == 1 else (stop - entry)
    row.update(confirm_time=m15[k]["end"], entry_time=entry_bar["start"],
               session=session_label(entry_bar["start"]), atr_h4=atr_ref,
               risk_atr=(risk / atr_ref) if atr_ref else None)
    if atr_ref is None or risk < params["min_risk_atr"] * atr_ref or risk > params["max_risk_atr"] * atr_ref:
        row["confirmation"] = "RISK_OUT_OF_BOUNDS"
        return row
    row.update(simulate_outcome(m15, entry_index, d, stop, params, split_end))
    return row
