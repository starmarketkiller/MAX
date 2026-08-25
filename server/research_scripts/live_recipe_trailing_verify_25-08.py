#!/usr/bin/env python3
"""
25/08 - verifica strategia-per-strategia del trailing sopra la RICETTA
LIVE REALE di ciascuna strategia (slMult/tpMult/htf/beR gia' in
NXS_StrategyProfiles.mqh, spesso frutto di una ricerca dedicata del
12/08 - non la mia ricetta semplificata ER+floor del 25/08). Lezione
di oggi (Z_SCORE_BREAKOUT): non si puo' copiare un numero trovato su
una ricetta diversa - va rifatto il test sulla ricetta VERA, con TP
fisso ancora attivo, gate HTF (EMA200 sul TF della strategia) e
breakeven dove presenti.

Nessun filtro ER qui: il motore live NON applica il mio filtro ER di
ricerca a queste strategie profilate (quello era solo nella pipeline
Python del 25/08) - questa e' la ricetta ESATTA che gira oggi.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import backtest as bt

MAX_HOLD = 400  # barre, generoso per D1/H4

# name: (tf, sl_mult, tp_mult, htf, beR, trailK_attuale)
LIVE_PROFILES = {
    "ADX_RSI":        ("1d", 1.0, 10.0, True,  1.5, 2.5),
    "SAR":            ("4h", 1.0, 6.0,  False, 0.0, 2.5),
    "MACD":           ("4h", 2.0, 8.0,  True,  1.0, 1.5),
    "FVG_CONT":       ("4h", 1.5, 6.0,  True,  1.5, 2.5),
    "FVG_MIT":        ("4h", 1.5, 4.5,  True,  0.0, 2.5),
    "EMA_PULLBACK":   ("1h", 1.5, 4.0,  True,  0.0, 1.5),
    "OTE_CONT":       ("1d", 2.0, 4.5,  True,  0.0, 2.5),
    "TSI":            ("1d", 2.0, 6.0,  True,  1.0, 2.0),
    "TURTLE_SOUP":    ("1h", 1.0, 4.5,  True,  0.0, 2.5),
    "MALAYSIAN_SNR":  ("1d", 2.0, 4.5,  True,  0.0, 1.5),
    "RSI_DIV":        ("1h", 1.0, 4.5,  False, 0.0, 1.5),
    "BOLLINGER":      ("1d", 1.0, 4.5,  False, 0.0, 1.5),
    "BREAKOUT_ACC":   ("1d", 1.0, 4.5,  True,  0.0, 2.5),
    "AMD_CONT":       ("30m",1.5, 3.0,  False, 0.0, 0.0),
    "LDN_REVERSAL":   ("15m",1.5, 3.0,  False, 0.0, 0.0),
}
ACT_K = 1.0  # InpAtrTrailActivateATR globale (default motore live)


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
    return (f"{label:26s} n={len(trades):4d} PF={pf(net):.2f} "
            f"(m1={pf(net[:mid]):.2f}/m2={pf(net[mid:]):.2f}) win={n_pos}/{len(wf) if wf else 0}")


_CACHE = {}


def get_data(tf):
    if tf not in _CACHE:
        bars = 4000 if tf == "1d" else 110000
        candles, src = bt._fetch_real("XAUUSD", tf, bars)
        ind = bt._prep(candles)
        ema200 = bt.ema_series(ind["close"], 200)
        _CACHE[tf] = (candles, ind, ema200)
    return _CACHE[tf]


def simulate(name, tf, sl_mult, tp_mult, htf, beR, trail_k, act_k=ACT_K):
    candles, ind, ema200 = get_data(tf)
    atr, closes = ind["atr"], ind["close"]
    n = len(candles)
    sig_fn = bt.STRATEGIES[name]
    out = []
    start = 250
    for i in range(start, n - 2):
        a = atr[i]
        if not a:
            continue
        sig = sig_fn(candles, ind, i)
        if sig == 0:
            continue
        if htf and ema200[i] and ema200[i] > 0:
            px = closes[i]
            if (sig == 1 and px < ema200[i]) or (sig == -1 and px > ema200[i]):
                continue
        entry = candles[i + 1]["open"]
        rd = sl_mult * a
        sl = entry - sig * rd
        tp = entry + sig * tp_mult * a
        extreme = entry
        beActive = False
        exit_r = None
        for j in range(i + 2, min(i + 2 + MAX_HOLD, n)):
            hi, lo = candles[j]["high"], candles[j]["low"]
            if sig == 1:
                if lo <= sl: exit_r = (sl - entry) / rd; break
                if hi >= tp: exit_r = (tp - entry) / rd; break
                # breakeven: una volta raggiunto beR*rd di profitto, SL->entry
                if beR > 0 and not beActive and hi - entry >= beR * rd:
                    beActive = True
                    if entry > sl: sl = entry
                # trailing: attiva dopo act_k*ATR di profitto, non allenta mai
                if trail_k > 0 and hi - entry >= act_k * a:
                    extreme = max(extreme, hi)
                    ns = extreme - trail_k * a
                    if ns > sl: sl = ns
            else:
                if hi >= sl: exit_r = (entry - sl) / rd; break
                if lo <= tp: exit_r = (entry - tp) / rd; break
                if beR > 0 and not beActive and entry - lo >= beR * rd:
                    beActive = True
                    if entry < sl: sl = entry
                if trail_k > 0 and entry - lo >= act_k * a:
                    extreme = min(extreme, lo)
                    ns = extreme + trail_k * a
                    if ns < sl: sl = ns
        if exit_r is None:
            continue
        out.append({"entry": entry, "risk_dist": rd, "raw_r": exit_r})
    return out


def main():
    for name, (tf, sl_m, tp_m, htf, beR, trailK_now) in LIVE_PROFILES.items():
        print(f"=== {name} (TF={tf} SL={sl_m} TP={tp_m} HTF={htf} beR={beR}) ===", flush=True)
        base = simulate(name, tf, sl_m, tp_m, htf, beR, 0.0)
        print(fmt(f"  fisso (trail=OFF)", base), flush=True)
        cur = simulate(name, tf, sl_m, tp_m, htf, beR, trailK_now)
        print(fmt(f"  trail={trailK_now} (ATTUALE live)", cur), flush=True)
        for tk in (1.5, 2.0, 2.5, 3.0):
            if abs(tk - trailK_now) < 1e-9:
                continue
            trades = simulate(name, tf, sl_m, tp_m, htf, beR, tk)
            print(fmt(f"  trail={tk}", trades), flush=True)
        print(flush=True)


if __name__ == "__main__":
    main()
