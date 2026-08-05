#!/usr/bin/env python3
"""
04/08 (13) - test indipendente di un'idea trovata sui social (screenshot
Instagram/X, @pranamghagare, "I backtested this XAU strategy so you don't
have to" - 76.53% win rate, <2% drawdown, ~98 trade in un mese su M15).

NON e' una strategia del roster NEXUS (nessuna versione MQL5, nessun
selector_index) - per questo NON passa dal registro canonico
(strategy_registry.resolve/require_strategies lo rifiuterebbe come
"strategia sconosciuta", correttamente: e' li' per proteggere le 37+4
strategie dichiarate, non per bloccare un'esplorazione). Vive qui come
script indipendente, riusa i pezzi generici del motore (_fetch_real,
_prep, ema_series, COST_PRESETS) senza toccare backtest.STRATEGIES.

Regole (dalle 8 slide, trascritte fedelmente):
- Indicatori: EMA 30 (chiusura) + "Support/Resistance with Breaks" con
  Left Bars=1, Right Bars=1 (pivot a UNA barra per lato - il livello piu'
  sensibile possibile, non i 3 bar del nostro choch_int).
- Sul timeframe di ingresso (dichiarato M15): il livello di supporto/
  resistenza ATTIVO e' l'ultimo pivot CONFERMATO (confermato con 1 barra
  di ritardo, come ta.pivotlow/high(1,1) - nessun lookahead: il livello
  usato per il check "rottura" di una barra e' quello noto PRIMA che
  quella barra chiuda, non quello (eventualmente) appena confermato dalla
  barra stessa).
- LONG: la barra buca (wick) sotto il supporto attivo ma CHIUDE sopra
  (liquidity grab) E chiude sopra EMA30. SHORT: simmetrico su resistenza/
  sotto EMA30.
- Entry al top/bottom di quella barra, stop al low/high della stessa
  barra, target 1:1 (stesso rischio del reward - "Low RR = Higher Win
  Rate", dichiarato esplicitamente dalla fonte).

Semplificazione dichiarata: qui l'entry e' approssimata alla CHIUSURA
della barra di segnale (convenzione di TUTTO il resto di questo motore -
nessuna strategia usa ordini pendenti/stop), non un vero ordine stop al
massimo/minimo della barra che potrebbe non riempirsi mai. Leggermente
ottimistica (in una barra rialzista di reversal la chiusura e' di solito
sotto il massimo), ma preserva forma e direzione del rischio:rendimento.

ATTENZIONE sul claim originale: 76.53% WR e <2% drawdown vengono da UN
MESE di dati (02-28 aprile, equity curve nello screenshot), senza alcuna
validazione Out-of-Sample mostrata - esattamente il tipo di risultato
che questa sessione ha imparato a NON fidarsi mai a occhio (vedi lezione
#4 in NQROS_CROSS_STRATEGY_LEARNINGS.md: "un PF spettacolare su un
campione minuscolo e' un'ipotesi, non un risultato"). Questo script
verifica le REGOLE in modo indipendente, col nostro storico e i nostri
costi realistici - non prende per buono il claim della fonte.

Esegui dalla root del repo: python3 server/research_scripts/test_liquidity_grab_ema30.py
"""
import sys
sys.path.insert(0, "server")
import backtest as bt


def _pivot_levels(candles):
    """Livello di supporto/resistenza ATTIVO PRIMA di ogni barra (no
    lookahead - pivot Left=1/Right=1, confermato con 1 barra di ritardo)."""
    n = len(candles)
    active_support = [None] * n
    active_resistance = [None] * n
    cur_sup = cur_res = None
    for i in range(2, n):
        active_support[i] = cur_sup
        active_resistance[i] = cur_res
        lo1, lo2, lo0 = candles[i - 1]["low"], candles[i - 2]["low"], candles[i]["low"]
        hi1, hi2, hi0 = candles[i - 1]["high"], candles[i - 2]["high"], candles[i]["high"]
        if lo1 < lo2 and lo1 < lo0:
            cur_sup = lo1
        if hi1 > hi2 and hi1 > hi0:
            cur_res = hi1
    return active_support, active_resistance


def signal_series(candles, ema30):
    sup, res = _pivot_levels(candles)
    n = len(candles)
    out = [0] * n
    for i in range(2, n):
        if ema30[i] is None:
            continue
        lo, hi, cl = candles[i]["low"], candles[i]["high"], candles[i]["close"]
        if sup[i] is not None and lo < sup[i] and cl > sup[i] and cl > ema30[i]:
            out[i] = 1
            continue
        if res[i] is not None and hi > res[i] and cl < res[i] and cl < ema30[i]:
            out[i] = -1
    return out


def run(symbol, timeframe, bars=2500, cost_preset="retail_standard"):
    candles, src = bt._fetch_real(symbol, timeframe, bars)
    closes = [c["close"] for c in candles]
    ema30 = bt.ema_series(closes, 30)
    sig = signal_series(candles, ema30)
    costs = bt.COST_PRESETS[cost_preset]

    equity = 10000.0
    peak = equity
    maxdd = 0.0
    trades = []
    pos = None
    for i in range(2, len(candles)):
        px = candles[i]["close"]
        if pos:
            hi, lo = candles[i]["high"], candles[i]["low"]
            hit = None
            if pos["dir"] == 1:
                if lo <= pos["sl"]:
                    hit = ("SL", pos["sl"])
                elif hi >= pos["tp"]:
                    hit = ("TP", pos["tp"])
            else:
                if hi >= pos["sl"]:
                    hit = ("SL", pos["sl"])
                elif lo <= pos["tp"]:
                    hit = ("TP", pos["tp"])
            if not hit and (i - pos["open_i"]) >= 40:
                hit = ("TIME", px)
            if hit:
                reason, exitpx = hit
                rd = pos["risk_dist"] if pos["risk_dist"] > 0 else 1e-9
                r_mult = ((exitpx - pos["entry"]) / rd) if pos["dir"] == 1 \
                    else ((pos["entry"] - exitpx) / rd)
                spread_r = (costs["spread_price"] / rd) if costs["spread_price"] > 0 else 0.0
                slip_r = 0.0
                if costs["slippage_price"] > 0:
                    slip_r = costs["slippage_price"] / rd
                    if reason in ("SL", "TIME"):
                        slip_r += costs["slippage_price"] / rd
                r_net = r_mult - spread_r - costs["commission_r"] - slip_r
                pnl = r_net * pos["risk_money"]
                equity += pnl
                peak = max(peak, equity)
                maxdd = max(maxdd, (peak - equity) / peak * 100 if peak else 0)
                trades.append({"pnl": pnl, "r": r_net, "reason": reason})
                pos = None
            continue
        v = sig[i]
        if v == 0:
            continue
        sl = candles[i]["low"] if v == 1 else candles[i]["high"]
        risk_dist = abs(px - sl)
        if risk_dist <= 0:
            continue
        tp = px + v * risk_dist   # 1:1 dichiarato dalla fonte
        risk_money = equity * 0.01
        pos = {"dir": v, "entry": px, "sl": sl, "tp": tp, "open_i": i,
               "risk_money": risk_money, "risk_dist": risk_dist}

    wins = [t for t in trades if t["pnl"] > 0]
    losses = [t for t in trades if t["pnl"] < 0]
    gw = sum(t["pnl"] for t in wins)
    gl = abs(sum(t["pnl"] for t in losses))
    pf = (gw / gl) if gl > 0 else (None if gw == 0 else float("inf"))
    wr = (len(wins) / len(trades) * 100) if trades else 0.0
    net = sum(t["pnl"] for t in trades)
    return {
        "tf": timeframe, "trades": len(trades), "pf": round(pf, 2) if pf not in (None, float("inf")) else pf,
        "wr": round(wr, 1), "net_pnl": round(net, 2), "max_dd_pct": round(maxdd, 2),
        "bars": len(candles), "src": src,
    }


if __name__ == "__main__":
    print("Liquidity Grab + EMA30 (idea social, verifica indipendente) - XAUUSD\n")
    for tf in ("15m", "30m", "1h", "4h"):
        r = run("XAUUSD", tf)
        print(f"{tf:4s}: PF={r['pf']} trades={r['trades']} WR={r['wr']}% "
              f"MaxDD={r['max_dd_pct']}% netpnl={r['net_pnl']} (bars={r['bars']}, src={r['src']})")
