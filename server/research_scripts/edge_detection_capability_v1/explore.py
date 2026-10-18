import sys, os, numpy as np, time
W=sys.argv[1]; P7=os.path.join(W,'server/research_scripts/phase7')
for d in ['phase7_27','phase7_21','phase7_25','engine']: sys.path.insert(0,os.path.join(P7,d))
from nxs_gold_d1_loader import load_d1
from nxs_regime_classifier import build_regime_table
import nxs_breakoutacc_dataset_loader as BA, nxs_liq_sweep_edge_dataset_loader as LS
df=load_d1(); rt=build_regime_table()
print('bars',len(df),df.time.min(),df.time.max())
c=df.close.values; atr=rt.atr14.values
f10=(np.roll(c,-10)-c); f10[-10:]=np.nan
z=f10/atr
print('ATR14 median %.1f p10 %.1f p90 %.1f'%tuple(np.nanpercentile(atr,[50,10,90])))
print('h10 fwd ret / ATR: mean %.3f sd %.3f'%(np.nanmean(z),np.nanstd(z)))
print('regime counts',rt.sma50_slope.value_counts().to_dict())
for name,mod,load in [('BREAKOUT_ACC',BA,BA.load_opened_events),('LIQ_SWEEP',LS,LS.load_closed_events)]:
    r=np.array([x for x in (mod.net_pnl_in_r(e) for e in load()) if x is not None])
    risk=np.array([mod.risk_r(e) for e in load()])
    print(name,'n',len(r),'meanR %.3f sdR %.3f skew %.2f'%(r.mean(),r.std(ddof=1),((r-r.mean())**3).mean()/r.std()**3),'min %.2f max %.2f'%(r.min(),r.max()),'risk$ median %.1f'%np.median(risk))
