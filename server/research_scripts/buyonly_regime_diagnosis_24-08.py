#!/usr/bin/env python3
"""
24/08 (13) - obiezione dell'utente, metodologicamente corretta: BUY-only
profittevole in un dataset a maggioranza rialzista (oro 2019-2026) puo'
essere solo beta direzionale (compra e tieni durante un rally), non un
edge di segnale genuino - se il lato SELL non ha ALCUNA qualita' anche
nei periodi non rialzisti, allora "BUY-only" non e' interessante, e'
solo "l'oro sale".

Test diretto (non assunto): guardo il PF per-finestra CON LE DATE di
inizio/fine di ciascuna finestra, e lo confronto con la classificazione
di regime gia' fatta il 15/08 (vedi [[NEXUS EA - Riverifica Walk-Forward
5 Finestre e Dipendenza da Regime (15-08)]]):
  F0 2019-03->2020-11: +44% (include crash COVID, non solo rialzo pulito)
  F1 2020-11->2022-04: +4.4% - LATERALE
  F2 2022-04->2023-10: +1.2% - LATERALE
  F3 2023-10->2025-03: +47.5% - rally
  F4 2025-03->2026-08: +49.9% - rally

Se BUY-only regge (PF>=1) anche nelle finestre LATERALI (F1/F2, quasi 3
anni dove l'oro non e' salito in modo significativo), e' un segnale reale
che funziona indipendentemente dal regime rialzista. Se BUY-only vive
SOLO nelle finestre di rally (F0/F3/F4) e crolla in F1/F2, e' beta
direzionale mascherato da "strategia" - esattamente il sospetto
dell'utente, da confermare o smentire con i numeri, non con l'intuizione.

Confronto diretto anche con il lato SELL nelle stesse finestre laterali:
se il SELL e' relativamente MENO peggio (anche se non profittevole) nelle
finestre laterali che in quelle di rally, e' un indizio di logica
bidirezionale genuina soffocata dal regime, non un segnale rotto sul lato
short.
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


def collect(name, sl_mult, tp_mult, candles, ind, atr, closes, lb_er):
    sig_fn = bt.STRATEGIES[name]
    n = len(candles)
    atr_hist, trades = [], []
    for i in range(max(300, lb_er + 50), n - 2):
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
        trades.append({"entry": entry, "risk_dist": rd, "raw_r": exit_r, "dir": sig,
                        "time": candles[i + 1]["time"]})
    return trades


def diagnose(name, sl_m, tp_m, candles, ind, atr, closes, lb_er):
    trades = collect(name, sl_m, tp_m, candles, ind, atr, closes, lb_er)
    buys = [t for t in trades if t["dir"] == 1]
    sells = [t for t in trades if t["dir"] == -1]
    print(f"\n=== {name} SL{sl_m}/TP{tp_m} — BUY n={len(buys)}, SELL n={len(sells)} ===", flush=True)
    for label, group in (("BUY", buys), ("SELL", sells)):
        if len(group) < 15:
            print(f"  {label}: campione troppo sottile ({len(group)})", flush=True)
            continue
        # 5 finestre EQUAL-COUNT (stessa convenzione di tutto il giorno),
        # ma qui stampo anche la data di inizio/fine di ciascuna per
        # poterla confrontare con la classificazione di regime del 15/08
        nw = 5
        size = len(group) // nw
        print(f"  {label} (n={len(group)}):", flush=True)
        for w in range(nw):
            seg = group[w * size:(w + 1) * size] if w < nw - 1 else group[w * size:]
            net = []
            for t in seg:
                cost = bt.scaled_cost_for_price("retail_standard", t["entry"])
                cost_r = min((cost["spread_price"] + cost["slippage_price"]) / t["risk_dist"], bt.MAX_COST_R_PER_TRADE)
                net.append(t["raw_r"] - cost_r)
            d0, d1 = seg[0]["time"], seg[-1]["time"]
            print(f"    F{w}: {d0} -> {d1}  n={len(seg):4d}  PF={pf(net):.2f}", flush=True)


def main():
    candles, src = bt._fetch_real("XAUUSD", "4h", 110000)
    ind = bt._prep(candles)
    atr, closes = ind["atr"], ind["close"]
    for name, sl_m, tp_m in [("BOLLINGER", 1.0, 6.0), ("STRUCT_REACT", 2.0, 6.0),
                              ("BJORGUM", 1.5, 6.0), ("ICHIMOKU", 1.0, 4.5)]:
        diagnose(name, sl_m, tp_m, candles, ind, atr, closes, 1000)


if __name__ == "__main__":
    main()
