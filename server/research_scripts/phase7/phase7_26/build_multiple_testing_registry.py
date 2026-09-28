#!/usr/bin/env python3
"""Phase 7.26 punto M - protezione dal multiple testing. Non fa
inferenza corretta (nessuna correzione di p-value applicata in questa
fase - dichiarato) - registra SOLO i conteggi minimi richiesti dal
task, cosi' un domani "100 tentativi casuali" non possano produrre un
falso edge che sembra speciale senza che il conteggio lo rifletta."""
import os
import sys
from collections import Counter

PHASE726_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(PHASE726_DIR, "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase6_6"))
from canonical_utils import wrap_with_provenance, save_json, load_json  # noqa: E402


def build():
    hyp = load_json(os.path.join(PHASE726_DIR, "hypothesis_registry_v1.json"))["payload"]
    exp = load_json(os.path.join(PHASE726_DIR, "experiment_registry_v1.json"))["payload"]
    exposure = load_json(os.path.join(PHASE726_DIR, "data_exposure_registry_v1.json"))["payload"]

    n_hypotheses = hyp["n_hypotheses"]
    n_strategies = len(set(s for h in hyp["hypotheses"] for s in h["originating_strategies"]))
    n_experiments = exp["n_experiments"]
    n_datasets = exposure["n_records"]

    dataset_experiment_count = Counter(e["dataset_id"] for e in exp["experiments"])
    reused_datasets = {d: n for d, n in dataset_experiment_count.items() if n > 1}

    validation_dataset_count = Counter()
    for h in hyp["hypotheses"]:
        for d in h["validation_dataset_ids"]:
            validation_dataset_count[d] += 1
    reused_as_validation = {d: n for d, n in validation_dataset_count.items() if n > 1}

    oos_dataset_ids = [r["dataset_id"] for r in exposure["records"] if r.get("oos_exposure")]
    n_oos_windows_consumed = len(oos_dataset_ids)

    payload = {
        "n_hypotheses_tested": n_hypotheses,
        "n_strategies_variants_tested": n_strategies,
        "n_experiments_run": n_experiments,
        "n_datasets_registered": n_datasets,
        "datasets_reused_across_multiple_experiments": reused_datasets,
        "datasets_reused_as_validation_for_multiple_hypotheses": reused_as_validation,
        "n_oos_holdout_windows_consumed": n_oos_windows_consumed,
        "oos_holdout_window_ids": oos_dataset_ids,
        "no_p_value_correction_applied_this_phase": True,
        "purpose": "Non e' inferenza statistica corretta (nessuna correzione multiple-comparison "
                  "applicata) - e' un CONTEGGIO dichiarato per rendere visibile, in futuro, se il "
                  "numero di ipotesi/varianti testate cresce piu' velocemente delle evidenze "
                  "indipendenti disponibili (segnale di allarme precoce, non una correzione "
                  "formale).",
        "warning_threshold_note": "Con 8 hypotheses testate su 4 strategie e un solo dataset OOS "
                                 "indipendente per strategia, il rapporto hypotheses/OOS_indipendenti "
                                 f"e' {n_hypotheses}/{n_oos_windows_consumed} - se questo rapporto "
                                 "continua a crescere senza nuovi holdout, la fiducia in qualunque "
                                 "singolo 'edge trovato' futuro va scontata di conseguenza "
                                 "(dichiarato qui, non ancora applicato come correzione numerica).",
    }
    return payload


def main():
    payload = build()
    doc = wrap_with_provenance(payload, script=os.path.abspath(__file__))
    out_path = os.path.join(PHASE726_DIR, "multiple_testing_registry_v1.json")
    save_json(out_path, doc)
    print(f"Scritto {out_path} (sha256={doc['canonical_sha256'][:16]}...)")
    print(f"  hypotheses={payload['n_hypotheses_tested']} experiments={payload['n_experiments_run']} "
         f"oos_windows={payload['n_oos_holdout_windows_consumed']}")


if __name__ == "__main__":
    main()
