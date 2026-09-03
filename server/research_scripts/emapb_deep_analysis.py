import csv
from datetime import datetime, timedelta

DEALS = r"C:\Users\User\AppData\Roaming\MetaQuotes\Terminal\D0E8209F77C8CF37AD8BF550E51FF075\nxs_emapb_step32_clean_nuda_deals.csv"
M15 = "nxs_m15_gold_extended.csv"

LOT_USD_PER_POINT = 1.0  # GOLD: 0.01 lot -> ~$1/point roughly per broker spec used elsewhere this session (confirmed via realized pnl below)

def parse_dt(s):
    return datetime.strptime(s.strip(), "%Y.%m.%d %H:%M:%S")

# ---- 1. reconstruct trades from deals (in/out pairs) ----
rows = []
with open(DEALS, encoding="utf-8") as f:
    r = csv.reader(f)
    for row in r:
        if len(row) < 11:
            continue
        rows.append(row)

trades = []
open_pos = None
for row in rows:
    t = row[0]
    action = row[4].strip()  # in/out
    dirn = row[3].strip()    # buy/sell (this is the ORDER direction, not position direction directly for 'out')
    vol = float(row[5])
    price = float(row[6])
    pnl = float(row[10]) if len(row) > 10 else 0.0
    comment = row[12] if len(row) > 12 else ""
    dt = parse_dt(t)
    if action == "in":
        open_pos = {
            "entry_time": dt, "entry_price": price, "vol": vol,
            "dir": 1 if dirn == "buy" else -1,
        }
    elif action == "out" and open_pos is not None:
        open_pos["exit_time"] = dt
        open_pos["exit_price"] = price
        open_pos["pnl"] = pnl
        open_pos["comment"] = comment
        trades.append(open_pos)
        open_pos = None

print(f"Trade ricostruiti: {len(trades)}")

# ---- 2. load M15 bars into a dict keyed by datetime for fast windowed scan ----
bars = []
with open(M15, encoding="utf-8") as f:
    r = csv.reader(f)
    next(r)
    for row in r:
        if len(row) < 5:
            continue
        dt = datetime.strptime(row[0].strip(), "%Y.%m.%d %H:%M")
        bars.append((dt, float(row[1]), float(row[2]), float(row[3]), float(row[4])))

print(f"Barre M15 caricate: {len(bars)}  ({bars[0][0]} -> {bars[-1][0]})")

# build a simple index: list is already sorted by time, use binary search via bisect on datetimes
import bisect
bar_times = [b[0] for b in bars]

def bars_between(t0, t1):
    i0 = bisect.bisect_left(bar_times, t0)
    i1 = bisect.bisect_right(bar_times, t1)
    return bars[i0:i1]

# ---- 3. per-trade MFE/MAE reconstruction using M15 highs/lows during the open window ----
POINT_VALUE = None  # infer from a trade with known pnl, vol, and price move
results = []
for tr in trades:
    window = bars_between(tr["entry_time"], tr["exit_time"])
    if not window:
        continue
    entry = tr["entry_price"]
    d = tr["dir"]
    vol = tr["vol"]
    # per-lot GOLD point value: standard 100oz contract -> $1 per 0.01 price move per 1.0 lot -> at 0.01 lot, $0.01 per 0.01 => effectively price_diff * vol * 100 ? Let's infer empirically below instead of assuming.
    mfe_price = entry
    mae_price = entry
    mfe_time = tr["entry_time"]
    mae_time = tr["entry_time"]
    for (bt, o, h, l, c) in window:
        if d == 1:
            if h > mfe_price: mfe_price, mfe_time = h, bt
            if l < mae_price: mae_price, mae_time = l, bt
        else:
            if l < mfe_price: mfe_price, mfe_time = l, bt
            if h > mae_price: mae_price, mae_time = h, bt
    mfe_points = (mfe_price - entry) * d
    mae_points = (mae_price - entry) * d  # negative
    exit_points = (tr["exit_price"] - entry) * d
    results.append({
        **tr,
        "mfe_price": mfe_price, "mfe_time": mfe_time, "mfe_points": mfe_points,
        "mae_price": mae_price, "mae_time": mae_time, "mae_points": mae_points,
        "exit_points": exit_points,
        "n_bars": len(window),
    })

# infer $ per point per 0.01 lot from realized pnl vs exit_points (exclude comment containing swap-affecting or breakeven-zero cases)
ratios = []
for r in results:
    if abs(r["exit_points"]) > 0.5 and r["vol"] > 0:
        ratio = r["pnl"] / (r["exit_points"] * (r["vol"] / 0.01))
        ratios.append(ratio)
ratios.sort()
if ratios:
    med = ratios[len(ratios)//2]
    print(f"$ per punto per 0.01 lotto (mediana empirica): {med:.4f}")
    USD_PER_POINT_PER_001 = med
else:
    USD_PER_POINT_PER_001 = 1.0

for r in results:
    scale = USD_PER_POINT_PER_001 * (r["vol"] / 0.01)
    r["mfe_usd"] = r["mfe_points"] * scale
    r["mae_usd"] = r["mae_points"] * scale
    r["giveback_usd"] = r["mfe_usd"] - r["pnl"]
    r["giveback_ratio"] = (r["giveback_usd"] / r["mfe_usd"]) if r["mfe_usd"] > 0.01 else None

# ---- 4. summary stats ----
wins = [r for r in results if r["pnl"] > 0]
losses = [r for r in results if r["pnl"] <= 0]
big_mfe = [r for r in results if r["mfe_usd"] > 5]  # trades that had a meaningful floating profit at some point

print(f"\nTotale trade analizzati: {len(results)}  (vinti={len(wins)} persi={len(losses)})")
print(f"Trade con MFE>$5 in qualche momento: {len(big_mfe)}")

gb = [r["giveback_ratio"] for r in results if r["giveback_ratio"] is not None]
gb_sorted = sorted(results, key=lambda r: (r["giveback_ratio"] if r["giveback_ratio"] is not None else -1), reverse=True)

print("\n=== TOP 15 trade per GIVEBACK (equity flottante raggiunta e poi persa) ===")
print(f"{'entry':17s} {'dir':4s} {'MFE$':>8s} {'exit$':>8s} {'giveback$':>10s} {'gb%':>6s} {'ore a MFE':>10s} {'durata h':>9s} {'comment':s}")
for r in gb_sorted[:15]:
    if r["giveback_ratio"] is None:
        continue
    dur_h = (r["exit_time"] - r["entry_time"]).total_seconds()/3600
    t_to_mfe_h = (r["mfe_time"] - r["entry_time"]).total_seconds()/3600
    print(f"{r['entry_time'].strftime('%Y-%m-%d %H:%M'):17s} {'buy' if r['dir']==1 else 'sell':4s} "
          f"{r['mfe_usd']:8.2f} {r['pnl']:8.2f} {r['giveback_usd']:10.2f} {r['giveback_ratio']*100:5.0f}% "
          f"{t_to_mfe_h:10.1f} {dur_h:9.1f} {r['comment'].strip()}")

print("\n=== Distribuzione giveback ratio (solo trade con MFE>$5) ===")
gb5 = [r["giveback_ratio"] for r in big_mfe if r["giveback_ratio"] is not None]
gb5.sort()
if gb5:
    import statistics
    print(f"n={len(gb5)}  media={statistics.mean(gb5)*100:.0f}%  mediana={statistics.median(gb5)*100:.0f}%")
    print(f"  >70% giveback (quasi tutto perso): {sum(1 for x in gb5 if x>0.7)}")
    print(f"  30-70% giveback: {sum(1 for x in gb5 if 0.3<=x<=0.7)}")
    print(f"  <30% giveback (efficiente): {sum(1 for x in gb5 if x<0.3)}")
    print(f"  giveback negativo (chiuso oltre il picco, es. trailing/tp successivo): {sum(1 for x in gb5 if x<0)}")

import json
with open("emapb_deep_results.json", "w", encoding="utf-8") as f:
    json.dump([{k: (v.isoformat() if isinstance(v, datetime) else v) for k, v in r.items()} for r in results], f, indent=2)
print("\nSalvato emapb_deep_results.json")
