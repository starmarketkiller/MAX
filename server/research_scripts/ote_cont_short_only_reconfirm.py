#!/usr/bin/env python3
"""
09/08 - ricostruzione del test OTE_CONT Short-Only (zona fib 61.8-79% +
rifiuto in direzione del trend interno, tolleranza wait_bars) su dati
Dukascopy reali (355 giorni, soglia 300 superata). Lo script scratch
originale che aveva prodotto PF 2.11/23 trade (wait_bars=8, Short-Only) su
finestra Yahoo corta NON e' stato salvato nel repo - solo il generatore di
segnale (ote_cont_state_series, in group_c_state_machine.py, GIA' committato
e fedele all'originale) e' sopravvissuto.

Qui il generatore di segnale reale viene rieseguito TALE E QUALE, sostituito
temporaneamente al posto della vera implementazione OTE_CONT in
bt.STRATEGIES (ripristinata a fine script) e fatto girare attraverso il
motore run_backtest() vero - stesso SL/TP (default retail 1.5/3.0 ATR),
stesso costo/drawdown/PF gia' usato da ogni altra strategia, invece di
reinventare a mano equity/drawdown (rischio di introdurre un bug sottile
nella ricostruzione). direction_lock="SELL" per la variante Short-Only,
None per la bidirezionale (confronto).
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import backtest as bt
from group_c_state_machine import ote_cont_state_series

_ORIGINAL_OTE_CONT = bt.STRATEGIES["OTE_CONT"]


def _make_signal(wait_bars):
    cache = {}

    def _sig(candles, ind, idx):
        key = (id(candles), wait_bars)
        if key not in cache:
            cache.clear()
            cache[key] = ote_cont_state_series(candles, ind["adx"], ind["choch_int"],
                                                ind["atr"], wait_bars=wait_bars)
        return cache[key][idx]
    return _sig


def main():
    print(f"{'wait_bars':<10}{'dir_lock':<10}{'trades':>8}{'pf':>8}{'wr%':>8}{'net_pnl':>10}{'max_dd%':>9}")
    for wait_bars in (5, 8, 12):
        bt.STRATEGIES["OTE_CONT"] = _make_signal(wait_bars)
        try:
            for lock, label in ((None, "bidir"), ("SELL", "short_only")):
                r = bt.run_backtest(symbol="XAUUSD", timeframe="1h", strategy="OTE_CONT",
                                    direction_lock=lock, atr_sl=1.5, atr_tp=3.0)
                print(f"{wait_bars:<10}{label:<10}{r['trades']:>8}{str(r['profit_factor']):>8}"
                      f"{r['win_rate']:>8}{r['net_pnl']:>10}{r['max_dd_pct']:>9}"
                      f"  (src={r['data_source']})")
        finally:
            bt.STRATEGIES["OTE_CONT"] = _ORIGINAL_OTE_CONT


if __name__ == "__main__":
    main()
