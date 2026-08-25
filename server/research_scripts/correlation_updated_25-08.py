#!/usr/bin/env python3
"""
25/08 - riprende il problema di allocazione del portafoglio, in pausa
dal 24/08 su richiesta dell'utente (vedi [[NEXUS EA - Correlazione tra
le 20 Strategie (24-08)]]). Da allora il catalogo e' cambiato molto:
quasi tutte le strategie hanno trailing/filtro Elliott/D1-align
aggiunti, 3 nuove strategie promosse (ML_ADAPTIVE_SUPERTREND/BOLLINGER/
RSI_DIV), 1 strategia nuova nata (ELLIOTT_WAVE3_CONT), TURTLE_SOUP e
LDN_REVERSAL riverificate. La correlazione del 24/08 usava le config
di allora - va ricalcolata prima di qualunque decisione di
allocazione, altrimenti si deciderebbe su dati vecchi.

Stesso metodo del 24/08: bucket giornaliero di R netto per strategia
(somma dei net_r di tutti i trade con quella data di apertura),
correlazione di Pearson a coppie sulla matrice giorno x strategia.

Registro delle config vincenti di oggi (dalla tabella master
aggiornata 25/08) - un generatore generico per le strategie ER+floor
standard (fixed o trailing, +Elliott dove validato), generatori
dedicati per le poche con meccaniche speciali (stop nativo/strutturale,
segnale esterno).
"""
import sys, os, bisect
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import backtest as bt
import importlib.util

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("ew", os.path.join(HERE, "elliott_wave_filter_25-08.py"))
ew = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ew)

THR_ER = 0.045
FLOOR_PCTL = 0.3
MAX_HOLD = 200
LOOKBACK_ER = {"4h": 1000, "1h": 4000}
DEV_MULT = 2.0

_CACHE = {}


def get_prepped(tf):
    if tf not in _CACHE:
        candles, src = bt._fetch_real("XAUUSD", tf, 110000)
        ind = bt._prep(candles)
        _CACHE[tf] = (candles, ind)
    return _CACHE[tf]


_EXH_CACHE = {}


def get_exhaustion(tf):
    if tf not in _EXH_CACHE:
        candles, ind = get_prepped(tf)
        exh, _ = ew.build_zigzag_full(candles, ind["atr"], DEV_MULT)
        _EXH_CACHE[tf] = exh
    return _EXH_CACHE[tf]


def get_d1_exhaustion():
    if "d1" not in _EXH_CACHE:
        candlesD1, srcD1 = bt._fetch_real("XAUUSD", "1d", 4000)
        indD1 = bt._prep(candlesD1)
        exh, _ = ew.build_zigzag_full(candlesD1, indD1["atr"], DEV_MULT)
        times = [c["time"] for c in candlesD1]
        _EXH_CACHE["d1"] = (exh, times)
    return _EXH_CACHE["d1"]


def d1_exh_at(t):
    exh, times = get_d1_exhaustion()
    j = bisect.bisect_right(times, t) - 1
    return exh[j] if j >= 0 else 0


# ---------------- generatore generico: ER+floor, fixed o trailing, +Elliott opzionale ----------------
def gen_generic(name, tf, sl_mult, tp_mult, buy_only, trailing, use_elliott, use_floor=True):
    candles, ind = get_prepped(tf)
    atr, closes = ind["atr"], ind["close"]
    n = len(candles)
    lb_er = LOOKBACK_ER[tf]
    sig_fn = bt.STRATEGIES[name]
    exh_tf = get_exhaustion(tf) if use_elliott else None
    atr_hist, out = [], []
    for i in range(max(1500, lb_er + 50), n - 2):
        a = atr[i]
        if a:
            atr_hist.append(a)
        sig = sig_fn(candles, ind, i)
        if sig == 0 or not a:
            continue
        if buy_only and sig != 1:
            continue
        e = ew.efficiency_ratio(closes, i, lb_er)
        if e is None or e < THR_ER or len(atr_hist) < 500:
            continue
        if use_floor:
            w = sorted(atr_hist[-2000:])
            floor = w[min(int(FLOOR_PCTL * len(w)), len(w) - 1)]
            if a < floor:
                continue
        if use_elliott:
            t = candles[i]["time"]
            if exh_tf[i] == sig or d1_exh_at(t) == sig:
                continue
        entry = candles[i + 1]["open"]
        if trailing is None:
            sl = entry - sig * sl_mult * a
            tp = entry + sig * tp_mult * a
            rd = abs(entry - sl)
            if rd <= 0:
                continue
            exit_r, exit_j = None, None
            for j in range(i + 2, min(i + 2 + MAX_HOLD, n)):
                hi, lo = candles[j]["high"], candles[j]["low"]
                if sig == 1:
                    if lo <= sl: exit_r, exit_j = (sl - entry) / rd, j; break
                    elif hi >= tp: exit_r, exit_j = (tp - entry) / rd, j; break
                else:
                    if hi >= sl: exit_r, exit_j = (entry - sl) / rd, j; break
                    elif lo <= tp: exit_r, exit_j = (entry - tp) / rd, j; break
        else:
            init_sl, trail_mult = trailing
            rd = init_sl * a
            sl = entry - sig * rd
            extreme = entry
            exit_r, exit_j = None, None
            for j in range(i + 2, min(i + 2 + MAX_HOLD, n)):
                hi, lo = candles[j]["high"], candles[j]["low"]
                if sig == 1:
                    if lo <= sl: exit_r, exit_j = (sl - entry) / rd, j; break
                    extreme = max(extreme, hi)
                    ns = extreme - trail_mult * a
                    if ns > sl: sl = ns
                else:
                    if hi >= sl: exit_r, exit_j = (entry - sl) / rd, j; break
                    extreme = min(extreme, lo)
                    ns = extreme + trail_mult * a
                    if ns < sl: sl = ns
            if exit_r is None:
                exit_j = min(i + 1 + MAX_HOLD, n - 1)
                lc = candles[exit_j]["close"]
                exit_r = (lc - entry) / rd if sig == 1 else (entry - lc) / rd
        if exit_r is None:
            continue
        out.append({"strat": name, "open_time": candles[i + 1]["time"],
                     "close_time": candles[exit_j]["time"], "entry": entry,
                     "risk_dist": rd, "net_r": exit_r})
    return out


# ---------------- generatore D1-align (OTE_CONT / FVG_MIT / EMA_PULLBACK) ----------------
def gen_d1align(name, sl_mult, tp_mult, trailing, use_elliott):
    candles, ind = get_prepped("4h")
    atr = ind["atr"]
    n = len(candles)
    sig_fn = bt.STRATEGIES[name]
    candlesD1, _ = bt._fetch_real("XAUUSD", "1d", 4000)
    indD1 = bt._prep(candlesD1)
    d1_close = indD1["close"]
    d1_ema50 = bt.ema_series(d1_close, 50)
    d1_times = [c["time"] for c in candlesD1]
    exh_4h = get_exhaustion("4h") if use_elliott else None
    out = []
    for i in range(max(1500, 250), n - 2):
        a = atr[i]
        if not a:
            continue
        sig = sig_fn(candles, ind, i)
        if sig == 0:
            continue
        t = candles[i]["time"]
        j_d1 = bisect.bisect_right(d1_times, t) - 1
        if j_d1 < 60 or not d1_ema50[j_d1]:
            continue
        d1_up = d1_close[j_d1] > d1_ema50[j_d1]
        if sig == 1 and not d1_up:
            continue
        if sig == -1 and d1_up:
            continue
        if use_elliott:
            if exh_4h[i] == sig or d1_exh_at(t) == sig:
                continue
        entry = candles[i + 1]["open"]
        close_idx = None
        if trailing is None:
            sl = entry - sig * sl_mult * a
            tp = entry + sig * tp_mult * a
            rd = abs(entry - sl)
            if rd <= 0:
                continue
            exit_r = None
            for k in range(i + 2, min(i + 2 + MAX_HOLD, n)):
                hi, lo = candles[k]["high"], candles[k]["low"]
                if sig == 1:
                    if lo <= sl: exit_r, close_idx = (sl - entry) / rd, k; break
                    elif hi >= tp: exit_r, close_idx = (tp - entry) / rd, k; break
                else:
                    if hi >= sl: exit_r, close_idx = (entry - sl) / rd, k; break
                    elif lo <= tp: exit_r, close_idx = (entry - tp) / rd, k; break
        else:
            init_sl, trail_mult = trailing
            rd = init_sl * a
            sl = entry - sig * rd
            extreme = entry
            exit_r = None
            for k in range(i + 2, min(i + 2 + MAX_HOLD, n)):
                hi, lo = candles[k]["high"], candles[k]["low"]
                if sig == 1:
                    if lo <= sl: exit_r, close_idx = (sl - entry) / rd, k; break
                    extreme = max(extreme, hi)
                    ns = extreme - trail_mult * a
                    if ns > sl: sl = ns
                else:
                    if hi >= sl: exit_r, close_idx = (entry - sl) / rd, k; break
                    extreme = min(extreme, lo)
                    ns = extreme + trail_mult * a
                    if ns < sl: sl = ns
            if exit_r is None:
                close_idx = min(i + 1 + MAX_HOLD, n - 1)
                lc = candles[close_idx]["close"]
                exit_r = (lc - entry) / rd if sig == 1 else (entry - lc) / rd
        if exit_r is None:
            continue
        out.append({"strat": name, "open_time": candles[i + 1]["time"],
                     "close_time": candles[close_idx]["time"], "entry": entry,
                     "risk_dist": rd, "net_r": exit_r})
    return out


# ---------------- FVG_CONT_V2: stop nativo + trailing + Elliott ----------------
def gen_fvgcontv2():
    candles, ind = get_prepped("4h")
    atr, closes = ind["atr"], ind["close"]
    n = len(candles)
    lb_er = LOOKBACK_ER["4h"]
    sig_fn = bt.STRATEGIES["FVG_CONT_V2"]
    exh_4h = get_exhaustion("4h")
    trail_mult = 2.0
    atr_hist, out = [], []
    for i in range(max(1500, lb_er + 50), n - 2):
        a = atr[i]
        if a:
            atr_hist.append(a)
        sig = sig_fn(candles, ind, i)
        if sig != 1 or not a:
            continue
        e = ew.efficiency_ratio(closes, i, lb_er)
        if e is None or e < THR_ER or len(atr_hist) < 500:
            continue
        w = sorted(atr_hist[-2000:])
        floor = w[min(int(FLOOR_PCTL * len(w)), len(w) - 1)]
        if a < floor:
            continue
        t = candles[i]["time"]
        if exh_4h[i] == sig or d1_exh_at(t) == sig:
            continue
        entry = candles[i + 1]["open"]
        sl0 = ind["fvg_v2_sl"][i]
        if sl0 is None:
            continue
        rd = abs(entry - sl0)
        if rd <= 0:
            continue
        sl = sl0
        extreme = entry
        exit_r, close_idx = None, None
        for j in range(i + 2, min(i + 2 + MAX_HOLD, n)):
            hi, lo = candles[j]["high"], candles[j]["low"]
            if lo <= sl: exit_r, close_idx = (sl - entry) / rd, j; break
            extreme = max(extreme, hi)
            ns = extreme - trail_mult * a
            if ns > sl: sl = ns
        if exit_r is None:
            close_idx = min(i + 1 + MAX_HOLD, n - 1)
            lc = candles[close_idx]["close"]
            exit_r = (lc - entry) / rd
        out.append({"strat": "FVG_CONT_V2", "open_time": candles[i + 1]["time"],
                     "close_time": candles[close_idx]["time"], "entry": entry,
                     "risk_dist": rd, "net_r": exit_r})
    return out


# ---------------- TURTLE_SOUP: wick sweep stop + fixed TP + Elliott ----------------
def gen_turtlesoup():
    candles, ind = get_prepped("4h")
    atr, closes = ind["atr"], ind["close"]
    n = len(candles)
    lb_er = LOOKBACK_ER["4h"]
    sig_fn = bt.STRATEGIES["TURTLE_SOUP"]
    exh_4h = get_exhaustion("4h")
    atr_hist, out = [], []
    for i in range(max(1500, lb_er + 50), n - 2):
        a = atr[i]
        if a:
            atr_hist.append(a)
        sig = sig_fn(candles, ind, i)
        if sig == 0 or not a:
            continue
        e = ew.efficiency_ratio(closes, i, lb_er)
        if e is None or e < THR_ER or len(atr_hist) < 500:
            continue
        w = sorted(atr_hist[-2000:])
        floor = w[min(int(FLOOR_PCTL * len(w)), len(w) - 1)]
        if a < floor:
            continue
        t = candles[i]["time"]
        if exh_4h[i] == sig or d1_exh_at(t) == sig:
            continue
        entry = candles[i + 1]["open"]
        r = bt._turtle_soup_sl_tp(candles, ind, i, sig, entry, a)
        sl = r[0] if r else None
        if sl is None:
            continue
        rd = abs(entry - sl)
        if rd <= 0:
            continue
        tp = entry + sig * 4.0 * a
        exit_r, close_idx = None, None
        for j in range(i + 2, min(i + 2 + MAX_HOLD, n)):
            hi, lo = candles[j]["high"], candles[j]["low"]
            if sig == 1:
                if lo <= sl: exit_r, close_idx = (sl - entry) / rd, j; break
                elif hi >= tp: exit_r, close_idx = (tp - entry) / rd, j; break
            else:
                if hi >= sl: exit_r, close_idx = (entry - sl) / rd, j; break
                elif lo <= tp: exit_r, close_idx = (entry - tp) / rd, j; break
        if exit_r is None:
            continue
        out.append({"strat": "TURTLE_SOUP", "open_time": candles[i + 1]["time"],
                     "close_time": candles[close_idx]["time"], "entry": entry,
                     "risk_dist": rd, "net_r": exit_r})
    return out


# ---------------- LDN_REVERSAL: structural swing stop + Elliott ----------------
def gen_ldnreversal():
    candles, ind = get_prepped("4h")
    atr, closes = ind["atr"], ind["close"]
    n = len(candles)
    lb_er = LOOKBACK_ER["4h"]
    sig_fn = bt.STRATEGIES["LDN_REVERSAL"]
    exh_4h = get_exhaustion("4h")
    swing_n, rr = 10, 3.0
    atr_hist, out = [], []
    for i in range(max(1500, lb_er + 50), n - 2):
        a = atr[i]
        if a:
            atr_hist.append(a)
        sig = sig_fn(candles, ind, i)
        if sig == 0 or not a:
            continue
        e = ew.efficiency_ratio(closes, i, lb_er)
        if e is None or e < THR_ER or len(atr_hist) < 500:
            continue
        w = sorted(atr_hist[-2000:])
        floor = w[min(int(FLOOR_PCTL * len(w)), len(w) - 1)]
        if a < floor:
            continue
        t = candles[i]["time"]
        if exh_4h[i] == sig or d1_exh_at(t) == sig:
            continue
        window = candles[max(0, i - swing_n + 1):i + 1]
        swing_hi = max(c["high"] for c in window)
        swing_lo = min(c["low"] for c in window)
        entry = candles[i + 1]["open"]
        sl = swing_lo if sig == 1 else swing_hi
        rd = abs(entry - sl)
        floor_dist = 0.3 * a
        if rd < floor_dist:
            rd = floor_dist
        if rd <= 0:
            continue
        tp = entry + sig * rr * rd
        exit_r, close_idx = None, None
        for j in range(i + 2, min(i + 2 + MAX_HOLD, n)):
            hi, lo = candles[j]["high"], candles[j]["low"]
            if sig == 1:
                if lo <= entry - rd: exit_r, close_idx = -1.0, j; break
                elif hi >= tp: exit_r, close_idx = rr, j; break
            else:
                if hi >= entry + rd: exit_r, close_idx = -1.0, j; break
                elif lo <= tp: exit_r, close_idx = rr, j; break
        if exit_r is None:
            continue
        out.append({"strat": "LDN_REVERSAL", "open_time": candles[i + 1]["time"],
                     "close_time": candles[close_idx]["time"], "entry": entry,
                     "risk_dist": rd, "net_r": exit_r})
    return out


# ---------------- ELLIOTT_WAVE3_CONT ----------------
def gen_wave3cont():
    spec2 = importlib.util.spec_from_file_location("w3", os.path.join(HERE, "elliott_wave3_continuation_25-08.py"))
    w3 = importlib.util.module_from_spec(spec2)
    spec2.loader.exec_module(w3)
    candles, ind = get_prepped("4h")
    atr, closes = ind["atr"], ind["close"]
    wave_sig = w3.wave3_signal_series(candles, atr)
    trades = w3.collect(candles, ind, atr, closes, wave_sig, 2.0, 6.0, buy_only=True)
    out = []
    for t in trades:
        out.append({"strat": "ELLIOTT_WAVE3_CONT", "open_time": t["time"],
                     "close_time": t["close_time"], "entry": t["entry"],
                     "risk_dist": t["risk_dist"], "net_r": t["raw_r"]})
    return out


# ==================== REGISTRO DELLE CONFIG VINCENTI (25/08) ====================
def collect_all():
    all_trades = []

    generic_specs = [
        # (name, tf, sl, tp, buy_only, trailing(init,trail) or None, use_elliott)
        ("SAR", "4h", 1.5, 4.0, True, (1.5, 2.0), True),
        ("MACD", "4h", 1.5, 4.0, False, (1.5, 2.0), True),
        ("FVG_CONT", "4h", 1.5, 4.0, True, (1.5, 2.0), True),
        ("LONDON_BO", "4h", 1.0, 4.5, True, (1.0, 2.0), False),
        ("DONCHIAN_TURTLE", "4h", 1.5, 4.0, True, None, True),
        ("DARVAS_BOX", "4h", 1.5, 4.0, True, None, True),
        ("ADX_RSI", "4h", 1.5, 4.0, True, (1.5, 2.5), True),
        ("SAR_ADX20", "4h", 1.5, 4.0, True, (1.5, 2.0), True),
        ("BREAKOUT_ACC", "4h", 1.5, 4.0, True, None, True),
        ("STRUCT_REACT", "4h", 2.0, 6.0, True, None, False),
        ("LIQ_SWEEP", "4h", 1.5, 6.0, True, (1.5, 3.0), False),
        ("TSI", "4h", 1.0, 6.0, True, None, True),
        ("MALAYSIAN_SNR_BREAKOUT", "4h", 1.5, 4.0, True, None, True),
        ("SAR_FLIP", "4h", 1.5, 4.0, True, (1.5, 2.0), True),
        ("AMD_CONT", "4h", 1.5, 4.0, True, None, True),
        ("BOLLINGER", "4h", 1.5, 4.0, True, None, True),
        ("RSI_DIV", "4h", 1.5, 4.0, True, None, True),
    ]
    for name, tf, sl, tp, buy_only, trailing, use_elliott in generic_specs:
        all_trades.extend(gen_generic(name, tf, sl, tp, buy_only, trailing, use_elliott))

    d1align_specs = [
        ("OTE_CONT", 1.0, 6.0, None, True),
        ("FVG_MIT", 2.0, 6.0, (2.0, 3.0), True),
        ("EMA_PULLBACK", 1.5, 4.0, (1.5, 3.0), True),
    ]
    for name, sl, tp, trailing, use_elliott in d1align_specs:
        all_trades.extend(gen_d1align(name, sl, tp, trailing, use_elliott))

    all_trades.extend(gen_fvgcontv2())
    all_trades.extend(gen_turtlesoup())
    all_trades.extend(gen_ldnreversal())
    all_trades.extend(gen_wave3cont())

    return all_trades


def build_daily_matrix(trades):
    strat_names = sorted(set(t["strat"] for t in trades))
    all_dates = sorted(set(t["open_time"].split(" ")[0] for t in trades))
    idx = {d: i for i, d in enumerate(all_dates)}
    mat = {s: [0.0] * len(all_dates) for s in strat_names}
    for t in trades:
        d = t["open_time"].split(" ")[0]
        mat[t["strat"]][idx[d]] += t["net_r"]
    return strat_names, all_dates, mat


def pearson(a, b):
    n = len(a)
    ma = sum(a) / n
    mb = sum(b) / n
    cov = sum((a[i] - ma) * (b[i] - mb) for i in range(n))
    va = sum((x - ma) ** 2 for x in a)
    vb = sum((x - mb) ** 2 for x in b)
    if va <= 0 or vb <= 0:
        return None
    return cov / (va ** 0.5 * vb ** 0.5)


def main():
    trades = collect_all()
    strat_names, all_dates, mat = build_daily_matrix(trades)
    n = len(strat_names)
    print(f"{n} strategie, {len(all_dates)} giorni con almeno un trade (qualche strategia)", flush=True)
    print("Strategie:", ", ".join(strat_names), flush=True)

    corr = {}
    for i in range(n):
        for j in range(i + 1, n):
            a, b = strat_names[i], strat_names[j]
            c = pearson(mat[a], mat[b])
            corr[(a, b)] = c

    pairs = sorted(corr.items(), key=lambda kv: -(kv[1] if kv[1] is not None else -2))
    print("\n=== Coppie piu' correlate ===", flush=True)
    for (a, b), c in pairs[:20]:
        print(f"  {a:26s} <-> {b:26s}  r={c:+.3f}", flush=True)

    print("\n=== Coppie piu' negativamente correlate ===", flush=True)
    for (a, b), c in pairs[-15:]:
        print(f"  {a:26s} <-> {b:26s}  r={c:+.3f}", flush=True)

    print("\n=== Correlazione media di ciascuna strategia ===", flush=True)
    avg_corr = {}
    for s in strat_names:
        vals = []
        for (a, b), c in corr.items():
            if c is None:
                continue
            if a == s or b == s:
                vals.append(c)
        avg_corr[s] = sum(vals) / len(vals) if vals else None
    for s, v in sorted(avg_corr.items(), key=lambda kv: -(kv[1] if kv[1] is not None else -2)):
        print(f"  {s:26s} corr_media={v:+.3f}" if v is not None else f"  {s:26s} n/a", flush=True)


if __name__ == "__main__":
    main()
