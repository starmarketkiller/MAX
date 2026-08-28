#!/usr/bin/env python3
"""
24/08 (21) - continua il test sistematico di ingredienti sulle baseline
rimaste. Split BUY/SELL (l'ingrediente che ha promosso LIQ_SWEEP e
STRUCT_REACT) su tutte le altre 14 baseline del nucleo/cluster/altre
solide, stessa config SL/TP nota per ciascuna. Per ogni lato migliore
del simmetrico, stampate anche le date della finestra piu' vecchia (F0)
per lo stesso controllo anti-beta gia' applicato a LIQ_SWEEP - non ci si
ferma al conteggio.
"""
import sys, os
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
    ("FVG_CONT_V2", None, None),   # stop nativo
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


_CACHE = {}


def get_4h():
    if "4h" not in _CACHE:
        candles, src = bt._fetch_real("XAUUSD", "4h", 110000)
        ind = bt._prep(candles)
        _CACHE["4h"] = (candles, ind)
    return _CACHE["4h"]


def collect(name, sl_mult, tp_mult):
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
        if sl_mult is None:
            sl, tp = ind["fvg_v2_sl"][i], ind["fvg_v2_tp"][i]
            if sl is None or tp is None:
                continue
        else:
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
        out.append({"entry": entry, "risk_dist": rd, "raw_r": exit_r, "dir": sig,
                     "time": candles[i + 1]["time"]})
    return out


def net_series(trades, preset="retail_standard"):
    out = []
    for t in trades:
        cost = bt.scaled_cost_for_price(preset, t["entry"])
        cost_r = min((cost["spread_price"] + cost["slippage_price"]) / t["risk_dist"], bt.MAX_COST_R_PER_TRADE)
        out.append(t["raw_r"] - cost_r)
    return out


def main():
    findings = []
    for name, sl_m, tp_m in CANDIDATES:
        trades = collect(name, sl_m, tp_m)
        buys = [t for t in trades if t["dir"] == 1]
        sells = [t for t in trades if t["dir"] == -1]
        sym_net = net_series(trades)
        sym_pf = pf(sym_net)
        print(f"{name:26s} simmetrica n={len(trades):4d} PF={sym_pf:.2f}", flush=True)
        for label, group in (("BUY", buys), ("SELL", sells)):
            if len(group) < 25:
                print(f"    {label}: n={len(group)} troppo pochi trade", flush=True)
                continue
            net = net_series(group)
            wf = walk_forward(net)
            mid = len(net) // 2
            h1, h2 = net[:mid], net[mid:]
            gpf = pf(net)
            n_pos = sum(1 for _, p in (wf or []) if p >= 1.0) if wf else 0
            better = gpf > sym_pf * 1.1 and pf(h1) >= 1.0 and pf(h2) >= 1.0
            flag = "  <-- CANDIDATO (entrambe le meta' >=1)" if better else ""
            print(f"    {label}: n={len(group):4d} PF={gpf:.2f} m1={pf(h1):.2f} m2={pf(h2):.2f} "
                  f"win{n_pos}/{len(wf) if wf else 0}  primo={group[0]['time']}{flag}", flush=True)
            if better:
                findings.append((name, label, gpf, pf(h1), pf(h2), len(group), group[0]["time"]))

    print("\n=== Candidati con split BUY/SELL da approfondire (entrambe le meta' >=1) ===", flush=True)
    for f in findings:
        print(f"  {f[0]:26s} [{f[1]}] PF={f[2]:.2f} m1={f[3]:.2f} m2={f[4]:.2f} n={f[5]} primo_trade={f[6]}", flush=True)


if __name__ == "__main__":
    main()
