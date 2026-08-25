#!/usr/bin/env python3
"""25/08 - ultimo lotto di ricerca da zero (non porting) sui segnali LIVE
rimasti da verificare con la disciplina di questa sessione: RANGE_FADE,
DISP_REBAL, IFVG, SH_BMS_RTO (v1, NON la V2 - quella e' gia' validata
14/08 walk-forward 5/5 su H1, fuori scope), SMS_BMS_RTO, WEEKLY_EXP.
Tutte in NXS_Strategies_Institutional.mqh / NXS_Strategies_SMC.mqh.

Semplificazioni dichiarate aggiuntive rispetto a
amd_cont_ldn_reversal_live_signal_25-08.py (le note 1-4 li' valgono
anche qui dove applicabile):
5) DISP_REBAL / SMS_BMS_RTO / WEEKLY_EXP nel codice reale confrontano
   "bid" (prezzo LIVE, intrabar) con una zona/soglia. Senza risoluzione
   intrabar, si usa il CLOSE della barra shift1 come proxy di "bid" -
   equivale a valutare la condizione solo al momento esatto della
   chiusura barra, non in qualunque istante dentro la barra. Sottostima
   leggermente il tasso di segnale reale (alcuni retest intrabar che
   non arrivano fino al close vengono persi) ma non introduce falsi
   positivi.
6) SH_BMS_RTO v1: la zona di ritorno "originLo/originHi" viene
   controllata con il RANGE (low/high) della barra invece del solo bid,
   essendo un "tocco" (touched), non un confronto puntuale - piu'
   fedele qui che usare solo il close.
7) WEEKLY_EXP: settimana calendario ISO (lun-dom) invece della
   sessione forex (dom 22:00 GMT - ven 22:00 GMT) - differenza di al
   massimo poche ore sul confine, irrilevante per un pattern settimanale.
"""
import sys, os, bisect, importlib.util
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import backtest as bt

_here = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("nxs_ctx", os.path.join(_here, "nxs_m15_context_25-08.py"))
nxs_ctx = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(nxs_ctx)
build_m15_context = nxs_ctx.build_m15_context
nearest_idx = nxs_ctx.nearest_idx
pf = nxs_ctx.pf
fmt = nxs_ctx.fmt
walk_forward = nxs_ctx.walk_forward
net_series = nxs_ctx.net_series
walk_exit = nxs_ctx.walk_exit
hm = nxs_ctx.hm
is_swing_high = nxs_ctx.is_swing_high
is_swing_low = nxs_ctx.is_swing_low
find_equal_high = nxs_ctx.find_equal_high
find_equal_low = nxs_ctx.find_equal_low
SWING_WING = nxs_ctx.SWING_WING


def clamp(v, lo, hi):
    return max(lo, min(hi, v))


# g_struct.chochUp/chochDown vengono azzerati e ricalcolati ad OGNI barra
# M15 (InpTFEntry) - restano "true" solo per la singola barra M15 in cui il
# CHOCH scatta, non in modo persistente. Una strategia con EffTF piu' alto
# (H4/D1) pero' viene rivalutata a OGNI TICK per l'intera giornata/periodo:
# se il CHOCH scatta in un QUALSIASI momento M15 dentro quel periodo, prima
# o poi un tick lo trovera' true. Allineare al solo M15 di chiusura del
# periodo (un singolo campione su 16-96 barre M15 possibili) sottostima
# drasticamente il tasso reale di attivazione - scoperto empiricamente
# durante il test di SMS_BMS_RTO (choch_up mai vero su 486 candidati con
# l'allineamento puntuale). Corretto: OR su tutte le barre M15 comprese fra
# l'apertura e la chiusura del periodo H4/D1.
def choch_any_in_period(flags, t15, t_start, t_end_excl):
    lo = bisect.bisect_left(t15, t_start)
    hi = bisect.bisect_left(t15, t_end_excl) - 1
    if hi < lo:
        return False
    return any(flags[lo:hi + 1])


# ===================== 1. RANGE_FADE (D1, self-contained) =====================
def test_range_fade(candlesD1, indD1):
    highs = [c["high"] for c in candlesD1]
    lows = [c["low"] for c in candlesD1]
    closes = [c["close"] for c in candlesD1]
    opens = [c["open"] for c in candlesD1]
    atr = indD1["atr"]
    adx = indD1["adx"]
    n = len(candlesD1)
    N, ADX_PERSIST, MAX_DRIFT, MIN_TOUCH, MIN_GAP, NO_BREAK = 40, 70.0, 0.35, 2, 3, 5
    out = []
    for i in range(2 * N + 5, n - 2):
        a = atr[i]
        if not a:
            continue
        adx_win = adx[i - N + 1:i + 1]
        if len(adx_win) < N or any(v is None for v in adx_win):
            continue
        below = sum(1 for v in adx_win if v < 20.0)
        if 100.0 * below / N < ADX_PERSIST:
            continue
        win_hi, win_lo = highs[i - N:i], lows[i - N:i]
        rngHi, rngLo = max(win_hi), min(win_lo)
        if (rngHi - rngLo) < a * 1.5:
            continue
        half = N // 2
        winA_hi, winA_lo = highs[i - 2 * half:i - half], lows[i - 2 * half:i - half]
        winB_hi, winB_lo = highs[i - half:i], lows[i - half:i]
        widthA = max(winA_hi) - min(winA_lo)
        widthB = max(winB_hi) - min(winB_lo)
        maxW = max(widthA, widthB)
        if maxW <= 0 or abs(widthA - widthB) / maxW > MAX_DRIFT:
            continue
        edgeBand = a * 0.4
        upT = loT = 0
        lastU = lastL = -1000
        aboveMid = 0
        rngMid = (rngHi + rngLo) * 0.5
        for sft in range(1, N + 1):
            idx = i - sft + 1
            hh, ll, cc = highs[idx], lows[idx], closes[idx]
            if hh >= rngHi - edgeBand and (sft - lastU) >= MIN_GAP:
                upT += 1; lastU = sft
            if ll <= rngLo + edgeBand and (sft - lastL) >= MIN_GAP:
                loT += 1; lastL = sft
            if cc > rngMid:
                aboveMid += 1
        if upT < MIN_TOUCH or loT < MIN_TOUCH:
            continue
        pct = 100.0 * aboveMid / N
        if pct < 30.0 or pct > 70.0:
            continue
        bBuf = a * 0.3
        broke = False
        for sft in range(1, NO_BREAK + 1):
            idx = i - sft + 1
            if closes[idx] > rngHi + bBuf or closes[idx] < rngLo - bBuf:
                broke = True; break
        if broke:
            continue
        c1, o1, h1, l1 = closes[i], opens[i], highs[i], lows[i]
        if abs(c1 - o1) < a * 0.25:
            continue
        sig = 0
        if l1 <= rngLo + 0.4 * a and c1 > o1 and c1 > rngLo:
            sig = 1
            sl = min(l1, rngLo) - 0.4 * a
        elif h1 >= rngHi - 0.4 * a and c1 < o1 and c1 < rngHi:
            sig = -1
            sl = max(h1, rngHi) + 0.4 * a
        else:
            continue
        entry_i = i + 1
        entry = candlesD1[entry_i]["open"]
        rd = abs(entry - sl)
        if rd <= 0:
            continue
        tp = min(rngMid, entry + 2.0 * (entry - sl)) if sig == 1 else max(rngMid, entry - 2.0 * (sl - entry))
        exit_r = walk_exit(candlesD1, entry_i, entry, sl, tp, sig, rd, 300)
        if exit_r is None:
            continue
        out.append({"entry": entry, "risk_dist": rd, "raw_r": exit_r, "dir": sig})
    print("--- RANGE_FADE (D1, range persistente + reject bordo) ---", flush=True)
    print(fmt("simmetrica", out), flush=True)
    print(fmt("BUY-only", [t for t in out if t["dir"] == 1]), flush=True)
    print(fmt("SELL-only", [t for t in out if t["dir"] == -1]), flush=True)


# ===================== 2. DISP_REBAL (H4, self-contained) =====================
def test_disp_rebal(candlesH4, indH4):
    highs = [c["high"] for c in candlesH4]
    lows = [c["low"] for c in candlesH4]
    closes = [c["close"] for c in candlesH4]
    opens = [c["open"] for c in candlesH4]
    atr = indH4["atr"]
    n = len(candlesH4)

    def disp_bar(i, direction, lookback, bodyMult, a):
        for sft in range(1, lookback + 1):
            idx = i - sft + 1
            if idx < 0:
                break
            o, c = opens[idx], closes[idx]
            if abs(c - o) < a * bodyMult:
                continue
            if direction > 0 and c > o:
                return sft
            if direction < 0 and c < o:
                return sft
        return -1

    out = []
    for i in range(30, n - 1):
        a = atr[i]
        if not a:
            continue
        c1, o1 = closes[i], opens[i]
        bid = c1  # nota 5
        sig = None
        dS = disp_bar(i, +1, 8, 1.3, a)
        if dS > 1:
            idxD = i - dS + 1
            c1High, c3Low = highs[idxD - 1], lows[idxD + 1]
            if c3Low > c1High + a * 0.1:
                fvgLo, fvgHi = c1High, c3Low
                ce = (fvgLo + fvgHi) * 0.5
                if fvgLo <= bid <= ce + a * 0.15 and c1 > o1:
                    sig = 1
                    sl = fvgLo - 0.3 * a
                    entry = bid
                    tp = max(fvgHi + 0.8 * (fvgHi - fvgLo), entry + 2.4 * (entry - sl))
        if sig is None:
            dSb = disp_bar(i, -1, 8, 1.3, a)
            if dSb > 1:
                idxD = i - dSb + 1
                c1Low, c3High = lows[idxD - 1], highs[idxD + 1]
                if c1Low > c3High + a * 0.1:
                    fvgLo, fvgHi = c3High, c1Low
                    ce = (fvgLo + fvgHi) * 0.5
                    if ce - a * 0.15 <= bid <= fvgHi and c1 < o1:
                        sig = -1
                        sl = fvgHi + 0.3 * a
                        entry = bid
                        tp = min(fvgLo - 0.8 * (fvgHi - fvgLo), entry - 2.4 * (sl - entry))
        if sig is None:
            continue
        rd = abs(entry - sl)
        if rd <= 0:
            continue
        exit_r = walk_exit(candlesH4, i, entry, sl, tp, sig, rd, 500)
        if exit_r is None:
            continue
        out.append({"entry": entry, "risk_dist": rd, "raw_r": exit_r, "dir": sig})
    print("--- DISP_REBAL (H4, FVG displacement + CE retest) ---", flush=True)
    print(fmt("simmetrica", out), flush=True)
    print(fmt("BUY-only", [t for t in out if t["dir"] == 1]), flush=True)
    print(fmt("SELL-only", [t for t in out if t["dir"] == -1]), flush=True)


# ===================== 3. IFVG (H4 + CHOCH M15 allineato) =====================
def test_ifvg(candlesH4, indH4, ctx):
    highs = [c["high"] for c in candlesH4]
    lows = [c["low"] for c in candlesH4]
    closes = [c["close"] for c in candlesH4]
    opens = [c["open"] for c in candlesH4]
    times = [c["time"] for c in candlesH4]
    atr = indH4["atr"]
    n = len(candlesH4)
    t15 = ctx["t15"]
    out = []
    for i in range(10, n - 2):
        a = atr[i]
        if not a or i - 4 < 0:
            continue
        h2, l2 = highs[i - 1], lows[i - 1]
        h4v, l4v = highs[i - 3], lows[i - 3]
        c1, o1 = closes[i], opens[i]
        reactionBear = (c1 < o1) and (abs(c1 - o1) > a * 0.3)
        reactionBull = (c1 > o1) and (abs(c1 - o1) > a * 0.3)
        chochDown = choch_any_in_period(ctx["choch_down"], t15, times[i], times[i + 1])
        chochUp = choch_any_in_period(ctx["choch_up"], t15, times[i], times[i + 1])
        sig = 0
        if l2 > h4v + a * 0.2 and c1 < h4v and reactionBear and chochDown:
            sig = -1
            sl = l2 + 0.5 * a
        elif h2 < l4v - a * 0.2 and c1 > l4v and reactionBull and chochUp:
            sig = 1
            sl = h2 - 0.5 * a
        if sig == 0:
            continue
        entry_i = i + 1
        entry = candlesH4[entry_i]["open"]
        rd = abs(entry - sl)
        if rd <= 0:
            continue
        tp = entry + sig * 2.4 * a
        exit_r = walk_exit(candlesH4, entry_i, entry, sl, tp, sig, rd, 500)
        if exit_r is None:
            continue
        out.append({"entry": entry, "risk_dist": rd, "raw_r": exit_r, "dir": sig})
    print("--- IFVG (H4, FVG invalidato + CHOCH M15) ---", flush=True)
    print(fmt("simmetrica", out), flush=True)
    print(fmt("BUY-only", [t for t in out if t["dir"] == 1]), flush=True)
    print(fmt("SELL-only", [t for t in out if t["dir"] == -1]), flush=True)


# ===================== D1 sweep detector (per SH_BMS_RTO) =====================
# NOTA IMPORTANTE: per una strategia con EffTF=D1, h1/l1/c1 di
# NXS_DetectSweepExt (letti su NXS_EffTF()=D1) sono LETTERALMENTE la stessa
# barra di pdh/pdl (iHigh/iLow(D1,1), fissi indipendentemente dal tf). Quindi
# "h1>pdh && c1<pdh" diventa "pdh>pdh" - SEMPRE falso. Lo sweep PDH/PDL e'
# strutturalmente morto per SH_BMS_RTO (non e' un bug isolato: qualunque
# strategia con EffTF=D1 che consumasse sw.sweptPDH/sweptPDL avrebbe lo
# stesso problema - SH_BMS_RTO e' l'unica in questo lotto che usa sw).
# Restano vivi solo Asia e EQH/EQL (priorita' Asia poi equal, come da codice).
def build_d1_sweep(candlesD1, indD1, ctx):
    highs = [c["high"] for c in candlesD1]
    lows = [c["low"] for c in candlesD1]
    closes = [c["close"] for c in candlesD1]
    dates = [c["time"].split(" ")[0] for c in candlesD1]
    atr = indD1["atr"]
    n = len(candlesD1)
    dirs = [0] * n
    levels = [0.0] * n
    confirmed = [False] * n
    for i in range(60, n):
        a = atr[i]
        if not a:
            continue
        h1, l1, c1 = highs[i], lows[i], closes[i]
        asiaHi = ctx["asian_hi_by_date"].get(dates[i])
        asiaLo = ctx["asian_lo_by_date"].get(dates[i])
        tol = a * 0.2
        eqH = find_equal_high(highs, i, SWING_WING, tol)
        eqL = find_equal_low(lows, i, SWING_WING, tol)
        if asiaHi and h1 > asiaHi and c1 < asiaHi:
            dirs[i], levels[i], confirmed[i] = -1, asiaHi, True
        elif asiaLo and l1 < asiaLo and c1 > asiaLo:
            dirs[i], levels[i], confirmed[i] = 1, asiaLo, True
        elif eqH > 0 and h1 > eqH and c1 < eqH:
            dirs[i], levels[i], confirmed[i] = -1, eqH, True
        elif eqL > 0 and l1 < eqL and c1 > eqL:
            dirs[i], levels[i], confirmed[i] = 1, eqL, True
    return dirs, levels, confirmed


# ===================== 4. SH_BMS_RTO v1 (D1, sweep + MSS + return) =====================
def test_sh_bms_rto(candlesD1, indD1, ctx):
    highs = [c["high"] for c in candlesD1]
    lows = [c["low"] for c in candlesD1]
    closes = [c["close"] for c in candlesD1]
    opens = [c["open"] for c in candlesD1]
    atr = indD1["atr"]
    n = len(candlesD1)
    sw_dir, sw_level, sw_conf = build_d1_sweep(candlesD1, indD1, ctx)

    out = []

    def run_side(direction):
        state = "IDLE"
        sweepLevel = swingRef = originLo = originHi = 0.0
        barsWaited = 0
        wantSweep = direction
        trades = []
        for i in range(70, n - 1):
            a = atr[i]
            if not a:
                continue
            c1, o1, h1, l1 = closes[i], opens[i], highs[i], lows[i]
            if state == "IDLE":
                if sw_conf[i] and sw_dir[i] == wantSweep:
                    state = "SWEPT"; barsWaited = 0; sweepLevel = sw_level[i]
                    win_hi, win_lo = highs[i - 15:i], lows[i - 15:i]
                    swingRef = max(win_hi) if direction == 1 else min(win_lo)
                continue
            if state == "SWEPT":
                if (direction == 1 and c1 < sweepLevel) or (direction == -1 and c1 > sweepLevel):
                    state = "IDLE"; continue
                barsWaited += 1
                if barsWaited > 20:
                    state = "IDLE"; continue
                body1 = abs(c1 - o1)
                mss = (swingRef > 0 and body1 >= a * 0.8 and
                       ((direction == 1 and c1 > swingRef) or (direction == -1 and c1 < swingRef)))
                if not mss:
                    continue
                originA, originB = o1, c1
                for k in range(2, 7):
                    idx = i - k + 1
                    if idx < 0:
                        break
                    ok, ck = opens[idx], closes[idx]
                    opp = (ck < ok) if direction == 1 else (ck > ok)
                    if opp:
                        originA, originB = ok, ck
                        break
                originLo, originHi = min(originA, originB), max(originA, originB)
                state = "WAITING"; barsWaited = 0
                continue
            # WAITING
            barsWaited += 1
            if barsWaited > 15:
                state = "IDLE"; continue
            if (direction == 1 and c1 < sweepLevel) or (direction == -1 and c1 > sweepLevel):
                state = "IDLE"; continue
            if originHi <= originLo:
                continue
            touched = (l1 <= originHi and h1 >= originLo)
            if not touched:
                continue
            entry = clamp(c1, originLo, originHi)
            if direction == 1:
                sl = min(sweepLevel, originLo) - 0.5 * a
                tp = entry + 2.6 * a
            else:
                sl = max(sweepLevel, originHi) + 0.5 * a
                tp = entry - 2.6 * a
            rd = abs(entry - sl)
            state = "IDLE"
            if rd <= 0:
                continue
            exit_r = walk_exit(candlesD1, i, entry, sl, tp, direction, rd, 300)
            if exit_r is None:
                continue
            trades.append({"entry": entry, "risk_dist": rd, "raw_r": exit_r, "dir": direction})
        return trades

    out = run_side(1) + run_side(-1)
    print("--- SH_BMS_RTO v1 (D1, sweep Asia/EQ + MSS + ritorno origine) ---", flush=True)
    print(fmt("simmetrica", out), flush=True)
    print(fmt("BUY-only", [t for t in out if t["dir"] == 1]), flush=True)
    print(fmt("SELL-only", [t for t in out if t["dir"] == -1]), flush=True)


# ===================== 5. SMS_BMS_RTO (D1 + CHOCH M15 allineato) =====================
def test_sms_bms_rto(candlesD1, indD1, ctx):
    highs = [c["high"] for c in candlesD1]
    lows = [c["low"] for c in candlesD1]
    closes = [c["close"] for c in candlesD1]
    opens = [c["open"] for c in candlesD1]
    times = [c["time"] for c in candlesD1]
    atr = indD1["atr"]
    n = len(candlesD1)
    t15 = ctx["t15"]
    out = []
    for i in range(35, n - 1):
        a = atr[i]
        if not a:
            continue
        c1, o1 = closes[i], opens[i]
        bodyAbs = abs(c1 - o1)
        rejBull = (c1 > o1) and bodyAbs > a * 0.3
        rejBear = (c1 < o1) and bodyAbs > a * 0.3
        hi_recent = max(highs[i - 9:i + 1])
        hi_older = max(highs[i - 29:i - 9])
        lo_recent = min(lows[i - 9:i + 1])
        lo_older = min(lows[i - 29:i - 9])
        failureLow = lo_recent > lo_older
        failureHigh = hi_recent < hi_older
        mid = (hi_recent + lo_recent) * 0.5
        chochUp = choch_any_in_period(ctx["choch_up"], t15, times[i], times[i + 1])
        chochDown = choch_any_in_period(ctx["choch_down"], t15, times[i], times[i + 1])
        bid = c1  # nota 5
        sig = None
        if failureLow and chochUp and rejBull and bid <= mid:
            sig = 1
            sl = lo_recent - 0.5 * a
            entry = bid
            tp = entry + 2.6 * a
        elif failureHigh and chochDown and rejBear and bid >= mid:
            sig = -1
            sl = hi_recent + 0.5 * a
            entry = bid
            tp = entry - 2.6 * a
        if sig is None:
            continue
        rd = abs(entry - sl)
        if rd <= 0:
            continue
        exit_r = walk_exit(candlesD1, i, entry, sl, tp, sig, rd, 300)
        if exit_r is None:
            continue
        out.append({"entry": entry, "risk_dist": rd, "raw_r": exit_r, "dir": sig})
    print("--- SMS_BMS_RTO (D1, failure swing + CHOCH M15 + RTO) ---", flush=True)
    print(fmt("simmetrica", out), flush=True)
    print(fmt("BUY-only", [t for t in out if t["dir"] == 1]), flush=True)
    print(fmt("SELL-only", [t for t in out if t["dir"] == -1]), flush=True)


# ===================== 6. WEEKLY_EXP (H4 + settimana ISO da D1 + CHOCH M15) ===
def iso_week_key(date_str):
    d = datetime.strptime(date_str, "%Y-%m-%d")
    y, w, _ = d.isocalendar()
    return (y, w)


def build_weekly_ranges(candlesD1):
    dates = [c["time"].split(" ")[0] for c in candlesD1]
    weeks_ordered = []
    week_info = {}
    for i, d in enumerate(dates):
        key = iso_week_key(d)
        if key not in week_info:
            week_info[key] = {"high": candlesD1[i]["high"], "low": candlesD1[i]["low"], "open": candlesD1[i]["open"]}
            weeks_ordered.append(key)
        else:
            week_info[key]["high"] = max(week_info[key]["high"], candlesD1[i]["high"])
            week_info[key]["low"] = min(week_info[key]["low"], candlesD1[i]["low"])
    prev_range = {}
    for idx, key in enumerate(weeks_ordered):
        if idx == 0:
            continue
        pk = weeks_ordered[idx - 1]
        prev_range[key] = (week_info[pk]["high"], week_info[pk]["low"])
    week_open = {k: week_info[k]["open"] for k in weeks_ordered}
    return prev_range, week_open


def test_weekly_exp(candlesH4, indH4, candlesD1, indD1, ctx):
    highs = [c["high"] for c in candlesH4]
    lows = [c["low"] for c in candlesH4]
    closes = [c["close"] for c in candlesH4]
    opens = [c["open"] for c in candlesH4]
    times = [c["time"] for c in candlesH4]
    atrH4 = indH4["atr"]
    n = len(candlesH4)
    t15 = ctx["t15"]
    prev_range, week_open = build_weekly_ranges(candlesD1)
    d1_times = ctx["d1_times"]
    atrD1 = indD1["atr"]

    out = []
    for i in range(40, n - 1):
        aH4 = atrH4[i]
        if not aH4:
            continue
        cH4, oH4 = closes[i], opens[i]
        if abs(cH4 - oH4) < aH4 * 0.8:
            continue
        j = bisect.bisect_right(d1_times, times[i]) - 1
        if j < 1:
            continue
        aD1 = atrD1[j - 1]
        if not aD1:
            continue
        date_i = times[i].split(" ")[0]
        key = iso_week_key(date_i)
        if key not in prev_range or key not in week_open:
            continue
        pwh, pwl = prev_range[key]
        wOpen = week_open[key]
        wMid = (pwh + pwl) * 0.5
        win_hi, win_lo = highs[i - 15:i], lows[i - 15:i]
        swingHiH4, swingLoH4 = max(win_hi), min(win_lo)
        bosUp = cH4 > swingHiH4
        bosDown = cH4 < swingLoH4
        chochUp = choch_any_in_period(ctx["choch_up"], t15, times[i], times[i + 1])
        chochDown = choch_any_in_period(ctx["choch_down"], t15, times[i], times[i + 1])
        bid = cH4  # nota 5
        sig = None
        if bid < wMid and cH4 > oH4 and bosUp and bid > wOpen and chochUp:
            sig = 1
            sl = min(pwl, bid - 1.5 * aD1)
            leg = pwh - pwl
            fib = pwh + 0.272 * leg
            entry = bid
            tp = max(max(pwh, fib), entry + 2.6 * (entry - sl))
        elif bid > wMid and cH4 < oH4 and bosDown and bid < wOpen and chochDown:
            sig = -1
            sl = max(pwh, bid + 1.5 * aD1)
            leg = pwh - pwl
            fib = pwl - 0.272 * leg
            entry = bid
            tp = min(min(pwl, fib), entry - 2.6 * (sl - entry))
        if sig is None:
            continue
        rd = abs(entry - sl)
        if rd <= 0:
            continue
        exit_r = walk_exit(candlesH4, i, entry, sl, tp, sig, rd, 500)
        if exit_r is None:
            continue
        out.append({"entry": entry, "risk_dist": rd, "raw_r": exit_r, "dir": sig})
    print("--- WEEKLY_EXP (H4 displacement + settimana ISO + CHOCH M15) ---", flush=True)
    print(fmt("simmetrica", out), flush=True)
    print(fmt("BUY-only", [t for t in out if t["dir"] == 1]), flush=True)
    print(fmt("SELL-only", [t for t in out if t["dir"] == -1]), flush=True)


def main():
    print("Costruzione contesto M15 (choch/sweep/asia)...", flush=True)
    ctx = build_m15_context()
    candlesD1 = ctx["candlesD1"]
    indD1 = bt._prep(candlesD1)
    candlesH4, _ = bt._fetch_real("XAUUSD", "4h", 30000)
    indH4 = bt._prep(candlesH4)

    test_range_fade(candlesD1, indD1)
    print(flush=True)
    test_disp_rebal(candlesH4, indH4)
    print(flush=True)
    test_ifvg(candlesH4, indH4, ctx)
    print(flush=True)
    test_sh_bms_rto(candlesD1, indD1, ctx)
    print(flush=True)
    test_sms_bms_rto(candlesD1, indD1, ctx)
    print(flush=True)
    test_weekly_exp(candlesH4, indH4, candlesD1, indD1, ctx)


if __name__ == "__main__":
    main()

