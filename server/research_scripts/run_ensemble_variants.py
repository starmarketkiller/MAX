#!/usr/bin/env python3
"""
10/08 (5) - "prova tutto": le tre piste lasciate aperte in
NEXUS EA - Ricerca Combinazioni Multi-Strategia (10-08).md dopo che
nessuna combinazione trovata sull'oro batteva MACD da sola:

1. Ensemble su BTCUSD (dati gia' disponibili via Yahoo, 10 anni
   giornalieri, cicli toro/orso veri) - stesso Metodo 3, mercato diverso.
2. Voto PESATO (peso = PF individuale IS) invece di uniforme, sull'oro.
3. Filtro di REGIME (_regime_series) sopra il miglior ensemble oro
   trovato finora, per vedere se restringere ai regimi favorevoli aiuta.

La quarta pista (piu' storico) non e' eseguibile oggi - richiede solo
tempo, il Dukascopy continua a crescere in background.
"""
import sys
import os
import json
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import backtest as bt
import ensemble_engine_search as e

GOLD_FINAL_COMBO = ["MACD", "LIQ_SWEEP", "FVG_CONT", "EMA_PULLBACK", "RSI_DIV", "SILVER_BULLET",
                     "ICHIMOKU", "FVG_MIT", "SH_BMS_RTO", "LONDON_BO", "AMD_CONT", "STRUCT_REACT",
                     "OTE_CONT", "TSI", "ADX_RSI"]


def part1_btc():
    print("\n########## PARTE 1: ensemble su BTCUSD (1d, 10 anni) ##########", flush=True)
    # Yahoo 1d range = 10y (vedi _YF_INTERVAL in backtest.py), bars alto
    # per non tagliare nulla del range disponibile.
    base, pool2, hist = e.main(symbol="BTCUSD", tf="1d", bars=5000,
                                out_name="ensemble_btc_results.json")
    return base, pool2, hist


def part2_weighted():
    print("\n########## PARTE 2: voto PESATO sull'oro (peso = PF individuale IS) ##########", flush=True)
    pool = e.pool_for("XAUUSD")
    base = e.baseline_all(pool, "XAUUSD", "4h", 60000)
    e.print_baseline(base)
    pool2 = e.robust_pool(base, min_is_trades=30)

    weights = {}
    for row in base:
        if row["strategy"] not in pool2:
            continue
        pf = row.get("is", {}).get("pf")
        w = 1.0 if pf is None else max(0.2, min(pf, 3.0))
        weights[row["strategy"]] = w
    print("\nPesi (PF individuale IS, clip [0.2, 3.0]):")
    print(", ".join(f"{k}={v:.2f}" for k, v in sorted(weights.items())))

    print("\n--- ricerca greedy pesata ---", flush=True)
    hist = e.greedy_search(pool2, "XAUUSD", "4h", 60000, weights=weights)

    out_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ensemble_weighted_results.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump({"weights": weights, "pool_ensemble": pool2, "greedy": hist}, f, indent=2)
    print(f"Salvato: {out_path}")
    return weights, hist


def part3_regime():
    print("\n########## PARTE 3: filtro di regime sul miglior ensemble oro ##########", flush=True)
    candles_is, ind_is = e.load_slice("XAUUSD", "4h", 60000, (0.0, 0.6))
    candles_oos, ind_oos = e.load_slice("XAUUSD", "4h", 60000, (0.6, 1.0))
    sigs_is = e.precompute_signals(candles_is, ind_is, GOLD_FINAL_COMBO)
    sigs_oos = e.precompute_signals(candles_oos, ind_oos, GOLD_FINAL_COMBO)

    REGIMES = {
        "TUTTI (baseline)": None,
        "STRONG_TREND": {1},
        "WEAK_TREND": {2},
        "VOLATILE": {3},
        "CHOPPY": {4},
        "RANGING": {5},
        "STRONG+WEAK_TREND": {1, 2},
    }
    print(f"{'Regime':<20}{'mv':>4}   {'IS PF':>7}{'IS n':>6}   {'OOS PF':>7}{'OOS n':>6}")
    results = {}
    for label, regime_ok in REGIMES.items():
        # sceglie la soglia di voto migliore SOLO su IS, per ciascun regime
        best = None
        for mv in [1, 2, 3, 4]:
            r_is = e.simulate(candles_is, ind_is, sigs_is, GOLD_FINAL_COMBO, mv, regime_ok=regime_ok)
            sc = e.score(r_is) if r_is["trades"] >= 15 else -999  # soglia piu' bassa: i regimi filtrano gia' molto
            if best is None or sc > best["score"]:
                best = {"mv": mv, "is": r_is, "score": sc}
        if best is None or best["score"] <= -900:
            print(f"{label:<20}{'--':>4}   campione insufficiente in-sample")
            continue
        r_oos = e.simulate(candles_oos, ind_oos, sigs_oos, GOLD_FINAL_COMBO, best["mv"], regime_ok=regime_ok)
        results[label] = {"mv": best["mv"], "is": best["is"], "oos": r_oos}
        print(f"{label:<20}{best['mv']:>4}   {best['is']['pf']:>7}{best['is']['trades']:>6}   "
              f"{r_oos['pf']:>7}{r_oos['trades']:>6}")

    out_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ensemble_regime_results.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    print(f"Salvato: {out_path}")
    return results


if __name__ == "__main__":
    part1_btc()
    part2_weighted()
    part3_regime()
    print("\n########## FATTO ##########", flush=True)
