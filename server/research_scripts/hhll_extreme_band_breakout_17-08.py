#!/usr/bin/env python3
"""
17/08 - spunto da "HHLL" (HPotter, TradingView). Non e' mean-reversion
come il nostro BOLLINGER: le bande usate sono offset di un'ulteriore
ampiezza oltre le Bollinger standard (arrivano a 4 deviazioni standard,
non 2), e con reverse=true (default dello script) la rottura della banda
estrema fa entrare NELLA direzione della rottura, non contro - breakout
su volatilita' estrema con continuazione, mai provato prima (diverso sia
da BOLLINGER 2sd mean-reversion sia da BB_SQUEEZE che aspetta prima una
compressione).
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import backtest as bt

BB_LEN = 29
LOOKBACK_ER, THR_ER = 4000, 0.045
MAX_HOLD = 200


def hlc3_series(candles):
    return [(c["high"] + c["low"] + c["close"]) / 3.0 for c in candles]


def rolling_std_mean(vals, n):
    out_mean = [None] * len(vals)
    out_std = [None] * len(vals)
    for i in range(len(vals)):
        if i + 1 < n:
            continue
        window = vals[i - n + 1:i + 1]
        m = sum(window) / n
        var = sum((x - m) ** 2 for x in window) / n
        out_mean[i] = m
        out_std[i] = var ** 0.5
    return out_mean, out_std


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
        typical = hlc3_series(candles)
        mean, std = rolling_std_mean(typical, BB_LEN)
        n = len(candles)

        # bande esterne: basis +/- 4*std (2 bande di larghezza 2*std oltre la basis)
        outer_hi = [(mean[i] + 4 * std[i]) if mean[i] is not None else None for i in range(n)]
        outer_lo = [(mean[i] - 4 * std[i]) if mean[i] is not None else None for i in range(n)]

        pos_state = [0] * n
        for i in range(1, n):
            if outer_hi[i - 1] is None or outer_lo[i - 1] is None:
                pos_state[i] = pos_state[i - 1]
                continue
            if candles[i]["low"] < outer_lo[i - 1]:
                pos_state[i] = 1
            elif candles[i]["high"] > outer_hi[i - 1]:
                pos_state[i] = -1
            else:
                pos_state[i] = pos_state[i - 1]

        trades = []
        for i in range(max(BB_LEN + 5, LOOKBACK_ER + 50), n - 2):
            a = atr[i]
            if not a:
                continue
            if pos_state[i] == pos_state[i - 1]:
                continue  # solo sul cambio di stato (evento)
            raw_sig = pos_state[i]
            sig = -raw_sig  # reverse=true: rottura ribassista (pos=1) -> short (-1) e viceversa
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

        print(f"--- HHLL breakout su banda estrema (4sd), TF={tf}: {len(trades)} trade grezzi ---", flush=True)
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
