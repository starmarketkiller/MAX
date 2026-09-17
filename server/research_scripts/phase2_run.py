#!/usr/bin/env python3
import sys, os, json
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import backtest as bt
import phase2_causal_screening as pc

SYMBOL = "XAUUSD"
OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..",
                        "results", "phase2_causal_screening")
os.makedirs(OUT_DIR, exist_ok=True)


def analyze_events(events, candles, max_hold, label, discovery_frac=0.70):
    if not events:
        return {"label": label, "n": 0, "verdict_data": None}
    for e in events:
        oc = pc.r_outcome(candles, e["entry_i"], e["entry_price"], e["invalidation_price"],
                           1 if e["direction"] == "BUY" else -1, max_hold)
        e["outcome"] = oc
    n = len(events)
    split_i = int(n * discovery_frac)
    discovery, validation = events[:split_i], events[split_i:]

    def stats(evs):
        evs = [e for e in evs if e["outcome"]]
        if not evs:
            return {"n": 0}
        n_ = len(evs)
        wins = [e for e in evs if e["outcome"]["first_outcome"] == "PLUS_1R_FIRST"]
        losses = [e for e in evs if e["outcome"]["first_outcome"] == "MINUS_1R_FIRST"]
        ambiguous = [e for e in evs if e["outcome"]["first_outcome"] == "AMBIGUOUS_SAME_BAR"]
        censored = [e for e in evs if e["outcome"]["first_outcome"] == "CENSORED"]
        mean_mfe = sum(e["outcome"]["mfe_r"] for e in evs) / n_
        mean_mae = sum(e["outcome"]["mae_r"] for e in evs) / n_
        # expectancy in R: +1R per win, -1R per loss, 0 per censored/ambiguous
        # (ambiguo trattato conservativamente come ne' vinto ne' perso, non
        # scartato - dichiarato)
        exp_r = (len(wins) * 1.0 - len(losses) * 1.0) / n_
        win_rate = len(wins) / (len(wins) + len(losses)) * 100 if (wins or losses) else None
        buys = [e for e in evs if e["direction"] == "BUY"]
        sells = [e for e in evs if e["direction"] == "SELL"]
        def dir_exp(sub):
            w = sum(1 for e in sub if e["outcome"]["first_outcome"] == "PLUS_1R_FIRST")
            l = sum(1 for e in sub if e["outcome"]["first_outcome"] == "MINUS_1R_FIRST")
            return (w - l) / len(sub) if sub else None
        return {
            "n": n_, "wins": len(wins), "losses": len(losses), "ambiguous": len(ambiguous),
            "censored": len(censored), "win_rate_pct": round(win_rate, 1) if win_rate else None,
            "expectancy_R": round(exp_r, 3), "mean_MFE_R": round(mean_mfe, 3), "mean_MAE_R": round(mean_mae, 3),
            "buy_n": len(buys), "sell_n": len(sells),
            "buy_expectancy_R": round(dir_exp(buys), 3) if dir_exp(buys) is not None else None,
            "sell_expectancy_R": round(dir_exp(sells), 3) if dir_exp(sells) is not None else None,
            "avg_bars_to_target": round(sum(e["outcome"]["bars_to_target"] for e in wins) / len(wins), 1) if wins else None,
            "avg_bars_to_stop": round(sum(e["outcome"]["bars_to_stop"] for e in losses) / len(losses), 1) if losses else None,
        }

    return {
        "label": label, "n_total": n,
        "window": f"{events[0]['timestamp']} -> {events[-1]['timestamp']}",
        "discovery": stats(discovery), "validation": stats(validation),
        "discovery_window": f"{discovery[0]['timestamp']} -> {discovery[-1]['timestamp']}" if discovery else None,
        "validation_window": f"{validation[0]['timestamp']} -> {validation[-1]['timestamp']}" if validation else None,
    }


def main():
    results = {}

    # ---- H4 data + indicators (ipotesi 1, 2, 4, regime) ----
    print("Fetching H4 XAUUSD...", flush=True)
    candles_h4, src = bt._fetch_real(SYMBOL, "4h", 110000)
    ind_h4 = bt._prep(candles_h4)
    print(f"  {len(candles_h4)} candele H4, {candles_h4[0]['time']} -> {candles_h4[-1]['time']} (fonte: {src})")

    print("\n=== 1. Failed Breakout Fade ===")
    ev1 = pc.detect_failed_breakout_fade(candles_h4, ind_h4)
    base1 = pc.baseline_unfailed_breakouts(candles_h4, ind_h4)
    results["1_failed_breakout_fade"] = analyze_events(ev1, candles_h4, pc.MAX_HOLD_BARS_H4, "Failed Breakout Fade")
    results["1_baseline_continuation"] = analyze_events(base1, candles_h4, pc.MAX_HOLD_BARS_H4, "Baseline: unfailed breakout continuation")
    print(json.dumps(results["1_failed_breakout_fade"], indent=1, default=str))
    print(json.dumps(results["1_baseline_continuation"], indent=1, default=str))

    print("\n=== 2. Volatility Compression Percentile Breakout ===")
    ev2 = pc.detect_vol_compression_breakout(candles_h4, ind_h4)
    base2 = pc.baseline_expansion_no_compression(candles_h4, ind_h4)
    results["2_vol_compression_breakout"] = analyze_events(ev2, candles_h4, pc.MAX_HOLD_BARS_H4, "Volatility Compression Breakout")
    results["2_baseline_expansion_no_compression"] = analyze_events(base2, candles_h4, pc.MAX_HOLD_BARS_H4, "Baseline: expansion w/o prior compression")
    print(json.dumps(results["2_vol_compression_breakout"], indent=1, default=str))
    print(json.dumps(results["2_baseline_expansion_no_compression"], indent=1, default=str))

    print("\n=== 4. Displacement Continuation via Imbalance Stack ===")
    ev4 = pc.detect_displacement_stack(candles_h4, ind_h4)
    base4 = pc.baseline_single_gap(candles_h4, ind_h4)
    results["4_displacement_stack"] = analyze_events(ev4, candles_h4, pc.MAX_HOLD_BARS_H4, "Displacement Imbalance Stack")
    results["4_baseline_single_gap"] = analyze_events(base4, candles_h4, pc.MAX_HOLD_BARS_H4, "Baseline: single isolated FVG")
    print(json.dumps(results["4_displacement_stack"], indent=1, default=str))
    print(json.dumps(results["4_baseline_single_gap"], indent=1, default=str))

    # ---- F. Regime experiment ----
    print("\n=== F. Regime-Conditional Momentum Persistence (diagnostico) ===")
    regime = ind_h4["regime"]
    closes = ind_h4["close"]
    ROC_N, ROC_THRESH = 10, 0.01  # 1% in 10 barre H4 - soglia dichiarata ex-ante
    regime_events, non_regime_events = [], []
    n = len(candles_h4)
    for i in range(ROC_N + 5, n - 1):
        if closes[i - ROC_N] is None or closes[i - ROC_N] == 0:
            continue
        roc = (closes[i] - closes[i - ROC_N]) / closes[i - ROC_N]
        if abs(roc) < ROC_THRESH:
            continue
        direction = 1 if roc > 0 else -1
        atr_i = ind_h4["atr"][i]
        if not atr_i:
            continue
        prior_regime = regime[i - 1]  # barra PRECEDENTE chiusa, causale
        invalidation = closes[i] - direction * atr_i  # stop 1xATR, stesso per entrambi i bracci per confronto equo
        ev = {"timestamp": candles_h4[i]["time"], "direction": "BUY" if direction == 1 else "SELL",
              "entry_i": i, "entry_price": closes[i], "invalidation_price": invalidation, "atr": atr_i}
        # TRENDING dichiarato ex-ante = STRONG_TREND o WEAK_TREND (ADX>=20,
        # cioe' i due codici di _regime_series che rappresentano un trend
        # confermato, non la sola volatilita' o il ranging/choppy)
        is_trending = prior_regime in (bt._REGIME_STRONG_TREND, bt._REGIME_WEAK_TREND)
        if is_trending:
            regime_events.append(ev)
        else:
            non_regime_events.append(ev)
    results["F_regime_trending"] = analyze_events(regime_events, candles_h4, pc.MAX_HOLD_BARS_H4, "ROC momentum IN regime TRENDING")
    results["F_regime_not_trending"] = analyze_events(non_regime_events, candles_h4, pc.MAX_HOLD_BARS_H4, "ROC momentum OUTSIDE regime TRENDING")
    print(json.dumps(results["F_regime_trending"], indent=1, default=str))
    print(json.dumps(results["F_regime_not_trending"], indent=1, default=str))

    # ---- G. Volatility_Breakout (open-source minimal signal) ----
    print("\n=== G2. Volatility_Breakout minimal signal (dual-mode) ===")
    ev_volbrk_confirmed, ev_volbrk_fade = [], []
    N = 20
    for i in range(N + 3, n - 1):
        hh = max(c["high"] for c in candles_h4[i - N - 1:i - 1])
        ll = min(c["low"] for c in candles_h4[i - N - 1:i - 1])
        atr_i = ind_h4["atr"][i]
        if not atr_i:
            continue
        c_i = candles_h4[i]["close"]
        tr_i = candles_h4[i]["high"] - candles_h4[i]["low"]
        if c_i > hh:
            brk_dir = 1
        elif c_i < ll:
            brk_dir = -1
        else:
            continue
        confirmed = tr_i > 1.0 * atr_i   # soglia dichiarata ex-ante (1.0xATR, stessa unita' di misura di EXPANSION_MULT ma piu' permissiva perche' qui e' un gate binario per-evento, non una persistenza)
        if confirmed:
            direction, invalidation = brk_dir, (ll if brk_dir == 1 else hh)
            ev_volbrk_confirmed.append({"timestamp": candles_h4[i]["time"], "direction": "BUY" if direction == 1 else "SELL",
                                         "entry_i": i, "entry_price": c_i, "invalidation_price": invalidation, "atr": atr_i})
        else:
            direction, invalidation = -brk_dir, (hh if brk_dir == 1 else ll)
            ev_volbrk_fade.append({"timestamp": candles_h4[i]["time"], "direction": "BUY" if direction == 1 else "SELL",
                                    "entry_i": i, "entry_price": c_i, "invalidation_price": invalidation, "atr": atr_i})
    results["G2_volbreakout_confirmed"] = analyze_events(ev_volbrk_confirmed, candles_h4, pc.MAX_HOLD_BARS_H4, "Volatility_Breakout: confirmed breakout arm")
    results["G2_volbreakout_fade"] = analyze_events(ev_volbrk_fade, candles_h4, pc.MAX_HOLD_BARS_H4, "Volatility_Breakout: failed-breakout fade arm")
    print(json.dumps(results["G2_volbreakout_confirmed"], indent=1, default=str))
    print(json.dumps(results["G2_volbreakout_fade"], indent=1, default=str))

    # ---- M15 data (ipotesi 3, G1 Asian Range fade, G3 Weekly Day Reversal) ----
    print("\nFetching M15 (Dukascopy local cache) XAUUSD...", flush=True)
    m15 = bt._load_dukascopy_m15(SYMBOL)
    if m15:
        print(f"  {len(m15)} candele M15, {m15[0]['time']} -> {m15[-1]['time']}")
        print("\n=== 3. Session Range Compression -> London Open Expansion ===")
        ev3 = pc.detect_session_compression_expansion(m15)
        base3 = pc.baseline_london_no_compression(m15)
        m15_hold = 4 * 96  # ~4 giorni di calendario in barre M15 (96/giorno) - dichiarato ex-ante
        results["3_session_compression"] = analyze_m15_events(ev3, m15, m15_hold, "Session Compression -> London Expansion")
        results["3_baseline_no_compression"] = analyze_m15_events(base3, m15, m15_hold, "Baseline: London breakout w/o Asian compression")
        print(json.dumps(results["3_session_compression"], indent=1, default=str))
        print(json.dumps(results["3_baseline_no_compression"], indent=1, default=str))

        print("\n=== G1. Asian Range Breakout EA - minimal fade signal ===")
        ev_g1 = detect_asian_fade(m15)
        results["G1_asian_range_fade"] = analyze_m15_events(ev_g1, m15, m15_hold, "Asian Range false-breakout fade (open-source minimal)")
        print(json.dumps(results["G1_asian_range_fade"], indent=1, default=str))

        print("\n=== G3. Weekly Day Reversal EA - minimal signal (Monday reverses Friday) ===")
        ev_g3 = detect_weekly_reversal(m15)
        results["G3_weekly_reversal"] = analyze_m15_events(ev_g3, m15, 5 * 96, "Weekly Day Reversal: Monday fades Friday direction")
        print(json.dumps(results["G3_weekly_reversal"], indent=1, default=str))
    else:
        print("  ATTENZIONE: nessuna cache M15 Dukascopy disponibile - ipotesi 3, G1, G3 SALTATE (dichiarato, non finto)")

    out_path = os.path.join(OUT_DIR, "phase2_results.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, default=str)
    print(f"\nSalvato: {out_path}")


def analyze_m15_events(events, candles, max_hold, label):
    fixed = []
    for e in events:
        idx = None
        # trova l'indice della candela nel dataset (per timestamp)
        # ottimizzazione: gli eventi mantengono gia' 'candle', serve solo l'indice - ricostruito via ricerca lineare cache
        fixed.append(e)
    # per efficienza, pre-indicizza per timestamp
    ts_to_idx = {c["time"]: i for i, c in enumerate(candles)}
    for e in fixed:
        e["entry_i"] = ts_to_idx.get(e["timestamp"])
    fixed = [e for e in fixed if e["entry_i"] is not None]
    return analyze_events(fixed, candles, max_hold, label)


def detect_asian_fade(m15_candles, MIN_RANGE_PIP=10, MAX_RANGE_PIP=100):
    """Segnale minimo Asian Range Breakout EA (fade), separato da
    risk/execution dell'autore: chiusura M5/M15 fuori dal range asiatico
    poi richiusura dentro. Qui su M15 (dato disponibile), range 10-100 pip
    come nell'originale (dichiarato, valori dell'autore non ritarati)."""
    from collections import defaultdict
    PIP = 0.10
    by_date = defaultdict(list)
    for c in m15_candles:
        d = c["time"].split(" ")[0]
        by_date[d].append(c)
    events = []
    for d, bars in by_date.items():
        asian_bars = [c for c in bars if 0 <= int(c["time"].split(" ")[1].split(":")[0]) < 7]
        if not asian_bars:
            continue
        hi = max(c["high"] for c in asian_bars)
        lo = min(c["low"] for c in asian_bars)
        rng_pip = (hi - lo) / PIP
        if not (MIN_RANGE_PIP <= rng_pip <= MAX_RANGE_PIP):
            continue
        other_bars = sorted([c for c in bars if int(c["time"].split(" ")[1].split(":")[0]) >= 7], key=lambda c: c["time"])
        broke_out, breakout_extreme, breakout_dir = False, None, 0
        for c in other_bars:
            if not broke_out:
                if c["close"] > hi:
                    broke_out, breakout_dir, breakout_extreme = True, 1, c["high"]
                elif c["close"] < lo:
                    broke_out, breakout_dir, breakout_extreme = True, -1, c["low"]
                continue
            breakout_extreme = max(breakout_extreme, c["high"]) if breakout_dir == 1 else min(breakout_extreme, c["low"])
            back_inside = (breakout_dir == 1 and c["close"] < hi) or (breakout_dir == -1 and c["close"] > lo)
            if back_inside:
                direction = -breakout_dir
                events.append({"timestamp": c["time"], "direction": "BUY" if direction == 1 else "SELL",
                                "entry_price": c["close"], "invalidation_price": breakout_extreme})
                break
    events.sort(key=lambda e: e["timestamp"])
    return events


def detect_weekly_reversal(m15_candles):
    """Segnale minimo Weekly Day Reversal EA: direzione di venerdi' (D1,
    close-open) -> il lunedi' successivo scommette sul FADE (reversal) di
    quella direzione, non sulla continuazione. Scelta dichiarata ex-ante
    (non scelta dopo aver visto quale braccio rende meglio)."""
    from collections import defaultdict
    from datetime import datetime as dt_
    by_date = defaultdict(list)
    for c in m15_candles:
        d = c["time"].split(" ")[0]
        by_date[d].append(c)
    dates = sorted(by_date.keys())
    daily = {}
    for d in dates:
        bars = by_date[d]
        daily[d] = {"open": bars[0]["open"], "close": bars[-1]["close"]}
    events = []
    for d in dates:
        wd = dt_.strptime(d, "%Y-%m-%d").weekday()
        if wd != 0:  # 0 = lunedi'
            continue
        idx = dates.index(d)
        if idx == 0:
            continue
        prev_d = dates[idx - 1]
        prev_wd = dt_.strptime(prev_d, "%Y-%m-%d").weekday()
        if prev_wd != 4:  # deve essere venerdi' immediatamente precedente
            continue
        fri_dir = 1 if daily[prev_d]["close"] > daily[prev_d]["open"] else -1
        mon_bars = by_date[d]
        if not mon_bars:
            continue
        mon_open = mon_bars[0]["open"]
        direction = -fri_dir  # reversal
        atr_proxy = abs(daily[prev_d]["close"] - daily[prev_d]["open"])  # ampiezza di venerdi' come proxy ATR
        if atr_proxy <= 0:
            continue
        invalidation = mon_open - direction * atr_proxy
        events.append({"timestamp": mon_bars[0]["time"], "direction": "BUY" if direction == 1 else "SELL",
                        "entry_price": mon_open, "invalidation_price": invalidation})
    return events


if __name__ == "__main__":
    main()
