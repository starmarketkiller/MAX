#!/usr/bin/env python3
"""NEXUS Strategy Foundry Phase 2 - Causal Edge Screening.

Costruisce un event dataset causale per ciascuna delle 4 ipotesi native
congelate in Phase 1, piu' l'esperimento di regime e 3 estrazioni minime
open-source, e misura l'esito con R-multiple walk-forward SENZA gestione
dinamica (nessun trailing/BE, solo target/stop fissi definiti al momento
dell'evento).

Nessun tuning dopo aver visto i dati: tutte le soglie sono dichiarate qui
sopra PRIMA di eseguire, ripescate identiche dalle specifiche Phase 1 dove
gia' fissate, o scelte come singolo valore ragionevole ex-ante dove Phase 1
lasciava un grado di liberta' (dichiarato inline).
"""
import sys, os, json, csv
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import backtest as bt

SYMBOL = "XAUUSD"
MAX_HOLD_BARS_H4 = 40       # ~6.7 giorni H4 - orizzonte dichiarato ex-ante, coerente con SL/TP ATR-based usati altrove nel progetto
MAX_HOLD_DAYS_SESSION = 3   # per l'ipotesi di sessione (evento giornaliero), orizzonte in giorni di calendario
R_LEVELS = [0.5, 1.0, 1.5, 2.0]

# Split discovery/validation deciso PRIMA di guardare i risultati: 70/30
# cronologico, stesso principio OOS gia' usato in tutte le fasi precedenti
# di questa sessione (Serious 3Y usava 77.5/22.5 sul periodo di test - qui
# 70/30 e' scelto perche' il periodo disponibile e' piu' lungo e vogliamo
# un blocco di validation via via piu' sostanzioso, non per far tornare un
# risultato).
DISCOVERY_FRAC = 0.70


def r_outcome(candles, entry_i, entry_price, invalidation_price, direction, max_hold):
    """Cammina in avanti da entry_i+1 (mai la barra dell'evento stessa) per
    max_hold barre. Nessuna gestione dinamica: target e stop sono fissi,
    definiti una sola volta qui. Ritorna un dict con MFE_R, MAE_R, bar a cui
    ciascun livello +0.5/+1/+1.5/+2R e' raggiunto (None se mai), bar a cui
    -1R e' raggiunto, e first_outcome (quale tra +1R e -1R arriva prima,
    CENSORED se nessuno dei due entro max_hold, AMBIGUOUS se nella stessa
    barra)."""
    R = abs(entry_price - invalidation_price)
    if R <= 0:
        return None
    mfe_r, mae_r = 0.0, 0.0
    level_bar = {lvl: None for lvl in R_LEVELS}
    minus1_bar = None
    n = len(candles)
    bars_used = 0
    for k in range(1, max_hold + 1):
        j = entry_i + k
        if j >= n:
            break
        bars_used = k
        bar = candles[j]
        if direction == 1:
            fav = (bar["high"] - entry_price) / R
            adv = (entry_price - bar["low"]) / R
        else:
            fav = (entry_price - bar["low"]) / R
            adv = (bar["high"] - entry_price) / R
        mfe_r = max(mfe_r, fav)
        mae_r = max(mae_r, adv)
        hit_1r = fav >= 1.0
        hit_m1r = adv >= 1.0
        for lvl in R_LEVELS:
            if level_bar[lvl] is None and fav >= lvl:
                level_bar[lvl] = k
        if minus1_bar is None and hit_m1r:
            minus1_bar = k
        if hit_1r and hit_m1r:
            first_outcome, bars_to_target, bars_to_stop = "AMBIGUOUS_SAME_BAR", k, k
            return _pack(mfe_r, mae_r, level_bar, minus1_bar, first_outcome, bars_to_target, bars_to_stop, bars_used, R)
        if hit_1r:
            return _pack(mfe_r, mae_r, level_bar, minus1_bar, "PLUS_1R_FIRST", k, None, bars_used, R)
        if hit_m1r:
            return _pack(mfe_r, mae_r, level_bar, minus1_bar, "MINUS_1R_FIRST", None, k, bars_used, R)
    return _pack(mfe_r, mae_r, level_bar, minus1_bar, "CENSORED", None, None, bars_used, R)


def _pack(mfe_r, mae_r, level_bar, minus1_bar, first_outcome, bars_to_target, bars_to_stop, bars_used, R):
    return {
        "R_price": round(R, 4), "mfe_r": round(mfe_r, 3), "mae_r": round(mae_r, 3),
        "bar_plus_0_5R": level_bar[0.5], "bar_plus_1R": level_bar[1.0],
        "bar_plus_1_5R": level_bar[1.5], "bar_plus_2R": level_bar[2.0],
        "bar_minus_1R": minus1_bar, "first_outcome": first_outcome,
        "bars_to_target": bars_to_target, "bars_to_stop": bars_to_stop,
        "bars_observed": bars_used,
    }


# --------------------------------------------------------------------------- #
# 1. Failed Breakout Fade
# Soglie: N=20 (range lookback, stessa convenzione di BREAKOUT_ACC per
# comparabilita' diretta), K=3 barre max per la conferma di fallimento
# (dichiarato ex-ante: abbastanza breve da restare "lo stesso evento", non
# tarato sui risultati). TF=H4.
# --------------------------------------------------------------------------- #
def detect_failed_breakout_fade(candles, ind, N=20, K=3):
    events = []
    n = len(candles)
    for i in range(N + 3, n - 1):
        hh = max(c["high"] for c in candles[i - N - 1:i - 1])
        ll = min(c["low"] for c in candles[i - N - 1:i - 1])
        atr_i = ind["atr"][i]
        if not atr_i:
            continue
        # cerca un breakout in una delle ultime K barre (esclusa i stessa)
        for kb in range(1, K + 1):
            b = i - kb
            if b < 1:
                break
            if candles[b]["close"] > hh:
                breakout_dir, breakout_extreme = 1, max(c["high"] for c in candles[b:i])
            elif candles[b]["close"] < ll:
                breakout_dir, breakout_extreme = -1, min(c["low"] for c in candles[b:i])
            else:
                continue
            # fallimento: barra i richiude DENTRO il range originale
            c_i = candles[i]["close"]
            failed = (breakout_dir == 1 and c_i < hh) or (breakout_dir == -1 and c_i > ll)
            if not failed:
                continue
            direction = -breakout_dir  # fade: si scommette sull'inversione
            entry_price = c_i
            invalidation = breakout_extreme
            events.append({
                "timestamp": candles[i]["time"], "direction": "BUY" if direction == 1 else "SELL",
                "entry_i": i, "entry_price": entry_price, "invalidation_price": invalidation,
                "atr": atr_i, "setup_range_hi": hh, "setup_range_lo": ll,
                "breakout_bar_offset": kb, "breakout_dir": breakout_dir,
            })
            break  # un solo evento per barra i
    return events


def baseline_unfailed_breakouts(candles, ind, N=20, K=3):
    """Baseline richiesto dal task: breakout che NON rientrano nel range
    (continuano), stesso N/K, stessa direzione di trade (continuazione,
    non fade) - per confrontare 'fallire e fare fade' vs 'accettare e
    continuare' sullo STESSO universo di breakout iniziali."""
    events = []
    n = len(candles)
    for i in range(N + 3, n - 1):
        hh = max(c["high"] for c in candles[i - N - 1:i - 1])
        ll = min(c["low"] for c in candles[i - N - 1:i - 1])
        atr_i = ind["atr"][i]
        if not atr_i:
            continue
        for kb in range(1, K + 1):
            b = i - kb
            if b < 1:
                break
            if candles[b]["close"] > hh:
                breakout_dir = 1
            elif candles[b]["close"] < ll:
                breakout_dir = -1
            else:
                continue
            c_i = candles[i]["close"]
            failed = (breakout_dir == 1 and c_i < hh) or (breakout_dir == -1 and c_i > ll)
            if failed:
                continue  # questo e' l'evento primario, non il baseline
            # baseline: continuazione, entry alla chiusura, invalidation = range opposto
            entry_price = c_i
            invalidation = ll if breakout_dir == 1 else hh
            events.append({
                "timestamp": candles[i]["time"], "direction": "BUY" if breakout_dir == 1 else "SELL",
                "entry_i": i, "entry_price": entry_price, "invalidation_price": invalidation,
                "atr": atr_i,
            })
            break
    return events


# --------------------------------------------------------------------------- #
# 2. Volatility Compression Percentile Breakout
# Soglie: finestra percentile=100 barre, percentile soglia=20, persistenza
# M=5 barre consecutive sotto soglia, espansione = true range > 1.5x ATR
# corrente E chiusura fuori dal range di compressione. TF=H4.
# --------------------------------------------------------------------------- #
def _percentile_rank(vals, x):
    below = sum(1 for v in vals if v is not None and v < x)
    total = sum(1 for v in vals if v is not None)
    return (below / total * 100.0) if total else None


def detect_vol_compression_breakout(candles, ind, PCTL_WINDOW=100, PCTL_THRESH=20, PERSIST_M=5, EXPANSION_MULT=1.5):
    events = []
    n = len(candles)
    atr = ind["atr"]
    for i in range(PCTL_WINDOW + PERSIST_M + 2, n - 1):
        # persistenza: le ultime PERSIST_M barre (i-PERSIST_M..i-1) devono
        # essere tutte sotto il percentile soglia calcolato SOLO su dati
        # fino a quella barra (causale, ricalcolato per ciascuna barra della
        # finestra di persistenza, non un singolo percentile riusato)
        compressed = True
        comp_range_hi, comp_range_lo = -1e18, 1e18
        for kb in range(1, PERSIST_M + 1):
            b = i - kb
            hist = atr[b - PCTL_WINDOW:b]
            if atr[b] is None or None in hist[-1:]:
                compressed = False
                break
            pr = _percentile_rank(hist, atr[b])
            if pr is None or pr > PCTL_THRESH:
                compressed = False
                break
            comp_range_hi = max(comp_range_hi, candles[b]["high"])
            comp_range_lo = min(comp_range_lo, candles[b]["low"])
        if not compressed:
            continue
        atr_i = atr[i]
        if not atr_i:
            continue
        tr_i = candles[i]["high"] - candles[i]["low"]
        c_i = candles[i]["close"]
        expansion = tr_i > EXPANSION_MULT * atr_i
        if not expansion:
            continue
        if c_i > comp_range_hi:
            direction = 1
            invalidation = comp_range_lo
        elif c_i < comp_range_lo:
            direction = -1
            invalidation = comp_range_hi
        else:
            continue
        events.append({
            "timestamp": candles[i]["time"], "direction": "BUY" if direction == 1 else "SELL",
            "entry_i": i, "entry_price": c_i, "invalidation_price": invalidation,
            "atr": atr_i, "compression_range_hi": comp_range_hi, "compression_range_lo": comp_range_lo,
        })
    return events


def baseline_expansion_no_compression(candles, ind, EXPANSION_MULT=1.5, PCTL_WINDOW=100):
    """Baseline: barre di espansione (TR>1.5xATR) NON precedute da
    compressione persistente - stesso trigger di espansione, senza la
    feature distintiva (compressione), per isolare il contributo della
    compressione stessa."""
    events = []
    n = len(candles)
    atr = ind["atr"]
    for i in range(PCTL_WINDOW + 6, n - 1):
        atr_i = atr[i]
        if not atr_i:
            continue
        tr_i = candles[i]["high"] - candles[i]["low"]
        if tr_i <= EXPANSION_MULT * atr_i:
            continue
        # richiede semplicemente che NON tutte le 5 barre precedenti siano
        # in compressione (quindi non e' un evento "primario" duplicato)
        hist = atr[i - 1 - PCTL_WINDOW:i - 1]
        pr = _percentile_rank(hist, atr[i - 1]) if atr[i - 1] is not None else None
        if pr is not None and pr <= 20:
            continue  # esclude i casi gia' in compressione (evita overlap col dataset primario)
        rng_hi = max(c["high"] for c in candles[i - 5:i])
        rng_lo = min(c["low"] for c in candles[i - 5:i])
        c_i = candles[i]["close"]
        if c_i > rng_hi:
            direction, invalidation = 1, rng_lo
        elif c_i < rng_lo:
            direction, invalidation = -1, rng_hi
        else:
            continue
        events.append({
            "timestamp": candles[i]["time"], "direction": "BUY" if direction == 1 else "SELL",
            "entry_i": i, "entry_price": c_i, "invalidation_price": invalidation, "atr": atr_i,
        })
    return events


# --------------------------------------------------------------------------- #
# 4. Displacement Continuation via Imbalance Stack
# Soglie: gap 3-barre stile sig_fvg_cont_ext (c[i] vs c[i-2]), stack = 2+
# gap consecutivi stessa direzione senza gap opposto nel mezzo, conferma =
# barra successiva all'ultimo gap chiude oltre senza ritracciare nella zona
# dell'ultimo gap. TF=H4.
# --------------------------------------------------------------------------- #
def _gap_at(candles, i):
    """Gap 3-barre: shift1 vs shift3 (stessa convenzione di sig_fvg_cont_ext
    in backtest.py). +1 = gap rialzista (low[i] > high[i-2]), -1 = ribassista,
    0 = nessun gap."""
    if i < 2:
        return 0, None, None
    hi2, lo2 = candles[i - 2]["high"], candles[i - 2]["low"]
    hi0, lo0 = candles[i]["high"], candles[i]["low"]
    if lo0 > hi2:
        return 1, hi2, lo0   # zona di gap [hi2, lo0]
    if hi0 < lo2:
        return -1, hi0, lo2  # zona di gap [hi0, lo2]
    return 0, None, None


def detect_displacement_stack(candles, ind, MIN_STACK=2):
    events = []
    n = len(candles)
    gap_dir_seq = [0] * n
    gap_lo_seq, gap_hi_seq = [None] * n, [None] * n
    for i in range(n):
        d, glo, ghi = _gap_at(candles, i)
        gap_dir_seq[i] = d
        if d != 0:
            gap_lo_seq[i], gap_hi_seq[i] = glo, ghi
    i = 2
    while i < n - 1:
        if gap_dir_seq[i] == 0:
            i += 1
            continue
        stack_dir = gap_dir_seq[i]
        stack_start = i
        stack_gaps = [i]
        j = i + 1
        while j < n:
            if gap_dir_seq[j] == stack_dir:
                stack_gaps.append(j)
                j += 1
            elif gap_dir_seq[j] == 0:
                j += 1
            else:
                break  # gap opposto: stack interrotto
        if len(stack_gaps) >= MIN_STACK:
            last_gap_i = stack_gaps[-1]
            confirm_i = last_gap_i + 1
            if confirm_i < n:
                atr_i = ind["atr"][confirm_i]
                if atr_i:
                    c_confirm = candles[confirm_i]["close"]
                    # zona del gap piu' vecchio (primo dello stack) = invalidation conservativa
                    first_gap_lo = gap_lo_seq[stack_gaps[0]] if stack_dir == 1 else gap_hi_seq[stack_gaps[0]]
                    continues = (stack_dir == 1 and c_confirm > candles[last_gap_i]["high"]) or \
                                (stack_dir == -1 and c_confirm < candles[last_gap_i]["low"])
                    not_retraced = (stack_dir == 1 and c_confirm > gap_hi_seq[last_gap_i]) or \
                                   (stack_dir == -1 and c_confirm < gap_lo_seq[last_gap_i])
                    if continues and not_retraced:
                        events.append({
                            "timestamp": candles[confirm_i]["time"],
                            "direction": "BUY" if stack_dir == 1 else "SELL",
                            "entry_i": confirm_i, "entry_price": c_confirm,
                            "invalidation_price": first_gap_lo, "atr": atr_i,
                            "stack_size": len(stack_gaps),
                        })
        i = j if j > i else i + 1
    return events


def baseline_single_gap(candles, ind):
    """Baseline: singolo gap isolato (stack_size=1) con la stessa logica di
    conferma - per isolare il contributo dello STACK vs un gap singolo
    (gia' l'ipotesi di FVG_CONT esistente, qui ricostruita in forma
    equivalente per un confronto sullo stesso schema evento)."""
    events = []
    n = len(candles)
    for i in range(2, n - 1):
        d, glo, ghi = _gap_at(candles, i)
        if d == 0:
            continue
        # deve essere isolato: barra i-1 e i+1 non hanno un gap concorde (altrimenti e' parte di uno stack)
        d_prev, _, _ = _gap_at(candles, i - 1) if i >= 1 else (0, None, None)
        confirm_i = i + 1
        if confirm_i >= n or d_prev == d:
            continue
        atr_i = ind["atr"][confirm_i]
        if not atr_i:
            continue
        c_confirm = candles[confirm_i]["close"]
        continues = (d == 1 and c_confirm > candles[i]["high"]) or (d == -1 and c_confirm < candles[i]["low"])
        not_retraced = (d == 1 and c_confirm > ghi) or (d == -1 and c_confirm < glo)
        if continues and not_retraced:
            invalidation = glo if d == 1 else ghi
            events.append({
                "timestamp": candles[confirm_i]["time"], "direction": "BUY" if d == 1 else "SELL",
                "entry_i": confirm_i, "entry_price": c_confirm, "invalidation_price": invalidation,
                "atr": atr_i, "stack_size": 1,
            })
    return events


# --------------------------------------------------------------------------- #
# 3. Session Range Compression -> London Open Expansion (richiede M15)
# Soglie: finestra percentile storico = 60 sessioni asiatiche precedenti,
# percentile soglia = 25, finestra di rottura londinese = 07:00-09:00 UTC,
# corpo minimo = 50% del range della barra di rottura.
# --------------------------------------------------------------------------- #
def detect_session_compression_expansion(m15_candles, PCTL_WINDOW=60, PCTL_THRESH=25, BODY_RATIO_MIN=0.5):
    from collections import defaultdict
    by_date = defaultdict(list)
    for c in m15_candles:
        d = c["time"].split(" ")[0]
        by_date[d].append(c)
    dates = sorted(by_date.keys())
    asian_ranges = {}   # date -> (hi, lo, range)
    for d in dates:
        asian_bars = [c for c in by_date[d] if 0 <= int(c["time"].split(" ")[1].split(":")[0]) < 7]
        if not asian_bars:
            continue
        hi = max(c["high"] for c in asian_bars)
        lo = min(c["low"] for c in asian_bars)
        asian_ranges[d] = (hi, lo, hi - lo)

    events = []
    for idx, d in enumerate(dates):
        if d not in asian_ranges:
            continue
        prior_dates = [dates[k] for k in range(max(0, idx - PCTL_WINDOW), idx) if dates[k] in asian_ranges]
        if len(prior_dates) < 20:   # campione minimo per un percentile decente, dichiarato ex-ante
            continue
        prior_ranges = [asian_ranges[pd][2] for pd in prior_dates]
        rng = asian_ranges[d][2]
        pr = _percentile_rank(prior_ranges, rng)
        if pr is None or pr > PCTL_THRESH:
            continue
        ah, al, _ = asian_ranges[d]
        london_bars = [c for c in by_date[d] if 7 <= int(c["time"].split(" ")[1].split(":")[0]) < 9]
        for lb in london_bars:
            body = abs(lb["close"] - lb["open"])
            full_range = lb["high"] - lb["low"]
            if full_range <= 0:
                continue
            body_ratio = body / full_range
            if body_ratio < BODY_RATIO_MIN:
                continue
            if lb["close"] > ah:
                direction, invalidation = 1, al
            elif lb["close"] < al:
                direction, invalidation = -1, ah
            else:
                continue
            events.append({
                "timestamp": lb["time"], "direction": "BUY" if direction == 1 else "SELL",
                "candle": lb, "invalidation_price": invalidation, "entry_price": lb["close"],
                "asian_hi": ah, "asian_lo": al, "asian_range": rng, "asian_pctl": pr,
            })
            break  # un solo evento per giorno (la prima rottura valida)
    return events


def baseline_london_no_compression(m15_candles, PCTL_WINDOW=60, PCTL_THRESH=25, BODY_RATIO_MIN=0.5):
    """Baseline: rotture di Londra dopo una sessione asiatica NON compressa
    (percentile > 50) - stesso trigger di rottura, senza la feature
    distintiva di compressione."""
    from collections import defaultdict
    by_date = defaultdict(list)
    for c in m15_candles:
        d = c["time"].split(" ")[0]
        by_date[d].append(c)
    dates = sorted(by_date.keys())
    asian_ranges = {}
    for d in dates:
        asian_bars = [c for c in by_date[d] if 0 <= int(c["time"].split(" ")[1].split(":")[0]) < 7]
        if not asian_bars:
            continue
        hi = max(c["high"] for c in asian_bars)
        lo = min(c["low"] for c in asian_bars)
        asian_ranges[d] = (hi, lo, hi - lo)

    events = []
    for idx, d in enumerate(dates):
        if d not in asian_ranges:
            continue
        prior_dates = [dates[k] for k in range(max(0, idx - PCTL_WINDOW), idx) if dates[k] in asian_ranges]
        if len(prior_dates) < 20:
            continue
        prior_ranges = [asian_ranges[pd][2] for pd in prior_dates]
        rng = asian_ranges[d][2]
        pr = _percentile_rank(prior_ranges, rng)
        if pr is None or pr <= 50:
            continue
        ah, al, _ = asian_ranges[d]
        london_bars = [c for c in by_date[d] if 7 <= int(c["time"].split(" ")[1].split(":")[0]) < 9]
        for lb in london_bars:
            body = abs(lb["close"] - lb["open"])
            full_range = lb["high"] - lb["low"]
            if full_range <= 0:
                continue
            if body / full_range < BODY_RATIO_MIN:
                continue
            if lb["close"] > ah:
                direction, invalidation = 1, al
            elif lb["close"] < al:
                direction, invalidation = -1, ah
            else:
                continue
            events.append({
                "timestamp": lb["time"], "direction": "BUY" if direction == 1 else "SELL",
                "candle": lb, "invalidation_price": invalidation, "entry_price": lb["close"],
                "asian_pctl": pr,
            })
            break
    return events


if __name__ == "__main__":
    print("Modulo di detection - eseguire phase2_run.py per l'analisi completa.")
