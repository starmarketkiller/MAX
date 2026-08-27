#!/usr/bin/env python3
"""26/08 - dettaglio dei singoli segnali MALAYSIAN_SNR (M30, ricetta live
esatta) nella stessa finestra usata dal test Tester MT5 reale (2026.08.12
- 2026.08.26): che direzione avevano, sarebbero andati in profitto o no,
di quanto - per rispondere alla domanda dell'utente sui 310 segnali
bloccati dallo spread durante quel test. Riusa la stessa logica di
malaysian_snr_live_signal_25-08.py (non duplicata linea per linea qui
sotto per il resto della pipeline - stesso approccio, stesso codice)."""
import sys, os, bisect
from datetime import datetime
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import backtest as bt

WINDOW_START = "2026-08-12"
WINDOW_END = "2026-08-26"


def week_key(dt):
    y, w, _ = dt.isocalendar()
    return (y, w)


def main():
    candlesH4, _ = bt._fetch_real("XAUUSD", "4h", 40000)
    candlesD1, _ = bt._fetch_real("XAUUSD", "1d", 4000)
    candlesM30, _ = bt._fetch_real("XAUUSD", "30m", 130000)
    indH4 = bt._prep(candlesH4)
    indM30 = bt._prep(candlesM30)
    atrH4_arr = indH4["atr"]
    atrM30_arr = indM30["atr"]
    h4_times = [c["time"] for c in candlesH4]
    h4_close = [c["close"] for c in candlesH4]
    h4_high = [c["high"] for c in candlesH4]
    h4_low = [c["low"] for c in candlesH4]

    d1_times = [c["time"] for c in candlesD1]
    d1_close = [c["close"] for c in candlesD1]

    week_order = []
    week_close = {}
    week_end_time = {}
    for c in candlesD1:
        dt = datetime.strptime(c["time"].split(" ")[0], "%Y-%m-%d")
        k = week_key(dt)
        if k not in week_close:
            week_order.append(k)
        week_close[k] = c["close"]
        week_end_time[k] = c["time"]
    weekly_closes_seq = [week_close[k] for k in week_order]
    week_end_seq = [week_end_time[k] for k in week_order]

    def h4_idx_at(t):
        return bisect.bisect_right(h4_times, t) - 1

    def d1_idx_at(t):
        return bisect.bisect_right(d1_times, t) - 1

    def week_idx_at(t):
        return bisect.bisect_right(week_end_seq, t) - 1

    def snr_context(t):
        j = h4_idx_at(t)
        if j < 25:
            return None
        a = atrH4_arr[j]
        if not a:
            return None
        win_close = h4_close[j - 11:j + 1]
        h4Hi, h4Lo = max(win_close), min(win_close)
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

    n = len(candlesM30)
    closes = [c["close"] for c in candlesM30]
    opens = [c["open"] for c in candlesM30]
    lows = [c["low"] for c in candlesM30]
    highs = [c["high"] for c in candlesM30]
    times = [c["time"] for c in candlesM30]

    print(f"{'Data/ora segnale':20s} {'Dir':5s} {'Entry':>9s} {'SL':>9s} {'TP':>9s} "
          f"{'Esito':>7s} {'R netto':>8s} {'Note'}")
    n_shown = 0
    n_win = n_lose = 0
    sum_r = 0.0
    for i in range(30, n - 2):
        t = times[i]
        if not (WINDOW_START <= t.split(" ")[0] <= WINDOW_END):
            continue
        a = atrM30_arr[i]
        if not a:
            continue
        ctx = snr_context(t)
        if ctx is None:
            continue
        h4Hi, h4Lo, atrH4, freshHi, freshLo, w1Hi, w1Lo, storyBull, storyBear = ctx
        c1, o1, l1, h1 = closes[i], opens[i], lows[i], highs[i]
        bodyAbs = abs(c1 - o1)
        if bodyAbs <= a * 0.5:
            continue
        sig = None
        note = ""
        if h4Lo - atrH4 * 0.4 <= l1 <= h4Lo + atrH4 * 0.4 and c1 > o1 and storyBull:
            sig = 1
            sl = h4Lo - 0.5 * atrH4
            note = "tocco supporto H4" + ("+W1" if w1Lo > 0 and abs(h4Lo - w1Lo) <= atrH4 * 0.5 else "") + (" fresh" if freshLo else " gia' testato")
        elif h4Hi - atrH4 * 0.4 <= h1 <= h4Hi + atrH4 * 0.4 and c1 < o1 and storyBear:
            sig = -1
            sl = h4Hi + 0.5 * atrH4
            note = "tocco resistenza H4" + ("+W1" if w1Hi > 0 and abs(h4Hi - w1Hi) <= atrH4 * 0.5 else "") + (" fresh" if freshHi else " gia' testata")
        if sig is None:
            continue
        entry_i = i + 1
        entry = candlesM30[entry_i]["open"]
        rd = abs(entry - sl)
        if rd <= 0:
            continue
        tp = entry + sig * 2.3 * a
        exit_r = None
        for j2 in range(entry_i + 1, min(entry_i + 1600, n)):
            hi, lo = highs[j2], lows[j2]
            if sig == 1:
                if lo <= sl: exit_r = (sl - entry) / rd; break
                if hi >= tp: exit_r = (tp - entry) / rd; break
            else:
                if hi >= sl: exit_r = (entry - sl) / rd; break
                if lo <= tp: exit_r = (entry - tp) / rd; break
        if exit_r is None:
            continue
        cost = bt.scaled_cost_for_price("retail_standard", entry)
        cost_r = min((cost["spread_price"] + cost["slippage_price"]) / rd, bt.MAX_COST_R_PER_TRADE)
        net_r = exit_r - cost_r
        n_shown += 1
        sum_r += net_r
        if net_r > 0:
            n_win += 1
        else:
            n_lose += 1
        print(f"{t:20s} {'BUY' if sig==1 else 'SELL':5s} {entry:9.2f} {sl:9.2f} {tp:9.2f} "
              f"{'WIN' if net_r>0 else 'LOSS':>7s} {net_r:+8.2f} {note}")

    print(f"\nTotale segnali nella finestra: {n_shown}  vinti={n_win}  persi={n_lose}  sumR netto={sum_r:+.2f}")


if __name__ == "__main__":
    main()
