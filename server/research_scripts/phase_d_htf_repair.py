#!/usr/bin/env python3
"""Phase D - HTF parity repair per i 4 candidati bloccati (BREAKOUT_ACC, LIQ_SWEEP,
MACD, FVG_CONT): usa strategy_profiles (native SL/TP) + htf_native_ema=True
(gate HTF reale portato 1:1 da NEXUS_EA_v2.mq5 riga ~634, vedi commento in
backtest.py). Nessuna nuova definizione inventata - solo la semantica gia'
esistente nel motore MQL5 reale, mai applicata dal lato Python in questa
sessione."""
import sys, os, json, time
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import backtest as bt

SYMBOL, BARS = "XAUUSD", 110000
BAR_RANGE = (0.6, 1.0)
RISK_PCT = 1.0

NATIVE_PROFILES = {
    "BREAKOUT_ACC": {"atr_sl": 1.0, "atr_tp": 4.5},
    "LIQ_SWEEP":    {"atr_sl": 1.5, "atr_tp": 3.0},
    "MACD":         {"atr_sl": 2.0, "atr_tp": 8.0},
    "FVG_CONT":     {"atr_sl": 1.5, "atr_tp": 6.0},
}
STRATEGY_TF = {
    "BREAKOUT_ACC": "1d",
    "LIQ_SWEEP": "1d",
    "MACD": "4h",
    "FVG_CONT": "4h",
}

ZERO_COST       = {"spread_price": 0.0,  "commission_r": 0.0, "slippage_price": 0.0}
BROKER_BASELINE = {"spread_price": 0.55, "commission_r": 0.0, "slippage_price": 0.10}
CONSERVATIVE    = {"spread_price": 0.70, "commission_r": 0.0, "slippage_price": 0.15}
STRESS          = {"spread_price": 1.30, "commission_r": 0.0, "slippage_price": 0.25}
PROFILES = {"ZERO_COST": ZERO_COST, "BROKER_BASELINE": BROKER_BASELINE,
            "CONSERVATIVE": CONSERVATIVE, "STRESS": STRESS}


def run_one(strat, tf, cost, htf_native_ema):
    prof = {strat: NATIVE_PROFILES[strat]}
    r = bt.run_backtest(symbol=SYMBOL, timeframe=tf, strategy=strat, strategies=[strat],
                         risk_pct=RISK_PCT, atr_sl=1.5, atr_tp=3.0,
                         bars=BARS, bar_range=BAR_RANGE,
                         strategy_profiles=prof, htf_native_ema=htf_native_ema,
                         spread_price=cost["spread_price"], commission_r=cost["commission_r"],
                         slippage_price=cost["slippage_price"])
    return {
        "n": r.get("trades"), "pf": r.get("profit_factor"), "gross_pf": r.get("gross_profit_factor"),
        "net": r.get("net_pnl"), "dd": r.get("max_dd_pct"), "exp_r": r.get("expectancy_r"),
    }


def main():
    t0 = time.time()
    out = {"pre_repair_generic_sltp_no_htf": {}, "post_repair_native_sltp_plus_htf": {}}
    for strat, tf in STRATEGY_TF.items():
        out["pre_repair_generic_sltp_no_htf"][strat] = {}
        out["post_repair_native_sltp_plus_htf"][strat] = {}
        for pname, cost in PROFILES.items():
            pre = run_one(strat, tf, cost, htf_native_ema=False)
            # pre-repair usa comunque strategy_profiles nativo (gia' fatto in
            # Phase Triage) - qui l'UNICA variabile aggiunta e' htf_native_ema
            post = run_one(strat, tf, cost, htf_native_ema=True)
            out["pre_repair_generic_sltp_no_htf"][strat][pname] = pre
            out["post_repair_native_sltp_plus_htf"][strat][pname] = post
            print(f"[{strat}/{tf}/{pname}] PRE(no-HTF) n={pre['n']} pf={pre['pf']} dd={pre['dd']}  "
                  f"POST(+HTF) n={post['n']} pf={post['pf']} dd={post['dd']}  ({time.time()-t0:.0f}s)",
                  flush=True)
    out_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..",
                            "results", "cost_calibration_67_rerun")
    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, "phase_d_htf_repair_results.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2, default=str)
    print(f"\nCompletato in {time.time()-t0:.0f}s")


if __name__ == "__main__":
    main()
