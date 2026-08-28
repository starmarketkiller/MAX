#!/usr/bin/env python3
"""
13/08 - IFVG_CHOCH_WINDOW era "promettente, non confermato" (11/08): su 4h
IS 3.32/7, OOS 1.53/10, ma walk-forward VOLATILE con 2 finestre su 5
completamente a zero trade (non solo deboli) - a differenza di
TURTLE_SOUP_CHOCH/FVG_MIT_WINDOW, il problema qui sembra piu' di frequenza/
regime che di qualita' del segnale.

Due leve mai provate su questa strategia:
1. regime_filter - stesso meccanismo gia' validato due volte in sessione
   (MACD 10/08, famiglia SCALP_* 11/08): se le finestre a zero trade
   coincidono con bassa volatilita'/range, filtrare per regime potrebbe
   stabilizzare la frequenza invece di un fix di trigger.
2. _IFVG_CHOCH_WINDOW (oggi fissa a 5 barre) - mai sweepata.

Per ogni combinazione regime x finestra: IS/OOS, poi walk-forward a 5
finestre sul migliore per verificare se le finestre a zero trade spariscono
o si spostano solo altrove (in tal caso non e' un fix, e' overfitting).
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import backtest as bt

SYMBOL, TF, BARS = "XAUUSD", "4h", 110000
IS_RANGE, OOS_RANGE = (0.0, 0.6), (0.6, 1.0)
N_WINDOWS = 5
WINDOW_GRID = [3, 5, 7, 10, 15]

REGIMES = {
    "nessun filtro": None,
    "STRONG_TREND": {1},
    "WEAK_TREND": {2},
    "VOLATILE": {3},
    "STRONG+WEAK_TREND": {1, 2},
}

MIN_IS_TRADES = 15   # 4h + gia' un trigger raro di suo: soglia bassa per non scartare tutto


def call(bar_range, regime_ok):
    return bt.run_backtest(symbol=SYMBOL, timeframe=TF, strategy="IFVG_CHOCH_WINDOW",
                            strategies=["IFVG_CHOCH_WINDOW"], risk_pct=1.0, bars=BARS,
                            bar_range=bar_range, regime_filter=regime_ok)


def walk_forward(window, regime_ok):
    bt._IFVG_CHOCH_WINDOW = window
    out = []
    for w in range(N_WINDOWS):
        br = (w / N_WINDOWS, (w + 1) / N_WINDOWS)
        r = call(br, regime_ok)
        out.append((r.get("profit_factor"), r.get("trades")))
    return out


def main():
    print("NEXUS - IFVG_CHOCH_WINDOW: regime_filter x finestra CHoCH", flush=True)
    base_oos = call(OOS_RANGE, None)
    bt._IFVG_CHOCH_WINDOW = 5
    print(f"BASELINE (finestra=5, nessun filtro) OOS: pf={base_oos.get('profit_factor')} "
          f"n={base_oos.get('trades')} dd={base_oos.get('max_dd_pct')}%", flush=True)

    best = None
    for window in WINDOW_GRID:
        bt._IFVG_CHOCH_WINDOW = window
        for label, regime_ok in REGIMES.items():
            is_r = call(IS_RANGE, regime_ok)
            pf_is = is_r.get("profit_factor") or 0
            if is_r.get("trades", 0) < MIN_IS_TRADES:
                continue
            oos_r = call(OOS_RANGE, regime_ok)
            pf_oos = oos_r.get("profit_factor") or 0
            print(f"  finestra={window:>2} regime={label:<18} -> "
                  f"IS pf={pf_is} n={is_r.get('trades')} | "
                  f"OOS pf={pf_oos} n={oos_r.get('trades')} dd={oos_r.get('max_dd_pct')}%", flush=True)
            if pf_is > 1.10 and pf_oos > (base_oos.get("profit_factor") or 0) and \
                    (best is None or pf_oos > best["oos_pf"]):
                best = {"window": window, "regime": label, "regime_ok": regime_ok,
                        "oos_pf": pf_oos, "oos_n": oos_r.get("trades"), "oos_dd": oos_r.get("max_dd_pct"),
                        "is_pf": pf_is, "is_n": is_r.get("trades")}

    if not best:
        print("-- Nessuna combinazione batte il baseline OOS con IS pf>1.10.", flush=True)
        return
    print(f"-- MIGLIOR CANDIDATO: {best}", flush=True)
    print("-- walk-forward di verifica (5 finestre): candidato vs baseline "
          "(le finestre a zero trade spariscono o si spostano solo?)...", flush=True)
    wf_cand = walk_forward(best["window"], best["regime_ok"])
    wf_base = walk_forward(5, None)
    print("   candidato: " + "  |  ".join(f"{pf}/{n}" for pf, n in wf_cand), flush=True)
    print("   baseline:  " + "  |  ".join(f"{pf}/{n}" for pf, n in wf_base), flush=True)


if __name__ == "__main__":
    main()
