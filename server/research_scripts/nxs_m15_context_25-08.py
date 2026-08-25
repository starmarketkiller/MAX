#!/usr/bin/env python3
"""25/08 - modulo condiviso: precalcola sull'M15 (InpTFEntry) tutto cio' da
cui dipendono le strategie institutional/SMC rimaste da verificare
(DISP_REBAL, IFVG, SH_BMS_RTO, SMS_BMS_RTO, RANGE_FADE, WEEKLY_EXP):
CHOCH/BOS di struttura (NXS_Structure.mqh), sweep vs Asia/PDH/PDL/EQH/EQL
(NXS_DetectSweepExt semplificato, no weekly/monthly - vedi nota in
amd_cont_ldn_reversal_live_signal_25-08.py), range Asia per giorno.
Riusa helper gia' verificati da amd_cont_ldn_reversal_live_signal_25-08.py
(pf/fmt/walk_forward/net_series/is_swing_*/find_equal_*/last_two_swings/
walk_exit/hm) via import diretto invece di duplicarli."""
import sys, os, bisect
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import backtest as bt
import importlib.util

_here = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("amd_base", os.path.join(_here, "amd_cont_ldn_reversal_live_signal_25-08.py"))
amd_base = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(amd_base)

pf = amd_base.pf
fmt = amd_base.fmt
walk_forward = amd_base.walk_forward
net_series = amd_base.net_series
is_swing_high = amd_base.is_swing_high
is_swing_low = amd_base.is_swing_low
find_equal_high = amd_base.find_equal_high
find_equal_low = amd_base.find_equal_low
last_two_swings = amd_base.last_two_swings
walk_exit = amd_base.walk_exit
hm = amd_base.hm
SWING_WING = amd_base.SWING_WING
ASIAN_START_H = amd_base.ASIAN_START_H
ASIAN_END_H = amd_base.ASIAN_END_H


def pdh_pdl_lookup(d1_times, d1_high, d1_low):
    def f(t):
        j = bisect.bisect_right(d1_times, t) - 1
        if j < 1:
            return None, None
        return d1_high[j - 1], d1_low[j - 1]
    return f


def build_m15_context(warmup=100):
    """Ritorna un dict con tutte le serie precalcolate sull'M15, indicizzate
    per indice di barra M15 (i = 'shift1'/ultima barra chiusa quando usata
    da un consumer)."""
    candles15, _ = bt._fetch_real("XAUUSD", "15m", 130000)
    candlesD1, _ = bt._fetch_real("XAUUSD", "1d", 4000)
    ind15 = bt._prep(candles15)
    atr15 = ind15["atr"]
    h15 = [c["high"] for c in candles15]
    l15 = [c["low"] for c in candles15]
    c15 = [c["close"] for c in candles15]
    t15 = [c["time"] for c in candles15]
    n15 = len(candles15)

    d1_times = [c["time"] for c in candlesD1]
    d1_high = [c["high"] for c in candlesD1]
    d1_low = [c["low"] for c in candlesD1]
    pdh_pdl = pdh_pdl_lookup(d1_times, d1_high, d1_low)

    asian_hi, asian_lo = {}, {}
    for i in range(n15):
        d, h = hm(t15[i])
        if ASIAN_START_H <= h < ASIAN_END_H:
            asian_hi[d] = max(asian_hi.get(d, -1e18), h15[i])
            asian_lo[d] = min(asian_lo.get(d, 1e18), l15[i])

    a_hi = [0.0] * n15
    a_lo = [0.0] * n15
    choch_up = [False] * n15
    choch_down = [False] * n15
    trend_arr = [0] * n15
    swept_ah = [False] * n15
    swept_pdh = [False] * n15
    swept_eqh = [False] * n15
    swept_al = [False] * n15
    swept_pdl = [False] * n15
    swept_eql = [False] * n15
    refHigh = [0.0] * n15
    refLow = [0.0] * n15
    swept_any = [False] * n15
    swept_dir = [0] * n15   # 1 = buy-side sweep (low swept), -1 = sell-side (high swept)
    swept_level = [0.0] * n15

    trend = 0
    for i in range(warmup, n15):
        d, h = hm(t15[i])
        hi, lo = asian_hi.get(d), asian_lo.get(d)
        if hi is None or lo is None or h < ASIAN_END_H:
            trend_arr[i] = trend
            continue
        a_hi[i], a_lo[i] = hi, lo
        c1 = c15[i]

        sH, sL = last_two_swings(h15, l15, i, SWING_WING, 60)
        lastSwingHigh = sH[0] if len(sH) >= 1 else 0
        lastSwingLow = sL[0] if len(sL) >= 1 else 0
        trendBefore = trend
        if len(sH) >= 2 and len(sL) >= 2:
            hh, hl = sH[0] > sH[1], sL[0] > sL[1]
            lh, ll = sH[0] < sH[1], sL[0] < sL[1]
            if hh and hl:
                trend = 1
            elif lh and ll:
                trend = -1
        if lastSwingHigh > 0 and c1 > lastSwingHigh and trendBefore == -1:
            choch_up[i] = True
        if lastSwingLow > 0 and c1 < lastSwingLow and trendBefore == 1:
            choch_down[i] = True
        trend_arr[i] = trend

        a = atr15[i]
        if not a:
            continue
        tol = a * 0.2
        eqH = find_equal_high(h15, i, SWING_WING, tol)
        eqL = find_equal_low(l15, i, SWING_WING, tol)
        pdh, pdl = pdh_pdl(t15[i])
        h1v, l1v = h15[i], l15[i]
        if h1v > hi and c1 < hi: swept_ah[i] = True
        if l1v < lo and c1 > lo: swept_al[i] = True
        if pdh is not None and h1v > pdh and c1 < pdh: swept_pdh[i] = True
        if pdl is not None and l1v < pdl and c1 > pdl: swept_pdl[i] = True
        if eqH > 0 and h1v > eqH and c1 < eqH: swept_eqh[i] = True
        if eqL > 0 and l1v < eqL and c1 > eqL: swept_eql[i] = True
        refHigh[i] = pdh if swept_pdh[i] else (hi if swept_ah[i] else (eqH if swept_eqh[i] else max(pdh or 0, hi)))
        refLow[i] = pdl if swept_pdl[i] else (lo if swept_al[i] else (eqL if swept_eql[i] else min(pdl or 1e18, lo)))

        # priorita' Asia -> daily -> equal (weekly/monthly ignorati, nota
        # dichiarata in amd_cont_ldn_reversal_live_signal_25-08.py punto 3)
        if swept_ah[i]:
            swept_any[i], swept_dir[i], swept_level[i] = True, -1, hi
        if swept_pdh[i]:
            swept_any[i], swept_dir[i], swept_level[i] = True, -1, pdh
        if swept_al[i]:
            swept_any[i], swept_dir[i], swept_level[i] = True, 1, lo
        if swept_pdl[i]:
            swept_any[i], swept_dir[i], swept_level[i] = True, 1, pdl
        if not swept_any[i] and swept_eqh[i]:
            swept_any[i], swept_dir[i], swept_level[i] = True, -1, eqH
        if not swept_any[i] and swept_eql[i]:
            swept_any[i], swept_dir[i], swept_level[i] = True, 1, eqL

    t15_idx_by_time = {t15[i]: i for i in range(n15)}

    return {
        "candles15": candles15, "t15": t15, "h15": h15, "l15": l15, "c15": c15,
        "atr15": atr15, "n15": n15,
        "a_hi": a_hi, "a_lo": a_lo,
        "choch_up": choch_up, "choch_down": choch_down, "trend": trend_arr,
        "swept_ah": swept_ah, "swept_pdh": swept_pdh, "swept_eqh": swept_eqh,
        "swept_al": swept_al, "swept_pdl": swept_pdl, "swept_eql": swept_eql,
        "refHigh": refHigh, "refLow": refLow,
        "swept_any": swept_any, "swept_dir": swept_dir, "swept_level": swept_level,
        "t15_idx_by_time": t15_idx_by_time,
        "pdh_pdl": pdh_pdl,
        "candlesD1": candlesD1, "d1_times": d1_times, "d1_high": d1_high, "d1_low": d1_low,
        "asian_hi_by_date": asian_hi, "asian_lo_by_date": asian_lo,
    }


def nearest_idx(t, times_sorted):
    j = bisect.bisect_right(times_sorted, t) - 1
    return j if j >= 0 else None
