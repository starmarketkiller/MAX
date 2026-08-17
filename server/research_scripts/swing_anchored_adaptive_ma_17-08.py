#!/usr/bin/env python3
"""
17/08 - spunto da "Dynamic Swing Anchored VWAP" (Zeiierman, TradingView).
Il VWAP vero non e' testabile: richiede volume reale, XAUUSD OTC ha solo
tick-volume (proxy inaffidabile, stesso limite gia' segnalato per Wyckoff
e per l'idea originale). Estratta la parte INDIPENDENTE dal volume, mai
provata prima: una media mobile che si RIANCORA a ogni nuovo swing (non
un periodo fisso come le nostre EMA9/20/50/200) con velocita' di
adattamento che si stringe quando la volatilita' (ATR) sale.

Segnale: incrocio del prezzo con questa media adattiva ancorata.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import backtest as bt
import math

PRD = 50          # finestra di rilevamento swing
BASE_APT = 20.0    # periodo base di adattamento (barre)
ATR_LEN = 50
VOL_BIAS = 10.0
LOOKBACK_ER, THR_ER = 4000, 0.045
MAX_HOLD = 200


def swing_anchored_ma(candles, atr):
    n = len(candles)
    highs = [c["high"] for c in candles]
    lows = [c["low"] for c in candles]
    closes = [c["close"] for c in candles]

    # rolling ATR average (RMA-style) per il rapporto di volatilita'
    atr_avg = [None] * n
    s = 0.0
    cnt = 0
    for i in range(n):
        if atr[i] is None:
            continue
        s += atr[i]
        cnt += 1
        if cnt > ATR_LEN:
            s -= atr[i - ATR_LEN] if atr[i - ATR_LEN] is not None else 0
            cnt = ATR_LEN
        atr_avg[i] = s / cnt

    ma_line = [None] * n
    dir_line = [0] * n
    ph = pl = None
    ph_idx = pl_idx = 0
    cur_dir = 0
    ma_val = None
    for i in range(n):
        if i >= PRD:
            win_hi = highs[i - PRD + 1:i + 1]
            win_lo = lows[i - PRD + 1:i + 1]
            new_hi = max(win_hi)
            new_lo = min(win_lo)
            if highs[i] == new_hi:
                ph, ph_idx = highs[i], i
            if lows[i] == new_lo:
                pl, pl_idx = lows[i], i
        new_dir = 1 if ph_idx > pl_idx else -1
        if new_dir != cur_dir:
            # nuovo swing confermato -> riancora la media al prezzo corrente
            ma_val = closes[i]
            cur_dir = new_dir
        else:
            a = atr[i]
            ratio = (a / atr_avg[i]) if (a and atr_avg[i]) else 1.0
            apt = BASE_APT / (ratio ** VOL_BIAS) if ratio > 0 else BASE_APT
            apt = max(5.0, min(300.0, apt))
            alpha = 1.0 - math.exp(-math.log(2.0) / max(1.0, apt))
            ma_val = (1 - alpha) * ma_val + alpha * closes[i] if ma_val is not None else closes[i]
        ma_line[i] = ma_val
        dir_line[i] = cur_dir
    return ma_line, dir_line


def efficiency_ratio(closes, i, lookback):
    if i < lookback:
        return None
    net = abs(closes[i] - closes[i - lookback])
    total = sum(abs(closes[k] - closes[k - 1]) for k in range(i - lookback + 1, i + 1))
    return net / total if total > 0 else None


def pf(rs):
    g = sum(r for r in rs if r > 0)
    l = -sum(r for r in rs if r < 0)
    return g / l if l > 0 else (float("inf") if g > 0 else 0.0)


def walk_forward(rs, nw=5):
    n = len(rs)
    if n < nw * 5:
        return None
    size = n // nw
    out = []
    for w in range(nw):
        seg = rs[w * size:(w + 1) * size] if w < nw - 1 else rs[w * size:]
        out.append((len(seg), pf(seg)))
    return out


def main():
    for tf in ("4h", "1h"):
        candles, src = bt._fetch_real("XAUUSD", tf, 110000)
        atr = bt.atr_series(candles, 14)
        closes = [c["close"] for c in candles]
        n = len(candles)
        ma_line, dir_line = swing_anchored_ma(candles, atr)

        trades = []
        for i in range(max(PRD + 5, LOOKBACK_ER + 50), n - 2):
            a = atr[i]
            if not a or ma_line[i] is None or ma_line[i - 1] is None:
                continue
            sig = 0
            # incrocio del prezzo con la media, nella direzione dello swing corrente
            if closes[i - 1] <= ma_line[i - 1] and closes[i] > ma_line[i] and dir_line[i] == 1:
                sig = 1
            elif closes[i - 1] >= ma_line[i - 1] and closes[i] < ma_line[i] and dir_line[i] == -1:
                sig = -1
            if sig == 0:
                continue
            e = efficiency_ratio(closes, i, LOOKBACK_ER)
            if e is None or e < THR_ER:
                continue
            entry = candles[i + 1]["open"]
            sl = entry - sig * 1.5 * a
            tp = entry + sig * 4.0 * a
            rd = abs(entry - sl)
            if rd <= 0:
                continue
            exit_r, exit_j = None, None
            for j in range(i + 2, min(i + 2 + MAX_HOLD, n)):
                hi, lo = candles[j]["high"], candles[j]["low"]
                if sig == 1:
                    if lo <= sl:
                        exit_r, exit_j = (sl - entry) / rd, j
                        break
                    elif hi >= tp:
                        exit_r, exit_j = (tp - entry) / rd, j
                        break
                else:
                    if hi >= sl:
                        exit_r, exit_j = (entry - sl) / rd, j
                        break
                    elif lo <= tp:
                        exit_r, exit_j = (entry - tp) / rd, j
                        break
            if exit_r is None:
                continue
            trades.append({"entry": entry, "risk_dist": rd, "raw_r": exit_r})

        print(f"--- Swing-Anchored Adaptive MA cross, TF={tf}: {len(trades)} trade grezzi ---", flush=True)
        for preset in ("retail_standard", "ecn"):
            net = []
            for t in trades:
                cost = bt.scaled_cost_for_price(preset, t["entry"])
                cost_r = min((cost["spread_price"] + cost["slippage_price"]) / t["risk_dist"], bt.MAX_COST_R_PER_TRADE)
                net.append(t["raw_r"] - cost_r)
            wf = walk_forward(net)
            wf_str = " | ".join(f"PF={p:.2f}" for _, p in wf) if wf else "n/a"
            n_pos = sum(1 for _, p in (wf or []) if p >= 1.0)
            print(f"  {preset:16s} aggPF={pf(net):.2f} sumR={sum(net):+.1f} "
                  f"finestre_PF>=1:{n_pos}/{len(wf) if wf else 0}  [{wf_str}]", flush=True)


if __name__ == "__main__":
    main()
