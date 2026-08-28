#!/usr/bin/env python3
"""
17/08 - risposta a "su tutte le strategie, non puoi vedere tu da solo cosa
gli serve?": estende la classificazione stop-nativo-per-famiglia (fatta a
mano per 6 strategie in native_structural_stop_16-08.py) a TUTTO il resto
del catalogo non ancora testato in questa indagine, usando una
classificazione automatica per ispezione del codice sorgente di ogni
sig_* (bt.STRATEGIES), non a occhio:

- se la strategia legge una serie SL gia' precalcolata in ind (crt_sl,
  crt_filt_sl, shbms_v2_sl, ote_v2_sl, ob_v2_sl, fvg_v2_sl, fvgmitw_sl) ->
  quella e' gia' la sua "verita'" strutturale, usata cosi' com'e'.
- se il sorgente chiama _sweep_ext_at (diretto o tramite una funzione
  helper che lo chiama, es. sig_turtle_soup_choch -> sig_turtle_soup) ->
  famiglia "sweep": stop = wick dello sweep +/- 0.5xATR.
- se il pattern e' una candela di rejection (wick contro un livello) ->
  stop oltre il wick della barra stessa +/- 0.3xATR.
- se e' una rottura di un range/squeeze (BB_SQUEEZE) -> stop al livello
  appena rotto (l'altro lato del range pre-breakout).
- altrimenti (trend/momentum senza livello strutturale proprio) -> lo
  stop generico M5 (minimo/massimo ultime 12 candele M5) gia' confermato
  su SAR/MACD/ICHIMOKU.

Escluse esplicitamente: famiglia sessione 15m/M5-scalp (SCALP_*,
JUDAS_SWING, SILVER_BULLET*, NY_REVERSAL*, PO3, AMD_*, LDN_REVERSAL) -
il concetto "ultima ora M5" non ha senso alla loro scala nativa, gia'
molto piu' stretta; famiglia MALAYSIAN_SNR* - gia' chiusa nel vault
l'11/08 per motivi strutturali (segnale quasi tautologico), non un
problema di stop; RANGE_FADE/LIQ_VOID - proxy duplicati di BOLLINGER/
FVG_CONT gia' testate. Gia' testate in run precedenti (broad_16 o
native_6): SAR, MACD, ICHIMOKU, EMA_PULLBACK, LONDON_BO, FVG_CONT,
ADX_RSI, DONCHIAN_TURTLE, LIQ_SWEEP, TURTLE_SOUP_CHOCH, STRUCT_REACT,
RSI_DIV, BOLLINGER, SH_BMS_RTO_V2, ORDER_BLOCK, IFVG.
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import backtest as bt

LOOKBACK_ER = 4000
THR_ER = 0.045
MAX_HOLD_BARS = 200
SWEEP_BUFFER_ATR = 0.5
REJECT_BUFFER_ATR = 0.3


def efficiency_ratio(closes, i, lookback):
    if i < lookback:
        return None
    net = abs(closes[i] - closes[i - lookback])
    total = sum(abs(closes[k] - closes[k - 1]) for k in range(i - lookback + 1, i + 1))
    return net / total if total > 0 else None


# --- stop nativo generico M5 (famiglia trend/momentum) ---
def make_m5_stop(m5_data, m5_times):
    import bisect

    def m5_idx_from(t_str):
        return bisect.bisect_left(m5_times, t_str)

    def stop_fn(c, ind, i, sig, entry, atr, entry_time):
        j_entry = m5_idx_from(entry_time)
        j_start = max(0, j_entry - 12)
        window = m5_data[j_start:j_entry]
        if len(window) < 3:
            return None
        return min(w["low"] for w in window) if sig == 1 else max(w["high"] for w in window)
    return stop_fn


# --- famiglia sweep (wick dello sweep +/- buffer) ---
def stop_sweep_generic(c, ind, i, sig, entry, atr, entry_time):
    sw = bt._sweep_ext_at(c, ind, i)
    if not sw:
        return None
    if sig == 1:
        if sw["refLow"] is None:
            return None
        return sw["refLow"] - SWEEP_BUFFER_ATR * atr
    if sw["refHigh"] is None:
        return None
    return sw["refHigh"] + SWEEP_BUFFER_ATR * atr


def stop_turtle_soup_family(c, ind, i, sig, entry, atr, entry_time):
    r = bt._turtle_soup_sl_tp(c, ind, i, sig, entry, atr)
    return r[0] if r else None


# --- famiglia rejection wick (barra stessa) ---
def stop_rejection_wick(c, ind, i, sig, entry, atr, entry_time):
    cur = c[i]
    return cur["low"] - REJECT_BUFFER_ATR * atr if sig == 1 else cur["high"] + REJECT_BUFFER_ATR * atr


# --- famiglia squeeze breakout: stop all'altro lato del range appena rotto ---
def stop_bb_squeeze(c, ind, i, sig, entry, atr, entry_time):
    closes = ind["close"]
    hi = bt._hh(c, 20, i - 1)
    lo = bt._ll(c, 20, i - 1)
    if hi is None or lo is None:
        return None
    return lo - REJECT_BUFFER_ATR * atr if sig == 1 else hi + REJECT_BUFFER_ATR * atr


# --- native precomputato (gia' nel motore) ---
def make_native_ind_stop(key):
    def stop_fn(c, ind, i, sig, entry, atr, entry_time):
        return ind[key][i]
    return stop_fn


NATIVE_LIST = [
    ("CRT", 4.0, make_native_ind_stop("crt_sl")),
    ("CRT_MINSTOP_FILTER", 4.0, make_native_ind_stop("crt_filt_sl")),
    ("OTE_CONT_V2", 4.0, make_native_ind_stop("ote_v2_sl")),
    ("ORDER_BLOCK_V2", 4.0, make_native_ind_stop("ob_v2_sl")),
    ("FVG_CONT_V2", 4.0, make_native_ind_stop("fvg_v2_sl")),
    ("FVG_MIT_WINDOW", 4.0, make_native_ind_stop("fvgmitw_sl")),
]

SWEEP_LIST = [
    ("TURTLE_SOUP", 4.0, stop_turtle_soup_family),
    ("TURTLE_SOUP_CHOCH_NEAR", 4.0, stop_turtle_soup_family),
    ("TURTLE_SOUP_CHOCH_DBLBODY", 4.0, stop_turtle_soup_family),
    ("CISD_TRUE", 4.0, stop_sweep_generic),
    ("SH_BMS_RTO", 4.0, stop_sweep_generic),
    ("SMS_BMS_RTO", 4.0, stop_sweep_generic),
    ("SMS_BMS_RTO_CHOCH_WINDOW", 4.0, stop_sweep_generic),
]

REJECTION_LIST = [
    ("DISP_REBAL", 4.0, stop_rejection_wick),
]

SQUEEZE_LIST = [
    ("BB_SQUEEZE", 4.0, stop_bb_squeeze),
]

GENERIC_M5_NAMES = [
    "SAR_ADX20", "SAR_FLIP", "BJORGUM", "BREAKOUT_ACC", "DARVAS_BOX",
    "EMA_CROSS_BENCHMARK", "Z_SCORE_BREAKOUT", "IFVG_CHOCH_WINDOW",
    "FVG_MIT", "OB_MIT", "TSI", "TSI_EXTREME", "WEEKLY_EXP", "OTE_CONT",
    "THREE_BAR_DELIVERY_BREAK",
]


def collect_trades(name, tp_mult, stop_fn, candles, ind, atr, closes, n):
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
        stop = stop_fn(candles, ind, i, sig, entry, a, entry_time)
        if stop is None:
            continue
        risk_dist = abs(entry - stop)
        floor = 0.3 * a
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
        out.append({"entry": entry, "risk_dist": risk_dist, "raw_r": exit_r})
    return out


def pf(trades):
    g = sum(t for t in trades if t > 0)
    l = -sum(t for t in trades if t < 0)
    if l == 0:
        return float("inf") if g > 0 else 0.0
    return g / l


def walk_forward(trades_net, n_windows=5):
    n = len(trades_net)
    if n < n_windows * 5:
        return None
    size = n // n_windows
    out = []
    for w in range(n_windows):
        seg = trades_net[w * size: (w + 1) * size] if w < n_windows - 1 else trades_net[w * size:]
        out.append((len(seg), pf(seg), sum(seg)))
    return out


def run_one(name, tp_mult, stop_fn, candles, ind, atr, closes, n, tag):
    raw_trades = collect_trades(name, tp_mult, stop_fn, candles, ind, atr, closes, n)
    if len(raw_trades) < 20:
        print(f"{name:30s} [{tag:8s}] n={len(raw_trades):4d} -> troppo pochi trade, salto", flush=True)
        return
    print(f"\n== {name} [{tag}] n_raw_trades={len(raw_trades)}", flush=True)
    for preset in ("retail_standard", "ecn"):
        net_trades = []
        for t in raw_trades:
            cost = bt.scaled_cost_for_price(preset, t["entry"])
            cost_r = min((cost["spread_price"] + cost["slippage_price"]) / t["risk_dist"],
                         bt.MAX_COST_R_PER_TRADE)
            net_trades.append(t["raw_r"] - cost_r)
        agg_pf = pf(net_trades)
        wf = walk_forward(net_trades)
        wf_str = "n/a" if wf is None else " | ".join(f"PF={p:.2f}" for _, p, _ in wf)
        n_pos = sum(1 for _, p, _ in (wf or []) if p >= 1.0)
        print(f"  {preset:16s} aggPF={agg_pf:5.2f}  sumR={sum(net_trades):+7.1f}  "
              f"finestre_PF>=1: {n_pos}/{len(wf) if wf else 0}   [{wf_str}]", flush=True)


def main():
    import json
    candles, src = bt._fetch_real("XAUUSD", "1h", 110000)
    print(f"H1: {len(candles)} candele ({src}) {candles[0]['time']} -> {candles[-1]['time']}", flush=True)
    ind = bt._prep(candles)
    atr, closes, n = ind["atr"], ind["close"], len(candles)

    with open(os.path.join(os.path.dirname(__file__), "..", "data_cache_m5",
                            "dukascopy_xauusd_m5.json"), encoding="utf-8") as f:
        m5_data = json.load(f)
    m5_times = [c["time"] for c in m5_data]
    generic_stop = make_m5_stop(m5_data, m5_times)

    for name, tp_mult, stop_fn in NATIVE_LIST:
        run_one(name, tp_mult, stop_fn, candles, ind, atr, closes, n, "nativo")
    for name, tp_mult, stop_fn in SWEEP_LIST:
        run_one(name, tp_mult, stop_fn, candles, ind, atr, closes, n, "sweep")
    for name, tp_mult, stop_fn in REJECTION_LIST:
        run_one(name, tp_mult, stop_fn, candles, ind, atr, closes, n, "rejection")
    for name, tp_mult, stop_fn in SQUEEZE_LIST:
        run_one(name, tp_mult, stop_fn, candles, ind, atr, closes, n, "squeeze")
    for name in GENERIC_M5_NAMES:
        if name not in bt.STRATEGIES:
            print(f"{name}: non in STRATEGIES, salto", flush=True)
            continue
        run_one(name, 4.0, generic_stop, candles, ind, atr, closes, n, "generico")


if __name__ == "__main__":
    main()
