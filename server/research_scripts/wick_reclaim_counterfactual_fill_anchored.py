"""Counterfactual FILL_ANCHORED replay for the 112 real WICK_SWEEP_RECLAIM trades
(Fast Smoke reale 2026.06.01-08.26, run5). NO new MT5 run, NO new sweep/reclaim
detection - reuses the exact 112 real trades (entry timestamp, actual fill,
actual SL/TP, actual outcome) already recorded in run5_dataset.json.

For each trade, rebuilds SL/TP anchored to the ACTUAL FILL price instead of
the stale trigger_price, then determines the counterfactual outcome by
replaying the REAL subsequent price path. Raw tick data was not re-extracted
(no MT5 rerun per instruction) - the price path uses M15 OHLC (High/Low per
bar) from nxs_m15_gold_extended.csv, the same GOLD M15 series used throughout
this research. This is a resolution DOWNGRADE vs the tick-level backtest that
produced the actual outcomes (which are known exactly, not re-simulated) -
only the COUNTERFACTUAL outcome is approximated at M15 bar resolution. When a
bar's High/Low range touches BOTH counterfactual SL and TP, the ambiguity is
resolved by whichever level is closer to that bar's OPEN (disclosed
approximation, not tick-verified) and flagged in the output.
"""
import json, csv, statistics
from datetime import datetime, timedelta
from collections import Counter

PIP = 0.1  # 1 pip = $0.10 = 10*pipSize for GOLD (session-wide convention)
SL_PIPS = 25.0
TP_PIPS = 100.0

# --- load M15 OHLC ---
m15 = {}
with open("nxs_m15_gold_extended.csv") as f:
    r = csv.DictReader(f)
    for row in r:
        t = datetime.strptime(row["time"], "%Y.%m.%d %H:%M")
        m15[t] = (float(row["open"]), float(row["high"]), float(row["low"]), float(row["close"]))
times_sorted = sorted(m15.keys())
print(f"M15 bars loaded: {len(m15)}  range {times_sorted[0]} .. {times_sorted[-1]}")

def bars_from(t0, horizon_days=10):
    """M15 bars at or after t0, up to horizon_days later."""
    end = t0 + timedelta(days=horizon_days)
    out = []
    for t in times_sorted:
        if t < t0:
            continue
        if t > end:
            break
        out.append(t)
    return out

def simulate(entry_time, entry_price, side, sl, tp):
    """side: 'LOW' (BUY) or 'HIGH' (SELL). Returns (outcome, exit_price, ambiguous_bar_or_None)."""
    is_buy = (side == "LOW")
    for t in bars_from(entry_time):
        o, h, l, c = m15[t]
        hit_sl = (l <= sl) if is_buy else (h >= sl)
        hit_tp = (h >= tp) if is_buy else (l <= tp)
        if hit_sl and hit_tp:
            # ambiguous same-bar: whichever threshold is closer to the bar's open wins (disclosed approximation)
            d_sl = abs(o - sl)
            d_tp = abs(o - tp)
            if d_sl <= d_tp:
                return ("SL", sl, t)
            else:
                return ("TP", tp, t)
        elif hit_sl:
            return ("SL", sl, None)
        elif hit_tp:
            return ("TP", tp, None)
    return ("NO_RESOLUTION", None, None)

rows = json.load(open(r"C:\Users\User\.claude\jobs\703d44b4\tmp\run5_dataset.json"))
resolved = [r for r in rows if r.get("outcome") in ("SL", "TP")]
print(f"real resolved trades: {len(resolved)}")

out_rows = []
ambiguous_count = 0
no_resolution_count = 0
for r in resolved:
    side = r["side"]
    is_buy = (side == "LOW")
    fill = r["fill_price"]
    trigger = r["trigger_price"]
    entry_time = datetime.fromisoformat(r["open_time"])

    actual_sl = trigger - SL_PIPS*PIP if is_buy else trigger + SL_PIPS*PIP
    actual_tp = trigger + TP_PIPS*PIP if is_buy else trigger - TP_PIPS*PIP
    cf_sl = fill - SL_PIPS*PIP if is_buy else fill + SL_PIPS*PIP
    cf_tp = fill + TP_PIPS*PIP if is_buy else fill - TP_PIPS*PIP

    cf_outcome, cf_exit, ambiguous_bar = simulate(entry_time, fill, side, cf_sl, cf_tp)
    if ambiguous_bar is not None:
        ambiguous_count += 1
    if cf_outcome == "NO_RESOLUTION":
        no_resolution_count += 1

    # BUG FIX (found while drafting): actual_pnl_pips must use the REAL realized
    # distance from fill to the ACTUAL (trigger-anchored) SL/TP - NOT a naive
    # fixed +-25/100, since slippage already distorts that distance (this is
    # exactly the phenomenon under study). A fixed assumption here would silently
    # contradict the $-based PF (0.78-0.80) already established from the real
    # MT5 exits. counterfactual_pnl_pips correctly stays exactly +-25/100 by
    # construction (cf_SL/TP ARE fill-anchored at exactly that distance).
    actual_exit_price = actual_tp if r["outcome"] == "TP" else actual_sl
    actual_pnl_pips = (actual_exit_price - fill)/PIP if is_buy else (fill - actual_exit_price)/PIP
    if cf_outcome == "TP":
        cf_pnl_pips = TP_PIPS
    elif cf_outcome == "SL":
        cf_pnl_pips = -SL_PIPS
    else:
        cf_pnl_pips = None

    if r["outcome"] == "SL" and cf_outcome == "TP":
        cat = "LOSS_SAVED"
    elif r["outcome"] == "TP" and cf_outcome == "TP":
        cat = "WIN_PRESERVED"
    elif r["outcome"] == "TP" and cf_outcome == "SL":
        cat = "WIN_LOST"
    elif r["outcome"] == "SL" and cf_outcome == "SL":
        cat = "BOTH_LOSS"
    elif r["outcome"] == "TP" and cf_outcome == "TP":
        cat = "BOTH_WIN"
    else:
        cat = "OUTCOME_CHANGED_OTHER"

    out_rows.append(dict(
        sweep_id=r["sweep_id"], side=side, trigger_price=trigger, actual_fill=fill,
        slippage_trigger_to_fill_pips=r["slippage_pips"],
        actual_SL=actual_sl, actual_TP=actual_tp,
        counterfactual_SL=cf_sl, counterfactual_TP=cf_tp,
        actual_outcome=r["outcome"], counterfactual_outcome=cf_outcome,
        actual_pnl_pips=actual_pnl_pips, counterfactual_pnl_pips=cf_pnl_pips,
        actual_pnl_usd=r["pnl"], category=cat, ambiguous_same_bar=(ambiguous_bar is not None),
    ))

print(f"ambiguous same-bar resolutions: {ambiguous_count}/{len(resolved)}")
print(f"no-resolution (ran off the end of available M15 data): {no_resolution_count}/{len(resolved)}")

with open("wick_reclaim_counterfactual_fill_anchored.csv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(out_rows[0].keys()))
    w.writeheader()
    for r in out_rows:
        w.writerow(r)

print("\n=== Classification ===")
cats = Counter(r["category"] for r in out_rows)
for k in ["LOSS_SAVED","WIN_PRESERVED","WIN_LOST","BOTH_LOSS","BOTH_WIN","OUTCOME_CHANGED_OTHER"]:
    print(f"  {k}: {cats.get(k,0)}")

usable = [r for r in out_rows if r["counterfactual_outcome"] in ("SL","TP")]
print(f"\nusable for metrics (excludes NO_RESOLUTION): {len(usable)}/{len(out_rows)}")

def metrics(rows_, pnl_key):
    n = len(rows_)
    wins = [r for r in rows_ if r[pnl_key.replace("pnl","outcome")] == "TP"] if False else None
    return n

def compute(rows_, outcome_key, pnl_pip_key):
    n = len(rows_)
    wins = [r for r in rows_ if r[outcome_key] == "TP"]
    losses = [r for r in rows_ if r[outcome_key] == "SL"]
    wr = 100*len(wins)/n if n else 0
    gross_win = sum(r[pnl_pip_key] for r in wins)
    gross_loss = -sum(r[pnl_pip_key] for r in losses)
    pf = gross_win/gross_loss if gross_loss else float("inf")
    expectancy = (gross_win - gross_loss)/n if n else 0
    avg_win = statistics.mean(r[pnl_pip_key] for r in wins) if wins else 0
    avg_loss = statistics.mean(r[pnl_pip_key] for r in losses) if losses else 0
    realized_rr = abs(avg_win/avg_loss) if avg_loss else float("inf")
    return dict(n=n, wins=len(wins), losses=len(losses), wr=wr, pf=pf, expectancy=expectancy,
                avg_win=avg_win, avg_loss=avg_loss, realized_rr=realized_rr)

print("\n=== TRIGGER_ANCHORED (actual, real trades) vs FILL_ANCHORED (counterfactual) ===")
m_actual = compute(usable, "actual_outcome", "actual_pnl_pips")
m_cf = compute(usable, "counterfactual_outcome", "counterfactual_pnl_pips")
for label, m in [("TRIGGER_ANCHORED (actual)", m_actual), ("FILL_ANCHORED (counterfactual)", m_cf)]:
    print(f"  {label}: n={m['n']} WR={m['wr']:.1f}% PF={m['pf']:.2f} expectancy={m['expectancy']:.2f}pip "
          f"avg_win={m['avg_win']:.1f}pip avg_loss={m['avg_loss']:.1f}pip realized_RR={m['realized_rr']:.2f}")

# sequential drawdown / losing streak (pip-based, in chronological order)
def seq_stats(rows_, outcome_key, pnl_pip_key):
    rows_sorted = sorted(rows_, key=lambda r: r["sweep_id"])
    equity = 0.0
    peak = 0.0
    max_dd = 0.0
    streak = 0
    max_streak = 0
    for r in rows_sorted:
        equity += r[pnl_pip_key]
        peak = max(peak, equity)
        dd = peak - equity
        max_dd = max(max_dd, dd)
        if r[outcome_key] == "SL":
            streak += 1
            max_streak = max(max_streak, streak)
        else:
            streak = 0
    return max_dd, max_streak

dd_actual, streak_actual = seq_stats(usable, "actual_outcome", "actual_pnl_pips")
dd_cf, streak_cf = seq_stats(usable, "counterfactual_outcome", "counterfactual_pnl_pips")
print(f"\n  TRIGGER_ANCHORED: max_DD_pips={dd_actual:.1f} max_losing_streak={streak_actual}")
print(f"  FILL_ANCHORED:    max_DD_pips={dd_cf:.1f} max_losing_streak={streak_cf}")

print("\n=== Segmented by |slippage_trigger_to_fill| bucket ===")
buckets = [(0,10),(10,25),(25,50),(50,75),(75,100),(100,10000)]
labels = ["<10pip","10-25","25-50","50-75","75-100","100+"]
for (lo,hi), lab in zip(buckets, labels):
    sub = [r for r in usable if lo <= abs(r["slippage_trigger_to_fill_pips"]) < hi]
    if not sub:
        print(f"  {lab}: n=0")
        continue
    ma = compute(sub, "actual_outcome", "actual_pnl_pips")
    mc = compute(sub, "counterfactual_outcome", "counterfactual_pnl_pips")
    print(f"  {lab}: n={len(sub)}  ACTUAL WR={ma['wr']:.1f}% PF={ma['pf']:.2f}  |  "
          f"FILL_ANCHORED WR={mc['wr']:.1f}% PF={mc['pf']:.2f}")

print("\n=== 15 example rows ===")
for r in out_rows[:15]:
    print(r)
