#!/usr/bin/env python3
"""
11/08 (9) - richiesta esplicita dell'utente: guardare come erano scritte
le strategie ai primi test e vedere se una versione "vera" scartata
nasconde qualcosa (come per CRT). THREE_BAR_DELIVERY_BREAK (ex CISD) e'
il caso piu' chiaro trovato nella storia git: sul sito la versione
"vera" MQL5 (displacement + ultima candela di delivery opposta + sweep
di liquidita' + reclaim) dava PF 5.95 ma non scattava MAI (0 setup su
1067) - sostituita con una versione molto piu' semplice (3 candele
stesso segno + rottura estremo), quella tuttora in uso e debole.

Codice originale "vero" (da git show dc13566^, NXS_Strat_CISD pre-
semplificazione):
  - displacement: |close-open| shift1 >= 0.7*ATR
  - ultima candela di "delivery" OPPOSTA (corpo >= 0.5*ATR) entro 15 barre
  - sweep di liquidita' (PDL/EQL/AsiaLow per buy, PDH/EQH/AsiaHigh per sell)
    - uso _sweep_ext_at(), lo stesso rilevatore condiviso gia' fedele
      usato da TURTLE_SOUP/JUDAS_SWING in questo motore
  - reclaim: chiusura oltre l'estremo della candela di delivery opposta

Fase 1: conteggio di frequenza per ogni condizione singola e la loro
combinazione (AND) - per capire quale sia il vero collo di bottiglia
prima di giudicare la P&L.
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import backtest as bt

SYMBOL, BARS = "XAUUSD", 110000
DISPLACEMENT_MULT = 0.7
DELIVERY_MULT = 0.5
LOOKBACK = 15


def _last_opposite_delivery(c, ind, i, want_bull):
    atr = ind["atr"][i]
    for k in range(1, LOOKBACK + 1):
        j = i - k
        if j < 0:
            break
        cd = c[j]
        body = abs(cd["close"] - cd["open"])
        if body < atr * DELIVERY_MULT:
            continue
        is_bull = cd["close"] > cd["open"]
        if is_bull == want_bull:
            return cd["high"], cd["low"]
    return None, None


def cisd_real_signal(c, ind, i):
    atr = ind["atr"][i]
    if not atr or i < LOOKBACK + 1:
        return 0, {}
    c1, o1 = c[i]["close"], c[i]["open"]
    body = abs(c1 - o1)
    disp_ok = body >= atr * DISPLACEMENT_MULT
    flags = {"disp": disp_ok}
    if not disp_ok:
        return 0, flags
    sw = bt._sweep_ext_at(c, ind, i)
    flags["sweep_struct"] = sw is not None
    if not sw:
        return 0, flags
    if c1 > o1:
        bear_hi, bear_lo = _last_opposite_delivery(c, ind, i, want_bull=False)
        flags["delivery_found"] = bear_hi is not None
        swept_low = sw["sweptPDL"] or sw["sweptEQL"] or sw["sweptAsiaLow"]
        flags["swept"] = swept_low
        if bear_hi is not None:
            flags["reclaim"] = c1 > bear_hi
            if swept_low and c1 > bear_hi:
                return 1, flags
    elif c1 < o1:
        bull_hi, bull_lo = _last_opposite_delivery(c, ind, i, want_bull=True)
        flags["delivery_found"] = bull_lo is not None
        swept_high = sw["sweptPDH"] or sw["sweptEQH"] or sw["sweptAsiaHigh"]
        flags["swept"] = swept_high
        if bull_lo is not None:
            flags["reclaim"] = c1 < bull_lo
            if swept_high and c1 < bull_lo:
                return -1, flags
    return 0, flags


def frequency_study(tf):
    candles, _src = bt._fetch_real(SYMBOL, tf, BARS)
    ind = bt._prep(candles)
    n = len(candles)
    counts = {"total": 0, "disp": 0, "sweep_struct": 0, "delivery_found": 0,
              "swept": 0, "reclaim": 0, "full_signal": 0}
    for i in range(LOOKBACK + 1, n):
        counts["total"] += 1
        sig, flags = cisd_real_signal(candles, ind, i)
        for k in ("disp", "sweep_struct", "delivery_found", "swept", "reclaim"):
            if flags.get(k):
                counts[k] += 1
        if sig != 0:
            counts["full_signal"] += 1
    print(f"TF={tf} barre totali={counts['total']}")
    for k in ("disp", "sweep_struct", "delivery_found", "swept", "reclaim", "full_signal"):
        print(f"  {k:<16}{counts[k]}")
    return counts


def main():
    for tf in ("15m", "1h", "4h"):
        frequency_study(tf)
        print()


if __name__ == "__main__":
    main()
