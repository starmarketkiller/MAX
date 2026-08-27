#!/usr/bin/env python3
"""25/08 - raccoglie trade a livello di portafoglio per la composizione
REALE di NEXUS v3.0 (non il vecchio set di ricerca Python usato dal
Monte Carlo di ieri sera, che includeva TURTLE_SOUP/LDN_REVERSAL nella
loro forma Python - oggi disattivate nel motore vero).

Due famiglie di generatori:
1. "Generiche ATR-SLTP" (NXS_DefaultSLTP, HTF gate + breakeven + trailing
   + TP fisso) - riusa simulate() di live_recipe_trailing_verify_25-08.py,
   con i valori CORRENTI (non quelli con cui lo script era stato scritto -
   diversi sono cambiati dopo: EMA_PULLBACK TF H1->H4, vari trailK) letti
   da NXS_StrategyProfiles.mqh stanotte. TrailForceOff applicato dove
   presente (ADX_RSI, OTE_CONT - trail_k=0 anche se la tabella TrailK
   avrebbe un valore, perche' il force-off vince per costruzione).
2. "Stop nativo" (segnale strutturale, slPrice/tpPrice diretti) - non
   rientrano nel simulate() generico, riusano le funzioni gia' scritte
   stanotte per MALAYSIAN_SNR (M30, corretta oggi) e per STRUCT_REACT/
   ELLIOTT (H4 BUY-only, corrette oggi).

Esclude esplicitamente: CRT, TURTLE_SOUP, AMD_CONT, LDN_REVERSAL, CISD,
IFVG, FVG_MIT, OB_MIT, LIQ_VOID, RANGE_FADE (disattivate stanotte).
Include con avvertenza: LIQ_SWEEP, LONDON_BO, ICHIMOKU, ORDER_BLOCK,
BB_SQUEEZE (live-abilitate ma non riverificate stanotte con questo
rigore - usa bt.STRATEGIES nella forma esistente, stesso rischio di
mismatch nativo-vs-Python gia' visto per altre; qui trattate come "resto
del catalogo", non nucleo verificato) e DISP_REBAL/SH_BMS_RTO/
SMS_BMS_RTO/WEEKLY_EXP (live-faithful ma risultati borderline di
stanotte, incluse cosi' come sono).
"""
import sys, os, importlib.util
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import backtest as bt

HERE = os.path.dirname(os.path.abspath(__file__))


def _load(modname, filename):
    spec = importlib.util.spec_from_file_location(modname, os.path.join(HERE, filename))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


lrv = _load("lrv", "live_recipe_trailing_verify_25-08.py")   # simulate() generico ATR-SLTP
msnr = _load("msnr", "malaysian_snr_live_signal_25-08.py")   # MALAYSIAN_SNR nativo

# name: (tf, sl_mult, tp_mult, htf, beR, trail_k) - valori CORRENTI da
# NXS_StrategyProfiles.mqh (25/08), trail_k=0 dove TrailForceOff=true.
CURRENT_GENERIC_PROFILES = {
    "ADX_RSI":      ("1d", 1.0, 10.0, True,  1.5, 0.0),   # TrailForceOff
    "SAR":          ("4h", 1.0, 6.0,  False, 0.0, 2.0),
    "MACD":         ("4h", 2.0, 8.0,  True,  1.0, 3.0),
    "FVG_CONT":     ("4h", 1.5, 6.0,  True,  1.5, 3.0),
    "EMA_PULLBACK": ("4h", 1.5, 4.0,  True,  0.0, 2.5),   # TF H1->H4 cambiato dopo
    "OTE_CONT":     ("1d", 2.0, 4.5,  True,  0.0, 0.0),   # TrailForceOff
    "TSI":          ("1d", 2.0, 6.0,  True,  1.0, 3.0),
    "RSI_DIV":      ("1h", 1.0, 4.5,  False, 0.0, 1.5),
    "BOLLINGER":    ("1d", 1.0, 2.0,  False, 0.0, 2.0),
    "BREAKOUT_ACC": ("1d", 1.0, 4.5,  True,  0.0, 2.5),
}


def collect_generic(preset="retail_standard"):
    """Trade per le 10 strategie ATR-generiche, con costo gia' applicato
    e campi compatibili col formato di correlation_updated_25-08.py
    (strat/open_time/close_time/risk_dist/net_r)."""
    out = []
    for name, (tf, slm, tpm, htf, beR, trailk) in CURRENT_GENERIC_PROFILES.items():
        if name not in bt.STRATEGIES:
            print(f"  [skip] {name} non in bt.STRATEGIES", flush=True)
            continue
        trades = lrv.simulate(name, tf, slm, tpm, htf, beR, trailk)
        candles, _, _ = lrv.get_data(tf)
        # simulate() non porta il timestamp - lo ricostruiamo cercando
        # l'indice del candle con quell'open (unico per costruzione: e'
        # sempre l'open della barra successiva al segnale).
        open_by_price = {}
        for c in candles:
            open_by_price.setdefault(c["open"], []).append(c["time"])
        net = lrv.net_series(trades, preset)
        for t, r in zip(trades, net):
            times = open_by_price.get(t["entry"])
            ot = times[0] if times else None
            out.append({"strat": name, "open_time": ot, "close_time": ot,
                        "risk_dist": t["risk_dist"], "net_r": r})
        print(f"  {name:14s} tf={tf:3s} n={len(trades):5d}", flush=True)
    return out


def _build_snr_context_fn():
    """snr_context() in malaysian_snr_live_signal_25-08.py e' annidata
    dentro main() (chiusura su h4_close/week_close/ecc.) - non importabile
    dall'esterno. Qui ricostruiamo lo stesso contesto in modo autonomo,
    stessa logica esatta, per riuso da questo script."""
    import bisect
    from datetime import datetime
    candlesH4, _ = bt._fetch_real("XAUUSD", "4h", 40000)
    candlesD1, _ = bt._fetch_real("XAUUSD", "1d", 4000)
    indH4 = bt._prep(candlesH4)
    atrH4_arr = indH4["atr"]
    h4_times = [c["time"] for c in candlesH4]
    h4_close = [c["close"] for c in candlesH4]
    h4_high = [c["high"] for c in candlesH4]
    h4_low = [c["low"] for c in candlesH4]
    d1_times = [c["time"] for c in candlesD1]
    d1_close = [c["close"] for c in candlesD1]
    week_order, week_close, week_end_time = [], {}, {}
    for c in candlesD1:
        dt = datetime.strptime(c["time"].split(" ")[0], "%Y-%m-%d")
        k = msnr.week_key(dt)
        if k not in week_close:
            week_order.append(k)
        week_close[k] = c["close"]
        week_end_time[k] = c["time"]
    weekly_closes_seq = [week_close[k] for k in week_order]
    week_end_seq = [week_end_time[k] for k in week_order]

    def snr_context(t):
        j = bisect.bisect_right(h4_times, t) - 1
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
        wk = bisect.bisect_right(week_end_seq, t) - 1
        if wk < 7:
            w1Hi = w1Lo = 0
        else:
            wwin = weekly_closes_seq[wk - 7:wk + 1]
            w1Hi, w1Lo = max(wwin), min(wwin)
        h4C1 = h4_close[j]
        h4C4 = h4_close[j - 3] if j >= 3 else h4C1
        d1j = bisect.bisect_right(d1_times, t) - 1
        if d1j < 2:
            return None
        d1C1, d1C2 = d1_close[d1j], d1_close[d1j - 1]
        storyBull = h4C1 > h4C4 and d1C1 >= d1C2
        storyBear = h4C1 < h4C4 and d1C1 <= d1C2
        return h4Hi, h4Lo, a, freshHi, freshLo, w1Hi, w1Lo, storyBull, storyBear

    return snr_context


def collect_malaysian_snr_m30(preset="retail_standard"):
    snr_context = _build_snr_context_fn()
    candlesM30, _ = bt._fetch_real("XAUUSD", "30m", 130000)
    ind = bt._prep(candlesM30)
    atr = ind["atr"]
    n = len(candlesM30)
    closes = [c["close"] for c in candlesM30]
    opens = [c["open"] for c in candlesM30]
    lows = [c["low"] for c in candlesM30]
    highs = [c["high"] for c in candlesM30]
    times = [c["time"] for c in candlesM30]
    out_raw = []
    for i in range(30, n - 2):
        a = atr[i]
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
        entry = candlesM30[entry_i]["open"]
        rd = abs(entry - sl)
        if rd <= 0:
            continue
        tp = entry + sig * 2.3 * a
        exit_r = None
        for j2 in range(entry_i + 1, min(entry_i + 1 + 800, n)):
            hi, lo = highs[j2], lows[j2]
            if sig == 1:
                if lo <= sl: exit_r = (sl - entry) / rd; break
                if hi >= tp: exit_r = (tp - entry) / rd; break
            else:
                if hi >= sl: exit_r = (entry - sl) / rd; break
                if lo <= tp: exit_r = (entry - tp) / rd; break
        if exit_r is None:
            continue
        out_raw.append({"entry": entry, "risk_dist": rd, "raw_r": exit_r, "time": times[entry_i]})
    net = msnr.net_series(out_raw, preset)
    out = [{"strat": "MALAYSIAN_SNR", "open_time": t["time"], "close_time": t["time"],
            "risk_dist": t["risk_dist"], "net_r": r} for t, r in zip(out_raw, net)]
    print(f"  MALAYSIAN_SNR  tf=M30 n={len(out)}", flush=True)
    return out


def collect_struct_react_h4_buy(preset="retail_standard"):
    trades = lrv.simulate("STRUCT_REACT", "4h", 2.0, 6.0, True, 0.0, 0.0)
    candles, _, _ = lrv.get_data("4h")
    open_by_price = {}
    for c in candles:
        open_by_price.setdefault(c["open"], []).append(c["time"])
    # BUY-only: bt.STRATEGIES["STRUCT_REACT"] non separa la direzione qui;
    # filtriamo dopo simulate() usando dir=+1 implicito nel segno di risk
    # non disponibile - rifacciamo con firma dir esplicita non prevista da
    # simulate(). Approssimazione dichiarata: usiamo TUTTI i trade (sim+dir)
    # e li filtriamo BUY-only ricalcolando il segnale direttamente.
    sig_fn = bt.STRATEGIES["STRUCT_REACT"]
    ind_data = lrv.get_data("4h")
    _, ind, ema200 = ind_data
    atr = ind["atr"]
    n = len(candles)
    out_raw = []
    for i in range(250, n - 2):
        a = atr[i]
        if not a:
            continue
        sig = sig_fn(candles, ind, i)
        if sig != 1:   # BUY-only
            continue
        if ema200[i] and ema200[i] > 0 and ind["close"][i] < ema200[i]:
            continue
        entry = candles[i + 1]["open"]
        rd = 2.0 * a
        sl = entry - rd
        tp = entry + 6.0 * a
        exit_r = None
        for j in range(i + 2, min(i + 2 + 400, n)):
            hi, lo = candles[j]["high"], candles[j]["low"]
            if lo <= sl: exit_r = (sl - entry) / rd; break
            if hi >= tp: exit_r = (tp - entry) / rd; break
        if exit_r is None:
            continue
        out_raw.append({"entry": entry, "risk_dist": rd, "raw_r": exit_r, "time": candles[i + 1]["time"]})
    net = lrv.net_series(out_raw, preset)
    out = [{"strat": "STRUCT_REACT", "open_time": t["time"], "close_time": t["time"],
            "risk_dist": t["risk_dist"], "net_r": r} for t, r in zip(out_raw, net)]
    print(f"  STRUCT_REACT   tf=4h  n={len(out)} (BUY-only)", flush=True)
    return out


def main():
    print("Raccolta trade generiche (ATR-SLTP, ricetta live corrente)...", flush=True)
    trades = collect_generic()
    print("Raccolta MALAYSIAN_SNR (M30, nativo)...", flush=True)
    trades += collect_malaysian_snr_m30()
    print("Raccolta STRUCT_REACT (H4 BUY-only)...", flush=True)
    trades += collect_struct_react_h4_buy()
    print(f"\nTotale trade raccolti: {len(trades)}", flush=True)
    from collections import defaultdict
    by = defaultdict(list)
    for t in trades:
        by[t["strat"]].append(t)
    for s in sorted(by, key=lambda k: -len(by[k])):
        rs = [t["net_r"] for t in by[s]]
        g = sum(r for r in rs if r > 0)
        l = -sum(r for r in rs if r < 0)
        pf = g / l if l > 0 else float("inf")
        print(f"  {s:16s} n={len(by[s]):5d} PF={pf:.2f}", flush=True)
    import json
    trades_sorted = sorted([t for t in trades if t["open_time"]], key=lambda t: t["open_time"])
    with open(os.path.join(HERE, "nexus_v3_portfolio_trades_25-08.json"), "w") as f:
        json.dump(trades_sorted, f)
    print(f"\nSalvato: nexus_v3_portfolio_trades_25-08.json ({len(trades_sorted)} trade con timestamp)", flush=True)


if __name__ == "__main__":
    main()
