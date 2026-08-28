#!/usr/bin/env python3
"""
16/08 - simulazione di portafoglio: le 5 "sopravvissute ai costi" (SAR,
MACD, LONDON_BO, EMA_PULLBACK, FVG_CONT), ciascuna col filtro di regime
(Efficiency Ratio Kaufman, lookback ~167 giorni, soglia 0.045) trovato
oggi, unite su un'unica curva equity in EURO reali - non 5 backtest
separati. Rischio fisso per trade in euro, tetto lotti fisso (stessa
logica della simulazione CRT del pomeriggio), max 2 posizioni
contemporanee (bucket, conto piccolo).

Contratto: 1 oz per 0.01 lotto (confermato dall'utente). EUR~USD 1:1
(approssimazione dichiarata).
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import backtest as bt

RISK_EUR = 10.0
MAX_LOTS_CAP = 0.10        # stesso ordine di grandezza validato oggi su CRT per un conto €200-500
MAX_CONCURRENT = 2
START_EQUITY = 300.0


def efficiency_ratio(closes, i, lookback):
    if i < lookback:
        return None
    net = abs(closes[i] - closes[i - lookback])
    total = sum(abs(closes[k] - closes[k - 1]) for k in range(i - lookback + 1, i + 1))
    return net / total if total > 0 else None


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


def build_ema_pullback(candles):
    closes = [c["close"] for c in candles]
    ema20 = bt.ema_series(closes, 20)
    ema50 = bt.ema_series(closes, 50)
    atr = bt.atr_series(candles, 14)
    TREND_PERSIST, MIN_DIST_ATR, TOUCH_TOL_ATR = 5, 1.0, 0.15

    def sig(i):
        e20, e50 = ema20[i], ema50[i]
        a = atr[i]
        if e20 is None or e50 is None or not a or i < 13:
            return 0
        up = e20 > e50
        for k in range(TREND_PERSIST):
            idx, idx_p = i - k, i - k - 1
            e20k, e50k, e20kp = ema20[idx], ema50[idx], ema20[idx_p]
            if e20k is None or e50k is None or e20kp is None:
                return 0
            trend_ok = (e20k > e50k and e20k >= e20kp) if up else (e20k < e50k and e20k <= e20kp)
            if not trend_ok:
                return 0
        had_impulse = False
        for k in range(1, 12):
            idx = i - k
            e20k = ema20[idx]
            if e20k is None:
                continue
            pxk = candles[idx]["high"] if up else candles[idx]["low"]
            dist = (pxk - e20k) if up else (e20k - pxk)
            if dist >= a * MIN_DIST_ATR:
                had_impulse = True
                break
        if not had_impulse:
            return 0
        c1, o1, l1, h1 = closes[i], candles[i]["open"], candles[i]["low"], candles[i]["high"]
        tol = a * TOUCH_TOL_ATR
        if up:
            if l1 <= e20 + tol and c1 > e20 and c1 > o1 and c1 > e50:
                return 1
        else:
            if h1 >= e20 - tol and c1 < e20 and c1 < o1 and c1 < e50:
                return -1
        return 0
    return sig


CONFIGS_5 = [
    ("SAR", "4h", build_sar, 1.5, 4.0, 0.0),
    ("MACD", "4h", build_macd, 2.0, 8.0, 1.0),
    ("LONDON_BO", "4h", build_london_bo, 1.0, 4.5, 0.0),
    ("FVG_CONT", "4h", build_fvg_cont, 1.5, 6.0, 1.5),
    ("EMA_PULLBACK", "1h", build_ema_pullback, 1.5, 4.0, 0.0),
]
# 16/08 - EMA_PULLBACK tolta: R totale negativo su entrambi i preset costi
# anche col filtro di regime attivo (uniche delle 5 con PF<1), zavorra il
# portafoglio invece di aiutarlo - vedi vault.
CONFIGS_4 = [c for c in CONFIGS_5 if c[0] != "EMA_PULLBACK"]
CONFIGS = CONFIGS_4
LONG_LB = {"4h": 1000, "1h": 4000}
THR = 0.045


def collect_all_trades(preset):
    """Genera i trade (con filtro regime) per ogni strategia, poi li fonde
    in una lista unica ordinata per tempo di apertura."""
    all_trades = []
    for name, tf, builder, sl_mult, tp_mult, be_r in CONFIGS:
        candles, src = bt._fetch_real("XAUUSD", tf, 110000)
        atr = bt.atr_series(candles, 14)
        closes = [c["close"] for c in candles]
        n = len(candles)
        sig_fn = builder(candles)
        lookback = LONG_LB[tf]

        for i in range(max(1500, lookback + 50), n - 1):
            sig = sig_fn(i)
            if sig == 0:
                continue
            er = efficiency_ratio(closes, i, lookback)
            if er is None or er < THR:
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
            exit_j = None
            for j in range(i + 1, min(i + 200, n - 1) + 1):
                hi, lo = candles[j]["high"], candles[j]["low"]
                if be_r > 0 and not be_armed:
                    fav = ((hi - entry) if sig == 1 else (entry - lo)) / risk_dist
                    if fav >= be_r:
                        cur_sl = entry
                        be_armed = True
                if sig == 1:
                    if lo <= cur_sl:
                        exit_r = (cur_sl - entry) / risk_dist
                        exit_j = j
                        break
                    elif hi >= tp:
                        exit_r = (tp - entry) / risk_dist
                        exit_j = j
                        break
                else:
                    if hi >= cur_sl:
                        exit_r = (entry - cur_sl) / risk_dist
                        exit_j = j
                        break
                    elif lo <= tp:
                        exit_r = (entry - tp) / risk_dist
                        exit_j = j
                        break
            if exit_r is None:
                continue
            net_r = exit_r - cost_r
            all_trades.append({
                "strat": name, "open_time": candles[i]["time"],
                "close_time": candles[exit_j]["time"], "entry": entry,
                "risk_dist": risk_dist, "net_r": net_r, "er": er,
            })
    all_trades.sort(key=lambda t: t["open_time"])
    return all_trades


def simulate_portfolio_streak(trades, start_equity, risk_eur, max_lots_cap, max_concurrent,
                               streak_trigger=3, streak_mult=0.5, streak_reset_wins=1):
    """Come simulate_portfolio ma con riduzione del rischio dopo
    streak_trigger perdite CONSECUTIVE (sul PORTAFOGLIO, non per strategia
    - riflette il vero stato del conto), ripristinato dopo streak_reset_wins
    vincite consecutive. Tecnica di risk management nota (non tarata su
    questo campione), non ancora provata oggi - vedi vault 16/08."""
    equity = start_equity
    peak = start_equity
    max_dd_pct = 0.0
    open_positions = []
    n_taken, n_skipped_bucket = 0, 0
    consec_losses, consec_wins = 0, 0
    risk_mult = 1.0
    n_reduced_trades = 0
    for t in trades:
        if equity <= 0:
            break
        open_positions = [ct for ct in open_positions if ct > t["open_time"]]
        if len(open_positions) >= max_concurrent:
            n_skipped_bucket += 1
            continue
        open_positions.append(t["close_time"])
        eff_risk_eur = risk_eur * risk_mult
        if risk_mult < 1.0:
            n_reduced_trades += 1
        lots = eff_risk_eur / (100.0 * t["risk_dist"]) if t["risk_dist"] > 0 else 0
        lots = min(round(lots * 100) / 100.0, max_lots_cap)
        lots = max(lots, 0.01)
        actual_risk_eur = lots * 100 * t["risk_dist"]
        pnl_eur = t["net_r"] * actual_risk_eur
        equity += pnl_eur
        peak = max(peak, equity)
        if peak > 0:
            max_dd_pct = max(max_dd_pct, (peak - equity) / peak * 100)
        n_taken += 1
        if pnl_eur < 0:
            consec_losses += 1
            consec_wins = 0
            if consec_losses >= streak_trigger:
                risk_mult = streak_mult
        else:
            consec_wins += 1
            consec_losses = 0
            if consec_wins >= streak_reset_wins:
                risk_mult = 1.0
    return {"final_equity": equity, "max_dd_pct": max_dd_pct, "n_taken": n_taken,
            "n_skipped_bucket": n_skipped_bucket, "net_pnl": equity - start_equity,
            "n_reduced_trades": n_reduced_trades}


def simulate_portfolio_capped(trades, start_equity, risk_eur, max_lots_cap, max_concurrent,
                               max_risk_eur_cap=None):
    """Come simulate_portfolio ma con un tetto DIRETTO in euro sul rischio
    per trade (oltre al minimo di 0.01 lotti) - scoperto il 16/08 che il
    minimo lotto puo' forzare fino a EUR61 su un trade a stop largo,
    indipendentemente dal capitale. Se il rischio forzato dal minimo
    lotto supera max_risk_eur_cap, il trade viene scartato del tutto
    (non c'e' modo di scendere sotto 0.01 lotti)."""
    equity = start_equity
    peak = start_equity
    max_dd_pct = 0.0
    open_positions = []
    n_taken, n_skipped_bucket, n_skipped_cap = 0, 0, 0
    for t in trades:
        if equity <= 0:
            break
        open_positions_local = [ct for ct in open_positions if ct > t["open_time"]]
        open_positions = open_positions_local
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
        pnl_eur = t["net_r"] * actual_risk_eur
        equity += pnl_eur
        peak = max(peak, equity)
        if peak > 0:
            max_dd_pct = max(max_dd_pct, (peak - equity) / peak * 100)
        n_taken += 1
    return {"final_equity": equity, "max_dd_pct": max_dd_pct, "n_taken": n_taken,
            "n_skipped_bucket": n_skipped_bucket, "n_skipped_cap": n_skipped_cap,
            "net_pnl": equity - start_equity}


def simulate_portfolio_er_weighted(trades, start_equity, risk_eur, max_lots_cap, max_concurrent,
                                    max_risk_eur_cap, er_thr, er_full_strength, max_weight=2.0):
    """Come simulate_portfolio_capped ma pesa risk_eur in base a quanto
    l'Efficiency Ratio e' sopra la soglia (er_thr) - segnale di regime
    forte = size piu' grande, fino a max_weight, non solo si/no come
    prima. Lineare tra er_thr (peso 1.0) e er_full_strength (peso
    max_weight), poi tetto."""
    equity = start_equity
    peak = start_equity
    max_dd_pct = 0.0
    open_positions = []
    n_taken, n_skipped_bucket, n_skipped_cap = 0, 0, 0
    for t in trades:
        if equity <= 0:
            break
        open_positions = [ct for ct in open_positions if ct > t["open_time"]]
        if len(open_positions) >= max_concurrent:
            n_skipped_bucket += 1
            continue
        er = t.get("er") or er_thr
        frac = (er - er_thr) / max(1e-9, (er_full_strength - er_thr))
        weight = 1.0 + min(1.0, max(0.0, frac)) * (max_weight - 1.0)
        eff_risk_eur = risk_eur * weight
        lots = eff_risk_eur / (100.0 * t["risk_dist"]) if t["risk_dist"] > 0 else 0
        lots = min(round(lots * 100) / 100.0, max_lots_cap)
        lots = max(lots, 0.01)
        actual_risk_eur = lots * 100 * t["risk_dist"]
        if max_risk_eur_cap is not None and actual_risk_eur > max_risk_eur_cap:
            n_skipped_cap += 1
            continue
        open_positions.append(t["close_time"])
        pnl_eur = t["net_r"] * actual_risk_eur
        equity += pnl_eur
        peak = max(peak, equity)
        if peak > 0:
            max_dd_pct = max(max_dd_pct, (peak - equity) / peak * 100)
        n_taken += 1
    return {"final_equity": equity, "max_dd_pct": max_dd_pct, "n_taken": n_taken,
            "n_skipped_bucket": n_skipped_bucket, "n_skipped_cap": n_skipped_cap,
            "net_pnl": equity - start_equity}


def simulate_portfolio(trades, start_equity, risk_eur, max_lots_cap, max_concurrent):
    equity = start_equity
    peak = start_equity
    max_dd_pct = 0.0
    open_positions = []  # lista di close_time per contare la concorrenza
    n_taken, n_skipped_bucket = 0, 0
    for t in trades:
        if equity <= 0:
            break
        open_positions = [ct for ct in open_positions if ct > t["open_time"]]
        if len(open_positions) >= max_concurrent:
            n_skipped_bucket += 1
            continue
        open_positions.append(t["close_time"])
        # 1 lotto = 100 oz -> $1 di movimento = $100 di PnL a lotto pieno,
        # quindi lots per rischiare esattamente risk_eur su risk_dist e'
        # risk_eur/(100*risk_dist), non risk_eur/risk_dist (bug trovato oggi:
        # mancava /100, mascherato su CRT perche' il tetto lotti interveniva
        # sempre comunque data la sua distanza di rischio minuscola).
        lots = risk_eur / (100.0 * t["risk_dist"]) if t["risk_dist"] > 0 else 0
        lots = min(round(lots * 100) / 100.0, max_lots_cap)
        lots = max(lots, 0.01)
        actual_risk_eur = lots * 100 * t["risk_dist"]
        pnl_eur = t["net_r"] * actual_risk_eur
        equity += pnl_eur
        peak = max(peak, equity)
        if peak > 0:
            max_dd_pct = max(max_dd_pct, (peak - equity) / peak * 100)
        n_taken += 1
    return {"final_equity": equity, "max_dd_pct": max_dd_pct, "n_taken": n_taken,
            "n_skipped_bucket": n_skipped_bucket, "net_pnl": equity - start_equity}


def main():
    for preset in ["retail_standard", "ecn"]:
        print(f"\n=== Portafoglio 5 strategie + filtro regime, {preset} ===", flush=True)
        trades = collect_all_trades(preset)
        print(f"  trade totali (dopo filtro regime, tutte le strategie): {len(trades)}", flush=True)
        by_strat = {}
        for t in trades:
            by_strat[t["strat"]] = by_strat.get(t["strat"], 0) + 1
        print(f"  per strategia: {by_strat}", flush=True)
        res = simulate_portfolio(trades, START_EQUITY, RISK_EUR, MAX_LOTS_CAP, MAX_CONCURRENT)
        print(f"  conto=EUR{START_EQUITY:.0f} rischio=EUR{RISK_EUR:.0f}/trade tetto_lotti={MAX_LOTS_CAP} "
              f"max_concorrenti={MAX_CONCURRENT}", flush=True)
        print(f"  trade eseguiti={res['n_taken']}  scartati_per_bucket_pieno={res['n_skipped_bucket']}  "
              f"finale=EUR{res['final_equity']:.2f}  netPnL=EUR{res['net_pnl']:.2f}  maxDD={res['max_dd_pct']:.1f}%",
              flush=True)


if __name__ == "__main__":
    main()
