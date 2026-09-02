import csv, json, statistics, bisect
from datetime import datetime, timedelta

with open('_tmp_barupdn_trades.json') as f:
    trades = json.load(f)
for t in trades:
    t['entry_time'] = datetime.fromisoformat(t['entry_time'])
    t['exit_time'] = datetime.fromisoformat(t['exit_time'])

bars = []
with open('nxs_m15_gold_extended.csv', encoding='utf-8') as f:
    r = csv.reader(f); next(r)
    for row in r:
        if len(row) < 5: continue
        dt = datetime.strptime(row[0].strip(), '%Y.%m.%d %H:%M')
        bars.append({'t': dt, 'o': float(row[1]), 'h': float(row[2]), 'l': float(row[3]), 'c': float(row[4])})
bar_times = [b['t'] for b in bars]

def idx_at_or_before(dt):
    i = bisect.bisect_right(bar_times, dt) - 1
    return i

for t in trades:
    # entry bar index = the M15 bar whose close time == entry_time (signal fires at open of the bar after the 2-bar pattern)
    i1 = idx_at_or_before(t['entry_time'])   # bar 1 = signal bar (just closed), i.e. index for entry bar - 1
    # bars used by the strategy: c1 (shift1) = bar at i1-? Actually entry_time == open time of the NEW bar (bar 0 at signal time).
    # The pattern bars are the ones closed BEFORE entry: shift1 = bar closing right at entry_time, shift2 = one before that.
    # bars list is indexed by OPEN time; bar closing at entry_time has open time = entry_time - 15min.
    i_sig1 = idx_at_or_before(t['entry_time'] - timedelta(minutes=1))   # bar1 (o1,c1) - the most recently closed bar
    i_sig2 = i_sig1 - 1                                                  # bar2 (c2)
    if i_sig1 < 5 or i_sig1 >= len(bars):
        t['_valid'] = False
        continue
    b1 = bars[i_sig1]; b2 = bars[i_sig2]
    body1 = abs(b1['c'] - b1['o'])
    range1 = b1['h'] - b1['l']
    # ATR proxy: avg range of last 14 bars before signal bar
    window = bars[max(0,i_sig1-14):i_sig1]
    atr = statistics.mean([w['h']-w['l'] for w in window]) if window else 0
    t['body1_atr'] = body1/atr if atr>0 else 0
    t['range1_atr'] = range1/atr if atr>0 else 0
    # momentum: net direction of prior 6 bars before bar1 (not incl bar1/bar2)
    prior = bars[max(0,i_sig1-8):i_sig1-2]
    up_count = sum(1 for w in prior if w['c']>w['o'])
    t['prior_up_frac'] = up_count/len(prior) if prior else 0.5
    # trend context: close vs EMA20-ish (sma of last 20 bar closes) at signal time
    win20 = bars[max(0,i_sig1-20):i_sig1]
    sma20 = statistics.mean([w['c'] for w in win20]) if win20 else b1['c']
    t['above_sma20'] = 1 if b1['c'] > sma20 else 0
    t['dist_sma20_atr'] = (b1['c']-sma20)/atr if atr>0 else 0
    # hour of day (signal time = entry bar open)
    t['hour'] = t['entry_time'].hour
    t['_valid'] = True

valid = [t for t in trades if t.get('_valid')]
print(f'valid trades: {len(valid)} / {len(trades)}')

wins = [t for t in valid if t['pnl']>0]
losses = [t for t in valid if t['pnl']<=0]
print(f'win rate: {len(wins)}/{len(valid)} = {len(wins)/len(valid)*100:.1f}%')

def compare(key, label, buckets=None):
    wv = [t[key] for t in wins]
    lv = [t[key] for t in losses]
    print(f'\n--- {label} ---')
    print(f'  vincenti: media={statistics.mean(wv):.3f} mediana={statistics.median(wv):.3f}')
    print(f'  perdenti: media={statistics.mean(lv):.3f} mediana={statistics.median(lv):.3f}')

compare('body1_atr', 'Corpo candela segnale / ATR')
compare('range1_atr', 'Range candela segnale / ATR')
compare('prior_up_frac', 'Frazione barre rialziste nelle 6 precedenti')
compare('dist_sma20_atr', 'Distanza da SMA20 (in ATR)')

# direction-specific: for buy, dist_sma20 positive (above) = trend aligned; for sell, negative = aligned
for t in valid:
    t['trend_aligned'] = (t['dir']==1 and t['dist_sma20_atr']>0) or (t['dir']==-1 and t['dist_sma20_atr']<0)

aligned = [t for t in valid if t['trend_aligned']]
contrary = [t for t in valid if not t['trend_aligned']]
def wr(group):
    if not group: return (0,0)
    w = sum(1 for t in group if t['pnl']>0)
    return (w, len(group))
wa,na = wr(aligned); wc,nc = wr(contrary)
print(f'\n=== Allineato al trend (SMA20) ===')
print(f'  allineato: {wa}/{na} = {wa/na*100:.1f}% win rate' if na else '  n/a')
print(f'  contrario: {wc}/{nc} = {wc/nc*100:.1f}% win rate' if nc else '  n/a')

# body size buckets
big_body = [t for t in valid if t['body1_atr'] > 0.5]
small_body = [t for t in valid if t['body1_atr'] <= 0.5]
wb,nb = wr(big_body); ws,ns = wr(small_body)
print(f'\n=== Corpo candela segnale ===')
print(f'  corpo >0.5xATR: {wb}/{nb} = {wb/nb*100:.1f}%' if nb else '  n/a')
print(f'  corpo <=0.5xATR: {ws}/{ns} = {ws/ns*100:.1f}%' if ns else '  n/a')

# hour of day
from collections import defaultdict
byhour = defaultdict(list)
for t in valid: byhour[t['hour']].append(t)
print('\n=== Per ora (UTC broker) ===')
for h in sorted(byhour):
    g = byhour[h]
    w = sum(1 for t in g if t['pnl']>0)
    if len(g)>=5:
        print(f'  ora {h:02d}: {w}/{len(g)} = {w/len(g)*100:.0f}%  pnl_sum={sum(t["pnl"] for t in g):.2f}')
