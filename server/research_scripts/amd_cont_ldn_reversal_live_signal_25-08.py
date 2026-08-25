#!/usr/bin/env python3
"""
25/08 - ricerca da zero (non porting) sui veri segnali LIVE di AMD_CONT
(NXS_Strat_AMD_Continuation) e LDN_REVERSAL (NXS_Strat_LondonReversal),
in NXS_Strategies_Institutional.mqh. Entrambi dipendono dalla state
machine NXS_GetAMD() (NXS_AMDModel.mqh) + NXS_DetectSweepExt()
(NXS_MarketAnalysis.mqh) + struttura/CHOCH (NXS_Structure.mqh).

Semplificazioni dichiarate rispetto al codice MQL5 reale:
1) BUG DI TICK NELLA STATE MACHINE AMD: NXS_GetAMD() viene chiamata a
   OGNI TICK (OnTick), non una volta per barra. La fase MANIPULATION
   incrementa g_amdBeyondCount ad ogni chiamata finche' "stillBeyond" e'
   vero - quindi su un simbolo liquido come XAUUSD, con piu' tick al
   secondo, la fase MANIPULATION dura literalmente 1-2 tick (millisecondi)
   prima di collassare in CONTINUATION_DISTRIBUTION. In pratica la fase
   osservabile da qualsiasi strategia e' quasi sempre gia'
   CONTINUATION_DISTRIBUTION dal primo tick dopo la chiusura beyond, non
   dopo 2 chiusure come il commento del codice suggerisce. Qui replichiamo
   il comportamento REALE (collasso immediato), non quello "intenzionale"
   del commento - coerente con la disciplina di questa sessione di
   testare cosa il codice fa davvero in live, non cosa dovrebbe fare.
2) Sessione Asia: uso hour GMT in [0,7) invece di [InpAsianStartHour,
   InpAsianEndHour] con l'edge esatto delle 07:00 - differenza di al
   massimo 1 barra M15, irrilevante.
3) NXS_DetectSweepExt: ignorato weekly/monthly (PWH/PWL/PMH/PML) - LDN_
   REVERSAL controlla solo sweptAsiaHigh/PDH/EQH e sweptAsiaLow/PDL/EQL
   per il trigger, quindi refHigh/refLow si riducono a PDH>AsiaHigh>EQH
   (e mirror), che e' comunque l'ordine di priorita' reale MENO i casi
   rari di sweep settimanale/mensile sulla stessa barra.
4) HTF bias: InpUseHTFBias = false di default nel codice live -> SNXSHTF
   e' SEMPRE HTF_NEUTRAL in pratica, quindi il filtro htf.bias in
   AMD_CONT (che accetta BULL o NEUTRAL / BEAR o NEUTRAL) e' un NO-OP.
   Non replicato: equivale a "sempre passato".

TF: AMD_CONT sul suo EffTF (M30, dal profilo). LDN_REVERSAL sul suo
EffTF (M15, = InpTFEntry, nessun disallineamento). La AMD state machine
e la struttura/CHOCH girano SEMPRE su InpTFEntry=M15 (indipendente dal
profilo della strategia) - per AMD_CONT questo crea un vero mismatch
multi-TF nel codice live, che qui viene replicato leggendo lo stato AMD
M15 "come si presentava" al momento di chiusura di ciascuna barra M30.
"""
import sys, os, bisect
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import backtest as bt

ASIAN_START_H = 0
ASIAN_END_H = 7
LDN_MAX_HOLD = 1600
AMD_MAX_HOLD = 800
SWING_WING = 3


def pf(rs):
    g = sum(r for r in rs if r > 0)
    l = -sum(r for r in rs if r < 0)
    return g / l if l > 0 else (float("inf") if g > 0 else 0.0)


def walk_forward(rs, nw=5):
    n = len(rs)
    if n < nw * 5:
        return None
    size = n // nw
    return [(len(rs[w * size:(w + 1) * size] if w < nw - 1 else rs[w * size:]),
              pf(rs[w * size:(w + 1) * size] if w < nw - 1 else rs[w * size:]))
            for w in range(nw)]


def net_series(trades, preset="retail_standard"):
    out = []
    for t in trades:
        cost = bt.scaled_cost_for_price(preset, t["entry"])
        cost_r = min((cost["spread_price"] + cost["slippage_price"]) / t["risk_dist"], bt.MAX_COST_R_PER_TRADE)
        out.append(t["raw_r"] - cost_r)
    return out


def fmt(label, trades):
    net = net_series(trades)
    wf = walk_forward(net)
    mid = len(net) // 2
    n_pos = sum(1 for _, p in (wf or []) if p >= 1.0)
    return (f"{label:34s} n={len(trades):4d} PF={pf(net):.2f} "
            f"(m1={pf(net[:mid]):.2f}/m2={pf(net[mid:]):.2f}) win={n_pos}/{len(wf) if wf else 0}")


def is_swing_high(highs, i, wing):
    h = highs[i]
    if h <= 0:
        return False
    for k in range(1, wing + 1):
        if i + k < len(highs) and highs[i + k] >= h:
            return False
        if i - k >= 0 and highs[i - k] >= h:
            return False
    return True


def is_swing_low(lows, i, wing):
    l = lows[i]
    if l <= 0:
        return False
    for k in range(1, wing + 1):
        if i + k < len(lows) and lows[i + k] <= l:
            return False
        if i - k >= 0 and lows[i - k] <= l:
            return False
    return True


def find_equal_high(highs, i, wing, tol):
    swings = []
    for s in range(wing + 1, 60):
        idx = i - s
        if idx < 0 or len(swings) >= 8:
            break
        if is_swing_high(highs, idx, wing):
            swings.append(highs[idx])
    for a in range(len(swings)):
        for b in range(a + 1, len(swings)):
            if abs(swings[a] - swings[b]) <= tol:
                return max(swings[a], swings[b])
    return 0


def find_equal_low(lows, i, wing, tol):
    swings = []
    for s in range(wing + 1, 60):
        idx = i - s
        if idx < 0 or len(swings) >= 8:
            break
        if is_swing_low(lows, idx, wing):
            swings.append(lows[idx])
    for a in range(len(swings)):
        for b in range(a + 1, len(swings)):
            if abs(swings[a] - swings[b]) <= tol:
                return min(swings[a], swings[b])
    return 0


def last_two_swings(highs, lows, i, wing=3, scan=60):
    sH, sL = [], []
    for sh in range(wing + 1, scan):
        idx = i - sh + 1
        if idx < 0:
            continue
        if len(sH) < 2 and is_swing_high(highs, idx, wing):
            sH.append(highs[idx])
        if len(sL) < 2 and is_swing_low(lows, idx, wing):
            sL.append(lows[idx])
        if len(sH) >= 2 and len(sL) >= 2:
            break
    return sH, sL


def hm(tstr):
    d, t = tstr.split(" ")
    return d, int(t.split(":")[0])


def walk_exit(candles, entry_i, entry, sl, tp, sig, rd, max_hold):
    for j in range(entry_i + 1, min(entry_i + 1 + max_hold, len(candles))):
        hi, lo = candles[j]["high"], candles[j]["low"]
        if sig == 1:
            if lo <= sl: return (sl - entry) / rd
            if hi >= tp: return (tp - entry) / rd
        else:
            if hi >= sl: return (entry - sl) / rd
            if lo <= tp: return (entry - tp) / rd
    return None


def main():
    candles15, _ = bt._fetch_real("XAUUSD", "15m", 130000)
    candles30, _ = bt._fetch_real("XAUUSD", "30m", 70000)
    candlesD1, _ = bt._fetch_real("XAUUSD", "1d", 4000)
    ind15 = bt._prep(candles15)
    ind30 = bt._prep(candles30)
    atr15, atr30 = ind15["atr"], ind30["atr"]
    h15 = [c["high"] for c in candles15]
    l15 = [c["low"] for c in candles15]
    c15 = [c["close"] for c in candles15]
    o15 = [c["open"] for c in candles15]
    t15 = [c["time"] for c in candles15]
    n15 = len(candles15)

    d1_times = [c["time"] for c in candlesD1]
    d1_high = [c["high"] for c in candlesD1]
    d1_low = [c["low"] for c in candlesD1]

    def pdh_pdl(t):
        j = bisect.bisect_right(d1_times, t) - 1
        if j < 1:
            return None, None
        return d1_high[j - 1], d1_low[j - 1]

    # --- Asian range per calendar day (GMT), from M15 bars hour in [0,7) ---
    asian_hi, asian_lo = {}, {}
    for i in range(n15):
        d, h = hm(t15[i])
        if ASIAN_START_H <= h < ASIAN_END_H:
            asian_hi[d] = max(asian_hi.get(d, -1e18), h15[i])
            asian_lo[d] = min(asian_lo.get(d, 1e18), l15[i])

    # --- sequential M15 pass: AMD phase (tick-collapsed), structure/CHOCH,
    #     EQH/EQL, sweep flags, refHigh/refLow ---
    amd_phase = [None] * n15   # 'CONT', 'REV', None
    amd_dir = [None] * n15     # 1 = BUY continuation dir, -1 = SELL
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

    phase, manip_dir, cur_day = None, 0, None
    trend = 0
    WARMUP = 100
    for i in range(WARMUP, n15):
        d, h = hm(t15[i])
        if d != cur_day:
            cur_day = d
            phase, manip_dir = "ACC", 0
        hi = asian_hi.get(d)
        lo = asian_lo.get(d)
        if hi is None or lo is None or h < ASIAN_END_H:
            continue
        a_hi[i], a_lo[i] = hi, lo
        c1 = c15[i]
        beyondHigh = c1 > hi
        beyondLow = c1 < lo
        if phase == "ACC":
            if beyondHigh:
                phase, manip_dir = "CONT", 1     # collapses past MANIPULATION (tick bug)
            elif beyondLow:
                phase, manip_dir = "CONT", -1
        elif phase == "CONT":
            stillBeyond = beyondHigh if manip_dir == 1 else beyondLow
            if not stillBeyond:
                phase = "REV"
        elif phase == "REV":
            oppBeyond = beyondLow if manip_dir == 1 else beyondHigh
            if oppBeyond:
                manip_dir = -manip_dir
                phase = "CONT"
        amd_phase[i] = phase
        amd_dir[i] = manip_dir

        # structure / CHOCH (InpTFEntry = M15, wing=3, scan=60)
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

        # sweep vs Asia/PDH/PDL/EQH/EQL (weekly/monthly ignorati, cfr. nota 3)
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

    # ================= LDN_REVERSAL (M15, session LONDON+OVERLAP = 7-15 GMT) =================
    ldn_out = []
    for i in range(WARMUP, n15 - 2):
        d, hgmt = hm(t15[i])
        if not (7 <= hgmt < 15):
            continue
        a = atr15[i]
        if not a:
            continue
        c1, o1 = c15[i], o15[i]
        sig, sl = 0, None
        if (swept_ah[i] or swept_pdh[i] or swept_eqh[i]) and c1 < refHigh[i] and choch_down[i]:
            sig = -1
            sl = refHigh[i] + 0.5 * a
        elif (swept_al[i] or swept_pdl[i] or swept_eql[i]) and c1 > refLow[i] and choch_up[i]:
            sig = 1
            sl = refLow[i] - 0.5 * a
        if sig == 0:
            continue
        entry = c15[i + 1] if False else None
        entry_i = i + 1
        entry = candles15[entry_i]["open"]
        rd = abs(entry - sl)
        if rd <= 0:
            continue
        if sig == -1:
            tgt = a_lo[i] if a_lo[i] > 0 else (entry - 2.5 * (sl - entry))
            tp = min(tgt, entry - 2.0 * (sl - entry))
        else:
            tgt = a_hi[i] if a_hi[i] > 0 else (entry + 2.5 * (entry - sl))
            tp = max(tgt, entry + 2.0 * (entry - sl))
        exit_r = walk_exit(candles15, entry_i, entry, sl, tp, sig, rd, LDN_MAX_HOLD)
        if exit_r is None:
            continue
        ldn_out.append({"entry": entry, "risk_dist": rd, "raw_r": exit_r, "dir": sig, "time": t15[i]})

    print("=== LDN_REVERSAL (live: M15, sweep AsiaHi/PDH/EQH + CHOCH, native stop) ===", flush=True)
    print(fmt("simmetrica", ldn_out), flush=True)
    print(fmt("BUY-only", [t for t in ldn_out if t["dir"] == 1]), flush=True)
    print(fmt("SELL-only", [t for t in ldn_out if t["dir"] == -1]), flush=True)

    # ================= AMD_CONT (M30, session LONDON+OVERLAP+NY = 7-20 GMT) =================
    t15_idx_by_time = {t15[i]: i for i in range(n15)}
    o30 = [c["open"] for c in candles30]
    h30 = [c["high"] for c in candles30]
    l30 = [c["low"] for c in candles30]
    c30 = [c["close"] for c in candles30]
    t30 = [c["time"] for c in candles30]
    n30 = len(candles30)

    amd_out = []
    for j in range(WARMUP, n30 - 2):
        d, hgmt = hm(t30[j])
        if not (7 <= hgmt < 20):
            continue
        i15 = t15_idx_by_time.get(t30[j])
        if i15 is None or amd_phase[i15] != "CONT":
            continue
        hi, lo = a_hi[i15], a_lo[i15]
        if hi <= 0 or lo <= 0:
            continue
        a = atr30[j]
        if not a:
            continue
        c1, l1v, h1v = c30[j], l30[j], h30[j]
        mid = (hi + lo) * 0.5
        sig = 0
        if amd_dir[i15] == 1 and c1 > hi and l1v <= hi + a * 0.6:
            sig = 1
            sl = min(hi - 0.3 * a, mid)
        elif amd_dir[i15] == -1 and c1 < lo and h1v >= lo - a * 0.6:
            sig = -1
            sl = max(lo + 0.3 * a, mid)
        if sig == 0:
            continue
        entry_i = j + 1
        entry = candles30[entry_i]["open"]
        rd = abs(entry - sl)
        if rd <= 0:
            continue
        tp = entry + sig * 2.4 * rd
        exit_r = walk_exit(candles30, entry_i, entry, sl, tp, sig, rd, AMD_MAX_HOLD)
        if exit_r is None:
            continue
        amd_out.append({"entry": entry, "risk_dist": rd, "raw_r": exit_r, "dir": sig, "time": t30[j]})

    print("\n=== AMD_CONT (live: M30 EffTF su fase AMD M15, retest nativo) ===", flush=True)
    print(fmt("simmetrica", amd_out), flush=True)
    print(fmt("BUY-only", [t for t in amd_out if t["dir"] == 1]), flush=True)
    print(fmt("SELL-only", [t for t in amd_out if t["dir"] == -1]), flush=True)


if __name__ == "__main__":
    main()
