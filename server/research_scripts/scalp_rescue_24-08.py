#!/usr/bin/env python3
"""
24/08 (22) - le SCALP_* erano state bocciate ieri sera testando 3 assi
(TF M15/M30, ampiezza stop 1.0/3.0->2.0/6.0, uscita a fine giornata) -
tutti e tre SENZA filtro di regime (deliberatamente scartato allora:
"la tesi di queste strategie e' il timing, non la forza del trend").
Oggi, dopo aver visto quanto conta il regime per tutto il resto del
catalogo, riprovate con tre ingredienti mai toccati sulle SCALP_*:

1. Filtro ER (lo stesso di tutto il resto del catalogo) - anche uno
   scalp ha bisogno di UN MINIMO di follow-through direzionale per
   arrivare al target, anche piccolo.
2. Target molto piu' stretti, coerenti con una tesi di scalping vera
   (0.5/1.0, 0.5/1.5, 0.3/0.9 ATR) - ieri sera i test partivano da
   1.0/3.0, gia' largo per uno scalp.
3. Floor ATR (filtra i momenti di volatilita' troppo bassa, dove il
   costo fisso pesa di piu' - lo stesso principio che ha salvato meta'
   del catalogo ieri).

M15 (TF nativo), uscita a fine giornata come ieri sera (non piu' il
punto debole, gia' verificato).
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import backtest as bt

SCALP_NAMES = ["SCALP_BB_FADE", "SCALP_EMA", "SCALP_RANGE_BRK", "SCALP_RSI_SNAP"]
THR_ER = 0.045
LOOKBACK_ER = 16000  # stessa finestra calendario (~167 giorni) di 1000 barre 4h, scalata a M15 (x16)
FLOOR_PCTL = 0.3
SLTP_GRID = [(0.3, 0.9), (0.5, 1.0), (0.5, 1.5), (1.0, 2.0)]
MAX_HOLD_BARS = 400


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
    return (f"{name:34s} [{tag}] n={n:5d}  "
            f"retail PF={r['pf']:.2f}(m1={r['m1']:.2f}/m2={r['m2']:.2f}) win{r['win']}/{r['nw']}  "
            f"ECN PF={e['pf']:.2f}(m1={e['m1']:.2f}/m2={e['m2']:.2f}) win{e['win']}/{e['nw']}")


def collect(name, sl_mult, tp_mult, candles, ind, atr, closes, dates):
    sig_fn = bt.STRATEGIES[name]
    n = len(candles)
    atr_hist, trades = [], []
    for i in range(max(1500, LOOKBACK_ER + 50), n - 2):
        a = atr[i]
        if a:
            atr_hist.append(a)
        sig = sig_fn(candles, ind, i)
        if sig == 0 or not a:
            continue
        e = efficiency_ratio(closes, i, LOOKBACK_ER)
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
        entry_date = dates[i + 1]
        exit_r = None
        last_j = min(i + 1 + MAX_HOLD_BARS, n - 1)
        for j in range(i + 2, min(i + 2 + MAX_HOLD_BARS, n)):
            hi, lo = candles[j]["high"], candles[j]["low"]
            if sig == 1:
                if lo <= sl: exit_r = (sl - entry) / rd; break
                elif hi >= tp: exit_r = (tp - entry) / rd; break
            else:
                if hi >= sl: exit_r = (entry - sl) / rd; break
                elif lo <= tp: exit_r = (entry - tp) / rd; break
            if dates[j] != entry_date:
                c = candles[j]["open"]
                exit_r = (c - entry) / rd if sig == 1 else (entry - c) / rd
                break
        if exit_r is None:
            c = candles[last_j]["close"]
            exit_r = (c - entry) / rd if sig == 1 else (entry - c) / rd
        trades.append({"entry": entry, "risk_dist": rd, "raw_r": exit_r})
    return trades


def main():
    candles, src = bt._fetch_real("XAUUSD", "15m", 110000)
    ind = bt._prep(candles)
    atr, closes = ind["atr"], ind["close"]
    dates = ind["sess"]["date"]
    print(f"M15: {len(candles)} candele ({src})", flush=True)

    for name in SCALP_NAMES:
        best = None
        for sl_m, tp_m in SLTP_GRID:
            trades = collect(name, sl_m, tp_m, candles, ind, atr, closes, dates)
            if len(trades) < 30:
                continue
            s = summarize(trades)
            score = s["retail_standard"]["pf"]
            if best is None or score > best[0]:
                best = (score, sl_m, tp_m, len(trades), s)
        if best is None:
            print(f"{name:34s} nessuna combinazione con campione sufficiente", flush=True)
            continue
        score, sl_m, tp_m, n, s = best
        flag = "  <-- CANDIDATO" if (s["retail_standard"]["pf"] >= 1.0 or s["ecn"]["pf"] >= 1.20) else ""
        print(fmt(f"{name} SL{sl_m}/TP{tp_m}", "15m", n, s) + flag, flush=True)


if __name__ == "__main__":
    main()
