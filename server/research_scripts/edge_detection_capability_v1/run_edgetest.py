"""NEXUS_P0_EDGE_DETECTION_CAPABILITY_V1 runner (scratchpad, read-only on repo).
Usage: python3 run_edgetest.py <worktree> <protocol.json> <out.json>"""
import sys, os, json, zlib, time
import numpy as np
from multiprocessing import Pool

W, PROTO, OUT = sys.argv[1:4]
P7 = os.path.join(W, 'server/research_scripts/phase7')
for d in ['phase7_27', 'phase7_21', 'phase7_25', 'engine']:
    sys.path.insert(0, os.path.join(P7, d))
from nxs_gold_d1_loader import load_d1
from nxs_regime_classifier import build_regime_table
import nxs_breakoutacc_dataset_loader as BA
import nxs_liq_sweep_edge_dataset_loader as LS
from matched_pair_permutation_test import block_sign_flip_permutation_p
from dependence_aware_mean_tests import studentized_block_bootstrap_p, hac_newey_west_p
from multiple_testing_v2 import benjamini_hochberg

P = json.load(open(PROTO))
ALPHA = P['signal_layer']['alpha']
BASE = 90000

def seed(key):
    return (BASE + zlib.crc32(key.encode())) % (2 ** 31)

# ---------- data (read-only) ----------
df = load_d1(); rt = build_regime_table()
c = df['close'].values; atr = rt['atr14'].values
Y = np.full(len(c), np.nan); Y[:-10] = (c[10:] - c[:-10]) / atr[:-10]
ok = (rt['sma50_slope'].values != 'UNKNOWN') & (rt['vol_tercile'].values != 'UNKNOWN') & ~np.isnan(Y)
ELIG = np.where(ok)[0]
KEY = np.array([f"{a}|{b}" for a, b in zip(rt['sma50_slope'].values, rt['vol_tercile'].values)])
BUCKET = {k: ELIG[KEY[ELIG] == k] for k in set(KEY[ELIG])}
UP = ELIG[rt['sma50_slope'].values[ELIG] == 'UP']
POP_MEAN = float(Y[ELIG].mean())
R_BA = np.array([x for x in (BA.net_pnl_in_r(e) for e in BA.load_opened_events()) if x is not None])
R_LS = np.array([x for x in (LS.net_pnl_in_r(e) for e in LS.load_closed_events()) if x is not None])
DIST = {'BREAKOUT_ACC': R_BA - R_BA.mean(), 'LIQ_SWEEP': R_LS - R_LS.mean()}

def iid_boot(x, rng, B=2000):
    n = len(x)
    m = x[rng.integers(0, n, size=(B, n))].mean(1)
    lo, hi = np.quantile(m, [0.025, 0.975])
    p = min(1.0, 2 * min((m <= 0).mean(), (m >= 0).mean()))
    return lo, hi, p

def gen_events(g, n, rng):
    if g == 'G_U':
        return np.sort(rng.choice(ELIG, n, replace=False))
    if g == 'G_B':
        return np.sort(rng.choice(UP, n, replace=False))
    if g == 'G_C':
        okset = set(ELIG.tolist()); ev = []
        while len(ev) < n:
            ctr = int(rng.choice(ELIG))
            cl = [ctr + k for k in (0, 2, 4, 6) if ctr + k in okset]
            ev.extend(cl)
        return np.sort(np.array(ev[:n]))

def matched(ev, rng):
    out = []
    for i in ev:
        pool = BUCKET[KEY[i]]
        j = i
        while j == i:
            j = int(pool[rng.integers(0, len(pool))])
        out.append(j)
    return np.array(out)

def signal_cell(args):
    g, n, delta, cost, reps = args
    key = f"S|{g}|{n}|{delta}|{cost}"
    rng = np.random.default_rng(seed(key))
    rej = {m: 0 for m in ('M1', 'M2', 'M3', 'M4', 'M_UNC')}
    est, cover, sig_est = [], 0, []
    true = delta - cost
    for r in range(reps):
        ev = gen_events(g, n, rng)
        ctl = matched(ev, rng)
        d = (Y[ev] + delta - cost) - Y[ctl]
        lo, hi, _ = iid_boot(d, rng)
        s1 = not (lo <= 0 <= hi)
        rej['M1'] += s1; cover += (lo <= true <= hi); est.append(d.mean())
        if s1: sig_est.append(d.mean())
        ss = int(rng.integers(0, 2 ** 31))
        rej['M2'] += block_sign_flip_permutation_p(d, n_boot=999, seed=ss)['p_value'] < ALPHA
        rej['M3'] += studentized_block_bootstrap_p(d, n_boot=999, seed=ss)['p_value'] < ALPHA
        rej['M4'] += hac_newey_west_p(d)['p_value'] < ALPHA
        if g == 'G_B':
            lo2, hi2, _ = iid_boot(Y[ev] - POP_MEAN, rng)
            rej['M_UNC'] += not (lo2 <= 0 <= hi2)
    est = np.array(est)
    out = {'layer': 'signal', 'gen': g, 'n': n, 'delta_atr': delta, 'cost_atr': cost, 'reps': reps,
           'true_Ed': true, 'rejection_rate': {k: v / reps for k, v in rej.items() if not (k == 'M_UNC' and g != 'G_B')},
           'mean_estimate': float(est.mean()), 'bias': float(est.mean() - true),
           'rmse': float(np.sqrt(((est - true) ** 2).mean())), 'sd_estimate': float(est.std()),
           'm1_ci_coverage': cover / reps,
           'mean_estimate_if_M1_significant': float(np.mean(sig_est)) if sig_est else None}
    return out

def trade_cell(args):
    dist, n, dR, cR, reps = args
    rng = np.random.default_rng(seed(f"T|{dist}|{n}|{dR}|{cR}"))
    base = DIST[dist]; true = dR - cR
    win, cover, est, sig = 0, 0, [], []
    for r in range(reps):
        x = base[rng.integers(0, len(base), n)] + dR - cR
        lo, hi, _ = iid_boot(x, rng)
        w = lo > 0; win += w; cover += lo <= true <= hi; est.append(x.mean())
        if w: sig.append(x.mean())
    est = np.array(est)
    return {'layer': 'trade', 'dist': dist, 'n': n, 'deltaR': dR, 'costR': cR, 'reps': reps,
            'true_ER': true, 'power_lower_ci_gt_0': win / reps, 'ci_coverage': cover / reps,
            'bias': float(est.mean() - true), 'sd_estimate': float(est.std()),
            'mean_estimate_if_significant': float(np.mean(sig)) if sig else None}

def sc_cell(args):
    m_true, n, reps = args
    S = P['screening_vs_confirmation']; K = S['family_size']; dT = S['true_deltaR']
    rng = np.random.default_rng(seed(f"SC|{m_true}|{n}"))
    base = DIST['BREAKOUT_ACC']
    fp_any, n_pos, n_false_pos, tp_screen, tp_confirm, infl, false_confirm = 0, 0, 0, 0, 0, [], 0
    for r in range(reps):
        deltas = np.array([dT] * m_true + [0.0] * (K - m_true))
        pv, means = [], []
        for k in range(K):
            x = base[rng.integers(0, len(base), n)] + deltas[k]
            _, _, p = iid_boot(x, rng); pv.append((k, p)); means.append(x.mean())
        bh = benjamini_hochberg(pv, q=0.10)
        sel = [k for k in range(K) if bh[k]['significant_at_q'] and means[k] > 0]
        falses = [k for k in sel if deltas[k] == 0]
        n_pos += len(sel); n_false_pos += len(falses); fp_any += bool(falses)
        for k in sel:
            if deltas[k] > 0:
                tp_screen += 1; infl.append(means[k] / dT)
            x2 = base[rng.integers(0, len(base), n)] + deltas[k]
            lo, _, _ = iid_boot(x2, rng)
            if lo > 0:
                if deltas[k] > 0: tp_confirm += 1
                else: false_confirm += 1
    return {'layer': 'screen_confirm', 'm_true': m_true, 'n': n, 'reps': reps,
            'P_any_false_positive_screen': fp_any / reps,
            'FDR_screen': (n_false_pos / n_pos) if n_pos else None,
            'mean_positives_per_family': n_pos / reps,
            'true_edge_pass_screen_rate': (tp_screen / (reps * m_true)) if m_true else None,
            'true_edge_pass_both_rate': (tp_confirm / (reps * m_true)) if m_true else None,
            'false_edges_confirmed_per_family': false_confirm / reps,
            'winners_curse_inflation_true_edges': float(np.mean(infl)) if infl else None}

if __name__ == '__main__':
    t0 = time.time()
    SL, TL, SCP = P['signal_layer'], P['trade_layer'], P['screening_vs_confirmation']
    R = SL['reps_per_cell']
    jobs_s = [(g, n, d, 0.0, R) for g in ('G_U', 'G_C') for n in SL['grid']['n'] for d in SL['grid']['delta_atr']]
    jobs_s += [('G_B', n, 0.0, 0.0, R) for n in SL['grid']['n']]
    jobs_s += [(g, n, d, cst, R) for g in ('G_U', 'G_C') for n in (47, 200) for d in (0, 0.25, 0.5) for cst in SL['grid']['cost_atr'][1:]]
    jobs_t = [(ds, n, d, 0.0, TL['reps_per_cell']) for ds in DIST for n in TL['grid']['n'] for d in TL['grid']['deltaR']]
    jobs_t += [('BREAKOUT_ACC', n, d, cr, TL['reps_per_cell']) for n in TL['grid']['n'] for d in TL['grid']['deltaR'] for cr in TL['grid']['costR'][1:]]
    jobs_sc = [(m, n, SCP['reps']) for m in SCP['m_true'] for n in SCP['n_per_strategy']]
    with Pool(4) as pool:
        res_s = pool.map(signal_cell, jobs_s, chunksize=1)
        res_t = pool.map(trade_cell, jobs_t, chunksize=1)
        res_sc = pool.map(sc_cell, jobs_sc, chunksize=1)
    meta = {'protocol_sha256': open(PROTO.replace('.json', '.sha256')).read().split()[0],
            'pop_mean_y_atr': POP_MEAN, 'sd_y_atr': float(Y[ELIG].std()), 'n_eligible_bars': int(len(ELIG)),
            'n_up_bars': int(len(UP)), 'trade_dist_sd': {k: float(v.std(ddof=1)) for k, v in DIST.items()},
            'runtime_s': round(time.time() - t0, 1)}
    json.dump({'meta': meta, 'signal': res_s, 'trade': res_t, 'screen_confirm': res_sc}, open(OUT, 'w'), indent=1)
    print('done', meta)
