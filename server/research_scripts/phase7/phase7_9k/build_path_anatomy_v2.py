#!/usr/bin/env python3
"""Phase 7.9K - Path Anatomy V2 (misurazione B, post-fill, 47 OPENED) +
confronto per-evento e aggregato prima/dopo (punto 4 della task)."""
import os
import statistics
import sys

PHASE79K_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(PHASE79K_DIR, "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase6_6"))
from canonical_utils import load_json, save_json, wrap_with_provenance  # noqa: E402

sys.path.insert(0, PHASE79K_DIR)
import nxs_forward_path_v2 as fp  # noqa: E402


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
    dataset = load_json(os.path.join(PHASE79K_DIR, "breakout_acc_intended_d1_v2_dataset.json"))["payload"]
    events = dataset["events"]
    opened = [e for e in events if e["funnel_terminal_stage"] == "OPENED"]

    DETERMINATE = ("CONTINUATION", "FAILURE")

    per_event = []
    n_outcome_flips = 0
    n_coverage_status_changes = 0
    n_comparable = 0
    for e in opened:
        v2 = e["measurement_B_post_fill_path"]
        v1 = e["post_entry_path_anatomy_V1_SUPERSEDED"]

        v2_fwd60 = v2["horizons"].get("fwd_return_60d1_price_units")
        v1_fwd60 = v1["horizons"].get("fwd_return_60d1_price_units") if v1 else None

        v2_cls = fp.classify_continuation_failure_v2(v2, 60)
        v1_cls = ("CONTINUATION" if v1_fwd60 and v1_fwd60 > 0 else
                 "FAILURE" if v1_fwd60 is not None else "UNKNOWN")

        # CORREZIONE: separare un vero cambio di ESITO (continuation<->failure, solo
        # fra eventi in cui ENTRAMBE le versioni producono una classificazione
        # determinata) da un cambio di STATO DI COPERTURA (una delle due versioni non
        # produce affatto un esito determinato - UNKNOWN in V1, UNKNOWN_CENSORED in
        # V2). Le due cose NON sono la stessa correzione e vanno riportate separate.
        comparable = v1_cls in DETERMINATE and v2_cls in DETERMINATE
        outcome_flip = comparable and v1_cls != v2_cls
        coverage_status_change = (not comparable) and (v1_cls != v2_cls)
        if comparable:
            n_comparable += 1
        if outcome_flip:
            n_outcome_flips += 1
        if coverage_status_change:
            n_coverage_status_changes += 1

        per_event.append({
            "event_id": e["event_id"], "direction_label": (
                "BUY" if e["direction"] == 1 else "SELL"),
            "d1_bar_date": e["d1_bar_date"],
            "v1_mfe": v1["mfe_price_units"] if v1 else None,
            "v2_mfe": v2.get("mfe_price_units"),
            "v1_mae": v1["mae_price_units"] if v1 else None,
            "v2_mae": v2.get("mae_price_units"),
            "v1_bars_to_mfe": v1["bars_to_mfe_d1"] if v1 else None,
            "v2_bars_to_mfe": v2.get("bars_to_mfe_d1"),
            "v1_bars_to_mae": v1["bars_to_mae_d1"] if v1 else None,
            "v2_bars_to_mae": v2.get("bars_to_mae_d1"),
            "v1_fwd_return_60d1": v1_fwd60,
            "v2_fwd_return_60d1": v2_fwd60,
            "v1_classification": v1_cls, "v2_classification": v2_cls,
            "comparable_v1_v2": comparable,
            "outcome_flip": outcome_flip,
            "coverage_status_change": coverage_status_change,
            "v2_status": v2.get("status"), "v2_coverage_bars": v2.get("coverage_bars"),
        })

    n_censored_60 = sum(1 for p in per_event if p["v2_status"] == "CENSORED_INSUFFICIENT_BARS")

    def agg(rows, key_v1, key_v2):
        return {"v1": _stats([r[key_v1] for r in rows]), "v2": _stats([r[key_v2] for r in rows])}

    aggregate_before_after = {
        "n_events": len(per_event),
        "n_censored_at_60_bars": n_censored_60,
        "n_comparable_v1_v2_both_determinate": n_comparable,
        "n_outcome_flips_continuation_vs_failure": n_outcome_flips,
        "n_outcome_flips_denominator": n_comparable,
        "n_coverage_status_changes": n_coverage_status_changes,
        "outcome_flip_breakdown": {
            "CONTINUATION_to_FAILURE": sum(1 for p in per_event if p["outcome_flip"]
                                           and p["v1_classification"] == "CONTINUATION"),
            "FAILURE_to_CONTINUATION": sum(1 for p in per_event if p["outcome_flip"]
                                           and p["v1_classification"] == "FAILURE"),
        },
        "mfe": agg(per_event, "v1_mfe", "v2_mfe"),
        "mae": agg(per_event, "v1_mae", "v2_mae"),
        "bars_to_mfe": agg(per_event, "v1_bars_to_mfe", "v2_bars_to_mfe"),
        "bars_to_mae": agg(per_event, "v1_bars_to_mae", "v2_bars_to_mae"),
        "fwd_return_60d1": agg(per_event, "v1_fwd_return_60d1", "v2_fwd_return_60d1"),
    }

    by_direction = {}
    for d in ("BUY", "SELL"):
        grp = [p for p in per_event if p["direction_label"] == d]
        n_cont_v1 = sum(1 for p in grp if p["v1_classification"] == "CONTINUATION")
        n_cont_v2 = sum(1 for p in grp if p["v2_classification"] == "CONTINUATION")
        n_censored = sum(1 for p in grp if p["v2_classification"] == "UNKNOWN_CENSORED")
        by_direction[d] = {
            "n": len(grp), "n_continuation_v1": n_cont_v1, "n_continuation_v2": n_cont_v2,
            "n_censored_v2": n_censored,
            "pct_continuation_v1": round(100 * n_cont_v1 / len(grp), 1) if grp else None,
            "pct_continuation_v2": round(100 * n_cont_v2 / (len(grp) - n_censored), 1)
                if (len(grp) - n_censored) > 0 else None,
            "denominator_v2_excludes_censored": len(grp) - n_censored,
        }

    return {
        "phase": "7.9K", "measurement": "B (post-fill, 47 OPENED, fill reale verificato)",
        "dataset_v2_sha256_reference": "vedi breakout_acc_intended_d1_v2_dataset.json",
        "per_event_before_after": per_event,
        "aggregate_before_after": aggregate_before_after,
        "by_direction_continuation_before_after": by_direction,
        "censoring_note": (
            f"{n_censored_60} evento/i con copertura <60 barre al momento del calcolo "
            "(vicino alla fine dello storico disponibile) - classificato UNKNOWN_CENSORED "
            "in V2. Denominatori per le percentuali di continuation ESCLUDONO "
            "esplicitamente i censurati."
        ),
        "outcome_flip_vs_coverage_status_change_note": (
            "CORREZIONE (revisione post-commit f70500a): dei 5 eventi con "
            "classificazione diversa fra V1 e V2, SOLO 4 sono veri cambi di ESITO "
            "(CONTINUATION<->FAILURE, fra eventi in cui ENTRAMBE le versioni producono "
            "una classificazione determinata) - 1 CONTINUATION->FAILURE, 3 "
            "FAILURE->CONTINUATION. Il quinto evento (2026.06.09) NON e' un cambio di "
            "esito: la sua classificazione V1 era GIA' 'UNKNOWN' (v1_fwd_return_60d1 = "
            "None, verificato nell'artifact stesso) - V1 non lo classificava come "
            "FAILURE, un'affermazione fatta erroneamente nel vault report originale di "
            "questa fase e qui corretta. Il difetto REALE di V1 su questo evento non "
            "era una classificazione sbagliata, ma l'ASSENZA di un campo di stato "
            "esplicito (coverage_bars/status) che dichiarasse ESPLICITAMENTE che MFE/"
            "MAE/bars_to_mfe/bars_to_mae per questo evento erano stati calcolati su una "
            "finestra INCOMPLETA (i valori numerici v1_mfe/v1_mae esistono comunque, "
            "calcolati silenziosamente su meno di 60 barre, senza segnalarlo) - V2 "
            "rende questo esplicito con 'status': 'CENSORED_INSUFFICIENT_BARS' e "
            "'coverage_bars': 51. Riportare questo come un 'quinto cambio di "
            "classificazione continuation/failure' (fatto nella prima versione di "
            "questo artifact) confondeva un cambio di STATO DI COPERTURA con un cambio "
            "di ESITO - corretto qui: vedere 'n_outcome_flips_continuation_vs_failure' "
            "(4, su un denominatore di 46 eventi comparabili) e "
            "'n_coverage_status_changes' (1) come campi separati."
        ),
    }


def main():
    payload = build()
    doc = wrap_with_provenance(payload, os.path.basename(__file__))
    save_json(os.path.join(PHASE79K_DIR, "breakout_acc_path_anatomy_v2.json"), doc)
    print(f"canonical_sha256={doc['canonical_sha256']}")
    agg = payload['aggregate_before_after']
    print(f"n_outcome_flips: {agg['n_outcome_flips_continuation_vs_failure']}/{agg['n_outcome_flips_denominator']}")
    print(f"n_coverage_status_changes: {agg['n_coverage_status_changes']}")
    print(f"n_censored: {payload['aggregate_before_after']['n_censored_at_60_bars']}")
    return doc


if __name__ == "__main__":
    main()
