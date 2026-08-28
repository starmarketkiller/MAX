#!/usr/bin/env python3
"""25/08 - CRT: perche' "ci sfugge qualcosa"? Riletto il codice live
(NXS_Strat_CRT, NXS_Strategies_SMC.mqh) e la storia gia' scritta:
- Il pattern e' walk-forward validato (5/5 finestre, ~20k trade) SENZA
  costi - il commento nel codice lo chiama "la scoperta piu' solida
  della sessione" all'11/08.
- Escluso dal registro il 25/08 perche' "costi-dominanti mai risolta":
  lo stop e' ancorato al wick della candela di sweep (spesso minuscolo),
  quindi il costo fisso (spread+slippage) diventa enorme in termini di R.
- Un tentativo di variante scalp (crt_h4range_m5confirm_24-08.py, ieri)
  ha peggiorato le cose: senza il vincolo implicito "una entrata per
  periodo" del CRT classico (3 candele fisse), il motore ha generato
  migliaia di trade quasi identici a rischio minimo (risk_dist mediano
  $1.22) - il floor 0.3xATR scartava il 93% dei trade e i superstiti
  restavano comunque negativi.

Qui si torna al pattern CLASSICO (3 candele consecutive sulla STESSA
TF, fedele a NXS_Strat_CRT) e si separano le DUE variabili che possono
risolvere il cost-dominance in modi diversi:
  (A) TIMEFRAME: scalp (M5/M15) vs nativo (M30) vs largo (H1/H4/D1) -
      un wick su un TF piu' alto e' naturalmente piu' largo in dollari,
      diluendo il costo fisso senza toccare la logica del pattern.
  (B) MECCANISMO DELLO STOP: nativo (ancorato al wick, con floor
      0.3xATR "widen" come nel vero EA) vs stop fisso ad ATR (1.0xATR,
      target RR=2.0) - stacca lo stop dal wick del tutto.

Nota metodologica: qui l'entrata e' all'APERTURA della barra
immediatamente dopo lo sweep (fedele a come esegue davvero l'EA live -
SymbolInfoDouble al momento della valutazione, che accade al primo tick
dopo la chiusura della barra di sweep). La validazione Python esistente
(_crt_series in backtest.py) esegue invece alla CHIUSURA di quella
stessa barra (un'intera barra di ritardo in piu') - una differenza di
convenzione mai isolata prima, qui usata quella piu' fedele al vivo.
"""
import sys, os, json, bisect
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import backtest as bt

RR_FIXED = 2.0
ATR_STOP_MULT = 1.0
MIN_STOP_ATR = 0.3   # floor nativo (widen), come InpCRT_MinStopATR


def load_m5():
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..",
                         "data_cache_m5", "dukascopy_xauusd_m5.json")
    with open(path, encoding="utf-8") as f:
        return json.load(f)


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
    rd = [t["risk_dist"] for t in trades]
    rd_med = sorted(rd)[len(rd) // 2] if rd else 0.0
    return (f"{label:34s} n={len(trades):5d} PF={pf(net):.2f} "
            f"(m1={pf(net[:mid]):.2f}/m2={pf(net[mid:]):.2f}) win={n_pos}/{len(wf) if wf else 0} "
            f"medRiskDist=${rd_med:.2f}")


def run_crt(candles, atr, stop_mode, max_hold):
    """stop_mode: 'native' (wick + floor widen) o 'atr_fixed' (1.0xATR, RR=2.0)."""
    n = len(candles)
    highs = [c["high"] for c in candles]
    lows = [c["low"] for c in candles]
    closes = [c["close"] for c in candles]
    out = []
    for i in range(2, n - 1):
        crh, crl = highs[i - 2], lows[i - 2]
        sweepHi, sweepLo, sweepC = highs[i - 1], lows[i - 1], closes[i - 1]
        sweptHigh = sweepHi > crh and sweepC <= crh
        sweptLow = sweepLo < crl and sweepC >= crl
        if sweptHigh and not sweptLow:
            sig = -1
            native_sl = sweepHi
        elif sweptLow and not sweptHigh:
            sig = 1
            native_sl = sweepLo
        else:
            continue
        a = atr[i]
        entry = candles[i]["open"]
        if stop_mode == "native":
            sl = native_sl
            cur_dist = abs(entry - sl)
            if a and MIN_STOP_ATR > 0:
                floor_dist = MIN_STOP_ATR * a
                if 0 < cur_dist < floor_dist:
                    sl = entry + floor_dist if sig == -1 else entry - floor_dist
            tp = crl if sig == -1 else crh
        else:
            if not a:
                continue
            sl = entry + ATR_STOP_MULT * a if sig == -1 else entry - ATR_STOP_MULT * a
            tp = entry - ATR_STOP_MULT * RR_FIXED * a if sig == -1 else entry + ATR_STOP_MULT * RR_FIXED * a
        rd = abs(entry - sl)
        if rd <= 0:
            continue
        exit_r = None
        for j in range(i + 1, min(i + 1 + max_hold, n)):
            hi, lo = highs[j], lows[j]
            if sig == 1:
                if lo <= sl: exit_r = (sl - entry) / rd; break
                if hi >= tp: exit_r = (tp - entry) / rd; break
            else:
                if hi >= sl: exit_r = (entry - sl) / rd; break
                if lo <= tp: exit_r = (entry - tp) / rd; break
        if exit_r is None:
            continue
        out.append({"entry": entry, "risk_dist": rd, "raw_r": exit_r, "dir": sig})
    return out


def main():
    tf_specs = [
        ("M5", None, 2400),
        ("M15", "15m", 1600),
        ("M30 (nativo)", "30m", 800),
        ("H1", "1h", 400),
        ("H4", "4h", 300),
        ("D1", "1d", 200),
    ]
    for label, interval, max_hold in tf_specs:
        if interval is None:
            candles = load_m5()
        else:
            candles, _ = bt._fetch_real("XAUUSD", interval, 130000)
        ind = bt._prep(candles)
        atr = ind["atr"]
        print(f"\n=== CRT su {label} ({len(candles)} barre) ===", flush=True)
        for stop_mode in ("native", "atr_fixed"):
            trades = run_crt(candles, atr, stop_mode, max_hold)
            print(fmt(f"  stop={stop_mode}", trades), flush=True)
            buys = [t for t in trades if t["dir"] == 1]
            sells = [t for t in trades if t["dir"] == -1]
            print(fmt(f"    BUY-only", buys), flush=True)
            print(fmt(f"    SELL-only", sells), flush=True)


if __name__ == "__main__":
    main()
