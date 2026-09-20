#!/usr/bin/env python3
"""Phase 7.4A Structural Verdict Semantics Patch - regression tests.
Verifica che nessun artifact affermi un'impossibilita' universale del
design (claim non dimostrato) e che la semantica della direction del
baseline sia etichettata correttamente. Nessun dato NEXUS, nessun
outcome, nessuna nuova esecuzione su dati reali."""
import json
import os
import re
import sys

PHASE74_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(PHASE74_DIR, "..", "..", "..", ".."))

RESULTS = []

# Frasi che affermerebbero un'impossibilita' universale (non dimostrata dai dati -
# l'evidenza disponibile riguarda SOLO la partition preregistrata attuale).
BANNED_OVERCLAIM_PHRASES = [
    "indipendentemente dalla quantita' di dati",
    "indipendentemente da quanti dati",
    "non puo' mai produrre",
    "non può mai produrre",
    "impossible regardless of additional data",
    "structurally_non_viable_under_frozen_spec",  # vecchio status value, sostituito
]
# Campi/paragrafi ESPLICITAMENTE dedicati a SPIEGARE la correzione - qui e' legittimo
# menzionare le frasi vietate per negarle (allowlist, stesso pattern di
# structural_audit_outcome_guard.py per return_direction/roc).
ALLOWLISTED_JSON_KEYS = {"not_a_universal_impossibility_claim"}
CORRECTION_PARAGRAPH_MARKERS = ["correzione esplicita", "correzione ("]


def check(name, condition, detail=""):
    status = "PASS" if condition else "FAIL"
    RESULTS.append({"check": name, "status": status})
    print(f"[{status}] {name} {('- ' + detail) if detail else ''}")
    return condition


def scan_json_for_banned_overclaims(obj, path=""):
    violations = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k in ALLOWLISTED_JSON_KEYS:
                continue
            violations.extend(scan_json_for_banned_overclaims(v, f"{path}.{k}"))
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            violations.extend(scan_json_for_banned_overclaims(v, f"{path}[{i}]"))
    elif isinstance(obj, str):
        low = obj.lower()
        for phrase in BANNED_OVERCLAIM_PHRASES:
            if phrase.lower() in low:
                violations.append((path, phrase))
    return violations


def scan_text_for_banned_overclaims_outside_correction_paragraphs(text):
    paragraphs = re.split(r"\n\s*\n", text)
    violations = []
    for i, para in enumerate(paragraphs):
        para_low = para.lower()
        if any(marker in para_low for marker in CORRECTION_PARAGRAPH_MARKERS):
            continue  # paragrafo di correzione - puo' legittimamente menzionare/negare la frase vietata
        for phrase in BANNED_OVERCLAIM_PHRASES:
            if phrase.lower() in para_low:
                violations.append((i, phrase))
    return violations


def test_structural_failure_artifact_no_overclaim():
    with open(os.path.join(PHASE74_DIR, "phase7_4_seq0015_structural_failure_v1.json"), encoding="utf-8") as f:
        artifact = json.load(f)
    violations = scan_json_for_banned_overclaims(artifact)
    check("structural_failure_artifact_has_no_universal_impossibility_claim", len(violations) == 0,
          f"violazioni={violations}" if violations else "")
    check("structural_failure_status_is_precise_not_universal",
          artifact["SEQ0015_STATUS"] == "FROZEN_EXPERIMENT_NOT_TESTABLE_ON_PREREGISTERED_DISCOVERY_PARTITION",
          f"status={artifact['SEQ0015_STATUS']}")
    check("structural_failure_has_explicit_non_universal_disclaimer", "not_a_universal_impossibility_claim" in artifact)


def test_failure_memory_fail009_no_overclaim():
    with open(os.path.join(ROOT, "server", "research_scripts", "phase7", "failure_memory_registry_v1.json"), encoding="utf-8") as f:
        registry = json.load(f)
    fail009 = next(p for p in registry["patterns"] if p["pattern_id"] == "FAIL-009")
    # FAIL-009 e' un caso interessante: la SUA descrizione contiene legittimamente una
    # frase di correzione esplicita (paragrafo con 'CORREZIONE ESPLICITA') che menziona
    # le frasi vietate per negarle - controlliamo quindi a livello di PARAGRAFO, non di
    # intero campo (a differenza dell'artifact strutturale che isola la correzione in
    # un campo dedicato).
    violations = scan_text_for_banned_overclaims_outside_correction_paragraphs(fail009["description"])
    check("fail009_no_overclaim_outside_correction_paragraph", len(violations) == 0, f"violazioni={violations}" if violations else "")
    check("fail009_signature_updated", fail009["signature"] == "INDEPENDENT_VIEW_COLLAPSE_ON_PREREGISTERED_PARTITION",
          f"signature={fail009['signature']}")


def test_candidate_lifecycle_docstring_no_overclaim():
    with open(os.path.join(ROOT, "server", "research_scripts", "phase7", "engine", "candidate_lifecycle.py"), encoding="utf-8") as f:
        content = f.read()
    docstring_match = re.search(r'"""(.*?)"""', content, re.DOTALL)
    check("candidate_lifecycle_docstring_found", docstring_match is not None)
    if docstring_match:
        violations = scan_text_for_banned_overclaims_outside_correction_paragraphs(docstring_match.group(1))
        check("candidate_lifecycle_docstring_no_overclaim_outside_correction", len(violations) == 0,
              f"violazioni={violations}" if violations else "")


def test_direction_semantics_documented():
    with open(os.path.join(ROOT, "server", "research_scripts", "phase7", "phase7_3", "sequence_baseline_adapter_v1.py"), encoding="utf-8") as f:
        content = f.read()
    check("direction_counterfactual_label_present", "direction-conditioned counterfactual" in content.lower() or "COUNTERFACTUAL" in content)
    check("direction_not_described_as_independently_observed",
          "osservata indipendentemente" in content or "independently observed" in content.lower(),
          "deve esistere una frase che CHIARISCE la distinzione (non basta l'assenza)")
    # Verifica comportamentale: il codice deve ancora assegnare la direzione dell'evento
    # a TUTTI i controlli (comportamento INVARIATO - solo la documentazione e' cambiata).
    check("control_direction_still_assigned_from_event_direction",
          "control_direction_by_id = {cid: direction for cid in control_pool_same_split}" in content)


def test_structural_failure_artifact_evidence_scoped_to_partition():
    with open(os.path.join(PHASE74_DIR, "phase7_4_seq0015_structural_failure_v1.json"), encoding="utf-8") as f:
        artifact = json.load(f)
    check("shortfall_mentions_partition_scope", "partition" in artifact["evidence"]["shortfall"].lower())
    check("no_rescue_mentions_new_preregistration_not_extension",
          "nuovo esperimento" in artifact["no_rescue_applied"].lower() or "nuova preregistrazione" in artifact["no_rescue_applied"].lower())


def test_no_v5_and_frozen_files_untouched():
    check("no_frozen_spec_v5_created", not os.path.exists(os.path.join(PHASE74_DIR, "phase7_4_seq0015_frozen_spec_v5.json")))
    for v in ["v1", "v2", "v3", "v4"]:
        check(f"frozen_spec_{v}_still_exists", os.path.exists(os.path.join(PHASE74_DIR, f"phase7_4_seq0015_frozen_spec_{v}.json")))
    detector_path = os.path.join(PHASE74_DIR, "seq0015_momentum_burst_detector.py")
    with open(detector_path, encoding="utf-8") as f:
        content = f.read()
    check("detector_still_v1_unchanged", 'DETECTOR_VERSION = "seq0015_momentum_burst_detector.py@v1"' in content)


def test_overall_verdict_unchanged():
    with open(os.path.join(PHASE74_DIR, "phase7_4_dependence_aware_method_selection_v1.json"), encoding="utf-8") as f:
        sel = json.load(f)
    check("primary_inference_method_still_not_yet_validated", sel["verdict"] == "PRIMARY INFERENCE METHOD NOT YET VALIDATED")
    with open(os.path.join(PHASE74_DIR, "phase7_4_baseline_matching_integrity_patch_v1.json"), encoding="utf-8") as f:
        engine = json.load(f)
    check("baseline_engine_status_still_fixed", engine["BASELINE_ENGINE_STATUS"] == "FIXED")


def main():
    test_structural_failure_artifact_no_overclaim()
    test_failure_memory_fail009_no_overclaim()
    test_candidate_lifecycle_docstring_no_overclaim()
    test_direction_semantics_documented()
    test_structural_failure_artifact_evidence_scoped_to_partition()
    test_no_v5_and_frozen_files_untouched()
    test_overall_verdict_unchanged()

    n_pass = sum(1 for r in RESULTS if r["status"] == "PASS")
    n_fail = len(RESULTS) - n_pass
    print(f"\n=== Phase 7.4A Structural Verdict Semantics regression suite: {n_pass} PASS, {n_fail} FAIL su {len(RESULTS)} check ===")
    return n_fail == 0


if __name__ == "__main__":
    ok = main()
    sys.exit(0 if ok else 1)
