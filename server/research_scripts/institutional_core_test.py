#!/usr/bin/env python3
"""
08/08 - v2: universo allargato a 9 strategie + score reali per-strategia
(letti da NXS_Strategies.mqh/NXS_Strategies_SMC.mqh/NXS_Strategies_Institutional.mqh,
non piu' uniformi a 70) per il port Python del Modello Istituzionale
(NXS_InstitutionalCore.mqh, v2.1.0).

Universo:
  - le 5 gia' validate via direction_lock=BUY (SCALP_EMA, BREAKOUT_ACC,
    LIQ_VOID, SAR, SCALP_RANGE_BRK): contribuiscono SOLO BUY (coerente con
    come sono state validate oggi - forzare anche il SELL rimetterebbe in
    gioco il lato che i test precedenti hanno scartato).
  - le 4 nuove (TSI, SH_BMS_RTO, FVG_CONT, LIQ_SWEEP), gia' validate
    BILATERALI via D_HTF (edge_decomposition.py, MANTIENI su entrambi i
    lati): contribuiscono in ENTRAMBE le direzioni, fedele a come
    NXS_Institutional_Decide() sceglie dir = (buySum>=sellSum)?+1:-1 -
    prima non lo replicavo (avevo hardcoded BUY-only su tutto il gruppo).

Score reali (letti riga per riga dai file MQL5, s.score= alla creazione del
segnale):
  SAR=60 (NXS_Strategies.mqh:259/261), TSI=66 (:331/333),
  BREAKOUT_ACC=68 (:445/447 circa), LIQ_SWEEP=72 (:388/390),
  FVG_CONT=70 (:416/418), LIQ_VOID=73.0 (NXS_Strategies_Institutional.mqh),
  SH_BMS_RTO=74.0 (NXS_Strategies_SMC.mqh, NXS_SHBMS_UpdateSide).
  SCALP_EMA/SCALP_RANGE_BRK: NESSUNA fonte reale - sono RESEARCH_ONLY nel
  registro (live_implementation=False, mai esistite in MQL5) - restano al
  proxy uniforme 70 dichiarato nel giro precedente, non un dato vero.

Rimane semplificato (vedi v1 per la lista completa): tier su 3/6 componenti
(structTrend/htfBias/sweepDir), niente allargamento SL strutturale.
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
    "SCALP_EMA": 70.0, "SCALP_RANGE_BRK": 70.0,   # nessuna fonte MQL5 reale (RESEARCH_ONLY)
}

INST_MIN_CONVICTION = 60.0
INST_MIN_CONTRIBUTORS = 1
INST_BASE_SL = 2.0
INST_BASE_TP = 4.0
TIER_MULT = {0: 1.0, 1: 2.0, 2: 3.5}

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


def conviction(contribs):
    fam_cnt = {}
    buy_adj = sell_adj = 0.0
    buy_n = sell_n = 0
    for name, d, score in contribs:
        fam = _family(name)
        w = 1.0 / (fam_cnt.get(fam, 0) + 1)
        fam_cnt[fam] = fam_cnt.get(fam, 0) + 1
        if d == 1:
            buy_adj += score * w
            buy_n += 1
        else:
            sell_adj += score * w
            sell_n += 1
    return buy_adj, sell_adj, buy_n, sell_n


def main():
    print("Universo:", STRATS)
    print("  BUY-only:", sorted(BUY_ONLY))
    print("  Bidirezionali:", sorted(BIDIRECTIONAL))
    print("  Famiglie:", {s: _family(s) for s in STRATS})
    print()

    candles, src = bt._fetch_real(SYMBOL, TF)
    ind = bt._prep(candles)
    htf_trend, htf_up, htf_down = bt._external_choch_series(candles, factor=HTF_FACTOR, wing=3)
    struct_trend = ind["choch_int"][0]
    atr = ind["atr"]
    adx = ind["adx"]

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
                trades.append({
                    "side": "BUY" if position["dir"] == 1 else "SELL",
                    "pnl": pnl, "reason": reason, "group": position["group"],
                    "contributors": position["contributors"], "tier": position["tier"],
                    "openTime": candles[position["open_i"]]["time"], "closeTime": candles[i]["time"],
                })
                position = None
            continue

        a = atr[i]
        adx_i = adx[i]
        if not a or adx_i is None or adx_i < 20.0:
            continue
        contribs = []
        for s in STRATS:
            v = bt.STRATEGIES[s](candles, ind, i)
            if v == 0:
                continue
            if s in BUY_ONLY and v == -1:
                continue
            contribs.append((s, v, SCORES[s]))
        if not contribs:
            continue
        buy_adj, sell_adj, buy_n, sell_n = conviction(contribs)
        if buy_adj == 0 and sell_adj == 0:
            continue
        dir_ = 1 if buy_adj >= sell_adj else -1
        net = abs(buy_adj - sell_adj)
        contributors = buy_n if dir_ == 1 else sell_n
        if net < INST_MIN_CONVICTION or contributors < INST_MIN_CONTRIBUTORS:
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

        entry = px
        sl_dist = a * INST_BASE_SL * mult
        tp_dist = a * INST_BASE_TP * mult
        sl = entry - sl_dist if dir_ == 1 else entry + sl_dist
        tp = entry + tp_dist if dir_ == 1 else entry - tp_dist
        risk_money = equity * (RISK_PCT / 100.0)
        group = "+".join(f"{x[0]}({'B' if x[1]==1 else 'S'})" for x in contribs if x[1] == dir_)
        position = {
            "dir": dir_, "entry": entry, "sl": sl, "tp": tp, "open_i": i,
            "risk_dist": sl_dist, "risk_money": risk_money,
            "group": group, "contributors": contributors, "tier": tier,
        }

    gross_win = sum(t["pnl"] for t in trades if t["pnl"] > 0)
    gross_loss = -sum(t["pnl"] for t in trades if t["pnl"] < 0)
    pf = round(gross_win / gross_loss, 2) if gross_loss > 0 else None
    wr = round(100 * sum(1 for t in trades if t["pnl"] >= 0) / len(trades), 1) if trades else None
    net_pnl = round(equity - START_EQUITY, 2)

    buys = [t for t in trades if t["side"] == "BUY"]
    sells = [t for t in trades if t["side"] == "SELL"]
    def _pf(lst):
        g = sum(t["pnl"] for t in lst if t["pnl"] > 0); l = -sum(t["pnl"] for t in lst if t["pnl"] < 0)
        return round(g / l, 2) if l > 0 else None

    print(f"src={src}  bars={n}")
    print(f"MODELLO ISTITUZIONALE (9 strategie, score reali, tier 0-2, adx>=20):")
    print(f"  trades={len(trades)}  PF={pf}  WR={wr}%  net_pnl={net_pnl}  equity_finale={round(equity,2)}")
    print(f"  BUY:  n={len(buys)}  PF={_pf(buys)}")
    print(f"  SELL: n={len(sells)}  PF={_pf(sells)}")
    print("  distribuzione contributors per trade:", Counter(t["contributors"] for t in trades))
    print("  distribuzione tier per trade:", Counter(t["tier"] for t in trades))
    print("  distribuzione gruppo (quali strategie hanno co-firmato), top 15:")
    for g, c in Counter(t["group"] for t in trades).most_common(15):
        print(f"    {g:<60} x{c}")
    print("  reason:", Counter(t["reason"] for t in trades))


if __name__ == "__main__":
    main()
