#!/usr/bin/env python3
"""
24/08 (9) - richiesta esplicita dell'utente: non fermarsi alla ricetta
uniforme di full_catalog_screen_24-08.py (stop ATR generico 1.5/4.0 per
tutte) - creare una ricetta VARIABILE per strategia, senza escludere
ingredienti, prima di continuare. Due lacune dello screening di prima:

FASE 1 - le strategie a stop generico bocciate ieri lo erano con UN SOLO
SL/TP (1.5/4.0). Griglia di 6 combinazioni SL/TP (con ER+floor invariati)
su tutte quelle respinte o fragili oggi.

FASE 2 - le strategie con stop STRUTTURALE proprio erano state escluse
dallo screening di prima ("gia' testate a fondo con lo stop nativo il
16-17/08") ma MAI con il floor ATR (l'ingrediente nuovo di oggi) sopra il
loro stop nativo - un ingrediente mai provato in quella combinazione.
Due sotto-famiglie:
  2a - stop+target GIA' precalcolati in ind{} (CRT/FVG_CONT_V2/
       FVG_MIT_WINDOW/ORDER_BLOCK_V2/OTE_CONT_V2/SILVER_BULLET_V2/
       SH_BMS_RTO_V2) - uso diretto, nessuna reimplementazione.
  2b - famiglia sweep (TURTLE_SOUP*/CISD_TRUE/SH_BMS_RTO/SMS_BMS_RTO*/
       NY_REVERSAL_CHOCH_WINDOW/IFVG_CHOCH_WINDOW) - stop dal wick dello
       sweep (_sweep_ext_at/_turtle_soup_sl_tp, stesse funzioni del
       motore reale), target 4.0xATR fisso (stessa convenzione del
       17/08).

Compromesso esplicito (l'utente lo ha chiesto): non e' una griglia
infinita - 6 SL/TP in fase 1, un solo giro (nessun tuning) in fase 2 -
abbastanza per non escludere l'ingrediente "SL/TP diverso" senza esplodere
in migliaia di combinazioni sospette di overfitting.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import backtest as bt

LOOKBACK_ER = {"4h": 1000, "1h": 4000}
THR_ER = 0.045
FLOOR_PCTL = 0.3
MAX_HOLD = 200


def efficiency_ratio(closes, i, lookback):
    if i < lookback:
        return None
    net = abs(closes[i] - closes[i - lookback])
    total = sum(abs(closes[k] - closes[k - 1]) for k in range(i - lookback + 1, i + 1))
    return net / total if total > 0 else None


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


def summarize(trades):
    out = {}
    for preset in ("retail_standard", "ecn"):
        net = []
        for t in trades:
            cost = bt.scaled_cost_for_price(preset, t["entry"])
            cost_r = min((cost["spread_price"] + cost["slippage_price"]) / t["risk_dist"], bt.MAX_COST_R_PER_TRADE)
            net.append(t["raw_r"] - cost_r)
        wf = walk_forward(net)
        n_pos = sum(1 for _, p in (wf or []) if p >= 1.0)
        mid = len(net) // 2
        h1, h2 = net[:mid], net[mid:]
        out[preset] = {"pf": pf(net), "sumR": sum(net), "win": n_pos, "nw": len(wf) if wf else 0,
                        "m1": pf(h1), "m2": pf(h2)}
    return out


def fmt(name, tag, n, s):
    r, e = s["retail_standard"], s["ecn"]
    return (f"{name:34s} [{tag}] n={n:4d}  "
            f"retail PF={r['pf']:.2f}(m1={r['m1']:.2f}/m2={r['m2']:.2f}) win{r['win']}/{r['nw']}  "
            f"ECN PF={e['pf']:.2f}(m1={e['m1']:.2f}/m2={e['m2']:.2f}) win{e['win']}/{e['nw']}")


# ==================== FASE 1: griglia SL/TP su stop generico ====================
FASE1_CANDIDATES = ["BJORGUM", "BOLLINGER", "RSI_DIV", "STRUCT_REACT", "LIQ_SWEEP",
                     "FVG_MIT", "LDN_REVERSAL", "TSI_EXTREME", "RANGE_FADE",
                     "OTE_CONT", "TSI", "ICHIMOKU"]
SLTP_GRID = [(1.0, 3.0), (1.0, 4.5), (1.0, 6.0), (1.5, 3.0), (1.5, 6.0), (2.0, 6.0)]


def collect_generic(name, sl_mult, tp_mult, tf, candles, ind, atr, closes, lb_er):
    sig_fn = bt.STRATEGIES[name]
    n = len(candles)
    atr_hist, trades = [], []
    for i in range(max(1500, lb_er + 50), n - 2):
        a = atr[i]
        if a:
            atr_hist.append(a)
        try:
            sig = sig_fn(candles, ind, i)
        except Exception:
            return None
        if sig == 0 or not a:
            continue
        e = efficiency_ratio(closes, i, lb_er)
        if e is None or e < THR_ER or len(atr_hist) < 500:
            continue
        w = sorted(atr_hist[-2000:])
        floor = w[min(int(FLOOR_PCTL * len(w)), len(w) - 1)]
        if a < floor:
            continue
        entry = candles[i + 1]["open"]
        sl = entry - sig * sl_mult * a
        tp = entry + sig * tp_mult * a
        rd = abs(entry - sl)
        if rd <= 0:
            continue
        exit_r = None
        for j in range(i + 2, min(i + 2 + MAX_HOLD, n)):
            hi, lo = candles[j]["high"], candles[j]["low"]
            if sig == 1:
                if lo <= sl: exit_r = (sl - entry) / rd; break
                elif hi >= tp: exit_r = (tp - entry) / rd; break
            else:
                if hi >= sl: exit_r = (entry - sl) / rd; break
                elif lo <= tp: exit_r = (entry - tp) / rd; break
        if exit_r is None:
            continue
        trades.append({"entry": entry, "risk_dist": rd, "raw_r": exit_r})
    return trades


def fase1():
    print("\n========== FASE 1: griglia SL/TP (6 combinazioni) su stop generico ==========", flush=True)
    for tf in ("4h",):
        candles, src = bt._fetch_real("XAUUSD", tf, 110000)
        ind = bt._prep(candles)
        atr, closes = ind["atr"], ind["close"]
        lb_er = LOOKBACK_ER[tf]
        for name in FASE1_CANDIDATES:
            best = None
            for sl_m, tp_m in SLTP_GRID:
                trades = collect_generic(name, sl_m, tp_m, tf, candles, ind, atr, closes, lb_er)
                if trades is None or len(trades) < 30:
                    continue
                s = summarize(trades)
                score = s["retail_standard"]["pf"]
                if best is None or score > best[0]:
                    best = (score, sl_m, tp_m, len(trades), s)
            if best is None:
                print(f"{name:34s} [{tf}] nessuna combinazione con campione sufficiente", flush=True)
                continue
            score, sl_m, tp_m, n, s = best
            flag = "  <-- CANDIDATO" if (s["retail_standard"]["pf"] >= 1.0 or s["ecn"]["pf"] >= 1.20) else ""
            print(fmt(f"{name} SL{sl_m}/TP{tp_m}", tf, n, s) + flag, flush=True)


# ==================== FASE 2a: stop nativo GIA' precalcolato in ind{} ====================
FASE2A = {
    "CRT": ("crt_sl", "crt_tp"),
    "CRT_MINSTOP_FILTER": ("crt_filt_sl", "crt_filt_tp"),
    "FVG_CONT_V2": ("fvg_v2_sl", "fvg_v2_tp"),
    "FVG_MIT_WINDOW": ("fvgmitw_sl", "fvgmitw_tp"),
    "ORDER_BLOCK_V2": ("ob_v2_sl", "ob_v2_tp"),
    "OTE_CONT_V2": ("ote_v2_sl", "ote_v2_tp"),
    "SILVER_BULLET_V2": ("sbv2_sl", "sbv2_tp"),
    "SH_BMS_RTO_V2": ("shbms_v2_sl", "shbms_v2_tp"),
}


def collect_native_precomputed(name, sl_key, tp_key, candles, ind, atr, closes, lb_er):
    sig_fn = bt.STRATEGIES[name]
    n = len(candles)
    atr_hist, trades = [], []
    for i in range(max(1500, lb_er + 50), n - 2):
        a = atr[i]
        if a:
            atr_hist.append(a)
        try:
            sig = sig_fn(candles, ind, i)
        except Exception:
            return None
        if sig == 0 or not a:
            continue
        e = efficiency_ratio(closes, i, lb_er)
        if e is None or e < THR_ER or len(atr_hist) < 500:
            continue
        w = sorted(atr_hist[-2000:])
        floor = w[min(int(FLOOR_PCTL * len(w)), len(w) - 1)]
        if a < floor:
            continue
        sl, tp = ind[sl_key][i], ind[tp_key][i]
        if sl is None or tp is None:
            continue
        entry = candles[i + 1]["open"]
        rd = abs(entry - sl)
        if rd <= 0:
            continue
        exit_r = None
        for j in range(i + 2, min(i + 2 + MAX_HOLD, n)):
            hi, lo = candles[j]["high"], candles[j]["low"]
            if sig == 1:
                if lo <= sl: exit_r = (sl - entry) / rd; break
                elif hi >= tp: exit_r = (tp - entry) / rd; break
            else:
                if hi >= sl: exit_r = (entry - sl) / rd; break
                elif lo <= tp: exit_r = (entry - tp) / rd; break
        if exit_r is None:
            continue
        trades.append({"entry": entry, "risk_dist": rd, "raw_r": exit_r})
    return trades


def fase2a():
    print("\n========== FASE 2a: stop nativo precalcolato + floor ATR ==========", flush=True)
    for tf in ("4h", "1h"):
        candles, src = bt._fetch_real("XAUUSD", tf, 110000)
        ind = bt._prep(candles)
        atr, closes = ind["atr"], ind["close"]
        lb_er = LOOKBACK_ER[tf]
        for name, (sl_key, tp_key) in FASE2A.items():
            trades = collect_native_precomputed(name, sl_key, tp_key, candles, ind, atr, closes, lb_er)
            if trades is None:
                print(f"{name:34s} [{tf}] SALTATA (firma incompatibile)", flush=True)
                continue
            if len(trades) < 30:
                print(f"{name:34s} [{tf}] n={len(trades):4d} -> troppo pochi trade", flush=True)
                continue
            s = summarize(trades)
            flag = "  <-- CANDIDATO" if (s["retail_standard"]["pf"] >= 1.0 or s["ecn"]["pf"] >= 1.20) else ""
            print(fmt(name, tf, len(trades), s) + flag, flush=True)


# ==================== FASE 2b: famiglia sweep (stop dal wick, target 4.0xATR) ====================
FASE2B = ["TURTLE_SOUP", "TURTLE_SOUP_CHOCH", "TURTLE_SOUP_CHOCH_NEAR",
          "TURTLE_SOUP_CHOCH_DBLBODY", "THREE_BAR_DELIVERY_BREAK", "SH_BMS_RTO",
          "SMS_BMS_RTO", "SMS_BMS_RTO_CHOCH_WINDOW", "NY_REVERSAL_CHOCH_WINDOW",
          "IFVG_CHOCH_WINDOW"]
SWEEP_BUFFER_ATR = 0.5
SWEEP_TP_MULT = 4.0


def sweep_stop(name, c, ind, i, sig, entry, atr):
    if name.startswith("TURTLE_SOUP"):
        r = bt._turtle_soup_sl_tp(c, ind, i, sig, entry, atr)
        return r[0] if r else None
    sw = bt._sweep_ext_at(c, ind, i)
    if not sw:
        return None
    if sig == 1:
        return (sw["refLow"] - SWEEP_BUFFER_ATR * atr) if sw["refLow"] is not None else None
    return (sw["refHigh"] + SWEEP_BUFFER_ATR * atr) if sw["refHigh"] is not None else None


def collect_sweep(name, candles, ind, atr, closes, lb_er):
    sig_fn = bt.STRATEGIES[name]
    n = len(candles)
    atr_hist, trades = [], []
    for i in range(max(1500, lb_er + 50), n - 2):
        a = atr[i]
        if a:
            atr_hist.append(a)
        try:
            sig = sig_fn(candles, ind, i)
        except Exception:
            return None
        if sig == 0 or not a:
            continue
        e = efficiency_ratio(closes, i, lb_er)
        if e is None or e < THR_ER or len(atr_hist) < 500:
            continue
        w = sorted(atr_hist[-2000:])
        floor = w[min(int(FLOOR_PCTL * len(w)), len(w) - 1)]
        if a < floor:
            continue
        entry = candles[i + 1]["open"]
        sl = sweep_stop(name, candles, ind, i, sig, entry, a)
        if sl is None:
            continue
        rd = abs(entry - sl)
        if rd <= 0:
            continue
        tp = entry + sig * SWEEP_TP_MULT * a
        exit_r = None
        for j in range(i + 2, min(i + 2 + MAX_HOLD, n)):
            hi, lo = candles[j]["high"], candles[j]["low"]
            if sig == 1:
                if lo <= sl: exit_r = (sl - entry) / rd; break
                elif hi >= tp: exit_r = (tp - entry) / rd; break
            else:
                if hi >= sl: exit_r = (entry - sl) / rd; break
                elif lo <= tp: exit_r = (entry - tp) / rd; break
        if exit_r is None:
            continue
        trades.append({"entry": entry, "risk_dist": rd, "raw_r": exit_r})
    return trades


def fase2b():
    print("\n========== FASE 2b: famiglia sweep (stop wick) + floor ATR ==========", flush=True)
    for tf in ("4h", "1h"):
        candles, src = bt._fetch_real("XAUUSD", tf, 110000)
        ind = bt._prep(candles)
        atr, closes = ind["atr"], ind["close"]
        lb_er = LOOKBACK_ER[tf]
        for name in FASE2B:
            trades = collect_sweep(name, candles, ind, atr, closes, lb_er)
            if trades is None:
                print(f"{name:34s} [{tf}] SALTATA (firma incompatibile)", flush=True)
                continue
            if len(trades) < 30:
                print(f"{name:34s} [{tf}] n={len(trades):4d} -> troppo pochi trade", flush=True)
                continue
            s = summarize(trades)
            flag = "  <-- CANDIDATO" if (s["retail_standard"]["pf"] >= 1.0 or s["ecn"]["pf"] >= 1.20) else ""
            print(fmt(name, tf, len(trades), s) + flag, flush=True)


def main():
    fase1()
    fase2a()
    fase2b()


if __name__ == "__main__":
    main()
