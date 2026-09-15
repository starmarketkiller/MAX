#!/usr/bin/env python3
"""
NEXUS Cost Calibration Final + 67 Strategy Re-Evaluation.

Riesegue TUTTE le strategie con research_implementation=true nel registry
canonico (contracts/strategy-registry.json == bt.STRATEGIES.keys(), 67 totali
- non 37, correzione esplicita rispetto al task precedente) con TF e
parametri ORIGINALI invariati (nessuna ottimizzazione), sotto 4 cost profile
congelati: ZERO_COST (diagnostico), BROKER_BASELINE, CONSERVATIVE, STRESS.

Nessuna modifica a segnali/parametri/soglie. Vedi report
'NEXUS - 37 Strategy Cost-Calibrated Re-Evaluation.md' per fonti/metodologia.
"""
import sys
import os
import json
import time
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import backtest as bt

SYMBOL, BARS = "XAUUSD", 110000
BAR_RANGE = (0.6, 1.0)   # OOS 60-100%, stesso range usato in tutti gli audit precedenti
RISK_PCT, ATR_SL, ATR_TP = 1.0, 1.5, 3.0   # parametri originari (nucleus_cost_reverify/find_best_profiles)

# ============================================================
# Cost profiles CONGELATI - vedi report §1-4 per le fonti esatte
# (90 giorni / 24.1M tick reali GOLD dal broker connesso).
# ============================================================
ZERO_COST = {"spread_price": 0.0, "commission_r": 0.0, "slippage_price": 0.0}
BROKER_BASELINE = {"spread_price": 0.55, "commission_r": 0.0, "slippage_price": 0.10}   # mediana overall (5.5 pip) + ASSUMED_SLIPPAGE
CONSERVATIVE = {"spread_price": 0.70, "commission_r": 0.0, "slippage_price": 0.15}       # p99 overall (7.0 pip)
STRESS = {"spread_price": 1.30, "commission_r": 0.0, "slippage_price": 0.25}             # p99 sessione Asia (13.0 pip, peggiore normale, non il max assoluto 33 pip)
PROFILES = {"ZERO_COST": ZERO_COST, "BROKER_BASELINE": BROKER_BASELINE,
            "CONSERVATIVE": CONSERVATIVE, "STRESS": STRESS}

# ============================================================
# Mappa strategia -> TF originario. Fonti (in ordine di autorità):
#  [MQL5]  NXS_Profile_TF (NXS_StrategyProfiles.mqh) - TF nativo dichiarato nell'EA
#  [PY]    TF_MAP in find_best_profiles.py / nucleus_cost_reverify_14-08.py -
#          override Python quando il TF MQL5 non produce trade validi nel
#          motore research (gate di sessione su barre non-intraday, ecc.)
#  [FAM]   ASSUNTO per famiglia/naming (nessun profilo originario documentato
#          trovato) - dichiarato esplicitamente come assunzione, non un dato
#          originario verificato.
# ============================================================
STRATEGY_TF = {
    # --- [MQL5]/[PY] diretti ---
    "ADX_RSI": "1d", "BB_SQUEEZE": "1d", "BJORGUM": "4h", "BREAKOUT_ACC": "1d",
    "THREE_BAR_DELIVERY_BREAK": "4h", "DISP_REBAL": "4h", "EMA_PULLBACK": "4h",
    "FVG_CONT": "4h", "FVG_MIT": "4h", "FVG_MIT_WINDOW": "4h", "ICHIMOKU": "4h",
    "IFVG": "4h", "LIQ_SWEEP": "1d", "LIQ_VOID": "4h", "MACD": "4h",
    "AMD_CONT": "30m", "LDN_REVERSAL": "15m", "AMD_REVERSAL": "15m",
    "MALAYSIAN_SNR": "30m", "OB_MIT": "1d", "ORDER_BLOCK": "1d", "OTE_CONT": "1d",
    "RANGE_FADE": "1d", "RSI_DIV": "1h", "SAR": "4h", "SH_BMS_RTO": "1d",
    "SH_BMS_RTO_V2": "1h", "SMS_BMS_RTO": "1d", "STRUCT_REACT": "4h", "TSI": "1d",
    "TURTLE_SOUP": "1h", "Z_SCORE_BREAKOUT": "1h", "CRT": "30m",
    "BOLLINGER": "1d",
    # [PY] override esplicito - profilo MQL5 (H4/D1) non produce trade nel
    # motore research per via del gate di sessione, gia' documentato nel codice:
    "LONDON_BO": "1h", "WEEKLY_EXP": "4h",
    # --- [FAM] assunte per famiglia (nessun profilo originario trovato) ---
    "CISD_TRUE": "4h",                          # famiglia THREE_BAR_DELIVERY_BREAK/CISD
    "CRT_MINSTOP_FILTER": "30m",                # variante CRT
    "DARVAS_BOX": "1d",                         # sistema daily breakout per costruzione
    "DONCHIAN_TURTLE": "1d",                    # sistema daily per costruzione
    "EMA_CROSS_BENCHMARK": "1d",                # benchmark di riferimento, daily
    "FVG_CONT_V2": "4h",                        # variante FVG_CONT
    "IFVG_CHOCH_WINDOW": "4h",                  # variante IFVG
    "JUDAS_SWING": "15m",                       # concetto ICT a sessione, scala M15
    "MALAYSIAN_SNR_BREAKOUT": "30m",            # famiglia MALAYSIAN_SNR
    "MALAYSIAN_SNR_V2_RETEST": "30m",
    "MALAYSIAN_SNR_V2_RETEST_OUTRANGE": "30m",
    "MALAYSIAN_SNR_V2_STAGE1": "30m",
    "MALAYSIAN_SNR_V2_STAGE3": "30m",
    "NY_REVERSAL": "15m",                       # famiglia LDN_REVERSAL/AMD_REVERSAL
    "NY_REVERSAL_CHOCH_WINDOW": "15m",
    "ORDER_BLOCK_V2": "1d",                     # famiglia ORDER_BLOCK
    "OTE_CONT_V2": "1d",                        # famiglia OTE_CONT
    "PO3": "1d",                                # concetto ICT Power-of-Three, range daily
    "SAR_ADX20": "4h", "SAR_FLIP": "4h",        # famiglia SAR
    "SCALP_BB_FADE": "15m", "SCALP_EMA": "15m",
    "SCALP_RANGE_BRK": "15m", "SCALP_RSI_SNAP": "15m",   # nessun profilo MQL5 dichiarato (solo motore Python)
    "SILVER_BULLET": "15m", "SILVER_BULLET_V2": "15m",   # concetto ICT a finestra oraria, scala M15
    "SMS_BMS_RTO_CHOCH_WINDOW": "1d",           # famiglia SMS_BMS_RTO
    "TSI_EXTREME": "1d",                        # famiglia TSI
    "TURTLE_SOUP_CHOCH": "1h", "TURTLE_SOUP_CHOCH_DBLBODY": "1h", "TURTLE_SOUP_CHOCH_NEAR": "1h",
}

ALL_STRATEGIES = sorted(bt.STRATEGIES.keys())
assert set(ALL_STRATEGIES) == set(STRATEGY_TF.keys()), (
    f"Mappa TF incompleta o disallineata: mancano {set(ALL_STRATEGIES)-set(STRATEGY_TF.keys())}, "
    f"extra {set(STRATEGY_TF.keys())-set(ALL_STRATEGIES)}")


def run_one(strat, tf, cost):
    try:
        r = bt.run_backtest(symbol=SYMBOL, timeframe=tf, strategy=strat, strategies=[strat],
                             risk_pct=RISK_PCT, atr_sl=ATR_SL, atr_tp=ATR_TP,
                             bars=BARS, bar_range=BAR_RANGE,
                             spread_price=cost["spread_price"], commission_r=cost["commission_r"],
                             slippage_price=cost["slippage_price"])
    except Exception as e:
        return {"error": str(e)[:200]}
    return {
        "n": r.get("trades"), "pf": r.get("profit_factor"), "gross_pf": r.get("gross_profit_factor"),
        "net": r.get("net_pnl"), "gross": r.get("gross_pnl"), "total_cost": r.get("total_cost"),
        "expectancy_r": r.get("expectancy_r"), "dd": r.get("max_dd_pct"),
        "spread_cost": r.get("total_spread_cost"), "slippage_cost": r.get("total_slippage_cost"),
        "commission_cost": r.get("total_commission_cost"),
    }


def main():
    t0 = time.time()
    results = {}
    # raggruppa per TF per massimizzare il riuso della cache di _fetch_real (stesso simbolo/TF)
    by_tf = {}
    for strat in ALL_STRATEGIES:
        by_tf.setdefault(STRATEGY_TF[strat], []).append(strat)

    n_done = 0
    for tf, strats in sorted(by_tf.items()):
        for strat in strats:
            results[strat] = {"tf": tf, "profiles": {}}
            for pname, cost in PROFILES.items():
                r = run_one(strat, tf, cost)
                results[strat]["profiles"][pname] = r
            n_done += 1
            b = results[strat]["profiles"]["BROKER_BASELINE"]
            z = results[strat]["profiles"]["ZERO_COST"]
            print(f"[{n_done}/{len(ALL_STRATEGIES)}] {strat:<34}{tf:<5} "
                  f"ZERO n={z.get('n')} PF={z.get('pf')}  |  "
                  f"BASE n={b.get('n')} PF={b.get('pf')} net={b.get('net')}  "
                  f"({time.time()-t0:.0f}s totali)", flush=True)

    out_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..",
                            "results", "cost_calibration_67_rerun")
    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, "rerun_results.json"), "w", encoding="utf-8") as f:
        json.dump({"profiles_definition": PROFILES, "strategy_tf": STRATEGY_TF, "results": results},
                   f, indent=2, default=str)
    print(f"\nCompletato in {time.time()-t0:.0f}s. Output: {out_dir}")
    return results


if __name__ == "__main__":
    main()
