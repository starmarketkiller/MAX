#!/usr/bin/env python3
"""25/08 - seguito a amd_cont_ldn_reversal_live_signal_25-08.py: entrambe
le config live (AMD_CONT M30, LDN_REVERSAL M15) sotto pareggio. Prima di
disattivare, scan su TF alternativi (M15/H1 per AMD_CONT, M30/H1 per
LDN_REVERSAL) per escludere che sia solo un problema di timeframe, come
gia' fatto per TURTLE_SOUP/STRUCT_REACT/EMA_PULLBACK. Riusa le stesse
strutture (fase AMD M15, CHOCH M15, sweep M15) - allinea al TF di test
via nearest-M15-bar-<=-time (bisect), stessa semplificazione dichiarata
nello script precedente."""
import sys, os, bisect
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import backtest as bt
import importlib.util
spec = importlib.util.spec_from_file_location(
    "amd_base", os.path.join(os.path.dirname(os.path.abspath(__file__)), "amd_cont_ldn_reversal_live_signal_25-08.py"))
amd_base = importlib.util.module_from_spec(spec)
spec.loader.exec_module(amd_base)


def main():
    candles15, _ = bt._fetch_real("XAUUSD", "15m", 130000)
    ind15 = bt._prep(candles15)
    atr15 = ind15["atr"]
    h15 = [c["high"] for c in candles15]
    l15 = [c["low"] for c in candles15]
    c15 = [c["close"] for c in candles15]
    t15 = [c["time"] for c in candles15]
    n15 = len(candles15)

    candlesD1, _ = bt._fetch_real("XAUUSD", "1d", 4000)
    d1_times = [c["time"] for c in candlesD1]
    d1_high = [c["high"] for c in candlesD1]
    d1_low = [c["low"] for c in candlesD1]

    def pdh_pdl(t):
        j = bisect.bisect_right(d1_times, t) - 1
        if j < 1:
            return None, None
        return d1_high[j - 1], d1_low[j - 1]

    asian_hi, asian_lo = {}, {}
    for i in range(n15):
        d, h = amd_base.hm(t15[i])
        if amd_base.ASIAN_START_H <= h < amd_base.ASIAN_END_H:
            asian_hi[d] = max(asian_hi.get(d, -1e18), h15[i])
            asian_lo[d] = min(asian_lo.get(d, 1e18), l15[i])

    amd_phase = [None] * n15
    amd_dir = [None] * n15
    a_hi = [0.0] * n15
    a_lo = [0.0] * n15
    choch_up = [False] * n15
    choch_down = [False] * n15
    swept_ah = [False] * n15
    swept_pdh = [False] * n15
    swept_eqh = [False] * n15
    swept_al = [False] * n15
    swept_pdl = [False] * n15
    swept_eql = [False] * n15
    refHigh = [0.0] * n15
    refLow = [0.0] * n15

    phase, manip_dir, cur_day, trend = None, 0, None, 0
    WARMUP = 100
    for i in range(WARMUP, n15):
        d, h = amd_base.hm(t15[i])
        if d != cur_day:
            cur_day, phase, manip_dir = d, "ACC", 0
        hi, lo = asian_hi.get(d), asian_lo.get(d)
        if hi is None or lo is None or h < amd_base.ASIAN_END_H:
            continue
        a_hi[i], a_lo[i] = hi, lo
        c1 = c15[i]
        beyondHigh, beyondLow = c1 > hi, c1 < lo
        if phase == "ACC":
            if beyondHigh: phase, manip_dir = "CONT", 1
            elif beyondLow: phase, manip_dir = "CONT", -1
        elif phase == "CONT":
            stillBeyond = beyondHigh if manip_dir == 1 else beyondLow
            if not stillBeyond: phase = "REV"
        elif phase == "REV":
            oppBeyond = beyondLow if manip_dir == 1 else beyondHigh
            if oppBeyond: manip_dir, phase = -manip_dir, "CONT"
        amd_phase[i], amd_dir[i] = phase, manip_dir

        sH, sL = amd_base.last_two_swings(h15, l15, i, amd_base.SWING_WING, 60)
        lastSwingHigh = sH[0] if len(sH) >= 1 else 0
        lastSwingLow = sL[0] if len(sL) >= 1 else 0
        trendBefore = trend
        if len(sH) >= 2 and len(sL) >= 2:
            hh, hl = sH[0] > sH[1], sL[0] > sL[1]
            lh, ll = sH[0] < sH[1], sL[0] < sL[1]
            if hh and hl: trend = 1
            elif lh and ll: trend = -1
        if lastSwingHigh > 0 and c1 > lastSwingHigh and trendBefore == -1: choch_up[i] = True
        if lastSwingLow > 0 and c1 < lastSwingLow and trendBefore == 1: choch_down[i] = True

        a = atr15[i]
        if not a:
            continue
        tol = a * 0.2
        eqH = amd_base.find_equal_high(h15, i, amd_base.SWING_WING, tol)
        eqL = amd_base.find_equal_low(l15, i, amd_base.SWING_WING, tol)
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

    def nearest_m15(t, times15):
        j = bisect.bisect_right(times15, t) - 1
        return j if j >= 0 else None

    def test_amd_cont(tf_label, candlesX, sess_lo=7, sess_hi=20, max_hold=800):
        indX = bt._prep(candlesX)
        atrX = indX["atr"]
        oX = [c["open"] for c in candlesX]
        hX = [c["high"] for c in candlesX]
        lX = [c["low"] for c in candlesX]
        cX = [c["close"] for c in candlesX]
        tX = [c["time"] for c in candlesX]
        out = []
        for j in range(WARMUP, len(candlesX) - 2):
            d, hgmt = amd_base.hm(tX[j])
            if not (sess_lo <= hgmt < sess_hi):
                continue
            i15 = nearest_m15(tX[j], t15)
            if i15 is None or amd_phase[i15] != "CONT":
                continue
            hi, lo = a_hi[i15], a_lo[i15]
            if hi <= 0 or lo <= 0:
                continue
            a = atrX[j]
            if not a:
                continue
            c1, l1v, h1v = cX[j], lX[j], hX[j]
            mid = (hi + lo) * 0.5
            sig, sl = 0, None
            if amd_dir[i15] == 1 and c1 > hi and l1v <= hi + a * 0.6:
                sig, sl = 1, min(hi - 0.3 * a, mid)
            elif amd_dir[i15] == -1 and c1 < lo and h1v >= lo - a * 0.6:
                sig, sl = -1, max(lo + 0.3 * a, mid)
            if sig == 0:
                continue
            entry_i = j + 1
            entry = candlesX[entry_i]["open"]
            rd = abs(entry - sl)
            if rd <= 0:
                continue
            tp = entry + sig * 2.4 * rd
            exit_r = amd_base.walk_exit(candlesX, entry_i, entry, sl, tp, sig, rd, max_hold)
            if exit_r is None:
                continue
            out.append({"entry": entry, "risk_dist": rd, "raw_r": exit_r, "dir": sig})
        print(f"--- AMD_CONT su {tf_label} ---", flush=True)
        print(amd_base.fmt("simmetrica", out), flush=True)
        print(amd_base.fmt("BUY-only", [t for t in out if t["dir"] == 1]), flush=True)
        print(amd_base.fmt("SELL-only", [t for t in out if t["dir"] == -1]), flush=True)

    def test_ldn_reversal(tf_label, candlesX, sess_lo=7, sess_hi=15, max_hold=1600):
        indX = bt._prep(candlesX)
        atrX = indX["atr"]
        tX = [c["time"] for c in candlesX]
        cX = [c["close"] for c in candlesX]
        out = []
        for j in range(WARMUP, len(candlesX) - 2):
            d, hgmt = amd_base.hm(tX[j])
            if not (sess_lo <= hgmt < sess_hi):
                continue
            i15 = nearest_m15(tX[j], t15)
            if i15 is None:
                continue
            a = atrX[j]
            if not a:
                continue
            c1 = cX[j]
            sig, sl = 0, None
            if (swept_ah[i15] or swept_pdh[i15] or swept_eqh[i15]) and c1 < refHigh[i15] and choch_down[i15]:
                sig, sl = -1, refHigh[i15] + 0.5 * a
            elif (swept_al[i15] or swept_pdl[i15] or swept_eql[i15]) and c1 > refLow[i15] and choch_up[i15]:
                sig, sl = 1, refLow[i15] - 0.5 * a
            if sig == 0:
                continue
            entry_i = j + 1
            entry = candlesX[entry_i]["open"]
            rd = abs(entry - sl)
            if rd <= 0:
                continue
            if sig == -1:
                tgt = a_lo[i15] if a_lo[i15] > 0 else (entry - 2.5 * (sl - entry))
                tp = min(tgt, entry - 2.0 * (sl - entry))
            else:
                tgt = a_hi[i15] if a_hi[i15] > 0 else (entry + 2.5 * (entry - sl))
                tp = max(tgt, entry + 2.0 * (entry - sl))
            exit_r = amd_base.walk_exit(candlesX, entry_i, entry, sl, tp, sig, rd, max_hold)
            if exit_r is None:
                continue
            out.append({"entry": entry, "risk_dist": rd, "raw_r": exit_r, "dir": sig})
        print(f"--- LDN_REVERSAL su {tf_label} ---", flush=True)
        print(amd_base.fmt("simmetrica", out), flush=True)
        print(amd_base.fmt("BUY-only", [t for t in out if t["dir"] == 1]), flush=True)
        print(amd_base.fmt("SELL-only", [t for t in out if t["dir"] == -1]), flush=True)

    candlesH1, _ = bt._fetch_real("XAUUSD", "1h", 110000)
    print("### AMD_CONT alternate TF ###", flush=True)
    test_amd_cont("M15 (=fase nativa)", candles15)
    test_amd_cont("H1", candlesH1)

    candles30, _ = bt._fetch_real("XAUUSD", "30m", 70000)
    print("\n### LDN_REVERSAL alternate TF ###", flush=True)
    test_ldn_reversal("M30", candles30)
    test_ldn_reversal("H1", candlesH1)


if __name__ == "__main__":
    main()
