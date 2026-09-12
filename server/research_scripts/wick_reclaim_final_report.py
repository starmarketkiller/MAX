import json, re, statistics
from datetime import datetime

path = r"C:\Users\User\.claude\jobs\703d44b4\tmp\t3_shadow4_window.txt"
LINE_RE = re.compile(r'(\d{4}\.\d{2}\.\d{2} \d{2}:\d{2}:\d{2})\s+(\[WICKSHADOW\]\[\w+\]|\[RESEARCH\]\[\w+\])\s+(.*)')
def parse_kv(s):
    d = {}
    for m in re.finditer(r'(\w+)=("[^"]*"|\S+)', s):
        d[m.group(1)] = m.group(2)
    return d

sweeps = {}
opens, exits = [], []
for line in open(path, encoding='utf-8', errors='ignore'):
    m = LINE_RE.search(line)
    if not m: continue
    bar_time_s, tag, rest = m.groups()
    bar_time = datetime.strptime(bar_time_s, '%Y.%m.%d %H:%M:%S')
    kv = parse_kv(rest)
    if tag == '[WICKSHADOW][SWEEP]':
        sid = int(kv['sweep_id'])
        sweeps[sid] = dict(sweep_id=sid, level_id=int(kv['level_id']), side=kv['side'],
                            level_price=float(kv['level']), trigger_price=float(kv['trigger']),
                            sweep_time=bar_time, reclaimed_trigger=False, reclaim_trigger_time=None,
                            max_pen=None, time_to_reclaim_sec=None, virtual_entry=None,
                            virtual_sl=None, virtual_tp=None, outcome=None, exit_time=None,
                            mae=None, mfe=None, hold_sec=None, abandoned=False, abandon_reason=None)
    elif tag == '[WICKSHADOW][RECLAIM_TRIGGER]':
        sid = int(kv['sweep_id'])
        if sid in sweeps:
            sweeps[sid].update(reclaimed_trigger=True, reclaim_trigger_time=bar_time,
                                time_to_reclaim_sec=int(kv['time_sweep_to_reclaim_sec']),
                                max_pen=float(kv['max_penetration_before_reclaim_pips']),
                                virtual_entry=float(kv['virtual_entry']), virtual_sl=float(kv['virtual_sl']),
                                virtual_tp=float(kv['virtual_tp']))
    elif tag == '[WICKSHADOW][EXIT]':
        sid = int(kv['sweep_id'])
        if sid in sweeps:
            sweeps[sid].update(outcome=kv['outcome'], exit_time=bar_time,
                                mae=float(kv['virtual_MAE_pips']), mfe=float(kv['virtual_MFE_pips']),
                                hold_sec=int(kv['hold_sec']))
    elif tag == '[WICKSHADOW][ABANDONED]':
        sid = int(kv['sweep_id'])
        if sid in sweeps:
            sweeps[sid].update(abandoned=True, abandon_reason=kv.get('reason'))
    elif tag == '[RESEARCH][OPEN]' and kv.get('strategy') == 'WICK_SWEEP_REV':
        opens.append(dict(time=bar_time, dir=kv['dir'], entry=float(kv['entry']), sl=float(kv['sl']), tp=float(kv['tp'])))
    elif tag == '[RESEARCH][EXIT]' and kv.get('strategy') == 'WICK_SWEEP_REV':
        exits.append(dict(time=bar_time, authority=kv['exit_authority'], pnl=float(kv['pnl'])))

opens_sorted = sorted(opens, key=lambda o: o['time'])
exits_sorted = sorted(exits, key=lambda e: e['time'])
trades = []
ei = 0
for o in opens_sorted:
    while ei < len(exits_sorted) and exits_sorted[ei]['time'] < o['time']:
        ei += 1
    if ei < len(exits_sorted):
        trades.append((o, exits_sorted[ei])); ei += 1

side_to_dir = {'LOW': 'BUY', 'HIGH': 'SELL'}
opens_by_key = {}
for i, o in enumerate(opens):
    key = (o['time'].isoformat(), round(o['entry'], 5), o['dir'])
    opens_by_key.setdefault(key, []).append(i)

# exact match sweep -> trade index
sweep_to_trade_idx = {}
used_open_idx = set()
for sid, sw in sweeps.items():
    key = (sw['sweep_time'].isoformat(), round(sw['trigger_price'], 5), side_to_dir[sw['side']])
    cand = opens_by_key.get(key)
    if cand:
        idx = cand[0]
        sweep_to_trade_idx[sid] = idx
        used_open_idx.add(idx)

# find orphan opens (real trades with no exact shadow match)
orphan_idx = [i for i in range(len(opens)) if i not in used_open_idx]

# manual reconciliation: known off-by-one-cohort-bar cases (sweep 101, 153) pair with
# the orphan open on the SAME side that occurs exactly one M15 bar (15 min) earlier
# than the shadow SWEEP timestamp, at a shallower (less negative) price on the same level.
for sid in (101, 153):
    sw = sweeps[sid]
    best = None
    for i in orphan_idx:
        o = opens[i]
        if o['dir'] != side_to_dir[sw['side']]:
            continue
        delta = (sw['sweep_time'] - o['time']).total_seconds()
        if 0 < delta <= 900:  # up to one M15 bar earlier
            best = i
            break
    if best is not None:
        sweep_to_trade_idx[sid] = best
        orphan_idx.remove(best)

# build trade-index -> (open, exit)
def trade_for_open_idx(i):
    o = opens[i]
    # find matching exit: sequential order among opens_sorted/exits_sorted was built on opens_sorted,
    # so re-derive via original open object identity search in `trades`
    for (oo, ee) in trades:
        if oo is o:
            return (oo, ee)
    return None

rows = []
for sid in sorted(sweeps.keys()):
    sw = sweeps[sid]
    trade = None
    if sid in sweep_to_trade_idx:
        trade = trade_for_open_idx(sweep_to_trade_idx[sid])
    if trade:
        o, e = trade
        canonical_entry_time = o['time']
        canonical_entry_price = o['entry']
        canonical_outcome = 'SL' if e['authority'] == 'BROKER_SL' else ('TP' if e['authority'] == 'BROKER_TP' else e['authority'])
    else:
        canonical_entry_time = None
        canonical_entry_price = None
        canonical_outcome = 'NO_ENTRY'

    reclaim_avail = sw['reclaimed_trigger'] and sw['outcome'] is not None
    virtual_outcome = sw['outcome'] if reclaim_avail else None

    if canonical_outcome == 'NO_ENTRY':
        cat = 'NO_BASELINE_ENTRY'
    elif not reclaim_avail:
        cat = 'RECLAIM_NOT_AVAILABLE'
    elif canonical_outcome == 'SL' and virtual_outcome == 'SL':
        cat = 'BOTH_SL'
    elif canonical_outcome == 'SL' and virtual_outcome == 'TP':
        cat = 'BASELINE_SL_AVOIDED'
    elif canonical_outcome == 'TP' and virtual_outcome == 'TP':
        cat = 'BASELINE_TP_PRESERVED'
    elif canonical_outcome == 'TP' and virtual_outcome == 'SL':
        cat = 'BASELINE_TP_LOST'
    else:
        cat = 'OTHER'

    rows.append(dict(
        sweep_id=sid, level_id=sw['level_id'], side=sw['side'],
        canonical_entry_time=canonical_entry_time.isoformat() if canonical_entry_time else None,
        canonical_entry_price=canonical_entry_price,
        canonical_outcome=canonical_outcome,
        reclaim_available=reclaim_avail,
        reclaim_time=sw['reclaim_trigger_time'].isoformat() if sw['reclaim_trigger_time'] else None,
        reclaim_delay_sec=sw['time_to_reclaim_sec'],
        reclaim_entry_price=sw['virtual_entry'],
        virtual_outcome=virtual_outcome,
        virtual_MAE=sw['mae'] if reclaim_avail else None,
        virtual_MFE=sw['mfe'] if reclaim_avail else None,
        max_penetration_before_reclaim=sw['max_pen'],
        category=cat,
        sweep_time=sw['sweep_time'].isoformat(),
    ))

with open(r"C:\Users\User\.claude\jobs\703d44b4\tmp\wick_reclaim_event_matrix.json", "w") as f:
    json.dump(rows, f, indent=1, default=str)

import csv
with open(r"C:\Users\User\.claude\jobs\703d44b4\tmp\wick_reclaim_event_matrix.csv", "w", newline='') as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
    w.writeheader()
    for r in rows: w.writerow(r)

print(f"Total rows: {len(rows)}")
print("\n=== CLASSIFICATION MATRIX ===")
from collections import Counter
c = Counter(r['category'] for r in rows)
for k in ['BASELINE_SL_AVOIDED','BOTH_SL','BASELINE_TP_PRESERVED','BASELINE_TP_LOST','RECLAIM_NOT_AVAILABLE','NO_BASELINE_ENTRY','OTHER']:
    print(f"  {k}: {c.get(k,0)}")

# --- baseline totals ---
base_sl_rows = [r for r in rows if r['canonical_outcome']=='SL']
base_tp_rows = [r for r in rows if r['canonical_outcome']=='TP']
print(f"\nBaseline totals: SL={len(base_sl_rows)} TP={len(base_tp_rows)} NO_ENTRY={sum(1 for r in rows if r['canonical_outcome']=='NO_ENTRY')}")

print("\n=== Fate of 148(baseline SL) rows ===")
sl_no_trade = sum(1 for r in base_sl_rows if r['category']=='RECLAIM_NOT_AVAILABLE')
sl_stays_sl = sum(1 for r in base_sl_rows if r['category']=='BOTH_SL')
sl_to_tp   = sum(1 for r in base_sl_rows if r['category']=='BASELINE_SL_AVOIDED')
print(f"  n={len(base_sl_rows)}  NO_TRADE(reclaim unavailable)={sl_no_trade}  stays_SL={sl_stays_sl}  becomes_TP={sl_to_tp}")

print("\n=== Fate of 30(baseline TP) rows ===")
tp_no_trade = sum(1 for r in base_tp_rows if r['category']=='RECLAIM_NOT_AVAILABLE')
tp_preserved = sum(1 for r in base_tp_rows if r['category']=='BASELINE_TP_PRESERVED')
tp_to_sl = sum(1 for r in base_tp_rows if r['category']=='BASELINE_TP_LOST')
print(f"  n={len(base_tp_rows)}  preserved(TP->TP)={tp_preserved}  lost_no_trade(reclaim unavailable)={tp_no_trade}  flips_to_SL={tp_to_sl}")

# --- aggregate reclaim stats ---
avail = [r for r in rows if r['reclaim_available'] and r['virtual_outcome'] is not None]
n_avail = len(avail); n_total = len(rows)
wins = [r for r in avail if r['virtual_outcome']=='TP']
losses = [r for r in avail if r['virtual_outcome']=='SL']
print(f"\n=== RECLAIM_TRIGGER aggregate (n_avail={n_avail}/{n_total} = {100*n_avail/n_total:.1f}%) ===")
wr_reclaim = 100*len(wins)/n_avail
pf_reclaim = (len(wins)*100.0)/(len(losses)*25.0) if losses else float('inf')
expectancy_reclaim = (wr_reclaim/100*100.0) - ((100-wr_reclaim)/100*25.0)
print(f"  WR_reclaim: {wr_reclaim:.1f}% ({len(wins)}/{n_avail})")
print(f"  PF_reclaim (pip, fixed 25/100): {pf_reclaim:.2f}")
print(f"  expectancy_reclaim: {expectancy_reclaim:.2f} pip/trade")
print(f"  median MAE: {statistics.median(r['virtual_MAE'] for r in avail):.2f} pip")
print(f"  median MFE: {statistics.median(r['virtual_MFE'] for r in avail):.2f} pip")
print(f"  median reclaim delay: {statistics.median(r['reclaim_delay_sec'] for r in avail):.0f} sec ({statistics.median(r['reclaim_delay_sec'] for r in avail)/60:.1f} min)")

buy = [r for r in avail if r['side']=='LOW']; sell = [r for r in avail if r['side']=='HIGH']
print(f"  BUY(LOW): n={len(buy)} WR={100*sum(1 for r in buy if r['virtual_outcome']=='TP')/len(buy):.1f}%")
print(f"  SELL(HIGH): n={len(sell)} WR={100*sum(1 for r in sell if r['virtual_outcome']=='TP')/len(sell):.1f}%")

ts = sorted(avail, key=lambda r: r['sweep_time'])
mid = len(ts)//2
h1, h2 = ts[:mid], ts[mid:]
print(f"  1st half: n={len(h1)} WR={100*sum(1 for r in h1 if r['virtual_outcome']=='TP')/len(h1):.1f}%")
print(f"  2nd half: n={len(h2)} WR={100*sum(1 for r in h2 if r['virtual_outcome']=='TP')/len(h2):.1f}%")

print("\n=== reclaim delay distribution (sec) ===")
delays = sorted(r['reclaim_delay_sec'] for r in avail)
qs = statistics.quantiles(delays, n=4)
print(f"  min={delays[0]} p25={qs[0]:.0f} median={statistics.median(delays):.0f} p75={qs[2]:.0f} max={delays[-1]}")
buckets = Counter()
for d in delays:
    if d <= 900: buckets['<=15min']+=1
    elif d <= 1800: buckets['15-30min']+=1
    elif d <= 3600: buckets['30-60min']+=1
    elif d <= 7200: buckets['1-2h']+=1
    else: buckets['>2h']+=1
for k in ['<=15min','15-30min','30-60min','1-2h','>2h']:
    print(f"    {k}: {buckets.get(k,0)}")

print("\n=== max_penetration_before_reclaim distribution (pip) ===")
pens = sorted(r['max_penetration_before_reclaim'] for r in avail if r['max_penetration_before_reclaim'] is not None)
qs = statistics.quantiles(pens, n=4)
print(f"  min={pens[0]:.1f} p25={qs[0]:.1f} median={statistics.median(pens):.1f} p75={qs[2]:.1f} max={pens[-1]:.1f}")
buckets = Counter()
for p in pens:
    if p <= 50: buckets['<=50pip']+=1
    elif p <= 100: buckets['50-100pip']+=1
    elif p <= 200: buckets['100-200pip']+=1
    elif p <= 500: buckets['200-500pip']+=1
    else: buckets['>500pip']+=1
for k in ['<=50pip','50-100pip','100-200pip','200-500pip','>500pip']:
    print(f"    {k}: {buckets.get(k,0)}")

# --- baseline aggregate (for WR/PF comparison) ---
print(f"\n=== BASELINE (IMMEDIATE_FADE reale) ===")
n_base = len(trades)
base_wins = sum(1 for o,e in trades if e['authority']=='BROKER_TP')
base_losses = sum(1 for o,e in trades if e['authority']=='BROKER_SL')
wr_base = 100*base_wins/n_base
pf_base = (base_wins*100.0)/(base_losses*25.0) if base_losses else float('inf')
expectancy_base = (wr_base/100*100.0) - ((100-wr_base)/100*25.0)
print(f"  n={n_base} TP={base_wins} SL={base_losses}")
print(f"  WR_baseline: {wr_base:.1f}%  PF_baseline: {pf_base:.2f}  expectancy_baseline: {expectancy_base:.2f} pip/trade")

print("\n=== 20 event examples (full detail) ===")
for r in rows[:20]:
    print(r)
