#!/usr/bin/env python3
"""
16/08 (3) - stessa simulazione di crt_multitf_m5_full_sim_16-08.py (entry
M5 precisa dentro il range 4h), ma in EURO REALI su un conto piccolo
(200-1000), non in multipli di R astratti - richiesta esplicita
dell'utente: "parliamo di euro, calcoliamo basandoci in euro".

Ipotesi contratto: XAUUSD 1 oz per 0.01 lotto (confermato dall'utente sul
suo broker) -> 1 unita' di prezzo ($1) = $1 di PnL per 0.01 lotto, quindi
lotti = risk_eur_target / risk_dist_dollari, arrotondati a step 0.01.
EUR~USD trattati 1:1 per semplicita' (il conto e' in euro ma XAUUSD quota
in dollari - approssimazione dichiarata, non un dato preciso).

Cap di margine: leva 1:500 (assunzione, la piu' comune su XAUUSD retail -
DA VERIFICARE col broker reale), niente posizione che impegni piu' del
50% dell'equity corrente come margine (guardrail, non un limite del
broker preciso).

Rischio fisso in euro per trade (non % che cambia con l'equity) come
descritto dall'utente ("su 200 euro rischio anche 20 euro a trade").
"""
import sys
import os
import json
import bisect
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import backtest as bt

SYMBOL = "XAUUSD"
HTF = "4h"
BARS = 110000
MAX_HOLD_M5 = 12 * 24 * 5
CONTRACT_OZ_PER_001LOT = 1.0   # confermato dall'utente
LEVERAGE = 500.0               # assunzione, verificare col broker
MAX_MARGIN_FRAC = 0.5          # non impegnare piu' del 50% equity in margine

with open(os.path.join(os.path.dirname(__file__), "..", "data_cache_m5",
                        "dukascopy_xauusd_m5.json"), encoding="utf-8") as f:
    M5 = json.load(f)
M5_TIMES = [c["time"] for c in M5]


def _m5_idx_from(t_str):
    return bisect.bisect_left(M5_TIMES, t_str)


MAX_COST_R_ENTRY_GATE = 0.8  # 16/08 - non aprire se il costo stimato (spread+slip
# convertiti in R sul risk_dist REALE, prima di qualunque cap) supera questa soglia:
# scoperto che il cap a MAX_COST_R_PER_TRADE=5.0 (buono per non falsare le medie
# statistiche) diventa devastante in euro su un conto piccolo - una singola perdita
# capped a -6R puo' essere -44% di un conto da 200 euro. Meglio scartare a monte i
# trade dove il costo e' gia' sproporzionato, non aprirli sperando nel tetto.


def collect_trades(candles, atr, sig, tp_a, start_idx, n, floor_atr_mult, cost_spread, cost_slip):
    """Ritorna lista di (time_entry, entry_price, risk_dist_$, net_r) - stessa
    logica di simulate() in crt_multitf_m5_full_sim_16-08.py, variante
    B/C (entry M5 precisa), ma conservando entry_price/risk_dist per il
    dimensionamento in euro."""
    out = []
    for i in range(start_idx, n):
        if sig[i] == 0:
            continue
        direction = sig[i]
        a = atr[i]
        if not a:
            continue
        t0 = candles[i]["time"]
        t1 = candles[i + 1]["time"] if i + 1 < n else None
        if t1 is None:
            continue
        j0, j1 = _m5_idx_from(t0), _m5_idx_from(t1)
        m5_win = M5[j0:j1]
        if not m5_win:
            continue
        if direction == 1:
            extreme_pos = min(range(len(m5_win)), key=lambda k: m5_win[k]["low"])
            extreme = m5_win[extreme_pos]["low"]
        else:
            extreme_pos = max(range(len(m5_win)), key=lambda k: m5_win[k]["high"])
            extreme = m5_win[extreme_pos]["high"]
        entry = extreme
        buf = 0.05 * a
        sl = extreme - buf if direction == 1 else extreme + buf
        risk_dist = abs(entry - sl)
        if floor_atr_mult:
            floor_dist = floor_atr_mult * a
            if risk_dist < floor_dist:
                sl = entry - floor_dist if direction == 1 else entry + floor_dist
                risk_dist = floor_dist
        tp = tp_a[i]
        if tp is None or risk_dist <= 0:
            continue
        entry_m5_idx = j0 + extreme_pos

        exit_r = None
        k_end = min(entry_m5_idx + MAX_HOLD_M5, len(M5) - 1)
        for k in range(entry_m5_idx + 1, k_end + 1):
            hi, lo = M5[k]["high"], M5[k]["low"]
            if direction == 1:
                if lo <= sl:
                    exit_r = -1.0
                    break
                elif hi >= tp:
                    exit_r = (tp - entry) / risk_dist
                    break
            else:
                if hi >= sl:
                    exit_r = -1.0
                    break
                elif lo <= tp:
                    exit_r = (entry - tp) / risk_dist
                    break
        if exit_r is None:
            continue
        cost_r_uncapped = (cost_spread + cost_slip) / risk_dist
        if cost_r_uncapped > MAX_COST_R_ENTRY_GATE:
            continue  # scartato A MONTE, non aperto - non solo "cappato" a valle
        net_r = exit_r - cost_r_uncapped
        out.append((M5[entry_m5_idx]["time"], entry, risk_dist, net_r))
    return out


def simulate_euro(trades, start_equity, risk_eur_target, max_lots_cap):
    # 16/08 - corretto: il vincolo di margine (leva/equity) era quasi sempre non
    # vincolante (bastava equity>~50-100EUR perche' il calcolo "lotti per centrare
    # risk_eur_target" - 38-65 lotti su uno stop stretto - diventasse "permesso"),
    # producendo posizioni assurde (milioni di $ nominali su un conto da poche
    # centinaia di euro) ed equity che esplodeva o si azzerava a seconda della
    # fortuna. Fix: tetto FISSO e ragionevole sui lotti (max_lots_cap,
    # indipendente dall'equity corrente) - se lo stop e' troppo stretto per
    # centrare risk_eur_target dentro quel tetto, si rischia MENO del target,
    # mai di piu' per compensare.
    equity = start_equity
    peak = start_equity
    max_dd_pct = 0.0
    curve = [equity]
    skipped_margin = 0
    for _time, entry, risk_dist, net_r in trades:
        if equity <= 0:
            break
        lots = risk_eur_target / risk_dist if risk_dist > 0 else 0
        lots = round(lots * 100) / 100.0  # step 0.01
        lots = min(lots, max_lots_cap)
        if lots < 0.01:
            lots = 0.01
        actual_risk_eur = lots * 100 * risk_dist
        pnl_eur = net_r * actual_risk_eur
        equity += pnl_eur
        peak = max(peak, equity)
        if peak > 0:
            max_dd_pct = max(max_dd_pct, (peak - equity) / peak * 100)
        curve.append(equity)
        if equity <= 0:
            break
    return {
        "final_equity": equity, "max_dd_pct": max_dd_pct, "n_trades": len(curve) - 1,
        "skipped_margin": skipped_margin, "net_pnl_eur": equity - start_equity,
    }


def main():
    candles, src = bt._fetch_real(SYMBOL, HTF, BARS)
    atr = bt.atr_series(candles, 14)
    n = len(candles)
    start_idx = next((i for i, c in enumerate(candles) if c["time"] >= "2021-11-30"), 0)
    sig, sl_a, tp_a = bt._crt_series(candles, atr, min_stop_atr=0.3, mode="widen")

    START_EQ = 200
    LEVERAGE_CONFIRMED = 500.0
    avg_price = sum(c["close"] for c in candles[start_idx:]) / len(candles[start_idx:])

    for preset in ["retail_standard", "ecn"]:
        c = bt.COST_PRESETS[preset]
        print(f"\n=== costi {preset}, conto=EUR{START_EQ}, leva confermata 1:{int(LEVERAGE_CONFIRMED)} ===", flush=True)
        for label, floor in (("B_m5_precise", None), ("C_m5_floor", 0.15)):
            trades = collect_trades(candles, atr, sig, tp_a, start_idx, n, floor,
                                     c["spread_price"], c["slippage_price"])
            print(f"  -- {label} --", flush=True)
            for max_lots_cap in (0.02, 0.05, 0.10, 0.20, 0.30):
                margin_used = max_lots_cap * 100 * avg_price / LEVERAGE_CONFIRMED
                margin_pct = margin_used / START_EQ * 100
                res = simulate_euro(trades, START_EQ, 20, max_lots_cap)
                print(f"    tetto_lotti={max_lots_cap:.2f} (margine~EUR{margin_used:5.1f}={margin_pct:5.1f}% conto)  "
                      f"n={res['n_trades']:4d}  finale=EUR{res['final_equity']:10.2f}  "
                      f"netPnL=EUR{res['net_pnl_eur']:10.2f}  maxDD={res['max_dd_pct']:5.1f}%", flush=True)


if __name__ == "__main__":
    main()
