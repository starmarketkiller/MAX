#!/usr/bin/env python3
"""
24/08 (10) - richiesta esplicita dell'utente: lo stop ATR fisso/nativo su
4h potrebbe semplicemente non essere il tipo di GESTIONE giusto per
alcune strategie, non un problema del segnale in se'. Ingrediente MAI
provato oggi (tutto era stop iniziale fisso + target fisso, anche il
floor ATR e la griglia SL/TP restano nella stessa famiglia): un
TRAILING STOP (chandelier - stop iniziale 1.5xATR, poi segue l'estremo
favorevole a distanza trail_mult*ATR, mai un target fisso) su tutte le
strategie ancora deboli dopo fase 1/2 di baseline_expansion_24-08.py.

Ipotesi: alcune strategie hanno una direzione spesso corretta ma un
target ATR-fisso le taglia troppo presto (o troppo tardi) - lasciare che
il prezzo decida quando finisce il movimento invece di un multiplo
arbitrario potrebbe rivelare edge nascosto. Stessa base ER+floor per
isolare l'unica variabile nuova (il TIPO di uscita), non il segnale.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import backtest as bt

LOOKBACK_ER = {"4h": 1000, "1h": 4000}
THR_ER = 0.045
FLOOR_PCTL = 0.3
MAX_HOLD = 200
INIT_SL_MULT = 1.5

CANDIDATES = ["BJORGUM", "RSI_DIV", "FVG_MIT", "LDN_REVERSAL", "TSI_EXTREME",
              "ICHIMOKU", "BOLLINGER", "STRUCT_REACT", "LIQ_SWEEP",
              "SH_BMS_RTO_V2", "FVG_MIT_WINDOW"]
TRAIL_MULTS = [2.0, 2.5, 3.0]


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


def simulate_trailing(candles, i, sig, entry, atr_val, trail_mult):
    rd = INIT_SL_MULT * atr_val
    sl = entry - sig * rd
    extreme = entry
    n = len(candles)
    for j in range(i + 2, min(i + 2 + MAX_HOLD, n)):
        hi, lo = candles[j]["high"], candles[j]["low"]
        if sig == 1:
            if lo <= sl:
                return (sl - entry) / rd
            extreme = max(extreme, hi)
            new_sl = extreme - trail_mult * atr_val
            if new_sl > sl:
                sl = new_sl
        else:
            if hi >= sl:
                return (entry - sl) / rd
            extreme = min(extreme, lo)
            new_sl = extreme + trail_mult * atr_val
            if new_sl < sl:
                sl = new_sl
    j_last = min(i + 1 + MAX_HOLD, n - 1)
    last_close = candles[j_last]["close"]
    return (last_close - entry) / rd if sig == 1 else (entry - last_close) / rd


def collect_trailing(name, trail_mult, candles, ind, atr, closes, lb_er):
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
        exit_r = simulate_trailing(candles, i, sig, entry, a, trail_mult)
        trades.append({"entry": entry, "risk_dist": INIT_SL_MULT * a, "raw_r": exit_r})
    return trades


def main():
    for tf in ("4h",):
        candles, src = bt._fetch_real("XAUUSD", tf, 110000)
        ind = bt._prep(candles)
        atr, closes = ind["atr"], ind["close"]
        lb_er = LOOKBACK_ER[tf]
        for name in CANDIDATES:
            best = None
            for tm in TRAIL_MULTS:
                trades = collect_trailing(name, tm, candles, ind, atr, closes, lb_er)
                if trades is None or len(trades) < 30:
                    continue
                s = summarize(trades)
                score = s["retail_standard"]["pf"]
                if best is None or score > best[0]:
                    best = (score, tm, len(trades), s)
            if best is None:
                print(f"{name:34s} [{tf}] nessuna trail_mult con campione sufficiente", flush=True)
                continue
            score, tm, n, s = best
            flag = "  <-- CANDIDATO" if (s["retail_standard"]["pf"] >= 1.0 or s["ecn"]["pf"] >= 1.20) else ""
            print(fmt(f"{name} trail={tm}xATR", tf, n, s) + flag, flush=True)


if __name__ == "__main__":
    main()
