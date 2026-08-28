#!/usr/bin/env python3
"""
16/08 - estende il filtro di regime (Efficiency Ratio di Kaufman, lookback
~167 giorni su 4h, scalato 4x su 1h) trovato su SAR alle altre 4
"sopravvissute ai costi" (MACD, LONDON_BO, EMA_PULLBACK, FVG_CONT).
Replica la logica di ingresso vera di ciascuna (stessa gia' verificata
con gli scenari sintetici oggi), walk-forward 5 finestre, costi scalati,
retail+ECN, filtro applicato PRIMA dell'apertura (non un post-filtro su
trade_list, che e' troncata a 200 voci).
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import backtest as bt


def efficiency_ratio(closes, i, lookback):
    if i < lookback:
        return None
    net = abs(closes[i] - closes[i - lookback])
    total = sum(abs(closes[k] - closes[k - 1]) for k in range(i - lookback + 1, i + 1))
    return net / total if total > 0 else None


def walk(candles, atr, sig_fn, sl_mult, tp_mult, breakeven_r, preset, k0, k1,
         closes, lookback, thr, use_filter, max_hold=200):
    trades = []
    for i in range(max(250, k0), k1):
        sig = sig_fn(i)
        if sig == 0:
            continue
        if use_filter:
            er = efficiency_ratio(closes, i, lookback)
            if er is None or er < thr:
                continue
        a = atr[i]
        if not a:
            continue
        entry = candles[i]["close"]
        sl = entry - sig * sl_mult * a
        tp = entry + sig * tp_mult * a
        risk_dist = abs(entry - sl)
        if risk_dist <= 0:
            continue
        cost = bt.scaled_cost_for_price(preset, entry)
        cost_r = min((cost["spread_price"] + cost["slippage_price"]) / risk_dist, bt.MAX_COST_R_PER_TRADE)
        cur_sl = sl
        be_armed = False
        exit_r = None
        for j in range(i + 1, min(i + max_hold, len(candles) - 1) + 1):
            hi, lo = candles[j]["high"], candles[j]["low"]
            if breakeven_r > 0 and not be_armed:
                fav = ((hi - entry) if sig == 1 else (entry - lo)) / risk_dist
                if fav >= breakeven_r:
                    cur_sl = entry
                    be_armed = True
            if sig == 1:
                if lo <= cur_sl:
                    exit_r = (cur_sl - entry) / risk_dist
                    break
                elif hi >= tp:
                    exit_r = (tp - entry) / risk_dist
                    break
            else:
                if hi >= cur_sl:
                    exit_r = (entry - cur_sl) / risk_dist
                    break
                elif lo <= tp:
                    exit_r = (entry - tp) / risk_dist
                    break
        if exit_r is None:
            continue
        trades.append(exit_r - cost_r)
    wins = sum(t for t in trades if t > 0)
    losses = -sum(t for t in trades if t < 0)
    pf = wins / losses if losses > 0 else None
    return pf, len(trades)


def build_sar(candles):
    closes = [c["close"] for c in candles]
    psar, _ = bt.psar_series(candles)
    ema9 = bt.ema_series(closes, 9)
    ema21 = bt.ema_series(closes, 21)

    def sig(i):
        if i < 21 or psar[i] is None or ema9[i] is None or ema21[i] is None:
            return 0
        px = closes[i]
        if psar[i] < px and ema9[i] > ema21[i]:
            return 1
        if psar[i] > px and ema9[i] < ema21[i]:
            return -1
        return 0
    return sig


def build_macd(candles):
    closes = [c["close"] for c in candles]
    ema12 = bt.ema_series(closes, 12)
    ema26 = bt.ema_series(closes, 26)
    macd_line, macd_signal = bt._macd_signal_series(ema12, ema26)
    ema200 = bt.ema_series(closes, 200)

    def sig(i):
        m, s, e = macd_line[i], macd_signal[i], ema200[i]
        if m is None or s is None or e is None:
            return 0
        px = closes[i]
        if m > s and m > 0 and px > e:
            return 1
        if m < s and m < 0 and px < e:
            return -1
        return 0
    return sig


def build_london_bo(candles):
    sess = bt._session_amd_series(candles)
    atr = bt.atr_series(candles, 14)

    def sig(i):
        if sess["session"][i] != "LONDON":
            return 0
        ah, al = sess["asian_hi"][i], sess["asian_lo"][i]
        if ah is None or al is None:
            return 0
        a = atr[i]
        if not a:
            return 0
        cur = candles[i]
        o1, c1, h1, l1 = cur["open"], cur["close"], cur["high"], cur["low"]
        body1 = abs(c1 - o1)
        range1 = h1 - l1
        if body1 < a * 0.5 or range1 <= 0:
            return 0
        clv_up = (c1 - l1) / range1
        clv_down = (h1 - c1) / range1
        if c1 > ah + a * 0.15 and clv_up >= 0.6:
            return 1
        if c1 < al - a * 0.15 and clv_down >= 0.6:
            return -1
        return 0
    return sig


def build_fvg_cont(candles):
    choch_ext = bt._external_choch_series(candles, factor=4, wing=3)

    def sig(i):
        if i < 3:
            return 0
        ext_trend = choch_ext[0][i]
        if candles[i]["low"] > candles[i - 2]["high"] and ext_trend == 1:
            return 1
        if candles[i]["high"] < candles[i - 2]["low"] and ext_trend == -1:
            return -1
        return 0
    return sig


def main():
    configs = [
        ("SAR", "4h", build_sar, 1.5, 4.0, 0.0, 1000),
        ("MACD", "4h", build_macd, 2.0, 8.0, 1.0, 1000),
        ("LONDON_BO", "4h", build_london_bo, 1.0, 4.5, 0.0, 1000),
        ("FVG_CONT", "4h", build_fvg_cont, 1.5, 6.0, 1.5, 1000),
    ]
    thr = 0.045

    for name, tf, builder, sl_mult, tp_mult, be_r, lookback in configs:
        candles, src = bt._fetch_real("XAUUSD", tf, 110000)
        atr = bt.atr_series(candles, 14)
        closes = [c["close"] for c in candles]
        n = len(candles)
        sig_fn = builder(candles)

        for preset in ["retail_standard", "ecn"]:
            print(f"\n=== {name} ({tf}), {preset} ===", flush=True)
            for w in range(5):
                k0, k1 = int(n * w / 5), int(n * (w + 1) / 5)
                pf_base, n_base = walk(candles, atr, sig_fn, sl_mult, tp_mult, be_r, preset,
                                        k0, k1, closes, lookback, thr, use_filter=False)
                pf_filt, n_filt = walk(candles, atr, sig_fn, sl_mult, tp_mult, be_r, preset,
                                        k0, k1, closes, lookback, thr, use_filter=True)
                print(f"  finestra {w}: base PF={pf_base} n={n_base}  |  "
                      f"con filtro PF={pf_filt} n={n_filt}", flush=True)


if __name__ == "__main__":
    main()
