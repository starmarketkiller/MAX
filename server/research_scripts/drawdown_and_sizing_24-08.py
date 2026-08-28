#!/usr/bin/env python3
"""
24/08 (25) - due domande dirette dell'utente:
1. Qual e' il drawdown massimo PER STRATEGIA (non solo a livello di
   portafoglio, gia' calcolato il 24/08 prima)?
2. Ha senso aumentare la size quando una strategia e' in drawdown
   CONTENUTO (non profondo), come leva di rischio distinta dal bucket a
   slot condivisi? E perche' lo stesso meccanismo non salverebbe le
   SCALP_*?

Metodo per il DD: curva equity in R (rischio fisso 1R per trade,
sequenziale nell'ordine cronologico reale dei trade della strategia -
non il portafoglio condiviso), drawdown massimo dal picco.

Metodo per il test di sizing: quando l'equity e' entro X% dal picco
(drawdown "contenuto"), il prossimo trade rischia size_mult x R invece
di 1x R; quando il drawdown supera X%, resta a 1x (o si riduce - qui
testato solo l'aumento, la domanda specifica dell'utente). Confrontato
con size fissa 1x su STRUCT_REACT/LIQ_SWEEP (buone, PF>1) e su
SCALP_RANGE_BRK al suo config migliore (PF<1) per mostrare perche' la
leva NON puo' aiutare li'.
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


def max_drawdown_r(net_r_series):
    equity = 0.0
    peak = 0.0
    max_dd = 0.0
    for r in net_r_series:
        equity += r
        peak = max(peak, equity)
        dd = peak - equity
        max_dd = max(max_dd, dd)
    return max_dd, equity


def collect_generic(name, sl_mult, tp_mult, tf, buy_only=False):
    candles, src = bt._fetch_real("XAUUSD", tf, 110000)
    ind = bt._prep(candles)
    atr, closes = ind["atr"], ind["close"]
    n = len(candles)
    lb_er = 1000 if tf == "4h" else 4000
    sig_fn = bt.STRATEGIES[name]
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
        out.append({"entry": entry, "risk_dist": rd, "raw_r": exit_r})
    return out


def net_series(trades, preset="retail_standard"):
    out = []
    for t in trades:
        cost = bt.scaled_cost_for_price(preset, t["entry"])
        cost_r = min((cost["spread_price"] + cost["slippage_price"]) / t["risk_dist"], bt.MAX_COST_R_PER_TRADE)
        out.append(t["raw_r"] - cost_r)
    return out


def simulate_dd_scaled_sizing(net_r, contained_dd_r, size_mult):
    """Size normale (1R) di default; se il drawdown corrente dal picco (in
    R) e' SOTTO contained_dd_r (drawdown poco profondo), il PROSSIMO trade
    rischia size_mult x R invece di 1x."""
    equity = 0.0
    peak = 0.0
    max_dd = 0.0
    for r in net_r:
        cur_dd = peak - equity
        mult = size_mult if cur_dd < contained_dd_r else 1.0
        equity += r * mult
        peak = max(peak, equity)
        max_dd = max(max_dd, peak - equity)
    return equity, max_dd


def report_dd(name_label, trades):
    for preset in ("retail_standard", "ecn"):
        net = net_series(trades, preset)
        dd, final = max_drawdown_r(net)
        print(f"  {name_label:34s} [{preset:16s}] n={len(trades):4d} PF={pf(net):.2f} "
              f"sumR={final:+7.1f} maxDD={dd:5.1f}R", flush=True)


def main():
    print("=== Drawdown massimo per strategia (in R, size fissa 1x) ===", flush=True)
    configs = [
        ("STRUCT_REACT (BUY-only)", "STRUCT_REACT", 2.0, 6.0, "4h", True),
        ("LIQ_SWEEP (BUY-only)", "LIQ_SWEEP", 1.5, 6.0, "4h", True),
        ("ADX_RSI (BUY-only)", "ADX_RSI", 1.5, 4.0, "4h", True),
        ("SAR (BUY-only)", "SAR", 1.5, 4.0, "4h", True),
        ("DONCHIAN_TURTLE (BUY-only)", "DONCHIAN_TURTLE", 1.5, 4.0, "4h", True),
    ]
    cache = {}
    for label, name, sl_m, tp_m, tf, buy_only in configs:
        trades = collect_generic(name, sl_m, tp_m, tf, buy_only)
        cache[label] = trades
        report_dd(label, trades)

    print("\n=== Test: aumentare la size quando il drawdown e' CONTENUTO (buone strategie) ===", flush=True)
    for label in ("STRUCT_REACT (BUY-only)", "LIQ_SWEEP (BUY-only)"):
        trades = cache[label]
        net = net_series(trades, "retail_standard")
        dd_base, final_base = max_drawdown_r(net)
        print(f"  {label} baseline 1x: finale={final_base:+.1f}R maxDD={dd_base:.1f}R", flush=True)
        for contained, mult in [(3.0, 1.5), (3.0, 2.0), (5.0, 1.5)]:
            final, dd = simulate_dd_scaled_sizing(net, contained, mult)
            print(f"    +{mult}x quando DD<{contained}R: finale={final:+.1f}R maxDD={dd:.1f}R", flush=True)

    print("\n=== Stesso test su una SCALP (PF<1, per capire perche' non aiuta) ===", flush=True)
    # riuso la config migliore trovata ieri: SCALP_RANGE_BRK SL4.0/TP8.0 overlap
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import importlib.util
    spec = importlib.util.spec_from_file_location("sr", os.path.join(os.path.dirname(os.path.abspath(__file__)), "scalp_session_rewrite_24-08.py"))
    sr = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(sr)
    candles, src = bt._fetch_real("XAUUSD", "15m", 110000)
    ind = bt._prep(candles)
    atr = ind["atr"]
    scalp_trades = sr.collect("SCALP_RANGE_BRK", 4.0, 8.0, candles, ind, atr, True)
    net = []
    for t in scalp_trades:
        cost = bt.scaled_cost_for_price("retail_standard", t["entry"])
        cost_r = min((cost["spread_price"] + cost["slippage_price"]) / t["risk_dist"], bt.MAX_COST_R_PER_TRADE)
        net.append(t["raw_r"] - cost_r)
    dd_base, final_base = max_drawdown_r(net)
    print(f"  SCALP_RANGE_BRK baseline 1x: n={len(net)} PF={pf(net):.2f} finale={final_base:+.1f}R maxDD={dd_base:.1f}R", flush=True)
    for contained, mult in [(3.0, 1.5), (3.0, 2.0), (5.0, 1.5)]:
        final, dd = simulate_dd_scaled_sizing(net, contained, mult)
        print(f"    +{mult}x quando DD<{contained}R: finale={final:+.1f}R maxDD={dd:.1f}R", flush=True)


if __name__ == "__main__":
    main()
