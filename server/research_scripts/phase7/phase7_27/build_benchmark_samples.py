#!/usr/bin/env python3
"""Phase 7.27 punto 2+3 - costruisce i campioni benchmark e calcola le
metriche di outcome per OGNI evento reale e OGNI barra di benchmark,
per le 3 strategie. Un solo artifact (le dipendenze a valle - per-
strategy/cross-strategy/regime-controlled - leggono da qui, nessuna
ricalcola i benchmark autonomamente - preregistrazione rispettata)."""
import os
import sys

PHASE727_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(PHASE727_DIR, "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase6_6"))
from canonical_utils import wrap_with_provenance, save_json  # noqa: E402

sys.path.insert(0, PHASE727_DIR)
import nxs_prereg_constants as C  # noqa: E402
from nxs_real_buy_events_loader import load_all_buy_events  # noqa: E402
from nxs_gold_d1_loader import bar_index_for_date, load_d1  # noqa: E402
from nxs_regime_classifier import regime_for_index  # noqa: E402
from nxs_outcome_metrics import compute_outcome_metrics  # noqa: E402
from nxs_benchmark_generators import (random_timestamps_matched, unconditional_population,  # noqa: E402
                                      periodic_entries, regime_matched_random, seed_for)

STRATEGY_PERIODS = {
    "BREAKOUT_ACC": ("2019.02.21", "2026.06.09"),
    "ORDER_BLOCK": ("2023.10.02", "2026.08.24"),
    "LIQ_SWEEP": ("2023.10.02", "2026.06.30"),
}


def _pdt(s):
    from datetime import datetime
    return datetime.strptime(s, "%Y.%m.%d")


def _metrics_for_indices(indices):
    out = []
    for idx in indices:
        if idx is None:
            out.append({"data_available": False, "reason": "nessun match di regime disponibile"})
            continue
        out.append(compute_outcome_metrics(idx))
    return out


def _population_summary(indices):
    """Per UNCONDITIONAL_LONG_EXPOSURE: la popolazione intera non ha
    incertezza campionaria propria (e' l'intero periodo, non un
    campione) - salviamo solo le statistiche aggregate per orizzonte,
    non ogni singola barra (migliaia di dict quasi duplicati altrimenti)."""
    import statistics
    metrics = [compute_outcome_metrics(i) for i in indices]
    available = [m for m in metrics if m.get("data_available")]
    summary = {"n_population_bars": len(indices), "n_data_available": len(available)}
    for h in C.HORIZONS_D1_BARS:
        rets = [m["horizons"][f"h{h}"]["forward_return_price_units"] for m in available
               if m["horizons"][f"h{h}"]["forward_return_price_units"] is not None]
        summary[f"h{h}"] = {
            "n": len(rets), "mean_forward_return": statistics.mean(rets) if rets else None,
            "stdev_forward_return": statistics.stdev(rets) if len(rets) > 1 else None,
            "pct_favorable": (sum(1 for r in rets if r > 0) / len(rets)) if rets else None,
        }
    mfes = [m["mfe_price_units"] for m in available]
    maes = [m["mae_price_units"] for m in available]
    summary["mean_mfe"] = statistics.mean(mfes) if mfes else None
    summary["mean_mae"] = statistics.mean(maes) if maes else None
    return summary


def _buy_and_hold(period_start_dt, period_end_dt):
    df = load_d1()
    mask = (df["time"] >= period_start_dt) & (df["time"] <= period_end_dt)
    sub = df.loc[mask]
    if sub.empty:
        return {"data_available": False}
    start_close = float(sub.iloc[0]["close"])
    end_close = float(sub.iloc[-1]["close"])
    return {"data_available": True, "period_start_close": start_close, "period_end_close": end_close,
           "total_return_price_units": end_close - start_close,
           "total_return_pct": (end_close - start_close) / start_close * 100,
           "n_bars": len(sub),
           "note": "Contesto macro (drift secolare) - MAI un confronto trade-per-trade diretto."}


def _real_events_with_metrics(strategy_identity, real_events):
    out = []
    for e in real_events:
        bar_idx = bar_index_for_date(e["entry_time"])
        if bar_idx is None:
            out.append({**e, "entry_time": e["entry_time"].strftime("%Y.%m.%d %H:%M:%S"),
                       "bar_index": None, "metrics_close_relative": {"data_available": False,
                       "reason": "fuori copertura serie D1"}})
            continue
        metrics_close = compute_outcome_metrics(bar_idx)
        metrics_signal = compute_outcome_metrics(bar_idx, ref_price=e["signal_price"])
        metrics_fill = (compute_outcome_metrics(bar_idx, ref_price=e["fill_price"])
                       if e.get("fill_price") is not None else {"data_available": False,
                       "reason": "nessun prezzo di fill separato per questa strategia"})
        out.append({
            "event_id": e["event_id"], "entry_time": e["entry_time"].strftime("%Y.%m.%d %H:%M:%S"),
            "bar_index": bar_idx, "regime": regime_for_index(bar_idx),
            "metrics_close_relative": metrics_close,
            "metrics_signal_relative_exploratory": metrics_signal,
            "metrics_fill_relative_exploratory": metrics_fill,
        })
    return out


def build():
    events_by_strategy = load_all_buy_events()
    result = {}
    for strat in C.STRATEGIES_INCLUDED:
        period_start, period_end = STRATEGY_PERIODS[strat]
        start_dt, end_dt = _pdt(period_start), _pdt(period_end)
        real_events = events_by_strategy[strat]
        n = len(real_events)

        real_with_metrics = _real_events_with_metrics(strat, real_events)
        real_bar_indices = [r["bar_index"] for r in real_with_metrics if r["bar_index"] is not None]

        seed_random = seed_for(strat, "RANDOM_TIMESTAMPS_MATCHED")
        seed_regime = seed_for(strat, "REGIME_MATCHED_RANDOM_LONG")

        random_idx = random_timestamps_matched(start_dt, end_dt, n, seed_random)
        periodic_idx = periodic_entries(start_dt, end_dt, n)
        regime_idx = regime_matched_random(real_bar_indices, start_dt, end_dt, seed_regime)
        unconditional_idx = unconditional_population(start_dt, end_dt)

        result[strat] = {
            "period": [period_start, period_end], "n_real_buy_events": n,
            "real_events": real_with_metrics,
            "benchmarks": {
                "RANDOM_TIMESTAMPS_MATCHED": {"seed": seed_random, "n": len(random_idx),
                    "samples": _metrics_for_indices(random_idx)},
                "PERIODIC_ENTRY_LONG": {"n": len(periodic_idx),
                    "samples": _metrics_for_indices(periodic_idx)},
                "REGIME_MATCHED_RANDOM_LONG": {"seed": seed_regime, "n": len(regime_idx),
                    "n_unmatched": sum(1 for i in regime_idx if i is None),
                    "samples": _metrics_for_indices(regime_idx)},
                "UNCONDITIONAL_LONG_EXPOSURE": {
                    "note": "Popolazione intera (nessuna incertezza campionaria propria - e' il "
                           "periodo completo, non un campione) - solo statistiche aggregate per "
                           "orizzonte, non ogni singola barra.",
                    "summary": _population_summary(unconditional_idx)},
                "BUY_AND_HOLD_MACRO_CONTEXT": _buy_and_hold(start_dt, end_dt),
            },
        }
    return result


def main():
    payload = build()
    doc = wrap_with_provenance(payload, script=os.path.abspath(__file__))
    out_path = os.path.join(PHASE727_DIR, "benchmark_samples_v1.json")
    save_json(out_path, doc)
    print(f"Scritto {out_path} (sha256={doc['canonical_sha256'][:16]}...)")
    for strat, d in payload.items():
        print(f"  {strat}: n_real={d['n_real_buy_events']} "
             f"unmatched_regime={d['benchmarks']['REGIME_MATCHED_RANDOM_LONG']['n_unmatched']}")


if __name__ == "__main__":
    main()
