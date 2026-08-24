#!/usr/bin/env python3
"""
24/08 (14) - esecuzione della lista di idee residue chiesta dall'utente.
Tre ingredienti nuovi, mai provati oggi, sulle strategie ancora deboli
in forma simmetrica dopo tutti i test precedenti (BJORGUM/RSI_DIV/
FVG_MIT/LDN_REVERSAL/TSI_EXTREME/STRUCT_REACT):

FASE C - stop STRUTTURALE (ultimo swing a N barre), un quarto tipo mai
provato oggi (dopo ATR-mult, nativo-wick, trailing-ATR). Target a
rapporto fisso sul rischio strutturale (1:3), non ATR.

FASE D - allineamento D1 (multi-timeframe): SOSTITUISCE il filtro ER
(non si somma - lezione della zona Fibonacci di ieri, troppi filtri
impilati fanno crollare il campione) - il segnale passa solo se il
trend D1 (close vs EMA50 D1) e' nella stessa direzione del segnale.

FASE E - filtro giorno della settimana: esclude un giorno alla volta
(lunedi'-gap weekend, venerdi'-rischio weekend) sulle stesse strategie,
ER+floor invariati.
"""
import sys, os, bisect
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import backtest as bt

THR_ER = 0.045
FLOOR_PCTL = 0.3
MAX_HOLD = 200
CANDIDATES = ["BJORGUM", "RSI_DIV", "FVG_MIT", "LDN_REVERSAL", "TSI_EXTREME", "STRUCT_REACT"]


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
    return (f"{name:30s} [{tag}] n={n:4d}  "
            f"retail PF={r['pf']:.2f}(m1={r['m1']:.2f}/m2={r['m2']:.2f}) win{r['win']}/{r['nw']}  "
            f"ECN PF={e['pf']:.2f}(m1={e['m1']:.2f}/m2={e['m2']:.2f}) win{e['win']}/{e['nw']}")


# ==================== FASE C: stop strutturale (swing a N barre) ====================
SWING_N = 10
RR = 3.0


def collect_structure_stop(name, candles, ind, atr, closes, lb_er):
    sig_fn = bt.STRATEGIES[name]
    n = len(candles)
    atr_hist, trades = [], []
    for i in range(max(1500, lb_er + 50), n - 2):
        a = atr[i]
        if a:
            atr_hist.append(a)
        sig = sig_fn(candles, ind, i)
        if sig == 0 or not a:
            continue
        e = efficiency_ratio(closes, i, lb_er)
        if e is None or e < THR_ER or len(atr_hist) < 500:
            continue
        w = sorted(atr_hist[-2000:])
        floor = w[min(int(FLOOR_PCTL * len(w)), len(w) - 1)]
        if a < floor:
            continue
        window = candles[max(0, i - SWING_N + 1):i + 1]
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
        tp = entry + sig * RR * rd
        exit_r = None
        for j in range(i + 2, min(i + 2 + MAX_HOLD, n)):
            hi, lo = candles[j]["high"], candles[j]["low"]
            if sig == 1:
                if lo <= entry - rd: exit_r = -1.0; break
                elif hi >= tp: exit_r = RR; break
            else:
                if hi >= entry + rd: exit_r = -1.0; break
                elif lo <= tp: exit_r = RR; break
        if exit_r is None:
            continue
        trades.append({"entry": entry, "risk_dist": rd, "raw_r": exit_r})
    return trades


def fase_c():
    print("\n========== FASE C: stop strutturale (swing 10 barre, RR 1:3) ==========", flush=True)
    candles, src = bt._fetch_real("XAUUSD", "4h", 110000)
    ind = bt._prep(candles)
    atr, closes = ind["atr"], ind["close"]
    for name in CANDIDATES:
        trades = collect_structure_stop(name, candles, ind, atr, closes, 1000)
        if len(trades) < 30:
            print(f"{name:30s} n={len(trades)} -> troppo pochi trade", flush=True)
            continue
        s = summarize(trades)
        flag = "  <-- CANDIDATO" if (s["retail_standard"]["pf"] >= 1.0 or s["ecn"]["pf"] >= 1.20) else ""
        print(fmt(name, "4h", len(trades), s) + flag, flush=True)


# ==================== FASE D: allineamento D1 (sostituisce ER) ====================
def collect_d1_aligned(name, candles, ind, atr, d1_times, d1_close, d1_ema50):
    sig_fn = bt.STRATEGIES[name]
    n = len(candles)
    trades = []
    for i in range(max(1500, 250), n - 2):
        a = atr[i]
        if not a:
            continue
        sig = sig_fn(candles, ind, i)
        if sig == 0:
            continue
        t = candles[i]["time"]
        j_d1 = bisect.bisect_right(d1_times, t) - 1
        if j_d1 < 60:
            continue
        d1_trend_up = d1_close[j_d1] > d1_ema50[j_d1] if d1_ema50[j_d1] else None
        if d1_trend_up is None:
            continue
        if sig == 1 and not d1_trend_up:
            continue
        if sig == -1 and d1_trend_up:
            continue
        entry = candles[i + 1]["open"]
        sl = entry - sig * 1.5 * a
        tp = entry + sig * 4.0 * a
        rd = abs(entry - sl)
        if rd <= 0:
            continue
        exit_r = None
        for k in range(i + 2, min(i + 2 + MAX_HOLD, n)):
            hi, lo = candles[k]["high"], candles[k]["low"]
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


def fase_d():
    print("\n========== FASE D: allineamento trend D1 (sostituisce ER, non si somma) ==========", flush=True)
    candles, src = bt._fetch_real("XAUUSD", "4h", 110000)
    ind = bt._prep(candles)
    atr = ind["atr"]
    d1, d1src = bt._fetch_real("XAUUSD", "1d", 4000)
    d1_times = [c["time"] for c in d1]
    d1_close = [c["close"] for c in d1]
    d1_ema50 = bt.ema_series(d1_close, 50)
    for name in CANDIDATES:
        trades = collect_d1_aligned(name, candles, ind, atr, d1_times, d1_close, d1_ema50)
        if len(trades) < 30:
            print(f"{name:30s} n={len(trades)} -> troppo pochi trade", flush=True)
            continue
        s = summarize(trades)
        flag = "  <-- CANDIDATO" if (s["retail_standard"]["pf"] >= 1.0 or s["ecn"]["pf"] >= 1.20) else ""
        print(fmt(name, "4h", len(trades), s) + flag, flush=True)


# ==================== FASE E: filtro giorno della settimana ====================
def collect_no_weekday(name, exclude_wd, candles, ind, atr, closes, lb_er):
    import datetime
    sig_fn = bt.STRATEGIES[name]
    n = len(candles)
    atr_hist, trades = [], []
    for i in range(max(1500, lb_er + 50), n - 2):
        a = atr[i]
        if a:
            atr_hist.append(a)
        sig = sig_fn(candles, ind, i)
        if sig == 0 or not a:
            continue
        e = efficiency_ratio(closes, i, lb_er)
        if e is None or e < THR_ER or len(atr_hist) < 500:
            continue
        w = sorted(atr_hist[-2000:])
        floor = w[min(int(FLOOR_PCTL * len(w)), len(w) - 1)]
        if a < floor:
            continue
        d, hm = candles[i + 1]["time"].split(" ")
        wd = datetime.date(*map(int, d.split("-"))).weekday()  # 0=lun ... 4=ven
        if wd == exclude_wd:
            continue
        entry = candles[i + 1]["open"]
        sl = entry - sig * 1.5 * a
        tp = entry + sig * 4.0 * a
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


def fase_e():
    print("\n========== FASE E: esclude lunedi' o venerdi' (ER+floor invariati) ==========", flush=True)
    candles, src = bt._fetch_real("XAUUSD", "4h", 110000)
    ind = bt._prep(candles)
    atr, closes = ind["atr"], ind["close"]
    for name in CANDIDATES:
        for wd, label in ((0, "no-LUN"), (4, "no-VEN")):
            trades = collect_no_weekday(name, wd, candles, ind, atr, closes, 1000)
            if len(trades) < 30:
                print(f"{name:20s} {label} n={len(trades)} -> troppo pochi trade", flush=True)
                continue
            s = summarize(trades)
            flag = "  <-- CANDIDATO" if (s["retail_standard"]["pf"] >= 1.0 or s["ecn"]["pf"] >= 1.20) else ""
            print(fmt(f"{name} {label}", "4h", len(trades), s) + flag, flush=True)


def main():
    fase_c()
    fase_d()
    fase_e()


if __name__ == "__main__":
    main()
