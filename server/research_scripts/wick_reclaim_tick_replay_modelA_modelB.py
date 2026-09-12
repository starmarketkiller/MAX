"""Tick-level replay comparing two executable entry models against the SAME
181 canonical sweep_id's already validated in the shadow/real WICK_SWEEP_RECLAIM
work. NO new detection/ARM logic, NO new sweeps - reuses level_id/side/
trigger_price/armed_time exactly as already recorded.

Tick data source: Dukascopy XAUUSD bid/ask (server/dukascopy_fetch.py family,
export_dukascopy_ticks_mt5.py) - NOT the MT5 broker's own tick feed that
produced the original 181 sweeps/112 real trades. This is a DIFFERENT tick
source (documented risk, not hidden): the project's own dukascopy_fetch.py
docstring already flags a known Python-vs-MT5-broker feed divergence. Used
here because it is the only tick-level data obtainable without launching MT5
(explicitly out of scope per instruction "prima di modificare codice"). The
level_id/side/trigger_price/reclaim_time/armed_time values themselves come
from the REAL MT5 run (run5_dataset.json) - only the tick PATH used to decide
what happens AFTER those events is Dukascopy.

BROKER-TIME OFFSET (found during this run, not assumed): MT5 broker timestamps
in run5_dataset.json are UTC+3, NOT UTC. Verified directly against the tick
data (not inferred): sweep_id=7's trigger_price 4427.26 (armed 2026-06-03
16:45:00 broker time) appears in the Dukascopy UTC tick stream at 13:44:58 -
exactly 3h00m02s earlier. All MT5-native timestamps are shifted by
-timedelta(hours=3) below before any tick lookup. Without this shift, every
sweep's tick lookup lands on the wrong 3-hour window, which is what caused the
apparently random 100-400+ pip "slippage" and impossible negative-pnl TP
outcomes in the first pass of this script - not a data gap, a timezone bug.


MODEL A - RECLAIM_TICK: ARM stays M15 (reused). After ARM, scan every tick for
the first crossing of trigger_price in the reclaim direction. virtual_entry =
actual bid/ask at that tick (NOT trigger_price). SL/TP initially anchored to
trigger_price (comparative baseline, same formula as the real strategy) -
slippage vs trigger recorded separately.

MODEL B - RECLAIM_LIMIT_RETEST: ARM stays M15, reclaim CONFIRMED at the same
M15-gated moment already recorded (reused, not recomputed). After that,
a virtual LIMIT sits at trigger_price; entry only fires if the tick stream
genuinely retests (touches) trigger_price exactly - no tolerance. SL/TP
anchored to trigger_price (exact, since entry price IS trigger_price by
construction when it fires).

Both models terminate their observation window at the same boundary used by
the real ARMED/RECLAIMED lifetime: the next sweep's armed_time on the SAME
side (level replacement), i.e. NO_TRADE if the crossing/retest never happens
before the level would have been replaced.
"""
import json, csv, glob, statistics
from datetime import datetime, timedelta
from collections import Counter, defaultdict

PIP = 0.1
SL_PIPS = 25.0
TP_PIPS = 100.0

# ---------- load tick data (all chunks) ----------
tick_files = sorted(glob.glob(r"C:\Users\User\.claude\jobs\703d44b4\tmp\ticks\chunk*.csv") +
                     glob.glob(r"C:\Users\User\.claude\jobs\703d44b4\tmp\ticks\gapfill.csv"))
print(f"tick chunk files: {tick_files}")

# per-side arrays for binary search: side_ticks[side] = sorted list of (datetime, bid, ask)
all_ticks = []
for fp in tick_files:
    with open(fp) as f:
        r = csv.reader(f)
        header = next(r)
        for row in r:
            date_s, time_s, bid_s, ask_s = row[0], row[1], row[2], row[3]
            t = datetime.strptime(date_s + " " + time_s.split(".")[0], "%Y.%m.%d %H:%M:%S")
            all_ticks.append((t, float(bid_s), float(ask_s)))
all_ticks.sort(key=lambda x: x[0])
print(f"total ticks loaded: {len(all_ticks)}  range {all_ticks[0][0]} .. {all_ticks[-1][0]}")

import bisect
tick_times = [t[0] for t in all_ticks]

def ticks_from(t0, t1):
    """ticks in [t0, t1)"""
    i0 = bisect.bisect_left(tick_times, t0)
    i1 = bisect.bisect_left(tick_times, t1)
    return all_ticks[i0:i1]

BROKER_TO_UTC = timedelta(hours=-3)  # verified against tick data, see module docstring

# ---------- load the 181 sweeps (ARM data, identical across shadow/real) ----------
rows = json.load(open(r"C:\Users\User\.claude\jobs\703d44b4\tmp\run5_dataset.json"))
rows.sort(key=lambda r: r["armed_time"])
for r in rows:
    r["armed_time_dt"] = datetime.fromisoformat(r["armed_time"]) + BROKER_TO_UTC

by_side = defaultdict(list)
for r in rows:
    by_side[r["side"]].append(r)
for side in by_side:
    by_side[side].sort(key=lambda r: r["armed_time_dt"])

TEST_END = datetime(2026, 8, 30)
window_end = {}
for side, lst in by_side.items():
    for i, r in enumerate(lst):
        nxt = lst[i+1]["armed_time_dt"] if i+1 < len(lst) else TEST_END
        window_end[r["sweep_id"]] = nxt

print(f"sweeps: {len(rows)}  window_end computed for all: {len(window_end)==len(rows)}")

GAP_THRESHOLD_SEC = 1200  # 20 min - real inter-tick gaps are seconds; anything
                          # this large means a Dukascopy data hole (even after
                          # gap-fill, 322/1521 weekday hours are still missing)
                          # likely sits right before this tick, so "first
                          # crossing found here" may really be "first crossing
                          # AFTER an unseen stretch" - flagged, not silently
                          # trusted.
def gap_before(t):
    i = bisect.bisect_left(tick_times, t)
    if i == 0:
        return None
    prev_t = tick_times[i-1]
    return (t - prev_t).total_seconds()

def sim_exit(entry_time, entry_price, side, sl, tp, window_end_t):
    """Walk ticks from entry_time to window_end_t, track MAE/MFE, exit on SL/TP touch."""
    is_buy = (side == "LOW")
    mfe = 0.0
    mae = 0.0
    for (t, bid, ask) in ticks_from(entry_time, window_end_t):
        px_for_pnl = bid if is_buy else ask  # close-side price for a BUY you'd sell at bid, for a SELL you'd buy at ask
        favorable = (px_for_pnl - entry_price) if is_buy else (entry_price - px_for_pnl)
        if favorable/PIP > mfe: mfe = favorable/PIP
        if -favorable/PIP > mae: mae = -favorable/PIP
        hit_sl = (bid <= sl) if is_buy else (ask >= sl)
        hit_tp = (bid >= tp) if is_buy else (ask <= tp)
        if hit_sl and hit_tp:
            # both crossed on the same tick record (rare at tick resolution) - use price proximity
            if abs(px_for_pnl - sl) <= abs(px_for_pnl - tp):
                return ("SL", sl, t, mae, mfe)
            else:
                return ("TP", tp, t, mae, mfe)
        elif hit_sl:
            return ("SL", sl, t, mae, mfe)
        elif hit_tp:
            return ("TP", tp, t, mae, mfe)
    return ("NO_RESOLUTION", None, None, mae, mfe)

modelA_rows = []
modelB_rows = []

for r in rows:
    sid = r["sweep_id"]
    side = r["side"]
    is_buy = (side == "LOW")
    trigger = r["trigger_price"]
    armed_t = r["armed_time_dt"]
    wend = window_end[sid]

    actual_sl = trigger - SL_PIPS*PIP if is_buy else trigger + SL_PIPS*PIP
    actual_tp = trigger + TP_PIPS*PIP if is_buy else trigger - TP_PIPS*PIP

    # --- MODEL A: RECLAIM_TICK ---
    entry_a = None
    for (t, bid, ask) in ticks_from(armed_t, wend):
        crossed = (bid <= trigger) if not is_buy else (ask >= trigger)
        if crossed:
            fill = bid if not is_buy else ask
            entry_a = (t, fill)
            break
    if entry_a is None:
        modelA_rows.append(dict(sweep_id=sid, side=side, available=False))
    else:
        entry_time, fill = entry_a
        slippage_pips = (fill - trigger)/PIP if is_buy else (trigger - fill)/PIP
        outcome, exitp, exitt, mae, mfe = sim_exit(entry_time, fill, side, actual_sl, actual_tp, wend)
        delay_sec = (entry_time - armed_t).total_seconds()
        pnl_pips = None
        if outcome in ("SL","TP"):
            exit_px = actual_tp if outcome=="TP" else actual_sl
            pnl_pips = (exit_px - fill)/PIP if is_buy else (fill - exit_px)/PIP
        gap = gap_before(entry_time)
        data_gap_suspect = (gap is not None and gap > GAP_THRESHOLD_SEC)
        modelA_rows.append(dict(sweep_id=sid, side=side, available=True, entry_time=entry_time.isoformat(),
                                 entry_delay_sec=delay_sec, fill=fill, slippage_vs_trigger_pips=slippage_pips,
                                 sl=actual_sl, tp=actual_tp, outcome=outcome, pnl_pips=pnl_pips, mae=mae, mfe=mfe,
                                 data_gap_suspect=data_gap_suspect, gap_before_entry_sec=gap))

    # --- MODEL B: RECLAIM_LIMIT_RETEST ---
    reclaim_t = (datetime.fromisoformat(r["reclaim_time"]) + BROKER_TO_UTC) if r.get("reclaim_time") else None
    if reclaim_t is None or reclaim_t >= wend:
        modelB_rows.append(dict(sweep_id=sid, side=side, available=False, reason="reclaim_not_available_M15"))
    else:
        entry_b = None
        for (t, bid, ask) in ticks_from(reclaim_t, wend):
            touched = (ask <= trigger) if is_buy else (bid >= trigger)
            if touched:
                entry_b = t
                break
        if entry_b is None:
            modelB_rows.append(dict(sweep_id=sid, side=side, available=False, reason="no_retest_before_replacement"))
        else:
            fill = trigger  # exact, by construction
            outcome, exitp, exitt, mae, mfe = sim_exit(entry_b, fill, side, actual_sl, actual_tp, wend)
            delay_sec = (entry_b - armed_t).total_seconds()
            pnl_pips = None
            if outcome in ("SL","TP"):
                exit_px = actual_tp if outcome=="TP" else actual_sl
                pnl_pips = (exit_px - fill)/PIP if is_buy else (fill - exit_px)/PIP
            gap = gap_before(entry_b)
            data_gap_suspect = (gap is not None and gap > GAP_THRESHOLD_SEC)
            modelB_rows.append(dict(sweep_id=sid, side=side, available=True, entry_time=entry_b.isoformat(),
                                     entry_delay_sec=delay_sec, fill=fill, slippage_vs_trigger_pips=0.0,
                                     sl=actual_sl, tp=actual_tp, outcome=outcome, pnl_pips=pnl_pips, mae=mae, mfe=mfe,
                                     data_gap_suspect=data_gap_suspect, gap_before_entry_sec=gap))

FIELDNAMES = ["sweep_id","side","available","entry_time","entry_delay_sec","fill",
              "slippage_vs_trigger_pips","sl","tp","outcome","pnl_pips","mae","mfe","reason",
              "data_gap_suspect","gap_before_entry_sec"]
with open("wick_reclaim_modelA_tick.csv","w",newline="") as f:
    w = csv.DictWriter(f, fieldnames=FIELDNAMES)
    w.writeheader()
    for r_ in modelA_rows: w.writerow(r_)
with open("wick_reclaim_modelB_limitretest.csv","w",newline="") as f:
    w = csv.DictWriter(f, fieldnames=FIELDNAMES)
    w.writeheader()
    for r_ in modelB_rows: w.writerow(r_)

def report(name, model_rows):
    n_total = len(model_rows)
    avail_all = [r for r in model_rows if r["available"]]
    n_gap_suspect = sum(1 for r in avail_all if r.get("data_gap_suspect"))
    avail = [r for r in avail_all if not r.get("data_gap_suspect")]
    resolved = [r for r in avail if r.get("outcome") in ("SL","TP")]
    print(f"\n=== {name} ===")
    print(f"  availability (raw): {len(avail_all)}/{n_total} ({100*len(avail_all)/n_total:.1f}%)")
    print(f"  data_gap_suspect entries EXCLUDED from stats below: {n_gap_suspect}")
    print(f"  availability (clean): {len(avail)}/{n_total} ({100*len(avail)/n_total:.1f}%)")
    print(f"  resolved (excl NO_RESOLUTION): {len(resolved)}")
    if not resolved:
        return
    wins = [r for r in resolved if r["outcome"]=="TP"]
    losses = [r for r in resolved if r["outcome"]=="SL"]
    wr = 100*len(wins)/len(resolved)
    gross_win = sum(r["pnl_pips"] for r in wins)
    gross_loss = -sum(r["pnl_pips"] for r in losses)
    pf = gross_win/gross_loss if gross_loss else float("inf")
    expectancy = (gross_win-gross_loss)/len(resolved)
    print(f"  n_entries={len(resolved)} WR={wr:.1f}% PF={pf:.2f} expectancy={expectancy:.2f}pip")
    print(f"  median MAE={statistics.median(r['mae'] for r in resolved):.1f}pip median MFE={statistics.median(r['mfe'] for r in resolved):.1f}pip")
    print(f"  median entry_delay={statistics.median(r['entry_delay_sec'] for r in avail):.0f}s")
    # losing streak
    seq = sorted(resolved, key=lambda r: r["sweep_id"])
    streak = maxstreak = 0
    for r in seq:
        if r["outcome"]=="SL": streak+=1; maxstreak=max(maxstreak,streak)
        else: streak=0
    print(f"  max_losing_streak={maxstreak}")
    mid = len(seq)//2
    h1, h2 = seq[:mid], seq[mid:]
    def wrf(lst):
        if not lst: return "n=0"
        w_ = sum(1 for r in lst if r["outcome"]=="TP")
        return f"n={len(lst)} WR={100*w_/len(lst):.1f}%"
    print(f"  1st half: {wrf(h1)}   2nd half: {wrf(h2)}")
    buy = [r for r in resolved if r["side"]=="LOW"]
    sell = [r for r in resolved if r["side"]=="HIGH"]
    print(f"  BUY: {wrf(buy)}   SELL: {wrf(sell)}")

report("MODEL A - RECLAIM_TICK", modelA_rows)
report("MODEL B - RECLAIM_LIMIT_RETEST", modelB_rows)

# ---------- matrix vs baseline (real WICK_SWEEP_RECLAIM outcome, run5) ----------
baseline_by_sid = {r["sweep_id"]: r for r in rows}

def matrix_vs_baseline(name, model_rows):
    cats = Counter()
    for mr in model_rows:
        sid = mr["sweep_id"]
        base = baseline_by_sid[sid]
        base_outcome = base.get("outcome")  # SL / TP / None(no trade)
        model_outcome = mr.get("outcome") if (mr["available"] and not mr.get("data_gap_suspect")) else None
        if base_outcome is None:
            base_state = "NO_TRADE"
        else:
            base_state = base_outcome
        if model_outcome is None or model_outcome == "NO_RESOLUTION":
            model_state = "NO_TRADE"
        else:
            model_state = model_outcome

        if base_state == "SL" and model_state == "TP":
            cat = "BASELINE_LOSS->MODEL_WIN"
        elif base_state == "SL" and model_state == "NO_TRADE":
            cat = "BASELINE_LOSS->NO_TRADE"
        elif base_state == "TP" and model_state == "TP":
            cat = "BASELINE_WIN->MODEL_WIN"
        elif base_state == "TP" and model_state == "SL":
            cat = "BASELINE_WIN->MODEL_LOSS"
        elif base_state == "TP" and model_state == "NO_TRADE":
            cat = "BASELINE_WIN->NO_TRADE"
        elif base_state == "SL" and model_state == "SL":
            cat = "BOTH_LOSS"
        elif base_state == "NO_TRADE" and model_state == "NO_TRADE":
            cat = "BOTH_NO_TRADE"
        elif base_state == "NO_TRADE" and model_state in ("SL","TP"):
            cat = f"NO_TRADE->MODEL_{model_state}"
        else:
            cat = "OTHER"
        cats[cat] += 1
    print(f"\n=== Matrix vs BASELINE (real WICK_SWEEP_RECLAIM) - {name} ===")
    for k, v in sorted(cats.items()):
        print(f"  {k}: {v}")

matrix_vs_baseline("MODEL A", modelA_rows)
matrix_vs_baseline("MODEL B", modelB_rows)

print("\nSaved wick_reclaim_modelA_tick.csv and wick_reclaim_modelB_limitretest.csv")
