#!/usr/bin/env python3
"""
11/08 - vera Candle Range Theory (PDF caricato dall'utente, "Candle Range
Theory" di Suven Raj): pattern preciso a 3 candele su un periodo (qui H4,
parametrizzabile), diverso dalla semplificazione "prezzo fuori dal range
del giorno prima" testata prima (quella resta valida come scoperta a se',
ma va rietichettata - non e' la vera CRT).

1. Candela 1 = il Range -> definisce CRH (Candle Range High) e CRL
   (Candle Range Low), cioe' high/low di quella singola candela.
2. Candela 2 = lo Sweep -> tocca con lo stoppino oltre CRH (o CRL) ma
   NON CHIUDE oltre (altrimenti il setup e' invalido - il mercato sta
   continuando, non invertendo).
3. Candela 3 = l'Entrata -> nella direzione OPPOSTA allo sweep, target
   il lato opposto del range (sweep su CRH -> target CRL, e viceversa).

Segnale generato alla CHIUSURA della candela 2 (quando sappiamo che ha
swippato E chiuso dentro il range) - entrata all'apertura della candela
3, come tutte le altre strategie di questo motore (next-bar-open).
SL oltre lo stoppino della candela 2, TP il lato opposto del range
(CRL se swipp su CRH, CRH se swipp su CRL) - target dalla fonte, non un
multiplo ATR generico.

Periodo: la fonte dice esplicitamente "puo' essere Daily, H4, H1... M1"
- qui testato DIRETTAMENTE sul TF base (nessun resample intermedio),
ripetuto su piu' TF come tutte le altre diagnosi di oggi, non fissato
a una combinazione periodo/base arbitraria.
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import backtest as bt

SYMBOL, BARS = "XAUUSD", 60000


def crt_series(candles):
    # 11/08 - CORRETTO: il motore run_backtest apre SEMPRE alla CHIUSURA
    # della barra del segnale (px = candles[i]["close"], vedi run_backtest),
    # non alla sua apertura. Il segnale va quindi generato alla chiusura
    # della candela SWEEP stessa (non un'altra candela dopo) - il motore
    # entrera' li', il momento piu' vicino a "candela 3 fornisce l'entrata"
    # ottenibile con la convenzione fissa di questo engine. Prima versione
    # (segnale alla candela successiva, entrata alla sua apertura) non
    # corrispondeva a come gira davvero il motore - numeri di quella
    # versione scartati, non piu' validi.
    n = len(candles)
    out_sig = [0] * n
    out_sl = [None] * n
    out_tp = [None] * n
    for i in range(1, n):
        rng, sweep = candles[i - 1], candles[i]
        crh, crl = rng["high"], rng["low"]
        swept_high = sweep["high"] > crh and sweep["close"] <= crh
        swept_low = sweep["low"] < crl and sweep["close"] >= crl
        if swept_high and not swept_low:
            out_sig[i] = -1
            out_sl[i] = sweep["high"]
            out_tp[i] = crl
        elif swept_low and not swept_high:
            out_sig[i] = 1
            out_sl[i] = sweep["low"]
            out_tp[i] = crh
    return out_sig, out_sl, out_tp


def backtest_crt(candles, sig, sl_arr, tp_arr, bar_range):
    n = len(candles)
    i0, i1 = int(n * bar_range[0]), int(n * bar_range[1])
    equity, trades = 10000.0, []
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
        entry = px   # chiusura della barra del segnale - stessa convenzione di run_backtest
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
    for tf in ["4h", "1h", "30m"]:
        candles, src = bt._fetch_real(SYMBOL, tf, bars=BARS)
        sig, sl_arr, tp_arr = crt_series(candles)
        print(f"\n=== CRT vera, {SYMBOL} {tf} ===")
        for label, br in [("Periodo intero", (0.0, 1.0)), ("IS 60%", (0.0, 0.6)), ("OOS 40%", (0.6, 1.0))]:
            r = backtest_crt(candles, sig, sl_arr, tp_arr, br)
            print(f"{label}: trades={r['trades']} pf={r['pf']}")


if __name__ == "__main__":
    main()
