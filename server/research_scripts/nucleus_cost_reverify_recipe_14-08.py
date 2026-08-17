#!/usr/bin/env python3
"""
14/08 (2) - correzione del batch nucleus_cost_reverify_14-08.py: quello
usava SL/TP flat (1.5/3.0 ATR, no HTF) per tutte le strategie, ma la
"ricetta ufficiale" per-strategia (NXS_Profile_Get, NXS_StrategyProfiles.mqh)
e' spesso diversa (es. TURTLE_SOUP: SL1.0/TP4.5/HTF, non 1.5/3.0 flat - il
vault avverte esplicitamente che il flat la sottostima: 0.96 flat vs 1.15
con la ricetta). Qui si ripete lo stesso identico batch costi ma con i
parametri reali di ciascuna, per non ripetere l'errore metodologico gia'
trovato su CRT lato Grok (parametri flat, non la vera ricetta).

Include anche le 4 gia' disattivate oggi (CRT esclusa: la sua SL/TP e'
strutturale/wick, gia' testata a fondo separatamente) per verificare se la
decisione di disattivazione regge anche con la ricetta vera.
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import backtest as bt

SYMBOL, BARS = "XAUUSD", 110000
BAR_RANGE = (0.6, 1.0)  # OOS

# strategia -> (tf, slMult, tpMult, htf, beR) da NXS_Profile_Get / NXS_Profile_TF
NUCLEUS = [
    ("ADX_RSI",                 "1d", 1.0, 10.0, True,  1.5),
    ("BREAKOUT_ACC",            "1d", 1.0, 4.5,  True,  0.0),
    ("THREE_BAR_DELIVERY_BREAK","4h", 1.5, 3.0,  True,  0.0),
    ("EMA_PULLBACK",            "1h", 1.5, 4.0,  True,  0.0),
    ("FVG_CONT",                "4h", 1.5, 6.0,  True,  1.5),
    ("LIQ_SWEEP",               "1d", 1.5, 3.0,  True,  0.0),
    ("LONDON_BO",               "4h", 1.0, 4.5,  True,  0.0),
    ("MACD",                    "4h", 2.0, 8.0,  True,  1.0),
    ("AMD_CONT",                "30m",1.5, 3.0,  False, 0.0),
    ("LDN_REVERSAL",            "15m",1.5, 3.0,  False, 0.0),
    ("AMD_REVERSAL",            "15m",1.5, 3.0,  False, 0.0),
    ("SAR",                     "4h", 1.5, 4.0,  True,  0.0),
    # gia' disattivate oggi col batch flat - riverificate qui con ricetta vera
    ("TURTLE_SOUP",             "1h", 1.0, 4.5,  True,  0.0),
]

PRESETS = ["none", "retail_standard", "ecn"]


def run(strat, tf, slm, tpm, htf, ber, preset):
    c = bt.COST_PRESETS[preset]
    try:
        r = bt.run_backtest(symbol=SYMBOL, timeframe=tf, strategy=strat, strategies=[strat],
                             risk_pct=1.0, atr_sl=slm, atr_tp=tpm, htf_filter=htf,
                             breakeven_r=ber, bars=BARS, bar_range=BAR_RANGE,
                             spread_price=c["spread_price"], commission_r=c["commission_r"],
                             slippage_price=c["slippage_price"])
    except Exception as e:
        return {"error": str(e)[:150]}
    return {"pf": r.get("profit_factor"), "n": r.get("trades"), "dd": r.get("max_dd_pct")}


def main():
    print(f"{'strategy':<26}{'tf':<5}{'recipe':<20}"
          f"{'PF_none':<9}{'n':<6}{'DD_none':<9}"
          f"{'PF_retail':<11}{'n':<6}{'DD_retail':<10}"
          f"{'PF_ecn':<9}{'n':<6}{'DD_ecn':<8}", flush=True)
    rows = []
    for strat, tf, slm, tpm, htf, ber in NUCLEUS:
        results = {}
        for preset in PRESETS:
            results[preset] = run(strat, tf, slm, tpm, htf, ber, preset)
        rn, rr, re = results["none"], results["retail_standard"], results["ecn"]
        recipe = f"sl{slm}/tp{tpm}/htf{int(htf)}/be{ber}"
        if "error" in rn or "error" in rr or "error" in re:
            print(f"{strat:<26}{tf:<5}{recipe:<20}ERROR none={rn.get('error','')} "
                  f"retail={rr.get('error','')} ecn={re.get('error','')}", flush=True)
            rows.append((strat, tf, None, None, None))
            continue
        line = (f"{strat:<26}{tf:<5}{recipe:<20}"
                f"{str(rn['pf']):<9}{str(rn['n']):<6}{str(rn['dd']):<9}"
                f"{str(rr['pf']):<11}{str(rr['n']):<6}{str(rr['dd']):<10}"
                f"{str(re['pf']):<9}{str(re['n']):<6}{str(re['dd']):<8}")
        print(line, flush=True)
        rows.append((strat, tf, rn, rr, re))

    print("\n--- SURVIVAL (PF_retail >= 1.0, n >= 30) ---", flush=True)
    for strat, tf, rn, rr, re in rows:
        if rr and rr.get("pf") is not None and rr.get("n", 0) >= 30 and rr["pf"] >= 1.0:
            print(f"  SOPRAVVIVE: {strat} ({tf}) PF_retail={rr['pf']} n={rr['n']} DD={rr['dd']}", flush=True)


if __name__ == "__main__":
    main()
