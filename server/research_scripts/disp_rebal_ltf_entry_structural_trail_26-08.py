#!/usr/bin/env python3
"""26/08 - test della proposta dell'utente: invece dello stop nativo largo
di DISP_REBAL (H4, FVG - 0.3xATR(H4), spesso $15-40+), scendere sul TF
d'ingresso (M15) per un punto di reazione piu' preciso e uno stop piu'
stretto, poi gestire l'uscita con breakeven+trailing STRUTTURALE (non
ATR) invece di un target fisso.

ATTENZIONE - lezione gia' imparata il 16-17/08 (vedi vault "NEXUS EA -
Stop Strutturale M5 su Segnali H1"): uno stop stretto CON TARGET FISSO
INVARIATO ha fatto esplodere il R:R (7-15R medio, serie di 159-172
perdite consecutive, DD 100%+). Uno stop stretto CON TARGET PROPORZIONALE
FISSO ha fatto crollare l'edge per costi dominanti (stessa lezione di
CRT). Nessuna delle due varianti a target FISSO ha funzionato. Qui si
prova la variabile mai testata allora: BREAKEVEN PRECOCE + TRAILING
STRUTTURALE (non un target fisso di nessun tipo) - il vincitore non e'
incastrato in un R:R deciso in anticipo, corre finche' la struttura lo
permette.

Gate incluso (la richiesta esplicita di stanotte - "gate non testati in
Python falsano i risultati"): RISK_SIZE - simula NXS_CalcLotRisk. Al
lotto minimo (0.01 = 1oz XAUUSD, quindi risk_dist in prezzo = risk in $
circa 1:1), se risk_dist supera InpMaxRiskAtMinLotPct% del saldo,
l'ordine viene RIFIUTATO (non eseguito, non solo segnalato) - esatto
comportamento di NXS_Risk.mqh. Testato a $500 e $1000, coerente con
l'obiettivo esplicito dell'utente di poter partire anche da $500.

Non modella spread/altri gate MQL5 (troppo lavoro per un primo giro) -
usa comunque il modello di costo retail_standard gia' in uso tutta la
sessione per net_r, che approssima ragionevolmente il costo reale anche
senza un hard-cap sullo spread."""
import sys, os, bisect
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import backtest as bt

MAX_RISK_AT_MIN_LOT_PCT = 8.0   # InpMaxRiskAtMinLotPct, valore live
ACCOUNTS = [500.0, 1000.0]
SWING_WING = 3


def pf(rs):
    g = sum(r for r in rs if r > 0)
    l = -sum(r for r in rs if r < 0)
    return g / l if l > 0 else (float("inf") if g > 0 else 0.0)


def walk_forward(rs, nw=5):
    n = len(rs)
    if n < nw * 5:
        return None
    size = n // nw
    return [(len(rs[w * size:(w + 1) * size] if w < nw - 1 else rs[w * size:]),
              pf(rs[w * size:(w + 1) * size] if w < nw - 1 else rs[w * size:]))
            for w in range(nw)]


def net_series(trades, preset="retail_standard"):
    out = []
    for t in trades:
        cost = bt.scaled_cost_for_price(preset, t["entry"])
        cost_r = min((cost["spread_price"] + cost["slippage_price"]) / t["risk_dist"], bt.MAX_COST_R_PER_TRADE)
        out.append(t["raw_r"] - cost_r)
    return out


def fmt(label, trades):
    net = net_series(trades)
    wf = walk_forward(net)
    mid = len(net) // 2
    n_pos = sum(1 for _, p in (wf or []) if p >= 1.0)
    rd = sorted(t["risk_dist"] for t in trades)
    rd_med = rd[len(rd) // 2] if rd else 0.0
    # max losing streak on net_r
    streak = maxstreak = 0
    for v in net:
        if v < 0:
            streak += 1
            maxstreak = max(maxstreak, streak)
        else:
            streak = 0
    return (f"{label:34s} n={len(trades):5d} PF={pf(net):.2f} "
            f"(m1={pf(net[:mid]):.2f}/m2={pf(net[mid:]):.2f}) win={n_pos}/{len(wf) if wf else 0} "
            f"medRiskDist=${rd_med:.2f} maxLossStreak={maxstreak}")


def is_swing_high(highs, i, wing):
    h = highs[i]
    if h <= 0:
        return False
    for k in range(1, wing + 1):
        if i + k < len(highs) and highs[i + k] >= h: return False
        if i - k >= 0 and highs[i - k] >= h: return False
    return True


def is_swing_low(lows, i, wing):
    l = lows[i]
    if l <= 0:
        return False
    for k in range(1, wing + 1):
        if i + k < len(lows) and lows[i + k] <= l: return False
        if i - k >= 0 and lows[i - k] <= l: return False
    return True


def disp_bar(opens, closes, atr, i, direction, lookback, bodyMult, a):
    for sft in range(1, lookback + 1):
        idx = i - sft + 1
        if idx < 0:
            break
        o, c = opens[idx], closes[idx]
        if abs(c - o) < a * bodyMult:
            continue
        if direction > 0 and c > o:
            return sft
        if direction < 0 and c < o:
            return sft
    return -1


def find_native_signals(candlesH4, indH4):
    """Ricetta live esatta di DISP_REBAL (H4) - stessa di stanotte."""
    highs = [c["high"] for c in candlesH4]
    lows = [c["low"] for c in candlesH4]
    closes = [c["close"] for c in candlesH4]
    opens = [c["open"] for c in candlesH4]
    times = [c["time"] for c in candlesH4]
    atr = indH4["atr"]
    n = len(candlesH4)
    out = []
    for i in range(30, n - 1):
        a = atr[i]
        if not a:
            continue
        c1, o1 = closes[i], opens[i]
        bid = c1
        sig = None
        dS = disp_bar(opens, closes, atr, i, +1, 8, 1.3, a)
        if dS > 1:
            idxD = i - dS + 1
            c1High, c3Low = highs[idxD - 1], lows[idxD + 1]
            if c3Low > c1High + a * 0.1:
                fvgLo, fvgHi = c1High, c3Low
                ce = (fvgLo + fvgHi) * 0.5
                if fvgLo <= bid <= ce + a * 0.15 and c1 > o1:
                    sig = 1
                    native_sl = fvgLo - 0.3 * a
                    native_tp = max(fvgHi + 0.8 * (fvgHi - fvgLo), bid + 2.4 * (bid - native_sl))
                    zone = (fvgLo, fvgHi)
        if sig is None:
            dSb = disp_bar(opens, closes, atr, i, -1, 8, 1.3, a)
            if dSb > 1:
                idxD = i - dSb + 1
                c1Low, c3High = lows[idxD - 1], highs[idxD + 1]
                if c1Low > c3High + a * 0.1:
                    fvgLo, fvgHi = c3High, c1Low
                    ce = (fvgLo + fvgHi) * 0.5
                    if ce - a * 0.15 <= bid <= fvgHi and c1 < o1:
                        sig = -1
                        native_sl = fvgHi + 0.3 * a
                        native_tp = min(fvgLo - 0.8 * (fvgHi - fvgLo), bid - 2.4 * (native_sl - bid))
                        zone = (fvgLo, fvgHi)
        if sig is None:
            continue
        out.append({"i": i, "time": times[i], "dir": sig, "entry_native": bid,
                     "sl_native": native_sl, "tp_native": native_tp, "zone": zone, "atr_h4": a})
    return out


def run_native(signals, candlesH4):
    highs = [c["high"] for c in candlesH4]
    lows = [c["low"] for c in candlesH4]
    n = len(candlesH4)
    out = []
    for s in signals:
        i, sig, entry, sl, tp = s["i"], s["dir"], s["entry_native"], s["sl_native"], s["tp_native"]
        rd = abs(entry - sl)
        if rd <= 0:
            continue
        exit_r = None
        for j in range(i + 1, min(i + 500, n)):
            hi, lo = highs[j], lows[j]
            if sig == 1:
                if lo <= sl: exit_r = (sl - entry) / rd; break
                if hi >= tp: exit_r = (tp - entry) / rd; break
            else:
                if hi >= sl: exit_r = (entry - sl) / rd; break
                if lo <= tp: exit_r = (entry - tp) / rd; break
        if exit_r is None:
            continue
        out.append({"entry": entry, "risk_dist": rd, "raw_r": exit_r, "dir": sig, "time": s["time"]})
    return out


def run_ltf_refined(signals, candlesM15, trail_mode, breakeven_at_r=0.5, max_wait_bars=8, max_hold_bars=3000):
    """Per ogni segnale H4, cerca sul M15 (dentro/subito dopo la zona FVG,
    entro max_wait_bars M15) una candela di reazione reale (corpo forte in
    direzione + tocco della zona) e usa il suo estremo come stop. Poi
    gestisce l'uscita con breakeven a breakeven_at_r*rischio_iniziale, poi
    trailing strutturale (trail_mode: 'prev_low' = minimo/massimo della
    candela M15 precedente; 'swing' = ultimo swing M15 confermato)."""
    times15 = [c["time"] for c in candlesM15]
    highs15 = [c["high"] for c in candlesM15]
    lows15 = [c["low"] for c in candlesM15]
    closes15 = [c["close"] for c in candlesM15]
    opens15 = [c["open"] for c in candlesM15]
    n15 = len(candlesM15)
    ind15 = bt._prep(candlesM15)
    atr15 = ind15["atr"]

    def m15_idx_at(t):
        return bisect.bisect_right(times15, t) - 1

    out = []
    for s in signals:
        sig = s["dir"]
        zoneLo, zoneHi = s["zone"]
        h4_i15 = m15_idx_at(s["time"])
        if h4_i15 < 30:
            continue
        # cerca la reazione entro max_wait_bars M15 successive alla chiusura H4
        entry_idx = None
        sl0 = None
        for w in range(1, max_wait_bars + 1):
            j = h4_i15 + w
            if j >= n15 - 1:
                break
            o, c, hi, lo = opens15[j], closes15[j], highs15[j], lows15[j]
            a15 = atr15[j]
            if not a15:
                continue
            body = abs(c - o)
            inZone = (lo <= zoneHi and hi >= zoneLo)
            if not inZone:
                continue
            strongBody = body > a15 * 0.3
            if sig == 1 and c > o and strongBody:
                entry_idx = j
                sl0 = lo - 0.2 * a15
                break
            if sig == -1 and c < o and strongBody:
                entry_idx = j
                sl0 = hi + 0.2 * a15
                break
        if entry_idx is None:
            continue
        entry_i = entry_idx + 1
        if entry_i >= n15:
            continue
        entry = candlesM15[entry_i]["open"]
        rd0 = abs(entry - sl0)
        if rd0 <= 0:
            continue

        sl = sl0
        be_done = False
        exit_r = None
        for j in range(entry_i + 1, min(entry_i + max_hold_bars, n15)):
            hi, lo = highs15[j], lows15[j]
            if sig == 1:
                if lo <= sl:
                    exit_r = (sl - entry) / rd0
                    break
                if not be_done and hi >= entry + breakeven_at_r * rd0:
                    sl = max(sl, entry)
                    be_done = True
                if trail_mode == "prev_low":
                    newsl = lows15[j - 1] - 0.1 * (atr15[j] or 0)
                    if newsl > sl:
                        sl = newsl
                elif trail_mode == "swing":
                    if is_swing_low(lows15, j - SWING_WING, SWING_WING):
                        newsl = lows15[j - SWING_WING]
                        if newsl > sl:
                            sl = newsl
            else:
                if hi >= sl:
                    exit_r = (entry - sl) / rd0
                    break
                if not be_done and lo <= entry - breakeven_at_r * rd0:
                    sl = min(sl, entry)
                    be_done = True
                if trail_mode == "prev_low":
                    newsl = highs15[j - 1] + 0.1 * (atr15[j] or 0)
                    if newsl < sl:
                        sl = newsl
                elif trail_mode == "swing":
                    if is_swing_high(highs15, j - SWING_WING, SWING_WING):
                        newsl = highs15[j - SWING_WING]
                        if newsl < sl:
                            sl = newsl
        if exit_r is None:
            continue
        out.append({"entry": entry, "risk_dist": rd0, "raw_r": exit_r, "dir": sig, "time": s["time"]})
    return out


def apply_risk_size_gate(trades, balance):
    kept, rejected = [], 0
    for t in trades:
        risk_at_min_lot = t["risk_dist"]  # 0.01 lot XAUUSD ~= $1/point -> risk_dist in price = risk in $
        if risk_at_min_lot > balance * (MAX_RISK_AT_MIN_LOT_PCT / 100.0):
            rejected += 1
            continue
        kept.append(t)
    return kept, rejected


def main():
    candlesH4, _ = bt._fetch_real("XAUUSD", "4h", 40000)
    candlesM15, _ = bt._fetch_real("XAUUSD", "15m", 130000)
    indH4 = bt._prep(candlesH4)

    signals = find_native_signals(candlesH4, indH4)
    print(f"Segnali H4 DISP_REBAL grezzi (pre-gate): {len(signals)}", flush=True)

    native = run_native(signals, candlesH4)
    ltf_prevlow = run_ltf_refined(signals, candlesM15, "prev_low")
    ltf_swing = run_ltf_refined(signals, candlesM15, "swing")

    print("\n=== BASELINE: stop nativo H4, target fisso (ricetta live di stanotte) ===", flush=True)
    print(fmt("nativo", native), flush=True)

    print("\n=== NUOVO: ingresso raffinato M15 + breakeven 0.5R + trailing 'candela precedente' ===", flush=True)
    print(fmt("LTF+trail(prev_low)", ltf_prevlow), flush=True)

    print("\n=== NUOVO: ingresso raffinato M15 + breakeven 0.5R + trailing 'ultimo swing M15' ===", flush=True)
    print(fmt("LTF+trail(swing)", ltf_swing), flush=True)

    for label, trades in (("nativo", native), ("LTF+trail(prev_low)", ltf_prevlow), ("LTF+trail(swing)", ltf_swing)):
        print(f"\n--- Gate RISK_SIZE per '{label}' ---", flush=True)
        for bal in ACCOUNTS:
            kept, rejected = apply_risk_size_gate(trades, bal)
            tot = len(trades)
            pct_rejected = 100.0 * rejected / tot if tot else 0.0
            print(f"  saldo=${bal:.0f}: rifiutati {rejected}/{tot} ({pct_rejected:.1f}%)  ->  " +
                  fmt("eseguiti", kept), flush=True)


if __name__ == "__main__":
    main()
