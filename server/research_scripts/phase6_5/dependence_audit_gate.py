#!/usr/bin/env python3
"""Phase 6.5 sec.9 - Automated Gate: DEPENDENCE_AUDIT_PASS.

Un futuro edge test (qualunque H00N) non puo' essere dichiarato
conclusivo (PASS/FAIL/BORDERLINE con peso probatorio) senza aver
prodotto, come minimo:
  1. dependence diagnostics (Event Dependence Model, sec.1) - n_nominal,
     n_clusters, largest_cluster, dependence_flag;
  2. overlap diagnostics (sec.6) - overlap_rate, classificazione;
  3. un metodo di incertezza appropriato alla dipendenza trovata -
     se dependence_flag != LOW, serve ALMENO un intervallo
     dependence-aware (block/stationary bootstrap), non solo Wilson/iid.

Uso: validate_record(record_dict) -> (verdict, missing_reasons).
Questo gate NON giudica il MERITO del risultato (non decide se
l'edge e' vero) - giudica solo se il risultato e' stato accompagnato
dalla strumentazione minima richiesta per essere preso sul serio.
"""
import json
import os

REQUIRED_FIELDS = [
    "n_nominal",
    "n_effective",
    "event_clusters",
    "overlap_rate",
    "iid_uncertainty",
    "dependence_aware_uncertainty",
    "baseline_method",
    "direction_specific_baseline_status",
]


def validate_record(record: dict):
    missing = []
    for f in REQUIRED_FIELDS:
        if f not in record or record[f] is None:
            missing.append(f"campo mancante: {f}")

    dependence_flag = record.get("dependence_flag")
    if dependence_flag and dependence_flag != "LOW":
        if "grade_cap_reason" not in record or not record.get("grade_cap_reason"):
            missing.append("dependence_flag != LOW ma grade_cap_reason assente/vuoto")
        dep_unc = record.get("dependence_aware_uncertainty")
        if not dep_unc or not isinstance(dep_unc, dict) or "ci_low" not in dep_unc:
            missing.append("dependence_flag != LOW ma dependence_aware_uncertainty assente o incompleto")

    verdict = "DEPENDENCE_AUDIT_PASS" if not missing else "DEPENDENCE_AUDIT_FAIL"
    return verdict, missing


if __name__ == "__main__":
    PHASE65_DIR = os.path.dirname(os.path.abspath(__file__))
    schema = json.load(open(os.path.join(PHASE65_DIR, "evidence_engine_v2_schema.json"), encoding="utf-8"))
    record = dict(schema["worked_example_H006"])
    record["dependence_flag"] = "HIGH"  # dal dependence audit di H006 (sec.1)

    verdict, missing = validate_record(record)
    result = {"tested_record": record["hypothesis_id"], "verdict": verdict, "missing_or_invalid": missing}
    out_path = os.path.join(PHASE65_DIR, "dependence_audit_gate_result_H006.json")
    json.dump(result, open(out_path, "w", encoding="utf-8"), indent=2, default=str)
    print(json.dumps(result, indent=2, default=str))
    print(f"\nwritten: {out_path}")
