#!/usr/bin/env python3
"""
08/08 - varianti SPERIMENTALI (NON fedeli all'MQL5 reale - verificato, vedi
nota di testa) per FVG_MIT/OTE_CONT/DISP_REBAL/IFVG: zona attiva + finestra
di attesa (N barre) + candela di rejection nella zona, stesso schema
IDLE->WAITING->entry gia' usato da _ob_series/_shbms_series/Silver Bullet
per le strategie che INVECE hanno davvero questa architettura in MQL5.

Ogni funzione qui e' auto-contenuta (candele+atr in input, nessuna modifica
a backtest.py) cosi' da poter essere confrontata direttamente contro la
versione a barra singola gia' in STRATEGIES.
"""
import sys
sys.path.insert(0, "server")
import backtest as bt

WAIT_BARS = 8


def fvg_mit_state_series(candles, atr, wait_bars=WAIT_BARS):
    """Zona = gap FVG (stesso shift della sig_fvg_mit reale: h2=i-4,l2=i-4,
    h0=i-6,l0=i-6 al momento della FORMAZIONE) - poi attesa fino a
    wait_bars per un rientro in zona + rejection, invece di richiedere
    tutto sulla stessa barra della formazione."""
    n = len(candles)
    out = [0] * n
    st = {1: {"active": False, "lo": None, "hi": None, "waited": 0},
          -1: {"active": False, "lo": None, "hi": None, "waited": 0}}
    for i in range(7, n):
        a = atr[i]
        if not a:
            continue
        # formazione (stessa geometria di sig_fvg_mit): controllata SOLO al
        # momento in cui la barra i-6/i-4 diventano quelle giuste, cioe' qui,
        # ogni barra, guardando fisso 4/6 indietro da i.
        h2, l2 = candles[i - 4]["high"], candles[i - 4]["low"]
        h0, l0 = candles[i - 6]["high"], candles[i - 6]["low"]
        if not st[1]["active"] and l0 > h2 + a * 0.15:
            st[1] = {"active": True, "lo": h2, "hi": l0, "waited": 0}
        if not st[-1]["active"] and h0 < l2 - a * 0.15:
            st[-1] = {"active": True, "lo": h0, "hi": l2, "waited": 0}

        c1, o1 = candles[i]["close"], candles[i]["open"]
        cur_lo, cur_hi = candles[i]["low"], candles[i]["high"]
        body = abs(c1 - o1)
        for d in (1, -1):
            s = st[d]
            if not s["active"]:
                continue
            s["waited"] += 1
            if s["waited"] > wait_bars:
                s["active"] = False
                continue
            in_zone = cur_hi >= s["lo"] and cur_lo <= s["hi"]
            if not in_zone:
                continue
            rej = (c1 > o1 and body > a * 0.35) if d == 1 else (c1 < o1 and body > a * 0.35)
            if rej:
                out[i] = d
                s["active"] = False
    return out


def disp_rebal_state_series(candles, atr, wait_bars=WAIT_BARS, disp_lookback=8, disp_body_atr=1.3):
    """Zona = FVG+consequent-encroachment da un displacement (stessa
    geometria di sig_disp_rebal reale) - poi attesa fino a wait_bars per il
    retest del CE + rejection, invece di richiederlo sulla stessa barra."""
    n = len(candles)
    out = [0] * n
    st = {1: {"active": False, "lo": None, "hi": None, "waited": 0},
          -1: {"active": False, "lo": None, "hi": None, "waited": 0}}
    for i in range(disp_lookback + 2, n):
        a = atr[i]
        if not a:
            continue
        for d in (1, -1):
            s = st[d]
            if s["active"]:
                continue
            for k in range(1, disp_lookback + 1):
                idx = i - k
                if idx - 1 < 0:
                    break
                cd = candles[idx]
                body = abs(cd["close"] - cd["open"])
                if body < disp_body_atr * a:
                    continue
                right_color = (cd["close"] > cd["open"]) if d == 1 else (cd["close"] < cd["open"])
                if not right_color:
                    continue
                c1_ref = candles[idx + 1]
                c3_ref = candles[idx - 1]
                if d == 1:
                    fvg_lo, fvg_hi = c1_ref["high"], c3_ref["low"]
                    if fvg_hi > fvg_lo + a * 0.1:
                        st[1] = {"active": True, "lo": fvg_lo, "hi": fvg_hi, "waited": 0}
                        break
                else:
                    fvg_lo, fvg_hi = c3_ref["high"], c1_ref["low"]
                    if fvg_hi > fvg_lo + a * 0.1:
                        st[-1] = {"active": True, "lo": fvg_lo, "hi": fvg_hi, "waited": 0}
                        break

        c1, o1 = candles[i]["close"], candles[i]["open"]
        cur_lo, cur_hi = candles[i]["low"], candles[i]["high"]
        for d in (1, -1):
            s = st[d]
            if not s["active"]:
                continue
            s["waited"] += 1
            if s["waited"] > wait_bars:
                s["active"] = False
                continue
            ce = (s["lo"] + s["hi"]) / 2.0
            if d == 1:
                touch = cur_lo <= ce + a * 0.15 and cur_hi >= s["lo"]
                rej = c1 > o1
            else:
                touch = cur_hi >= ce - a * 0.15 and cur_lo <= s["hi"]
                rej = c1 < o1
            if touch and rej:
                out[i] = d
                s["active"] = False
    return out


def ifvg_state_series(candles, choch_int, atr, wait_bars=WAIT_BARS):
    """Zona = FVG (stessa geometria di sig_ifvg reale, shift2/4) - poi
    attesa fino a wait_bars per una chiusura oltre la zona (INVALIDAZIONE,
    non un semplice retest - e' il concetto IFVG: gap fallito = reversal)
    + rejection + CHoCH, invece di richiederlo sulla stessa barra della
    formazione."""
    n = len(candles)
    out = [0] * n
    choch_up, choch_down = choch_int[1], choch_int[2]
    # zona bullish [h4..l2] si invalida SOTTO (-> SELL), zona bearish
    # [h2..l4] si invalida SOPRA (-> BUY) - stessa polarita' di sig_ifvg
    st = {"bull_zone": {"active": False, "lo": None, "hi": None, "waited": 0},
          "bear_zone": {"active": False, "lo": None, "hi": None, "waited": 0}}
    for i in range(5, n):
        a = atr[i]
        if not a:
            continue
        h2, l2 = candles[i - 2]["high"], candles[i - 2]["low"]
        h4, l4 = candles[i - 4]["high"], candles[i - 4]["low"]
        if not st["bull_zone"]["active"] and l2 > h4 + a * 0.2:
            st["bull_zone"] = {"active": True, "lo": h4, "hi": l2, "waited": 0}
        if not st["bear_zone"]["active"] and h2 < l4 - a * 0.2:
            st["bear_zone"] = {"active": True, "lo": h2, "hi": l4, "waited": 0}

        c1, o1 = candles[i]["close"], candles[i]["open"]
        body = abs(c1 - o1)
        s = st["bull_zone"]
        if s["active"]:
            s["waited"] += 1
            if s["waited"] > wait_bars:
                s["active"] = False
            elif c1 < s["lo"] and c1 < o1 and body > a * 0.3 and choch_down[i]:
                out[i] = -1
                s["active"] = False
        s = st["bear_zone"]
        if s["active"]:
            s["waited"] += 1
            if s["waited"] > wait_bars:
                s["active"] = False
            elif c1 > s["hi"] and c1 > o1 and body > a * 0.3 and choch_up[i]:
                out[i] = 1
                s["active"] = False
    return out


def ote_cont_state_series(candles, adx, choch_int, atr, wait_bars=WAIT_BARS, swing_bars=20):
    """Zona = fascia fib 61.8-79% dell'ultimo swing (stessa idea di
    sig_ote_cont reale) - poi attesa fino a wait_bars per l'ingresso in
    zona + candela nella direzione del trend, invece di richiederlo sulla
    stessa barra del BOS."""
    n = len(candles)
    out = [0] * n
    trend = choch_int[0]
    st = {"dir": 0, "active": False, "fib_lo": None, "fib_hi": None, "waited": 0}
    for i in range(swing_bars + 1, n):
        a = atr[i]
        if not a:
            continue
        if not st["active"]:
            window = candles[i - swing_bars:i]
            shi = max(x["high"] for x in window)
            slo = min(x["low"] for x in window)
            rng = shi - slo
            if rng > 0 and trend[i] != 0:
                if trend[i] > 0:
                    fib_hi, fib_lo = shi - rng * 0.618, shi - rng * 0.79
                else:
                    fib_lo, fib_hi = slo + rng * 0.618, slo + rng * 0.79
                st = {"dir": trend[i], "active": True, "fib_lo": fib_lo, "fib_hi": fib_hi, "waited": 0}

        if not st["active"]:
            continue
        st["waited"] += 1
        if st["waited"] > wait_bars:
            st["active"] = False
            continue
        c1, o1 = candles[i]["close"], candles[i]["open"]
        in_zone = st["fib_lo"] <= c1 <= st["fib_hi"]
        if not in_zone:
            continue
        if st["dir"] > 0 and c1 > o1:
            out[i] = 1
            st["active"] = False
        elif st["dir"] < 0 and c1 < o1:
            out[i] = -1
            st["active"] = False
    return out
