#!/usr/bin/env python3
"""Phase 7.27 punto 3 - calcolo delle metriche di outcome per un
entry BUY a un dato indice di barra D1. Definizione comune per
confrontabilita' reale<->benchmark: ref_price = CLOSE della barra di
entry (i benchmark non hanno un 'prezzo di segnale' proprio - per il
confronto primario si usa la stessa definizione per tutti). Per gli
eventi REALI, signal-relative/fill-relative sono riportati SEPARATAMENTE
(vedi build_per_strategy_results.py) come check di robustezza
esplorativo, non come base del confronto primario."""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from nxs_gold_d1_loader import load_d1, bars_forward  # noqa: E402
import nxs_prereg_constants as C  # noqa: E402

MAX_HORIZON = max(C.HORIZONS_D1_BARS)


def compute_outcome_metrics(bar_index, ref_price=None):
    """direction e' sempre BUY in questo test (per costruzione - la
    hypothesis riguarda specificamente la dominanza BUY)."""
    df = load_d1()
    if ref_price is None:
        ref_price = float(df.iloc[bar_index]["close"])
    bars = bars_forward(bar_index, MAX_HORIZON)
    if not bars:
        return {"data_available": False, "reason": "nessuna barra forward disponibile (fine serie)"}

    horizons = {}
    for h in C.HORIZONS_D1_BARS:
        if len(bars) >= h:
            ret = bars[h - 1]["close"] - ref_price
            horizons[f"h{h}"] = {"forward_return_price_units": ret, "favorable": ret > 0}
        else:
            horizons[f"h{h}"] = {"forward_return_price_units": None, "favorable": None,
                                 "censored": True}

    running_max_fav = running_max_adv = 0.0
    t_mfe = t_mae = t_profit = None
    mae_before_profit = 0.0
    for i, b in enumerate(bars, start=1):
        fav = b["high"] - ref_price
        adv = ref_price - b["low"]
        if fav > running_max_fav:
            running_max_fav, t_mfe = fav, i
        if adv > running_max_adv:
            running_max_adv, t_mae = adv, i
        if t_profit is None:
            if b["close"] > ref_price:
                t_profit = i
            else:
                mae_before_profit = max(mae_before_profit, adv)

    return {
        "data_available": True, "ref_price": ref_price, "n_bars_available": len(bars),
        "censored_horizon": len(bars) < MAX_HORIZON,
        "horizons": horizons,
        "mfe_price_units": running_max_fav, "mae_price_units": running_max_adv,
        "time_to_mfe_bars": t_mfe, "time_to_mae_bars": t_mae,
        "time_to_profit_bars": t_profit,
        "adverse_excursion_before_favorable_movement": mae_before_profit if t_profit else None,
    }
