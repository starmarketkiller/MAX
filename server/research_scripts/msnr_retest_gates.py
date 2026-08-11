#!/usr/bin/env python3
"""
11/08 - "proviamo piu' versioni, non dobbiamo attenerci solo ai file della
fonte, basta che abbia senso e ci sia prova": tre gate/confluenze aggiuntivi
su MALAYSIAN_SNR_V2_RETEST, ciascuno con una motivazione precisa, non a
caso:

1. Regime STRONG_TREND: RETEST e' concettualmente un pattern di
   CONTINUAZIONE (rottura + retest + prosegue) - la stessa ipotesi che ha
   reso BREAKOUT_ACC il candidato piu' solido della sessione. Se il
   meccanismo e' davvero "il trend prosegue dopo la rottura", dovrebbe
   funzionare meglio quando il regime e' gia' di trend forte.
2. CRT (Candle Range Theory, dalla fonte MSNR, mai implementata prima -
   vedi vault): il prezzo e' FUORI dal range (max/min) del giorno
   precedente al momento del segnale - motivazione: un breakout che porta
   il prezzo fuori dal contesto range del giorno prima e' piu' probabile
   sia un vero movimento direzionale, non rumore intra-range.
3. Confluenza con LIQ_SWEEP: un segnale RETEST e' rinforzato se un vero
   sweep di liquidita' (sig_liq_sweep_ext, gia' testato e affidabile in
   questa sessione) e' avvenuto nella stessa direzione entro poche barre -
   idea dell'utente, lo stesso principio del "Marriage Concept" della
   fonte (due segnali indipendenti che confluiscono sullo stesso punto
   sono piu' forti) ma con la liquidita' al posto della trendline.

Selezione disciplinata: ogni gate scelto SOLO se migliora il punteggio
in-sample, verificato SOLO su out-of-sample mai visto durante la scelta -
stessa disciplina di regime_filter_singles.py.
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import backtest as bt

SYMBOL, BARS = "XAUUSD", 60000
STRAT = "MALAYSIAN_SNR_V2_RETEST"
ATR_SL, ATR_TP = 1.5, 3.0
MIN_IS_TRADES = 15
LIQ_SWEEP_WINDOW = 6   # barre di tolleranza per la confluenza


def load_slice(tf, bar_range):
    candles, src = bt._fetch_real(SYMBOL, tf, bars=BARS)
    n = len(candles)
    i0, i1 = int(n * bar_range[0]), int(n * bar_range[1])
    full = candles
    candles = candles[i0:i1]
    intraday = bt._load_dukascopy_m15(SYMBOL) if src == "dukascopy" else None
    ind = bt._prep(candles, intraday_ref=intraday, snr_ref=full)
    return candles, ind, full, list(range(i0, i1))


def crt_outside_mask(candles, full, idx_map):
    """True se il close della barra e' fuori dal range max/min del giorno
    precedente (Candle Range Theory)."""
    d1 = bt._resample_ohlc(full, 24)
    out = [False] * len(candles)
    for i in range(len(candles)):
        ri = idx_map[i]
        d1_idx = ri // 24 - 1
        if d1_idx < 1:
            continue
        prev = d1[d1_idx - 1]
        c1 = candles[i]["close"]
        out[i] = c1 > prev["high"] or c1 < prev["low"]
    return out


def liq_sweep_confluence_mask(candles, ind):
    """True se sig_liq_sweep_ext ha sparato nella stessa direzione entro
    +-LIQ_SWEEP_WINDOW barre."""
    fn = bt.STRATEGIES["LIQ_SWEEP"]
    sweep = [fn(candles, ind, i) for i in range(len(candles))]
    n = len(candles)
    out = [0] * n
    for i in range(n):
        if sweep[i] == 0:
            continue
        for j in range(max(0, i - LIQ_SWEEP_WINDOW), min(n, i + LIQ_SWEEP_WINDOW + 1)):
            out[j] = out[j] or sweep[i]
    return out


def run_gated(candles, ind, base_sig, gate_mask=None, gate_dir_aware=False):
    equity, trades = 10000.0, []
    position = None
    atr = ind["atr"]
    for i in range(60, len(candles)):
        px = candles[i]["close"]
        if position is not None:
            hi, lo = candles[i]["high"], candles[i]["low"]
            hit = None
            if position["dir"] == 1:
                if lo <= position["sl"]: hit = position["sl"]
                elif hi >= position["tp"]: hit = position["tp"]
            else:
                if hi >= position["sl"]: hit = position["sl"]
                elif lo <= position["tp"]: hit = position["tp"]
            if not hit and (i - position["open_i"]) >= 40:
                hit = px
            if hit is not None:
                rd = position["risk"] if position["risk"] > 0 else 1e-9
                r = ((hit - position["entry"]) / rd) if position["dir"] == 1 else ((position["entry"] - hit) / rd)
                trades.append(r)
                position = None
            continue
        a = atr[i]
        d = base_sig[i]
        if not a or d == 0:
            continue
        if gate_mask is not None:
            g = gate_mask[i]
            if gate_dir_aware:
                if g != d:
                    continue
            elif not g:
                continue
        entry = px
        sl = entry - ATR_SL * a if d == 1 else entry + ATR_SL * a
        tp = entry + ATR_TP * a if d == 1 else entry - ATR_TP * a
        position = {"dir": d, "entry": entry, "sl": sl, "tp": tp, "open_i": i, "risk": abs(entry - sl)}
    gw = sum(r for r in trades if r > 0)
    gl = -sum(r for r in trades if r < 0)
    pf = round(gw / gl, 2) if gl > 0 else (None if gw == 0 else float("inf"))
    exp_r = round(sum(trades) / len(trades), 3) if trades else 0.0
    return {"trades": len(trades), "pf": pf, "exp_r": exp_r}


def score(res):
    if res["pf"] is None or res["trades"] < MIN_IS_TRADES:
        return -999
    return res["exp_r"] * (res["trades"] ** 0.5)


def main():
    for tf in ["1h", "30m"]:
        print(f"\n=== {STRAT} + gate, {tf} ===")
        candles_is, ind_is, full, idx_is = load_slice(tf, (0.0, 0.6))
        candles_oos, ind_oos, _, idx_oos = load_slice(tf, (0.6, 1.0))
        sig_is = ind_is["snr_v2ret_signal"]
        sig_oos = ind_oos["snr_v2ret_signal"]

        regime_is, regime_oos = ind_is["regime"], ind_oos["regime"]
        crt_is = crt_outside_mask(candles_is, full, idx_is)
        crt_oos = crt_outside_mask(candles_oos, full, idx_oos)
        liq_is = liq_sweep_confluence_mask(candles_is, ind_is)
        liq_oos = liq_sweep_confluence_mask(candles_oos, ind_oos)

        gates = {
            "nessuno": (None, False, None, False),
            "regime STRONG_TREND": ([1 if r == 1 else 0 for r in regime_is], False,
                                     [1 if r == 1 else 0 for r in regime_oos], False),
            "CRT (fuori range gg prima)": (crt_is, False, crt_oos, False),
            "confluenza LIQ_SWEEP": (liq_is, True, liq_oos, True),
        }

        base_oos = run_gated(candles_oos, ind_oos, sig_oos)
        print(f"{'Gate':<26}{'IS PF':>7}{'IS n':>6}{'IS score':>10}   {'OOS PF':>7}{'OOS n':>6}   {'Base OOS':>10}")
        best_label, best_score, best_goos, best_dir_oos = None, -999, None, False
        for label, (gis, dir_is, goos, dir_oos) in gates.items():
            r_is = run_gated(candles_is, ind_is, sig_is, gis, dir_is)
            sc = score(r_is)
            r_oos = run_gated(candles_oos, ind_oos, sig_oos, goos, dir_oos)
            print(f"{label:<26}{r_is['pf']!s:>7}{r_is['trades']:>6}{sc:>10.2f}   "
                  f"{r_oos['pf']!s:>7}{r_oos['trades']:>6}   {base_oos['pf']!s:>10}")
            if sc > best_score:
                best_label, best_score = label, sc
                best_goos, best_dir_oos = goos, dir_oos
        r_best_oos = run_gated(candles_oos, ind_oos, sig_oos, best_goos, best_dir_oos)
        helped = (r_best_oos["pf"] is not None and base_oos["pf"] is not None
                  and r_best_oos["pf"] > base_oos["pf"] and r_best_oos["trades"] >= 15)
        print(f"--> scelto SOLO su IS: '{best_label}'   OOS pf={r_best_oos['pf']} n={r_best_oos['trades']}"
              f"   baseline OOS pf={base_oos['pf']} n={base_oos['trades']}"
              f"{'  <- aiuta (campione OOS credibile)' if helped else ''}")


if __name__ == "__main__":
    main()
