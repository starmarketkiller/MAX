#!/usr/bin/env python3
"""
08/08 - versione "blindata" (rifattorizzata, riusabile) del TREND_GATE che
oggi ha dato PF 2.28 nel prototipo state_machine_test.py. Stessa logica
ESATTA (rect_engine + institutional conviction + gate direzionale sul
breakout confermato), estratta in una funzione unica cosi' la si puo'
applicare a QUALSIASI gruppo di strategie/TF senza duplicare codice -
usata sotto per ciclare sulle strategie "in quarantena".

Nessuna modifica alla logica gia' validata: stessi INST_MIN_CONVICTION=60,
INST_BASE_SL/TP=2.0/4.0, tier su 3 componenti, rect_engine N=20 barre
+ conferma corpo >=0.3xATR, adx_min=20, MAX_HOLD=40 - identici a prima.
"""
import sys
sys.path.insert(0, "server")
import backtest as bt

COSTS = bt.COST_PRESETS["retail_standard"]
SYMBOL = "XAUUSD"
HTF_FACTOR_BY_TF = {"1h": 4, "4h": 6, "1d": 5}  # stesso criterio di mtf_cascade_test.py

INST_MIN_CONVICTION = 60.0
INST_MIN_CONTRIBUTORS = 1
INST_BASE_SL = 2.0
INST_BASE_TP = 4.0
TIER_MULT = {0: 1.0, 1: 2.0, 2: 3.5}

RECT_N = 20
RECT_CONFIRM_BODY_ATR = 0.3

RISK_PCT = 1.0
START_EQUITY = 10000.0
MAX_HOLD = 40


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


def _conviction(contribs):
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


def _rect_engine_series(candles, atr, n=RECT_N, confirm_body_atr=RECT_CONFIRM_BODY_ATR):
    out = ["RANGING"] * len(candles)
    for i in range(n, len(candles)):
        window = candles[i - n:i]
        hi = max(x["high"] for x in window)
        lo = min(x["low"] for x in window)
        a = atr[i]
        if not a:
            continue
        c, o = candles[i]["close"], candles[i]["open"]
        body = abs(c - o)
        if c > hi and body >= confirm_body_atr * a:
            out[i] = "BROKEN_UP"
        elif c < lo and body >= confirm_body_atr * a:
            out[i] = "BROKEN_DOWN"
    return out


def run_trend_gate(strats, tf, buy_only=frozenset(), scores=None, bars_min=60,
                    buy_only_execution=True):
    """Ciclo TREND_GATE su un gruppo di strategie condiviso su un TF.
    strats: lista id strategia (bt.STRATEGIES). buy_only: sottoinsieme a cui
    e' vietato contribuire come SELL (replica direction_lock gia' validato).
    scores: dict id->score reale MQL5, default 70 (uniforme, dichiarato) per
    chi non ce l'ha (RESEARCH_ONLY o non ancora cercato).
    buy_only_execution: se True (default, FEDELE al PF 2.28 misurato in
    state_machine_test.py) il sistema non esegue MAI un SELL anche se la
    conviction e il regime BROKEN_DOWN lo permetterebbero - eredita' dal
    test "ibrido" precedente, non e' specifico del TREND_GATE. Mettere a
    False per lasciar eseguire anche SELL quando regime+conviction
    concordano (utile per capire se una strategia sotto quarantena ha un
    vero lato short da questo gate, cosa che con True resterebbe invisibile)."""
    scores = scores or {}
    candles, src = bt._fetch_real(SYMBOL, tf)
    ind = bt._prep(candles)
    factor = HTF_FACTOR_BY_TF.get(tf, 5)
    htf_trend, _, _ = bt._external_choch_series(candles, factor=factor, wing=3)
    struct_trend = ind["choch_int"][0]
    atr = ind["atr"]
    adx = ind["adx"]
    rect_state = _rect_engine_series(candles, atr)

    equity = START_EQUITY
    trades = []
    position = None
    n = len(candles)
    for i in range(bars_min, n):
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
            if not hit and (i - position["open_i"]) >= MAX_HOLD:
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
                trades.append({"side": "BUY" if position["dir"] == 1 else "SELL", "pnl": pnl, "reason": reason})
                position = None
            continue

        a = atr[i]
        adx_i = adx[i]
        if not a or adx_i is None or adx_i < 20.0:
            continue
        regime = rect_state[i]
        if regime == "RANGING":
            continue

        contribs = []
        for s in strats:
            v = bt.STRATEGIES[s](candles, ind, i)
            if v == 0:
                continue
            if s in buy_only and v == -1:
                continue
            contribs.append((s, v, scores.get(s, 70.0)))
        if not contribs:
            continue
        buy_adj, sell_adj, buy_n, sell_n = _conviction(contribs)
        if not (buy_adj or sell_adj):
            continue
        dir_ = 1 if buy_adj >= sell_adj else -1
        net = abs(buy_adj - sell_adj)
        contributors = buy_n if dir_ == 1 else sell_n
        if net < INST_MIN_CONVICTION or contributors < INST_MIN_CONTRIBUTORS:
            continue
        if buy_only_execution and dir_ == -1:
            continue
        if (regime == "BROKEN_UP" and dir_ != 1) or (regime == "BROKEN_DOWN" and dir_ != -1):
            continue

        st = struct_trend[i]
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
        position = {"dir": dir_, "entry": entry, "sl": sl, "tp": tp, "open_i": i,
                    "risk_dist": sl_dist, "risk_money": equity * (RISK_PCT / 100.0)}

    gross_win = sum(t["pnl"] for t in trades if t["pnl"] > 0)
    gross_loss = -sum(t["pnl"] for t in trades if t["pnl"] < 0)
    pf = round(gross_win / gross_loss, 2) if gross_loss > 0 else (None if gross_win == 0 else float("inf"))
    wr = round(100 * sum(1 for t in trades if t["pnl"] >= 0) / len(trades), 1) if trades else None
    buys = [t for t in trades if t["side"] == "BUY"]
    sells = [t for t in trades if t["side"] == "SELL"]
    def _pf(lst):
        g = sum(t["pnl"] for t in lst if t["pnl"] > 0); l = -sum(t["pnl"] for t in lst if t["pnl"] < 0)
        return round(g / l, 2) if l > 0 else (None if g == 0 else float("inf"))
    return {
        "src": src, "trades": len(trades), "pf": pf, "wr": wr,
        "net_pnl": round(equity - START_EQUITY, 2),
        "n_buy": len(buys), "pf_buy": _pf(buys), "n_sell": len(sells), "pf_sell": _pf(sells),
    }


def _run_gated(strat, tf, score, gate_fn, bars_min=60):
    """Nucleo condiviso da run_range_gate/run_session_gate: STESSO tier/SL-TP
    del TREND_GATE, ma il gate di ingresso (`gate_fn(regime, session, i)` ->
    bool) e' esterno e sostituisce del tutto il breakout+direzione - qui la
    strategia esegue in ENTRAMBE le direzioni (mean-reversion/reversal non
    hanno un "lato" di default come il nucleo trend BUY-only)."""
    candles, src = bt._fetch_real(SYMBOL, tf)
    ind = bt._prep(candles)
    factor = HTF_FACTOR_BY_TF.get(tf, 5)
    htf_trend, _, _ = bt._external_choch_series(candles, factor=factor, wing=3)
    struct_trend = ind["choch_int"][0]
    atr = ind["atr"]
    adx = ind["adx"]
    rect_state = _rect_engine_series(candles, atr)

    equity = START_EQUITY
    trades = []
    position = None
    n = len(candles)
    for i in range(bars_min, n):
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
            if not hit and (i - position["open_i"]) >= MAX_HOLD:
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
                trades.append({"side": "BUY" if position["dir"] == 1 else "SELL", "pnl": pnl, "reason": reason})
                position = None
            continue

        a = atr[i]
        adx_i = adx[i]
        if not a or adx_i is None or adx_i < 20.0:
            continue
        if not gate_fn(rect_state[i], ind["sess"]["session"][i], i):
            continue

        v = bt.STRATEGIES[strat](candles, ind, i)
        if v == 0:
            continue
        dir_ = v
        st = struct_trend[i]
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
        position = {"dir": dir_, "entry": entry, "sl": sl, "tp": tp, "open_i": i,
                    "risk_dist": sl_dist, "risk_money": equity * (RISK_PCT / 100.0)}

    gross_win = sum(t["pnl"] for t in trades if t["pnl"] > 0)
    gross_loss = -sum(t["pnl"] for t in trades if t["pnl"] < 0)
    pf = round(gross_win / gross_loss, 2) if gross_loss > 0 else (None if gross_win == 0 else float("inf"))
    wr = round(100 * sum(1 for t in trades if t["pnl"] >= 0) / len(trades), 1) if trades else None
    buys = [t for t in trades if t["side"] == "BUY"]
    sells = [t for t in trades if t["side"] == "SELL"]
    def _pf(lst):
        g = sum(t["pnl"] for t in lst if t["pnl"] > 0); l = -sum(t["pnl"] for t in lst if t["pnl"] < 0)
        return round(g / l, 2) if l > 0 else (None if g == 0 else float("inf"))
    return {
        "src": src, "trades": len(trades), "pf": pf, "wr": wr,
        "net_pnl": round(equity - START_EQUITY, 2),
        "n_buy": len(buys), "pf_buy": _pf(buys), "n_sell": len(sells), "pf_sell": _pf(sells),
    }


def run_range_gate(strat, tf, score=70.0, bars_min=60):
    """08/08 - Gruppo A (mean-reversion vera): esegue SOLO quando rect_engine
    dice RANGING (l'opposto esatto del TREND_GATE) - nessun requisito di
    direzione (il rimbalzo puo' essere BUY o SELL, decide il segnale nativo
    della strategia)."""
    return _run_gated(strat, tf, score, lambda regime, sess, i: regime == "RANGING", bars_min)


def run_session_gate(strat, tf, score=70.0, sessions=frozenset({"LONDON", "NY"}), bars_min=60):
    """08/08 - Gruppo B (reversal di sessione): esegue SOLO nelle sessioni
    indicate (default LONDON+NY, stesso set gia' usato da session_filter nel
    motore principale) - NESSUNA dipendenza da rect_engine/trend, la
    congestione o il breakout non c'entrano per queste strategie."""
    return _run_gated(strat, tf, score, lambda regime, sess, i: sess in sessions, bars_min)


def run_trend_gate_windowed(strat, tf, score=70.0, wait_bars=10, bars_min=60):
    """08/08 - Gruppo C ("continuazione ritardata"): stesso rect_engine/tier/
    SL-TP del TREND_GATE, ma NON pretende che rottura+ADX+segnale cadano
    sulla stessa barra. Su ogni TRANSIZIONE verso BROKEN_UP/DOWN (non ad
    ogni barra del breakout, solo il momento in cui scatta - altrimenti si
    riarma ogni barra e la finestra perde senso) si apre una finestra di
    `wait_bars` barre in quella direzione; se durante la finestra il
    segnale NATIVO della strategia scatta nella STESSA direzione (e ADX
    resta >=20), si entra. Stesso schema a stati gia' usato da SH_BMS_RTO/
    Silver Bullet (IDLE -> WAITING -> entry o scadenza), qui applicato al
    gate di trend invece che a uno sweep."""
    candles, src = bt._fetch_real(SYMBOL, tf)
    ind = bt._prep(candles)
    factor = HTF_FACTOR_BY_TF.get(tf, 5)
    htf_trend, _, _ = bt._external_choch_series(candles, factor=factor, wing=3)
    struct_trend = ind["choch_int"][0]
    atr = ind["atr"]
    adx = ind["adx"]
    rect_state = _rect_engine_series(candles, atr)

    equity = START_EQUITY
    trades = []
    position = None
    window = None   # {"dir": 1/-1, "deadline": bar_idx}
    n = len(candles)
    for i in range(bars_min, n):
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
            if not hit and (i - position["open_i"]) >= MAX_HOLD:
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
                trades.append({"side": "BUY" if position["dir"] == 1 else "SELL", "pnl": pnl, "reason": reason})
                position = None
            continue

        a = atr[i]
        adx_i = adx[i]
        if not a:
            continue
        regime = rect_state[i]
        prev_regime = rect_state[i - 1] if i > 0 else "RANGING"

        # arma/ri-arma la finestra SOLO sulla transizione verso un breakout fresco
        if regime in ("BROKEN_UP", "BROKEN_DOWN") and regime != prev_regime:
            window = {"dir": 1 if regime == "BROKEN_UP" else -1, "deadline": i + wait_bars}

        if window is None:
            continue
        if i > window["deadline"]:
            window = None
            continue
        if adx_i is None or adx_i < 20.0:
            continue

        v = bt.STRATEGIES[strat](candles, ind, i)
        if v == 0 or v != window["dir"]:
            continue

        dir_ = v
        st = struct_trend[i]
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
        position = {"dir": dir_, "entry": entry, "sl": sl, "tp": tp, "open_i": i,
                    "risk_dist": sl_dist, "risk_money": equity * (RISK_PCT / 100.0)}
        window = None   # consumata, one-shot come SH_BMS_RTO/Silver Bullet

    gross_win = sum(t["pnl"] for t in trades if t["pnl"] > 0)
    gross_loss = -sum(t["pnl"] for t in trades if t["pnl"] < 0)
    pf = round(gross_win / gross_loss, 2) if gross_loss > 0 else (None if gross_win == 0 else float("inf"))
    wr = round(100 * sum(1 for t in trades if t["pnl"] >= 0) / len(trades), 1) if trades else None
    buys = [t for t in trades if t["side"] == "BUY"]
    sells = [t for t in trades if t["side"] == "SELL"]
    def _pf(lst):
        g = sum(t["pnl"] for t in lst if t["pnl"] > 0); l = -sum(t["pnl"] for t in lst if t["pnl"] < 0)
        return round(g / l, 2) if l > 0 else (None if g == 0 else float("inf"))
    return {
        "src": src, "trades": len(trades), "pf": pf, "wr": wr,
        "net_pnl": round(equity - START_EQUITY, 2),
        "n_buy": len(buys), "pf_buy": _pf(buys), "n_sell": len(sells), "pf_sell": _pf(sells),
    }
