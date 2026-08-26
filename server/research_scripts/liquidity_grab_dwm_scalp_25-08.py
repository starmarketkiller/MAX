#!/usr/bin/env python3
"""25/08 notte - nuova idea richiesta dall'utente: uno strato "scalp" a
turnover rapido (target piccolo, es. 100 pip / pochi dollari) per dare
azione all'EA anche mentre le strategie strutturali (per lo piu' H4/D1
dopo le correzioni di stasera) restano ferme per giorni. Meccanismo
NUOVO, non un porting: sweep (wick oltre un livello + chiusura di
rientro) di PDH/PDL (D1 shift1), PWH/PWL (settimana CALENDARIO
precedente) o PMH/PML (mese calendario precedente) - stessa convenzione
di livello di NXS_DetectSweepExt in NXS_MarketAnalysis.mqh - fade del
sweep, entrata all'apertura della barra successiva, su TF veloce
(M15/M30), target fisso in dollari (non R-multiple, per centrare
davvero "piccola vincita frequente").

Due variabili testate come per CRT stasera:
  (A) livello: D / W / M, isolati e in combinazione con la stessa
      priorita' del codice live (mensile > settimanale > giornaliero se
      piu' livelli sweepano sulla stessa barra).
  (B) meccanismo di stop: nativo (ancorato al wick della barra di sweep,
      con floor 0.3xATR "widen" come CRT) vs fisso ad ATR (1.0xATR) -
      target fisso $5/$8/$12 in entrambi i casi (non RR-based, per
      restare fedele a "vincita piccola e definita", non un multiplo
      dello stop).

Nota "100 pip": in questo codebase 1 lotto standard XAUUSD ~= $100 per
$1 di movimento (vedi commento InpMaxTotalLotMult in NXS_Inputs.mqh),
quindi "1 pip" qui equivarrebbe a $1 di prezzo - "100 pip" sarebbe un
movimento di $100, enorme per uno scalp M15/M30. Ambiguo: testati target
diretti in dollari ($5/$8/$12) invece di indovinare una conversione pip
probabilmente sproporzionata.
"""
import sys, os, bisect
from datetime import datetime
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import backtest as bt

STOP_ATR_MULT = 1.0
MIN_STOP_ATR = 0.3
TARGETS = (5.0, 8.0, 12.0)
MAX_HOLD = {"15m": 800, "30m": 500}


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


def fmt(label, trades, days_span):
    net = net_series(trades)
    wf = walk_forward(net)
    mid = len(net) // 2
    n_pos = sum(1 for _, p in (wf or []) if p >= 1.0)
    rd = [t["risk_dist"] for t in trades]
    rd_med = sorted(rd)[len(rd) // 2] if rd else 0.0
    tpd = len(trades) / days_span if days_span else 0.0
    return (f"{label:46s} n={len(trades):5d} tpd={tpd:5.2f} PF={pf(net):.2f} "
            f"(m1={pf(net[:mid]):.2f}/m2={pf(net[mid:]):.2f}) win={n_pos}/{len(wf) if wf else 0} "
            f"medRiskDist=${rd_med:.2f}")


def date_key(tstr):
    return tstr.split(" ")[0]


def iso_week_key(date_str):
    d = datetime.strptime(date_str, "%Y-%m-%d")
    y, w, _ = d.isocalendar()
    return (y, w)


def month_key(date_str):
    d = datetime.strptime(date_str, "%Y-%m-%d")
    return (d.year, d.month)


def build_level_lookups(candlesD1):
    """Ritorna 3 funzioni date->livello (prev day/week/month H/L), fedeli
    alla convenzione shift1 di NXS_DetectSweepExt (livello del periodo
    PRECEDENTE, non quello in corso)."""
    dates = [date_key(c["time"]) for c in candlesD1]
    highs = [c["high"] for c in candlesD1]
    lows = [c["low"] for c in candlesD1]

    # daily: shift1 = giorno D1 immediatamente precedente
    d1_times = dates

    def day_lookup(d):
        j = bisect.bisect_left(d1_times, d)
        if j < 1:
            return None, None
        return highs[j - 1], lows[j - 1]

    # weekly / monthly: aggrega D1 per chiave calendario, poi usa il
    # periodo precedente a quello della data richiesta.
    def build_period_lookup(key_fn):
        info = {}
        order = []
        for i, d in enumerate(dates):
            k = key_fn(d)
            if k not in info:
                info[k] = {"high": highs[i], "low": lows[i]}
                order.append(k)
            else:
                info[k]["high"] = max(info[k]["high"], highs[i])
                info[k]["low"] = min(info[k]["low"], lows[i])
        prev = {}
        for idx, k in enumerate(order):
            if idx == 0:
                continue
            pk = order[idx - 1]
            prev[k] = (info[pk]["high"], info[pk]["low"])

        def lookup(d):
            k = key_fn(d)
            return prev.get(k, (None, None))
        return lookup

    week_lookup = build_period_lookup(iso_week_key)
    month_lookup = build_period_lookup(month_key)
    return day_lookup, week_lookup, month_lookup


def run_scan(candles, atr, day_lu, week_lu, month_lu, level_mode, stop_mode, target):
    """level_mode: 'D','W','M','combo' (priorita' M>W>D come nel codice live)."""
    n = len(candles)
    highs = [c["high"] for c in candles]
    lows = [c["low"] for c in candles]
    closes = [c["close"] for c in candles]
    times = [c["time"] for c in candles]
    out = []
    for i in range(2, n - 1):
        d = date_key(times[i])
        pdh, pdl = day_lu(d)
        pwh, pwl = week_lu(d)
        pmh, pml = month_lu(d)
        h1, l1, c1 = highs[i], lows[i], closes[i]

        sig, level_used = 0, None
        candidates_sell = []
        candidates_buy = []
        if level_mode in ("D", "combo") and pdh is not None and h1 > pdh and c1 <= pdh:
            candidates_sell.append(("D", pdh))
        if level_mode in ("D", "combo") and pdl is not None and l1 < pdl and c1 >= pdl:
            candidates_buy.append(("D", pdl))
        if level_mode in ("W", "combo") and pwh is not None and h1 > pwh and c1 <= pwh:
            candidates_sell.append(("W", pwh))
        if level_mode in ("W", "combo") and pwl is not None and l1 < pwl and c1 >= pwl:
            candidates_buy.append(("W", pwl))
        if level_mode in ("M", "combo") and pmh is not None and h1 > pmh and c1 <= pmh:
            candidates_sell.append(("M", pmh))
        if level_mode in ("M", "combo") and pml is not None and l1 < pml and c1 >= pml:
            candidates_buy.append(("M", pml))

        # priorita' M > W > D (stessa di NXS_DetectSweepExt: l'ultimo che
        # scatta in ordine di scala vince); qui semplicemente si sceglie
        # l'ultima corrispondenza trovata scandendo in ordine D,W,M.
        prio = {"D": 0, "W": 1, "M": 2}
        if candidates_sell and not candidates_buy:
            level_used, lvl_price = max(candidates_sell, key=lambda x: prio[x[0]])
            sig = -1
            native_sl = h1
        elif candidates_buy and not candidates_sell:
            level_used, lvl_price = max(candidates_buy, key=lambda x: prio[x[0]])
            sig = 1
            native_sl = l1
        else:
            continue

        a = atr[i]
        entry = candles[i + 1]["open"]
        if stop_mode == "native":
            sl = native_sl
            cur_dist = abs(entry - sl)
            if a and MIN_STOP_ATR > 0:
                floor_dist = MIN_STOP_ATR * a
                if 0 < cur_dist < floor_dist:
                    sl = entry + floor_dist if sig == -1 else entry - floor_dist
        else:
            if not a:
                continue
            sl = entry + STOP_ATR_MULT * a if sig == -1 else entry - STOP_ATR_MULT * a
        rd = abs(entry - sl)
        if rd <= 0:
            continue
        tp = entry - target if sig == -1 else entry + target

        max_hold = MAX_HOLD.get("30m", 500)
        exit_r = None
        for j in range(i + 2, min(i + 2 + max_hold, n)):
            hi, lo = highs[j], lows[j]
            if sig == 1:
                if lo <= sl: exit_r = (sl - entry) / rd; break
                if hi >= tp: exit_r = (tp - entry) / rd; break
            else:
                if hi >= sl: exit_r = (entry - sl) / rd; break
                if lo <= tp: exit_r = (entry - tp) / rd; break
        if exit_r is None:
            continue
        out.append({"entry": entry, "risk_dist": rd, "raw_r": exit_r, "dir": sig, "level": level_used})
    return out


def main():
    candlesD1, _ = bt._fetch_real("XAUUSD", "1d", 4000)
    day_lu, week_lu, month_lu = build_level_lookups(candlesD1)
    d0 = datetime.strptime(date_key(candlesD1[0]["time"]), "%Y-%m-%d")
    d1 = datetime.strptime(date_key(candlesD1[-1]["time"]), "%Y-%m-%d")
    days_span = (d1 - d0).days or 1

    for tf_label, interval in (("M15", "15m"), ("M30", "30m")):
        candles, _ = bt._fetch_real("XAUUSD", interval, 130000)
        ind = bt._prep(candles)
        atr = ind["atr"]
        print(f"\n########## TF={tf_label} ({len(candles)} barre, {days_span}g calendario) ##########", flush=True)
        for level_mode in ("D", "W", "M", "combo"):
            print(f"--- livello={level_mode} ---", flush=True)
            for stop_mode in ("native", "atr_fixed"):
                for target in TARGETS:
                    trades = run_scan(candles, atr, day_lu, week_lu, month_lu, level_mode, stop_mode, target)
                    label = f"  stop={stop_mode} target=${target:.0f}"
                    print(fmt(label, trades, days_span), flush=True)


if __name__ == "__main__":
    main()
