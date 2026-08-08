#!/usr/bin/env python3
"""
08/08 - prototipo Python della State Machine adattiva discussa con l'utente
(prompt corretto per l'agente MQL5): rect_engine (NUOVO, non esisteva) +
structure_engine (choch_int/choch_ext, gia' in backtest.py) decidono il
regime; il Modello Istituzionale (9 strategie, gia' portato oggi) esegue
solo nello stato TREND, un fade ai bordi del box esegue nello stato RANGE.

rect_engine: box N barre (rolling, SOLO barre chiuse precedenti, niente
look-ahead) - RANGING se il prezzo e' dentro, BROKEN_UP/DOWN se chiude
oltre con corpo di conferma (stesso principio gia' validato per LONDON_BO:
niente breakout "a tocco marginale").

3 varianti confrontate:
  A) BASELINE - Istituzionale sempre attivo, nessun gate di regime (= il
     test "ibrido" di oggi, PF 1.64/84 trade, per confronto)
  B) TREND-GATE - Istituzionale attivo SOLO quando rect_engine conferma un
     breakout, E solo nella direzione del breakout (rigoroso come da
     richiesta: "filtrata in direzione del trend")
  C) TREND-GATE + RANGE-FADE - B) + una logica di fade ai bordi del box
     quando rect_engine dice RANGING (wick oltre il bordo, chiusura dentro
     = falso breakout, turtle-soup-style sul box stesso)

NON include NXS_SMCReactionOK (non esiste in Python, dichiarato nel prompt
corretto) ne' il News Filter (nessun dato calendario storico disponibile
qui). Stesso universo/score/famiglie del test Istituzionale di oggi.
"""
import sys
from collections import Counter
sys.path.insert(0, "server")
import backtest as bt

COSTS = bt.COST_PRESETS["retail_standard"]
SYMBOL = "XAUUSD"
TF = "1d"
HTF_FACTOR = 5

BUY_ONLY = {"SCALP_EMA", "BREAKOUT_ACC", "LIQ_VOID", "SAR", "SCALP_RANGE_BRK"}
BIDIRECTIONAL = {"TSI", "SH_BMS_RTO", "FVG_CONT", "LIQ_SWEEP"}
STRATS = sorted(BUY_ONLY | BIDIRECTIONAL)
SCORES = {
    "SAR": 60.0, "TSI": 66.0, "BREAKOUT_ACC": 68.0, "LIQ_SWEEP": 72.0,
    "FVG_CONT": 70.0, "LIQ_VOID": 73.0, "SH_BMS_RTO": 74.0,
    "SCALP_EMA": 70.0, "SCALP_RANGE_BRK": 70.0,
}
INST_MIN_CONVICTION = 60.0
INST_MIN_CONTRIBUTORS = 1
INST_BASE_SL = 2.0
INST_BASE_TP = 4.0
TIER_MULT = {0: 1.0, 1: 2.0, 2: 3.5}

# rect_engine
RECT_N = 20
RECT_CONFIRM_BODY_ATR = 0.3

RISK_PCT = 1.0
START_EQUITY = 10000.0
MAX_HOLD = 40
RANGE_MAX_HOLD = 15  # il fade ai bordi e' un trade piu' corto, non un trend-follow


def _family(name):
    if any(k in name for k in ("FVG", "IFVG", "DISP", "VOID")):
        return "IMBALANCE"
    if any(k in name for k in ("OB", "ORDER_BLOCK", "BMS", "STRUCT")):
        return "STRUCTURE"
    if any(k in name for k in ("LIQ", "SWEEP", "TURTLE", "JUDAS")):
        return "LIQUIDITY"
    if any(k in name for k in ("REVERSAL", "RSI", "BOLLINGER", "RANGE")):
        return "MEAN_REVERSION"
    if any(k in name for k in ("BREAKOUT", "BO", "MACD", "ADX", "EMA", "SAR")):
        return "MOMENTUM"
    return "OTHER"


def conviction(contribs):
    fam_cnt = {}
    buy_adj = sell_adj = 0.0
    buy_n = sell_n = 0
    for name, d, score in contribs:
        fam = _family(name)
        w = 1.0 / (fam_cnt.get(fam, 0) + 1)
        fam_cnt[fam] = fam_cnt.get(fam, 0) + 1
        if d == 1:
            buy_adj += score * w; buy_n += 1
        else:
            sell_adj += score * w; sell_n += 1
    return buy_adj, sell_adj, buy_n, sell_n


def rect_engine_series(candles, atr, n=RECT_N, confirm_body_atr=RECT_CONFIRM_BODY_ATR):
    """NUOVO - non esisteva. Box rolling di n barre CHIUSE precedenti (niente
    barra corrente, niente look-ahead). RANGING se il prezzo e' dentro il
    box; BROKEN_UP/DOWN se la barra corrente chiude oltre il bordo CON corpo
    di conferma (>= confirm_body_atr x ATR), non un tocco marginale."""
    out = ["RANGING"] * len(candles)
    box_hi = [None] * len(candles)
    box_lo = [None] * len(candles)
    for i in range(n, len(candles)):
        window = candles[i - n:i]
        hi = max(x["high"] for x in window)
        lo = min(x["low"] for x in window)
        box_hi[i], box_lo[i] = hi, lo
        a = atr[i]
        if not a:
            continue
        c, o = candles[i]["close"], candles[i]["open"]
        body = abs(c - o)
        if c > hi and body >= confirm_body_atr * a:
            out[i] = "BROKEN_UP"
        elif c < lo and body >= confirm_body_atr * a:
            out[i] = "BROKEN_DOWN"
    return out, box_hi, box_lo


def rect_fade_signal(candles, atr, box_hi, box_lo, i):
    """Falso breakout stile Turtle Soup sul bordo del box: wick oltre il
    bordo, chiusura rientrata dentro -> fade. SL oltre il wick, TP a meta'
    box (consequent encroachment, stesso principio gia' usato da LIQ_VOID)."""
    a = atr[i]
    hi, lo = box_hi[i], box_lo[i]
    if not a or hi is None or lo is None or hi <= lo:
        return 0, None, None
    h, l, c = candles[i]["high"], candles[i]["low"], candles[i]["close"]
    mid = (hi + lo) / 2.0
    if l < lo and c > lo and c < mid:
        sl = l - 0.3 * a
        return 1, sl, mid
    if h > hi and c < hi and c > mid:
        sl = h + 0.3 * a
        return -1, sl, mid
    return 0, None, None


def run(variant):
    """variant: 'BASELINE' | 'TREND_GATE' | 'TREND_GATE_RANGE_FADE'"""
    candles, src = bt._fetch_real(SYMBOL, TF)
    ind = bt._prep(candles)
    htf_trend, _, _ = bt._external_choch_series(candles, factor=HTF_FACTOR, wing=3)
    atr = ind["atr"]
    adx = ind["adx"]
    rect_state, box_hi, box_lo = rect_engine_series(candles, atr)

    equity = START_EQUITY
    trades = []
    position = None
    n = len(candles)
    for i in range(60, n):
        px = candles[i]["close"]
        if position is not None:
            hi, lo = candles[i]["high"], candles[i]["low"]
            hit = None
            if position["dir"] == 1:
                if lo <= position["sl"]:
                    hit = ("SL", position["sl"])
                elif hi >= position["tp"]:
                    hit = ("TP", position["tp"])
            else:
                if hi >= position["sl"]:
                    hit = ("SL", position["sl"])
                elif lo <= position["tp"]:
                    hit = ("TP", position["tp"])
            if not hit and (i - position["open_i"]) >= position["max_hold"]:
                hit = ("TIME", px)
            if hit:
                reason, exitpx = hit
                rd = position["risk_dist"] if position["risk_dist"] > 0 else 1e-9
                r_mult = ((exitpx - position["entry"]) / rd) if position["dir"] == 1 \
                    else ((position["entry"] - exitpx) / rd)
                spread_r = COSTS["spread_price"] / rd if COSTS["spread_price"] > 0 else 0.0
                slip_r = 0.0
                if COSTS["slippage_price"] > 0:
                    slip_r = COSTS["slippage_price"] / rd
                    if reason in ("SL", "TIME"):
                        slip_r += COSTS["slippage_price"] / rd
                r_net = r_mult - spread_r - COSTS["commission_r"] - slip_r
                pnl = round(r_net * position["risk_money"], 2)
                equity += pnl
                trades.append({"side": "BUY" if position["dir"] == 1 else "SELL",
                                "pnl": pnl, "reason": reason, "source": position["source"]})
                position = None
            continue

        a = atr[i]
        adx_i = adx[i]
        if not a or adx_i is None or adx_i < 20.0:
            continue
        regime = rect_state[i]

        if variant == "BASELINE" or regime != "RANGING":
            # stato TREND (o baseline senza gate) - Modello Istituzionale
            contribs = []
            for s in STRATS:
                v = bt.STRATEGIES[s](candles, ind, i)
                if v == 0:
                    continue
                if s in BUY_ONLY and v == -1:
                    continue
                contribs.append((s, v, SCORES[s]))
            if contribs:
                buy_adj, sell_adj, buy_n, sell_n = conviction(contribs)
                if buy_adj or sell_adj:
                    dir_ = 1 if buy_adj >= sell_adj else -1
                    net = abs(buy_adj - sell_adj)
                    contributors = buy_n if dir_ == 1 else sell_n
                    ok = net >= INST_MIN_CONVICTION and contributors >= INST_MIN_CONTRIBUTORS
                    if ok and dir_ == -1:
                        ok = False  # nucleo BUY-only nel prototipo: SELL mai eseguito, solo filtro passivo
                    if ok and variant in ("TREND_GATE", "TREND_GATE_RANGE_FADE"):
                        # rigoroso in direzione del trend: il breakout deve concordare col verso deciso
                        if (regime == "BROKEN_UP" and dir_ != 1) or (regime == "BROKEN_DOWN" and dir_ != -1):
                            ok = False
                    if ok:
                        st = ind["choch_int"][0][i]
                        ht = htf_trend[i]
                        sw = bt._sweep_ext_at_raw(candles, ind["sess"], i, atr,
                                                   ind["weekly_pwh"], ind["weekly_pwl"],
                                                   ind["monthly_pmh"], ind["monthly_pml"])
                        sweep_dir = sw["dir"] if sw else 0
                        aligned = sum(1 for x in (st, ht, sweep_dir) if x == dir_)
                        tier = 2 if aligned >= 3 else (1 if aligned >= 2 else 0)
                        mult = TIER_MULT[tier]
                        sl_dist = a * INST_BASE_SL * mult
                        tp_dist = a * INST_BASE_TP * mult
                        entry = px
                        sl = entry - sl_dist if dir_ == 1 else entry + sl_dist
                        tp = entry + tp_dist if dir_ == 1 else entry - tp_dist
                        position = {"dir": dir_, "entry": entry, "sl": sl, "tp": tp,
                                    "open_i": i, "risk_dist": sl_dist,
                                    "risk_money": equity * (RISK_PCT / 100.0),
                                    "source": "INST", "max_hold": MAX_HOLD}
        elif variant == "TREND_GATE_RANGE_FADE" and regime == "RANGING":
            d, sl, tp = rect_fade_signal(candles, atr, box_hi, box_lo, i)
            if d != 0:
                entry = px
                risk_dist = abs(entry - sl)
                position = {"dir": d, "entry": entry, "sl": sl, "tp": tp,
                            "open_i": i, "risk_dist": risk_dist,
                            "risk_money": equity * (RISK_PCT / 100.0),
                            "source": "RANGE_FADE", "max_hold": RANGE_MAX_HOLD}

    gross_win = sum(t["pnl"] for t in trades if t["pnl"] > 0)
    gross_loss = -sum(t["pnl"] for t in trades if t["pnl"] < 0)
    pf = round(gross_win / gross_loss, 2) if gross_loss > 0 else None
    wr = round(100 * sum(1 for t in trades if t["pnl"] >= 0) / len(trades), 1) if trades else None
    net_pnl = round(equity - START_EQUITY, 2)

    by_source = {}
    for src_name in ("INST", "RANGE_FADE"):
        lst = [t for t in trades if t["source"] == src_name]
        if not lst:
            continue
        g = sum(t["pnl"] for t in lst if t["pnl"] > 0); l = -sum(t["pnl"] for t in lst if t["pnl"] < 0)
        pf_s = round(g / l, 2) if l > 0 else None
        by_source[src_name] = (len(lst), pf_s)

    print(f"\n=== {variant} ===  (regimi: {Counter(rect_state[60:])})")
    print(f"  trades={len(trades)}  PF={pf}  WR={wr}%  net_pnl={net_pnl}")
    print(f"  per fonte: {by_source}")
    print(f"  reason: {Counter(t['reason'] for t in trades)}")
    return {"variant": variant, "trades": len(trades), "pf": pf, "wr": wr, "net_pnl": net_pnl}


def main():
    results = []
    for v in ("BASELINE", "TREND_GATE", "TREND_GATE_RANGE_FADE"):
        results.append(run(v))
    print("\n" + "=" * 70)
    print(f"{'Variante':<26}{'Trade':>7}{'PF':>7}{'WR%':>7}{'NetPnL':>10}")
    for r in results:
        print(f"{r['variant']:<26}{r['trades']:>7}{str(r['pf']):>7}{str(r['wr']):>7}{r['net_pnl']:>10}")


if __name__ == "__main__":
    main()
