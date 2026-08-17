#!/usr/bin/env python3
"""
16/08 - audit di coerenza (direzione/esito) esteso a TUTTE le 67 strategie
registrate, non solo le 12 del nucleo attivo (gia' verificate separatamente
con scenari sintetici + questo stesso controllo). Per ogni strategia: gira
run_backtest su dati reali, poi controlla che ogni trade con reason=SL/TP
abbia il prezzo di chiusura dal lato coerente con side/risultato (BUY che
vince deve avere chiuso piu' in alto, SELL che vince piu' in basso, ecc.).
Non sostituisce una vera fedelta' MQL5 (quella e' in altri documenti) - e'
un controllo di sanita' sul motore e sulla logica di uscita.
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import backtest as bt

ALREADY_AUDITED = {
    "SAR", "MACD", "LONDON_BO", "EMA_PULLBACK", "FVG_CONT",
    "BREAKOUT_ACC", "ADX_RSI", "TSI", "LIQ_SWEEP", "AMD_CONT",
    "AMD_REVERSAL", "LDN_REVERSAL",
}

# TF di profilo dove esiste (NXS_Profile_TF), altrimenti default ragionevole
TF_MAP = {
    "BB_SQUEEZE": "1d", "BJORGUM": "4h", "BOLLINGER": "1d",
    "DISP_REBAL": "4h", "FVG_MIT": "4h", "FVG_MIT_WINDOW": "4h",
    "ICHIMOKU": "4h", "IFVG": "4h", "LIQ_VOID": "4h",
    "MALAYSIAN_SNR": "1d", "OB_MIT": "1d", "ORDER_BLOCK": "1d",
    "OTE_CONT": "1d", "RANGE_FADE": "1d", "RSI_DIV": "1h",
    "SH_BMS_RTO": "1d", "SH_BMS_RTO_V2": "1h", "SMS_BMS_RTO": "1d",
    "STRUCT_REACT": "1h", "TURTLE_SOUP": "1h", "WEEKLY_EXP": "1d",
    "CRT": "30m", "CRT_MINSTOP_FILTER": "30m",
    "TURTLE_SOUP_CHOCH": "1h", "TURTLE_SOUP_CHOCH_NEAR": "1h",
    "TURTLE_SOUP_CHOCH_DBLBODY": "1h",
    "JUDAS_SWING": "15m", "SILVER_BULLET": "15m", "SILVER_BULLET_V2": "15m",
    "NY_REVERSAL": "15m", "NY_REVERSAL_CHOCH_WINDOW": "15m", "PO3": "15m",
    "SCALP_BB_FADE": "15m", "SCALP_EMA": "15m", "SCALP_RANGE_BRK": "15m",
    "SCALP_RSI_SNAP": "15m",
    "SAR_ADX20": "4h", "SAR_FLIP": "4h",
    "IFVG_CHOCH_WINDOW": "4h", "FVG_CONT_V2": "4h",
    "MALAYSIAN_SNR_BREAKOUT": "1d", "MALAYSIAN_SNR_V2_RETEST": "30m",
    "MALAYSIAN_SNR_V2_RETEST_OUTRANGE": "30m",
    "MALAYSIAN_SNR_V2_STAGE1": "30m", "MALAYSIAN_SNR_V2_STAGE3": "30m",
    "ORDER_BLOCK_V2": "1d", "OTE_CONT_V2": "1d",
    "SMS_BMS_RTO_CHOCH_WINDOW": "1d", "CISD_TRUE": "4h",
    "TSI_EXTREME": "1d", "DARVAS_BOX": "1d", "DONCHIAN_TURTLE": "1d",
    "EMA_CROSS_BENCHMARK": "4h", "Z_SCORE_BREAKOUT": "1d",
}


def audit_one(name):
    tf = TF_MAP.get(name, "1d")
    try:
        r = bt.run_backtest(symbol="XAUUSD", timeframe=tf, strategy=name, strategies=[name],
                             risk_pct=1.0, atr_sl=1.5, atr_tp=3.0, bars=20000)
    except Exception as e:
        return {"status": "ERRORE", "detail": str(e)[:150], "tf": tf}
    tl = r.get("trade_list", [])
    n_trades = r.get("trades", 0)
    errors = []
    for t in tl:
        side, o, c, reason = t.get("side"), t.get("openPrice"), t.get("closePrice"), t.get("reason")
        if o is None or c is None:
            continue
        if reason == "SL":
            if side == "SELL" and not (c > o):
                errors.append(t)
            if side == "BUY" and not (c < o):
                errors.append(t)
        elif reason == "TP":
            if side == "SELL" and not (c < o):
                errors.append(t)
            if side == "BUY" and not (c > o):
                errors.append(t)
    return {"status": "OK", "tf": tf, "n_trades": n_trades, "n_checked": len(tl),
            "n_errors": len(errors), "sample_errors": errors[:2]}


def main():
    all_keys = sorted(bt.STRATEGIES.keys())
    todo = [k for k in all_keys if k not in ALREADY_AUDITED]
    print(f"Da controllare: {len(todo)} strategie (escluse le 12 gia' auditate)", flush=True)
    n_ok, n_zero_trades, n_errors, n_crash = 0, 0, 0, 0
    for name in todo:
        res = audit_one(name)
        if res["status"] == "ERRORE":
            n_crash += 1
            print(f"  {name:35s} tf={res['tf']:4s} ERRORE: {res['detail']}", flush=True)
            continue
        if res["n_trades"] == 0:
            n_zero_trades += 1
            print(f"  {name:35s} tf={res['tf']:4s} n_trades=0 (nessun segnale nel campione)", flush=True)
            continue
        if res["n_errors"] > 0:
            n_errors += 1
            print(f"  {name:35s} tf={res['tf']:4s} n_trades={res['n_trades']:5d} "
                  f"n_checked={res['n_checked']:4d}  INCOERENZE={res['n_errors']}  <-- DA GUARDARE", flush=True)
            for e in res["sample_errors"]:
                print(f"      esempio: {e}", flush=True)
        else:
            n_ok += 1
            print(f"  {name:35s} tf={res['tf']:4s} n_trades={res['n_trades']:5d} "
                  f"n_checked={res['n_checked']:4d}  OK", flush=True)

    print(f"\nRIEPILOGO: {n_ok} pulite, {n_errors} con incoerenze, "
          f"{n_zero_trades} senza trade nel campione, {n_crash} in errore/crash", flush=True)


if __name__ == "__main__":
    main()
