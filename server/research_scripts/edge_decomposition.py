#!/usr/bin/env python3
"""
06/08 - screening Python complementare al brief "Decomposizione Edge
Strategie NEXUS" (MT5/Strategy Tester, lavoro desktop separato). Copre
TUTTE le strategie con implementazione Python (non solo le 13 del brief),
sulle configurazioni che questo motore puo' rappresentare:

  A. GREZZO      - solo condizione base, SL=1.5xATR TP=3.0xATR, nessun filtro
  B. +ADX        - A + adx_min=20 (ind["adx"], stesso ADX(14) del grid)
  C. +SESSIONE   - B + session_filter={LONDON,NY,OVERLAP} (solo se il TF e'
                   intraday - su 1d la sessione non esiste, vedi il bug
                   LONDON_BO/WEEKLY_EXP gia' trovato oggi: se il TF e'
                   1d/1wk lo step e' identico a B, non si applica)
  D. +HTF        - C + htf_filter=True (trend SMA50, l'unico "contesto HTF"
                   che questo motore ha - non un vero controllo candela H1)
  F. COMPLETO    - profilo SL/TP/BE/trailing migliore gia' trovato oggi
                   (find_best_profiles.py/optimize_max_per_dir.py) se
                   disponibile, altrimenti uguale ad A (nessun profilo
                   noto ancora)

NON copre: filtro Volume (step E del brief - questo motore non ha dati di
volume tick, OHLC puro) e costi/leva/modello "every tick" reali di un
broker - quello resta lavoro MT5 Strategy Tester, non sostituibile qui.
Ogni config riporta anche PF/WR/trade separati per lato (BUY/SELL) - il
controllo piu' utile trovato oggi contro l'illusione di edge che e' solo
il bull market dell'oro.

Esegui dalla root del repo: python3 server/research_scripts/edge_decomposition.py
"""
import sys
sys.path.insert(0, "server")
import backtest as bt

COSTS = bt.COST_PRESETS["retail_standard"]

# TF per strategia = quello dove ha piu' segnali grezzi (debug_all_strategies.py,
# 06/08) - stesso criterio, non un valore arbitrario.
TF_MAP = {
    "ADX_RSI": "1h", "AMD_CONT": "4h", "AMD_REVERSAL": "4h", "BB_SQUEEZE": "4h",
    "BJORGUM": "4h", "BOLLINGER": "1d", "BREAKOUT_ACC": "1d", "DISP_REBAL": "4h",
    "EMA_PULLBACK": "4h", "FVG_CONT": "1d", "FVG_MIT": "1d", "ICHIMOKU": "1h",
    "IFVG": "1d", "JUDAS_SWING": "4h", "LDN_REVERSAL": "4h", "LIQ_SWEEP": "1d",
    "LIQ_VOID": "1d", "LONDON_BO": "4h", "MACD": "1h", "MALAYSIAN_SNR": "4h",
    "MALAYSIAN_SNR_BREAKOUT": "1h", "NY_REVERSAL": "1h", "OB_MIT": "1d",
    "ORDER_BLOCK": "1d", "OTE_CONT": "1h", "PO3": "4h", "RANGE_FADE": "1d",
    "RSI_DIV": "1h", "SAR": "1d", "SCALP_BB_FADE": "1h", "SCALP_EMA": "1d",
    "SCALP_RANGE_BRK": "1d", "SCALP_RSI_SNAP": "4h", "SH_BMS_RTO": "1d",
    "SILVER_BULLET": "4h", "SMS_BMS_RTO": "4h", "STRUCT_REACT": "1h",
    "THREE_BAR_DELIVERY_BREAK": "1d", "TSI": "1d", "TURTLE_SOUP": "1d",
    "WEEKLY_EXP": "1h",
}

# Profili migliori gia' trovati oggi (find_best_profiles.py/optimize_max_per_dir.py/
# session_strategies_test.py) - usati per Config F. Assente = F identica ad A.
BEST_PROFILES = {
    "OTE_CONT":                 dict(atr_sl=1.0, atr_tp=4.0, breakeven_r=1.0, trailing_atr=2.5),
    "BREAKOUT_ACC":             dict(atr_sl=2.0, atr_tp=4.0, breakeven_r=1.5, trailing_atr=2.5),
    "SH_BMS_RTO":               dict(atr_sl=1.0, atr_tp=2.0, breakeven_r=1.0, trailing_atr=2.5),
    "TSI":                      dict(atr_sl=1.0, atr_tp=4.0, breakeven_r=0.0, trailing_atr=2.5),
    "ADX_RSI":                  dict(atr_sl=2.0, atr_tp=4.0, breakeven_r=0.0, trailing_atr=2.5),
    "LIQ_SWEEP":                dict(atr_sl=1.5, atr_tp=2.0, breakeven_r=0.0, trailing_atr=0.0),
    "FVG_MIT":                  dict(atr_sl=1.0, atr_tp=2.0, breakeven_r=0.0, trailing_atr=0.0),
    "THREE_BAR_DELIVERY_BREAK": dict(atr_sl=1.5, atr_tp=3.0, breakeven_r=0.0, trailing_atr=0.0),
    "EMA_PULLBACK":             dict(atr_sl=1.0, atr_tp=4.0, breakeven_r=0.0, trailing_atr=0.0),
    "MACD":                     dict(atr_sl=1.0, atr_tp=4.0, breakeven_r=0.0, trailing_atr=0.0),
    "SAR":                      dict(atr_sl=2.0, atr_tp=4.0, breakeven_r=0.0, trailing_atr=0.0),
    "FVG_CONT":                 dict(atr_sl=1.0, atr_tp=4.0, breakeven_r=0.0, trailing_atr=0.0),
    "LIQ_VOID":                 dict(atr_sl=1.5, atr_tp=3.0, breakeven_r=0.0, trailing_atr=0.0),
    "LONDON_BO":                dict(atr_sl=2.0, atr_tp=4.0, breakeven_r=0.0, trailing_atr=0.0),
}

SESSION_INTRADAY = {"1h", "4h", "15m", "30m", "5m"}


def _side_split(trade_list):
    buys = [t for t in trade_list if t["side"] == "BUY"]
    sells = [t for t in trade_list if t["side"] == "SELL"]
    def pf(lst):
        g = sum(t["pnl"] for t in lst if t["pnl"] > 0)
        l = -sum(t["pnl"] for t in lst if t["pnl"] < 0)
        return round(g / l, 2) if l > 0 else (None if g == 0 else float("inf"))
    def wr(lst):
        return round(100 * sum(1 for t in lst if t["pnl"] >= 0) / len(lst), 1) if lst else None
    return len(buys), pf(buys), wr(buys), len(sells), pf(sells), wr(sells)


def run_config(strat, tf, **kw):
    r = bt.run_backtest(symbol="XAUUSD", strategy=strat, timeframe=tf, **kw, **COSTS)
    nb, pfb, wrb, ns, pfs, wrs = _side_split(r["trade_list"])
    return {
        "trades": r["trades"], "pf": r["profit_factor"], "wr": r["win_rate"],
        "dd": r["max_dd_pct"], "avg_trade": (r["net_pnl"] / r["trades"]) if r["trades"] else None,
        "n_buy": nb, "pf_buy": pfb, "wr_buy": wrb,
        "n_sell": ns, "pf_sell": pfs, "wr_sell": wrs,
    }


def main():
    rows = []
    strategies = sorted(bt.STRATEGIES)
    for idx, strat in enumerate(strategies, 1):
        tf = TF_MAP.get(strat, "1d")
        try:
            a = run_config(strat, tf, atr_sl=1.5, atr_tp=3.0)
            b = run_config(strat, tf, atr_sl=1.5, atr_tp=3.0, adx_min=20)
            if tf in SESSION_INTRADAY:
                c = run_config(strat, tf, atr_sl=1.5, atr_tp=3.0, adx_min=20,
                               session_filter={"LONDON", "NY", "OVERLAP"})
            else:
                c = dict(b)  # sessione non applicabile su TF non-intraday - step saltato
            d = run_config(strat, tf, atr_sl=1.5, atr_tp=3.0, adx_min=20,
                           session_filter={"LONDON", "NY", "OVERLAP"} if tf in SESSION_INTRADAY else None,
                           htf_filter=True)
            f_kw = BEST_PROFILES.get(strat)
            f = run_config(strat, tf, **f_kw) if f_kw else dict(a)
            for cfg_name, cfg in (("A_GREZZO", a), ("B_ADX", b), ("C_SESSIONE", c),
                                  ("D_HTF", d), ("F_COMPLETO", f)):
                rows.append({"strat": strat, "tf": tf, "config": cfg_name, **cfg})
            print(f"[{idx}/{len(strategies)}] {strat} fatto", flush=True)
        except Exception as e:
            print(f"[{idx}/{len(strategies)}] {strat} ERRORE: {str(e)[:150]}", flush=True)

    print("\n" + "=" * 150)
    print(f"{'Strategia':<26}{'TF':>4}{'Config':<12}{'Trade':>6}{'PF':>7}{'WR%':>6}{'MaxDD%':>8}"
          f"{'AvgTr':>8}  {'BUY(n/PF/WR)':<20}{'SELL(n/PF/WR)':<20}")
    for r in rows:
        pf_s = f"{r['pf']:.2f}" if r["pf"] is not None else "n/a"
        avg_s = f"{r['avg_trade']:.1f}" if r["avg_trade"] is not None else "n/a"
        buy_s = f"{r['n_buy']}/{r['pf_buy']}/{r['wr_buy']}"
        sell_s = f"{r['n_sell']}/{r['pf_sell']}/{r['wr_sell']}"
        print(f"{r['strat']:<26}{r['tf']:>4}{r['config']:<12}{r['trades']:>6}{pf_s:>7}"
              f"{r['wr']:>6.1f}{r['dd']:>8.2f}{avg_s:>8}  {buy_s:<20}{sell_s:<20}")
    print("=" * 150)


if __name__ == "__main__":
    main()
