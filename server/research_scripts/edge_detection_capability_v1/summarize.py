import json,sys
R=json.load(open(sys.argv[1])); print('META',R['meta'])
S=R['signal']
def f(x): return '  -  ' if x is None else f'{x:5.2f}'
print('\n== SIGNAL: rejection rate (M1 M2 M3 M4) | bias | M1 coverage | est|sig  (cost=0)')
for g in ('G_U','G_C','G_B'):
    for c in sorted([c for c in S if c['gen']==g and c['cost_atr']==0], key=lambda c:(c['delta_atr'],c['n'])):
        rr=c['rejection_rate']
        print(f"{g} d={c['delta_atr']:<4} n={c['n']:<4} "+' '.join(f(rr[m]) for m in ('M1','M2','M3','M4'))+(f" UNC={rr['M_UNC']:.2f}" if 'M_UNC' in rr else '')+f" | bias {c['bias']:+.3f} sd {c['sd_estimate']:.2f} | cov {c['m1_ci_coverage']:.2f} | est|sig {f(c['mean_estimate_if_M1_significant'])}")
print('\n== SIGNAL cost cells (M1 M2 M3 M4)')
for c in [c for c in S if c['cost_atr']>0]:
    rr=c['rejection_rate']; print(f"{c['gen']} n={c['n']} d={c['delta_atr']} cost={c['cost_atr']} true={c['true_Ed']:+.3f} "+' '.join(f(rr[m]) for m in ('M1','M2','M3','M4')))
print('\n== TRADE: power (lower CI>0) | coverage | est|sig')
for c in R['trade']:
    print(f"{c['dist']:<12} n={c['n']:<4} dR={c['deltaR']:<4} cR={c['costR']:<5} power {c['power_lower_ci_gt_0']:.2f} cov {c['ci_coverage']:.2f} est|sig {f(c['mean_estimate_if_significant'])}")
print('\n== SCREEN -> CONFIRM')
for c in R['screen_confirm']: print(c)
