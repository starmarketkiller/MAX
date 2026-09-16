import sys, csv, json
from collections import defaultdict
from datetime import datetime

path = sys.argv[1]
label = sys.argv[2] if len(sys.argv) > 2 else "STRAT"
ALL_RESULTS = {}

try:
    f = open(path, encoding="utf-16")
    rows = list(csv.reader(f))
    if not rows or len(rows[0]) < 5:
        raise ValueError("not utf-16")
except Exception:
    f = open(path, encoding="utf-8-sig")
    rows = list(csv.reader(f))

trades = []
pending = None
for r in rows:
    r = [c.strip() for c in r]
    if len(r) < 9:
        continue
    time_, kind = r[0], r[1]
    if kind == "OPEN":
        price, sl, tp, reason = r[4], r[6], r[7], r[9]
        direction = "BUY" if ("below_price" in reason or "bull" in reason.lower() or "acceptance_above" in reason.lower()) else \
                    ("SELL" if ("above_price" in reason or "bear" in reason.lower() or "acceptance_below" in reason.lower()) else "?")
        pending = {"open_time": time_, "open_price": float(price), "sl": float(sl), "tp": float(tp),
                   "open_reason": reason, "dir": direction}
    elif kind == "CLOSE" and pending is not None:
        price, lots, pnl, reason = r[4], r[5], r[8], r[9]
        rmult = r[11] if len(r) > 11 else None
        pending.update({"close_time": time_, "close_price": float(price), "pnl": float(pnl),
                         "exit_reason": reason, "r": float(rmult) if rmult else None,
                         "lots": float(lots)})
        trades.append(pending)
        pending = None

def dt(s):
    return datetime.strptime(s, "%Y.%m.%d %H:%M:%S")

for t in trades:
    t["open_dt"] = dt(t["open_time"])
    t["close_dt"] = dt(t["close_time"])

n = len(trades)
print(f"=== {label}: {n} trade chiusi (pending non chiuso={1 if pending else 0}) ===\n")

def stats(ts, name="TOTALE"):
    n = len(ts)
    if n == 0:
        print(f"--- {name}: 0 trade ---")
        return {}
    wins = [t for t in ts if t["pnl"] > 0]
    losses = [t for t in ts if t["pnl"] <= 0]
    gross_win = sum(t["pnl"] for t in wins)
    gross_loss = -sum(t["pnl"] for t in losses)
    pf = gross_win / gross_loss if gross_loss > 0 else float("inf")
    net = sum(t["pnl"] for t in ts)
    avg_win = gross_win / len(wins) if wins else 0
    avg_loss = gross_loss / len(losses) if losses else 0
    win_rate = len(wins) / n * 100
    exp = net / n
    payoff = avg_win / avg_loss if avg_loss else float("inf")
    equity = 10000.0
    curve = []
    for t in ts:
        equity += t["pnl"]
        curve.append(equity)
    peak = curve[0]
    maxdd_pct = 0.0
    maxdd_abs = 0.0
    for e in curve:
        peak = max(peak, e)
        dd = peak - e
        ddp = dd / peak * 100 if peak else 0
        maxdd_pct = max(maxdd_pct, ddp)
        maxdd_abs = max(maxdd_abs, dd)
    # max consecutive losses
    maxc = c = 0
    for t in ts:
        if t["pnl"] <= 0:
            c += 1
            maxc = max(maxc, c)
        else:
            c = 0
    # longest flat period (days between a new equity high and the next new equity high)
    peak = curve[0]
    peak_time = ts[0]["close_dt"]
    longest_flat_days = 0
    for i, e in enumerate(curve):
        if e > peak:
            gap = (ts[i]["close_dt"] - peak_time).days
            longest_flat_days = max(longest_flat_days, gap)
            peak = e
            peak_time = ts[i]["close_dt"]
    buys = [t for t in ts if t["dir"] == "BUY"]
    sells = [t for t in ts if t["dir"] == "SELL"]
    def pf_of(sub):
        w = sum(t["pnl"] for t in sub if t["pnl"] > 0)
        l = -sum(t["pnl"] for t in sub if t["pnl"] <= 0)
        return (w / l) if l > 0 else float("inf")
    r = {
        "n": n, "pf": pf, "net": round(net, 2), "expectancy": round(exp, 2),
        "max_dd_pct": round(maxdd_pct, 2), "max_dd_abs": round(maxdd_abs, 2),
        "win_rate": round(win_rate, 1), "avg_win": round(avg_win, 2), "avg_loss": round(avg_loss, 2),
        "payoff": round(payoff, 2), "buy_n": len(buys), "sell_n": len(sells),
        "buy_pf": round(pf_of(buys), 2) if buys else None, "sell_pf": round(pf_of(sells), 2) if sells else None,
        "max_consec_losses": maxc, "longest_flat_days": longest_flat_days,
    }
    r["pf"] = round(pf, 4) if pf != float("inf") else None
    print(f"--- {name} ---")
    for k, v in r.items():
        print(f"  {k}: {v}")
    print()
    ALL_RESULTS[name] = r
    return r

overall = stats(trades, "TOTALE 3Y")

# monthly / yearly
monthly = defaultdict(lambda: {"n": 0, "pnl": 0.0})
yearly = defaultdict(lambda: {"n": 0, "pnl": 0.0})
for t in trades:
    ym = t["close_dt"].strftime("%Y-%m")
    y = t["close_dt"].strftime("%Y")
    monthly[ym]["n"] += 1
    monthly[ym]["pnl"] += t["pnl"]
    yearly[y]["n"] += 1
    yearly[y]["pnl"] += t["pnl"]

print("--- Monthly PnL ---")
for ym in sorted(monthly):
    print(f"  {ym}: n={monthly[ym]['n']:3d} pnl={monthly[ym]['pnl']:9.2f}")
print("\n--- Yearly PnL ---")
for y in sorted(yearly):
    print(f"  {y}: n={yearly[y]['n']:3d} pnl={yearly[y]['pnl']:9.2f}")

# temporal decomposition: Year1/2/3 by calendar position in the window, first/second half
t0 = trades[0]["open_dt"]
t_end = trades[-1]["close_dt"]
total_days = (t_end - t0).days
print(f"\nWindow: {t0} -> {t_end} ({total_days} days)")

y1_end = t0.replace(year=t0.year + 1)
y2_end = t0.replace(year=t0.year + 2)
y3_end = t0.replace(year=t0.year + 3)

year1 = [t for t in trades if t["open_dt"] < y1_end]
year2 = [t for t in trades if y1_end <= t["open_dt"] < y2_end]
year3 = [t for t in trades if t["open_dt"] >= y2_end]
stats(year1, "Year 1")
stats(year2, "Year 2")
stats(year3, "Year 3")

mid = t0 + (t_end - t0) / 2
first_half = [t for t in trades if t["open_dt"] < mid]
second_half = [t for t in trades if t["open_dt"] >= mid]
stats(first_half, "First half")
stats(second_half, "Second half")

# OOS: last 20-25% chronologically
oos_start = t0 + (t_end - t0) * 0.775
is_trades = [t for t in trades if t["open_dt"] < oos_start]
oos_trades = [t for t in trades if t["open_dt"] >= oos_start]
print(f"\nOOS split at {oos_start} (last ~22.5%)")
stats(is_trades, "IS (in-sample, first ~77.5%)")
stats(oos_trades, "OOS (last ~22.5%)")

# cost robustness: post-trade pip stress (GOLD, 100oz/lot convention, $1/pip per 0.01 lot => pip_value = lots*100*0.01 = lots)
NATIVE_PIP = 5.5
CONSERVATIVE_PIP = 7.0
STRESS_PIP = 13.0
def apply_cost(ts, extra_pip):
    out = []
    for t in ts:
        pip_value = t["lots"] * 100 * 0.01  # $ per pip for this trade's lot size
        extra_cost = extra_pip * pip_value
        tt = dict(t)
        tt["pnl"] = t["pnl"] - extra_cost
        out.append(tt)
    return out

print("\n=== COST ROBUSTNESS (post-trade pip stress, applied once per round-trip trade) ===")
print(f"Native (baked into MT5 realized PnL, ~{NATIVE_PIP} pip assumed baseline):")
stats(trades, "NATIVE")
cons = apply_cost(trades, CONSERVATIVE_PIP - NATIVE_PIP)
stats(cons, "CONSERVATIVE")
stress = apply_cost(trades, STRESS_PIP - NATIVE_PIP)
stats(stress, "STRESS")

out_json = path.rsplit(".", 1)[0] + "_metrics.json"
with open(out_json, "w", encoding="utf-8") as f:
    json.dump({"label": label, "window": f"{t0} -> {t_end}", "results": ALL_RESULTS,
               "monthly": {k: v for k, v in monthly.items()}, "yearly": {k: v for k, v in yearly.items()}},
              f, indent=2, default=str)
print(f"\nJSON salvato in {out_json}")
