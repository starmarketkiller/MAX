#!/usr/bin/env python3
"""
09/08 - scan sistematico di tutte le 37 strategie LIVE su Dukascopy reale
(357+ giorni), motore SEMPLICE run_backtest() (nessun TREND_GATE), su tre
timeframe (1h/4h/1d) indipendentemente da cosa dichiara
contracts/strategy-registry.json (supported_timeframes) - quel campo si e'
gia' dimostrato INAFFIDABILE da solo (LONDON_BO dichiarato D1 ma il codice
stesso, backtest.py righe 1497-1498, dice esplicitamente "testarla su D1
dava 0 trade perche' g_session non esiste su una barra giornaliera").
Testare su tutti e tre i TF, non solo quello dichiarato, fa emergere
automaticamente questi casi (0 trade dove il segnale e' TF-dipendente)
invece di fidarsi ciecamente del registro.

SL/TP: default retail (1.5/3.0 ATR), stesso standard usato dal test live
sul sito per LONDON_BO ieri - confronto onesto, stessa configurazione.
"""
import sys
import os
import json
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import backtest as bt

REG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..",
                        "contracts", "strategy-registry.json")
TFS = ["1h", "4h", "1d"]
MIN_TRADES_MEANINGFUL = 15


def main():
    reg = json.load(open(REG_PATH, encoding="utf-8"))
    declared_tf = {"D1": "1d", "H4": "4h", "H1": "1h", "*": None}
    live = [(s["strategy_id"], s["supported_timeframes"][0]) for s in reg["strategies"]
            if s["live_implementation"]]

    results = []
    for idx, (sid, decl) in enumerate(sorted(live), 1):
        for tf in TFS:
            try:
                r = bt.run_backtest(symbol="XAUUSD", timeframe=tf, strategy=sid,
                                    atr_sl=1.5, atr_tp=3.0)
                results.append({
                    "strategy": sid, "declared_tf": declared_tf.get(decl, decl), "tf": tf,
                    "src": r["data_source"], "trades": r["trades"],
                    "pf": r["profit_factor"], "wr": r["win_rate"], "max_dd": r["max_dd_pct"],
                    "net_pnl": r["net_pnl"],
                })
            except Exception as e:
                results.append({"strategy": sid, "declared_tf": declared_tf.get(decl, decl),
                               "tf": tf, "error": str(e)[:100]})
        print(f"[{idx}/{len(live)}] {sid} fatto", flush=True)

    print("\n" + "=" * 110)
    print(f"{'Strategia':<26}{'TF-registro':<12}{'TF-test':<8}{'trade':>7}{'PF':>7}{'WR%':>7}{'MaxDD%':>8}{'src':>12}")
    for r in results:
        if "error" in r:
            print(f"{r['strategy']:<26}{r['declared_tf'] or '*':<12}{r['tf']:<8}  ERRORE: {r['error']}")
            continue
        flag = "" if r["trades"] >= MIN_TRADES_MEANINGFUL else "  (campione piccolo)"
        match = " <-- TF registro" if r["tf"] == r["declared_tf"] else ""
        print(f"{r['strategy']:<26}{(r['declared_tf'] or '*'):<12}{r['tf']:<8}{r['trades']:>7}"
              f"{str(r['pf']):>7}{r['wr']:>7}{r['max_dd']:>8}{r['src']:>12}{match}{flag}")
    print("=" * 110)

    out_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..",
                            "server", "research_scripts", "full_strategy_tf_scan_results.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    print(f"\nSalvato: {out_path}")


if __name__ == "__main__":
    main()
