#!/usr/bin/env python3
"""Phase 7.1 Integrity & Provenance Patch (post-review, 2026-09-19) -
sec.2: validation_access_log_p71.json vive sotto phase7_1/data/, una
directory ESCLUSA da git (.gitignore: 'data/') - non verificabile dal
commit. Questo script deriva un artifact CANONICO E VERSIONATO dal
ledger REALE locale (mai inventato), cosi' l'evidenza di quali split
sono stati letti resta ispezionabile anche solo dal repository, senza
accesso alla macchina che ha eseguito la run.
"""
import json
import os
import sys
from collections import defaultdict
from datetime import datetime, timezone

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", ".."))
PHASE7_DIR = os.path.join(ROOT, "server", "research_scripts", "phase7")
DATA_DIR = os.path.join(PHASE7_DIR, "phase7_1", "data")
LEDGER_PATH = os.path.join(DATA_DIR, "validation_access_log_p71.json")
FROZEN_SPEC_PATH = os.path.join(PHASE7_DIR, "phase7_1", "phase7_1_frozen_spec_v1.json")
sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase6_6"))
from canonical_utils import wrap_with_provenance, save_json, canonical_sha256  # noqa: E402

TRACKED_SPLITS = ["internal_validation", "locked_validation", "final_holdout"]


def summarize_ledger(ledger_log: list) -> dict:
    """Funzione PURA (nessun I/O) che deriva conteggi/verdetto da una
    lista di record di ledger - separata da main() per essere testabile
    con dati sintetici (Integrity & Provenance Patch, sec.4: 'validation
    access evidence derivato da ledger vuoto')."""
    counts_by_split = {split: defaultdict(int) for split in TRACKED_SPLITS}
    access_records = []
    for rec in ledger_log:
        split = rec.get("split")
        cid = rec.get("candidate_id")
        access_records.append({"access_id": rec.get("access_id"), "candidate_id": cid, "split": split,
                                "timestamp": rec.get("timestamp"), "purpose": rec.get("purpose")})
        if split in counts_by_split:
            counts_by_split[split][cid] += 1
    total_by_split = {split: sum(counts_by_split[split].values()) for split in TRACKED_SPLITS}
    no_validation_split_consumed = all(total_by_split[s] == 0 for s in TRACKED_SPLITS)
    return {
        "access_records": access_records,
        "counts_by_split": {s: dict(counts_by_split[s]) for s in TRACKED_SPLITS},
        "total_by_split": total_by_split,
        "verdict": "NO_VALIDATION_SPLIT_CONSUMED" if no_validation_split_consumed else "VALIDATION_SPLIT_ACCESSED",
    }


def main():
    with open(FROZEN_SPEC_PATH, encoding="utf-8") as f:
        spec = json.load(f)
    candidate_ids = [c["candidate_id"] for c in spec["candidate_family_FROZEN"]["candidates"]]
    run_id = spec["run_id"]

    if os.path.exists(LEDGER_PATH):
        with open(LEDGER_PATH, encoding="utf-8") as f:
            ledger_log = json.load(f)
        ledger_present = True
    else:
        ledger_log = []
        ledger_present = False

    ledger_hash = canonical_sha256(ledger_log)
    summary = summarize_ledger(ledger_log)
    total_by_split = summary["total_by_split"]

    payload = {
        "run_id": run_id,
        "candidate_ids": candidate_ids,
        "ledger_source_path": "server/research_scripts/phase7/phase7_1/data/validation_access_log_p71.json (gitignored - derivato qui, non ricostruito)",
        "ledger_present_on_disk_at_build_time": ledger_present,
        "ledger_content_hash": ledger_hash,
        "ledger_raw_records": summary["access_records"],
        "discovery_access_summary": {
            "access_mode": "ITERABLE (validation_access_policy_v1.json) - non tracciato dal ledger per policy",
            "n_candidates_screened_at_discovery": len(candidate_ids),
            "note": "Ogni candidato e' stato calcolato una volta su development.discovery - lo split discovery non passa per ValidationAccessLedger (nessun limite previsto dalla policy), quindi non compare come 'accesso' nel ledger.",
        },
        "internal_validation_access_count_by_candidate": summary["counts_by_split"]["internal_validation"],
        "locked_validation_access_count_by_candidate": summary["counts_by_split"]["locked_validation"],
        "final_holdout_access_count_by_candidate": summary["counts_by_split"]["final_holdout"],
        "internal_validation_access_count_total": total_by_split["internal_validation"],
        "locked_validation_access_count_total": total_by_split["locked_validation"],
        "final_holdout_access_count_total": total_by_split["final_holdout"],
        "verdict": summary["verdict"],
        "verdict_basis": "Derivato meccanicamente dal conteggio di accessi per split nel ledger reale - non dichiarato, calcolato.",
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
    out_path = os.path.join(PHASE7_DIR, "phase7_1", "phase7_1_validation_access_evidence_v1.json")
    save_json(out_path, wrap_with_provenance(payload, "phase7/phase7_1/build_validation_access_evidence.py"))
    print(json.dumps(payload, indent=2, default=str, ensure_ascii=False))
    print(f"\nwritten: {out_path}")
    return payload


def _self_test():
    """Regression test (Integrity & Provenance Patch sec.4): la logica di
    derivazione deve dare NO_VALIDATION_SPLIT_CONSUMED su un ledger vuoto
    E deve correttamente contare accessi reali su un ledger sintetico non
    vuoto - prova che il verdetto e' calcolato, non semplicemente sempre
    'vuoto per default'."""
    empty_summary = summarize_ledger([])
    assert empty_summary["verdict"] == "NO_VALIDATION_SPLIT_CONSUMED"
    assert all(v == 0 for v in empty_summary["total_by_split"].values())
    print("Self-test 1 (ledger vuoto) -> NO_VALIDATION_SPLIT_CONSUMED: OK")

    synthetic_ledger = [
        {"access_id": "ACC-000001", "candidate_id": "CAND-X", "split": "internal_validation",
         "timestamp": "2026-01-01T00:00:00Z", "purpose": "test"},
        {"access_id": "ACC-000002", "candidate_id": "CAND-X", "split": "locked_validation",
         "timestamp": "2026-01-02T00:00:00Z", "purpose": "test"},
    ]
    non_empty_summary = summarize_ledger(synthetic_ledger)
    assert non_empty_summary["verdict"] == "VALIDATION_SPLIT_ACCESSED"
    assert non_empty_summary["total_by_split"]["internal_validation"] == 1
    assert non_empty_summary["total_by_split"]["locked_validation"] == 1
    assert non_empty_summary["total_by_split"]["final_holdout"] == 0
    assert non_empty_summary["counts_by_split"]["internal_validation"] == {"CAND-X": 1}
    print("Self-test 2 (ledger sintetico non vuoto) -> conteggi corretti, VALIDATION_SPLIT_ACCESSED: OK")


if __name__ == "__main__":
    _self_test()
    main()
