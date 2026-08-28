#!/usr/bin/env python3
"""
24/08 (23) - richiesta esplicita dell'utente: riscrivere le SCALP_* per
un edge reale, cercando anche online. Ricerca (fonti in fondo, per lo
piu' blog/marketing non backtest rigorosi - i numeri di win-rate citati
NON sono presi per buoni, solo il meccanismo strutturale): il tema che
ricorre ovunque, anche in fonti indipendenti tra loro, e' l'overlap
London-New York (12:00-16:00 UTC) come finestra di liquidita' massima
per l'oro - spread piu' stretti, volume piu' alto, "una strategia di
breakout che funziona nell'overlap si comporta diversamente in sessione
asiatica" (mql5.com). Ingrediente MAI provato oggi: ho testato
"uscita a fine giornata" ieri sera, MAI "ingresso ristretto alla
finestra di overlap" - un vincolo diverso, sulla FONTE del segnale non
sulla sua gestione.

Combinato con la lezione di oggi (ER lungo=contraddizione di scala,
target troppo stretto=costi dominanti): niente filtro ER, SL/TP
moderati (non 0.5/1.0 che aveva incendiato i costi, non 1.0/3.0+ che
aveva reso il campione troppo esile ieri) - griglia 0.75/1.5-2.5xATR.

Fonti (contenuto per lo piu' promozionale, meccanismo strutturale
plausibile e indipendentemente confermato, numeri non verificati):
- https://www.mql5.com/en/blogs/post/770488
- https://fxnx.com/en/blog/session-session-scalping-your-precision-guide
- https://zayecapitalmarkets.com/london-new-york-overlap-session-2/
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import backtest as bt

SCALP_NAMES = ["SCALP_BB_FADE", "SCALP_EMA", "SCALP_RANGE_BRK", "SCALP_RSI_SNAP"]
OVERLAP_START_H, OVERLAP_END_H = 12, 16  # UTC, London-NY overlap
SLTP_GRID = [(0.75, 1.5), (0.75, 2.25), (1.0, 2.0), (1.0, 2.5)]
MAX_HOLD_BARS = 200


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


def collect(name, sl_mult, tp_mult, candles, ind, atr, restrict_overlap):
    sig_fn = bt.STRATEGIES[name]
    n = len(candles)
    trades = []
    for i in range(300, n - 2):
        a = atr[i]
        if not a:
            continue
        sig = sig_fn(candles, ind, i)
        if sig == 0:
            continue
        if restrict_overlap:
            hh = int(candles[i + 1]["time"].split(" ")[1].split(":")[0])
            if not (OVERLAP_START_H <= hh < OVERLAP_END_H):
                continue
        entry = candles[i + 1]["open"]
        sl = entry - sig * sl_mult * a
        tp = entry + sig * tp_mult * a
        rd = abs(entry - sl)
        if rd <= 0:
            continue
        exit_r = None
        for j in range(i + 2, min(i + 2 + MAX_HOLD_BARS, n)):
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
    candles, src = bt._fetch_real("XAUUSD", "15m", 110000)
    ind = bt._prep(candles)
    atr = ind["atr"]
    print(f"M15: {len(candles)} candele ({src})", flush=True)

    for name in SCALP_NAMES:
        print(f"\n--- {name} ---", flush=True)
        best_no, best_ov = None, None
        for sl_m, tp_m in SLTP_GRID:
            t_no = collect(name, sl_m, tp_m, candles, ind, atr, False)
            t_ov = collect(name, sl_m, tp_m, candles, ind, atr, True)
            if len(t_no) >= 30:
                s = summarize(t_no)
                if best_no is None or s["retail_standard"]["pf"] > best_no[0]:
                    best_no = (s["retail_standard"]["pf"], sl_m, tp_m, len(t_no), s)
            if len(t_ov) >= 30:
                s = summarize(t_ov)
                if best_ov is None or s["retail_standard"]["pf"] > best_ov[0]:
                    best_ov = (s["retail_standard"]["pf"], sl_m, tp_m, len(t_ov), s)
        if best_no:
            score, sl_m, tp_m, n, s = best_no
            print(fmt(f"tutte le ore, SL{sl_m}/TP{tp_m}", "24h", n, s), flush=True)
        else:
            print("  tutte le ore: nessuna combinazione sufficiente", flush=True)
        if best_ov:
            score, sl_m, tp_m, n, s = best_ov
            flag = "  <-- CANDIDATO" if (s["retail_standard"]["pf"] >= 1.0 or s["ecn"]["pf"] >= 1.20) else ""
            print(fmt(f"SOLO overlap 12-16 UTC, SL{sl_m}/TP{tp_m}", "overlap", n, s) + flag, flush=True)
        else:
            print("  solo overlap: nessuna combinazione sufficiente", flush=True)


if __name__ == "__main__":
    main()
