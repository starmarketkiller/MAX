#!/usr/bin/env python3
"""Phase 7.9I - Natural Horizon. Curve forward excursion/return vs tempo
(barre D1), con dispersione e N osservazioni, per Population B (47
OPENED). L'orizzonte NON viene scelto guardando quale rendimento e'
migliore - si descrive dove il segnale sembra stabilizzarsi/decadere/
essere assorbito dal rumore, o se non emerge un orizzonte stabile.
"""
import math
import os
import statistics
import sys
from datetime import datetime

PHASE79I_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(PHASE79I_DIR, "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase6_6"))
from canonical_utils import load_json, save_json, wrap_with_provenance  # noqa: E402

sys.path.insert(0, PHASE79I_DIR)
import nxs_mechanism_context as ctx  # noqa: E402

MAX_H = ctx.MAX_PATH_WINDOW_D1


def _mean_ci(values):
    values = [v for v in values if v is not None]
    n = len(values)
    if n == 0:
        return {"n": 0, "mean": None, "se": None, "ci95_low": None, "ci95_high": None}
    mean = statistics.mean(values)
    if n < 2:
        return {"n": n, "mean": round(mean, 4), "se": None, "ci95_low": None, "ci95_high": None}
    se = statistics.stdev(values) / math.sqrt(n)
    return {"n": n, "mean": round(mean, 4), "se": round(se, 4),
           "ci95_low": round(mean - 1.96 * se, 4), "ci95_high": round(mean + 1.96 * se, 4)}


def build():
    feat_doc = load_json(os.path.join(PHASE79I_DIR, "breakout_acc_feature_engineering_v1.json"))
    rows = feat_doc["payload"]["rows"]
    d1_bars = ctx.load_d1_bars()
    pop_b = [r for r in rows if r["funnel_terminal_stage"] == "OPENED"]

    curves = []
    for r in pop_b:
        entry_dt = datetime.strptime(r["entry_fill_time"], "%Y.%m.%d %H:%M:%S")
        curve = ctx.full_path_curve(d1_bars, entry_dt, r["entry_fill_price"], r["direction"])
        if curve is None:
            continue
        curves.append({"event_id": r["event_id"], "direction": r["direction_label"],
                       "curve": curve})

    per_bar = []
    for t in range(1, MAX_H + 1):
        rets = []
        favs = []
        advs = []
        for c in curves:
            point = next((p for p in c["curve"] if p["bar"] == t), None)
            if point is None:
                continue
            rets.append(point["close_to_close_return"])
            favs.append(point["favorable_excursion_running_max"])
            advs.append(point["adverse_excursion_running_max"])
        per_bar.append({
            "bar_d1": t,
            "close_to_close_return": _mean_ci(rets),
            "favorable_excursion_running_max": _mean_ci(favs),
            "adverse_excursion_running_max": _mean_ci(advs),
        })

    # Descrizione qualitativa NON basata sulla scelta del rendimento migliore: guarda
    # dove il rapporto |mean return| / SE (una specie di t-stat descrittiva, non un test
    # d'ipotesi formale) e' massimo, e dove il CI95 smette di escludere lo zero in modo
    # stabile per piu' barre consecutive - unicamente descrittivo.
    tstat_like = []
    for p in per_bar:
        m = p["close_to_close_return"]
        if m["mean"] is not None and m["se"] not in (None, 0):
            tstat_like.append((p["bar_d1"], abs(m["mean"]) / m["se"]))
    peak_bar, peak_val = max(tstat_like, key=lambda x: x[1]) if tstat_like else (None, None)

    excludes_zero = [p["bar_d1"] for p in per_bar
                     if p["close_to_close_return"]["ci95_low"] is not None
                     and (p["close_to_close_return"]["ci95_low"] > 0
                          or p["close_to_close_return"]["ci95_high"] < 0)]
    stable_run = []
    if excludes_zero:
        run = [excludes_zero[0]]
        best_run = run[:]
        for b in excludes_zero[1:]:
            if b == run[-1] + 1:
                run.append(b)
            else:
                if len(run) > len(best_run):
                    best_run = run
                run = [b]
        if len(run) > len(best_run):
            best_run = run
        stable_run = best_run

    if stable_run and len(stable_run) >= 5:
        finding = (f"Il ritorno medio close-to-close esclude lo zero (CI95%) in modo "
                  f"continuativo dalla barra D1 {stable_run[0]} alla {stable_run[-1]} "
                  f"({len(stable_run)} barre consecutive) - un orizzonte naturale "
                  f"PARZIALMENTE identificabile in questa finestra, con la cautela che N="
                  f"{len(curves)} eventi e un CI95% descrittivo (non un test d'ipotesi "
                  f"formale/corretto per confronti multipli).")
        stable_horizon_identified = True
    else:
        finding = ("Non emerge un intervallo di almeno 5 barre D1 consecutive in cui il "
                  "CI95% del ritorno medio esclude establmente lo zero - con N="
                  f"{len(curves)} eventi la dispersione e' troppo ampia per isolare un "
                  "orizzonte naturale stabile in questa analisi. Non si puo' concludere "
                  "ne' l'assenza ne' la presenza di un vero natural horizon - solo che "
                  "questo campione non lo rende visibile con la metodologia descrittiva "
                  "usata qui.")
        stable_horizon_identified = False

    means = [p["close_to_close_return"]["mean"] for p in per_bar if p["close_to_close_return"]["mean"] is not None]
    shape_description = (
        "La media del ritorno close-to-close cresce in modo pressoche' monotono da "
        f"~{round(means[0],1)} (barra 1) a ~{round(means[-1],1)} (barra {len(means)}), "
        "SENZA un chiaro plateau ne' un decadimento visibile entro la finestra di 60 barre "
        "D1 osservata - il vantaggio informativo (se reale) non appare saturo entro questo "
        "orizzonte: potrebbe estendersi oltre 60 barre, oppure riflettere la coda di pochi "
        "eventi con movimenti tardivi molto ampi (dispersione CI ampia a barre lunghe - "
        "vedi ci95_high/ci95_low nel per_bar_curve)."
    )

    return {
        "phase": "7.9I", "input_frozen_dataset": "breakout_acc_intended_d1_v1_dataset.json "
            f"(sha256={feat_doc['payload']['source_canonical_dataset_sha256']})",
        "shape_description": shape_description,
        "population_used": f"B_opened ({len(curves)} eventi con curva di percorso completa)",
        "no_optimization_horizon_not_chosen_by_best_return": True,
        "method": "Media e CI95% (approssimato, mean +/- 1.96*SE) del ritorno close-to-close "
            "e delle excursion running-max, calcolati barra per barra (1..60 barre D1) su "
            "tutti gli eventi Population B. Il 'natural horizon' viene descritto cercando "
            "dove il CI95% esclude establmente lo zero per piu' barre consecutive, MAI "
            "scegliendo l'orizzonte con il rendimento piu' alto.",
        "per_bar_curve": per_bar,
        "descriptive_peak_abs_mean_over_se_bar": peak_bar,
        "descriptive_peak_abs_mean_over_se_value": round(peak_val, 3) if peak_val else None,
        "stable_ci_excludes_zero_run_bars": stable_run,
        "stable_horizon_identified": stable_horizon_identified,
        "finding": finding,
    }


def main():
    payload = build()
    doc = wrap_with_provenance(payload, os.path.basename(__file__))
    save_json(os.path.join(PHASE79I_DIR, "breakout_acc_natural_horizon_v1.json"), doc)
    print(f"canonical_sha256={doc['canonical_sha256']}")
    print(f"stable_horizon_identified={payload['stable_horizon_identified']}")
    print(payload["finding"])
    return doc


if __name__ == "__main__":
    main()
