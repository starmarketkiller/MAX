#!/usr/bin/env python3
"""
11/08 - richiesta dell'utente: non "usare l'apertura" (violerebbe la
convenzione del motore, run_backtest entra sempre alla chiusura della
barra del segnale), ma una versione equivalente e valida - aggiungere
una candela di CONFERMA dopo lo sweep prima di entrare, eseguita comunque
alla chiusura reale. Domanda: aspettare che il movimento nella direzione
attesa sia gia' iniziato migliora la qualita' dei trade rispetto a CRT
(entra appena lo sweep si conferma, senza aspettare altro)?

   candela k-2 = RANGE
   candela k-1 = SWEEP (come CRT)
   candela k   = CONFERMA -> deve chiudere nella direzione attesa
                 (quella opposta allo sweep) - se non conferma, niente
                 segnale (non si aspetta oltre, il setup e' scaduto)
   segnale registrato su k -> il motore esegue alla sua chiusura (una
   candela dopo rispetto a CRT base, ma sempre "alla chiusura del
   segnale", nessuna violazione della convenzione)
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import backtest as bt

SYMBOL, BARS = "XAUUSD", 60000


def crt_confirm_series(candles):
    n = len(candles)
    out_sig = [0] * n
    out_sl = [None] * n
    out_tp = [None] * n
    for k in range(2, n):
        rng, sweep = candles[k - 2], candles[k - 1]
        confirm = candles[k]
        crh, crl = rng["high"], rng["low"]
        swept_high = sweep["high"] > crh and sweep["close"] <= crh
        swept_low = sweep["low"] < crl and sweep["close"] >= crl
        if swept_high and not swept_low and confirm["close"] < confirm["open"]:
            out_sig[k] = -1
            out_sl[k] = sweep["high"]
            out_tp[k] = crl
        elif swept_low and not swept_high and confirm["close"] > confirm["open"]:
            out_sig[k] = 1
            out_sl[k] = sweep["low"]
            out_tp[k] = crh
    return out_sig, out_sl, out_tp


def backtest_series(candles, sig, sl_arr, tp_arr, bar_range):
    n = len(candles)
    i0, i1 = int(n * bar_range[0]), int(n * bar_range[1])
    trades = []
    position = None
    for i in range(max(60, i0), i1):
        px = candles[i]["close"]
        if position is not None:
            hi, lo = candles[i]["high"], candles[i]["low"]
            hit = None
            if position["dir"] == 1:
                if lo <= position["sl"]: hit = position["sl"]
                elif hi >= position["tp"]: hit = position["tp"]
            else:
                if hi >= position["sl"]: hit = position["sl"]
                elif lo <= position["tp"]: hit = position["tp"]
            if not hit and (i - position["open_i"]) >= 40:
                hit = px
            if hit is not None:
                rd = position["risk"] if position["risk"] > 0 else 1e-9
                r = ((hit - position["entry"]) / rd) if position["dir"] == 1 else ((position["entry"] - hit) / rd)
                trades.append(r)
                position = None
            continue
        d = sig[i]
        if d == 0 or sl_arr[i] is None:
            continue
        entry = px
        sl, tp = sl_arr[i], tp_arr[i]
        risk = abs(entry - sl)
        if risk <= 0:
            continue
        position = {"dir": d, "entry": entry, "sl": sl, "tp": tp, "open_i": i, "risk": risk}
    gw = sum(r for r in trades if r > 0)
    gl = -sum(r for r in trades if r < 0)
    pf = round(gw / gl, 2) if gl > 0 else (None if gw == 0 else float("inf"))
    return {"trades": len(trades), "pf": pf}


def main():
    N = 5
    for tf in ["4h", "1h", "30m"]:
        candles, src = bt._fetch_real(SYMBOL, tf, bars=BARS)
        sig, sl_arr, tp_arr = crt_confirm_series(candles)
        print(f"\n=== CRT+conferma, {SYMBOL} {tf} ===")
        for label, br in [("IS 60%", (0.0, 0.6)), ("OOS 40%", (0.6, 1.0))]:
            r = backtest_series(candles, sig, sl_arr, tp_arr, br)
            print(f"{label}: trades={r['trades']} pf={r['pf']}")
        print(f"--- walk-forward a {N} finestre ---")
        for w in range(N):
            br = (w / N, (w + 1) / N)
            r = backtest_series(candles, sig, sl_arr, tp_arr, br)
            print(f"{w+1}/{N}: trades={r['trades']} pf={r['pf']}")


if __name__ == "__main__":
    main()
