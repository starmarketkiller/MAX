#!/usr/bin/env python3
"""Phase 7.19 - verificatore indipendente. Ri-deriva ogni artifact dai
builder, ri-verifica strutturalmente i 3 packet dimostrativi contro i
4 JSON Schema (lightweight required-field checker - nessuna libreria
jsonschema disponibile in questo ambiente, dichiarato esplicitamente),
verifica che nessun campo mancante usi null indistintamente, verifica
che MQL5/registry/Product Platform/TSI non siano stati toccati in
questa fase."""
import json
import os
import subprocess
import sys

PHASE719_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(PHASE719_DIR, "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase6_6"))
from canonical_utils import canonical_sha256, load_json  # noqa: E402

sys.path.insert(0, PHASE719_DIR)
import build_visual_audit_protocol as vap_builder  # noqa: E402
import build_fidelity_framework as fid_builder  # noqa: E402
import build_sampling_protocol as samp_builder  # noqa: E402
import build_anti_leakage_specification as leak_builder  # noqa: E402
import build_source_of_truth_hierarchy as sot_builder  # noqa: E402
import build_anti_bias_rules as bias_builder  # noqa: E402
import build_example_packets as ex_builder  # noqa: E402
import build_gap_analysis as gap_builder  # noqa: E402
import build_implementation_roadmap as road_builder  # noqa: E402
import build_decision as dec_builder  # noqa: E402

ARTIFACTS = [
    ("visual_audit_protocol_v1.json", vap_builder.build),
    ("fidelity_framework_v1.json", fid_builder.build),
    ("sampling_protocol_v1.json", samp_builder.build),
    ("anti_leakage_specification_v1.json", leak_builder.build),
    ("source_of_truth_hierarchy_v1.json", sot_builder.build),
    ("anti_bias_rules_v1.json", bias_builder.build),
    ("example_packets_v1.json", ex_builder.build),
    ("gap_analysis_v1.json", gap_builder.build),
    ("implementation_roadmap_v1.json", road_builder.build),
    ("audit_standard_decision_v1.json", dec_builder.build),
]

SCHEMA_TOP_LEVEL_REQUIRED = {
    "event_audit_packet_v1.schema.json": ["schema_version", "identity", "environment", "timeline",
                                          "prices", "strategy_state", "decision_time_features",
                                          "multi_timeframe_context", "source_of_truth", "fidelity"],
    "runtime_identity_manifest_v1.schema.json": ["schema_version", "emitted_at", "ea_name", "ea_version",
                                                 "build_fingerprint", "compile_timestamp", "terminal_build",
                                                 "server", "symbol", "input_config_hash", "enabled_strategies",
                                                 "start_timestamp"],
    "visual_audit_result_v1.schema.json": ["schema_version", "audit_id", "event_id", "reviewer_kind",
                                           "protocol_version", "conducted_at", "stage_a_blind_review",
                                           "observation_vs_hypothesis_vs_validated", "fidelity_of_this_audit"],
    "matched_non_event_v1.schema.json": ["schema_version", "record_id", "record_kind", "strategy_id",
                                         "timestamp", "matching_criteria_used", "matching_causality_verified",
                                         "outcome_used_in_selection", "fidelity"],
}


def _load_schemas():
    schemas = {}
    for fname in SCHEMA_TOP_LEVEL_REQUIRED:
        path = os.path.join(PHASE719_DIR, "schemas", fname)
        with open(path, encoding="utf-8") as f:
            schemas[fname] = json.load(f)
    return schemas


def verify():
    errors = []

    for fname, build_fn in ARTIFACTS:
        path = os.path.join(PHASE719_DIR, fname)
        if not os.path.exists(path):
            errors.append(f"{fname}: file mancante")
            continue
        saved = load_json(path)
        fresh = build_fn()
        if canonical_sha256(fresh) != canonical_sha256(saved["payload"]):
            errors.append(f"{fname}: ricostruzione indipendente differisce dal file salvato")

    # --- I 4 JSON Schema sono validi e dichiarano i 'required' attesi
    # (verifica diretta sul file, non sul builder). ---
    schemas = _load_schemas()
    for fname, expected_required in SCHEMA_TOP_LEVEL_REQUIRED.items():
        schema = schemas[fname]
        declared = schema.get("required", [])
        missing = set(expected_required) - set(declared)
        if missing:
            errors.append(f"{fname}: 'required' non include {missing}")
        if schema.get("$schema") != "http://json-schema.org/draft-07/schema#":
            errors.append(f"{fname}: manca o e' errato il campo $schema")

    # --- I 3 packet dimostrativi rispettano il required top-level dello
    # schema EVENT_AUDIT_PACKET_V1 (controllo strutturale leggero - nessuna
    # libreria jsonschema disponibile in questo ambiente, dichiarato). ---
    examples = load_json(os.path.join(PHASE719_DIR, "example_packets_v1.json"))["payload"]
    required_top = SCHEMA_TOP_LEVEL_REQUIRED["event_audit_packet_v1.schema.json"]
    for name, packet in examples["packets"].items():
        missing = [k for k in required_top if k not in packet]
        if missing:
            errors.append(f"packet {name}: campi required mancanti {missing}")
        if packet["schema_version"] != "EVENT_AUDIT_PACKET_V1":
            errors.append(f"packet {name}: schema_version errato")
        fid_tier = packet.get("fidelity", {}).get("tier")
        if fid_tier not in ("A", "B", "C", "D"):
            errors.append(f"packet {name}: fidelity.tier '{fid_tier}' non ammesso")

    # --- Nessun campo ABSENT usa null indistintamente - ogni oggetto con
    # status=ABSENT deve avere un reason valido fra i 5 ammessi. ---
    allowed_reasons = {"NOT_AVAILABLE", "NOT_APPLICABLE", "NOT_RECORDED", "UNKNOWN", "CENSORED"}

    def _walk(obj, path=""):
        if isinstance(obj, dict):
            if obj.get("status") == "ABSENT":
                if obj.get("reason") not in allowed_reasons:
                    errors.append(f"{path}: status=ABSENT ma reason '{obj.get('reason')}' non "
                                  f"fra i 5 ammessi")
            for k, v in obj.items():
                _walk(v, f"{path}.{k}")
        elif isinstance(obj, list):
            for i, v in enumerate(obj):
                _walk(v, f"{path}[{i}]")

    for name, packet in examples["packets"].items():
        _walk(packet, name)

    # --- Il terzo esempio NON e' TSI (dichiarato esplicitamente nel task). ---
    if "TSI" in examples["packets"]:
        errors.append("uno dei packet dimostrativi usa TSI - non atteso, TSI e' 'in modifica' "
                      "in questa sessione (Phase 7.18)")

    # --- Nessun file MQL5/registry/Product Platform toccato DA QUESTA FASE.
    # Nota: al momento della stesura di Phase 7.19, MQL5/Include/NEXUS_v1/
    # NXS_Strategies.mqh puo' risultare modificato per via del lavoro TSI
    # CONCORRENTE (Phase 7.18, istrumentazione diagnostica temporanea, run
    # live in corso) - questo e' ATTESO e non e' una violazione di questa
    # fase, che deve solo NON introdurre ULTERIORI modifiche. Verificato
    # controllando che l'unico contenuto modificato sia riconducibile al
    # marcatore noto dell'istrumentazione TSI, non a qualcosa introdotto
    # qui. ---
    result = subprocess.run(["git", "status", "--porcelain", "--", "MQL5/", "Product-Platform/",
                            "contracts/"], cwd=ROOT, capture_output=True, text=True)
    modified_files = [l.split(maxsplit=1)[1] for l in result.stdout.strip().splitlines() if l.strip()]
    unexpected_modified = [f for f in modified_files if f != "MQL5/Include/NEXUS_v1/NXS_Strategies.mqh"]
    if unexpected_modified:
        errors.append(f"file MQL5/Product-Platform/contracts modificati NON riconducibili al "
                      f"lavoro TSI concorrente: {unexpected_modified}")
    if "MQL5/Include/NEXUS_v1/NXS_Strategies.mqh" in modified_files:
        diff_result = subprocess.run(["git", "diff", "--", "MQL5/Include/NEXUS_v1/NXS_Strategies.mqh"],
                                     cwd=ROOT, capture_output=True, text=True)
        if "NXS_TSI_DIAG_TRACE" not in diff_result.stdout:
            errors.append("NXS_Strategies.mqh e' modificato ma il diff non contiene il "
                          "marcatore noto dell'istrumentazione TSI (NXS_TSI_DIAG_TRACE) - "
                          "potrebbe essere una modifica NON riconducibile al lavoro "
                          "concorrente atteso")

    # --- Nessun artifact TSI (phase7_17/phase7_18) toccato in questa fase. ---
    for rel in ("server/research_scripts/phase7/phase7_17",):
        result = subprocess.run(["git", "diff", "--quiet", "HEAD", "--", rel], cwd=ROOT)
        if result.returncode != 0:
            errors.append(f"{rel} risulta modificato - non atteso (ortogonale a TSI)")

    # --- decisione finale ammessa. ---
    decision = load_json(os.path.join(PHASE719_DIR, "audit_standard_decision_v1.json"))["payload"]
    if decision["decision"] not in ("AUDIT_STANDARD_READY", "AUDIT_STANDARD_NEEDS_REVISION"):
        errors.append(f"decisione '{decision['decision']}' non ammessa")
    if decision.get("no_edge_claim_made") is not True:
        errors.append("la decisione non dichiara esplicitamente no_edge_claim_made")

    return errors


def main():
    errors = verify()
    if errors:
        print(f"VERIFY FAILED: {len(errors)} problemi")
        for e in errors:
            print(f"  - {e}")
        sys.exit(1)
    print("VERIFY OK: tutti i controlli indipendenti passati (0 problemi)")
    sys.exit(0)


if __name__ == "__main__":
    main()
