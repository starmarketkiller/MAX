#!/usr/bin/env python3
"""
15/08 - le 5 "sopravvissute ai costi" (SAR/LONDON_BO/MACD/EMA_PULLBACK/
FVG_CONT) non reggono il walk-forward a 5 finestre (vedi vault "Riverifica
Walk-Forward 5 Finestre e Dipendenza da Regime"). Prossimo passo: cercare
nel catalogo completo (nucleo + escluse) su TF H4/D1 (i TF bassi sono gia'
esclusi, sistematicamente peggio - vedi stesso vault) se esiste QUALCHE
strategia con PF>=1 stabile su tutte/quasi tutte le 5 finestre, non solo
sull'ultima. Ricette da NXS_Profile_Get/NXS_Profile_TF (NXS_StrategyProfiles.mqh).
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import backtest as bt

SYMBOL, BARS = "XAUUSD", 110000
N_WINDOWS = 5

# strategia -> (tf, slMult, tpMult, htf, beR) da NXS_Profile_Get / NXS_Profile_TF
CANDIDATES = [
    ("BJORGUM",                 "4h", 1.5, 3.0, False, 0.0),
    ("DISP_REBAL",              "4h", 1.0, 4.5, False, 0.0),
    ("FVG_MIT",                 "4h", 1.5, 4.5, True,  0.0),
    ("ICHIMOKU",                "4h", 1.0, 4.5, True,  0.0),
    ("IFVG",                    "4h", 1.5, 4.5, True,  0.0),
    ("LIQ_VOID",                "4h", 1.0, 4.5, True,  0.0),
    ("BB_SQUEEZE",              "1d", 1.0, 4.5, False, 0.0),
    ("BOLLINGER",               "1d", 1.0, 2.0, False, 0.0),
    ("MALAYSIAN_SNR",           "1d", 2.0, 4.5, True,  0.0),
    ("OB_MIT",                  "1d", 1.5, 4.0, False, 0.0),
    ("ORDER_BLOCK",             "1d", 1.0, 3.0, True,  0.0),
    ("OTE_CONT",                "1d", 2.0, 4.5, True,  0.0),
    ("RANGE_FADE",              "1d", 1.0, 2.0, False, 0.0),
    ("SH_BMS_RTO",              "1d", 1.0, 4.5, False, 0.0),
    ("SMS_BMS_RTO",             "1d", 1.0, 4.5, False, 0.0),
    ("TSI",                     "1d", 2.0, 6.0, True,  1.0),
    ("WEEKLY_EXP",              "1d", 1.0, 4.5, True,  0.0),
]


def run(strat, tf, slm, tpm, htf, ber, br):
    c = bt.COST_PRESETS["retail_standard"]
    try:
        r = bt.run_backtest(symbol=SYMBOL, timeframe=tf, strategy=strat, strategies=[strat],
                             risk_pct=1.0, atr_sl=slm, atr_tp=tpm, htf_filter=htf,
                             breakeven_r=ber, bars=BARS, bar_range=br,
                             spread_price=c["spread_price"], commission_r=c["commission_r"],
                             slippage_price=c["slippage_price"])
    except Exception as e:
        return {"error": str(e)[:150]}
    return {"pf": r.get("profit_factor"), "n": r.get("trades"), "dd": r.get("max_dd_pct")}


def main():
    for strat, tf, slm, tpm, htf, ber in CANDIDATES:
        row = []
        err = None
        for w in range(N_WINDOWS):
            br = (w / N_WINDOWS, (w + 1) / N_WINDOWS)
            r = run(strat, tf, slm, tpm, htf, ber, br)
            if "error" in r:
                err = r["error"]
                break
            row.append(r)
        if err:
            print(f"{strat:14s} {tf:4s} ERROR: {err}", flush=True)
            continue
        pf_str = " | ".join(f"{r['pf']}/{r['n']}" for r in row)
        n_pos = sum(1 for r in row if r["pf"] is not None and r["pf"] >= 1.0)
        n_total = sum(r["n"] or 0 for r in row)
        flag = "  <-- CANDIDATO STABILE" if n_pos >= 4 and n_total >= 100 else ""
        print(f"{strat:14s} {tf:4s} [{n_pos}/{N_WINDOWS}] n_tot={n_total:5d}  {pf_str}{flag}", flush=True)


if __name__ == "__main__":
    main()
