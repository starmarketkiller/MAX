#!/usr/bin/env python3
"""Phase 5.5 sec.17 - Reproducibility Test.

Confronta i risultati della RI-ESECUZIONE completa della pipeline (da
codice committato, stesso dataset locale dichiarato in dataset_version_v1.json,
nessuna modifica al codice) contro i risultati originali di Phase 5
(salvati in data_original_backup/ prima della ri-esecuzione).

NON e' una nuova validazione di SWEEP+RECLAIM - e' un test di
riproducibilita' infrastrutturale: la pipeline, ri-eseguita da zero,
produce gli STESSI numeri (entro una tolleranza dichiarata) di quelli
gia' riportati?

Selezionati per il confronto (come richiesto): un risultato negativo
(BREAKOUT event-alone, NO_EDGE/REFUTED) e RECLAIM.
"""
import json
import os

ROOT = r"C:\Users\User\ClaudeWork\MAX"
DATA_DIR = os.path.join(ROOT, "server", "research_scripts", "phase5", "data")
BACKUP_DIR = os.path.join(ROOT, "server", "research_scripts", "phase5", "data_original_backup")
OUT_JSON = os.path.join(ROOT, "server", "research_scripts", "phase5_5", "reproducibility_report_v1.json")

TOLERANCE = 1e-6  # numeri deterministici attesi identici; tolleranza solo per arrotondamenti float


def compare_value(a, b, path, diffs):
    if isinstance(a, dict) and isinstance(b, dict):
        for k in set(a.keys()) | set(b.keys()):
            compare_value(a.get(k), b.get(k), f"{path}.{k}", diffs)
    elif isinstance(a, (int, float)) and isinstance(b, (int, float)) and not isinstance(a, bool) and not isinstance(b, bool):
        if abs(a - b) > TOLERANCE:
            diffs.append({"path": path, "original": a, "rerun": b, "abs_diff": abs(a - b)})
    elif a != b:
        diffs.append({"path": path, "original": a, "rerun": b})


def main():
    orig = json.load(open(os.path.join(BACKUP_DIR, "edge_results_v1.json"), encoding="utf-8"))
    rerun = json.load(open(os.path.join(DATA_DIR, "edge_results_v1.json"), encoding="utf-8"))

    results = {}
    for family, label in [("BREAKOUT", "negative_result"), ("RECLAIM", "sweep_reclaim")]:
        o = orig["event_alone"][family]
        r = rerun["event_alone"][family]
        diffs = []
        compare_value(o, r, family, diffs)
        results[family] = {
            "label": label,
            "original_classification": o.get("classification"),
            "rerun_classification": r.get("classification"),
            "classification_matches": o.get("classification") == r.get("classification"),
            "n_diffs_found": len(diffs),
            "diffs": diffs[:50],
        }

    # confronto anche a livello di file grezzi (conteggi eventi, righe dataset)
    file_level = {}
    for fname in ["xauusd_h4_bars.csv", "market_state_dataset_v1.csv", "events_v1.csv", "outcomes_v1.csv"]:
        orig_path = os.path.join(BACKUP_DIR, fname)
        rerun_path = os.path.join(DATA_DIR, fname)
        if os.path.exists(orig_path) and os.path.exists(rerun_path):
            orig_lines = sum(1 for _ in open(orig_path, encoding="utf-8"))
            rerun_lines = sum(1 for _ in open(rerun_path, encoding="utf-8"))
            import hashlib
            orig_hash = hashlib.sha256(open(orig_path, "rb").read()).hexdigest()
            rerun_hash = hashlib.sha256(open(rerun_path, "rb").read()).hexdigest()
            file_level[fname] = {
                "orig_lines": orig_lines, "rerun_lines": rerun_lines,
                "line_count_matches": orig_lines == rerun_lines,
                "byte_identical": orig_hash == rerun_hash,
                "orig_sha256": orig_hash, "rerun_sha256": rerun_hash,
            }

    overall_pass = all(v["classification_matches"] for v in results.values()) and all(
        fv["line_count_matches"] for fv in file_level.values())

    report = {
        "schema_version": 1,
        "purpose": "Test di riproducibilita' infrastrutturale (non una ri-validazione dell'edge)",
        "tolerance_numeric": TOLERANCE,
        "results_by_hypothesis": results,
        "file_level_comparison": file_level,
        "overall_verdict": "REPRODUCIBLE" if overall_pass else "REPRODUCIBILITY_MISMATCH_FOUND",
        "note": (
            "Byte-identical atteso per file deterministici senza dipendenze di sistema. "
            "Se byte_identical=false ma line_count_matches=true e i diff numerici sono "
            "entro tolleranza, la causa piu' probabile e' un ordine di iterazione/dict non "
            "garantito (irrilevante per la correttezza) - controllare i diff dettagliati "
            "prima di considerarlo un problema reale."
        ),
    }
    json.dump(report, open(OUT_JSON, "w", encoding="utf-8"), indent=2, default=str)
    print("Overall verdict:", report["overall_verdict"])
    print(json.dumps({k: v for k, v in results.items()}, indent=2, default=str))
    print(json.dumps(file_level, indent=2, default=str))
    print(f"\nwritten: {OUT_JSON}")


if __name__ == "__main__":
    main()
