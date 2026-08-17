#!/usr/bin/env python3
"""
16/08 (6) - portafoglio in euro reali con SAR+MACD+ICHIMOKU (i 3
sopravvissuti veri di m5_structural_stop_broad_16-08.py) sullo stop
strutturale M5, stessa disciplina del pomeriggio
(portfolio_regime_sim_16-08.py): tetto diretto in euro sul rischio per
trade (oltre al minimo 0.01 lotti), walk-forward, due meta' della storia
separate. Domanda motivante: lo stop molto piu' stretto (mediana attesa
pochi dollari, contro ~$23 dello stop ATR) allevia il vincolo del lotto
minimo su un conto piccolo (EUR200-500)?
"""
import sys
import os
import json
import bisect
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import backtest as bt

with open(os.path.join(os.path.dirname(__file__), "..", "data_cache_m5",
                        "dukascopy_xauusd_m5.json"), encoding="utf-8") as f:
    M5 = json.load(f)
M5_TIMES = [c["time"] for c in M5]

SWING_BARS = 12
FLOOR_ATR = 0.3
LOOKBACK_ER = 4000
THR_ER = 0.045
MAX_HOLD_BARS = 200

STRAT_LIST = [("SAR", 4.0), ("MACD", 8.0), ("ICHIMOKU", 4.0)]


def efficiency_ratio(closes, i, lookback):
    if i < lookback:
        return None
    net = abs(closes[i] - closes[i - lookback])
    total = sum(abs(closes[k] - closes[k - 1]) for k in range(i - lookback + 1, i + 1))
    return net / total if total > 0 else None


def m5_idx_from(t_str):
    return bisect.bisect_left(M5_TIMES, t_str)


def m5_structural_stop(entry_time_str, direction):
    j_entry = m5_idx_from(entry_time_str)
    j_start = max(0, j_entry - SWING_BARS)
    window = M5[j_start:j_entry]
    if len(window) < 3:
        return None
    return min(c["low"] for c in window) if direction == 1 else max(c["high"] for c in window)


def collect_trades(name, tp_mult, candles, ind, atr, closes, n):
    sig_fn = bt.STRATEGIES[name]
    out = []
    for i in range(max(1500, LOOKBACK_ER + 50), n - 2):
        sig = sig_fn(candles, ind, i)
        if sig == 0:
            continue
        er = efficiency_ratio(closes, i, LOOKBACK_ER)
        if er is None or er < THR_ER:
            continue
        a = atr[i]
        if not a:
            continue
        entry_time = candles[i + 1]["time"]
        entry = candles[i + 1]["open"]
        stop = m5_structural_stop(entry_time, sig)
        if stop is None:
            continue
        risk_dist = abs(entry - stop)
        floor = FLOOR_ATR * a
        if risk_dist < floor:
            risk_dist = floor
        if risk_dist <= 0:
            continue
        tp = entry + sig * tp_mult * a
        exit_r, exit_j = None, None
        for j in range(i + 2, min(i + 2 + MAX_HOLD_BARS, n)):
            hi, lo = candles[j]["high"], candles[j]["low"]
            if sig == 1:
                if lo <= entry - risk_dist:
                    exit_r, exit_j = -1.0, j
                    break
                elif hi >= tp:
                    exit_r, exit_j = (tp - entry) / risk_dist, j
                    break
            else:
                if hi >= entry + risk_dist:
                    exit_r, exit_j = -1.0, j
                    break
                elif lo <= tp:
                    exit_r, exit_j = (entry - tp) / risk_dist, j
                    break
        if exit_r is None:
            continue
        out.append({"strat": name, "open_time": entry_time, "close_time": candles[exit_j]["time"],
                    "entry": entry, "risk_dist": risk_dist, "raw_r": exit_r})
    return out


def with_net_r(trades, preset):
    out = []
    for t in trades:
        cost = bt.scaled_cost_for_price(preset, t["entry"])
        cost_r = min((cost["spread_price"] + cost["slippage_price"]) / t["risk_dist"],
                     bt.MAX_COST_R_PER_TRADE)
        t2 = dict(t)
        t2["net_r"] = t["raw_r"] - cost_r
        out.append(t2)
    return out


def simulate_portfolio_capped(trades, start_equity, risk_eur, max_lots_cap, max_concurrent,
                               max_risk_eur_cap=None):
    equity, peak, max_dd_pct = start_equity, start_equity, 0.0
    open_positions = []
    n_taken, n_skipped_bucket, n_skipped_cap = 0, 0, 0
    for t in trades:
        if equity <= 0:
            break
        open_positions = [ct for ct in open_positions if ct > t["open_time"]]
        if len(open_positions) >= max_concurrent:
            n_skipped_bucket += 1
            continue
        lots = risk_eur / (100.0 * t["risk_dist"]) if t["risk_dist"] > 0 else 0
        lots = min(round(lots * 100) / 100.0, max_lots_cap)
        lots = max(lots, 0.01)
        actual_risk_eur = lots * 100 * t["risk_dist"]
        if max_risk_eur_cap is not None and actual_risk_eur > max_risk_eur_cap:
            n_skipped_cap += 1
            continue
        open_positions.append(t["close_time"])
        equity += t["net_r"] * actual_risk_eur
        peak = max(peak, equity)
        if peak > 0:
            max_dd_pct = max(max_dd_pct, (peak - equity) / peak * 100)
        n_taken += 1
    return {"final_equity": equity, "max_dd_pct": max_dd_pct, "n_taken": n_taken,
            "n_skipped_bucket": n_skipped_bucket, "n_skipped_cap": n_skipped_cap,
            "net_pnl": equity - start_equity}


def pctl(vals, p):
    if not vals:
        return None
    s = sorted(vals)
    k = int(len(s) * p)
    return s[min(k, len(s) - 1)]


def main():
    candles, src = bt._fetch_real("XAUUSD", "1h", 110000)
    ind = bt._prep(candles)
    atr, closes, n = ind["atr"], ind["close"], len(candles)
    print(f"H1: {len(candles)} candele ({src}) {candles[0]['time']} -> {candles[-1]['time']}", flush=True)

    all_raw = []
    for name, tp_mult in STRAT_LIST:
        trades = collect_trades(name, tp_mult, candles, ind, atr, closes, n)
        print(f"  {name}: {len(trades)} trade grezzi", flush=True)
        all_raw.extend(trades)
    all_raw.sort(key=lambda t: t["open_time"])

    risk_dists = [t["risk_dist"] for t in all_raw]
    print(f"\nDistribuzione risk_dist ($ per unita' di prezzo, stop M5): "
          f"p10={pctl(risk_dists,0.10):.2f} p50={pctl(risk_dists,0.50):.2f} "
          f"p90={pctl(risk_dists,0.90):.2f}  (per confronto, stop ATR nucleo: p10=13.64 p50=23.14 p90=61.09)",
          flush=True)
    # rischio forzato a lotto minimo (0.01) indipendente dal capitale
    forced = [0.01 * 100 * rd for rd in risk_dists]
    print(f"Rischio forzato a 0.01 lotti ($ per trade, indipendente dal capitale): "
          f"p10={pctl(forced,0.10):.2f} p50={pctl(forced,0.50):.2f} p90={pctl(forced,0.90):.2f}", flush=True)

    for preset in ("retail_standard", "ecn"):
        net_trades = with_net_r(all_raw, preset)
        print(f"\n=== Portafoglio SAR+MACD+ICHIMOKU (stop M5), {preset} ===", flush=True)
        for start_equity in (300.0, 500.0, 1000.0):
            for risk_eur in (10.0, 15.0):
                r = simulate_portfolio_capped(net_trades, start_equity, risk_eur,
                                               max_lots_cap=0.10, max_concurrent=2,
                                               max_risk_eur_cap=risk_eur * 3.0)
                print(f"  conto=EUR{start_equity:.0f} rischio=EUR{risk_eur:.0f}/trade "
                      f"tetto_cap=EUR{risk_eur*3:.0f}  trade={r['n_taken']:4d} "
                      f"scartati_bucket={r['n_skipped_bucket']:4d} scartati_cap={r['n_skipped_cap']:4d}  "
                      f"finale=EUR{r['final_equity']:8.2f}  netPnL=EUR{r['net_pnl']:8.2f}  "
                      f"maxDD={r['max_dd_pct']:5.1f}%", flush=True)

        # due meta' della storia, conto EUR300/rischio EUR10 (il caso realistico)
        mid = len(net_trades) // 2
        first_half, second_half = net_trades[:mid], net_trades[mid:]
        for label, seg in (("prima meta'", first_half), ("seconda meta'", second_half)):
            r = simulate_portfolio_capped(seg, 300.0, 10.0, max_lots_cap=0.10,
                                           max_concurrent=2, max_risk_eur_cap=30.0)
            print(f"  [{label}] n={len(seg):4d} finale=EUR{r['final_equity']:8.2f} "
                  f"netPnL=EUR{r['net_pnl']:8.2f} maxDD={r['max_dd_pct']:5.1f}%", flush=True)


if __name__ == "__main__":
    main()
