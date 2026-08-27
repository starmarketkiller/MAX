#!/usr/bin/env python3
"""26/08 - secondo giro della proposta ingresso-raffinato-M15 +
breakeven/trailing strutturale, stavolta su WEEKLY_EXP: stop nativo =
min(pwl, bid - 1.5xATR(D1)) - l'ATR D1 di XAUUSD e' tipicamente $25-45,
quindi QUESTO e' un vero candidato a stop largo (a differenza di
DISP_REBAL, primo giro, dove lo stop nativo era gia' stretto $7 e il
tentativo ha solo peggiorato le cose per costi dominanti).

Correzioni rispetto al primo giro (fallito):
1) Conferma di reazione M15 piu' severa: replica ESATTA di
   NXS_HasPriceReaction (pin bar: wick > 1.5x corpo E > 0.5x range,
   OPPURE chiusura direzionale con corpo > 0.3xATR) invece del semplice
   "corpo forte" generico - stesso criterio del vero motore, non
   inventato.
2) Breakeven piu' tardivo: 1.0R invece di 0.5R (piu' spazio prima di
   bloccare a pareggio).
3) Trailing con margine piu' largo: 0.3xATR invece di 0.1xATR (meno
   whipsaw).
4) Trailing NON attivo da subito dopo breakeven - parte solo dopo che
   il prezzo e' andato 1.5R in profitto, lasciando respirare il trade."""
import sys, os, bisect, importlib.util
from datetime import datetime
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import backtest as bt

_here = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("nxs_ctx", os.path.join(_here, "nxs_m15_context_25-08.py"))
nxs_ctx = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(nxs_ctx)

MAX_RISK_AT_MIN_LOT_PCT = 8.0
ACCOUNTS = [500.0, 1000.0]
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
    rd = sorted(t["risk_dist"] for t in trades)
    rd_med = rd[len(rd) // 2] if rd else 0.0
    streak = maxstreak = 0
    for v in net:
        if v < 0:
            streak += 1
            maxstreak = max(maxstreak, streak)
        else:
            streak = 0
    return (f"{label:30s} n={len(trades):5d} PF={pf(net):.2f} "
            f"(m1={pf(net[:mid]):.2f}/m2={pf(net[mid:]):.2f}) win={n_pos}/{len(wf) if wf else 0} "
            f"medRiskDist=${rd_med:.2f} maxLossStreak={maxstreak}")


def is_swing_high(highs, i, wing):
    h = highs[i]
    if h <= 0: return False
    for k in range(1, wing + 1):
        if i + k < len(highs) and highs[i + k] >= h: return False
        if i - k >= 0 and highs[i - k] >= h: return False
    return True


def is_swing_low(lows, i, wing):
    l = lows[i]
    if l <= 0: return False
    for k in range(1, wing + 1):
        if i + k < len(lows) and lows[i + k] <= l: return False
        if i - k >= 0 and lows[i - k] <= l: return False
    return True


def choch_any_in_period(flags, t15, t_start, t_end_excl):
    lo = bisect.bisect_left(t15, t_start)
    hi = bisect.bisect_left(t15, t_end_excl) - 1
    if hi < lo:
        return False
    return any(flags[lo:hi + 1])


def iso_week_key(date_str):
    d = datetime.strptime(date_str, "%Y-%m-%d")
    y, w, _ = d.isocalendar()
    return (y, w)


def build_weekly_ranges(candlesD1):
    dates = [c["time"].split(" ")[0] for c in candlesD1]
    weeks_ordered, week_info = [], {}
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
        if idx == 0: continue
        pk = weeks_ordered[idx - 1]
        prev_range[key] = (week_info[pk]["high"], week_info[pk]["low"])
    week_open = {k: week_info[k]["open"] for k in weeks_ordered}
    return prev_range, week_open


def find_native_signals(candlesH4, indH4, candlesD1, indD1, ctx):
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
        bid = cH4
        sig = None
        if bid < wMid and cH4 > oH4 and bosUp and bid > wOpen and chochUp:
            sig = 1
            sl = min(pwl, bid - 1.5 * aD1)
            entry = bid
        elif bid > wMid and cH4 < oH4 and bosDown and bid < wOpen and chochDown:
            sig = -1
            sl = max(pwh, bid + 1.5 * aD1)
            entry = bid
        if sig is None:
            continue
        out.append({"i": i, "time": times[i], "dir": sig, "entry_native": entry,
                     "sl_native": sl, "atr_h4": aH4, "pwh": pwh, "pwl": pwl})
    return out


def run_native(signals, candlesH4):
    highs = [c["high"] for c in candlesH4]
    lows = [c["low"] for c in candlesH4]
    n = len(candlesH4)
    out = []
    for s in signals:
        i, sig, entry, sl = s["i"], s["dir"], s["entry_native"], s["sl_native"]
        rd = abs(entry - sl)
        if rd <= 0:
            continue
        leg = s["pwh"] - s["pwl"]
        fib = s["pwh"] + 0.272 * leg if sig == 1 else s["pwl"] - 0.272 * leg
        tp = max(max(s["pwh"], fib), entry + 2.6 * (entry - sl)) if sig == 1 else \
             min(min(s["pwl"], fib), entry - 2.6 * (sl - entry))
        exit_r = None
        for j in range(i + 1, min(i + 500, n)):
            hi, lo = highs[j], lows[j]
            if sig == 1:
                if lo <= sl: exit_r = (sl - entry) / rd; break
                if hi >= tp: exit_r = (tp - entry) / rd; break
            else:
                if hi >= sl: exit_r = (entry - sl) / rd; break
                if lo <= tp: exit_r = (entry - tp) / rd; break
        if exit_r is None:
            continue
        out.append({"entry": entry, "risk_dist": rd, "raw_r": exit_r, "dir": sig, "time": s["time"]})
    return out


def has_reaction(o, c, h, l, direction):
    body = abs(c - o)
    rng = max(h - l, 1e-9)
    upWick = h - max(o, c)
    dnWick = min(o, c) - l
    if direction > 0:
        pin = dnWick > body * 1.5 and dnWick > rng * 0.5
        close = c > o
        return pin or close
    else:
        pin = upWick > body * 1.5 and upWick > rng * 0.5
        close = c < o
        return pin or close


def run_ltf_refined(signals, candlesM15, breakeven_at_r=1.0, trail_activate_r=1.5,
                     trail_buffer_atr=0.3, max_wait_bars=8, max_hold_bars=3000):
    times15 = [c["time"] for c in candlesM15]
    highs15 = [c["high"] for c in candlesM15]
    lows15 = [c["low"] for c in candlesM15]
    closes15 = [c["close"] for c in candlesM15]
    opens15 = [c["open"] for c in candlesM15]
    n15 = len(candlesM15)
    ind15 = bt._prep(candlesM15)
    atr15 = ind15["atr"]

    def m15_idx_at(t):
        return bisect.bisect_right(times15, t) - 1

    out = []
    for s in signals:
        sig = s["dir"]
        h4_i15 = m15_idx_at(s["time"])
        if h4_i15 < 30:
            continue
        entry_idx = None
        sl0 = None
        for w in range(1, max_wait_bars + 1):
            j = h4_i15 + w
            if j >= n15 - 1:
                break
            o, c, hi, lo = opens15[j], closes15[j], highs15[j], lows15[j]
            a15 = atr15[j]
            if not a15:
                continue
            if abs(c - o) < a15 * 0.3:
                continue
            if has_reaction(o, c, hi, lo, sig):
                entry_idx = j
                sl0 = (lo - 0.2 * a15) if sig == 1 else (hi + 0.2 * a15)
                break
        if entry_idx is None:
            continue
        entry_i = entry_idx + 1
        if entry_i >= n15:
            continue
        entry = candlesM15[entry_i]["open"]
        rd0 = abs(entry - sl0)
        if rd0 <= 0:
            continue

        sl = sl0
        be_done = trail_on = False
        exit_r = None
        for j in range(entry_i + 1, min(entry_i + max_hold_bars, n15)):
            hi, lo = highs15[j], lows15[j]
            a15 = atr15[j] or 0
            if sig == 1:
                if lo <= sl:
                    exit_r = (sl - entry) / rd0
                    break
                if not be_done and hi >= entry + breakeven_at_r * rd0:
                    sl = max(sl, entry)
                    be_done = True
                if not trail_on and hi >= entry + trail_activate_r * rd0:
                    trail_on = True
                if trail_on:
                    newsl = lows15[j - 1] - trail_buffer_atr * a15
                    if newsl > sl:
                        sl = newsl
            else:
                if hi >= sl:
                    exit_r = (entry - sl) / rd0
                    break
                if not be_done and lo <= entry - breakeven_at_r * rd0:
                    sl = min(sl, entry)
                    be_done = True
                if not trail_on and lo <= entry - trail_activate_r * rd0:
                    trail_on = True
                if trail_on:
                    newsl = highs15[j - 1] + trail_buffer_atr * a15
                    if newsl < sl:
                        sl = newsl
        if exit_r is None:
            continue
        out.append({"entry": entry, "risk_dist": rd0, "raw_r": exit_r, "dir": sig, "time": s["time"]})
    return out


def apply_risk_size_gate(trades, balance):
    kept, rejected = [], 0
    for t in trades:
        if t["risk_dist"] > balance * (MAX_RISK_AT_MIN_LOT_PCT / 100.0):
            rejected += 1
            continue
        kept.append(t)
    return kept, rejected


def main():
    ctx = nxs_ctx.build_m15_context()
    candlesD1 = ctx["candlesD1"]
    indD1 = bt._prep(candlesD1)
    candlesH4, _ = bt._fetch_real("XAUUSD", "4h", 40000)
    indH4 = bt._prep(candlesH4)

    signals = find_native_signals(candlesH4, indH4, candlesD1, indD1, ctx)
    print(f"Segnali H4 WEEKLY_EXP grezzi (pre-gate, CON filtro CHOCH - ricetta verificata): {len(signals)}", flush=True)

    native = run_native(signals, candlesH4)
    ltf = run_ltf_refined(signals, ctx["candles15"])

    print("\n=== BASELINE: stop nativo (1.5xATR-D1 dal livello settimanale) ===", flush=True)
    print(fmt("nativo", native), flush=True)

    print("\n=== NUOVO: ingresso raffinato M15 (reazione vera) + BE 1.0R + trailing attivato a 1.5R ===", flush=True)
    print(fmt("LTF+trail v2", ltf), flush=True)

    for label, trades in (("nativo", native), ("LTF+trail v2", ltf)):
        print(f"\n--- Gate RISK_SIZE per '{label}' ---", flush=True)
        for bal in ACCOUNTS:
            kept, rejected = apply_risk_size_gate(trades, bal)
            tot = len(trades)
            pct = 100.0 * rejected / tot if tot else 0.0
            print(f"  saldo=${bal:.0f}: rifiutati {rejected}/{tot} ({pct:.1f}%)  ->  " + fmt("eseguiti", kept), flush=True)


if __name__ == "__main__":
    main()
