#!/usr/bin/env python3
"""
24/08 (5) - attacco diretto al problema di fondo, mai risolto da metà
agosto: dipendenza dal rally 2023-2026 (vedi vault "NEXUS EA - Riverifica
Walk-Forward 5 Finestre e Dipendenza da Regime 15-08" - windows 2020-11
-> 2023-10 genuinamente laterali, confermato indipendentemente dai costi;
regime_filter ADX non risolve; TF piu' bassi peggiorano; e "NEXUS EA -
Filtro di Regime e Portafoglio 5 Strategie 16-08" - Efficiency Ratio
migliora ma non chiude il divario, riconfermato oggi su Hull Suite/ML
Adaptive SuperTrend con la stessa identica firma).

Tre leve NUOVE (non ancora provate in nessuna nota precedente) testate
su SAR e MACD (4h, le due piu' solide e meglio caratterizzate del
nucleo), stesso storico Dukascopy reale, walk-forward 5 finestre, costi
scalati sul prezzo storico (retail/ECN):

1. BREAKEVEN sul "near-miss" - la diagnosi del 15/08 aveva trovato
   avg_loss_mfe_r=0.78 e near_miss_loss_pct=55.8% (piu' della meta' dei
   perdenti erano andati quasi al bersaglio prima di girare) ma non era
   mai stata testata una CORREZIONE, solo diagnosticato il meccanismo.
   Sweep di beR (0.5/0.7/1.0/1.5xR) - muove lo stop a breakeven una volta
   raggiunto quel multiplo di R favorevole.
2. FLOOR DI VOLATILITA' ASSOLUTA - il filtro ER (Efficiency Ratio) misura
   la FORMA del movimento (quanto e' diretto), non la sua AMPIEZZA
   assoluta. Ipotesi: un trend "efficiente" (ER alto) in un periodo a
   volatilita' assoluta bassa (es. 2020-2022) puo' comunque essere troppo
   piccolo perche' un target ATR-multiplo lo catturi prima che il rumore
   lo cancelli - aggiunge un secondo gate (percentile di ATR sulla sua
   distribuzione storica) ORTOGONALE al primo (forma vs ampiezza).
3. SOGLIA ER ADATTIVA (percentile mobile invece di soglia fissa 0.045) -
   la soglia fissa confronta ER di ere a volatilita' molto diversa con lo
   stesso numero assoluto; una soglia a percentile mobile (es. "sopra il
   60% della sua distribuzione nei precedenti N bar") si adatta alla
   baseline di ciascuna epoca invece di usare un unico righello globale.

Una variabile alla volta (P4.1 del roadmap: "ordine corretto, non
ottimizzare tutto insieme") - i tre blocchi sono esperimenti indipendenti,
non incrociati tra loro in questo script.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import backtest as bt

STRATS = ("SAR", "MACD")
LOOKBACK_ER = {"4h": 1000, "1h": 4000}
THR_ER = 0.045
MAX_HOLD = 200
SL_MULT, TP_MULT = 1.5, 4.0

_CACHE = {}


def get_data(tf):
    if tf not in _CACHE:
        candles, src = bt._fetch_real("XAUUSD", tf, 110000)
        ind = bt._prep(candles)
        _CACHE[tf] = (candles, ind)
    return _CACHE[tf]


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


def report(label, trades):
    print(f"--- {label}: {len(trades)} trade grezzi ---", flush=True)
    for preset in ("retail_standard", "ecn"):
        net = []
        for t in trades:
            cost = bt.scaled_cost_for_price(preset, t["entry"])
            cost_r = min((cost["spread_price"] + cost["slippage_price"]) / t["risk_dist"], bt.MAX_COST_R_PER_TRADE)
            net.append(t["raw_r"] - cost_r)
        wf = walk_forward(net)
        wf_str = " | ".join(f"{p:.2f}" for _, p in wf) if wf else "n/a"
        n_pos = sum(1 for _, p in (wf or []) if p >= 1.0)
        mid = len(net) // 2
        h1, h2 = net[:mid], net[mid:]
        print(f"  {preset:16s} aggPF={pf(net):.2f} sumR={sum(net):+7.1f} win>=1:{n_pos}/{len(wf) if wf else 0}"
              f"  meta1={pf(h1):.2f}/meta2={pf(h2):.2f}  [{wf_str}]", flush=True)


def simulate_exit(candles, i, sig, entry, sl0, tp, be_r):
    """be_r=0 -> nessun breakeven (comportamento base). be_r>0 -> una volta
    raggiunto be_r*risk_dist a favore, lo stop si sposta a breakeven (entry)."""
    rd = abs(entry - sl0)
    n = len(candles)
    sl = sl0
    be_trigger = entry + sig * be_r * rd if be_r > 0 else None
    be_moved = False
    for j in range(i + 2, min(i + 2 + MAX_HOLD, n)):
        hi, lo = candles[j]["high"], candles[j]["low"]
        if not be_moved and be_trigger is not None:
            reached = (hi >= be_trigger) if sig == 1 else (lo <= be_trigger)
            if reached:
                sl = entry
                be_moved = True
        if sig == 1:
            if lo <= sl:
                return (sl - entry) / rd
            elif hi >= tp:
                return (tp - entry) / rd
        else:
            if hi >= sl:
                return (entry - sl) / rd
            elif lo <= tp:
                return (entry - tp) / rd
    return None


def collect_base(tf, strat_name, be_r=0.0, filter_mode="fixed_er", pctl_thr=None, atr_pctl_floor=None):
    candles, ind = get_data(tf)
    closes, atr = ind["close"], ind["atr"]
    n = len(candles)
    lb_er = LOOKBACK_ER[tf]
    sig_fn = bt.STRATEGIES[strat_name]

    er_hist = []   # per filtro a percentile mobile
    atr_hist = []  # per floor di volatilita' assoluta
    trades = []
    for i in range(max(1500, lb_er + 50), n - 2):
        sig = sig_fn(candles, ind, i)
        a = atr[i]
        e = efficiency_ratio(closes, i, lb_er)
        if e is not None:
            er_hist.append(e)
        if a:
            atr_hist.append(a)
        if sig == 0 or e is None or not a:
            continue

        if filter_mode == "fixed_er":
            if e < THR_ER:
                continue
        elif filter_mode == "pctl_er":
            if len(er_hist) < 500:
                continue
            window = er_hist[-2000:]
            window_sorted = sorted(window)
            idx = int(pctl_thr * len(window_sorted))
            thr = window_sorted[min(idx, len(window_sorted) - 1)]
            if e < thr:
                continue
        elif filter_mode == "er_and_atrfloor":
            if e < THR_ER:
                continue
            if len(atr_hist) < 500:
                continue
            window = sorted(atr_hist[-2000:])
            idx = int(atr_pctl_floor * len(window))
            floor = window[min(idx, len(window) - 1)]
            if a < floor:
                continue
        else:
            raise ValueError(filter_mode)

        entry = candles[i + 1]["open"]
        sl0 = entry - sig * SL_MULT * a
        tp = entry + sig * TP_MULT * a
        rd = abs(entry - sl0)
        if rd <= 0:
            continue
        exit_r = simulate_exit(candles, i, sig, entry, sl0, tp, be_r)
        if exit_r is None:
            continue
        trades.append({"entry": entry, "risk_dist": rd, "raw_r": exit_r})
    return trades


def block1_breakeven():
    print("\n========== BLOCCO 1: breakeven sul near-miss ==========", flush=True)
    for strat in STRATS:
        for be_r in (0.0, 0.5, 0.7, 1.0, 1.5):
            trades = collect_base("4h", strat, be_r=be_r, filter_mode="fixed_er")
            report(f"{strat} 4h beR={be_r}", trades)


def block2_atr_floor():
    print("\n========== BLOCCO 2: floor di volatilita' assoluta (ER + ATR percentile) ==========", flush=True)
    for strat in STRATS:
        for floor_pctl in (0.0, 0.2, 0.3, 0.4, 0.5, 0.6):
            trades = collect_base("4h", strat, be_r=0.0, filter_mode="er_and_atrfloor", atr_pctl_floor=floor_pctl)
            report(f"{strat} 4h ER+ATR_floor_pctl={floor_pctl}", trades)


def block3_adaptive_er():
    print("\n========== BLOCCO 3: soglia ER adattiva (percentile mobile vs fissa) ==========", flush=True)
    for strat in STRATS:
        for pctl_thr in (0.5, 0.6, 0.7, 0.8):
            trades = collect_base("4h", strat, be_r=0.0, filter_mode="pctl_er", pctl_thr=pctl_thr)
            report(f"{strat} 4h ER_pctl_thr={pctl_thr}", trades)


def main():
    block1_breakeven()
    block2_atr_floor()
    block3_adaptive_er()


if __name__ == "__main__":
    main()
