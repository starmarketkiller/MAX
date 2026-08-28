#!/usr/bin/env python3
"""
24/08 (7) - richiesta esplicita dell'utente: prima di continuare a
raffinare le 4 già solide (SAR/MACD/FVG_CONT/Z_SCORE_BREAKOUT), trovare
baseline per QUANTE PIÙ strategie possibile nel catalogo esistente (67 in
bt.STRATEGIES), usando la ricetta migliore nota oggi (ER≥0.045 + floor
ATR al 30° percentile mobile, la scoperta di
rally_dependency_attack_24-08.py) invece delle ricette più vecchie con
cui molte erano state bocciate.

Non è un test "meno ovvio" (quello viene dopo, promesso all'utente):
è uno screening a ricetta UNIFORME (stop ATR generico 1.5/4.0, come le
strategie senza stop nativo) su tutto il catalogo compatibile con la
firma (c, ind, i) - esclude le famiglie con stop strutturale proprio
(CRT/TURTLE_SOUP/SH_BMS_RTO/sweep - già testate a fondo con il LORO stop
nativo il 16-17/08, la ricetta generica qui le sottostimerebbe e non
aggiungerebbe informazione) e le SCALP_* (scala M15/M30 diversa, TF non
comparabile a 4h/1h). Obiettivo: individuare candidati con un raw PF
decente su un campione vero, da passare poi alla verifica due-metà-storia
prima di promuoverli - un primo filtro grezzo, non un verdetto finale.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import backtest as bt

LOOKBACK_ER = {"4h": 1000, "1h": 4000}
THR_ER = 0.045
FLOOR_PCTL = 0.3
MAX_HOLD = 200
SL_MULT, TP_MULT = 1.5, 4.0

# Famiglie con stop strutturale proprio, già testate a fondo con il loro
# stop nativo (16-17/08) - uno stop ATR generico qui le sottostimerebbe,
# non e' un test onesto per queste. Escluse esplicitamente, non per pigrizia.
NATIVE_STOP_FAMILY = {
    "CRT", "CRT_MINSTOP_FILTER", "TURTLE_SOUP", "TURTLE_SOUP_CHOCH",
    "TURTLE_SOUP_CHOCH_NEAR", "TURTLE_SOUP_CHOCH_DBLBODY", "CISD_TRUE",
    "THREE_BAR_DELIVERY_BREAK", "SH_BMS_RTO", "SH_BMS_RTO_V2", "SMS_BMS_RTO",
    "SMS_BMS_RTO_CHOCH_WINDOW", "OTE_CONT_V2", "ORDER_BLOCK_V2", "FVG_CONT_V2",
    "FVG_MIT_WINDOW", "NY_REVERSAL_CHOCH_WINDOW", "IFVG_CHOCH_WINDOW",
    "SILVER_BULLET_V2", "MALAYSIAN_SNR_V2_RETEST", "MALAYSIAN_SNR_V2_RETEST_OUTRANGE",
    "MALAYSIAN_SNR_V2_STAGE1", "MALAYSIAN_SNR_V2_STAGE3",
}
SCALP_FAMILY = {"SCALP_BB_FADE", "SCALP_EMA", "SCALP_RANGE_BRK", "SCALP_RSI_SNAP"}
ALREADY_KNOWN_GOOD_OR_PORTED = {"SAR", "MACD", "FVG_CONT", "Z_SCORE_BREAKOUT", "LONDON_BO"}

SKIP = NATIVE_STOP_FAMILY | SCALP_FAMILY | ALREADY_KNOWN_GOOD_OR_PORTED

CANDIDATES = sorted(set(bt.STRATEGIES.keys()) - SKIP)


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


def run_strategy(name, candles, ind, atr, closes, lb_er):
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
            return None  # firma incompatibile o richiede argomenti extra - salta
        if sig == 0 or not a:
            continue
        e = efficiency_ratio(closes, i, lb_er)
        if e is None or e < THR_ER:
            continue
        if len(atr_hist) < 500:
            continue
        w = sorted(atr_hist[-2000:])
        floor = w[min(int(FLOOR_PCTL * len(w)), len(w) - 1)]
        if a < floor:
            continue
        entry = candles[i + 1]["open"]
        sl = entry - sig * SL_MULT * a
        tp = entry + sig * TP_MULT * a
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


def main():
    results = []
    for tf in ("4h", "1h"):
        candles, src = bt._fetch_real("XAUUSD", tf, 110000)
        ind = bt._prep(candles)
        atr, closes = ind["atr"], ind["close"]
        lb_er = LOOKBACK_ER[tf]
        print(f"\n### TF={tf} ({len(candles)} candele, {src}) ###", flush=True)
        for name in CANDIDATES:
            trades = run_strategy(name, candles, ind, atr, closes, lb_er)
            if trades is None:
                print(f"{name:32s} [{tf}] SALTATA (firma incompatibile)", flush=True)
                continue
            if len(trades) < 30:
                print(f"{name:32s} [{tf}] n={len(trades):4d} -> troppo pochi trade, salto", flush=True)
                continue
            row = {"name": name, "tf": tf, "n": len(trades)}
            for preset in ("retail_standard", "ecn"):
                net = []
                for t in trades:
                    cost = bt.scaled_cost_for_price(preset, t["entry"])
                    cost_r = min((cost["spread_price"] + cost["slippage_price"]) / t["risk_dist"], bt.MAX_COST_R_PER_TRADE)
                    net.append(t["raw_r"] - cost_r)
                wf = walk_forward(net)
                n_pos = sum(1 for _, p in (wf or []) if p >= 1.0)
                row[preset] = {"pf": pf(net), "sumR": sum(net), "win": n_pos, "nw": len(wf) if wf else 0}
            results.append(row)
            flag = ""
            if row["retail_standard"]["pf"] >= 1.0 or row["ecn"]["pf"] >= 1.20:
                flag = "  <-- CANDIDATO"
            print(f"{name:32s} [{tf}] n={len(trades):4d}  "
                  f"retail PF={row['retail_standard']['pf']:.2f} win{row['retail_standard']['win']}/{row['retail_standard']['nw']}  "
                  f"ECN PF={row['ecn']['pf']:.2f} win{row['ecn']['win']}/{row['ecn']['nw']}{flag}", flush=True)

    print("\n=== RIEPILOGO CANDIDATI (retail PF>=1.0 o ECN PF>=1.20, n>=30) ===", flush=True)
    cands = [r for r in results if r["retail_standard"]["pf"] >= 1.0 or r["ecn"]["pf"] >= 1.20]
    cands.sort(key=lambda r: -r["ecn"]["pf"])
    for r in cands:
        print(f"{r['name']:32s} [{r['tf']}] n={r['n']:4d}  "
              f"retail PF={r['retail_standard']['pf']:.2f} win{r['retail_standard']['win']}/{r['retail_standard']['nw']}  "
              f"ECN PF={r['ecn']['pf']:.2f} win{r['ecn']['win']}/{r['ecn']['nw']}", flush=True)


if __name__ == "__main__":
    main()
