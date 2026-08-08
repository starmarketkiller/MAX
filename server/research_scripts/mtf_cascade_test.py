#!/usr/bin/env python3
"""
08/08 - test del bias Multi-Timeframe VERO (htf_factor/htf_fresh_bars,
_external_choch_series su un TF davvero ricampionato) su TUTTE le
strategie, non solo le 5 gia' validate Long-Only. Confronto a 3 punti:

  BASE    - adx_min=20, nessun bias HTF (come B_ADX dello screening precedente)
  HTF     - + htf_filter=True, htf_factor=X (trend REALE sul TF superiore,
            non lo SMA(50) sullo stesso TF che htf_filter usava da solo)
  HTF+FRESH - + htf_fresh_bars=10 (il segnale LTF deve cadere entro 10 barre
            HTF da un CHoCH HTF nella stessa direzione - la finestra
            "bias fresco apre la ricerca", non solo "il trend e' quello")

htf_factor scelto per rappresentare un vero salto di timeframe (non un
multiplo arbitrario):
  entry 1h  -> factor=4  (bias ~4h)
  entry 4h  -> factor=6  (bias ~1d)
  entry 1d  -> factor=5  (bias ~1 settimana)

BUY/SELL sempre riportato separato (il controllo che ha gia' smascherato
piu' "edge" fasulli in questa sessione).
"""
import sys
sys.path.insert(0, "server")
import backtest as bt

COSTS = bt.COST_PRESETS["retail_standard"]

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
    # varianti _v2 (08/08) - incluse, stesso trattamento delle altre
    "SH_BMS_RTO_V2": "1d", "SILVER_BULLET_V2": "4h", "OTE_CONT_V2": "1h",
    "ORDER_BLOCK_V2": "1d", "FVG_CONT_V2": "1d",
}
HTF_FACTOR = {"1h": 4, "4h": 6, "1d": 5}
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
        "dd": r["max_dd_pct"], "n_buy": nb, "pf_buy": pfb, "wr_buy": wrb,
        "n_sell": ns, "pf_sell": pfs, "wr_sell": wrs,
    }


def main():
    rows = []
    strategies = sorted(TF_MAP)
    for idx, strat in enumerate(strategies, 1):
        tf = TF_MAP[strat]
        factor = HTF_FACTOR[tf]
        try:
            base = run_config(strat, tf, atr_sl=1.5, atr_tp=3.0, adx_min=20)
            htf = run_config(strat, tf, atr_sl=1.5, atr_tp=3.0, adx_min=20,
                              htf_filter=True, htf_factor=factor)
            fresh = run_config(strat, tf, atr_sl=1.5, atr_tp=3.0, adx_min=20,
                                htf_filter=True, htf_factor=factor, htf_fresh_bars=10)
            for cfg_name, cfg in (("BASE", base), ("HTF", htf), ("HTF+FRESH", fresh)):
                rows.append({"strat": strat, "tf": tf, "factor": factor, "config": cfg_name, **cfg})
            print(f"[{idx}/{len(strategies)}] {strat} fatto", flush=True)
        except Exception as e:
            print(f"[{idx}/{len(strategies)}] {strat} ERRORE: {str(e)[:150]}", flush=True)

    print("\n" + "=" * 150)
    print(f"{'Strategia':<26}{'TF':>3}{'Config':<11}{'Trade':>6}{'PF':>7}{'WR%':>6}{'MaxDD%':>8}"
          f"  {'BUY(n/PF/WR)':<20}{'SELL(n/PF/WR)':<20}")
    for r in rows:
        pf_s = f"{r['pf']:.2f}" if r["pf"] is not None else "n/a"
        buy_s = f"{r['n_buy']}/{r['pf_buy']}/{r['wr_buy']}"
        sell_s = f"{r['n_sell']}/{r['pf_sell']}/{r['wr_sell']}"
        wr = r['wr'] if r['wr'] is not None else 0.0
        dd = r['dd'] if r['dd'] is not None else 0.0
        print(f"{r['strat']:<26}{r['tf']:>3}{r['config']:<11}{r['trades']:>6}{pf_s:>7}"
              f"{wr:>6.1f}{dd:>8.2f}  {buy_s:<20}{sell_s:<20}")
    print("=" * 150)


if __name__ == "__main__":
    main()
