import re, json, statistics
from datetime import datetime
from collections import Counter

path = r"C:\Users\User\.claude\jobs\703d44b4\tmp\run5_wickreclaim_window.txt"
LINE_RE = re.compile(r'(\d{4}\.\d{2}\.\d{2} \d{2}:\d{2}:\d{2})\s+(\[WICKRECLAIM\]\[[A-Z_]+\]|\[RESEARCH\]\[\w+\])\s+(.*)')
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

    if tag == '[WICKRECLAIM][ARMED]':
        sid = int(kv['sweep_id'])
        sweeps[sid] = dict(sweep_id=sid, level_id=int(kv['level_id']), side=kv['side'],
                            level_price=float(kv['level']), trigger_price=float(kv['trigger']),
                            armed_time=bar_time, reclaim_time=None, entry_attempts=0,
                            opened=False, open_time=None, blocked_reasons=[], abandoned=False,
                            abandoned_time=None)
    elif tag == '[WICKRECLAIM][RECLAIM_AVAILABLE]':
        sid = int(kv['sweep_id'])
        if sid in sweeps:
            sweeps[sid]['reclaim_time'] = bar_time
            sweeps[sid]['reclaim_price'] = float(kv['price'])
            sweeps[sid]['max_pen'] = float(kv['max_penetration_before_reclaim_pips'])
            sweeps[sid]['reclaim_delay_sec'] = int(kv['time_sweep_to_reclaim_sec'])
    elif tag == '[WICKRECLAIM][ENTRY_ATTEMPT]':
        sid = int(kv['sweep_id'])
        if sid in sweeps:
            sweeps[sid]['entry_attempts'] += 1
    elif tag == '[WICKRECLAIM][OPENED]':
        sid = int(kv['sweep_id'])
        if sid in sweeps:
            sweeps[sid]['opened'] = True
            sweeps[sid]['open_time'] = bar_time
    elif tag.startswith('[WICKRECLAIM][BLOCKED'):
        sid = int(kv['sweep_id'])
        if sid in sweeps:
            sweeps[sid]['blocked_reasons'].append(tag)
    elif tag == '[WICKRECLAIM][ABANDONED]':
        sid = int(kv['sweep_id'])
        if sid in sweeps:
            sweeps[sid]['abandoned'] = True
            sweeps[sid]['abandoned_time'] = bar_time
    elif tag == '[RESEARCH][OPEN]' and kv.get('strategy') == 'WICK_SWEEP_RECLAIM':
        opens.append(dict(time=bar_time, dir=kv['dir'], entry=float(kv['entry']), sl=float(kv['sl']), tp=float(kv['tp'])))
    elif tag == '[RESEARCH][EXIT]' and kv.get('strategy') == 'WICK_SWEEP_RECLAIM':
        exits.append(dict(time=bar_time, authority=kv['exit_authority'], pnl=float(kv['pnl'])))

print(f"run5 sweeps parsed: {len(sweeps)}")
print(f"run5 real opens: {len(opens)}  exits: {len(exits)}")

# pair opens/exits sequentially
opens_sorted = sorted(opens, key=lambda o: o['time'])
exits_sorted = sorted(exits, key=lambda e: e['time'])
trades = []
ei = 0
for o in opens_sorted:
    while ei < len(exits_sorted) and exits_sorted[ei]['time'] < o['time']:
        ei += 1
    if ei < len(exits_sorted):
        trades.append((o, exits_sorted[ei])); ei += 1
print(f"paired real trades: {len(trades)}")

# match trade to sweep by exact opened_time == open.time and entry price == open.entry (fill price, not trigger)
opens_by_time = {}
for i, o in enumerate(opens):
    opens_by_time.setdefault(o['time'].isoformat(), []).append(i)

matched_idx = set()
for sid, sw in sweeps.items():
    if not sw['opened']: continue
    cand = opens_by_time.get(sw['open_time'].isoformat())
    if cand:
        for i in cand:
            if i not in matched_idx:
                sw['trade_idx'] = i
                matched_idx.add(i)
                break

n_opened_sweeps = sum(1 for sw in sweeps.values() if sw['opened'])
n_matched = sum(1 for sw in sweeps.values() if 'trade_idx' in sw)
print(f"sweeps marked opened: {n_opened_sweeps}, matched to a real OPEN by exact time: {n_matched}")

# real WR/PF
def trade_for_idx(i):
    o = opens[i]
    for (oo, ee) in trades:
        if oo is o: return (oo, ee)
    return None

wins = losses = 0
for sw in sweeps.values():
    if 'trade_idx' not in sw: continue
    t = trade_for_idx(sw['trade_idx'])
    if not t: continue
    o, e = t
    sw['fill_price'] = o['entry']
    sw['outcome'] = 'TP' if e['authority'] == 'BROKER_TP' else ('SL' if e['authority'] == 'BROKER_SL' else e['authority'])
    sw['pnl'] = e['pnl']
    sw['slippage_pips'] = (o['entry'] - sw['trigger_price']) / 0.1 if sw['side']=='LOW' else (sw['trigger_price'] - o['entry']) / 0.1
    if sw['outcome'] == 'TP': wins += 1
    elif sw['outcome'] == 'SL': losses += 1

n_resolved = wins + losses
print(f"\n=== REAL trade outcomes (resolved={n_resolved}) ===")
print(f"  WR: {100*wins/n_resolved:.1f}% ({wins}/{n_resolved})")
pf = (wins*100.0)/(losses*25.0) if losses else float('inf')
print(f"  PF (pip, 25/100 fixed): {pf:.2f}")

# delay from RECLAIM_AVAILABLE to actual OPEN (bars)
delays_open = []
for sw in sweeps.values():
    if sw.get('reclaim_time') and sw.get('open_time'):
        d = (sw['open_time'] - sw['reclaim_time']).total_seconds()
        delays_open.append(d)
        sw['reclaim_to_open_delay_sec'] = d
print(f"\n=== Reclaim-available -> actual OPEN delay (real, n={len(delays_open)}) ===")
if delays_open:
    print(f"  same-bar (0s): {sum(1 for d in delays_open if d==0)}")
    print(f"  1 bar later (900s): {sum(1 for d in delays_open if d==900)}")
    print(f"  2+ bars later (>900s): {sum(1 for d in delays_open if d>900)}")
    print(f"  median: {statistics.median(delays_open):.0f}s  max: {max(delays_open):.0f}s")

# slippage stats (fill vs trigger_price)
slips = [sw['slippage_pips'] for sw in sweeps.values() if 'slippage_pips' in sw]
print(f"\n=== Slippage: fill price vs trigger_price (pips, positive=favorable) n={len(slips)} ===")
if slips:
    print(f"  median: {statistics.median(slips):.2f}  min: {min(slips):.2f}  max: {max(slips):.2f}")
    print(f"  |slippage|>10pip: {sum(1 for s in slips if abs(s)>10)}")

# outcome split by delay bucket (same-bar vs delayed)
same_bar_outcomes = [sw['outcome'] for sw in sweeps.values() if sw.get('reclaim_to_open_delay_sec')==0 and 'outcome' in sw]
delayed_outcomes  = [sw['outcome'] for sw in sweeps.values() if sw.get('reclaim_to_open_delay_sec',0)>0 and 'outcome' in sw]
def wr(lst):
    n = len(lst); w = sum(1 for x in lst if x=='TP')
    return f"n={n} WR={100*w/n:.1f}%" if n else "n=0"
print(f"\n=== Outcome by entry-delay bucket ===")
print(f"  same-bar entry (0 delay): {wr(same_bar_outcomes)}")
print(f"  delayed entry (>=1 bar blocked first): {wr(delayed_outcomes)}")

# blocked reasons summary
all_blocked = Counter()
for sw in sweeps.values():
    for r in sw['blocked_reasons']:
        all_blocked[r] += 1
print(f"\n=== Blocked reasons (all attempts, may be >1 per sweep) ===")
for k, v in all_blocked.items():
    print(f"  {k}: {v}")

# compare cohort vs shadow run4
shadow_rows = json.load(open(r"C:\Users\User\.claude\jobs\703d44b4\tmp\shadow4_dataset.json"))
shadow_by_key = {}
for r in shadow_rows:
    key = (r['level_id'], r['side'])
    shadow_by_key[key] = r

print(f"\n=== Sweep cohort comparison (run5 real ARMED vs run4 shadow SWEEP) ===")
real_keys = set((sw['level_id'], sw['side']) for sw in sweeps.values())
shadow_keys = set(shadow_by_key.keys())
print(f"  real ARMED: {len(real_keys)}  shadow SWEEP: {len(shadow_keys)}")
print(f"  identical level_id+side sets: {real_keys == shadow_keys}")
only_real = real_keys - shadow_keys
only_shadow = shadow_keys - real_keys
print(f"  only in real: {len(only_real)}  only in shadow: {len(only_shadow)}")
if only_real: print(f"    {list(only_real)[:10]}")
if only_shadow: print(f"    {list(only_shadow)[:10]}")

# reclaim availability comparison
real_reclaim_keys = set((sw['level_id'], sw['side']) for sw in sweeps.values() if sw.get('reclaim_time'))
shadow_reclaim_keys = set(k for k,r in shadow_by_key.items() if r['reclaimed_trigger'])
print(f"\n=== Reclaim availability comparison ===")
print(f"  real reclaim available: {len(real_reclaim_keys)}  shadow reclaim available: {len(shadow_reclaim_keys)}")
print(f"  identical sets: {real_reclaim_keys == shadow_reclaim_keys}")
diff1 = real_reclaim_keys - shadow_reclaim_keys
diff2 = shadow_reclaim_keys - real_reclaim_keys
print(f"  reclaim in real but NOT shadow: {len(diff1)} {list(diff1)[:5]}")
print(f"  reclaim in shadow but NOT real: {len(diff2)} {list(diff2)[:5]}")

# entry price/time comparison for matched reclaim events
print(f"\n=== 15 esempi (level_id, side): shadow trigger vs real trigger, shadow reclaim vs real reclaim ===")
common = list(real_reclaim_keys & shadow_reclaim_keys)[:15]
for key in common:
    lid, side = key
    sw = next(s for s in sweeps.values() if s['level_id']==lid and s['side']==side)
    shr = shadow_by_key[key]
    print(f"  level_id={lid} side={side}: real_trigger={sw['trigger_price']:.5f} shadow_trigger={shr['trigger_price']:.5f} "
          f"real_reclaim_delay={sw.get('reclaim_delay_sec')}s shadow_reclaim_delay={shr['time_to_reclaim_sec']}s "
          f"real_opened={sw['opened']} real_outcome={sw.get('outcome')} shadow_outcome={shr['outcome']}")

with open(r"C:\Users\User\.claude\jobs\703d44b4\tmp\run5_dataset.json", "w") as f:
    out = []
    for sid, sw in sorted(sweeps.items()):
        row = dict(sw)
        for k in ('armed_time','reclaim_time','open_time','abandoned_time'):
            if row.get(k): row[k] = row[k].isoformat()
        out.append(row)
    json.dump(out, f, indent=1, default=str)
print("\nSaved run5_dataset.json")
