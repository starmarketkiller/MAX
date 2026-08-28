#!/usr/bin/env python3
"""25/08 - seguito a remaining_institutional_smc_live_signal_25-08.py:
DISP_REBAL/SH_BMS_RTO(v1)/SMS_BMS_RTO/WEEKLY_EXP tutti borderline sul TF
nativo (DISP_REBAL H4 PF0.86 n=69, SH_BMS_RTO D1 PF1.49 n=25, SMS_BMS_RTO
D1 PF0.92 n=117, WEEKLY_EXP H4/W1 PF1.18 n=16). Scan su TF alternativi
("scalp" = un TF piu' basso, "wide" = un TF piu' alto) per vedere se il
risultato nativo nasconde un edge piu' chiaro altrove o se resta
borderline ovunque - stesso schema gia' usato per AMD_CONT/LDN_REVERSAL
in amd_cont_ldn_reversal_tf_scan_25-08.py (template strutturale di questo
script).

Note aggiuntive rispetto a remaining_institutional_smc_live_signal_25-08.py:
8) SH_BMS_RTO v1 dipende da NXS_DetectSweepExt (Asia range sub-daily +
   PDH/PDL giornaliero). Su TF=D1 nativo, PDH/PDL e' strutturalmente morto
   (vedi nota nel file precedente: h1/l1/c1==pdh/pdl, sempre falso) - per
   questo la versione D1 originale lo escludeva. Su TF=H4 (variante
   "scalp" qui) PDH/PDL NON e' piu' auto-referenziale ed e' stato
   reincluso (build_generic_sweep sotto), piu' fedele a cosa succederebbe
   davvero se EffTF fosse H4. Una variante W1 ("wide") e' stata SALTATA
   di proposito: sia Asia range (sub-daily) sia PDH/PDL (giornaliero) non
   hanno un analogo sensato quando la barra stessa e' larga una settimana
   - il test darebbe numeri privi di significato, non un'estensione
   fedele della logica.
9) SMS_BMS_RTO non dipende da sweep/Asia (solo HH/LL failure-swing +
   CHOCH), quindi generalizza in modo pulito a qualunque TF inclusa W1
   (costruita per aggregazione dei D1, settimana ISO).
10) WEEKLY_EXP: la logica di range settimanale (W1 da D1, invariata) resta
    quella nativa - solo il controllo displacement/BOS/CHOCH cambia TF
    (nativo H4 -> qui H1 "scalp" e D1 "wide"), come da istruzione: non e'
    un cambio di timeframe della strategia intera, e' un cambio del TF su
    cui si verifica la candela di displacement dentro la stessa settimana.
"""
import sys, os, bisect, importlib.util
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import backtest as bt

_here = os.path.dirname(os.path.abspath(__file__))


def _load(name, fname):
    spec = importlib.util.spec_from_file_location(name, os.path.join(_here, fname))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


nxs_ctx = _load("nxs_ctx", "nxs_m15_context_25-08.py")
base = _load("rism_base", "remaining_institutional_smc_live_signal_25-08.py")

build_m15_context = nxs_ctx.build_m15_context
pf = nxs_ctx.pf
fmt = nxs_ctx.fmt
walk_exit = nxs_ctx.walk_exit
find_equal_high = nxs_ctx.find_equal_high
find_equal_low = nxs_ctx.find_equal_low
SWING_WING = nxs_ctx.SWING_WING
choch_any_in_period = base.choch_any_in_period
clamp = base.clamp
iso_week_key = base.iso_week_key
build_weekly_ranges = base.build_weekly_ranges


def resample_weekly(candlesD1):
    weeks, order = {}, []
    for c in candlesD1:
        key = iso_week_key(c["time"].split(" ")[0])
        if key not in weeks:
            weeks[key] = {"time": c["time"], "open": c["open"], "high": c["high"],
                          "low": c["low"], "close": c["close"]}
            order.append(key)
        else:
            weeks[key]["high"] = max(weeks[key]["high"], c["high"])
            weeks[key]["low"] = min(weeks[key]["low"], c["low"])
            weeks[key]["close"] = c["close"]
    return [weeks[k] for k in order]


# ===== generic sweep detector (Asia/PDH-PDL/EQH-EQL) for any TF != D1-native =====
def build_generic_sweep(candlesX, indX, ctx):
    highs = [c["high"] for c in candlesX]
    lows = [c["low"] for c in candlesX]
    closes = [c["close"] for c in candlesX]
    times = [c["time"] for c in candlesX]
    dates = [t.split(" ")[0] for t in times]
    atr = indX["atr"]
    d1_times, d1_high, d1_low = ctx["d1_times"], ctx["d1_high"], ctx["d1_low"]
    n = len(candlesX)
    dirs, levels, confirmed = [0] * n, [0.0] * n, [False] * n
    for i in range(60, n):
        a = atr[i]
        if not a:
            continue
        h1, l1, c1 = highs[i], lows[i], closes[i]
        asiaHi = ctx["asian_hi_by_date"].get(dates[i])
        asiaLo = ctx["asian_lo_by_date"].get(dates[i])
        j = bisect.bisect_right(d1_times, times[i]) - 1
        pdh = d1_high[j - 1] if j >= 1 else None
        pdl = d1_low[j - 1] if j >= 1 else None
        tol = a * 0.2
        eqH = find_equal_high(highs, i, SWING_WING, tol)
        eqL = find_equal_low(lows, i, SWING_WING, tol)
        if asiaHi and h1 > asiaHi and c1 < asiaHi:
            dirs[i], levels[i], confirmed[i] = -1, asiaHi, True
        elif asiaLo and l1 < asiaLo and c1 > asiaLo:
            dirs[i], levels[i], confirmed[i] = 1, asiaLo, True
        elif pdh is not None and h1 > pdh and c1 < pdh:
            dirs[i], levels[i], confirmed[i] = -1, pdh, True
        elif pdl is not None and l1 < pdl and c1 > pdl:
            dirs[i], levels[i], confirmed[i] = 1, pdl, True
        elif eqH > 0 and h1 > eqH and c1 < eqH:
            dirs[i], levels[i], confirmed[i] = -1, eqH, True
        elif eqL > 0 and l1 < eqL and c1 > eqL:
            dirs[i], levels[i], confirmed[i] = 1, eqL, True
    return dirs, levels, confirmed


# ===================== DISP_REBAL scan (M15 scalp, D1 wide; native H4) =====
def scan_disp_rebal(ctx):
    print("### DISP_REBAL (nativo H4 PF0.86 n=69) ###", flush=True)
    candles15, indD1 = ctx["candles15"], None
    ind15 = bt._prep(candles15)
    base.test_disp_rebal(candles15, ind15)
    candlesD1 = ctx["candlesD1"]
    indD1 = bt._prep(candlesD1)
    base.test_disp_rebal(candlesD1, indD1)


# ===================== SH_BMS_RTO scan (H4 scalp only; native D1) =========
def test_sh_bms_rto_generic(tf_label, candlesX, indX, ctx, max_hold):
    highs = [c["high"] for c in candlesX]
    lows = [c["low"] for c in candlesX]
    closes = [c["close"] for c in candlesX]
    opens = [c["open"] for c in candlesX]
    atr = indX["atr"]
    n = len(candlesX)
    sw_dir, sw_level, sw_conf = build_generic_sweep(candlesX, indX, ctx)

    def run_side(direction):
        state = "IDLE"
        sweepLevel = swingRef = originLo = originHi = 0.0
        barsWaited = 0
        trades = []
        for i in range(70, n - 1):
            a = atr[i]
            if not a:
                continue
            c1, o1, h1, l1 = closes[i], opens[i], highs[i], lows[i]
            if state == "IDLE":
                if sw_conf[i] and sw_dir[i] == direction:
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
            exit_r = walk_exit(candlesX, i, entry, sl, tp, direction, rd, max_hold)
            if exit_r is None:
                continue
            trades.append({"entry": entry, "risk_dist": rd, "raw_r": exit_r, "dir": direction})
        return trades

    out = run_side(1) + run_side(-1)
    print(f"--- SH_BMS_RTO su {tf_label} (sweep Asia/PDH-PDL/EQ + MSS + ritorno) ---", flush=True)
    print(fmt("simmetrica", out), flush=True)
    print(fmt("BUY-only", [t for t in out if t["dir"] == 1]), flush=True)
    print(fmt("SELL-only", [t for t in out if t["dir"] == -1]), flush=True)


def scan_sh_bms_rto(ctx):
    print("\n### SH_BMS_RTO v1 (nativo D1 PF1.49 n=25) ###", flush=True)
    candlesH4, _ = bt._fetch_real("XAUUSD", "4h", 30000)
    indH4 = bt._prep(candlesH4)
    test_sh_bms_rto_generic("H4", candlesH4, indH4, ctx, 500)
    print("(W1 saltata di proposito: Asia range e PDH/PDL non hanno un analogo "
          "sensato su barre larghe una settimana - vedi nota 8 in testa al file)", flush=True)


# ===================== SMS_BMS_RTO scan (H4 scalp, W1 wide; native D1) ====
def scan_sms_bms_rto(ctx):
    print("\n### SMS_BMS_RTO (nativo D1 PF0.92 n=117) ###", flush=True)
    candlesH4, _ = bt._fetch_real("XAUUSD", "4h", 30000)
    indH4 = bt._prep(candlesH4)
    base.test_sms_bms_rto(candlesH4, indH4, ctx)
    candlesW1 = resample_weekly(ctx["candlesD1"])
    indW1 = bt._prep(candlesW1)
    print(f"(W1: {len(candlesW1)} barre settimanali ricostruite dai D1)", flush=True)
    base.test_sms_bms_rto(candlesW1, indW1, ctx)


# ===================== WEEKLY_EXP scan (H1 scalp, D1 wide displacement) ===
# NOTA: quando il displacement-check gira SULLA STESSA barra D1 usata per
# il range settimanale (variante "wide"), il lookup dell'ATR-D1 di
# base.test_weekly_exp (bisect sul giorno "di oggi" poi -1 per l'ATR di
# "ieri") sbaglierebbe di un giorno extra: la barra i stessa, appena
# chiusa, E' gia' "ieri" rispetto al momento di valutazione (che avviene
# subito dopo la sua chiusura), non l'antivigilia. Per H1/H4 (intraday,
# strettamente dentro la stessa giornata della barra D1 "di oggi") la
# logica originale resta corretta - il problema esiste solo quando il TF
# di displacement E' D1. Versione locale con il fix, usata solo qui.
def test_weekly_exp_same_d1(candlesD1, indD1, ctx):
    highs = [c["high"] for c in candlesD1]
    lows = [c["low"] for c in candlesD1]
    closes = [c["close"] for c in candlesD1]
    opens = [c["open"] for c in candlesD1]
    times = [c["time"] for c in candlesD1]
    atrD1 = indD1["atr"]
    n = len(candlesD1)
    t15 = ctx["t15"]
    prev_range, week_open = build_weekly_ranges(candlesD1)

    out = []
    for i in range(40, n - 1):
        aD1 = atrD1[i]
        if not aD1:
            continue
        cH4, oH4 = closes[i], opens[i]
        if abs(cH4 - oH4) < aD1 * 0.8:
            continue
        date_i = times[i].split(" ")[0]
        key = iso_week_key(date_i)
        if key not in prev_range or key not in week_open:
            continue
        pwh, pwl = prev_range[key]
        wOpen = week_open[key]
        wMid = (pwh + pwl) * 0.5
        win_hi, win_lo = highs[i - 15:i], lows[i - 15:i]
        bosUp = cH4 > max(win_hi)
        bosDown = cH4 < min(win_lo)
        chochUp = choch_any_in_period(ctx["choch_up"], t15, times[i], times[i + 1])
        chochDown = choch_any_in_period(ctx["choch_down"], t15, times[i], times[i + 1])
        bid = cH4
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
        exit_r = walk_exit(candlesD1, i, entry, sl, tp, sig, rd, 500)
        if exit_r is None:
            continue
        out.append({"entry": entry, "risk_dist": rd, "raw_r": exit_r, "dir": sig})
    print("--- WEEKLY_EXP su D1-displacement (ATR-D1 shift corretto: no lookup extra) ---", flush=True)
    print(fmt("simmetrica", out), flush=True)
    print(fmt("BUY-only", [t for t in out if t["dir"] == 1]), flush=True)
    print(fmt("SELL-only", [t for t in out if t["dir"] == -1]), flush=True)


def scan_weekly_exp(ctx):
    print("\n### WEEKLY_EXP (nativo H4-disp/W1-range PF1.18 n=16) ###", flush=True)
    candlesD1, indD1 = ctx["candlesD1"], bt._prep(ctx["candlesD1"])
    candlesH1, _ = bt._fetch_real("XAUUSD", "1h", 110000)
    indH1 = bt._prep(candlesH1)
    base.test_weekly_exp(candlesH1, indH1, candlesD1, indD1, ctx)
    test_weekly_exp_same_d1(candlesD1, indD1, ctx)


def main():
    print("Costruzione contesto M15 (choch/sweep/asia)...", flush=True)
    ctx = build_m15_context()
    scan_disp_rebal(ctx)
    scan_sh_bms_rto(ctx)
    scan_sms_bms_rto(ctx)
    scan_weekly_exp(ctx)


if __name__ == "__main__":
    main()
