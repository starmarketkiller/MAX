#!/usr/bin/env python3
"""
09/08 - filtro di congestione per il Gruppo A (mean-reversion: BOLLINGER,
RANGE_FADE, RSI_DIV) proposto dall'utente mentre si aspetta che il fetch
Dukascopy arrivi a 10 anni. SOLO CODICE, non ancora eseguito su dati reali
per esplicita richiesta (il campione attuale, 355gg, e' gia' abbastanza
corto da rendere un nuovo filtro con piu' gradi di liberta' un rischio di
overfitting aggiuntivo - meglio aspettare piu' storia prima di leggere i
numeri). NESSUNA fedeltà MQL5 dichiarata: e' un'architettura nuova, non
esiste nulla di equivalente in NXS_Strat_Bollinger/RSI_DIV reali.

Differenza deliberata dal range_gate gia' esistente (run_range_gate in
trend_gate_core.py, usato per il test Group A PF 0.54 di ieri): quel gate
condivide _run_gated con TREND_GATE, che impone un floor `adx >= 20`
PRIMA del gate stesso - contraddittorio per un filtro di ranging (che
vuole ADX basso, non alto). Qui il floor non c'e': la soglia ADX e' PARTE
del filtro di ranging stesso (adx < adx_max), non un prerequisito esterno.

Tre filtri indipendenti e componibili (cosi' si puo' sperimentare quale
combinazione conta davvero, invece di bloccarne una a priori):

  1) Filtro Matematico (ADX + Bollinger Band Width):
     adx[i] < adx_max (default 25) E bbw[i] < media_mobile(bbw, bbw_ma_period)
     - "il trend non c'e' ancora abbastanza forte, E le bande non si
     stanno allargando" (BBW crescente precede spesso un vero breakout).

  2) Filtro Geometrico (box di contenimento vs ATR):
     max(high, ultime box_n barre) - min(low, ultime box_n barre) <= box_atr_mult * atr[i]
     nota: e' la STESSA idea del box RANGING gia' in _rect_engine_series
     (trend_gate_core.py, N=20 barre) - qui riformulato con soglia ATR
     esplicita invece che sulla chiusura+corpo, per poter sperimentare
     indipendentemente dal box gia' usato dal TREND_GATE.

  3) Filtro di "Entanglement" (incroci EMA20, OPZIONALE, default off):
     >= ema_cross_min attraversamenti chiusura/EMA20 nelle ultime
     ema_cross_lookback barre. La spec originale lo descrive ma poi la
     sezione "come integrarlo" combina solo Filtro 1+2 - incoerenza nella
     spec pastata, non risolta qui: esposto come flag indipendente
     (require_ema_entanglement) cosi' la scelta si fa quando si testa,
     non ora.

is_ranging_series: True solo se Filtro 1 E Filtro 2 sono allineati
(sempre) E, se richiesto, anche Filtro 3.

Clausola di salvaguardia (state machine IDLE->WAITING->fill/scadenza,
stesso schema gia' validato per SH_BMS_RTO/Silver Bullet/OTE_CONT in
questo repo): un segnale nativo del Gruppo A arma un'attesa di wait_bars
barre; se durante l'attesa is_ranging diventa False, l'ordine e'
annullato PRIMA di essere eseguito; altrimenti si entra alla prima barra
successiva in cui is_ranging e' ancora True (di norma la barra stessa o
la successiva, dato che il regime non cambia ad ogni barra).
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import backtest as bt
from trend_gate_core import (COSTS, SYMBOL, RISK_PCT, START_EQUITY, MAX_HOLD)


def _bbw_series(closes, period=20):
    """Bollinger Band Width = (upper-lower)/mid = 4*std/mid (bande a 2
    deviazioni standard, stessa convenzione di sig_bollinger in
    backtest.py: fedelta' verificata li' contro NXS_Strat_Bollinger)."""
    n = len(closes)
    out = [None] * n
    for i in range(n):
        sd, mid = bt._std(closes, period, i), bt.sma(closes, period, i)
        if sd is None or mid is None or mid == 0:
            continue
        out[i] = (4.0 * sd) / mid
    return out


def _sma_series(vals, period):
    n = len(vals)
    out = [None] * n
    for i in range(n):
        window = [x for x in vals[max(0, i - period + 1):i + 1] if x is not None]
        if len(window) < period:
            continue
        out[i] = sum(window) / len(window)
    return out


def _box_contained_series(candles, atr, box_n=20, box_atr_mult=2.0):
    n = len(candles)
    out = [False] * n
    for i in range(box_n, n):
        a = atr[i]
        if not a:
            continue
        window = candles[i - box_n:i]
        box_range = max(c["high"] for c in window) - min(c["low"] for c in window)
        out[i] = box_range <= box_atr_mult * a
    return out


def _ema_cross_count_series(closes, ema20, lookback=15):
    """Conta gli attraversamenti chiusura/EMA20 (chiusura sopra poi sotto,
    o viceversa, fra barre consecutive) nelle ultime `lookback` barre."""
    n = len(closes)
    out = [0] * n
    above = [None] * n
    for i in range(n):
        if ema20[i] is None:
            continue
        above[i] = closes[i] > ema20[i]
    for i in range(lookback, n):
        cnt = 0
        for k in range(i - lookback + 1, i + 1):
            if above[k] is None or above[k - 1] is None:
                continue
            if above[k] != above[k - 1]:
                cnt += 1
        out[i] = cnt
    return out


def is_ranging_series(candles, ind, atr, adx, *,
                       adx_max=25.0, bbw_ma_period=20,
                       box_n=20, box_atr_mult=2.0,
                       ema_cross_lookback=15, ema_cross_min=3,
                       require_ema_entanglement=False):
    closes = ind["close"]
    bbw = _bbw_series(closes, 20)
    bbw_ma = _sma_series(bbw, bbw_ma_period)
    box_ok = _box_contained_series(candles, atr, box_n, box_atr_mult)
    cross_cnt = _ema_cross_count_series(closes, ind["ema20"], ema_cross_lookback) \
        if require_ema_entanglement else None

    n = len(candles)
    out = [False] * n
    for i in range(n):
        adx_i = adx[i]
        if adx_i is None or adx_i >= adx_max:
            continue
        if bbw[i] is None or bbw_ma[i] is None or bbw[i] >= bbw_ma[i]:
            continue
        if not box_ok[i]:
            continue
        if require_ema_entanglement and (cross_cnt is None or cross_cnt[i] < ema_cross_min):
            continue
        out[i] = True
    return out


def run_group_a_windowed(strat, tf, wait_bars=5, *,
                         adx_max=25.0, bbw_ma_period=20,
                         box_n=20, box_atr_mult=2.0,
                         ema_cross_lookback=15, ema_cross_min=3,
                         require_ema_entanglement=False,
                         atr_sl_mult=1.5, atr_tp_mult=3.0,
                         bars_min=60):
    """Backtest Gruppo A: segnale nativo della strategia + is_ranging con
    finestra di tolleranza/invalidazione. SL/TP ad ATR semplice (nessun
    Modello Istituzionale/tier qui: il Gruppo A e' mean-reversion, non
    condivide il framework di conviction del nucleo trend)."""
    candles, src = bt._fetch_real(SYMBOL, tf)
    ind = bt._prep(candles)
    atr = ind["atr"]
    adx = ind["adx"]
    ranging = is_ranging_series(candles, ind, atr, adx,
                                adx_max=adx_max, bbw_ma_period=bbw_ma_period,
                                box_n=box_n, box_atr_mult=box_atr_mult,
                                ema_cross_lookback=ema_cross_lookback,
                                ema_cross_min=ema_cross_min,
                                require_ema_entanglement=require_ema_entanglement)

    equity = START_EQUITY
    trades = []
    position = None
    pending = None   # {"dir": 1/-1, "deadline": bar_idx}
    n = len(candles)
    for i in range(bars_min, n):
        px = candles[i]["close"]
        if position is not None:
            hi, lo = candles[i]["high"], candles[i]["low"]
            hit = None
            if position["dir"] == 1:
                if lo <= position["sl"]:
                    hit = ("SL", position["sl"])
                elif hi >= position["tp"]:
                    hit = ("TP", position["tp"])
            else:
                if hi >= position["sl"]:
                    hit = ("SL", position["sl"])
                elif lo <= position["tp"]:
                    hit = ("TP", position["tp"])
            if not hit and (i - position["open_i"]) >= MAX_HOLD:
                hit = ("TIME", px)
            if hit:
                reason, exitpx = hit
                rd = position["risk_dist"] if position["risk_dist"] > 0 else 1e-9
                r_mult = ((exitpx - position["entry"]) / rd) if position["dir"] == 1 \
                    else ((position["entry"] - exitpx) / rd)
                spread_r = COSTS["spread_price"] / rd if COSTS["spread_price"] > 0 else 0.0
                slip_r = 0.0
                if COSTS["slippage_price"] > 0:
                    slip_r = COSTS["slippage_price"] / rd
                    if reason in ("SL", "TIME"):
                        slip_r += COSTS["slippage_price"] / rd
                r_net = r_mult - spread_r - COSTS["commission_r"] - slip_r
                pnl = round(r_net * position["risk_money"], 2)
                equity += pnl
                trades.append({"side": "BUY" if position["dir"] == 1 else "SELL", "pnl": pnl, "reason": reason})
                position = None
            continue

        a = atr[i]
        if not a:
            continue

        if pending is not None:
            if not ranging[i]:
                pending = None            # invalidato: il regime e' cambiato prima del fill
            elif i > pending["deadline"]:
                pending = None            # scaduto
            else:
                dir_ = pending["dir"]
                entry = px
                sl_dist = a * atr_sl_mult
                tp_dist = a * atr_tp_mult
                sl = entry - sl_dist if dir_ == 1 else entry + sl_dist
                tp = entry + tp_dist if dir_ == 1 else entry - tp_dist
                position = {"dir": dir_, "entry": entry, "sl": sl, "tp": tp, "open_i": i,
                            "risk_dist": sl_dist, "risk_money": equity * (RISK_PCT / 100.0)}
                pending = None
                continue

        if not ranging[i]:
            continue
        v = bt.STRATEGIES[strat](candles, ind, i)
        if v == 0:
            continue
        pending = {"dir": v, "deadline": i + wait_bars}

    gross_win = sum(t["pnl"] for t in trades if t["pnl"] > 0)
    gross_loss = -sum(t["pnl"] for t in trades if t["pnl"] < 0)
    pf = round(gross_win / gross_loss, 2) if gross_loss > 0 else (None if gross_win == 0 else float("inf"))
    wr = round(100 * sum(1 for t in trades if t["pnl"] >= 0) / len(trades), 1) if trades else None
    buys = [t for t in trades if t["side"] == "BUY"]
    sells = [t for t in trades if t["side"] == "SELL"]
    def _pf(lst):
        g = sum(t["pnl"] for t in lst if t["pnl"] > 0); l = -sum(t["pnl"] for t in lst if t["pnl"] < 0)
        return round(g / l, 2) if l > 0 else (None if g == 0 else float("inf"))
    return {
        "src": src, "trades": len(trades), "pf": pf, "wr": wr,
        "net_pnl": round(equity - START_EQUITY, 2),
        "n_buy": len(buys), "pf_buy": _pf(buys), "n_sell": len(sells), "pf_sell": _pf(sells),
    }


if __name__ == "__main__":
    print("Modulo pronto, NON eseguito automaticamente (in attesa di piu' storico Dukascopy).")
    print("Per testare quando i 10 anni saranno pronti:")
    print("  from group_a_congestion_gate import run_group_a_windowed")
    print("  run_group_a_windowed('BOLLINGER', '1d', wait_bars=5)")
