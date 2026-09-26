#!/usr/bin/env python3
"""Phase 7.9I - BLOCKED/BROKER_REJECT non trattati come trade persi o
vinti. Domanda: se il segnale fosse stato eseguito, il path successivo
era statisticamente diverso dagli OPENED? Path anatomy CONTROFATTUALE
(prezzo di chiusura della barra di breakout come proxy, MAI un fill
reale) per capire se i gate filtrano causalmente eventi peggiori,
casualmente, o eliminano eventi migliori. Analisi diagnostica, NON
proposta di modifica del gate.
"""
import os
import statistics
import sys

PHASE79I_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(PHASE79I_DIR, "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase6_6"))
from canonical_utils import load_json, save_json, wrap_with_provenance  # noqa: E402

sys.path.insert(0, PHASE79I_DIR)
import nxs_mechanism_context as ctx  # noqa: E402


def _stats(values):
    values = [v for v in values if v is not None]
    if not values:
        return {"n": 0}
    out = {"n": len(values), "mean": round(statistics.mean(values), 4),
           "median": round(statistics.median(values), 4)}
    if len(values) > 1:
        out["stdev"] = round(statistics.stdev(values), 4)
    return out


def build():
    feat_doc = load_json(os.path.join(PHASE79I_DIR, "breakout_acc_feature_engineering_v1.json"))
    rows = feat_doc["payload"]["rows"]
    d1_bars = ctx.load_d1_bars()

    groups = {"OPENED": [], "BLOCKED": [], "BROKER_REJECT": []}
    for r in rows:
        stage = r["funnel_terminal_stage"]
        if stage not in groups:
            continue
        if stage == "OPENED":
            path = r["post_entry_path_anatomy"]
        else:
            if r["breakout_close_c1"] is None:
                continue
            path = ctx.counterfactual_path_anatomy(
                d1_bars, r["d1_bar_date"], r["breakout_close_c1"], r["direction"])
        if path.get("status") != "OK":
            continue
        fwd60 = path["horizons"].get("fwd_return_60d1_price_units")
        groups[stage].append({
            "event_id": r["event_id"], "direction_label": r["direction_label"],
            "mfe": path["mfe_price_units"], "mae": path["mae_price_units"],
            "fwd_return_60d1": fwd60,
            "continuation": (fwd60 is not None and fwd60 > 0),
        })

    summary = {}
    for stage, evs in groups.items():
        n_cont = sum(1 for e in evs if e["continuation"])
        summary[stage] = {
            "n": len(evs), "path_method": ("REALE (fill verificato)" if stage == "OPENED"
                else "CONTROFATTUALE (prezzo di chiusura della barra di breakout come "
                     "proxy - il segnale non e' mai stato eseguito)"),
            "mfe": _stats([e["mfe"] for e in evs]),
            "mae": _stats([e["mae"] for e in evs]),
            "fwd_return_60d1": _stats([e["fwd_return_60d1"] for e in evs]),
            "n_continuation": n_cont, "n_events": len(evs),
            "pct_continuation": round(100 * n_cont / len(evs), 1) if evs else None,
        }

    opened_fwd60 = summary["OPENED"]["fwd_return_60d1"].get("median")
    blocked_fwd60 = summary["BLOCKED"]["fwd_return_60d1"].get("median")
    reject_fwd60 = summary["BROKER_REJECT"]["fwd_return_60d1"].get("median")

    interpretation_points = []
    if blocked_fwd60 is not None and opened_fwd60 is not None:
        if blocked_fwd60 < opened_fwd60 * 0.5 or (opened_fwd60 > 0 and blocked_fwd60 < 0):
            interpretation_points.append(
                "BLOCKED (cooldown) mostra un forward return mediano a 60 barre "
                f"({blocked_fwd60}) sostanzialmente PEGGIORE di OPENED ({opened_fwd60}) - "
                "compatibile con un gate che filtra CAUSALMENTE eventi peggiori (ma N "
                f"={summary['BLOCKED']['n']} e' piccolo, cautela richiesta).")
        elif abs(blocked_fwd60 - opened_fwd60) < 0.2 * abs(opened_fwd60 or 1):
            interpretation_points.append(
                "BLOCKED (cooldown) mostra un forward return mediano simile a OPENED - "
                "compatibile con un filtro CASUALE rispetto all'esito (il cooldown "
                "sopprime eventi non sistematicamente diversi dagli eseguiti).")
        else:
            interpretation_points.append(
                "BLOCKED (cooldown) mostra un forward return mediano MIGLIORE di OPENED - "
                "possibile indicazione che il gate di cooldown elimina ANCHE eventi "
                f"potenzialmente migliori (N={summary['BLOCKED']['n']}, cautela richiesta).")
    if reject_fwd60 is not None and opened_fwd60 is not None:
        interpretation_points.append(
            f"BROKER_REJECT: forward return mediano controfattuale={reject_fwd60} vs "
            f"OPENED={opened_fwd60} (N={summary['BROKER_REJECT']['n']}) - questi eventi "
            "sono rifiutati dal broker (non da un gate strategico), quindi qualunque "
            "differenza qui riflette la geometria dei segnali che tendono a essere "
            "rifiutati (es. spread/margine), non un giudizio sulla qualita' del segnale.")

    return {
        "phase": "7.9I",
        "purpose": "Diagnostica dei gate - NON proposta di modifica. Confronto fra il path "
            "REALE degli eventi OPENED e il path CONTROFATTUALE (proxy, mai eseguito) di "
            "BLOCKED e BROKER_REJECT.",
        "method": "Per BLOCKED/BROKER_REJECT, il prezzo di chiusura della barra di breakout "
            "(c1, causalmente disponibile per costruzione, stessa fonte usata per la "
            "magnitudine del breakout in Edge Decomposition) e' usato come proxy di "
            "ingresso - MAI un fill reale, questi eventi non sono mai stati eseguiti. "
            "Stessa metodologia di path anatomy (MFE/MAE/forward return a 60 barre D1) "
            "usata per gli OPENED reali, per un confronto comparabile 1:1.",
        "counterfactual_disclaimer": "Questi NON sono trade reali - nessuna decisione di "
            "modifica del gate deve basarsi su questi numeri da soli (N piccoli, nessuna "
            "esecuzione reale, nessuno slippage/costo simulato).",
        "by_stage": summary,
        "interpretation": interpretation_points,
        "sample_size_caveat": (
            f"BLOCKED n={summary['BLOCKED']['n']}, BROKER_REJECT n={summary['BROKER_REJECT']['n']} "
            "- entrambi troppo piccoli per una conclusione statisticamente forte; il "
            "campione e' compatibile con piu' di una delle tre ipotesi (filtro causale, "
            "filtro casuale, eliminazione di eventi migliori) - non decidibile con questi N."
        ),
    }


def main():
    payload = build()
    doc = wrap_with_provenance(payload, os.path.basename(__file__))
    save_json(os.path.join(PHASE79I_DIR, "breakout_acc_gate_diagnostic_v1.json"), doc)
    print(f"canonical_sha256={doc['canonical_sha256']}")
    for k, v in payload["by_stage"].items():
        print(k, v["n"], v.get("pct_continuation"), v["fwd_return_60d1"].get("median"))
    return doc


if __name__ == "__main__":
    main()
