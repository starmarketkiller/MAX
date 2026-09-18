#!/usr/bin/env python3
"""Phase 6.6 sec.11 - Integrity tests automatici sugli artifact canonici
di questa fase. Ogni check e' indipendente e riporta PASS/FAIL con un
messaggio - nessun check "aggiusta" silenziosamente un problema trovato.
"""
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from canonical_utils import ROOT, load_json  # noqa: E402

PHASE66_DIR = os.path.dirname(os.path.abspath(__file__))

RESULTS = []


def check(name, condition, detail=""):
    RESULTS.append({"check": name, "result": "PASS" if condition else "FAIL", "detail": detail})


def load(fname):
    return load_json(os.path.join(PHASE66_DIR, fname))


def main():
    evidence = load("h006_evidence_v2.json")["payload"]
    card = load("h006_decision_card_v2.json")["payload"]
    obs = load("post_hoc_observations_v1.json")["payload"]
    ledger = load("research_evidence_ledger_v1.json")["payload"]
    relations = load("research_relations_v1.json")["payload"]

    # 1. duplicate evidence ID
    ids = [evidence["primary_evidence"]["identity"]["evidence_id"],
           evidence["retroactive_methodological_audit"]["identity"]["evidence_id"]]
    check("no_duplicate_evidence_id", len(ids) == len(set(ids)), f"ids={ids}")

    # 2. missing hypothesis
    hid_primary = evidence["primary_evidence"]["identity"]["hypothesis_id"]
    hid_audit = evidence["retroactive_methodological_audit"]["identity"]["hypothesis_id"]
    hid_card = card["hypothesis_id"]
    check("hypothesis_id_present_and_consistent",
          all([hid_primary, hid_audit, hid_card]) and hid_primary == hid_audit == hid_card,
          f"primary={hid_primary} audit={hid_audit} card={hid_card}")

    # 3. broken relation (ogni 'from'/'to' che referenzia un id noto deve
    # comparire da qualche parte nel corpus - controllo debole ma reale:
    # nessun nodo isolato che non compare MAI in nessun altro artifact)
    known_ids = set()
    known_ids.add(evidence["primary_evidence"]["identity"]["evidence_id"])
    known_ids.add(evidence["retroactive_methodological_audit"]["identity"]["evidence_id"])
    known_ids.add(evidence["hypothesis_id"])
    known_ids.add(obs["observations"][0]["observation_id"])
    known_ids.add("H004_EVENT_RECLAIM")
    for t in ledger["transitions"]:
        known_ids.add(t["entity"])
    broken = []
    for e in relations["edges"]:
        for endpoint in (e["from"], e["to"]):
            if endpoint not in known_ids and not endpoint.startswith("EXP-") and endpoint not in ("DEPENDENCE_AUDIT_PASS_GATE", "H006_PRE_PHASE6.5_RECORD"):
                broken.append(endpoint)
    check("no_broken_relation_endpoints", len(broken) == 0, f"unresolved={broken}")

    # 4. malformed source (source_files devono essere path relativi, mai assoluti)
    bad_paths = []
    for section in (evidence["primary_evidence"], evidence["retroactive_methodological_audit"]):
        for p in section["provenance"]["source_files"]:
            if os.path.isabs(p) or ":" in p or p.startswith("C") and "\\" in p:
                bad_paths.append(p)
    check("no_absolute_source_paths", len(bad_paths) == 0, f"bad={bad_paths}")

    # 5. hash mismatch (ricalcola gli hash dei source_files dichiarati e confronta)
    from canonical_utils import file_sha256
    mismatches = []
    for section in (evidence["primary_evidence"], evidence["retroactive_methodological_audit"]):
        for relp, declared_hash in section["provenance"]["source_hashes"].items():
            abs_path = os.path.join(ROOT, relp)
            if os.path.exists(abs_path):
                real_hash = file_sha256(abs_path)
                if real_hash != declared_hash:
                    mismatches.append(relp)
            else:
                mismatches.append(f"{relp} (file not found)")
    check("no_hash_mismatch", len(mismatches) == 0, f"mismatches={mismatches}")

    # 6. forbidden grade promotion: grade primario deve restare E2, mai E3/E4/E5
    grade = evidence["primary_evidence"]["evidence_classification"]["evidence_grade"]
    check("h006_grade_not_promoted", grade == "E2", f"grade={grade}")
    check("audit_record_has_no_own_grade", evidence["retroactive_methodological_audit"]["evidence_classification"]["evidence_grade"] is None,
          f"audit_grade={evidence['retroactive_methodological_audit']['evidence_classification']['evidence_grade']}")

    # 7. post-hoc observation erroneamente marcata come edge
    o = obs["observations"][0]
    check("post_hoc_observation_not_marked_as_edge", o["is_edge"] is False and o["is_validated"] is False,
          f"is_edge={o['is_edge']} is_validated={o['is_validated']}")
    check("post_hoc_observation_requires_new_work", o["requires_new_hypothesis"] is True and o["requires_new_holdout"] is True)

    # 8. H006 erroneamente portata a E3
    check("h006_not_at_e3", card["current_grade"] != "E3" and card["decision"] == "RETAIN_E2",
          f"current_grade={card['current_grade']} decision={card['decision']}")

    # 9. E4/E5 erroneamente autorizzati
    check("e4_e5_not_authorized", card["promotion_allowed"] is False and card["next_stage_allowed"] is False
          and set(card["next_stages_explicitly_not_authorized"]) >= {"E4", "E5"},
          f"promotion_allowed={card['promotion_allowed']} next_stage_allowed={card['next_stage_allowed']}")

    # 10. deterministic regeneration - rilancia ogni generatore due volte e
    # confronta canonical_sha256
    generators = ["build_h006_evidence_v2.py", "build_h006_decision_card_v2.py",
                  "build_post_hoc_observations.py", "build_research_ledger.py",
                  "build_research_relations.py"]
    det_failures = []
    for g in generators:
        hashes = set()
        for _ in range(2):
            out = subprocess.run([sys.executable, os.path.join(PHASE66_DIR, g)],
                                  capture_output=True, text=True, cwd=PHASE66_DIR)
            for line in out.stdout.splitlines():
                if line.startswith("canonical_sha256:"):
                    hashes.add(line.split(":", 1)[1].strip())
        if len(hashes) != 1:
            det_failures.append({g: list(hashes)})
    check("deterministic_regeneration", len(det_failures) == 0, f"failures={det_failures}")

    n_pass = sum(1 for r in RESULTS if r["result"] == "PASS")
    n_fail = sum(1 for r in RESULTS if r["result"] == "FAIL")
    overall = "INTEGRITY_SUITE_PASS" if n_fail == 0 else "INTEGRITY_SUITE_FAIL"

    report = {"schema_version": 1, "overall": overall, "n_checks": len(RESULTS), "n_pass": n_pass, "n_fail": n_fail, "checks": RESULTS}
    from canonical_utils import save_json, wrap_with_provenance
    wrapped = wrap_with_provenance(report, script="server/research_scripts/phase6_6/validate_integrity.py")
    save_json(os.path.join(PHASE66_DIR, "integrity_test_report.json"), wrapped)
    print(f"OVERALL: {overall} ({n_pass}/{len(RESULTS)} passed)")
    for r in RESULTS:
        print(f"  [{r['result']}] {r['check']} {('- ' + r['detail']) if r['detail'] else ''}")
    return overall


if __name__ == "__main__":
    overall = main()
    sys.exit(0 if overall == "INTEGRITY_SUITE_PASS" else 1)
