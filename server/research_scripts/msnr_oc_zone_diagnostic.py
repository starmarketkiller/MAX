#!/usr/bin/env python3
"""
11/08 - richiesta esplicita dell'utente: caratterizzare cosa succede
davvero sui livelli "OC" (open-close, cioe' i pivot close-to-open H4 gia'
usati da Stadio 1/Stadio 3/RETEST - "dalla chiusura all'apertura delle
candele"). Non un test di una strategia specifica, ma una domanda di
frequenza: quando il prezzo torna su uno di questi livelli, quante volte
INVERTE (rimbalza, il livello tiene) contro quante volte CONTINUA
(rompe)? E quando rompe, quante volte poi ritorna a fare retest (utile
come controllo incrociato sui numeri gia' visti con MALAYSIAN_SNR_V2_RETEST)?

Due parti:
1. Frequenza: per ogni livello H4 fresco, il primo approccio nella zona
   (0.4xATR(H4), stessa tolleranza usata ovunque in MALAYSIAN_SNR) viene
   classificato TENUTO (rimbalzo, chiusura dalla parte giusta) o ROTTO
   (chiusura oltre). Per i ROTTI, controlla se poi c'e' un retest entro
   N barre (incrocio con MALAYSIAN_SNR_V2_RETEST).
2. P&L: un ingresso "continuazione immediata" sui livelli OC (rottura
   fresca, entra subito, NESSUNA attesa di retest) - il pezzo mancante:
   Stadio 1 testa gia' il rimbalzo su questi livelli, MALAYSIAN_SNR_V2_
   RETEST testa gia' rottura+attesa+retest, MALAYSIAN_SNR_BREAKOUT testa
   la continuazione immediata ma sui livelli VECCHI (max/min 12 barre),
   non su questi OC. Qui si completa il quadro sugli stessi livelli OC.
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import backtest as bt
import bt_verdict

SYMBOL, TF, BARS = "XAUUSD", "4h", 60000
TOUCH_TOL_MULT = 0.4    # stessa tolleranza usata in tutte le varianti MSNR
FORWARD_HORIZON = 60    # barre base da scandire dopo la formazione del livello
RETEST_WINDOW = 12      # stesso MAX_WAIT_RETEST della variante RETEST


def build_oc_levels(h4):
    """Stessa identificazione close-to-open di Stadio 1/3/RETEST."""
    m = len(h4)
    res_at, sup_at = [None] * m, [None] * m
    last_res = last_sup = None
    fresh_res, fresh_sup = [False] * m, [False] * m
    for k in range(m):
        res_at[k], sup_at[k] = last_res, last_sup
        if k + 1 < m:
            bull = h4[k]["close"] > h4[k]["open"]
            bear = h4[k]["close"] < h4[k]["open"]
            if bull and h4[k + 1]["open"] < h4[k]["close"]:
                if h4[k]["close"] != last_res:
                    fresh_res[k + 1] = True
                last_res = h4[k]["close"]
            if bear and h4[k + 1]["open"] > h4[k]["close"]:
                if h4[k]["close"] != last_sup:
                    fresh_sup[k + 1] = True
                last_sup = h4[k]["close"]
    return res_at, sup_at, fresh_res, fresh_sup


def h4_to_base_idx(h4_idx, candles, h4):
    """Prima barra base con epoch >= apertura della barra H4."""
    target_epoch = bt._epoch_utc(h4[h4_idx]["time"])
    for i, c in enumerate(candles):
        if bt._epoch_utc(c["time"]) >= target_epoch:
            return i
    return None


def frequency_study(candles, h4, atr_h4, res_at, sup_at, fresh_res, fresh_sup):
    events = []
    for k in range(len(h4)):
        for side, levels, fresh in (("RES", res_at, fresh_res), ("SUP", sup_at, fresh_sup)):
            if not fresh[k] or levels[k] is None:
                continue
            level = levels[k]
            atrH4 = atr_h4[k]
            if not atrH4:
                continue
            tol = atrH4 * TOUCH_TOL_MULT
            start = h4_to_base_idx(k, candles, h4)
            if start is None:
                continue
            outcome = None
            broken_at = None
            for i in range(start, min(start + FORWARD_HORIZON, len(candles))):
                c1 = candles[i]["close"]
                if level - tol <= c1 <= level + tol:
                    if side == "RES":
                        outcome = "ROTTO" if c1 > level else "TENUTO"
                    else:
                        outcome = "ROTTO" if c1 < level else "TENUTO"
                    broken_at = i
                    break
            if outcome is None:
                events.append({"side": side, "outcome": "MAI_TOCCATO"})
                continue
            retested = None
            if outcome == "ROTTO":
                retested = False
                for j in range(broken_at + 1, min(broken_at + 1 + RETEST_WINDOW, len(candles))):
                    c1 = candles[j]["close"]
                    if level - tol <= c1 <= level + tol:
                        retested = True
                        break
            events.append({"side": side, "outcome": outcome, "retested": retested})
    return events


def print_frequency(events):
    n = len(events)
    toccati = [e for e in events if e["outcome"] != "MAI_TOCCATO"]
    tenuti = [e for e in toccati if e["outcome"] == "TENUTO"]
    rotti = [e for e in toccati if e["outcome"] == "ROTTO"]
    retest_ok = [e for e in rotti if e.get("retested")]
    print(f"Livelli OC formati: {n}")
    print(f"  mai toccati entro {FORWARD_HORIZON} barre: {n - len(toccati)} ({100*(n-len(toccati))/n:.0f}%)")
    print(f"  toccati: {len(toccati)}")
    if toccati:
        print(f"    TENUTO (rimbalzo/rifiuto): {len(tenuti)} ({100*len(tenuti)/len(toccati):.0f}%)")
        print(f"    ROTTO (continuazione): {len(rotti)} ({100*len(rotti)/len(toccati):.0f}%)")
    if rotti:
        print(f"      di cui con retest entro {RETEST_WINDOW} barre: {len(retest_ok)} "
              f"({100*len(retest_ok)/len(rotti):.0f}%)")


def sig_oc_immediate_continuation(candles, sess, atr, res_at, sup_at, atr_h4, ref, idx_map):
    """Continuazione IMMEDIATA sui livelli OC (rottura fresca, entra subito -
    il pezzo mancante: BREAKOUT esistente usa i livelli VECCHI 12-barre,
    non questi OC)."""
    n = len(candles)
    h4 = bt._resample_ohlc(ref, 4)
    d1 = bt._resample_ohlc(ref, 24)
    out = [0] * n
    for i in range(n):
        ri = idx_map[i]
        h4_idx, d1_idx = ri // 4 - 1, ri // 24 - 1
        if h4_idx < 3 or h4_idx >= len(h4) or d1_idx < 2:
            continue
        atrH4 = atr_h4[h4_idx]
        a = atr[i]
        if not atrH4 or not a:
            continue
        if sess["session"][i] == "ASIAN":
            continue
        h4C1, h4C4 = h4[h4_idx]["close"], h4[h4_idx - 3]["close"]
        d1C1, d1C2 = d1[d1_idx]["close"], d1[d1_idx - 1]["close"]
        story_bull = h4C1 > h4C4 and d1C1 >= d1C2
        story_bear = h4C1 < h4C4 and d1C1 <= d1C2
        resL, supL = res_at[h4_idx], sup_at[h4_idx]
        cur = candles[i]
        c1, o1 = cur["close"], cur["open"]
        c_prev = ref[ri - 1]["close"] if ri > 0 else c1
        if resL is not None and story_bull and c1 > resL and c_prev <= resL and c1 > o1:
            out[i] = 1
        elif supL is not None and story_bear and c1 < supL and c_prev >= supL and c1 < o1:
            out[i] = -1
    return out


def pnl_test(candles_full, ind_full, res_at, sup_at, atr_h4, ref, label, bar_range):
    n = len(candles_full)
    i0, i1 = int(n * bar_range[0]), int(n * bar_range[1])
    candles = candles_full[i0:i1]
    sess = {"session": ind_full["sess"]["session"][i0:i1]}
    atr = ind_full["atr"][i0:i1]
    # idx_map: la finestra e' un taglio CONTIGUO dello stesso array ref
    # (candles_full), quindi l'indice locale i mappa su i0+i nel ref - non
    # l'identita' (bug: con OOS i0>0 l'identita' punterebbe all'inizio del
    # ref invece che al vero punto della finestra).
    idx_map = list(range(i0, i1))
    sig = sig_oc_immediate_continuation(candles, sess, atr, res_at, sup_at, atr_h4, ref, idx_map)
    trades = []
    position = None
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
        if not a or sig[i] == 0:
            continue
        d = sig[i]
        entry = px
        sl = entry - 1.5 * a if d == 1 else entry + 1.5 * a
        tp = entry + 3.0 * a if d == 1 else entry - 3.0 * a
        position = {"dir": d, "entry": entry, "sl": sl, "tp": tp, "open_i": i, "risk": abs(entry - sl)}
    gw = sum(r for r in trades if r > 0)
    gl = -sum(r for r in trades if r < 0)
    pf = round(gw / gl, 2) if gl > 0 else (None if gw == 0 else float("inf"))
    print(f"{label}: trades={len(trades)} pf={pf}")


def main():
    candles, src = bt._fetch_real(SYMBOL, TF, bars=BARS)
    intraday = bt._load_dukascopy_m15(SYMBOL) if src == "dukascopy" else None
    ind = bt._prep(candles, intraday_ref=intraday)
    h4 = bt._resample_ohlc(candles, 4)
    atr_h4 = bt.atr_series(h4, 14)
    res_at, sup_at, fresh_res, fresh_sup = build_oc_levels(h4)

    print("=== Parte 1: frequenza TENUTO vs ROTTO sui livelli OC (periodo intero) ===")
    events = frequency_study(candles, h4, atr_h4, res_at, sup_at, fresh_res, fresh_sup)
    print_frequency(events)

    print("\n=== Parte 2: P&L continuazione immediata sui livelli OC (IS/OOS) ===")
    for label, br in [("IS 60%", (0.0, 0.6)), ("OOS 40%", (0.6, 1.0))]:
        pnl_test(candles, ind, res_at, sup_at, atr_h4, candles, label, br)


if __name__ == "__main__":
    main()
