#!/usr/bin/env python3
"""
14/08 - riverifica costi su tutto il nucleo demo (16 strategie, esclusa
CRT gia' chiusa oggi) con lo stesso standard che ha chiuso CRT: costi
retail/ecn realistici applicati in R (spread_price/commission_r/
slippage_price), storico Dukascopy ampio (bars=110000, capped
internamente ai dati reali disponibili), OOS 60-100%, TF di profilo
reale (NXS_StrategyProfiles.mqh -> NXS_Profile_TF).

Uso:
python3 server/research_scripts/nucleus_cost_reverify_14-08.py
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import backtest as bt

SYMBOL, BARS = "XAUUSD", 110000
BAR_RANGE = (0.6, 1.0)  # OOS

# strategia -> TF di profilo (NXS_Profile_TF, NXS_StrategyProfiles.mqh)
NUCLEUS = [
    ("ADX_RSI", "1d"),
    ("BREAKOUT_ACC", "1d"),
    ("THREE_BAR_DELIVERY_BREAK", "4h"),
    ("EMA_PULLBACK", "1h"),
    ("FVG_CONT", "4h"),
    ("FVG_MIT_WINDOW", "4h"),
    ("LIQ_SWEEP", "1d"),
    ("LONDON_BO", "4h"),
    ("MACD", "4h"),
    ("AMD_CONT", "30m"),
    ("LDN_REVERSAL", "15m"),
    ("AMD_REVERSAL", "15m"),
    ("SAR", "4h"),
    ("SH_BMS_RTO_V2", "1h"),
    ("TSI", "1d"),
    ("TURTLE_SOUP", "1h"),
]

PRESETS = ["none", "retail_standard", "ecn"]


def run(strat, tf, preset):
    c = bt.COST_PRESETS[preset]
    try:
        r = bt.run_backtest(symbol=SYMBOL, timeframe=tf, strategy=strat, strategies=[strat],
                             risk_pct=1.0, atr_sl=1.5, atr_tp=3.0, bars=BARS, bar_range=BAR_RANGE,
                             spread_price=c["spread_price"], commission_r=c["commission_r"],
                             slippage_price=c["slippage_price"])
    except Exception as e:
        return {"error": str(e)[:150]}
    return {"pf": r.get("profit_factor"), "n": r.get("trades"), "dd": r.get("max_dd_pct")}


def main():
    print(f"{'strategy':<26}{'tf':<6}"
          f"{'PF_none':<10}{'n':<7}{'DD_none':<9}"
          f"{'PF_retail':<11}{'n':<7}{'DD_retail':<10}"
          f"{'PF_ecn':<9}{'n':<7}{'DD_ecn':<8}", flush=True)
    rows = []
    for strat, tf in NUCLEUS:
        results = {}
        for preset in PRESETS:
            results[preset] = run(strat, tf, preset)
        rn, rr, re = results["none"], results["retail_standard"], results["ecn"]
        if "error" in rn or "error" in rr or "error" in re:
            print(f"{strat:<26}{tf:<6}ERROR none={rn.get('error','')} "
                  f"retail={rr.get('error','')} ecn={re.get('error','')}", flush=True)
            rows.append((strat, tf, None, None, None))
            continue
        line = (f"{strat:<26}{tf:<6}"
                f"{str(rn['pf']):<10}{str(rn['n']):<7}{str(rn['dd']):<9}"
                f"{str(rr['pf']):<11}{str(rr['n']):<7}{str(rr['dd']):<10}"
                f"{str(re['pf']):<9}{str(re['n']):<7}{str(re['dd']):<8}")
        print(line, flush=True)
        rows.append((strat, tf, rn, rr, re))

    print("\n--- SURVIVAL (PF_retail >= 1.0, n >= 30) ---", flush=True)
    for strat, tf, rn, rr, re in rows:
        if rr and rr.get("pf") is not None and rr.get("n", 0) >= 30 and rr["pf"] >= 1.0:
            print(f"  SOPRAVVIVE: {strat} ({tf}) PF_retail={rr['pf']} n={rr['n']} DD={rr['dd']}", flush=True)


if __name__ == "__main__":
    main()
