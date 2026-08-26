#!/usr/bin/env python3
"""25/08 - MALAYSIAN_SNR (NXS_Strat_MalaysianSNR_Rejection, NXS_Strategies_
SMC.mqh) non era mai stata testata sulla ricetta live esatta. Trovato un
segnale d'allarme gia' nel codice: NXS_Profile_Risk("MALAYSIAN_SNR")=0.4%
(tier minimo) con commento "PF 0.00" - qualcuno ha gia' osservato dal vivo
che perde sempre e ha reagito tagliando il rischio al minimo invece di
disattivarla o correggerla. E' anche su EffTF=D1 (lentissima - esattamente
la paura dell'utente stasera: "molte operazioni possono non aprire... per
molti giorni").

Meccanica reale:
- Livello chiave = massimo/minimo delle CHIUSURE (non wick) delle ultime
  12 candele H4 CHIUSE (InpTFHigh, fisso H4 indipendente dall'EffTF).
- Bonus/conferma W1 = max/min delle chiusure delle ultime 8 settimane
  CHIUSE (PERIOD_W1) - qui solo bonus di score, non gate d'entrata.
- Storyline: H4 (close shift1 vs shift4) e D1 (close shift1 vs shift2)
  devono concordare in direzione.
- Freshness: il livello H4 non deve essere gia' stato toccato nelle
  ultime 20 barre H4 (esclude le 3 piu' recenti).
- Entrata valutata sulla barra shift1 dell'EffTF DELLA STRATEGIA (oggi
  D1): tocco del livello (low/high entro +-0.4xATR_H4) + corpo forte
  (>0.5xATR_EffTF) + storyline.
- Stop nativo = livello H4 +-0.5xATR_H4. Target = 2.3xATR_EffTF (ATR
  MULTIPLE, non RR sulla distanza reale dello stop - stessa formula di
  _smc_tp usata da altre strategie SMC).

Qui si testa l'EffTF (quello che nel codice determina l1/h1/c1/o1 e
l'ATR del target) su una scansione: D1 (nativo, lento) vs H4/H1/M30/M15
(scalp, per rispondere alla richiesta dell'utente di vedere azione
piu' frequente) - il livello H4/W1 di riferimento resta IDENTICO in
ogni caso, cambia solo quanto spesso/precisamente si controlla il
tocco."""
import sys, os, bisect
from datetime import datetime
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import backtest as bt

MAX_HOLD = {"M15": 1600, "M30": 800, "H1": 400, "H4": 300, "D1": 200}


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
    rd = sorted(t["risk_dist"] for t in trades)
    rd_med = rd[len(rd) // 2] if rd else 0.0
    return (f"{label:24s} n={len(trades):5d} PF={pf(net):.2f} "
            f"(m1={pf(net[:mid]):.2f}/m2={pf(net[mid:]):.2f}) win={n_pos}/{len(wf) if wf else 0} "
            f"medRiskDist=${rd_med:.2f}")


def week_key(dt):
    y, w, _ = dt.isocalendar()
    return (y, w)


def main():
    candlesH4, _ = bt._fetch_real("XAUUSD", "4h", 40000)
    candlesD1, _ = bt._fetch_real("XAUUSD", "1d", 4000)
    indH4 = bt._prep(candlesH4)
    atrH4_arr = indH4["atr"]
    h4_times = [c["time"] for c in candlesH4]
    h4_close = [c["close"] for c in candlesH4]
    h4_high = [c["high"] for c in candlesH4]
    h4_low = [c["low"] for c in candlesH4]
    nH4 = len(candlesH4)

    d1_times = [c["time"] for c in candlesD1]
    d1_close = [c["close"] for c in candlesD1]

    # weekly closes: last D1 close of each ISO week, chronological
    week_order = []
    week_close = {}
    for i, c in enumerate(candlesD1):
        dt = datetime.strptime(c["time"].split(" ")[0], "%Y-%m-%d")
        k = week_key(dt)
        if k not in week_close:
            week_order.append(k)
        week_close[k] = c["close"]   # overwritten each day -> ends as last close of week
    weekly_closes_seq = [week_close[k] for k in week_order]
    # end-time of each week = time of its last D1 bar (approx, good enough for bisect)
    week_end_time = {}
    for i, c in enumerate(candlesD1):
        dt = datetime.strptime(c["time"].split(" ")[0], "%Y-%m-%d")
        k = week_key(dt)
        week_end_time[k] = c["time"]
    week_end_seq = [week_end_time[k] for k in week_order]

    def h4_idx_at(t):
        return bisect.bisect_right(h4_times, t) - 1

    def d1_idx_at(t):
        return bisect.bisect_right(d1_times, t) - 1

    def week_idx_at(t):
        return bisect.bisect_right(week_end_seq, t) - 1

    def snr_context(t):
        """Ritorna (h4Hi, h4Lo, atrH4, freshHi, freshLo, w1Hi, w1Lo, storyBull, storyBear) o None."""
        j = h4_idx_at(t)
        if j < 25:
            return None
        a = atrH4_arr[j]
        if not a:
            return None
        win_close = h4_close[j - 11:j + 1]   # shift1..12 -> idx j-11..j
        h4Hi, h4Lo = max(win_close), min(win_close)
        # freshness: shift4..20 (esclude le 3 piu' recenti) -> idx j-19..j-3
        freshHi, freshLo = True, True
        for idx in range(max(0, j - 19), j - 2):
            hh, ll = h4_high[idx], h4_low[idx]
            if h4Hi - a * 0.3 <= hh <= h4Hi + a * 0.3:
                freshHi = False
            if h4Lo - a * 0.3 <= ll <= h4Lo + a * 0.3:
                freshLo = False
        wk = week_idx_at(t)
        if wk < 7:
            w1Hi = w1Lo = 0
        else:
            wwin = weekly_closes_seq[wk - 7:wk + 1]
            w1Hi, w1Lo = max(wwin), min(wwin)
        h4C1 = h4_close[j]
        h4C4 = h4_close[j - 3] if j >= 3 else h4C1
        d1j = d1_idx_at(t)
        if d1j < 2:
            return None
        d1C1, d1C2 = d1_close[d1j], d1_close[d1j - 1]
        storyBull = h4C1 > h4C4 and d1C1 >= d1C2
        storyBear = h4C1 < h4C4 and d1C1 <= d1C2
        return h4Hi, h4Lo, a, freshHi, freshLo, w1Hi, w1Lo, storyBull, storyBear

    def test_tf(label, candles, atr_arr):
        n = len(candles)
        closes = [c["close"] for c in candles]
        opens = [c["open"] for c in candles]
        lows = [c["low"] for c in candles]
        highs = [c["high"] for c in candles]
        times = [c["time"] for c in candles]
        max_hold = MAX_HOLD[label.split()[0]]
        out = []
        for i in range(30, n - 2):
            a = atr_arr[i]
            if not a:
                continue
            ctx = snr_context(times[i])
            if ctx is None:
                continue
            h4Hi, h4Lo, atrH4, freshHi, freshLo, w1Hi, w1Lo, storyBull, storyBear = ctx
            c1, o1, l1, h1 = closes[i], opens[i], lows[i], highs[i]
            bodyAbs = abs(c1 - o1)
            if bodyAbs <= a * 0.5:
                continue
            sig = None
            if h4Lo - atrH4 * 0.4 <= l1 <= h4Lo + atrH4 * 0.4 and c1 > o1 and storyBull:
                sig = 1
                sl = h4Lo - 0.5 * atrH4
            elif h4Hi - atrH4 * 0.4 <= h1 <= h4Hi + atrH4 * 0.4 and c1 < o1 and storyBear:
                sig = -1
                sl = h4Hi + 0.5 * atrH4
            if sig is None:
                continue
            entry_i = i + 1
            entry = candles[entry_i]["open"]
            rd = abs(entry - sl)
            if rd <= 0:
                continue
            tp = entry + sig * 2.3 * a
            exit_r = None
            for j2 in range(entry_i + 1, min(entry_i + 1 + max_hold, n)):
                hi, lo = highs[j2], lows[j2]
                if sig == 1:
                    if lo <= sl: exit_r = (sl - entry) / rd; break
                    if hi >= tp: exit_r = (tp - entry) / rd; break
                else:
                    if hi >= sl: exit_r = (entry - sl) / rd; break
                    if lo <= tp: exit_r = (entry - tp) / rd; break
            if exit_r is None:
                continue
            out.append({"entry": entry, "risk_dist": rd, "raw_r": exit_r, "dir": sig})
        print(f"--- MALAYSIAN_SNR EffTF={label} ---", flush=True)
        print(fmt("simmetrica", out), flush=True)
        print(fmt("BUY-only", [t for t in out if t["dir"] == 1]), flush=True)
        print(fmt("SELL-only", [t for t in out if t["dir"] == -1]), flush=True)

    test_tf("D1 (nativo)", candlesD1, bt._prep(candlesD1)["atr"])
    test_tf("H4", candlesH4, atrH4_arr)
    for label, interval in (("H1", "1h"), ("M30", "30m"), ("M15", "15m")):
        candles, _ = bt._fetch_real("XAUUSD", interval, 130000)
        ind = bt._prep(candles)
        test_tf(label, candles, ind["atr"])


if __name__ == "__main__":
    main()
