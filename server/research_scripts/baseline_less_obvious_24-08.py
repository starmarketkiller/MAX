#!/usr/bin/env python3
"""
24/08 (12) - metodi MENO ovvi per trovare altre baseline, oltre a
ricetta uniforme/griglia SL-TP/stop nativo/trailing/sessione gia'
provati oggi. Due ingredienti mai toccati finora in tutta l'indagine di
oggi:

FASE A - split BUY/SELL. Principio gia' scritto nel roadmap del
progetto ("Buy e Sell sono setup distinti - analizzarli separatamente
prima di disattivarne uno") ma MAI applicato oggi - ogni test ha trattato
i segnali in modo simmetrico. Una strategia bocciata nell'aggregato puo'
avere un lato solo con edge reale, annacquato dall'altro lato negativo.
Split sulle strategie bocciate/marginali di oggi, stessa ricetta migliore
gia' trovata per ciascuna (griglia SL/TP di baseline_expansion_24-08.py).

FASE B - timeframe D1. Mai testato oggi (solo 4h/1h per il nucleo/nuove
baseline, M15/M30 per sessione/scalp) - alcune strategie del catalogo
avevano profili storici D1 (ADX_RSI, MALAYSIAN_SNR, LIQ_SWEEP, SH_BMS_RTO,
ORDER_BLOCK) mai riverificati con la ricetta ER+floor di oggi. ER
lookback e finestra floor scalati proporzionalmente (un D1 "trend" dura
mesi, non ha senso usare lo stesso numero di barre di un 4h).
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import backtest as bt

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


def collect(name, sl_mult, tp_mult, candles, ind, atr, closes, lb_er, floor_pctl):
    sig_fn = bt.STRATEGIES[name]
    n = len(candles)
    atr_hist, trades = [], []
    for i in range(max(300, lb_er + 50), n - 2):
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
        if e is None or e < THR_ER or len(atr_hist) < 100:
            continue
        if floor_pctl is not None:
            w = sorted(atr_hist[-2000:])
            floor = w[min(int(floor_pctl * len(w)), len(w) - 1)]
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
        trades.append({"entry": entry, "risk_dist": rd, "raw_r": exit_r, "dir": sig})
    return trades


# ==================== FASE A: split BUY/SELL ====================
# (nome, sl_mult, tp_mult) - migliore config gia' trovata oggi per ciascuna,
# incluse le marginali/bocciate (per dare a entrambi i lati una chance equa)
FASE_A = [
    ("BJORGUM", 1.5, 6.0), ("RSI_DIV", 1.0, 3.0), ("FVG_MIT", 2.0, 6.0),
    ("LDN_REVERSAL", 1.0, 4.5), ("TSI_EXTREME", 2.0, 6.0), ("ICHIMOKU", 1.0, 4.5),
    ("STRUCT_REACT", 2.0, 6.0), ("BOLLINGER", 1.0, 6.0), ("SAR_ADX20", 1.5, 4.0),
    ("SAR_FLIP", 1.5, 4.0), ("DARVAS_BOX", 1.5, 4.0),
]


def fase_a():
    print("\n========== FASE A: split BUY/SELL (4h) ==========", flush=True)
    candles, src = bt._fetch_real("XAUUSD", "4h", 110000)
    ind = bt._prep(candles)
    atr, closes = ind["atr"], ind["close"]
    lb_er = 1000
    for name, sl_m, tp_m in FASE_A:
        trades = collect(name, sl_m, tp_m, candles, ind, atr, closes, lb_er, FLOOR_PCTL)
        if not trades:
            print(f"{name:34s} nessun trade")
            continue
        buys = [t for t in trades if t["dir"] == 1]
        sells = [t for t in trades if t["dir"] == -1]
        for label, group in (("BUY", buys), ("SELL", sells)):
            if len(group) < 30:
                print(f"{name:24s} {label:5s} n={len(group):4d} -> troppo pochi trade", flush=True)
                continue
            s = summarize(group)
            flag = "  <-- CANDIDATO" if (s["retail_standard"]["pf"] >= 1.0 or s["ecn"]["pf"] >= 1.20) else ""
            print(fmt(f"{name} [{label}]", "4h", len(group), s) + flag, flush=True)


# ==================== FASE B: timeframe D1 ====================
FASE_B_NAMES = ["ADX_RSI", "MALAYSIAN_SNR_BREAKOUT", "LIQ_SWEEP", "SH_BMS_RTO",
                 "ORDER_BLOCK", "BJORGUM", "BOLLINGER", "RSI_DIV", "SAR",
                 "MACD", "TSI", "OTE_CONT", "DARVAS_BOX", "DONCHIAN_TURTLE",
                 "BREAKOUT_ACC", "EMA_PULLBACK"]


def fase_b():
    print("\n========== FASE B: timeframe D1 ==========", flush=True)
    candles, src = bt._fetch_real("XAUUSD", "1d", 4000)
    ind = bt._prep(candles)
    atr, closes = ind["atr"], ind["close"]
    lb_er = 120   # ~4-6 mesi di trading su D1, scalato dai 1000 barre/167gg del 4h
    print(f"D1: {len(candles)} candele ({src})", flush=True)
    for name in FASE_B_NAMES:
        best = None
        for sl_m, tp_m in [(1.0, 3.0), (1.5, 4.0), (1.0, 4.5), (1.5, 6.0)]:
            trades = collect(name, sl_m, tp_m, candles, ind, atr, closes, lb_er, 0.2)
            if trades is None or len(trades) < 30:
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
        print(fmt(f"{name} SL{sl_m}/TP{tp_m}", "1d", n, s) + flag, flush=True)


def main():
    fase_a()
    fase_b()


if __name__ == "__main__":
    main()
