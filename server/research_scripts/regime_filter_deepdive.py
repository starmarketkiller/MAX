#!/usr/bin/env python3
"""
10/08 (7) - approfondimento richiesto sui due candidati che il filtro
STRONG_TREND ha davvero aiutato (regime_filter_singles.py):
BREAKOUT_ACC (OOS PF 1.78->1.84, 43 trade) e LIQ_SWEEP (1.48->2.17,
21 trade). Un solo split 60/40 non basta a fidarsi - qui si controllano
tre cose diverse:

1. Walk-forward su 5 finestre sequenziali (non solo IS/OOS 60/40):
   il vantaggio del filtro e' consistente nel tempo o concentrato in
   una sola finestra fortunata?
2. Distribuzione temporale dei trade filtrati entro l'OOS: sparsi
   lungo tutto il periodo o ammassati in poche settimane?
3. Verifica incrociata su BTCUSD: lo stesso filtro aiuta anche li'?
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ensemble_engine_search as e

CANDIDATES = [("BREAKOUT_ACC", {1}), ("LIQ_SWEEP", {1})]  # {1} = STRONG_TREND


def walk_forward(symbol, tf, bars, strat, regime_ok, n_windows=5):
    print(f"\n--- {strat} su {symbol} {tf}: walk-forward a {n_windows} finestre ---")
    print(f"{'Finestra':<12}{'Filtrato PF':>12}{'n':>5}   {'Baseline PF':>12}{'n':>5}")
    for w in range(n_windows):
        br = (w / n_windows, (w + 1) / n_windows)
        candles, ind = e.load_slice(symbol, tf, bars, br)
        sigs = e.precompute_signals(candles, ind, [strat])
        r_filt = e.simulate(candles, ind, sigs, [strat], 1, regime_ok=regime_ok)
        r_base = e.simulate(candles, ind, sigs, [strat], 1, regime_ok=None)
        print(f"{w+1}/{n_windows:<8}{str(r_filt['pf']):>12}{r_filt['trades']:>5}   "
              f"{str(r_base['pf']):>12}{r_base['trades']:>5}")


def trade_timing(symbol, tf, bars, strat, regime_ok):
    """Dove cadono nel tempo i trade filtrati vs quelli scartati, dentro l'OOS."""
    candles, ind = e.load_slice(symbol, tf, bars, (0.6, 1.0))
    regime = ind["regime"]
    sig_fn = ind is not None
    import backtest as bt
    fn = bt.STRATEGIES[strat]
    n = len(candles)
    in_regime_bars = sum(1 for i in range(n) if regime[i] in regime_ok)
    signals = [(i, fn(candles, ind, i)) for i in range(60, n)]
    sig_bars = [i for i, s in signals if s != 0]
    sig_in_regime = [i for i, s in signals if s != 0 and regime[i] in regime_ok]
    print(f"\n--- {strat}: dove cadono i segnali nell'OOS ({symbol}) ---")
    print(f"barre totali OOS: {n}, barre in STRONG_TREND: {in_regime_bars} ({100*in_regime_bars/n:.0f}%)")
    print(f"segnali totali: {len(sig_bars)}, di cui in STRONG_TREND: {len(sig_in_regime)} "
          f"({100*len(sig_in_regime)/max(1,len(sig_bars)):.0f}%)")
    if sig_in_regime:
        span = sig_in_regime[-1] - sig_in_regime[0]
        print(f"primo/ultimo segnale filtrato: barra {sig_in_regime[0]}/{sig_in_regime[-1]} "
              f"su {n} totali (span {100*span/n:.0f}% della finestra) - "
              f"{'sparsi' if span > n*0.5 else 'concentrati in una parte della finestra'}")


def btc_check(strat, regime_ok):
    print(f"\n--- {strat} su BTCUSD 1d (verifica incrociata) ---")
    for label, br in [("IS 60%", (0.0, 0.6)), ("OOS 40%", (0.6, 1.0))]:
        candles, ind = e.load_slice("BTCUSD", "1d", 5000, br)
        sigs = e.precompute_signals(candles, ind, [strat])
        r_filt = e.simulate(candles, ind, sigs, [strat], 1, regime_ok=regime_ok)
        r_base = e.simulate(candles, ind, sigs, [strat], 1, regime_ok=None)
        print(f"{label}: filtrato pf={r_filt['pf']} n={r_filt['trades']}   "
              f"baseline pf={r_base['pf']} n={r_base['trades']}")


def main():
    for strat, regime_ok in CANDIDATES:
        walk_forward("XAUUSD", "4h", 60000, strat, regime_ok, n_windows=5)
        trade_timing("XAUUSD", "4h", 60000, strat, regime_ok)
        btc_check(strat, regime_ok)


if __name__ == "__main__":
    main()
