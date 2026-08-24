#!/usr/bin/env python3
"""
24/08 (15) - portafoglio con la lista di baseline aggiornata di oggi,
stessa disciplina del 16/08 (curva equity unica in euro, tetto diretto
in euro sul rischio per trade, max 2 posizioni concorrenti - il
candidato piu' solido trovato il 16/08, vedi
portfolio_regime_sim_16-08.py da cui questo script riusa
simulate_portfolio_capped verbatim).

20 strategie (5 nucleo gia' note + 15 trovate/riverificate oggi), UNA
config per strategia (la migliore verificata, non la piu' vistosa) -
escluse deliberatamente TURTLE_SOUP (ribalta 3+ rifiuti precedenti, da
riverificare prima di fidarsene in portafoglio) e LDN_REVERSAL (campione
troppo sottile, 31 trade). Ogni strategia usa bt.STRATEGIES[name]
direttamente (non reimplementazioni a mano come nello script del 16/08)
per fedelta' con tutti i test di oggi.
"""
import sys, os, json, bisect
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import backtest as bt

THR_ER = 0.045
LOOKBACK_ER = {"4h": 1000, "1h": 4000, "1d": 120}
FLOOR_PCTL_DEFAULT = 0.3
MAX_HOLD = 200

RISK_EUR = 10.0
MAX_LOTS_CAP = 0.10
MAX_CONCURRENT = 2
START_EQUITY = 1000.0
MAX_RISK_EUR_CAP = 40.0

_CACHE = {}


def get_prepped(tf):
    if tf not in _CACHE:
        candles, src = bt._fetch_real("XAUUSD", tf, 110000 if tf != "1d" else 4000)
        ind = bt._prep(candles)
        _CACHE[tf] = (candles, ind)
    return _CACHE[tf]


def efficiency_ratio(closes, i, lookback):
    if i < lookback:
        return None
    net = abs(closes[i] - closes[i - lookback])
    total = sum(abs(closes[k] - closes[k - 1]) for k in range(i - lookback + 1, i + 1))
    return net / total if total > 0 else None


def atr_floor(atr_hist, pctl):
    if pctl is None or len(atr_hist) < 500:
        return None
    w = sorted(atr_hist[-2000:])
    return w[min(int(pctl * len(w)), len(w) - 1)]


# ---------- generatore generico: sig ATR-based, ER fisso, floor opzionale ----------
def gen_generic(name, tf, sl_mult, tp_mult, floor_pctl, buy_only=False):
    candles, ind = get_prepped(tf)
    atr, closes = ind["atr"], ind["close"]
    n = len(candles)
    lb_er = LOOKBACK_ER[tf]
    sig_fn = bt.STRATEGIES[name]
    atr_hist, out = [], []
    for i in range(max(300, lb_er + 50), n - 2):
        a = atr[i]
        if a:
            atr_hist.append(a)
        sig = sig_fn(candles, ind, i)
        if sig == 0 or not a:
            continue
        if buy_only and sig != 1:
            continue
        e = efficiency_ratio(closes, i, lb_er)
        if e is None or e < THR_ER:
            continue
        if floor_pctl is not None:
            floor = atr_floor(atr_hist, floor_pctl)
            if floor is None or a < floor:
                continue
        entry = candles[i + 1]["open"]
        sl = entry - sig * sl_mult * a
        tp = entry + sig * tp_mult * a
        rd = abs(entry - sl)
        if rd <= 0:
            continue
        exit_r, exit_j = None, None
        for j in range(i + 2, min(i + 2 + MAX_HOLD, n)):
            hi, lo = candles[j]["high"], candles[j]["low"]
            if sig == 1:
                if lo <= sl: exit_r, exit_j = (sl - entry) / rd, j; break
                elif hi >= tp: exit_r, exit_j = (tp - entry) / rd, j; break
            else:
                if hi >= sl: exit_r, exit_j = (entry - sl) / rd, j; break
                elif lo <= tp: exit_r, exit_j = (entry - tp) / rd, j; break
        if exit_r is None:
            continue
        out.append({"strat": name, "open_time": candles[i + 1]["time"],
                     "close_time": candles[exit_j]["time"], "entry": entry,
                     "risk_dist": rd, "raw_r": exit_r})
    return out


# ---------- LIQ_SWEEP: trailing 3.0xATR (doppiamente confermata) ----------
def gen_liq_sweep_trailing():
    candles, ind = get_prepped("4h")
    atr, closes = ind["atr"], ind["close"]
    n = len(candles)
    lb_er = LOOKBACK_ER["4h"]
    sig_fn = bt.STRATEGIES["LIQ_SWEEP"]
    atr_hist, out = [], []
    INIT_SL_MULT, TRAIL = 1.5, 3.0
    for i in range(max(300, lb_er + 50), n - 2):
        a = atr[i]
        if a:
            atr_hist.append(a)
        sig = sig_fn(candles, ind, i)
        if sig == 0 or not a:
            continue
        e = efficiency_ratio(closes, i, lb_er)
        if e is None or e < THR_ER:
            continue
        floor = atr_floor(atr_hist, FLOOR_PCTL_DEFAULT)
        if floor is None or a < floor:
            continue
        entry = candles[i + 1]["open"]
        rd = INIT_SL_MULT * a
        sl = entry - sig * rd
        extreme = entry
        exit_r, exit_j = None, None
        for j in range(i + 2, min(i + 2 + MAX_HOLD, n)):
            hi, lo = candles[j]["high"], candles[j]["low"]
            if sig == 1:
                if lo <= sl: exit_r, exit_j = (sl - entry) / rd, j; break
                extreme = max(extreme, hi)
                new_sl = extreme - TRAIL * a
                if new_sl > sl: sl = new_sl
            else:
                if hi >= sl: exit_r, exit_j = (entry - sl) / rd, j; break
                extreme = min(extreme, lo)
                new_sl = extreme + TRAIL * a
                if new_sl < sl: sl = new_sl
        if exit_r is None:
            j_last = min(i + 1 + MAX_HOLD, n - 1)
            last_close = candles[j_last]["close"]
            exit_r = (last_close - entry) / rd if sig == 1 else (entry - last_close) / rd
            exit_j = j_last
        out.append({"strat": "LIQ_SWEEP", "open_time": candles[i + 1]["time"],
                     "close_time": candles[exit_j]["time"], "entry": entry,
                     "risk_dist": rd, "raw_r": exit_r})
    return out


# ---------- STRUCT_REACT: BUY-only ----------
def gen_struct_react_buyonly():
    return gen_generic("STRUCT_REACT", "4h", 2.0, 6.0, FLOOR_PCTL_DEFAULT, buy_only=True)


# ---------- FVG_MIT: allineamento D1 al posto di ER ----------
def gen_fvg_mit_d1aligned():
    candles, ind = get_prepped("4h")
    atr = ind["atr"]
    n = len(candles)
    sig_fn = bt.STRATEGIES["FVG_MIT"]
    d1, _ = get_prepped("1d")
    d1_times = [c["time"] for c in d1]
    d1_close = [c["close"] for c in d1]
    d1_ema50 = bt.ema_series(d1_close, 50)
    out = []
    for i in range(max(1500, 250), n - 2):
        a = atr[i]
        if not a:
            continue
        sig = sig_fn(candles, ind, i)
        if sig == 0:
            continue
        t = candles[i]["time"]
        j_d1 = bisect.bisect_right(d1_times, t) - 1
        if j_d1 < 60 or not d1_ema50[j_d1]:
            continue
        d1_up = d1_close[j_d1] > d1_ema50[j_d1]
        if sig == 1 and not d1_up:
            continue
        if sig == -1 and d1_up:
            continue
        entry = candles[i + 1]["open"]
        sl = entry - sig * 1.5 * a
        tp = entry + sig * 4.0 * a
        rd = abs(entry - sl)
        if rd <= 0:
            continue
        exit_r, exit_j = None, None
        for k in range(i + 2, min(i + 2 + MAX_HOLD, n)):
            hi, lo = candles[k]["high"], candles[k]["low"]
            if sig == 1:
                if lo <= sl: exit_r, exit_j = (sl - entry) / rd, k; break
                elif hi >= tp: exit_r, exit_j = (tp - entry) / rd, k; break
            else:
                if hi >= sl: exit_r, exit_j = (entry - sl) / rd, k; break
                elif lo <= tp: exit_r, exit_j = (entry - tp) / rd, k; break
        if exit_r is None:
            continue
        out.append({"strat": "FVG_MIT", "open_time": candles[i + 1]["time"],
                     "close_time": candles[exit_j]["time"], "entry": entry,
                     "risk_dist": rd, "raw_r": exit_r})
    return out


# ---------- FVG_CONT_V2: stop nativo precalcolato ----------
def gen_fvg_cont_v2():
    candles, ind = get_prepped("4h")
    atr, closes = ind["atr"], ind["close"]
    n = len(candles)
    lb_er = LOOKBACK_ER["4h"]
    sig_fn = bt.STRATEGIES["FVG_CONT_V2"]
    atr_hist, out = [], []
    for i in range(max(300, lb_er + 50), n - 2):
        a = atr[i]
        if a:
            atr_hist.append(a)
        sig = sig_fn(candles, ind, i)
        if sig == 0 or not a:
            continue
        e = efficiency_ratio(closes, i, lb_er)
        if e is None or e < THR_ER:
            continue
        floor = atr_floor(atr_hist, FLOOR_PCTL_DEFAULT)
        if floor is None or a < floor:
            continue
        sl, tp = ind["fvg_v2_sl"][i], ind["fvg_v2_tp"][i]
        if sl is None or tp is None:
            continue
        entry = candles[i + 1]["open"]
        rd = abs(entry - sl)
        if rd <= 0:
            continue
        exit_r, exit_j = None, None
        for j in range(i + 2, min(i + 2 + MAX_HOLD, n)):
            hi, lo = candles[j]["high"], candles[j]["low"]
            if sig == 1:
                if lo <= sl: exit_r, exit_j = (sl - entry) / rd, j; break
                elif hi >= tp: exit_r, exit_j = (tp - entry) / rd, j; break
            else:
                if hi >= sl: exit_r, exit_j = (entry - sl) / rd, j; break
                elif lo <= tp: exit_r, exit_j = (entry - tp) / rd, j; break
        if exit_r is None:
            continue
        out.append({"strat": "FVG_CONT_V2", "open_time": candles[i + 1]["time"],
                     "close_time": candles[exit_j]["time"], "entry": entry,
                     "risk_dist": rd, "raw_r": exit_r})
    return out


# ---------- Z_SCORE_BREAKOUT: stop strutturale M5 ----------
def gen_zscore_breakout():
    candles, ind = get_prepped("1h")
    atr, closes = ind["atr"], ind["close"]
    n = len(candles)
    lb_er = LOOKBACK_ER["1h"]
    sig_fn = bt.STRATEGIES["Z_SCORE_BREAKOUT"]
    with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..",
                            "data_cache_m5", "dukascopy_xauusd_m5.json"), encoding="utf-8") as f:
        m5_data = json.load(f)
    m5_times = [c["time"] for c in m5_data]

    def m5_stop(sig, entry_time):
        j_entry = bisect.bisect_left(m5_times, entry_time)
        window = m5_data[max(0, j_entry - 12):j_entry]
        if len(window) < 3:
            return None
        return min(w["low"] for w in window) if sig == 1 else max(w["high"] for w in window)

    atr_hist, out = [], []
    for i in range(max(300, lb_er + 50), n - 2):
        a = atr[i]
        if a:
            atr_hist.append(a)
        sig = sig_fn(candles, ind, i)
        if sig == 0 or not a:
            continue
        e = efficiency_ratio(closes, i, lb_er)
        if e is None or e < THR_ER:
            continue
        floor = atr_floor(atr_hist, FLOOR_PCTL_DEFAULT)
        if floor is None or a < floor:
            continue
        entry_time = candles[i + 1]["time"]
        entry = candles[i + 1]["open"]
        stop = m5_stop(sig, entry_time)
        if stop is None:
            continue
        rd = abs(entry - stop)
        floor_dist = 0.3 * a
        if rd < floor_dist:
            rd = floor_dist
        if rd <= 0:
            continue
        tp = entry + sig * 4.0 * a
        exit_r, exit_j = None, None
        for j in range(i + 2, min(i + 2 + MAX_HOLD, n)):
            hi, lo = candles[j]["high"], candles[j]["low"]
            if sig == 1:
                if lo <= entry - rd: exit_r, exit_j = -1.0, j; break
                elif hi >= tp: exit_r, exit_j = (tp - entry) / rd, j; break
            else:
                if hi >= entry + rd: exit_r, exit_j = -1.0, j; break
                elif lo <= tp: exit_r, exit_j = (entry - tp) / rd, j; break
        if exit_r is None:
            continue
        out.append({"strat": "Z_SCORE_BREAKOUT", "open_time": candles[i + 1]["time"],
                     "close_time": candles[exit_j]["time"], "entry": entry,
                     "risk_dist": rd, "raw_r": exit_r})
    return out


# name, tf, sl, tp, floor_pctl (None per LONDON_BO/EMA_PULLBACK-D1 gia' verificati senza)
GENERIC_CONFIGS = [
    ("SAR", "4h", 1.5, 4.0, 0.3),
    ("MACD", "4h", 1.5, 4.0, 0.3),
    ("FVG_CONT", "4h", 1.5, 4.0, 0.3),
    ("LONDON_BO", "4h", 1.0, 4.5, None),
    ("DONCHIAN_TURTLE", "4h", 1.5, 4.0, 0.3),
    ("ADX_RSI", "4h", 1.5, 4.0, 0.3),
    ("MALAYSIAN_SNR_BREAKOUT", "4h", 1.5, 4.0, 0.3),
    ("DARVAS_BOX", "4h", 1.5, 4.0, 0.3),
    ("AMD_CONT", "4h", 1.5, 4.0, 0.3),
    ("SAR_FLIP", "4h", 1.5, 4.0, 0.3),
    ("EMA_PULLBACK", "1d", 1.5, 6.0, 0.2),
    ("SAR_ADX20", "4h", 1.5, 4.0, 0.3),
    ("BREAKOUT_ACC", "4h", 1.5, 4.0, 0.3),
    ("OTE_CONT", "4h", 1.0, 6.0, 0.3),
    ("TSI", "4h", 1.0, 6.0, 0.3),
]

SPECIAL_GENERATORS = [gen_liq_sweep_trailing, gen_struct_react_buyonly,
                      gen_fvg_mit_d1aligned, gen_fvg_cont_v2, gen_zscore_breakout]


def collect_all_trades(preset):
    all_trades = []
    for name, tf, sl_m, tp_m, floor_pctl in GENERIC_CONFIGS:
        raw = gen_generic(name, tf, sl_m, tp_m, floor_pctl)
        for t in raw:
            cost = bt.scaled_cost_for_price(preset, t["entry"])
            cost_r = min((cost["spread_price"] + cost["slippage_price"]) / t["risk_dist"], bt.MAX_COST_R_PER_TRADE)
            t["net_r"] = t["raw_r"] - cost_r
        all_trades.extend(raw)
    for gen in SPECIAL_GENERATORS:
        raw = gen()
        for t in raw:
            cost = bt.scaled_cost_for_price(preset, t["entry"])
            cost_r = min((cost["spread_price"] + cost["slippage_price"]) / t["risk_dist"], bt.MAX_COST_R_PER_TRADE)
            t["net_r"] = t["raw_r"] - cost_r
        all_trades.extend(raw)
    all_trades.sort(key=lambda t: t["open_time"])
    return all_trades


def simulate_portfolio_capped(trades, start_equity, risk_eur, max_lots_cap, max_concurrent, max_risk_eur_cap):
    equity = start_equity
    peak = start_equity
    max_dd_pct = 0.0
    open_positions = []
    n_taken, n_skipped_bucket, n_skipped_cap = 0, 0, 0
    per_strat_pnl = {}
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
        if actual_risk_eur > max_risk_eur_cap:
            n_skipped_cap += 1
            continue
        open_positions.append(t["close_time"])
        pnl_eur = t["net_r"] * actual_risk_eur
        equity += pnl_eur
        peak = max(peak, equity)
        if peak > 0:
            max_dd_pct = max(max_dd_pct, (peak - equity) / peak * 100)
        n_taken += 1
        per_strat_pnl[t["strat"]] = per_strat_pnl.get(t["strat"], 0.0) + pnl_eur
    return {"final_equity": equity, "max_dd_pct": max_dd_pct, "n_taken": n_taken,
            "n_skipped_bucket": n_skipped_bucket, "n_skipped_cap": n_skipped_cap,
            "net_pnl": equity - start_equity, "per_strat_pnl": per_strat_pnl}


def main():
    for preset in ("retail_standard", "ecn"):
        print(f"\n=== Portafoglio 20 strategie, {preset} ===", flush=True)
        trades = collect_all_trades(preset)
        by_strat = {}
        for t in trades:
            by_strat[t["strat"]] = by_strat.get(t["strat"], 0) + 1
        print(f"  trade totali: {len(trades)}  per strategia: {by_strat}", flush=True)
        res = simulate_portfolio_capped(trades, START_EQUITY, RISK_EUR, MAX_LOTS_CAP,
                                         MAX_CONCURRENT, MAX_RISK_EUR_CAP)
        print(f"  conto=EUR{START_EQUITY:.0f} rischio=EUR{RISK_EUR:.0f}/trade tetto_lotti={MAX_LOTS_CAP} "
              f"tetto_rischio=EUR{MAX_RISK_EUR_CAP:.0f} max_concorrenti={MAX_CONCURRENT}", flush=True)
        print(f"  eseguiti={res['n_taken']}  scartati_bucket={res['n_skipped_bucket']}  "
              f"scartati_tetto={res['n_skipped_cap']}  finale=EUR{res['final_equity']:.2f}  "
              f"netPnL=EUR{res['net_pnl']:.2f}  maxDD={res['max_dd_pct']:.1f}%", flush=True)
        print("  contributo per strategia (EUR):", flush=True)
        for name, pnl in sorted(res["per_strat_pnl"].items(), key=lambda kv: -kv[1]):
            print(f"    {name:26s} {pnl:+9.2f}", flush=True)


if __name__ == "__main__":
    main()
