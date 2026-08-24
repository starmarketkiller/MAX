#!/usr/bin/env python3
"""
24/08 (20) - l'allineamento D1 (sostituisce il filtro ER, non si somma)
ha vinto 2 volte su 2 (FVG_MIT, OTE_CONT) con lo stesso pattern pulito:
tutte le finestre positive, campione piu' ampio. Test sistematico su
tutte le altre baseline non ancora provate con questo ingrediente,
stessa config SL/TP gia' nota per ciascuna - confronto diretto ER vs
D1-alignment, stessa disciplina (due meta' + 5 finestre).
"""
import sys, os, bisect
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import backtest as bt

THR_ER = 0.045
FLOOR_PCTL = 0.3
MAX_HOLD = 200

CANDIDATES = [
    ("SAR", 1.5, 4.0),
    ("MACD", 1.5, 4.0),
    ("FVG_CONT", 1.5, 4.0),
    ("LONDON_BO", 1.0, 4.5),
    ("DONCHIAN_TURTLE", 1.5, 4.0),
    ("ADX_RSI", 1.5, 4.0),
    ("MALAYSIAN_SNR_BREAKOUT", 1.5, 4.0),
    ("DARVAS_BOX", 1.5, 4.0),
    ("AMD_CONT", 1.5, 4.0),
    ("SAR_FLIP", 1.5, 4.0),
    ("SAR_ADX20", 1.5, 4.0),
    ("BREAKOUT_ACC", 1.5, 4.0),
    ("TSI", 1.0, 6.0),
    ("EMA_PULLBACK", 1.5, 4.0),
]


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


_CACHE = {}


def get_4h():
    if "4h" not in _CACHE:
        candles, src = bt._fetch_real("XAUUSD", "4h", 110000)
        ind = bt._prep(candles)
        _CACHE["4h"] = (candles, ind)
    return _CACHE["4h"]


def get_d1():
    if "1d" not in _CACHE:
        d1, src = bt._fetch_real("XAUUSD", "1d", 4000)
        d1_times = [c["time"] for c in d1]
        d1_close = [c["close"] for c in d1]
        d1_ema50 = bt.ema_series(d1_close, 50)
        _CACHE["1d"] = (d1_times, d1_close, d1_ema50)
    return _CACHE["1d"]


def collect_er(name, sl_mult, tp_mult):
    candles, ind = get_4h()
    atr, closes = ind["atr"], ind["close"]
    n = len(candles)
    sig_fn = bt.STRATEGIES[name]
    atr_hist, out = [], []
    for i in range(max(1500, 1050), n - 2):
        a = atr[i]
        if a:
            atr_hist.append(a)
        sig = sig_fn(candles, ind, i)
        if sig == 0 or not a:
            continue
        e = efficiency_ratio(closes, i, 1000)
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
        out.append({"entry": entry, "risk_dist": rd, "raw_r": exit_r})
    return out


def collect_d1_aligned(name, sl_mult, tp_mult):
    candles, ind = get_4h()
    atr = ind["atr"]
    n = len(candles)
    sig_fn = bt.STRATEGIES[name]
    d1_times, d1_close, d1_ema50 = get_d1()
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
        entry = candles[i + 1]["open"]
        sl = entry - sig * sl_mult * a
        tp = entry + sig * tp_mult * a
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
        out.append({"entry": entry, "risk_dist": rd, "raw_r": exit_r})
    return out


def main():
    wins, losses = [], []
    for name, sl_m, tp_m in CANDIDATES:
        er_trades = collect_er(name, sl_m, tp_m)
        d1_trades = collect_d1_aligned(name, sl_m, tp_m)
        s_er = summarize(er_trades)
        s_d1 = summarize(d1_trades)
        print(fmt(f"{name} [ER]", "4h", len(er_trades), s_er), flush=True)
        print(fmt(f"{name} [D1-align]", "4h", len(d1_trades), s_d1), flush=True)
        er_pf = s_er["retail_standard"]["pf"]
        d1_pf = s_d1["retail_standard"]["pf"]
        er_win = s_er["retail_standard"]["win"]
        d1_win = s_d1["retail_standard"]["win"]
        better = d1_pf > er_pf and d1_win >= er_win
        (wins if better else losses).append(name)
        print(f"  --> D1-align {'MEGLIO' if better else 'non chiaramente meglio'} di ER", flush=True)
        print(flush=True)

    print(f"\n=== Riepilogo: D1-alignment migliora {len(wins)}/{len(CANDIDATES)} ===", flush=True)
    print("Migliorate:", wins, flush=True)
    print("Non migliorate:", losses, flush=True)


if __name__ == "__main__":
    main()
