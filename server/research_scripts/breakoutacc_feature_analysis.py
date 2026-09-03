import csv, json, statistics, bisect
from datetime import datetime, timedelta

with open('_tmp_breakoutacc_trades.json') as f:
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

def idx_before(dt):
    return bisect.bisect_right(bar_times, dt) - 1

for t in trades:
    i1 = idx_before(t['entry_time'] - timedelta(minutes=1))   # bar1 = shift1, the breakout confirmation bar
    i2 = i1 - 1
    if i1 < 25 or i1 >= len(bars):
        t['_valid'] = False; continue
    # replicate the strategy's own range: highest/lowest of n=20 bars, shift 3..22 (iHighest with start shift 3, count n)
    window = bars[i1-22:i1-2]   # bars shift3..22 relative to entry check (approx, off-by-a-bit acceptable for a feature scan)
    if len(window) < 15:
        t['_valid'] = False; continue
    range_hi = max(w['h'] for w in window)
    range_lo = min(w['l'] for w in window)
    c1 = bars[i1]['c']
    rng = range_hi - range_lo
    if rng <= 0:
        t['_valid'] = False; continue
    if t['dir'] == 1:
        accept_strength = (c1 - range_hi) / rng
    else:
        accept_strength = (range_lo - c1) / rng
    t['accept_strength'] = accept_strength
    # ATR proxy
    atrwin = bars[max(0,i1-14):i1]
    atr = statistics.mean([w['h']-w['l'] for w in atrwin]) if atrwin else 0
    t['accept_strength_atr'] = ((c1-range_hi) if t['dir']==1 else (range_lo-c1))/atr if atr>0 else 0
    # momentum before breakout (8 bars)
    prior = bars[max(0,i1-8):i1]
    up_count = sum(1 for w in prior if w['c']>w['o'])
    t['prior_up_frac'] = up_count/len(prior) if prior else 0.5
    t['hour'] = t['entry_time'].hour
    t['range_width_atr'] = rng/atr if atr>0 else 0
    t['_valid'] = True

valid = [t for t in trades if t.get('_valid')]
print(f'validi: {len(valid)}/{len(trades)}')
wins = [t for t in valid if t['pnl']>0]
losses = [t for t in valid if t['pnl']<=0]
print(f'win rate: {len(wins)}/{len(valid)} = {len(wins)/len(valid)*100:.1f}%')

def compare(key,label):
    wv=[t[key] for t in wins]; lv=[t[key] for t in losses]
    print(f'\n--- {label} ---')
    print(f'  vincenti: media={statistics.mean(wv):.3f} mediana={statistics.median(wv):.3f}')
    print(f'  perdenti: media={statistics.mean(lv):.3f} mediana={statistics.median(lv):.3f}')

compare('accept_strength', 'Forza accettazione (frazione del range)')
compare('accept_strength_atr', 'Forza accettazione (in ATR)')
compare('prior_up_frac', 'Frazione barre rialziste nelle 8 precedenti')
compare('range_width_atr', 'Ampiezza range 20 barre (in ATR)')

def wr(g):
    if not g: return (0,0)
    return (sum(1 for t in g if t['pnl']>0), len(g))

strong = [t for t in valid if t['accept_strength_atr'] > statistics.median([x['accept_strength_atr'] for x in valid])]
weak = [t for t in valid if t not in strong]
w1,n1 = wr(strong); w2,n2 = wr(weak)
print(f'\n=== Accettazione sopra/sotto mediana ===')
print(f'  forte: {w1}/{n1} = {w1/n1*100:.0f}%' if n1 else '')
print(f'  debole: {w2}/{n2} = {w2/n2*100:.0f}%' if n2 else '')

from collections import defaultdict
byhour = defaultdict(list)
for t in valid: byhour[t['hour']].append(t)
print('\n=== Per ora ===')
for h in sorted(byhour):
    g = byhour[h]
    w = sum(1 for t in g if t['pnl']>0)
    if len(g)>=5:
        print(f'  ora {h:02d}: {w}/{len(g)} = {w/len(g)*100:.0f}%  pnl_sum={sum(t["pnl"] for t in g):.2f}')

wide = [t for t in valid if t['range_width_atr'] > statistics.median([x['range_width_atr'] for x in valid])]
narrow = [t for t in valid if t not in wide]
w1,n1 = wr(wide); w2,n2 = wr(narrow)
print(f'\n=== Range largo vs stretto (mediana) ===')
print(f'  range largo: {w1}/{n1} = {w1/n1*100:.0f}%' if n1 else '')
print(f'  range stretto: {w2}/{n2} = {w2/n2*100:.0f}%' if n2 else '')
