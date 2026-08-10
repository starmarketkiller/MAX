#!/usr/bin/env python3
"""
10/08 (6) - la raccomandazione dopo "prova tutto": il filtro di regime
(STRONG_TREND) ha aiutato MACD da sola (OOS PF 1.58->2.08, 47 trade)
molto piu' di quanto abbia aiutato qualsiasi ensemble. Prima di
considerarlo un pattern generale (e non un caso isolato di MACD),
ripeterlo sulle altre singole "buone" trovate oggi: TURTLE_SOUP,
BREAKOUT_ACC, LIQ_SWEEP, LONDON_BO, FVG_MIT. MACD inclusa come
riferimento/controllo di coerenza con quanto gia' trovato.

Per ciascuna strategia: sceglie il regime migliore SOLO su in-sample
(tra tutti i _REGIME_* singoli + STRONG+WEAK_TREND insieme + nessun
filtro), verifica il risultato di quella scelta su out-of-sample mai
visto durante la selezione - stessa disciplina di tutta la sessione.

10/08 (8) - STRATS reso configurabile da riga di comando: ri-eseguito
su ADX_RSI/SAR/TSI (campione grande, mai isolate prima con un filtro
di regime proprio - segnalate nel report di stato ottimizzazione).
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ensemble_engine_search as e

SYMBOL, TF, BARS = "XAUUSD", "4h", 60000
STRATS = sys.argv[1:] if len(sys.argv) > 1 else \
    ["MACD", "TURTLE_SOUP", "BREAKOUT_ACC", "LIQ_SWEEP", "LONDON_BO", "FVG_MIT"]
MIN_IS_TRADES = 15

REGIMES = {
    "nessun filtro": None,
    "STRONG_TREND": {1},
    "WEAK_TREND": {2},
    "VOLATILE": {3},
    "CHOPPY": {4},
    "RANGING": {5},
    "STRONG+WEAK_TREND": {1, 2},
}


def main():
    candles_is, ind_is = e.load_slice(SYMBOL, TF, BARS, (0.0, 0.6))
    candles_oos, ind_oos = e.load_slice(SYMBOL, TF, BARS, (0.6, 1.0))
    sigs_is = e.precompute_signals(candles_is, ind_is, STRATS)
    sigs_oos = e.precompute_signals(candles_oos, ind_oos, STRATS)

    print(f"{'Strategia':<14}{'Regime scelto (su IS)':<20}{'IS PF':>7}{'IS n':>6}   "
          f"{'OOS PF':>7}{'OOS n':>6}   {'Baseline OOS (no filtro)':>26}")
    results = []
    for strat in STRATS:
        base_oos = e.simulate(candles_oos, ind_oos, sigs_oos, [strat], 1, regime_ok=None)
        best = None
        for label, regime_ok in REGIMES.items():
            r_is = e.simulate(candles_is, ind_is, sigs_is, [strat], 1, regime_ok=regime_ok)
            if r_is["pf"] is None or r_is["trades"] < MIN_IS_TRADES:
                continue
            sc = e.score(r_is) if r_is["trades"] >= 20 else r_is["exp_r"] * (r_is["trades"] ** 0.5)
            if best is None or sc > best["score"]:
                best = {"label": label, "regime_ok": regime_ok, "is": r_is, "score": sc}
        if best is None:
            print(f"{strat:<14}{'--':<20}   nessun regime con >= {MIN_IS_TRADES} trade IS")
            continue
        r_oos = e.simulate(candles_oos, ind_oos, sigs_oos, [strat], 1, regime_ok=best["regime_ok"])
        results.append({"strategy": strat, "regime": best["label"], "is": best["is"],
                         "oos": r_oos, "baseline_oos": base_oos})
        helped = (r_oos["pf"] is not None and base_oos["pf"] is not None and r_oos["pf"] > base_oos["pf"])
        print(f"{strat:<14}{best['label']:<20}{best['is']['pf']:>7}{best['is']['trades']:>6}   "
              f"{r_oos['pf']:>7}{r_oos['trades']:>6}   {base_oos['pf']:>26}"
              f"{'  <- aiuta' if helped else ''}")

    import json
    out_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "regime_filter_singles_results.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    print(f"\nSalvato: {out_path}")


if __name__ == "__main__":
    main()
